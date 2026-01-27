"""
Chain-of-Thought (CoT) Pipeline for rKYC

LLM 응답 품질 향상을 위한 단계별 추론 파이프라인.

P3-2: CoT vs Reflection 역할 구분
========================================

**CoT Pipeline**: 복잡한 추론이 필요한 '1회성' 작업
- 사용 시점: 시그널 추출, 인사이트 생성, 프로필 추출
- 방식: 단계별 추론 (UNDERSTAND → IDENTIFY → ANALYZE → EVIDENCE → SYNTHESIZE)
- 특징: 추론 과정의 투명성, 근거 체인 명시화
- 비용: LLM 1회 호출 (프롬프트에 단계 포함)

**Reflection Agent**: 품질 기준 미달 시 '반복' 개선
- 사용 시점: 품질 검증이 중요한 최종 출력물 (보고서, 요약문)
- 방식: 생성 → 비평 → 재생성 (최대 2회 반복)
- 특징: 자기 검증, 품질 점수 기반 개선
- 비용: LLM 2~3회 호출

**선택 가이드**:
- 추론 과정 추적 필요 → CoT
- 최종 품질 보장 필요 → Reflection
- 둘 다 필요 → CoT로 추론 후 Reflection으로 검증

Features:
- 단계별 추론 강제 (step-by-step reasoning)
- 중간 추론 과정 로깅
- Signal 추출 시 근거 체인 명시화
- 추론 단계별 품질 검증

Usage:
    from app.worker.llm.cot_pipeline import CoTPipeline, CoTStep

    pipeline = CoTPipeline()

    # Signal 추출 with CoT
    result = await pipeline.extract_signals_with_cot(context, corp_name)

    # 일반 CoT 호출
    result = pipeline.call_with_cot(prompt, steps=[...])
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional

from app.worker.tracing import get_logger, LogEvents
from app.worker.llm.service import LLMService
from app.worker.llm.model_router import TaskType, TaskComplexity

logger = get_logger("CoTPipeline")


class ReasoningStrategy(str, Enum):
    """
    P3-2: 추론 전략 선택 가이드

    작업 유형에 따라 적절한 추론 전략 선택
    """
    NONE = "none"                   # 단순 작업 (추출, 분류)
    COT_ONLY = "cot_only"           # 복잡한 추론 (시그널 추출)
    REFLECTION_ONLY = "reflection"  # 품질 보장 (최종 보고서)
    COT_THEN_REFLECTION = "cot_reflection"  # 둘 다 (고품질 분석)


# P3-2: 작업 유형별 추천 전략
TASK_REASONING_STRATEGY: dict[str, ReasoningStrategy] = {
    # CoT Only - 추론 과정 추적 필요
    "signal_extraction": ReasoningStrategy.COT_ONLY,
    "insight_generation": ReasoningStrategy.COT_ONLY,
    "profile_extraction": ReasoningStrategy.COT_ONLY,
    "risk_assessment": ReasoningStrategy.COT_ONLY,

    # Reflection Only - 최종 품질 보장
    "final_report": ReasoningStrategy.REFLECTION_ONLY,
    "executive_summary": ReasoningStrategy.REFLECTION_ONLY,
    "client_communication": ReasoningStrategy.REFLECTION_ONLY,

    # CoT + Reflection - 고품질 분석
    "comprehensive_analysis": ReasoningStrategy.COT_THEN_REFLECTION,
    "due_diligence": ReasoningStrategy.COT_THEN_REFLECTION,

    # None - 단순 작업
    "validation": ReasoningStrategy.NONE,
    "classification": ReasoningStrategy.NONE,
    "simple_extraction": ReasoningStrategy.NONE,
}


def get_reasoning_strategy(task_name: str) -> ReasoningStrategy:
    """
    P3-2: 작업 유형에 맞는 추론 전략 반환

    Args:
        task_name: 작업 이름 (예: "signal_extraction", "final_report")

    Returns:
        ReasoningStrategy: 추천 전략
    """
    return TASK_REASONING_STRATEGY.get(task_name.lower(), ReasoningStrategy.COT_ONLY)


class CoTStepType(str, Enum):
    """CoT 단계 유형"""
    UNDERSTAND = "understand"       # 문제/컨텍스트 이해
    IDENTIFY = "identify"           # 핵심 요소 식별
    ANALYZE = "analyze"             # 분석 및 추론
    EVALUATE = "evaluate"           # 평가 및 검증
    SYNTHESIZE = "synthesize"       # 종합 및 결론
    EVIDENCE = "evidence"           # 근거 명시


@dataclass
class CoTStep:
    """CoT 단계 정의"""
    step_type: CoTStepType
    instruction: str
    expected_output: str
    required: bool = True


@dataclass
class CoTStepResult:
    """CoT 단계 결과"""
    step_type: CoTStepType
    reasoning: str
    output: Any
    confidence: float
    duration_ms: int


@dataclass
class CoTResult:
    """CoT 파이프라인 최종 결과"""
    final_output: Any
    steps: list[CoTStepResult]
    total_duration_ms: int
    model_used: str
    reasoning_chain: str


# ============================================================================
# Predefined CoT Templates
# ============================================================================


SIGNAL_EXTRACTION_STEPS = [
    CoTStep(
        step_type=CoTStepType.UNDERSTAND,
        instruction="기업의 현재 상황과 컨텍스트를 파악합니다.",
        expected_output="기업 현황 요약 (업종, 규모, 주요 사업)",
    ),
    CoTStep(
        step_type=CoTStepType.IDENTIFY,
        instruction="리스크 또는 기회 시그널이 될 수 있는 핵심 변화/이벤트를 식별합니다.",
        expected_output="잠재 시그널 목록 (변화, 이벤트, 지표 변동)",
    ),
    CoTStep(
        step_type=CoTStepType.ANALYZE,
        instruction="각 잠재 시그널의 영향도와 신뢰도를 분석합니다.",
        expected_output="시그널별 영향 분석 (방향, 강도, 확률)",
    ),
    CoTStep(
        step_type=CoTStepType.EVIDENCE,
        instruction="각 시그널의 근거를 명시적으로 제시합니다.",
        expected_output="시그널별 근거 체인 (출처, 데이터 포인트, 추론 경로)",
    ),
    CoTStep(
        step_type=CoTStepType.EVALUATE,
        instruction="시그널의 중요도를 평가하고 우선순위를 정합니다.",
        expected_output="우선순위 정렬된 시그널 목록",
    ),
    CoTStep(
        step_type=CoTStepType.SYNTHESIZE,
        instruction="최종 시그널 목록을 구조화된 형식으로 출력합니다.",
        expected_output="JSON 형식의 시그널 배열",
    ),
]


INSIGHT_GENERATION_STEPS = [
    CoTStep(
        step_type=CoTStepType.UNDERSTAND,
        instruction="발견된 시그널들의 전체 맥락을 이해합니다.",
        expected_output="시그널 요약 및 분류",
    ),
    CoTStep(
        step_type=CoTStepType.ANALYZE,
        instruction="시그널 간의 관계와 종합적 영향을 분석합니다.",
        expected_output="상호작용 분석, 복합 리스크 식별",
    ),
    CoTStep(
        step_type=CoTStepType.EVALUATE,
        instruction="기업에 대한 종합적인 리스크/기회 수준을 평가합니다.",
        expected_output="종합 평가 점수 및 근거",
    ),
    CoTStep(
        step_type=CoTStepType.SYNTHESIZE,
        instruction="경영진 브리핑용 인사이트를 작성합니다.",
        expected_output="1-2문단의 핵심 인사이트",
    ),
]


PROFILE_EXTRACTION_STEPS = [
    CoTStep(
        step_type=CoTStepType.UNDERSTAND,
        instruction="검색 결과에서 기업 관련 정보를 파악합니다.",
        expected_output="정보 출처별 요약",
    ),
    CoTStep(
        step_type=CoTStepType.IDENTIFY,
        instruction="각 필드에 해당하는 정보를 식별합니다.",
        expected_output="필드별 후보 정보",
    ),
    CoTStep(
        step_type=CoTStepType.EVALUATE,
        instruction="정보의 신뢰도와 최신성을 평가합니다.",
        expected_output="필드별 신뢰도 점수",
    ),
    CoTStep(
        step_type=CoTStepType.SYNTHESIZE,
        instruction="최종 프로필을 구조화된 형식으로 출력합니다.",
        expected_output="JSON 형식의 프로필",
    ),
]


# ============================================================================
# CoT System Prompt Template
# ============================================================================


COT_SYSTEM_PROMPT = """당신은 금융기관의 기업 심사 전문가입니다.
주어진 작업을 수행할 때 반드시 단계별로 추론하고, 각 단계의 근거를 명시적으로 제시해야 합니다.

