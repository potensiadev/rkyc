"""
Signal Extraction Pipeline Stage
Stage 5: Extract risk signals using LLM

Production-grade validation with:
- Forbidden word detection
- Headline length validation
- Signal type / Event type mapping validation
- Confidence-based source verification

2026-01-22 해커톤 최적화:
- 페르소나 기반 판단 (Risk Manager, IB Manager)
- Chain-of-Thought 8단계
- Soft Guardrails
- Few-shot 예시 포함

Sprint 2 Multi-Agent Architecture (ADR-009):
- 3-Agent parallel execution (Direct, Industry, Environment)
- Orchestrator-based coordination
- Deduplication and cross-validation

Sprint 3/4 Enhancements (ADR-009):
- Cross-Validation with conflict detection
- Graceful Degradation with partial_failure tracking
- Provider Concurrency Limiting
- OrchestratorMetadata for monitoring

Sprint 5 Rule-Based Signal Generator (2026-02-06):
- Internal Snapshot에서 결정론적 시그널 생성
- OVERDUE_FLAG_ON, INTERNAL_RISK_GRADE_CHANGE 등 100% 감지 보장
- LLM Agent 호출 전에 Rule-Based 시그널 먼저 생성
- 중복 방지: event_signature 기반 deduplication
"""

import json
import hashlib
import logging
import re
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.prompts import (
    SIGNAL_EXTRACTION_SYSTEM,
    format_signal_extraction_prompt,
    # 해커톤 최적화: 향상된 프롬프트
    RISK_MANAGER_PERSONA,
    IB_MANAGER_PERSONA,
    SOFT_GUARDRAILS,
    CHAIN_OF_THOUGHT_GUIDE,
    DIRECT_FEW_SHOT_EXAMPLES,
    INDUSTRY_FEW_SHOT_EXAMPLES,
    ENVIRONMENT_FEW_SHOT_EXAMPLES,
)
from app.worker.llm.exceptions import AllProvidersFailedError

# Sprint 2/3/4: Multi-Agent imports
from app.worker.pipelines.signal_agents import (
    SignalAgentOrchestrator,
    get_signal_orchestrator,
)
from app.worker.pipelines.signal_agents.orchestrator import OrchestratorMetadata

# Sprint 5: Rule-Based Signal Generator
from app.worker.pipelines.signal_agents.rule_based_generator import (
    RuleBasedSignalGenerator,
    get_rule_based_generator,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Validation Rules
# =============================================================================

# Forbidden words in summary (auto-fail if present)
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
    "것으로 보인다",  # Too speculative
]

# Compiled regex patterns for forbidden words
FORBIDDEN_PATTERNS = [re.compile(re.escape(word)) for word in FORBIDDEN_WORDS]

# Signal Type to allowed Event Types mapping
SIGNAL_EVENT_MAPPING = {
    "DIRECT": {
        "KYC_REFRESH",
        "INTERNAL_RISK_GRADE_CHANGE",
        "OVERDUE_FLAG_ON",
        "LOAN_EXPOSURE_CHANGE",
        "COLLATERAL_CHANGE",
        "OWNERSHIP_CHANGE",
        "GOVERNANCE_CHANGE",
        "FINANCIAL_STATEMENT_UPDATE",
    },
    "INDUSTRY": {"INDUSTRY_SHOCK"},
    "ENVIRONMENT": {"POLICY_REGULATION_CHANGE"},
}

# Maximum lengths (PRD 14.7 rkyc_signal schema)
MAX_TITLE_LENGTH = 50
MAX_SUMMARY_LENGTH = 200


