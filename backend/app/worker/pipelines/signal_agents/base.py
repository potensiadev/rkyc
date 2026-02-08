"""
Base Signal Agent - Abstract base class for all signal agents

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
Sprint 1 Integration: Enhanced prompts and strict validation (2026-02-08)

Features:
- Shared validation logic
- Common signature computation
- Agent-specific LLM tracking
- Forbidden word detection
- [2026-02-08] Buffett-style anti-hallucination guardrails
- [2026-02-08] Sprint 1: Enhanced validation with schemas_strict
"""

import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.usage_tracker import log_llm_usage
from app.worker.llm.exceptions import AllProvidersFailedError

# Sprint 1 Integration: Enhanced prompts and strict schemas
from app.worker.llm.prompts_enhanced import (
    check_forbidden_patterns,
    validate_signal_strict,
    ForbiddenCategory,
    ALL_FORBIDDEN_LITERALS,
)
from app.worker.llm.schemas_strict import (
    validate_signal_dict,
    SignalStrictSchema,
    RetrievalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Buffett-Style Anti-Hallucination Constants (2026-02-08)
# =============================================================================

# Warren Buffett Principle: "You are a librarian, not an analyst"
BUFFETT_LIBRARIAN_PERSONA = """
# 핵심 원칙: 도서관 사서 (Librarian)
당신은 분석가(Analyst)가 아닌 **도서관 사서(Librarian)**입니다.

## 사서의 역할
- 사실(Fact)을 **찾아서 복사**하는 것 = ✅ 허용
- 사실을 **해석하거나 분석**하는 것 = ❌ 금지
- 데이터에 **없는 숫자를 생성**하는 것 = ❌ 절대 금지

## 인용 신뢰도 (retrieval_confidence) - 필수 명시
모든 사실에는 다음 중 하나를 **반드시** 명시 (없으면 거부됨):
- `VERBATIM`: 원문 그대로 복사 (필수 우선)
- `PARAPHRASED`: 명확성을 위해 다듬음 (허용)
- `INFERRED`: 문맥에서 추론 (**confidence_reason 필수**, 없으면 거부됨)

## 금지 표현 (사용 시 즉시 거부)
다음 표현이 포함되면 시그널 전체가 거부됩니다:
- "약", "대략", "정도", "내외", "가량"
- "추정", "전망", "예상", "예측"
- "~로 보인다", "~할 것", "일반적으로"

## "모르겠다"는 정답이다
확실하지 않으면 시그널을 생성하지 마세요.
빈 결과 []가 잘못된 시그널보다 **훨씬** 낫습니다.
"""

# Hallucination Indicators - expressions that suggest LLM is guessing
HALLUCINATION_INDICATORS = [
    "추정됨", "추정된다", "추정된 바",
    "전망", "전망됨", "전망된다",
    "예상", "예상됨", "예상된다",
    "것으로 보인다", "것으로 보임",
    "것으로 추측", "추측됨",
    "일반적으로", "통상적으로",
    "약 ", "대략 ", "추산",
    "~할 것이다", "~일 것이다",
    "예측", "예측됨",
]

# Falsification Check - Warren Buffett's "Invert, Always Invert"
FALSIFICATION_KEYWORDS = [
    # 극단적 수치 (검증 필요)
    r"\d{2,3}%\s*(급등|폭등|급락|폭락|증가|감소)",
    r"(사상|역대)\s*(최고|최대|최저)",
    r"전년\s*대비\s*\d{2,}%",
    # 불확실한 시간 표현
    r"(곧|조만간|머지않아)",
    r"(예정|계획|검토)",
    # 익명 소스
    r"(관계자|소식통|업계에 따르면)",
]

# Source Credibility Scores (for evidence prioritization)
SOURCE_CREDIBILITY = {
    # Tier 1: 공식 소스 (100점)
    "dart.fss.or.kr": 100,  # 금융감독원 DART
    "kind.krx.co.kr": 100,  # 한국거래소 KIND
    "data.go.kr": 100,      # 공공데이터포털
    "law.go.kr": 100,       # 법제처
    "bok.or.kr": 95,        # 한국은행
    "kostat.go.kr": 95,     # 통계청
    # Tier 2: 언론 (70-80점)
    "reuters.com": 80,
    "bloomberg.com": 80,
    "yonhapnews.co.kr": 75,
    "yna.co.kr": 75,
    "hankyung.com": 70,
    "mk.co.kr": 70,
    "sedaily.com": 70,
    "edaily.co.kr": 65,
    "newsis.com": 65,
    # Tier 3: 기타 (50점 이하)
    "naver.com": 50,
    "daum.net": 50,
}

# =============================================================================
# Shared Validation Constants
# =============================================================================

# Legacy forbidden words (still used for basic validation)
FORBIDDEN_WORDS = [
    "반드시",
    "즉시",
    "확실히",
    "틀림없이",
    "무조건",
    "긴급",
    "예상됨",
    "전망됨",
    "~할 것이다",
    "~일 것이다",
    "것으로 보인다",
] + HALLUCINATION_INDICATORS  # P0: Add hallucination indicators

FORBIDDEN_PATTERNS = [re.compile(re.escape(word)) for word in FORBIDDEN_WORDS]

# Sprint 1 Integration: Use enhanced 50+ forbidden patterns
# ALL_FORBIDDEN_LITERALS is imported from prompts_enhanced.py (50+ patterns)
# check_forbidden_patterns() provides categorized detection

MAX_TITLE_LENGTH = 50
MAX_SUMMARY_LENGTH = 200  # prompts_enhanced uses 300, but keep 200 for stricter validation


class BaseSignalAgent(ABC):
    """
    Abstract base class for all signal extraction agents.

    Each agent specializes in one signal_type:
    - DirectSignalAgent: DIRECT (8 event_types)
    - IndustrySignalAgent: INDUSTRY (1 event_type)
    - EnvironmentSignalAgent: ENVIRONMENT (1 event_type)

    Shared features:
    - LLM service with usage tracking
    - Validation and enrichment logic
    - Signature computation for deduplication
    """

    # Subclasses must define these
    AGENT_NAME: str = "base"
    SIGNAL_TYPE: str = ""
    ALLOWED_EVENT_TYPES: set[str] = set()

    def __init__(self):
        self.llm = LLMService()
        self._trace_id: Optional[str] = None

    @abstractmethod
    def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """Return agent-specific system prompt."""
        pass

    @abstractmethod
    def get_user_prompt(self, context: dict) -> str:
        """Return agent-specific user prompt."""
        pass

    @abstractmethod
    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract relevant events for this agent from context."""
        pass

    def execute(self, context: dict) -> list[dict]:
        """
        Execute signal extraction for this agent's signal_type.

        Args:
            context: Unified context from ContextPipeline

        Returns:
            List of validated signal dicts
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")
        industry_name = context.get("industry_name", "")

        # Set trace ID for this execution
        self._trace_id = f"{self.AGENT_NAME}_{corp_id}_{int(time.time() * 1000)}"

        logger.info(
            f"[{self.AGENT_NAME}] Starting signal extraction for "
            f"corp_id={corp_id}, signal_type={self.SIGNAL_TYPE}"
        )

        # Get relevant events for this agent
        relevant_events = self.get_relevant_events(context)
        if not relevant_events and self.SIGNAL_TYPE != "DIRECT":
            # DIRECT can still extract signals from internal snapshot
            logger.info(
                f"[{self.AGENT_NAME}] No relevant events, skipping "
                f"(signal_type={self.SIGNAL_TYPE})"
            )
            return []

        # Build prompts
        system_prompt = self.get_system_prompt(corp_name, industry_name)
        user_prompt = self.get_user_prompt(context)

        start_time = time.time()

        try:
            # Call LLM with agent-specific tracking
            # P0-5 Fix: Pass trace_id for observability
            # Use sync version since execute() is not async
            signals = self.llm.extract_signals_sync(
                context=context,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_name=self.AGENT_NAME,
                trace_id=self._trace_id,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Validate and enrich signals
            validated_signals = []
            for signal in signals:
                # Force signal_type to this agent's type
                signal["signal_type"] = self.SIGNAL_TYPE

                enriched = self._enrich_signal(signal, context)
                if enriched:
                    validated_signals.append(enriched)

            logger.info(
                f"[{self.AGENT_NAME}] Completed: {len(validated_signals)}/{len(signals)} "
                f"signals validated (latency={latency_ms}ms)"
            )

            return validated_signals

        except AllProvidersFailedError as e:
            logger.error(
                f"[{self.AGENT_NAME}] All LLM providers failed for "
                f"corp_id={corp_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"[{self.AGENT_NAME}] Signal extraction failed for "
                f"corp_id={corp_id}: {e}"
            )
            raise

    def _enrich_signal(self, signal: dict, context: dict) -> Optional[dict]:
        """
        Validate and enrich signal with metadata.

        Validation rules:
        1. Required fields present
        2. Evidence exists (minimum 1)
        3. Valid enum values
        4. Event type in allowed set
        5. Forbidden words check
        6. Length constraints
        7. [P0] Hallucination detection - numbers must exist in input data
        8. [P0] Evidence URL validation - URLs must be from actual search results
        9. [P0] retrieval_confidence 검증 (E2E Test Fix 2026-02-08)

        Returns None if signal is invalid.
        """
        # 0. [P0 E2E Test Fix] retrieval_confidence 검증
        retrieval_confidence = signal.get("retrieval_confidence")
        if retrieval_confidence:
            if retrieval_confidence not in {"VERBATIM", "PARAPHRASED", "INFERRED"}:
                logger.warning(
                    f"[{self.AGENT_NAME}][REJECTED] Invalid retrieval_confidence: "
                    f"'{retrieval_confidence}'"
                )
                return None
            # INFERRED인 경우 confidence_reason 필수
            if retrieval_confidence == "INFERRED":
                if not signal.get("confidence_reason"):
                    logger.warning(
                        f"[{self.AGENT_NAME}][REJECTED] INFERRED without confidence_reason"
                    )
                    return None
        # 1. Required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary"
        ]
        for field in required_fields:
            if not signal.get(field):
                logger.warning(
                    f"[{self.AGENT_NAME}] Signal missing field: {field}"
                )
                return None

        # 2. Evidence check
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning(f"[{self.AGENT_NAME}] Signal has no evidence")
            return None

        # =====================================================================
        # P0: Anti-Hallucination Validation (2026-02-08)
        # =====================================================================

        # 7. Validate numbers in summary exist in input data
        hallucination_result = self._detect_number_hallucination(signal, context)
        if hallucination_result["is_hallucinated"]:
            logger.warning(
                f"[{self.AGENT_NAME}][HALLUCINATION] Signal rejected: "
                f"{hallucination_result['reason']} | "
                f"title='{signal.get('title', '')[:30]}' | "
                f"hallucinated_number={hallucination_result.get('number', 'N/A')}"
            )
            return None

        # 8. Validate evidence URLs are from actual search results
        evidence_validation = self._validate_evidence_sources(evidence, context)
        if not evidence_validation["valid"]:
            logger.warning(
                f"[{self.AGENT_NAME}][EVIDENCE] Signal rejected: "
                f"{evidence_validation['reason']} | "
                f"title='{signal.get('title', '')[:30]}'"
            )
            return None

        # 9. [P0] Entity Confusion Prevention - Verify corp_name in summary
        entity_validation = self._validate_entity_attribution(signal, context)
        if not entity_validation["valid"]:
            logger.warning(
                f"[{self.AGENT_NAME}][ENTITY CONFUSION] Signal rejected: "
                f"{entity_validation['reason']} | "
                f"title='{signal.get('title', '')[:30]}'"
            )
            return None

        # 3. Enum validation
        valid_directions = {"RISK", "OPPORTUNITY", "NEUTRAL"}
        valid_strengths = {"HIGH", "MED", "LOW"}

        if signal["impact_direction"] not in valid_directions:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid impact_direction: "
                f"{signal['impact_direction']}"
            )
            return None

        if signal["impact_strength"] not in valid_strengths:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid impact_strength: "
                f"{signal['impact_strength']}"
            )
            return None

        if signal["confidence"] not in valid_strengths:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid confidence: {signal['confidence']}"
            )
            return None

        # 4. Event type validation
        event_type = signal.get("event_type", "")
        if event_type not in self.ALLOWED_EVENT_TYPES:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid event_type '{event_type}' "
                f"for signal_type '{self.SIGNAL_TYPE}'. "
                f"Allowed: {self.ALLOWED_EVENT_TYPES}"
            )
            return None

        # 5. Forbidden words check (Enhanced with Sprint 1 patterns - 50+)
        summary = signal.get("summary", "")
        title = signal.get("title", "")

        # Use enhanced forbidden pattern checking from prompts_enhanced.py
        title_forbidden = check_forbidden_patterns(title)
        if title_forbidden:
            categories = list(set([f["category"] for f in title_forbidden]))
            logger.warning(
                f"[{self.AGENT_NAME}] Sprint1: Forbidden patterns in title: "
                f"categories={categories}, patterns={[f['pattern'] for f in title_forbidden[:3]]}"
            )
            return None

        summary_forbidden = check_forbidden_patterns(summary)
        if summary_forbidden:
            categories = list(set([f["category"] for f in summary_forbidden]))
            logger.warning(
                f"[{self.AGENT_NAME}] Sprint1: Forbidden patterns in summary: "
                f"categories={categories}, patterns={[f['pattern'] for f in summary_forbidden[:3]]}"
            )
            return None

        # Legacy pattern check (backup)
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(summary):
                logger.warning(
                    f"[{self.AGENT_NAME}] Forbidden word in summary: "
                    f"'{pattern.pattern}'"
                )
                return None
            if pattern.search(title):
                logger.warning(
                    f"[{self.AGENT_NAME}] Forbidden word in title: "
                    f"'{pattern.pattern}'"
                )
                return None

        # 6. Length constraints (truncate if needed)
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                f"[{self.AGENT_NAME}] Title too long, truncating"
            )
            signal["title"] = title[:MAX_TITLE_LENGTH]

        if len(summary) > MAX_SUMMARY_LENGTH:
            logger.warning(
                f"[{self.AGENT_NAME}] Summary too long, truncating"
            )
            signal["summary"] = summary[:MAX_SUMMARY_LENGTH]

        # Sprint 1 Integration: Additional strict validation using schemas_strict.py
        is_valid, errors = validate_signal_strict(signal, context)
        if not is_valid:
            logger.warning(
                f"[{self.AGENT_NAME}] Sprint1 strict validation failed: "
                f"errors={errors[:3]}"  # Log first 3 errors
            )
            # Mark for review instead of rejecting (soft validation)
            signal["needs_review"] = True
            signal["review_reason"] = f"Sprint1 validation: {', '.join(errors[:2])}"

        # Add metadata
        signal["corp_id"] = context.get("corp_id", "")
        signal["snapshot_version"] = context.get("snapshot_version", 0)
        signal["event_signature"] = self._compute_signature(signal)
        signal["extracted_by"] = self.AGENT_NAME

        return signal

    # =========================================================================
    # P0: Anti-Hallucination Methods (2026-02-08)
    # =========================================================================

    def _detect_number_hallucination(
        self, signal: dict, context: dict
    ) -> dict:
        """
        Detect if numbers in signal summary are hallucinated.

        P0 Fix: Numbers (especially percentages) must exist in:
        - Internal snapshot data
        - External search results
        - Document facts

        Returns:
            dict with keys:
            - is_hallucinated: bool
            - reason: str (if hallucinated)
            - number: str (the hallucinated number)
        """
        import json

        summary = signal.get("summary", "")
        title = signal.get("title", "")
        text_to_check = f"{title} {summary}"

        # Extract all percentages from signal text
        percentage_pattern = re.compile(r'[-+]?\d+(?:\.\d+)?%')
        percentages_in_signal = percentage_pattern.findall(text_to_check)

        if not percentages_in_signal:
            return {"is_hallucinated": False}

        # Build reference text from all input sources
        reference_texts = []

        # 1. Snapshot JSON
        snapshot = context.get("snapshot_json", {})
        if snapshot:
            reference_texts.append(json.dumps(snapshot, ensure_ascii=False))

        # 2. External search results
        for event_key in ["direct_events", "industry_events", "environment_events", "external_events"]:
            events = context.get(event_key, [])
            if events:
                reference_texts.append(json.dumps(events, ensure_ascii=False))

        # 3. Document facts
        doc_facts = context.get("document_facts", [])
        if doc_facts:
            reference_texts.append(json.dumps(doc_facts, ensure_ascii=False))

        # 4. Corp profile
        corp_profile = context.get("corp_profile", {})
        if corp_profile:
            reference_texts.append(json.dumps(corp_profile, ensure_ascii=False))

        combined_reference = " ".join(reference_texts)

        # Check each percentage
        for pct in percentages_in_signal:
            normalized = pct.replace("+", "")

            if normalized not in combined_reference:
                num_only = normalized.replace("%", "")
                if num_only not in combined_reference:
                    try:
                        num_value = float(num_only)
                        # Extreme values (>50% change) are highly suspicious
                        if abs(num_value) > 50:
                            return {
                                "is_hallucinated": True,
                                "reason": f"Extreme percentage {pct} not found in any input data",
                                "number": pct,
                            }
                        # Moderate values mark for review
                        if abs(num_value) > 30:
                            signal["needs_review"] = True
                            signal["review_reason"] = f"Percentage {pct} not directly in input"
                    except ValueError:
                        pass

        return {"is_hallucinated": False}

    def _validate_evidence_sources(
        self, evidence: list[dict], context: dict
    ) -> dict:
        """
        Validate that evidence URLs are from actual search results.

        P0 Fix: Prevent LLM from generating fake URLs.

        Returns:
            dict with keys:
            - valid: bool
            - reason: str (if invalid)
        """
        import json

        # Collect all valid URLs from external search results
        valid_urls = set()

        for event_key in ["direct_events", "industry_events", "environment_events", "external_events"]:
            events = context.get(event_key, [])
            for event in events:
                if isinstance(event, dict):
                    for url_field in ["url", "source_url", "ref_value", "link"]:
                        url = event.get(url_field, "")
                        if url and url.startswith("http"):
                            valid_urls.add(url)
                    citations = event.get("citations", [])
                    for citation in citations:
                        if isinstance(citation, str) and citation.startswith("http"):
                            valid_urls.add(citation)
                        elif isinstance(citation, dict):
                            valid_urls.add(citation.get("url", ""))

        # Check each evidence item
        for ev in evidence:
            ref_type = ev.get("ref_type", "")
            ref_value = ev.get("ref_value", "")

            if ref_type == "URL" and ref_value:
                if ref_value.startswith("http"):
                    if ref_value not in valid_urls:
                        domain_match = False
                        for valid_url in valid_urls:
                            if self._extract_domain(ref_value) == self._extract_domain(valid_url):
                                domain_match = True
                                break

                        if not domain_match and valid_urls:
                            return {
                                "valid": False,
                                "reason": f"Evidence URL not from search results: {ref_value[:50]}",
                            }

            elif ref_type == "SNAPSHOT_KEYPATH" and ref_value:
                snapshot = context.get("snapshot_json", {})
                if not self._validate_keypath(ref_value, snapshot):
                    return {
                        "valid": False,
                        "reason": f"Snapshot keypath does not exist: {ref_value}",
                    }

        return {"valid": True}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            if "://" in url:
                url = url.split("://")[1]
            if "/" in url:
                url = url.split("/")[0]
            return url.lower()
        except Exception:
            return ""

    def _validate_keypath(self, keypath: str, data: dict) -> bool:
        """Validate that a JSON Pointer keypath exists in data."""
        if not keypath or not data:
            return False

        parts = keypath.strip("/").split("/")

        current = data
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return False
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return False
                except ValueError:
                    return False
            else:
                return False

        return True

    def _validate_entity_attribution(self, signal: dict, context: dict) -> dict:
        """
        [P0] Validate that the signal is about the correct entity (corporation).

        Prevents Entity Confusion where LLM attributes information about
        company A to company B (e.g., attributing 엑시큐어하이트론's delisting
        to 엠케이전자).

        Returns:
            dict with keys:
            - valid: bool
            - reason: str (if invalid)
        """
        corp_name = context.get("corp_name", "")
        if not corp_name:
            return {"valid": True}

        summary = signal.get("summary", "")
        title = signal.get("title", "")

        # Extreme event keywords requiring strict entity verification
        EXTREME_EVENTS = [
            "상장폐지", "상장 폐지", "delisting",
            "부도", "파산", "bankruptcy",
            "법정관리", "회생", "청산",
            "횡령", "배임", "사기",
            "수사", "기소", "구속",
        ]

        is_extreme_event = any(
            kw in summary.lower() or kw in title.lower()
            for kw in EXTREME_EVENTS
        )

        if is_extreme_event:
            # For extreme events, corp_name MUST be in summary
            if corp_name not in summary and corp_name not in title:
                return {
                    "valid": False,
                    "reason": f"Extreme event does not mention target corp "
                              f"'{corp_name}'. Possible Entity Confusion.",
                }

            # Verify evidence snippets mention the corp
            evidence = signal.get("evidence", [])
            corp_in_evidence = any(
                corp_name in ev.get("snippet", "")
                for ev in evidence
            )

            if not corp_in_evidence and evidence:
                # Extract other company names to detect confusion
                other_companies = self._extract_company_names(summary)
                if other_companies and corp_name not in other_companies:
                    return {
                        "valid": False,
                        "reason": f"Evidence does not mention '{corp_name}'. "
                                  f"Found: {other_companies}. Entity Confusion.",
                    }

        return {"valid": True}

    def _extract_company_names(self, text: str) -> list[str]:
        """Extract potential company names from text."""
        patterns = [
            r'[가-힣]{2,10}(?:전자|건설|식품|기계|산업|홀딩스|그룹|증권|은행|보험|제약|바이오)',
            r'[가-힣]{2,10}(?:주식회사|㈜)',
        ]

        companies = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            companies.update(matches)

        return list(companies)

    def _compute_signature(self, signal: dict) -> str:
        """
        Compute event_signature for deduplication.

        Signature based on:
        - signal_type
        - event_type
        - evidence ref_values (sorted)
        """
        evidence_refs = sorted([
            ev.get("ref_value", "")
            for ev in signal.get("evidence", [])
        ])

        sig_string = "|".join([
            signal.get("signal_type", ""),
            signal.get("event_type", ""),
            ",".join(evidence_refs),
        ])

        return hashlib.sha256(sig_string.encode()).hexdigest()
