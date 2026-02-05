"""
Consensus Engine for Multi-Agent Profile Synthesis

PRD v1.2 결정 사항:
- Perplexity (검색) + Gemini (검증/보완) + Claude Opus (합성)
- Jaccard Similarity >= 0.7 기준 문자열 매칭
- discrepancy 필드 표시 및 Perplexity 값 우선

v1.3 변경사항:
- kiwipiepy 형태소 분석기 도입 (BUG-001 수정)
- 품사 기반 불용어 필터링

v1.4 변경사항:
- Hybrid Semantic Consensus 추가
- Primary: Embedding 유사도 (코사인 유사도)
- Fallback: Jaccard 유사도 (Embedding 사용 불가 시)

P2-3 Fix:
- Jaccard Similarity 캐싱 (LRU Cache)
- 필드별 다른 threshold 지원 (FieldThresholds)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Optional
from enum import Enum

from app.worker.tracing import get_logger

logger = get_logger("ConsensusEngine")

# Lazy import for kiwipiepy (heavy initialization)
_kiwi_instance = None


def _get_kiwi():
    """Kiwi 인스턴스 싱글톤 (lazy initialization)"""
    global _kiwi_instance
    if _kiwi_instance is None:
        try:
            from kiwipiepy import Kiwi
            _kiwi_instance = Kiwi()
            logger.info("[ConsensusEngine] Kiwi morphological analyzer initialized")
        except ImportError:
            logger.warning(
                "[ConsensusEngine] kiwipiepy not installed. "
                "Falling back to simple tokenization. "
                "Install with: pip install kiwipiepy"
            )
            _kiwi_instance = False  # Mark as unavailable
    return _kiwi_instance


# ============================================================================
# Korean POS Tags to Filter (Stopwords)
# ============================================================================

# 품사 태그 기반 불용어 (형태소 분석기 사용 시)
# Reference: https://github.com/bab2min/kiwipiepy#품사-태그
STOPWORD_POS_TAGS = {
    # 조사 (모든 종류의 조사 필터링)
    "JKS",  # 주격 조사 (이/가)
    "JKC",  # 보격 조사 (이/가)
    "JKG",  # 관형격 조사 (의)
    "JKO",  # 목적격 조사 (을/를)
    "JKB",  # 부사격 조사 (에/에서/로/으로)
    "JKV",  # 호격 조사 (아/야)
    "JKQ",  # 인용격 조사 (고/라고)
    "JX",   # 보조사 (은/는/도/만/까지/부터)
    "JC",   # 접속 조사 (와/과)
    # 어미
    "EP",   # 선어말 어미
    "EF",   # 종결 어미
    "EC",   # 연결 어미
    "ETN",  # 명사형 전성 어미
    "ETM",  # 관형형 전성 어미
    # 기호
    "SF",   # 마침표, 물음표, 느낌표
    "SP",   # 쉼표, 가운뎃점, 콜론, 빗금
    "SS",   # 따옴표, 괄호표, 줄표
    "SE",   # 줄임표
    "SO",   # 붙임표 (물결, 숨김, 빠짐)
    "SW",   # 기타 특수문자
}

# 의미 없는 의존 명사 (NNB) 및 기능 명사
STOPWORD_NOUNS = {
    "것", "수", "때", "중", "내", "외", "바", "데", "뿐",
    "등",  # "등의", "등을" 등에서 분리된 "등"
    "위", "후", "전", "간", "상", "하",
}

# 단독 출현 시 불용어로 처리할 단일 문자
# (형태소 분석기가 NNG/IC 등으로 잘못 분류하는 경우 대응)
SINGLE_CHAR_STOPWORDS = {
    # 조사가 단독으로 나올 때 NNG로 분류되는 경우
    "의", "을", "를", "이", "가", "은", "는", "에", "와", "과",
    "로", "으", "도", "만", "께", "한", "랑", "처",
    # 조사 일부
    "르",  # "을를"에서 분리
    "부", "터",  # "부터"에서 분리
    "까", "지",  # "까지"에서 분리
    "서",  # "에서"에서 분리
}

# 접속부사/일반부사 (MAJ, MAG) 중 불용어
STOPWORD_ADVERBS = {
    "및", "등", "또는", "그리고", "하지만", "그러나", "따라서",
    "또한", "그래서", "그런데", "왜냐하면", "즉",
}

# Fallback용 기존 불용어 (형태소 분석기 없을 때)
KOREAN_STOPWORDS = {
    # 단일 조사
    "은", "는", "이", "가", "을", "를", "에", "에서", "로", "으로",
    "의", "와", "과", "도", "만", "까지", "부터", "에게", "한테",
    # 복합 조사 (BUG-001 수정)
    "등의", "을를", "은는", "에서는", "로부터", "이나", "에게는",
    "까지는", "부터는", "만으로", "으로서", "으로써", "에서의",
    "와의", "과의", "로의", "에의", "에도", "에서도", "로도",
    # 주격+보격 조사 결합 (BUG-001 추가 수정)
    "이가", "은는", "을를",
    # 접속사/부사
    "및", "등", "또는", "그리고", "하지만", "그러나", "따라서",
    "또한", "그래서", "그런데", "왜냐하면", "즉",
    # 의존 명사
    "것", "수", "때", "중", "내", "외", "바", "데", "뿐",
}


# ============================================================================
# Data Classes
# ============================================================================


class SourceType(str, Enum):
    """데이터 출처 유형"""
    PERPLEXITY = "PERPLEXITY"
    GEMINI_INFERRED = "GEMINI_INFERRED"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class FieldConsensus:
    """개별 필드의 합의 결과"""
    field_name: str
    final_value: Any
    source: SourceType
    confidence: str  # HIGH, MED, LOW
    discrepancy: bool = False
    perplexity_value: Optional[Any] = None
    gemini_value: Optional[Any] = None
    similarity_score: Optional[float] = None
    notes: str = ""


@dataclass
class ConsensusMetadata:
    """합의 프로세스 메타데이터 (PRD v1.2)"""
    consensus_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    perplexity_success: bool = True
    gemini_success: bool = True
    claude_success: bool = True
    total_fields: int = 0
    matched_fields: int = 0
    discrepancy_fields: int = 0
    enriched_fields: int = 0
    overall_confidence: str = "MED"
    # v1.1 추가 필드
    fallback_layer: int = 0  # 0: 정상, 1: Perplexity 실패, 2: Claude 실패, 3: Rule-based
    retry_count: int = 0
    error_messages: list[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """Consensus Engine 최종 결과"""
    profile: dict
    field_details: list[FieldConsensus]
    metadata: ConsensusMetadata


# ============================================================================
# Jaccard Similarity
# ============================================================================


def tokenize(text: str) -> set[str]:
    """
    한국어 텍스트 토큰화 (형태소 분석 기반)

    kiwipiepy 사용 시:
    - 형태소 분석으로 정확한 토큰 분리
    - 품사(POS) 태그 기반 불용어 필터링
    - 복합 조사 자동 처리

    Fallback (kiwipiepy 미설치 시):
    - 공백/구두점 기준 분리
    - 확장된 KOREAN_STOPWORDS로 필터링
    """
    if not text:
        return set()

    kiwi = _get_kiwi()

    if kiwi:
        # 형태소 분석기 사용
        return _tokenize_with_kiwi(text, kiwi)
    else:
        # Fallback: 단순 토큰화
        return _tokenize_simple(text)


def _tokenize_with_kiwi(text: str, kiwi) -> set[str]:
    """kiwipiepy 형태소 분석기를 사용한 토큰화"""
    tokens = set()

    try:
        # 형태소 분석 수행
        result = kiwi.tokenize(text)

        for token in result:
            form = token.form.lower()  # 원형
            tag = token.tag  # 품사 태그

            # [P1 FIX] 단일 문자 불용어 필터링 - 품사 태그와 무관하게 적용
            # "의", "를", "은", "는" 등이 NNG로 잘못 분류되어도 필터링
            # 반드시 품사 기반 필터링 전에 수행
            if len(form) == 1 and form in SINGLE_CHAR_STOPWORDS:
                continue

            # 품사 기반 필터링
            if tag in STOPWORD_POS_TAGS:
                continue

            # 의존 명사 필터링 (NNB)
            if tag == "NNB" and form in STOPWORD_NOUNS:
                continue

            # 일반 명사 중 기능어 필터링 (NNG)
            # "등", "위", "후" 등은 문맥에서 불용어로 작용
            if tag == "NNG" and form in STOPWORD_NOUNS:
                continue

            # 접속부사 필터링
            if tag in ("MAJ", "MAG") and form in STOPWORD_ADVERBS:
                continue

            # IC(감탄사) 중 조사 역할인 것 필터링
            if tag == "IC" and form in SINGLE_CHAR_STOPWORDS:
                continue

            # 빈 토큰 제외
            if form.strip():
                tokens.add(form)

    except Exception as e:
        logger.warning(f"[tokenize] Kiwi analysis failed, falling back: {e}")
        return _tokenize_simple(text)

    return tokens


def _tokenize_simple(text: str) -> set[str]:
    """Fallback: 단순 공백 기반 토큰화"""
    # 소문자 변환
    text = text.lower()

    # 구두점을 공백으로 변환
    text = re.sub(r'[^\w\s가-힣]', ' ', text)

    # 토큰 분리
    tokens = text.split()

    # Stopwords 제거 및 빈 토큰 제거
    tokens = {t for t in tokens if t and t not in KOREAN_STOPWORDS}

    return tokens


@lru_cache(maxsize=1024)
def _tokenize_cached(text: str) -> frozenset:
    """P2-3: 캐싱을 위한 tokenize wrapper (frozenset 반환)"""
    return frozenset(tokenize(text))


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Jaccard Similarity 계산 (P2-3: LRU 캐싱 적용)

    J(A,B) = |A ∩ B| / |A ∪ B|

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트

    Returns:
        float: 유사도 (0.0 ~ 1.0)
    """
    if not text_a and not text_b:
        return 1.0  # 둘 다 비어있으면 일치
    if not text_a or not text_b:
        return 0.0  # 하나만 비어있으면 불일치

    # P2-3: 캐시된 tokenize 사용
    tokens_a = _tokenize_cached(text_a)
    tokens_b = _tokenize_cached(text_b)

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union) if union else 0.0


