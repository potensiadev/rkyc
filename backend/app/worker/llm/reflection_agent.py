"""
Reflection Agent for rKYC

LLM 자기 검증 패턴 구현:
- 초기 응답 생성 후 자기 비평
- 품질 점수 기반 재생성 결정
- 최대 2회 iteration

P3-2: CoT vs Reflection 역할 구분
========================================

**Reflection Agent**: 품질 기준 미달 시 '반복' 개선
- 사용 시점: 품질 검증이 중요한 최종 출력물 (보고서, 요약문)
- 방식: 생성 → 비평 → 재생성 (최대 2회 반복)
- 특징: 자기 검증, 품질 점수 기반 개선
- 비용: LLM 2~3회 호출

**CoT Pipeline**: 복잡한 추론이 필요한 '1회성' 작업
- 사용 시점: 시그널 추출, 인사이트 생성, 프로필 추출
- 방식: 단계별 추론 (UNDERSTAND → IDENTIFY → ANALYZE → EVIDENCE)
- 특징: 추론 과정의 투명성, 근거 체인 명시화
- 비용: LLM 1회 호출

**선택 가이드**:
| 상황 | 선택 |
|------|------|
| 추론 과정 추적 필요 | CoT |
| 최종 품질 보장 필요 | Reflection |
| 고품질 분석 보고서 | CoT + Reflection 조합 |
| 단순 추출/분류 | 둘 다 불필요 |

Usage:
    from app.worker.llm.reflection_agent import ReflectionAgent

    agent = ReflectionAgent()

    # 자동 품질 개선
    result = agent.generate_with_reflection(
        task="시그널 추출",
        prompt="...",
        quality_threshold=0.7,
    )
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional, Callable

from app.worker.tracing import get_logger, LogEvents
from app.worker.llm.service import LLMService
from app.worker.llm.model_router import TaskType

logger = get_logger("ReflectionAgent")


@dataclass
class CritiqueResult:
    """비평 결과"""
    quality_score: float  # 0.0 ~ 1.0
    issues: list[str]
    suggestions: list[str]
    should_regenerate: bool
    critique_reasoning: str


@dataclass
class ReflectionIteration:
    """반복 단계 결과"""
    iteration: int
    response: Any
    critique: CritiqueResult
    duration_ms: int


@dataclass
class ReflectionResult:
    """Reflection Agent 최종 결과"""
    final_response: Any
    iterations: list[ReflectionIteration]
    total_iterations: int
    final_quality_score: float
    improved: bool
    model_used: str


# ============================================================================
# Critique Prompts
# ============================================================================


CRITIQUE_SYSTEM_PROMPT = """당신은 금융 분석 품질 검증 전문가입니다.
주어진 응답을 엄격하게 평가하고 개선점을 제시해야 합니다.

## 평가 기준

1. **완전성 (Completeness)**: 요청된 모든 항목이 포함되었는가?
2. **정확성 (Accuracy)**: 논리적 오류나 모순이 없는가?
3. **근거 (Evidence)**: 모든 주장에 구체적 근거가 있는가?
4. **명확성 (Clarity)**: 표현이 명확하고 이해하기 쉬운가?
5. **일관성 (Consistency)**: 응답 내 정보가 서로 일관적인가?

## 출력 형식 (반드시 JSON)

```json
{
    "quality_score": 0.0-1.0,
    "issues": ["이슈1", "이슈2"],
    "suggestions": ["개선점1", "개선점2"],
    "should_regenerate": true/false,
    "reasoning": "평가 근거 설명"
}
```

**주의**: should_regenerate는 quality_score < 0.7이고 수정 가능한 이슈가 있을 때만 true입니다."""


CRITIQUE_USER_PROMPT_TEMPLATE = """## 원래 작업
{original_task}

## 평가할 응답
{response}

## 평가 요청
위 응답을 평가 기준에 따라 엄격하게 검토하고, JSON 형식으로 결과를 출력하세요.
품질 점수는 0.0 ~ 1.0 사이의 값입니다."""


REGENERATE_SYSTEM_PROMPT = """당신은 금융 분석 전문가입니다.
이전 응답의 문제점을 개선하여 더 나은 응답을 생성해야 합니다.