class SignalExtractionPipeline:
    """
    Stage 5: SIGNAL - Extract risk signals using LLM

    Uses Claude Opus 4.5 (with GPT-4o fallback) to analyze
    unified context and extract risk signals.

    2026-01-22 해커톤 최적화:
    - 페르소나 기반 판단 (Risk Manager, IB Manager)
    - Chain-of-Thought 8단계 추론
    - Soft Guardrails (자기 검증)
    - Signal Type별 Few-shot 예시

    Sprint 2 Multi-Agent Architecture (ADR-009):
    - 3-Agent parallel execution
    - use_multi_agent=True enables parallel mode
    - use_multi_agent=False uses legacy single-LLM mode
    """

    def __init__(self, use_multi_agent: bool = True):
        """
        Initialize pipeline.

        Args:
            use_multi_agent: True to use 3-Agent parallel mode (Sprint 2)
                           False to use legacy single-LLM mode
        """
        self.llm = LLMService()
        self.use_multi_agent = use_multi_agent

        # Sprint 5: Rule-Based Signal Generator (항상 사용)
        self._rule_based_generator = get_rule_based_generator()

        if use_multi_agent:
            self._orchestrator = get_signal_orchestrator()
            logger.info("SignalExtractionPipeline initialized with Multi-Agent mode + Rule-Based Generator")
        else:
            self._orchestrator = None
            logger.info("SignalExtractionPipeline initialized with Legacy mode + Rule-Based Generator")

    def _build_enhanced_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """
        해커톤 최적화: 향상된 시스템 프롬프트 조립

        포함 요소:
        - 페르소나 (Risk Manager, IB Manager)
        - Soft Guardrails
        - Chain-of-Thought 가이드
        - Signal Type별 Few-shot 예시
        """
        return f"""당신은 한국 금융기관의 기업심사 AI 분석가입니다.
주어진 기업 데이터와 외부 이벤트를 분석하여 리스크(RISK)와 기회(OPPORTUNITY) 시그널을 추출합니다.

# 전문가 페르소나 (두 관점에서 분석)
{RISK_MANAGER_PERSONA}

{IB_MANAGER_PERSONA}

# 판단 기준
- RISK 시그널: Risk Manager 관점 - "대출 시 원리금 상환에 문제가 생길 수 있는가?"
- OPPORTUNITY 시그널: IB Manager 관점 - "투자 시 성장 기회가 있는가?"
- RISK는 Recall 우선 (놓치지 않기), OPPORTUNITY는 Precision 우선 (확실한 것만)

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

# Signal Type별 규칙 및 예시

## DIRECT (기업 직접 영향)
- 해당 기업에 직접적으로 영향을 미치는 변화
- event_type: KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON, LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE, OWNERSHIP_CHANGE, GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE
- **규칙**: 기업명 필수, 내부 데이터 HIGH confidence, 정량 정보 필수

{DIRECT_FEW_SHOT_EXAMPLES}

## INDUSTRY (산업 영향)
- 해당 산업 전체에 영향을 미치는 변화
- event_type: INDUSTRY_SHOCK만 사용
- **규칙**: summary 마지막에 "{corp_name}에 미치는 영향" 1문장 필수

{INDUSTRY_FEW_SHOT_EXAMPLES}

## ENVIRONMENT (거시환경 영향)
- 정책, 규제, 거시경제 변화
- event_type: POLICY_REGULATION_CHANGE만 사용
- **규칙**: summary에 "{corp_name}/{industry_name}에 미치는 영향 가능성" 1문장 필수

{ENVIRONMENT_FEW_SHOT_EXAMPLES}

# 출력 형식 (JSON)
```json
{{
  "signals": [
    {{
      "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",
      "event_type": "<10종 중 하나>",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "시그널 제목 (50자 이내)",
      "summary": "상세 설명 (200자 이내, 금지표현 미사용)",
      "evidence": [
        {{
          "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
          "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
          "ref_value": "/credit/loan_summary/overdue_flag 또는 URL",
          "snippet": "관련 텍스트 (100자 이내)"
        }}
      ]
    }}
  ]
}}
```

# 분석 지침
1. **Chain-of-Thought 8단계** 따라 분석 수행
2. **내부 스냅샷 먼저**: 연체, 등급, 담보 등 변화 확인 → HIGH confidence
3. **외부 이벤트 연결**: 기업/산업과의 연관성 분석
4. **중복 금지**: 동일 사안 여러 시그널 생성 금지
5. **근거 필수**: evidence 없는 시그널 생성 금지
6. **RISK는 놓치지 말기**, OPPORTUNITY는 확실한 것만
"""

    def execute(self, context: dict) -> list[dict]:
        """
        Execute signal extraction stage.

        Args:
            context: Unified context from ContextPipeline

        Returns:
            list of signal dicts with structure:
                - signal_type: DIRECT|INDUSTRY|ENVIRONMENT
                - event_type: One of 10 event types
                - impact_direction: RISK|OPPORTUNITY|NEUTRAL
                - impact_strength: HIGH|MED|LOW
                - confidence: HIGH|MED|LOW
                - title: Short title
                - summary: Detailed summary
                - evidence: List of evidence dicts
                - corp_id: Corporation ID
                - snapshot_version: Snapshot version
                - event_signature: SHA256 hash for deduplication
        """
        corp_id = context.get("corp_id", "")

        # Sprint 2: Use Multi-Agent mode if enabled
        if self.use_multi_agent and self._orchestrator:
            logger.info(
                f"SIGNAL stage starting for corp_id={corp_id} "
                f"[Multi-Agent Mode: 3-Agent Parallel]"
            )
            return self._execute_multi_agent(context)
        else:
            logger.info(
                f"SIGNAL stage starting for corp_id={corp_id} "
                f"[Legacy Mode: Single LLM]"
            )
            return self._execute_legacy(context)

    def _execute_multi_agent(self, context: dict) -> list[dict]:
        """
        Execute signal extraction using 3-Agent parallel architecture.

        Sprint 2 (ADR-009):
        - DirectSignalAgent: 8 DIRECT event_types
        - IndustrySignalAgent: INDUSTRY_SHOCK
        - EnvironmentSignalAgent: POLICY_REGULATION_CHANGE

        Sprint 3/4 (ADR-009):
        - Cross-Validation with conflict detection
        - Graceful Degradation with partial_failure tracking
        - OrchestratorMetadata for monitoring

        Sprint 5 (2026-02-06):
        - Rule-Based Signal Generator 먼저 실행
        - Internal Snapshot에서 결정론적 시그널 추출 (OVERDUE, GRADE_CHANGE 등)
        - LLM Agent 결과와 병합 (중복 제거)

        All agents run in parallel, results are merged and deduplicated.
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")

        logger.info(
            f"Multi-Agent extraction: "
            f"direct_events={len(context.get('direct_events', []))}, "
            f"industry_events={len(context.get('industry_events', []))}, "
            f"environment_events={len(context.get('environment_events', []))}"
        )

        all_signals = []

        # =====================================================================
        # Sprint 5: Rule-Based Signal Generator 먼저 실행
        # =====================================================================
        try:
            rule_based_signals = self._rule_based_generator.generate(
                corp_id=corp_id,
                corp_name=corp_name,
                snapshot=context.get("snapshot_json", {}),
                prev_snapshot=context.get("previous_snapshot_json"),  # 이전 스냅샷 (있으면)
            )

            if rule_based_signals:
                logger.info(
                    f"[Rule-Based Generator] Generated {len(rule_based_signals)} "
                    f"deterministic signals for {corp_name}"
                )
                # Enrich with context metadata
                for signal in rule_based_signals:
                    signal["corp_id"] = corp_id
                    signal["snapshot_version"] = context.get("snapshot_version", 0)
                all_signals.extend(rule_based_signals)

        except Exception as e:
            logger.warning(f"Rule-Based Generator failed for {corp_id}: {e}")
            # Continue with LLM agents even if rule-based fails

        # =====================================================================
        # LLM-based Multi-Agent Extraction
        # =====================================================================
        try:
            # Execute all 3 agents via orchestrator
            # Sprint 3/4: Returns tuple (signals, metadata)
            llm_signals, metadata = self._orchestrator.execute(context)

            # Log orchestrator metadata for monitoring
            self._log_orchestrator_metadata(corp_id, metadata)

            # Check for partial failure
            if metadata.partial_failure:
                logger.warning(
                    f"SIGNAL stage completed with partial failure: "
                    f"failed_agents={metadata.failed_agents}"
                )

            # =====================================================================
            # Sprint 5: Merge Rule-Based + LLM signals with deduplication
            # =====================================================================
            existing_signatures = {s.get("event_signature") for s in all_signals}
            for signal in llm_signals:
                sig = signal.get("event_signature", "")
                if sig and sig not in existing_signatures:
                    all_signals.append(signal)
                    existing_signatures.add(sig)
                elif not sig:
                    # No signature, add anyway (shouldn't happen)
                    all_signals.append(signal)

            logger.info(
                f"SIGNAL stage completed [Multi-Agent + Rule-Based]: "
                f"rule_based={len(rule_based_signals) if 'rule_based_signals' in dir() else 0}, "
                f"llm={len(llm_signals)}, "
                f"total={len(all_signals)}, "
                f"conflicts={metadata.conflicts_detected}, "
                f"needs_review={metadata.needs_review_count}"
            )
            return all_signals

        except Exception as e:
            logger.error(
                f"Multi-Agent extraction failed for corp_id={corp_id}: {e}"
            )
            # If we have rule-based signals, return them
            if all_signals:
                logger.warning(
                    f"LLM agents failed, returning {len(all_signals)} rule-based signals only"
                )
                return all_signals
            # Fallback to legacy mode on complete failure
            logger.warning("Falling back to Legacy mode...")
            return self._execute_legacy(context)

    def _log_orchestrator_metadata(
        self,
        corp_id: str,
        metadata: OrchestratorMetadata,
    ) -> None:
        """
        Log orchestrator metadata for monitoring and debugging.

        Sprint 3/4: Structured logging of agent performance metrics.
        """
        logger.info(
            f"[OrchestratorMetrics] corp_id={corp_id} "
            f"total_raw={metadata.total_raw_signals} "
            f"deduplicated={metadata.deduplicated_count} "
            f"validated={metadata.validated_count} "
            f"conflicts={metadata.conflicts_detected} "
            f"needs_review={metadata.needs_review_count} "
            f"processing_ms={metadata.processing_time_ms} "
            f"partial_failure={metadata.partial_failure}"
        )

        # Log individual agent results
        for agent_name, result in metadata.agent_results.items():
            if isinstance(result, dict):
                logger.info(
                    f"[AgentMetrics] agent={agent_name} "
                    f"status={result.get('status', 'unknown')} "
                    f"signals={result.get('signal_count', 0)} "
                    f"time_ms={result.get('execution_time_ms', 0)} "
                    f"retries={result.get('retry_count', 0)}"
                )

        # Log failed agents with error messages
        if metadata.failed_agents:
            for agent_name in metadata.failed_agents:
                agent_result = metadata.agent_results.get(agent_name, {})
                error_msg = agent_result.get('error_message', 'unknown error')
                logger.warning(
                    f"[AgentFailure] agent={agent_name} error={error_msg}"
                )

    def _execute_legacy(self, context: dict) -> list[dict]:
        """
        Execute signal extraction using legacy single-LLM approach.

        This is the original implementation kept for:
        - Backward compatibility
        - Fallback when multi-agent fails
        - Comparison testing

        Sprint 5: Rule-Based Generator도 여기서 실행
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")
        industry_name = context.get("industry_name", "")

        all_signals = []

        # =====================================================================
        # Sprint 5: Rule-Based Signal Generator 먼저 실행
        # =====================================================================
        try:
            rule_based_signals = self._rule_based_generator.generate(
                corp_id=corp_id,
                corp_name=corp_name,
                snapshot=context.get("snapshot_json", {}),
                prev_snapshot=context.get("previous_snapshot_json"),
            )

            if rule_based_signals:
                logger.info(
                    f"[Rule-Based Generator] Generated {len(rule_based_signals)} "
                    f"deterministic signals for {corp_name}"
                )
                for signal in rule_based_signals:
                    signal["corp_id"] = corp_id
                    signal["snapshot_version"] = context.get("snapshot_version", 0)
                all_signals.extend(rule_based_signals)

        except Exception as e:
            logger.warning(f"Rule-Based Generator failed for {corp_id}: {e}")

        # 해커톤 최적화: 향상된 시스템 프롬프트 사용
        enhanced_system_prompt = self._build_enhanced_system_prompt(
            corp_name=corp_name,
            industry_name=industry_name,
        )

        # Format prompt with context data (3-track events + DART info)
        user_prompt = format_signal_extraction_prompt(
            corp_name=corp_name,
            corp_reg_no=context.get("corp_reg_no", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=industry_name,
            snapshot_json=json.dumps(
                context.get("snapshot_json", {}),
                ensure_ascii=False,
                indent=2,
            ),
            external_events=json.dumps(
                context.get("external_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            # New 3-track events
            direct_events=json.dumps(
                context.get("direct_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            industry_events=json.dumps(
                context.get("industry_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            environment_events=json.dumps(
                context.get("environment_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            # DART 공시 기반 정보 (100% Fact 데이터)
            dart_corp_code=context.get("dart_corp_code"),
            established_date=context.get("established_date"),
            headquarters=context.get("headquarters"),
            jurir_no=context.get("jurir_no"),
            corp_name_eng=context.get("corp_name_eng"),
            acc_mt=context.get("acc_mt"),
        )

        logger.info(
            f"SIGNAL extraction [Legacy mode]: "
            f"direct={len(context.get('direct_events', []))}, "
            f"industry={len(context.get('industry_events', []))}, "
            f"environment={len(context.get('environment_events', []))}"
        )

        try:
            # Call LLM for signal extraction with enhanced prompt
            # P0-FIX: Use sync version since execute() is not async
            llm_signals = self.llm.extract_signals_sync(
                context=context,
                system_prompt=enhanced_system_prompt,
                user_prompt=user_prompt,
            )

            # Enrich LLM signals with metadata
            existing_signatures = {s.get("event_signature") for s in all_signals}

            for signal in llm_signals:
                enriched = self._enrich_signal(signal, context)
                if enriched:
                    # Sprint 5: Deduplication - skip if already exists from Rule-Based
                    sig = enriched.get("event_signature", "")
                    if sig and sig not in existing_signatures:
                        all_signals.append(enriched)
                        existing_signatures.add(sig)
                    elif not sig:
                        all_signals.append(enriched)

            rule_based_count = len([s for s in all_signals if "RULE_BASED" in s.get("event_signature", "")])
            llm_count = len(all_signals) - rule_based_count

            logger.info(
                f"SIGNAL stage completed [Legacy + Rule-Based]: "
                f"rule_based={rule_based_count}, llm={llm_count}, total={len(all_signals)}"
            )
            return all_signals

        except AllProvidersFailedError as e:
            logger.error(f"All LLM providers failed for corp_id={corp_id}: {e}")
            # Sprint 5: Return rule-based signals even if LLM fails
            if all_signals:
                logger.warning(
                    f"LLM failed, returning {len(all_signals)} rule-based signals only"
                )
                return all_signals
            return []

        except Exception as e:
            logger.error(f"Signal extraction failed for corp_id={corp_id}: {e}")
            # Sprint 5: Return rule-based signals on error
            if all_signals:
                logger.warning(
                    f"LLM error, returning {len(all_signals)} rule-based signals only"
                )
                return all_signals
            raise

    def _enrich_signal(self, signal: dict, context: dict) -> Optional[dict]:
        """
        Enrich signal with metadata and validate.

        Validation rules:
        1. Required fields present
        2. Evidence exists (minimum 1)
        3. Valid enum values
        4. Signal type / Event type mapping
        5. Forbidden words check
        6. Length constraints (headline, title, summary)
        7. [P0] Hallucination detection - numbers must exist in input data
        8. [P0] Evidence URL validation - URLs must be from actual search results

        Returns None if signal is invalid.
        """
        # 1. Validate required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary"
        ]
        for field in required_fields:
            if not signal.get(field):
                logger.warning(f"Signal missing required field: {field}")
                return None

        # 2. Validate evidence
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning("Signal has no evidence, skipping")
            return None

        # =====================================================================
        # P0: Anti-Hallucination Validation (2026-02-08)
        # =====================================================================

        # 7. Validate numbers in summary exist in input data
        hallucination_result = self._detect_number_hallucination(signal, context)
        if hallucination_result["is_hallucinated"]:
            logger.warning(
                f"[HALLUCINATION DETECTED] Signal rejected: {hallucination_result['reason']} "
                f"| title='{signal.get('title', '')[:30]}' "
                f"| hallucinated_number={hallucination_result.get('number', 'N/A')}"
            )
            return None

        # 8. Validate evidence URLs are from actual search results
        evidence_validation = self._validate_evidence_sources(evidence, context)
        if not evidence_validation["valid"]:
            logger.warning(
                f"[EVIDENCE INVALID] Signal rejected: {evidence_validation['reason']} "
                f"| title='{signal.get('title', '')[:30]}'"
            )
            return None

        # 3. Validate enums
        valid_directions = {"RISK", "OPPORTUNITY", "NEUTRAL"}
        valid_strengths = {"HIGH", "MED", "LOW"}

        signal_type = signal["signal_type"]
        event_type = signal["event_type"]

        if signal_type not in SIGNAL_EVENT_MAPPING:
            logger.warning(f"Invalid signal_type: {signal_type}")
            return None

        if signal["impact_direction"] not in valid_directions:
            logger.warning(f"Invalid impact_direction: {signal['impact_direction']}")
            return None
        if signal["impact_strength"] not in valid_strengths:
            logger.warning(f"Invalid impact_strength: {signal['impact_strength']}")
            return None
        if signal["confidence"] not in valid_strengths:
            logger.warning(f"Invalid confidence: {signal['confidence']}")
            return None

        # 4. Validate signal_type / event_type mapping
        allowed_events = SIGNAL_EVENT_MAPPING[signal_type]
        if event_type not in allowed_events:
            logger.warning(
                f"Invalid event_type '{event_type}' for signal_type '{signal_type}'. "
                f"Allowed: {allowed_events}"
            )
            return None

        # 5. Check forbidden words in summary
        summary = signal.get("summary", "")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(summary):
                logger.warning(
                    f"Signal summary contains forbidden word, skipping: "
                    f"'{pattern.pattern}' in '{summary[:50]}...'"
                )
                return None

        # Also check title for forbidden words
        title = signal.get("title", "")
        if title:
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(title):
                    logger.warning(
                        f"Signal title contains forbidden word: '{pattern.pattern}'"
                    )
                    return None

        # 6. Validate length constraints
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                f"Title too long ({len(title)} > {MAX_TITLE_LENGTH}), truncating"
            )
            signal["title"] = title[:MAX_TITLE_LENGTH]

        if len(summary) > MAX_SUMMARY_LENGTH:
            logger.warning(
                f"Summary too long ({len(summary)} > {MAX_SUMMARY_LENGTH}), truncating"
            )
            signal["summary"] = summary[:MAX_SUMMARY_LENGTH]

        # Add metadata (PRD 14.7 rkyc_signal schema)
        signal["corp_id"] = context.get("corp_id", "")
        signal["snapshot_version"] = context.get("snapshot_version", 0)
        signal["event_signature"] = self._compute_signature(signal)

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
        - External search results (direct_events, industry_events, environment_events)
        - Document facts

        Returns:
            dict with keys:
            - is_hallucinated: bool
            - reason: str (if hallucinated)
            - number: str (the hallucinated number)
        """
        summary = signal.get("summary", "")
        title = signal.get("title", "")
        text_to_check = f"{title} {summary}"

        # Extract all percentages from signal text
        # Pattern: number followed by % (e.g., 88%, 30.4%, -20%)
        percentage_pattern = re.compile(r'[-+]?\d+(?:\.\d+)?%')
        percentages_in_signal = percentage_pattern.findall(text_to_check)

        if not percentages_in_signal:
            # No percentages to validate
            return {"is_hallucinated": False}

        # Build reference text from all input sources
        reference_texts = []

        # 1. Snapshot JSON (stringify for searching)
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

        # 4. Corp profile (if available)
        corp_profile = context.get("corp_profile", {})
        if corp_profile:
            reference_texts.append(json.dumps(corp_profile, ensure_ascii=False))

        combined_reference = " ".join(reference_texts)

        # Check each percentage
        for pct in percentages_in_signal:
            # Normalize: remove + sign, handle negative
            normalized = pct.replace("+", "")

            # Check if this percentage exists in reference
            if normalized not in combined_reference:
                # Also check without % sign (e.g., "88" instead of "88%")
                num_only = normalized.replace("%", "")
                if num_only not in combined_reference:
                    # This percentage is likely hallucinated
                    # Additional check: is it an extreme value?
                    try:
                        num_value = float(num_only)
                        # Extreme values (>50% change) are highly suspicious
                        if abs(num_value) > 50:
                            return {
                                "is_hallucinated": True,
                                "reason": f"Extreme percentage {pct} not found in any input data",
                                "number": pct,
                            }
                        # For moderate values, mark as needs_review but don't reject
                        # (could be calculated from input data)
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
        # Collect all valid URLs from external search results
        valid_urls = set()

        for event_key in ["direct_events", "industry_events", "environment_events", "external_events"]:
            events = context.get(event_key, [])
            for event in events:
                if isinstance(event, dict):
                    # URL could be in different fields
                    for url_field in ["url", "source_url", "ref_value", "link"]:
                        url = event.get(url_field, "")
                        if url and url.startswith("http"):
                            valid_urls.add(url)
                    # Also check citations array
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

            # Only validate URL type evidence
            if ref_type == "URL" and ref_value:
                if ref_value.startswith("http"):
                    # Check if this URL is from our search results
                    if ref_value not in valid_urls:
                        # Check partial match (domain level)
                        domain_match = False
                        for valid_url in valid_urls:
                            # Extract domain from both URLs
                            if self._extract_domain(ref_value) == self._extract_domain(valid_url):
                                domain_match = True
                                break

                        if not domain_match and valid_urls:
                            # URL is completely fabricated - reject
                            return {
                                "valid": False,
                                "reason": f"Evidence URL not from search results: {ref_value[:50]}",
                            }

            # Validate SNAPSHOT_KEYPATH references
            elif ref_type == "SNAPSHOT_KEYPATH" and ref_value:
                # Check if the keypath actually exists in snapshot
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
            # Simple extraction: get the part between // and next /
            if "://" in url:
                url = url.split("://")[1]
            if "/" in url:
                url = url.split("/")[0]
            return url.lower()
        except Exception:
            return ""

    def _validate_keypath(self, keypath: str, data: dict) -> bool:
        """
        Validate that a JSON Pointer keypath exists in data.

        Args:
            keypath: JSON Pointer format (e.g., "/credit/loan_summary/overdue_flag")
            data: The snapshot JSON data

        Returns:
            True if keypath exists, False otherwise
        """
        if not keypath or not data:
            return False

        # Remove leading slash and split
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

    def _compute_signature(self, signal: dict) -> str:
        """
        Compute event_signature for deduplication.

        Signature is based on:
        - signal_type
        - event_type
        - evidence ref_values (sorted)
        """
        # Get sorted evidence references
        evidence_refs = sorted([
            ev.get("ref_value", "")
            for ev in signal.get("evidence", [])
        ])

        # Create signature string
        sig_string = "|".join([
            signal.get("signal_type", ""),
            signal.get("event_type", ""),
            ",".join(evidence_refs),
        ])

        # Compute SHA256 hash
        return hashlib.sha256(sig_string.encode()).hexdigest()