def clear_jaccard_cache():
    """P2-3: 테스트용 캐시 클리어"""
    _tokenize_cached.cache_clear()
    logger.debug("[ConsensusEngine] Jaccard cache cleared")


# ============================================================================
# Semantic (Embedding) Similarity - v1.4
# ============================================================================

# Embedding service cache
_embedding_service = None
_embedding_available = None


def _get_embedding_service():
    """Embedding 서비스 싱글톤 (lazy initialization)"""
    global _embedding_service, _embedding_available

    if _embedding_available is None:
        try:
            from app.worker.llm.embedding import get_embedding_service
            _embedding_service = get_embedding_service()
            _embedding_available = True
            logger.info("embedding_service_initialized")
        except Exception as e:
            logger.warning(
                "embedding_service_unavailable",
                error=str(e),
                fallback="jaccard"
            )
            _embedding_available = False

    return _embedding_service if _embedding_available else None


def semantic_similarity(text_a: str, text_b: str) -> Optional[float]:
    """
    Semantic (Embedding) Similarity 계산 (동기 버전)

    P0-2 Fix: asyncio.run() 제거, 순수 동기 버전으로 변경.
    Celery Worker에서 안전하게 사용 가능.

    Note: 동기 컨텍스트에서는 Jaccard fallback을 사용하는 것을 권장.
    비동기 컨텍스트에서는 semantic_similarity_async() 사용.

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트

    Returns:
        Optional[float]: 유사도 (0.0 ~ 1.0), Embedding 사용 불가 시 None
    """
    if not text_a or not text_b:
        return None

    embedding_service = _get_embedding_service()
    if not embedding_service:
        return None

    try:
        # 동기 버전: embed_sync 메서드 사용 (있는 경우)
        if hasattr(embedding_service, 'embed_batch_sync'):
            embeddings = embedding_service.embed_batch_sync([text_a, text_b])
            if len(embeddings) != 2:
                return None
            return embedding_service.compute_similarity(embeddings[0], embeddings[1])
        else:
            # Embedding 서비스가 동기 메서드를 지원하지 않으면 None 반환
            # 호출자는 Jaccard fallback 사용
            logger.debug(
                "semantic_similarity_sync_unavailable",
                message="EmbeddingService does not support sync operations, use async version"
            )
            return None

    except Exception as e:
        logger.warning(
            "semantic_similarity_failed",
            error=str(e),
            fallback="jaccard"
        )
        return None