## 핵심 원칙

1. 지적된 이슈를 반드시 해결합니다.
2. 기존 응답의 좋은 부분은 유지합니다.
3. 추가 근거나 설명이 필요한 부분을 보완합니다.
4. 원래 요청의 형식을 준수합니다."""


REGENERATE_USER_PROMPT_TEMPLATE = """## 원래 작업
{original_task}

## 이전 응답
{previous_response}

## 비평 피드백
**품질 점수**: {quality_score}
**이슈**: {issues}
**개선 제안**: {suggestions}

## 요청
위 피드백을 반영하여 개선된 응답을 생성하세요.
원래 요청의 형식을 반드시 준수하세요."""


# ============================================================================
# Reflection Agent
# ============================================================================


class ReflectionAgent:
    """
    Reflection Agent - 자기 검증 및 개선

    LLM 응답을 자동으로 평가하고 품질이 낮으면 재생성합니다.
    """

    MAX_ITERATIONS = 2
    DEFAULT_QUALITY_THRESHOLD = 0.7

    def __init__(self, llm_service: Optional[LLMService] = None):
        self._llm = llm_service

    @property
    def llm(self) -> LLMService:
        """LLM 서비스 인스턴스"""
        if self._llm is None:
            self._llm = LLMService()
        return self._llm

    def critique(
        self,
        original_task: str,
        response: str,
    ) -> CritiqueResult:
        """
        응답 비평

        Args:
            original_task: 원래 작업 설명
            response: 평가할 응답

        Returns:
            CritiqueResult: 비평 결과
        """
        user_prompt = CRITIQUE_USER_PROMPT_TEMPLATE.format(
            original_task=original_task,
            response=response[:5000],  # Truncate
        )

        messages = [
            {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # 비평은 빠른 모델 사용
        critique_response = self.llm.call_with_smart_routing(
            messages=messages,
            task_type=TaskType.VALIDATION,
            temperature=0.1,
            max_tokens=2048,
        )

        # JSON 파싱
        try:
            # JSON 블록 추출
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', critique_response, re.DOTALL)
            if json_match:
                critique_data = json.loads(json_match.group(1))
            else:
                # 전체 응답이 JSON인 경우
                critique_data = json.loads(critique_response)

            return CritiqueResult(
                quality_score=float(critique_data.get("quality_score", 0.5)),
                issues=critique_data.get("issues", []),
                suggestions=critique_data.get("suggestions", []),
                should_regenerate=critique_data.get("should_regenerate", False),
                critique_reasoning=critique_data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "critique_parse_failed",
                error=str(e),
                response_preview=critique_response[:200],
            )
            # Fallback: 중간 품질로 가정
            return CritiqueResult(
                quality_score=0.5,
                issues=["비평 파싱 실패"],
                suggestions=[],
                should_regenerate=False,
                critique_reasoning="비평 응답 파싱 실패",
            )

    def regenerate(
        self,
        original_task: str,
        previous_response: str,
        critique: CritiqueResult,
        original_messages: list[dict],
    ) -> str:
        """
        개선된 응답 재생성

        Args:
            original_task: 원래 작업 설명
            previous_response: 이전 응답
            critique: 비평 결과
            original_messages: 원래 프롬프트 메시지

        Returns:
            str: 개선된 응답
        """
        user_prompt = REGENERATE_USER_PROMPT_TEMPLATE.format(
            original_task=original_task,
            previous_response=previous_response[:3000],
            quality_score=critique.quality_score,
            issues="\n".join(f"- {i}" for i in critique.issues),
            suggestions="\n".join(f"- {s}" for s in critique.suggestions),
        )

        messages = [
            {"role": "system", "content": REGENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # 재생성은 고품질 모델 사용
        return self.llm.call_with_smart_routing(
            messages=messages,
            task_type=TaskType.MULTI_STEP_REASONING,
            temperature=0.2,
            max_tokens=8192,
        )

    def generate_with_reflection(
        self,
        task_description: str,
        messages: list[dict],
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
        max_iterations: int = MAX_ITERATIONS,
        task_type: Optional[TaskType] = None,
    ) -> ReflectionResult:
        """
        Reflection 패턴으로 응답 생성

        Args:
            task_description: 작업 설명 (비평에 사용)
            messages: LLM 프롬프트 메시지
            quality_threshold: 품질 임계값 (이상이면 재생성 안함)
            max_iterations: 최대 반복 횟수
            task_type: 작업 유형 (model routing용)

        Returns:
            ReflectionResult: 최종 결과 및 반복 이력
        """
        import time

        iterations = []
        current_response = None
        improved = False

        for i in range(max_iterations + 1):  # +1 for initial generation
            start_time = time.time()

            if i == 0:
                # Initial generation
                logger.info(
                    "reflection_initial_generation",
                    iteration=i,
                )
                current_response = self.llm.call_with_smart_routing(
                    messages=messages,
                    task_type=task_type or TaskType.MULTI_STEP_REASONING,
                    temperature=0.2,
                    max_tokens=8192,
                )
            else:
                # Regeneration based on critique
                logger.info(
                    "reflection_regeneration",
                    iteration=i,
                    previous_score=iterations[-1].critique.quality_score,
                )
                current_response = self.regenerate(
                    original_task=task_description,
                    previous_response=current_response,
                    critique=iterations[-1].critique,
                    original_messages=messages,
                )
                improved = True

            # Critique
            critique = self.critique(task_description, current_response)

            duration_ms = int((time.time() - start_time) * 1000)

            iterations.append(ReflectionIteration(
                iteration=i,
                response=current_response,
                critique=critique,
                duration_ms=duration_ms,
            ))

            logger.info(
                "reflection_iteration_complete",
                iteration=i,
                quality_score=critique.quality_score,
                should_regenerate=critique.should_regenerate,
                issues_count=len(critique.issues),
            )

            # Check if quality is sufficient
            if critique.quality_score >= quality_threshold:
                logger.info(
                    "reflection_quality_met",
                    iteration=i,
                    final_score=critique.quality_score,
                )
                break

            # Check if regeneration is recommended
            if not critique.should_regenerate:
                logger.info(
                    "reflection_no_regenerate_recommended",
                    iteration=i,
                    reason="critique says no improvement possible",
                )
                break

            # Check if max iterations reached
            if i >= max_iterations:
                logger.warning(
                    "reflection_max_iterations_reached",
                    final_score=critique.quality_score,
                )
                break

        final_iteration = iterations[-1]

        return ReflectionResult(
            final_response=final_iteration.response,
            iterations=iterations,
            total_iterations=len(iterations),
            final_quality_score=final_iteration.critique.quality_score,
            improved=improved and len(iterations) > 1,
            model_used=self.llm.last_successful_model or "unknown",
        )

    def extract_signals_with_reflection(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> ReflectionResult:
        """
        Reflection 패턴으로 시그널 추출

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            context: 컨텍스트 정보

        Returns:
            ReflectionResult: 추출된 시그널 및 반복 이력
        """
        task_description = f"""
        기업 리스크/기회 시그널 추출 작업.

        요구사항:
        - 모든 시그널에 구체적 근거(evidence) 필수
        - signal_type: DIRECT, INDUSTRY, ENVIRONMENT
        - impact_direction: RISK, OPPORTUNITY, NEUTRAL
        - confidence: HIGH, MED, LOW
        - JSON 형식 출력

        컨텍스트 요약: corp_id={context.get('corp_id', 'unknown')}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self.generate_with_reflection(
            task_description=task_description,
            messages=messages,
            quality_threshold=0.7,
            task_type=TaskType.SIGNAL_EXTRACTION,
        )


# Singleton instance
_reflection_agent: Optional[ReflectionAgent] = None


def get_reflection_agent() -> ReflectionAgent:
    """Get singleton Reflection Agent instance"""
    global _reflection_agent
    if _reflection_agent is None:
        _reflection_agent = ReflectionAgent()
    return _reflection_agent


def reset_reflection_agent() -> None:
    """Reset singleton instance (for testing)"""
    global _reflection_agent
    _reflection_agent = None
