"""
Consensus Engine for Multi-Agent Profile Synthesis

PRD v1.2 결정 사항:
- Perplexity (검색) + Gemini (검증/보완) + Claude Opus (합성)
- Jaccard Similarity >= 0.7 기준 문자열 매칭
- discrepancy 필드 표시 및 Perplexity 값 우선

v1.3 변경사항:
- kiwipiepy 형태소 분석기 도입 (BUG-001 수정)
- 품사 기반 불용어 필터링
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

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
    consensus_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
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
    error_messages: list = field(default_factory=list)


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


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Jaccard Similarity 계산

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

    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union) if union else 0.0


def compare_values(value_a: Any, value_b: Any, threshold: float = 0.7) -> tuple[bool, float]:
    """
    두 값 비교

    Args:
        value_a: 첫 번째 값
        value_b: 두 번째 값
        threshold: 유사도 임계값 (기본 0.7)

    Returns:
        tuple[bool, float]: (일치 여부, 유사도 점수)
    """
    # 둘 다 None이면 일치
    if value_a is None and value_b is None:
        return True, 1.0

    # 하나만 None이면 불일치
    if value_a is None or value_b is None:
        return False, 0.0

    # 타입이 다르면 불일치
    if type(value_a) != type(value_b):
        return False, 0.0

    # 숫자 비교
    if isinstance(value_a, (int, float)):
        if value_a == 0 and value_b == 0:
            return True, 1.0
        if value_a == 0 or value_b == 0:
            return False, 0.0
        # 10% 이내 차이면 일치
        ratio = min(value_a, value_b) / max(value_a, value_b)
        return ratio >= 0.9, ratio

    # 리스트 비교
    if isinstance(value_a, list):
        if not value_a and not value_b:
            return True, 1.0
        if not value_a or not value_b:
            return False, 0.0
        # 리스트 요소의 Jaccard
        set_a = set(str(x).lower() for x in value_a)
        set_b = set(str(x).lower() for x in value_b)
        intersection = set_a & set_b
        union = set_a | set_b
        score = len(intersection) / len(union) if union else 0.0
        return score >= threshold, score

    # 딕셔너리 비교
    if isinstance(value_a, dict):
        if not value_a and not value_b:
            return True, 1.0
        if not value_a or not value_b:
            return False, 0.0
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
                if compare_values(value_a[k], value_b[k], threshold)[0]
            )
            value_score = value_matches / len(key_intersection)
        else:
            value_score = 0.0

        # 종합 점수
        score = (key_score + value_score) / 2
        return score >= threshold, score

    # 문자열 비교 (Jaccard Similarity)
    if isinstance(value_a, str):
        score = jaccard_similarity(value_a, value_b)
        return score >= threshold, score

    # 기타 타입: 정확히 일치 확인
    return value_a == value_b, 1.0 if value_a == value_b else 0.0


# ============================================================================
# Consensus Engine
# ============================================================================


class ConsensusEngine:
    """
    Multi-Agent Consensus Engine

    3개 소스의 프로필 정보를 합성:
    1. Perplexity (Primary Search)
    2. Gemini (Validation + Enrichment)
    3. Claude (Final Synthesis)

    합의 규칙:
    - Jaccard Similarity >= 0.7: 일치 → Perplexity 값 채택
    - 불일치: Perplexity 값 채택 + discrepancy: true
    - null: Gemini enriched 값 사용 (source: GEMINI_INFERRED)
    """

    SIMILARITY_THRESHOLD = 0.7

    # 필드별 비교 전략
    STRING_FIELDS = {"business_summary"}
    NUMERIC_FIELDS = {"revenue_krw", "export_ratio_pct", "employee_count"}
    LIST_FIELDS = {"key_materials", "key_customers", "overseas_operations", "key_suppliers"}
    DICT_FIELDS = {"country_exposure", "supply_chain", "regulatory_exposure"}

    def __init__(self):
        self.metadata = ConsensusMetadata()

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

        logger.info(
            f"[Consensus] Merged profile: "
            f"total={self.metadata.total_fields}, "
            f"matched={self.metadata.matched_fields}, "
            f"discrepancy={self.metadata.discrepancy_fields}, "
            f"enriched={self.metadata.enriched_fields}, "
            f"confidence={self.metadata.overall_confidence}"
        )

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

        # Gemini enriched 값 추출
        gemini_value = None
        gemini_confidence = "LOW"
        if gemini_enriched:
            if isinstance(gemini_enriched, dict) and "value" in gemini_enriched:
                gemini_value = gemini_enriched["value"]
                gemini_confidence = gemini_enriched.get("confidence", "LOW")
            else:
                gemini_value = gemini_enriched

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

        # Case 3: 둘 다 값이 있는 경우 - Jaccard Similarity 비교
        if gemini_value is not None:
            is_match, score = compare_values(
                perplexity_value,
                gemini_value,
                self.SIMILARITY_THRESHOLD,
            )

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
                    notes=f"Matched (Jaccard={score:.2f})",
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
                    notes=f"Discrepancy (Jaccard={score:.2f} < {self.SIMILARITY_THRESHOLD})",
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