async def semantic_similarity_async(text_a: str, text_b: str) -> Optional[float]:
    """
    Semantic (Embedding) Similarity 계산 (비동기 버전)

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트

    Returns:
        Optional[float]: 유사도 (0.0 ~ 1.0), Embedding 사용 불가 시 None
    """
    if not text_a or not text_b:
        return None

    embedding_service = _get_embedding_service()
    if not embedding_service:
        return None

    try:
        embeddings = await embedding_service.embed_batch([text_a, text_b])
        if len(embeddings) != 2:
            return None
        return embedding_service.compute_similarity(embeddings[0], embeddings[1])
    except Exception as e:
        logger.warning(
            "semantic_similarity_async_failed",
            error=str(e),
            fallback="jaccard"
        )
        return None


def hybrid_similarity(text_a: str, text_b: str, prefer_jaccard: bool = False) -> tuple[float, str]:
    """
    Hybrid Similarity 계산 (동기 버전)

    P0-2 Fix: 동기 컨텍스트에서 안전하게 사용 가능.

    Primary: Embedding 유사도 (정확도 높음, 동기 API 지원 시)
    Fallback: Jaccard 유사도 (Embedding 사용 불가 시)

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트
        prefer_jaccard: True면 Embedding 시도 없이 바로 Jaccard 사용

    Returns:
        tuple[float, str]: (유사도, 사용된 방법 "embedding" | "jaccard")
    """
    if not text_a and not text_b:
        return 1.0, "both_empty"
    if not text_a or not text_b:
        return 0.0, "one_empty"

    # Jaccard 선호 모드 (async 컨텍스트에서 sync 호출 시 유용)
    if prefer_jaccard:
        jaccard_score = jaccard_similarity(text_a, text_b)
        return jaccard_score, "jaccard"

    # Try embedding similarity first
    embedding_score = semantic_similarity(text_a, text_b)
    if embedding_score is not None:
        logger.debug(
            "hybrid_similarity_used_embedding",
            score=embedding_score
        )
        return embedding_score, "embedding"

    # Fallback to Jaccard
    jaccard_score = jaccard_similarity(text_a, text_b)
    logger.debug(
        "hybrid_similarity_used_jaccard",
        score=jaccard_score
    )
    return jaccard_score, "jaccard"


async def hybrid_similarity_async(text_a: str, text_b: str) -> tuple[float, str]:
    """
    Hybrid Similarity 계산 (비동기 버전)

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트

    Returns:
        tuple[float, str]: (유사도, 사용된 방법)
    """
    if not text_a and not text_b:
        return 1.0, "both_empty"
    if not text_a or not text_b:
        return 0.0, "one_empty"

    # Try embedding similarity first
    embedding_score = await semantic_similarity_async(text_a, text_b)
    if embedding_score is not None:
        return embedding_score, "embedding"

    # Fallback to Jaccard
    jaccard_score = jaccard_similarity(text_a, text_b)
    return jaccard_score, "jaccard"


# ============================================================================
# Value Comparison
# ============================================================================


def compare_values(value_a: Any, value_b: Any, threshold: float = 0.7, use_semantic: bool = True) -> tuple[bool, float, str]:
    """
    두 값 비교 (Hybrid Semantic Similarity 지원)

    Args:
        value_a: 첫 번째 값
        value_b: 두 번째 값
        threshold: 유사도 임계값 (기본 0.7)
        use_semantic: Semantic Similarity 사용 여부 (기본 True)

    Returns:
        tuple[bool, float, str]: (일치 여부, 유사도 점수, 사용된 방법)
    """
    # 둘 다 None이면 일치
    if value_a is None and value_b is None:
        return True, 1.0, "both_none"

    # 하나만 None이면 불일치
    if value_a is None or value_b is None:
        return False, 0.0, "one_none"

    # 타입이 다르면 불일치
    if type(value_a) != type(value_b):
        return False, 0.0, "type_mismatch"

    # 숫자 비교
    if isinstance(value_a, (int, float)):
        if value_a == 0 and value_b == 0:
            return True, 1.0, "numeric"
        if value_a == 0 or value_b == 0:
            return False, 0.0, "numeric"
        # 10% 이내 차이면 일치
        ratio = min(value_a, value_b) / max(value_a, value_b)
        return ratio >= 0.9, ratio, "numeric"

    # 리스트 비교
    if isinstance(value_a, list):
        if not value_a and not value_b:
            return True, 1.0, "list_empty"
        if not value_a or not value_b:
            return False, 0.0, "list_one_empty"
        # 리스트 요소의 Jaccard
        set_a = set(str(x).lower() for x in value_a)
        set_b = set(str(x).lower() for x in value_b)
        intersection = set_a & set_b
        union = set_a | set_b
        score = len(intersection) / len(union) if union else 0.0
        return score >= threshold, score, "list_jaccard"

    # 딕셔너리 비교
    if isinstance(value_a, dict):
        if not value_a and not value_b:
            return True, 1.0, "dict_empty"
        if not value_a or not value_b:
            return False, 0.0, "dict_one_empty"
        # 키 일치도
        keys_a = set(value_a.keys())
        keys_b = set(value_b.keys())
        key_intersection = keys_a & keys_b
        key_union = keys_a | keys_b
        key_score = len(key_intersection) / len(key_union) if key_union else 0.0

        # 공통 키의 값 일치도
        if key_intersection:
            value_matches = sum(
                1 for k in key_intersection
                if compare_values(value_a[k], value_b[k], threshold, use_semantic)[0]
            )
            value_score = value_matches / len(key_intersection)
        else:
            value_score = 0.0

        # 종합 점수
        score = (key_score + value_score) / 2
        return score >= threshold, score, "dict"

    # 문자열 비교 (Hybrid Similarity)
    if isinstance(value_a, str):
        if use_semantic:
            score, method = hybrid_similarity(value_a, value_b)
        else:
            score = jaccard_similarity(value_a, value_b)
            method = "jaccard"
        return score >= threshold, score, method

    # 기타 타입: 정확히 일치 확인
    return value_a == value_b, 1.0 if value_a == value_b else 0.0, "exact"