## 추론 규칙

1. **단계별 추론**: 각 단계를 명확히 구분하여 진행합니다.
2. **근거 명시**: 모든 판단에는 구체적인 근거를 제시합니다.
3. **불확실성 인정**: 확신이 없는 부분은 "~로 추정됨", "~가능성 있음"으로 표현합니다.
4. **출처 추적**: 정보의 출처를 항상 명시합니다.

## 출력 형식

각 단계는 다음 형식으로 출력합니다:

### [단계명]
**추론 과정**: (해당 단계에서 수행한 분석)
**결과**: (해당 단계의 출력)
**신뢰도**: HIGH/MED/LOW
---

마지막에 최종 결과를 JSON 형식으로 출력합니다."""


COT_USER_PROMPT_TEMPLATE = """## 작업
{task_description}

## 컨텍스트
{context}

## 수행할 단계
{steps_description}

## 요구사항
- 각 단계를 순서대로 수행하세요.
- 각 단계의 추론 과정을 명시적으로 작성하세요.
- 근거 없는 추측은 피하고, 불확실한 경우 명시하세요.
- 마지막에 최종 결과를 JSON으로 출력하세요.

시작하세요."""


# ============================================================================
# CoT Pipeline
# ============================================================================


class CoTPipeline:
    """
    Chain-of-Thought 추론 파이프라인

    LLM의 추론 품질을 높이기 위해 단계별 사고를 강제합니다.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self._llm = llm_service
        self._default_temperature = 0.2  # CoT에는 낮은 temperature

    @property
    def llm(self) -> LLMService:
        """LLM 서비스 인스턴스 (lazy initialization)"""
        if self._llm is None:
            self._llm = LLMService()
        return self._llm

    def _format_steps(self, steps: list[CoTStep]) -> str:
        """단계 목록을 프롬프트 형식으로 변환"""
        formatted = []
        for i, step in enumerate(steps, 1):
            formatted.append(
                f"{i}. **{step.step_type.value.upper()}**: {step.instruction}\n"
                f"   - 예상 출력: {step.expected_output}"
            )
        return "\n".join(formatted)

    def _parse_cot_response(self, response: str) -> tuple[list[CoTStepResult], Any]:
        """CoT 응답 파싱"""
        import re
        import time

        step_results = []

        # 단계별 결과 추출 (### [단계명] 형식)
        step_pattern = r'### \[?(\w+)\]?\s*\n(.*?)(?=### |\Z)'
        matches = re.findall(step_pattern, response, re.DOTALL)

        for step_name, content in matches:
            # 신뢰도 추출
            confidence_match = re.search(r'\*\*신뢰도\*\*:\s*(HIGH|MED|LOW)', content)
            confidence = 0.8 if confidence_match and confidence_match.group(1) == "HIGH" else \
                        0.5 if confidence_match and confidence_match.group(1) == "MED" else 0.3

            # 단계 유형 매핑
            step_type_map = {
                "understand": CoTStepType.UNDERSTAND,
                "identify": CoTStepType.IDENTIFY,
                "analyze": CoTStepType.ANALYZE,
                "evaluate": CoTStepType.EVALUATE,
                "synthesize": CoTStepType.SYNTHESIZE,
                "evidence": CoTStepType.EVIDENCE,
            }
            step_type = step_type_map.get(step_name.lower(), CoTStepType.ANALYZE)

            step_results.append(CoTStepResult(
                step_type=step_type,
                reasoning=content.strip(),
                output=None,  # Intermediate outputs
                confidence=confidence,
                duration_ms=0,  # Not tracked per step
            ))

        # 최종 JSON 추출
        final_output = None
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                final_output = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        if final_output is None:
            # JSON 블록이 없으면 마지막 {} 또는 [] 찾기
            json_patterns = [
                r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # Nested objects
                r'(\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])',  # Arrays
            ]
            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                if matches:
                    try:
                        final_output = json.loads(matches[-1])
                        break
                    except json.JSONDecodeError:
                        continue

        return step_results, final_output

    def call_with_cot(
        self,
        task_description: str,
        context: str,
        steps: list[CoTStep],
        response_schema: Optional[dict] = None,
    ) -> CoTResult:
        """
        CoT 방식으로 LLM 호출

        Args:
            task_description: 수행할 작업 설명
            context: 컨텍스트 정보
            steps: CoT 단계 목록
            response_schema: 예상 응답 스키마 (optional)

        Returns:
            CoTResult: CoT 추론 결과
        """
        import time
        start_time = time.time()

        # 프롬프트 구성
        steps_description = self._format_steps(steps)
        user_prompt = COT_USER_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context=context,
            steps_description=steps_description,
        )

        messages = [
            {"role": "system", "content": COT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(
            LogEvents.LLM_CALL_START,
            operation="cot_pipeline",
            step_count=len(steps),
        )

        # LLM 호출 (Complex task로 분류)
        response = self.llm.call_with_smart_routing(
            messages=messages,
            task_type=TaskType.MULTI_STEP_REASONING,
            temperature=self._default_temperature,
            max_tokens=8192,  # CoT는 긴 응답 필요
        )

        # 응답 파싱
        step_results, final_output = self._parse_cot_response(response)

        total_duration = int((time.time() - start_time) * 1000)

        # 추론 체인 구성
        reasoning_chain = "\n---\n".join([
            f"[{r.step_type.value}] {r.reasoning[:200]}..."
            for r in step_results
        ])

        logger.info(
            LogEvents.LLM_CALL_SUCCESS,
            operation="cot_pipeline",
            step_count=len(step_results),
            duration_ms=total_duration,
            model=self.llm.last_successful_model,
        )

        return CoTResult(
            final_output=final_output,
            steps=step_results,
            total_duration_ms=total_duration,
            model_used=self.llm.last_successful_model or "unknown",
            reasoning_chain=reasoning_chain,
        )

    def extract_signals_with_cot(
        self,
        context: dict,
        corp_name: str,
        industry_code: str,
    ) -> CoTResult:
        """
        CoT 방식으로 시그널 추출

        Args:
            context: 통합 컨텍스트 (snapshot, external, docs)
            corp_name: 기업명
            industry_code: 업종 코드

        Returns:
            CoTResult: 추출된 시그널 및 추론 과정
        """
        task_description = f"""
        기업 '{corp_name}' (업종: {industry_code})에 대한 리스크 및 기회 시그널을 추출합니다.

        시그널 유형:
        - DIRECT: 직접 리스크 (재무, 신용, 담보 등)
        - INDUSTRY: 산업 리스크 (업종 전반 영향)
        - ENVIRONMENT: 환경 리스크 (정책, 규제, 거시경제)

        각 시그널에는 반드시 구체적인 근거(evidence)를 명시해야 합니다.
        """

        context_str = json.dumps(context, ensure_ascii=False, indent=2)[:8000]  # Truncate if too long

        return self.call_with_cot(
            task_description=task_description,
            context=context_str,
            steps=SIGNAL_EXTRACTION_STEPS,
        )

    def generate_insight_with_cot(
        self,
        signals: list[dict],
        context: dict,
        corp_name: str,
    ) -> CoTResult:
        """
        CoT 방식으로 인사이트 생성

        Args:
            signals: 추출된 시그널 목록
            context: 통합 컨텍스트
            corp_name: 기업명

        Returns:
            CoTResult: 생성된 인사이트 및 추론 과정
        """
        task_description = f"""
        기업 '{corp_name}'에 대해 발견된 {len(signals)}개의 시그널을 종합하여
        경영진 브리핑용 인사이트를 작성합니다.

        인사이트 요구사항:
        - 핵심 리스크/기회 요약
        - 상호 연관된 시그널 식별
        - 권고 사항 (있는 경우)
        - 모니터링 필요 항목
        """

        context_data = {
            "signals": signals,
            "corp_context": {
                k: v for k, v in context.items()
                if k in ["corp_id", "corp_name", "industry_code", "snapshot_summary"]
            }
        }
        context_str = json.dumps(context_data, ensure_ascii=False, indent=2)

        return self.call_with_cot(
            task_description=task_description,
            context=context_str,
            steps=INSIGHT_GENERATION_STEPS,
        )

    def extract_profile_with_cot(
        self,
        search_results: str,
        corp_name: str,
        industry_code: str,
    ) -> CoTResult:
        """
        CoT 방식으로 기업 프로필 추출

        Args:
            search_results: 검색 결과 텍스트
            corp_name: 기업명
            industry_code: 업종 코드

        Returns:
            CoTResult: 추출된 프로필 및 추론 과정
        """
        task_description = f"""
        검색 결과에서 기업 '{corp_name}' (업종: {industry_code})의 프로필 정보를 추출합니다.

        추출 대상 필드:
        - 기본 정보: 대표이사, 설립연도, 본사 위치, 임직원 수
        - 사업 현황: 매출액, 사업 영역, 비즈니스 모델
        - 글로벌: 수출 비중, 국가별 노출도, 해외 법인
        - 공급망: 주요 공급사, 원자재, 고객사

        정보가 없는 필드는 null로 표시하고, 추정치는 "~로 추정됨"으로 명시합니다.
        """

        return self.call_with_cot(
            task_description=task_description,
            context=search_results[:10000],  # Truncate
            steps=PROFILE_EXTRACTION_STEPS,
        )


# Singleton instance
_cot_pipeline: Optional[CoTPipeline] = None


def get_cot_pipeline() -> CoTPipeline:
    """Get singleton CoT pipeline instance"""
    global _cot_pipeline
    if _cot_pipeline is None:
        _cot_pipeline = CoTPipeline()
    return _cot_pipeline


def reset_cot_pipeline() -> None:
    """Reset singleton instance (for testing)"""
    global _cot_pipeline
    _cot_pipeline = None