def compare_values_legacy(value_a: Any, value_b: Any, threshold: float = 0.7) -> tuple[bool, float]:
    """
    Legacy compare_values (backward compatibility)

    Returns:
        tuple[bool, float]: (일치 여부, 유사도 점수)
    """
    is_match, score, _ = compare_values(value_a, value_b, threshold, use_semantic=False)
    return is_match, score


# ============================================================================
# Consensus Engine
# ============================================================================


@dataclass
class FieldThresholds:
    """
    P2-3: 필드별 Similarity Threshold 관리

    필드 유형에 따라 다른 threshold 적용:
    - name: 높은 정확도 요구 (0.9)
    - summary: 유연한 매칭 허용 (0.6)
    - numeric: 비율 기반 비교 (10%)
    - default: 기본값 (0.7)
    """
    default: float = 0.7
    name: float = 0.9
    summary: float = 0.6
    numeric: float = 0.1  # 10% tolerance

    # 필드명 매핑
    NAME_FIELDS: set[str] = field(default_factory=lambda: {
        "ceo_name", "corp_name", "headquarters", "key_suppliers",
        "key_customers", "executives", "competitors",
    })
    SUMMARY_FIELDS: set[str] = field(default_factory=lambda: {
        "business_summary", "industry_overview", "business_model",
    })
    NUMERIC_FIELDS: set[str] = field(default_factory=lambda: {
        "revenue_krw", "export_ratio_pct", "employee_count", "founded_year",
    })

    def get_threshold(self, field_name: str) -> float:
        """필드명에 맞는 threshold 반환"""
        if field_name in self.NAME_FIELDS:
            return self.name
        elif field_name in self.SUMMARY_FIELDS:
            return self.summary
        elif field_name in self.NUMERIC_FIELDS:
            return self.numeric
        return self.default

    @classmethod
    def from_settings(cls) -> "FieldThresholds":
        """설정에서 threshold 로드"""
        try:
            from app.core.config import settings
            return cls(
                default=settings.CONSENSUS_SIMILARITY_THRESHOLD,
                name=settings.CONSENSUS_THRESHOLD_NAME,
                summary=settings.CONSENSUS_THRESHOLD_SUMMARY,
                numeric=settings.CONSENSUS_THRESHOLD_NUMBER,
            )
        except Exception:
            return cls()  # 기본값 사용


class ConsensusEngine:
    """
    Multi-Agent Consensus Engine (v1.4 Hybrid Semantic)

    3개 소스의 프로필 정보를 합성:
    1. Perplexity (Primary Search)
    2. Gemini (Validation + Enrichment)
    3. Claude (Final Synthesis)

    합의 규칙 (v1.4):
    - Hybrid Similarity >= threshold: 일치 → Perplexity 값 채택
      - Primary: Embedding 코사인 유사도
      - Fallback: Jaccard 유사도
    - 불일치: Perplexity 값 채택 + discrepancy: true
    - null: Gemini enriched 값 사용 (source: GEMINI_INFERRED)

    P2-3: 필드별 threshold 지원
    """

    # 필드별 비교 전략
    STRING_FIELDS = {"business_summary", "industry_overview", "business_model"}
    NUMERIC_FIELDS = {"revenue_krw", "export_ratio_pct", "employee_count", "founded_year"}
    LIST_FIELDS = {"key_materials", "key_customers", "overseas_operations", "key_suppliers", "executives", "competitors", "macro_factors"}
    DICT_FIELDS = {"country_exposure", "supply_chain", "regulatory_exposure", "overseas_business", "shareholders", "financial_history"}

    def __init__(self, use_semantic: bool = True, thresholds: Optional[FieldThresholds] = None):
        """
        Args:
            use_semantic: Semantic (Embedding) Similarity 사용 여부 (기본 True)
            thresholds: 필드별 threshold 설정 (None이면 settings에서 로드)
        """
        self.metadata = ConsensusMetadata()
        self.use_semantic = use_semantic
        self._similarity_methods_used: dict[str, str] = {}
        self.thresholds = thresholds or FieldThresholds.from_settings()

    def merge(
        self,
        perplexity_profile: dict,
        gemini_result: dict,
        corp_name: str,
        industry_code: str,
    ) -> ConsensusResult:
        """
        Perplexity + Gemini 결과 합성

        Args:
            perplexity_profile: Perplexity 추출 프로필
            gemini_result: Gemini 검증/보완 결과
            corp_name: 기업명
            industry_code: 업종 코드

        Returns:
            ConsensusResult: 합성된 프로필
        """
        field_details = []
        merged_profile = {}

        # Gemini 결과에서 enriched_fields와 discrepancies 추출
        gemini_enriched = gemini_result.get("enriched_fields", {})
        gemini_discrepancies = {
            d["field"]: d for d in gemini_result.get("discrepancies", [])
        }
        gemini_validated = set(gemini_result.get("validated_fields", []))

        # 모든 필드 목록 수집
        all_fields = set(perplexity_profile.keys()) | set(gemini_enriched.keys())
        all_fields -= {"_source_urls", "_uncertainty_notes", "profile_id", "corp_id"}

        for field_name in all_fields:
            consensus = self._merge_field(
                field_name=field_name,
                perplexity_value=perplexity_profile.get(field_name),
                gemini_enriched=gemini_enriched.get(field_name),
                is_validated=field_name in gemini_validated,
                discrepancy_info=gemini_discrepancies.get(field_name),
            )

            field_details.append(consensus)
            merged_profile[field_name] = consensus.final_value

            # 메타데이터 업데이트
            if consensus.discrepancy:
                self.metadata.discrepancy_fields += 1
            elif consensus.source == SourceType.GEMINI_INFERRED:
                self.metadata.enriched_fields += 1
            else:
                self.metadata.matched_fields += 1

        self.metadata.total_fields = len(field_details)
        self.metadata.overall_confidence = self._determine_overall_confidence(field_details)

        # 메타데이터를 프로필에 추가
        merged_profile["_consensus_metadata"] = {
            "consensus_at": self.metadata.consensus_at,
            "perplexity_success": self.metadata.perplexity_success,
            "gemini_success": self.metadata.gemini_success,
            "total_fields": self.metadata.total_fields,
            "matched_fields": self.metadata.matched_fields,
            "discrepancy_fields": self.metadata.discrepancy_fields,
            "enriched_fields": self.metadata.enriched_fields,
            "overall_confidence": self.metadata.overall_confidence,
            "fallback_layer": self.metadata.fallback_layer,
            "retry_count": self.metadata.retry_count,
            "error_messages": self.metadata.error_messages,
        }

        # Count similarity methods used
        embedding_count = sum(1 for m in self._similarity_methods_used.values() if m == "embedding")
        jaccard_count = sum(1 for m in self._similarity_methods_used.values() if m == "jaccard")

        logger.info(
            "consensus_merged",
            total_fields=self.metadata.total_fields,
            matched_fields=self.metadata.matched_fields,
            discrepancy_fields=self.metadata.discrepancy_fields,
            enriched_fields=self.metadata.enriched_fields,
            confidence=self.metadata.overall_confidence,
            use_semantic=self.use_semantic,
            embedding_comparisons=embedding_count,
            jaccard_comparisons=jaccard_count,
        )

        # Add similarity method stats to metadata
        merged_profile["_consensus_metadata"]["similarity_methods"] = {
            "embedding": embedding_count,
            "jaccard": jaccard_count,
            "use_semantic_enabled": self.use_semantic,
        }

        return ConsensusResult(
            profile=merged_profile,
            field_details=field_details,
            metadata=self.metadata,
        )

    def _merge_field(
        self,
        field_name: str,
        perplexity_value: Any,
        gemini_enriched: Optional[dict],
        is_validated: bool,
        discrepancy_info: Optional[dict],
    ) -> FieldConsensus:
        """개별 필드 합성"""

        # P1-1 Fix: Gemini enriched 값 추출 (다양한 형식 처리)
        gemini_value = None
        gemini_confidence = "LOW"
        if gemini_enriched:
            gemini_value, gemini_confidence = self._extract_gemini_value(
                gemini_enriched, field_name
            )

        # Case 1: Perplexity 값이 null이고 Gemini가 보완한 경우
        if perplexity_value is None or perplexity_value == [] or perplexity_value == {}:
            if gemini_value is not None:
                return FieldConsensus(
                    field_name=field_name,
                    final_value=gemini_value,
                    source=SourceType.GEMINI_INFERRED,
                    confidence=gemini_confidence,
                    discrepancy=False,
                    perplexity_value=perplexity_value,
                    gemini_value=gemini_value,
                    similarity_score=None,
                    notes="Perplexity null, Gemini enriched",
                )
            else:
                # 둘 다 null
                return FieldConsensus(
                    field_name=field_name,
                    final_value=None,
                    source=SourceType.UNKNOWN,
                    confidence="LOW",
                    discrepancy=False,
                    perplexity_value=None,
                    gemini_value=None,
                    similarity_score=None,
                    notes="Both sources null",
                )

        # Case 2: Gemini에서 discrepancy 발견
        if discrepancy_info:
            return FieldConsensus(
                field_name=field_name,
                final_value=perplexity_value,  # Perplexity 값 채택
                source=SourceType.PERPLEXITY,
                confidence="MED",  # discrepancy면 confidence 낮춤
                discrepancy=True,
                perplexity_value=perplexity_value,
                gemini_value=gemini_value,
                similarity_score=0.0,
                notes=discrepancy_info.get("issue", "Gemini flagged discrepancy"),
            )

        # Case 3: 둘 다 값이 있는 경우 - Hybrid Similarity 비교
        if gemini_value is not None:
            # P2-3: 필드별 threshold 사용
            field_threshold = self.thresholds.get_threshold(field_name)

            is_match, score, method = compare_values(
                perplexity_value,
                gemini_value,
                field_threshold,
                use_semantic=self.use_semantic,
            )

            # Track which method was used
            self._similarity_methods_used[field_name] = method

            if is_match:
                # 일치: Perplexity 값 채택, 높은 신뢰도
                return FieldConsensus(
                    field_name=field_name,
                    final_value=perplexity_value,
                    source=SourceType.PERPLEXITY,
                    confidence="HIGH" if score >= 0.9 else "MED",
                    discrepancy=False,
                    perplexity_value=perplexity_value,
                    gemini_value=gemini_value,
                    similarity_score=score,
                    notes=f"Matched ({method}={score:.2f}, threshold={field_threshold})",
                )
            else:
                # 불일치: Perplexity 값 채택 + discrepancy 표시
                return FieldConsensus(
                    field_name=field_name,
                    final_value=perplexity_value,
                    source=SourceType.PERPLEXITY,
                    confidence="MED",
                    discrepancy=True,
                    perplexity_value=perplexity_value,
                    gemini_value=gemini_value,
                    similarity_score=score,
                    notes=f"Discrepancy ({method}={score:.2f} < {field_threshold})",
                )

        # Case 4: Perplexity만 값이 있는 경우
        # Gemini 검증 통과 여부에 따라 신뢰도 결정
        return FieldConsensus(
            field_name=field_name,
            final_value=perplexity_value,
            source=SourceType.PERPLEXITY,
            confidence="MED" if is_validated else "LOW",
            discrepancy=False,
            perplexity_value=perplexity_value,
            gemini_value=None,
            similarity_score=None,
            notes="Perplexity only" + (" (validated)" if is_validated else ""),
        )

    def _extract_gemini_value(
        self,
        gemini_enriched: Any,
        field_name: str,
    ) -> tuple[Any, str]:
        """
        P1-1 Fix: Gemini enriched 필드에서 값 안전하게 추출

        다양한 형식 처리:
        1. {"value": X, "confidence": Y} - 표준 형식
        2. {"field_name": X, "source": "GEMINI_INFERRED"} - 메타데이터 포함
        3. 직접 값 (list, dict, str 등)

        Returns:
            (value, confidence)
        """
        if gemini_enriched is None:
            return None, "LOW"

        # 표준 형식: {"value": X, "confidence": Y}
        if isinstance(gemini_enriched, dict) and "value" in gemini_enriched:
            return (
                gemini_enriched["value"],
                gemini_enriched.get("confidence", "LOW"),
            )

        # 메타데이터 포함 형식: {"source": "GEMINI_INFERRED", ...}
        # "value" 키가 없지만 source/confidence 같은 메타 키가 있는 경우
        if isinstance(gemini_enriched, dict):
            meta_keys = {"source", "confidence", "reasoning", "error", "error_type"}
            data_keys = set(gemini_enriched.keys()) - meta_keys

            if data_keys and meta_keys & set(gemini_enriched.keys()):
                # 메타 키 제외하고 실제 데이터만 추출
                if len(data_keys) == 1:
                    # 단일 필드인 경우 그 값 반환
                    data_key = list(data_keys)[0]
                    return (
                        gemini_enriched[data_key],
                        gemini_enriched.get("confidence", "LOW"),
                    )
                else:
                    # 여러 필드인 경우 메타 키 제외한 dict 반환
                    extracted = {k: v for k, v in gemini_enriched.items() if k not in meta_keys}
                    return extracted, gemini_enriched.get("confidence", "LOW")

            # 일반 dict (메타 키 없음) - 그대로 반환
            return gemini_enriched, "LOW"

        # 직접 값 (list, str, int 등)
        return gemini_enriched, "LOW"

    def _determine_overall_confidence(self, field_details: list[FieldConsensus]) -> str:
        """전체 프로필 신뢰도 결정"""
        if not field_details:
            return "LOW"

        # discrepancy 비율
        discrepancy_ratio = sum(1 for f in field_details if f.discrepancy) / len(field_details)

        # GEMINI_INFERRED 비율
        inferred_ratio = sum(
            1 for f in field_details if f.source == SourceType.GEMINI_INFERRED
        ) / len(field_details)

        # HIGH 신뢰도 필드 비율
        high_confidence_ratio = sum(
            1 for f in field_details if f.confidence == "HIGH"
        ) / len(field_details)

        # 판정
        if discrepancy_ratio > 0.3:
            return "LOW"  # 30% 이상 불일치
        if inferred_ratio > 0.5:
            return "LOW"  # 50% 이상 Gemini 추론
        if high_confidence_ratio >= 0.5 and discrepancy_ratio < 0.1:
            return "HIGH"
        return "MED"

    def set_fallback_info(self, layer: int, retry_count: int, error_messages: list[str]):
        """Fallback 정보 설정"""
        self.metadata.fallback_layer = layer
        self.metadata.retry_count = retry_count
        self.metadata.error_messages = error_messages

    def set_source_status(self, perplexity: bool, gemini: bool, claude: bool):
        """소스별 성공 여부 설정"""
        self.metadata.perplexity_success = perplexity
        self.metadata.gemini_success = gemini
        self.metadata.claude_success = claude


# Factory function
def get_consensus_engine() -> ConsensusEngine:
    """ConsensusEngine 인스턴스 반환"""
    return ConsensusEngine()


# ============================================================================
# Structured Conflict Resolution (OpenAI Context 유지)
# ============================================================================


@dataclass
class ConflictInfo:
    """개별 충돌 정보"""
    field: str
    perplexity_value: Any
    gemini_value: Any
    perplexity_source: Optional[str] = None
    gemini_source: Optional[str] = None
    perplexity_source_score: int = 50
    gemini_source_score: int = 50
    resolution_hint: str = ""  # Rule-based 해결 힌트
    needs_llm_judgment: bool = False  # LLM 판단 필요 여부


@dataclass
class StructuredConflictInput:
    """
    OpenAI 합성을 위한 Structured Input

    OpenAI가 context를 유지하며 충돌을 해결할 수 있도록
    원본 쿼리, 확인된 필드, 충돌 필드, 단일 소스 필드를 구조화
    """
    corp_name: str
    industry_name: str
    original_query: str  # 원본 검색 쿼리 (맥락 유지)
    confirmed: list[dict]  # 두 소스가 일치하는 필드
    conflicts: list[ConflictInfo]  # 충돌 필드 (Rule로 해결 안 된 것만)
    perplexity_only: list[dict]  # Perplexity만 값 있는 필드
    gemini_only: list[dict]  # Gemini만 값 있는 필드
    rule_resolved: list[dict]  # Rule-based로 이미 해결된 충돌

    def to_openai_prompt(self) -> str:
        """OpenAI 프롬프트용 JSON 생성"""
        import json

        return json.dumps({
            "corp_name": self.corp_name,
            "industry_name": self.industry_name,
            "original_query": self.original_query,
            "confirmed_fields": self.confirmed,
            "conflicts_needing_judgment": [
                {
                    "field": c.field,
                    "perplexity": {
                        "value": c.perplexity_value,
                        "source": c.perplexity_source,
                        "source_credibility": c.perplexity_source_score,
                    },
                    "gemini": {
                        "value": c.gemini_value,
                        "source": c.gemini_source,
                        "source_credibility": c.gemini_source_score,
                    },
                    "hint": c.resolution_hint,
                }
                for c in self.conflicts if c.needs_llm_judgment
            ],
            "perplexity_only_fields": self.perplexity_only,
            "gemini_only_fields": self.gemini_only,
            "rule_resolved_fields": self.rule_resolved,
        }, ensure_ascii=False, indent=2)


@dataclass
class ConflictResolutionResult:
    """충돌 해결 결과"""
    resolved_profile: dict
    source_map: dict  # {"field": "PERPLEXITY" | "GEMINI" | "OPENAI_RESOLVED"}
    rule_resolved_count: int  # Rule로 해결된 충돌 수
    llm_resolved_count: int  # LLM이 해결한 충돌 수
    unresolved_count: int  # 미해결 충돌 수
    resolution_details: list[dict]  # 해결 상세 내역


class StructuredConflictResolver:
    """
    Structured Conflict Resolution

    충돌 해결 2단계:
    1. Rule-based: 출처 신뢰도, 날짜, 숫자 정확도 기반
    2. LLM-based: Rule로 해결 안 되는 경우 OpenAI 판단

    OpenAI Context 유지:
    - 원본 쿼리 전달 (맥락)
    - 출처 신뢰도 힌트 제공
    - 구조화된 충돌 정보 전달
    """

    # 출처 도메인별 신뢰도 점수
    SOURCE_CREDIBILITY = {
        # 공시 (최고 신뢰도)
        "dart.fss.or.kr": 100,
        "kind.krx.co.kr": 100,
        "opendart.fss.or.kr": 100,
        # 공식 IR
        "ir.": 95,
        "investor.": 95,
        # 정부/공공 통계
        "kostat.go.kr": 95,
        "kita.net": 90,
        "kosis.kr": 90,
        # 주요 언론
        "hankyung.com": 80,
        "mk.co.kr": 80,
        "sedaily.com": 80,
        "reuters.com": 85,
        "bloomberg.com": 85,
        # 일반 뉴스
        "news.": 60,
        "default": 50,
    }

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def get_source_credibility(self, url: Optional[str]) -> int:
        """URL에서 출처 신뢰도 점수 반환"""
        if not url:
            return self.SOURCE_CREDIBILITY["default"]

        url_lower = url.lower()
        for domain, score in self.SOURCE_CREDIBILITY.items():
            if domain in url_lower:
                return score
        return self.SOURCE_CREDIBILITY["default"]

    def build_structured_input(
        self,
        perplexity_profile: dict,
        gemini_profile: dict,
        corp_name: str,
        industry_name: str,
        original_query: str,
        perplexity_citations: Optional[list[str]] = None,
        gemini_citations: Optional[list[str]] = None,
    ) -> StructuredConflictInput:
        """
        Structured Conflict Input 생성

        1. 두 프로필 비교
        2. 일치/충돌/단일소스 분류
        3. Rule-based로 해결 가능한 충돌 미리 처리
        """
        confirmed = []
        conflicts = []
        perplexity_only = []
        gemini_only = []
        rule_resolved = []

        all_fields = set(perplexity_profile.keys()) | set(gemini_profile.keys())
        all_fields -= {"_source_urls", "_search_source", "_uncertainty_notes", "error", "error_type"}

        p_source = perplexity_citations[0] if perplexity_citations else None
        g_source = gemini_citations[0] if gemini_citations else None

        for field in all_fields:
            p_val = perplexity_profile.get(field)
            g_val = gemini_profile.get(field)

            # 둘 다 없음
            if p_val is None and g_val is None:
                continue

            # Perplexity만 있음
            if g_val is None:
                perplexity_only.append({
                    "field": field,
                    "value": p_val,
                    "source": p_source,
                    "confidence": "MED",
                })
                continue

            # Gemini만 있음
            if p_val is None:
                gemini_only.append({
                    "field": field,
                    "value": g_val,
                    "source": g_source,
                    "confidence": "LOW",  # Gemini 추론은 낮은 신뢰도
                })
                continue

            # 둘 다 있음 - 비교
            is_match, score, method = compare_values(p_val, g_val, self.similarity_threshold)

            if is_match:
                # 일치
                confirmed.append({
                    "field": field,
                    "value": p_val,
                    "sources": ["perplexity", "gemini"],
                    "similarity": score,
                    "method": method,
                    "confidence": "HIGH",
                })
            else:
                # 충돌 - Rule-based 해결 시도
                p_score = self.get_source_credibility(p_source)
                g_score = self.get_source_credibility(g_source)

                conflict = ConflictInfo(
                    field=field,
                    perplexity_value=p_val,
                    gemini_value=g_val,
                    perplexity_source=p_source,
                    gemini_source=g_source,
                    perplexity_source_score=p_score,
                    gemini_source_score=g_score,
                )

                # Rule-based 해결 시도
                resolved, reason = self._try_rule_based_resolution(
                    field, p_val, g_val, p_score, g_score
                )

                if resolved is not None:
                    # Rule로 해결됨
                    rule_resolved.append({
                        "field": field,
                        "resolved_value": resolved,
                        "resolution_reason": reason,
                        "perplexity_value": p_val,
                        "gemini_value": g_val,
                    })
                else:
                    # LLM 판단 필요
                    conflict.needs_llm_judgment = True
                    conflict.resolution_hint = reason
                    conflicts.append(conflict)

        return StructuredConflictInput(
            corp_name=corp_name,
            industry_name=industry_name,
            original_query=original_query,
            confirmed=confirmed,
            conflicts=conflicts,
            perplexity_only=perplexity_only,
            gemini_only=gemini_only,
            rule_resolved=rule_resolved,
        )

    def _try_rule_based_resolution(
        self,
        field: str,
        p_val: Any,
        g_val: Any,
        p_score: int,
        g_score: int,
    ) -> tuple[Optional[Any], str]:
        """
        Rule-based 충돌 해결 시도

        Returns:
            (resolved_value, reason): 해결된 값과 이유, 해결 못하면 (None, hint)
        """
        # Rule 1: 출처 신뢰도 차이가 큰 경우 (20점 이상)
        score_diff = abs(p_score - g_score)
        if score_diff >= 20:
            if p_score > g_score:
                return p_val, f"Perplexity source more credible ({p_score} vs {g_score})"
            else:
                return g_val, f"Gemini source more credible ({g_score} vs {p_score})"

        # Rule 2: 숫자 필드 - 더 정밀한 값 선택
        if isinstance(p_val, (int, float)) and isinstance(g_val, (int, float)):
            # 비율/퍼센트 필드 (0-100 범위): 소수점이 더 정밀
            both_in_ratio_range = (0 <= float(p_val) <= 100) and (0 <= float(g_val) <= 100)

            if both_in_ratio_range:
                # 소수점 유무 확인 (35.5 vs 36)
                p_has_decimal = isinstance(p_val, float) and p_val != int(p_val)
                g_has_decimal = isinstance(g_val, float) and g_val != int(g_val)

                if p_has_decimal and not g_has_decimal:
                    return p_val, "More precise decimal value for ratio/percentage"
                if g_has_decimal and not p_has_decimal:
                    return g_val, "More precise decimal value for ratio/percentage"

            # 둘 다 같은 정밀도면 Perplexity 우선 (한국 공시 데이터 강점)
            return p_val, "Same precision, Perplexity preferred for Korean financial data"

        # Rule 3: 문자열 길이 - 더 상세한 값 선택 (단, 너무 길면 제외)
        if isinstance(p_val, str) and isinstance(g_val, str):
            p_len = len(p_val)
            g_len = len(g_val)

            if p_len > 500 or g_len > 500:
                # 너무 긴 값은 LLM 판단 필요
                return None, "Both values too long, need LLM judgment"

            if abs(p_len - g_len) > 50:
                # 길이 차이가 크면 더 상세한 것 선택
                if p_len > g_len:
                    return p_val, "More detailed (longer) value"
                else:
                    return g_val, "More detailed (longer) value"

        # Rule 4: 리스트 - 더 많은 항목 선택
        if isinstance(p_val, list) and isinstance(g_val, list):
            if len(p_val) != len(g_val):
                if len(p_val) > len(g_val):
                    return p_val, "More comprehensive list"
                else:
                    return g_val, "More comprehensive list"

        # Rule로 해결 불가 - LLM 판단 필요
        return None, f"Similar credibility ({p_score} vs {g_score}), need contextual judgment"

    def resolve(
        self,
        structured_input: StructuredConflictInput,
        llm_resolution_fn: Optional[Callable[[str], dict]] = None,
    ) -> ConflictResolutionResult:
        """
        충돌 해결 실행

        Args:
            structured_input: 구조화된 충돌 정보
            llm_resolution_fn: LLM 호출 함수 (Optional)
                signature: fn(prompt: str) -> dict[str, Any]

        Returns:
            ConflictResolutionResult
        """
        resolved_profile = {}
        source_map = {}
        resolution_details = []

        # 1. 확인된 필드 (일치)
        for item in structured_input.confirmed:
            field = item["field"]
            resolved_profile[field] = item["value"]
            source_map[field] = "CONFIRMED_BOTH"
            resolution_details.append({
                "field": field,
                "type": "confirmed",
                "value": item["value"],
            })

        # 2. Rule로 해결된 충돌
        for item in structured_input.rule_resolved:
            field = item["field"]
            resolved_profile[field] = item["resolved_value"]
            source_map[field] = "RULE_RESOLVED"
            resolution_details.append({
                "field": field,
                "type": "rule_resolved",
                "value": item["resolved_value"],
                "reason": item["resolution_reason"],
            })

        # 3. Perplexity만 있는 필드
        for item in structured_input.perplexity_only:
            field = item["field"]
            resolved_profile[field] = item["value"]
            source_map[field] = "PERPLEXITY"
            resolution_details.append({
                "field": field,
                "type": "perplexity_only",
                "value": item["value"],
            })

        # 4. Gemini만 있는 필드
        for item in structured_input.gemini_only:
            field = item["field"]
            resolved_profile[field] = item["value"]
            source_map[field] = "GEMINI_INFERRED"
            resolution_details.append({
                "field": field,
                "type": "gemini_only",
                "value": item["value"],
            })

        # 5. LLM 판단 필요한 충돌
        llm_resolved_count = 0
        unresolved_count = 0

        if structured_input.conflicts and llm_resolution_fn:
            # LLM 호출
            try:
                prompt = structured_input.to_openai_prompt()
                llm_result = llm_resolution_fn(prompt)

                if isinstance(llm_result, dict):
                    for conflict in structured_input.conflicts:
                        if conflict.field in llm_result:
                            resolved_profile[conflict.field] = llm_result[conflict.field]
                            source_map[conflict.field] = "OPENAI_RESOLVED"
                            llm_resolved_count += 1
                            resolution_details.append({
                                "field": conflict.field,
                                "type": "llm_resolved",
                                "value": llm_result[conflict.field],
                            })
                        else:
                            # LLM이 해결 못한 경우 Perplexity 우선
                            resolved_profile[conflict.field] = conflict.perplexity_value
                            source_map[conflict.field] = "PERPLEXITY_DEFAULT"
                            unresolved_count += 1
                            resolution_details.append({
                                "field": conflict.field,
                                "type": "unresolved_default",
                                "value": conflict.perplexity_value,
                            })
            except Exception as e:
                logger.warning(f"LLM resolution failed: {e}")
                # LLM 실패 시 Perplexity 우선
                for conflict in structured_input.conflicts:
                    resolved_profile[conflict.field] = conflict.perplexity_value
                    source_map[conflict.field] = "PERPLEXITY_FALLBACK"
                    unresolved_count += 1
        else:
            # LLM 함수 없으면 Perplexity 우선
            for conflict in structured_input.conflicts:
                resolved_profile[conflict.field] = conflict.perplexity_value
                source_map[conflict.field] = "PERPLEXITY_DEFAULT"
                unresolved_count += 1
                resolution_details.append({
                    "field": conflict.field,
                    "type": "no_llm_default",
                    "value": conflict.perplexity_value,
                })

        return ConflictResolutionResult(
            resolved_profile=resolved_profile,
            source_map=source_map,
            rule_resolved_count=len(structured_input.rule_resolved),
            llm_resolved_count=llm_resolved_count,
            unresolved_count=unresolved_count,
            resolution_details=resolution_details,
        )


# Factory function
def get_conflict_resolver() -> StructuredConflictResolver:
    """StructuredConflictResolver 인스턴스 반환"""
    return StructuredConflictResolver()
