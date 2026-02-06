"""
Task-Aware Model Router for rKYC

Intelligently selects LLM models based on task complexity:
- Simple tasks: Claude Haiku / GPT-4o-mini (fast, cost-effective)
- Complex tasks: Claude Opus / GPT-4o (high quality)

Task Classification:
- SIMPLE: Validation, short extraction, yes/no questions
- MODERATE: Standard extraction, summarization
- COMPLEX: Multi-step reasoning, insight generation, consensus

Usage:
    from app.worker.llm.model_router import ModelRouter, TaskComplexity

    router = ModelRouter()

    # Classify task automatically
    complexity = router.classify_task(prompt, context)

    # Get appropriate models for the task
    models = router.get_models(complexity)

    # Or use convenience method
    models = router.get_models_for_prompt(prompt, context)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.worker.tracing import get_logger

logger = get_logger("ModelRouter")


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class TaskType(str, Enum):
    """Known task types with pre-defined complexity"""
    # Simple tasks
    VALIDATION = "validation"
    FIELD_EXTRACTION = "field_extraction"
    YES_NO_QUESTION = "yes_no_question"
    CLASSIFICATION = "classification"

    # Moderate tasks
    SUMMARIZATION = "summarization"
    ENTITY_EXTRACTION = "entity_extraction"
    TRANSLATION = "translation"
    PROFILE_EXTRACTION = "profile_extraction"

    # Complex tasks
    SIGNAL_EXTRACTION = "signal_extraction"
    INSIGHT_GENERATION = "insight_generation"
    CONSENSUS = "consensus"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    DOCUMENT_ANALYSIS = "document_analysis"


# Task type to complexity mapping
TASK_COMPLEXITY_MAP: dict[TaskType, TaskComplexity] = {
    # Simple
    TaskType.VALIDATION: TaskComplexity.SIMPLE,
    TaskType.FIELD_EXTRACTION: TaskComplexity.SIMPLE,
    TaskType.YES_NO_QUESTION: TaskComplexity.SIMPLE,
    TaskType.CLASSIFICATION: TaskComplexity.SIMPLE,
    # Moderate
    TaskType.SUMMARIZATION: TaskComplexity.MODERATE,
    TaskType.ENTITY_EXTRACTION: TaskComplexity.MODERATE,
    TaskType.TRANSLATION: TaskComplexity.MODERATE,
    TaskType.PROFILE_EXTRACTION: TaskComplexity.MODERATE,
    # Complex
    TaskType.SIGNAL_EXTRACTION: TaskComplexity.COMPLEX,
    TaskType.INSIGHT_GENERATION: TaskComplexity.COMPLEX,
    TaskType.CONSENSUS: TaskComplexity.COMPLEX,
    TaskType.MULTI_STEP_REASONING: TaskComplexity.COMPLEX,
    TaskType.DOCUMENT_ANALYSIS: TaskComplexity.COMPLEX,
}


@dataclass
class ModelConfig:
    """LLM model configuration"""
    model: str
    provider: str
    max_tokens: int = 4096
    supports_json_mode: bool = True
    supports_vision: bool = False


@dataclass
class ModelTier:
    """Model tier with primary and fallback models"""
    primary: ModelConfig
    fallbacks: list[ModelConfig] = field(default_factory=list)

    def all_models(self) -> list[ModelConfig]:
        """Get all models including fallbacks"""
        return [self.primary] + self.fallbacks


class ModelRouter:
    """
    Task-Aware Model Router

    Selects appropriate LLM models based on task complexity.

    P1-1: Configuration 외부화 - 모델 설정을 config.py에서 읽기
    """

    @staticmethod
    def _load_models_from_settings() -> dict[str, ModelTier]:
        """Load model configurations from settings (P1-1)"""
        try:
            from app.core.config import settings

            def _get_provider(model: str) -> str:
                if "claude" in model.lower():
                    return "anthropic"
                elif "gpt" in model.lower():
                    return "openai"
                elif "gemini" in model.lower():
                    return "google"
                return "anthropic"

            simple = ModelTier(
                primary=ModelConfig(
                    model=settings.MODEL_SIMPLE_PRIMARY,
                    provider=_get_provider(settings.MODEL_SIMPLE_PRIMARY),
                    max_tokens=4096,
                ),
                fallbacks=[
                    ModelConfig(
                        model=settings.MODEL_SIMPLE_FALLBACK,
                        provider=_get_provider(settings.MODEL_SIMPLE_FALLBACK),
                        max_tokens=4096,
                    ),
                ],
            )

            moderate = ModelTier(
                primary=ModelConfig(
                    model=settings.MODEL_MODERATE_PRIMARY,
                    provider=_get_provider(settings.MODEL_MODERATE_PRIMARY),
                    max_tokens=8192,
                ),
                fallbacks=[
                    ModelConfig(
                        model=settings.MODEL_MODERATE_FALLBACK1,
                        provider=_get_provider(settings.MODEL_MODERATE_FALLBACK1),
                        max_tokens=8192,
                    ),
                    ModelConfig(
                        model=settings.MODEL_MODERATE_FALLBACK2,
                        provider=_get_provider(settings.MODEL_MODERATE_FALLBACK2),
                        max_tokens=8192,
                    ),
                ],
            )

            complex_tier = ModelTier(
                primary=ModelConfig(
                    model=settings.MODEL_COMPLEX_PRIMARY,
                    provider=_get_provider(settings.MODEL_COMPLEX_PRIMARY),
                    max_tokens=8192,
                ),
                fallbacks=[
                    ModelConfig(
                        model=settings.MODEL_COMPLEX_FALLBACK1,
                        provider=_get_provider(settings.MODEL_COMPLEX_FALLBACK1),
                        max_tokens=8192,
                    ),
                    ModelConfig(
                        model=settings.MODEL_COMPLEX_FALLBACK2,
                        provider=_get_provider(settings.MODEL_COMPLEX_FALLBACK2),
                        max_tokens=8192,
                    ),
                ],
            )

            return {
                "simple": simple,
                "moderate": moderate,
                "complex": complex_tier,
            }
        except Exception as e:
            logger.warning(f"Failed to load model config from settings: {e}, using defaults")
            return ModelRouter._get_default_models()

    @staticmethod
    def _get_default_models() -> dict[str, ModelTier]:
        """Fallback default model configurations"""
        return {
            "simple": ModelTier(
                primary=ModelConfig(model="claude-3-5-haiku-20241022", provider="anthropic", max_tokens=4096),
                fallbacks=[ModelConfig(model="gpt-4o-mini", provider="openai", max_tokens=4096)],
            ),
            "moderate": ModelTier(
                primary=ModelConfig(model="claude-sonnet-4-20250514", provider="anthropic", max_tokens=8192),
                fallbacks=[
                    ModelConfig(model="gpt-4o", provider="openai", max_tokens=8192),
                    ModelConfig(model="gemini/gemini-3-pro-preview", provider="google", max_tokens=8192),
                ],
            ),
            "complex": ModelTier(
                primary=ModelConfig(model="claude-opus-4-5-20251101", provider="anthropic", max_tokens=8192),
                fallbacks=[
                    ModelConfig(model="gpt-4o", provider="openai", max_tokens=8192),
                    ModelConfig(model="gemini/gemini-3-pro-preview", provider="google", max_tokens=8192),
                ],
            ),
        }

    # Class-level defaults (for backwards compatibility)
    _default_models = _get_default_models.__func__()
    SIMPLE_MODELS = _default_models["simple"]
    MODERATE_MODELS = _default_models["moderate"]
    COMPLEX_MODELS = _default_models["complex"]

    # Complexity indicators in prompts (English)
    SIMPLE_INDICATORS_EN = [
        r"validate\b",
        r"check\s+if\b",
        r"is\s+this\s+valid",
        r"yes\s+or\s+no",
        r"true\s+or\s+false",
        r"classify\b",
        r"extract\s+(the\s+)?(single|one)",
        r"simple\b",
        r"verify\b",
    ]

    # P3-1: 한국어 지표 추가
    SIMPLE_INDICATORS_KO = [
        r"검증",
        r"확인",
        r"유효(한|성)",
        r"예/아니오",
        r"참/거짓",
        r"분류",
        r"단일\s*추출",
        r"간단(한|히)",
        r"검사",
    ]

    SIMPLE_INDICATORS = SIMPLE_INDICATORS_EN + SIMPLE_INDICATORS_KO

    COMPLEX_INDICATORS_EN = [
        r"analyze\b",
        r"insight",
        r"signal",
        r"risk\s+assess",
        r"multi(-|\s)?step",
        r"chain\s+of\s+thought",
        r"reason(ing)?",
        r"synthesize",
        r"comprehensive",
        r"detailed\s+analysis",
        r"expert\b",
        r"consensus",
        r"compare\s+and\s+contrast",
        r"evaluate\b",
        r"generate\s+report",
    ]

    # P3-1: 한국어 지표 추가
    COMPLEX_INDICATORS_KO = [
        r"분석",
        r"인사이트",
        r"시그널",
        r"리스크\s*평가",
        r"위험\s*평가",
        r"다단계",
        r"사고\s*과정",
        r"추론",
        r"종합",
        r"상세\s*분석",
        r"전문가",
        r"합의",
        r"비교\s*분석",
        r"평가",
        r"보고서\s*생성",
        r"심층\s*분석",
        r"기업\s*분석",
        r"산업\s*분석",
    ]

    COMPLEX_INDICATORS = COMPLEX_INDICATORS_EN + COMPLEX_INDICATORS_KO

    # P3-1: Moderate indicators (English + Korean)
    MODERATE_INDICATORS_EN = [
        r"summarize\b",
        r"extract\s+entities",
        r"translate\b",
        r"profile\s+extraction",
        r"outline\b",
        r"list\s+all",
        r"describe\b",
    ]

    MODERATE_INDICATORS_KO = [
        r"요약",
        r"개체\s*추출",
        r"번역",
        r"프로필\s*추출",
        r"개요",
        r"목록\s*작성",
        r"설명",
        r"정리",
    ]

    MODERATE_INDICATORS = MODERATE_INDICATORS_EN + MODERATE_INDICATORS_KO

    def __init__(self):
        # P1-1: Load models from settings (falls back to class defaults)
        models = self._load_models_from_settings()
        self._tier_map = {
            TaskComplexity.SIMPLE: models.get("simple", self.SIMPLE_MODELS),
            TaskComplexity.MODERATE: models.get("moderate", self.MODERATE_MODELS),
            TaskComplexity.COMPLEX: models.get("complex", self.COMPLEX_MODELS),
        }

    def classify_task(
        self,
        prompt: str,
        context: Optional[dict] = None,
        task_type: Optional[TaskType] = None,
    ) -> TaskComplexity:
        """
        Classify task complexity based on prompt and context.

        Args:
            prompt: The prompt text
            context: Optional context dict
            task_type: Optional pre-defined task type

        Returns:
            TaskComplexity: Classified complexity level
        """
        # If task type is provided, use predefined mapping
        if task_type:
            complexity = TASK_COMPLEXITY_MAP.get(task_type, TaskComplexity.MODERATE)
            logger.debug(
                "task_classified_by_type",
                task_type=task_type.value,
                complexity=complexity.value,
            )
            return complexity

        # Analyze prompt for complexity indicators
        # P3-1: 한국어 프롬프트도 지원 (lower()는 영어에만 적용)
        prompt_lower = prompt.lower()

        # Check for complex indicators
        complex_score = sum(
            1 for pattern in self.COMPLEX_INDICATORS
            if re.search(pattern, prompt_lower) or re.search(pattern, prompt)
        )

        # Check for moderate indicators (P3-1)
        moderate_score = sum(
            1 for pattern in self.MODERATE_INDICATORS
            if re.search(pattern, prompt_lower) or re.search(pattern, prompt)
        )

        # Check for simple indicators
        simple_score = sum(
            1 for pattern in self.SIMPLE_INDICATORS
            if re.search(pattern, prompt_lower) or re.search(pattern, prompt)
        )

        # Consider prompt length
        prompt_length = len(prompt)
        if prompt_length > 2000:
            complex_score += 1
        elif prompt_length < 200:
            simple_score += 1

        # Consider context size
        if context:
            context_size = len(str(context))
            if context_size > 5000:
                complex_score += 1

        # Determine complexity (P3-1: moderate_score 추가)
        scores = {
            TaskComplexity.COMPLEX: complex_score,
            TaskComplexity.MODERATE: moderate_score,
            TaskComplexity.SIMPLE: simple_score,
        }
        complexity = max(scores, key=scores.get)

        # Default to MODERATE if all scores are 0
        if all(s == 0 for s in scores.values()):
            complexity = TaskComplexity.MODERATE

        logger.debug(
            "task_classified_by_analysis",
            complexity=complexity.value,
            complex_score=complex_score,
            moderate_score=moderate_score,
            simple_score=simple_score,
            prompt_length=prompt_length,
        )

        return complexity

    def get_models(self, complexity: TaskComplexity) -> list[dict]:
        """
        Get models for a given complexity level.

        Args:
            complexity: Task complexity level

        Returns:
            list[dict]: List of model configurations for LLMService
        """
        tier = self._tier_map[complexity]
        models = []

        for config in tier.all_models():
            models.append({
                "model": config.model,
                "provider": config.provider,
                "max_tokens": config.max_tokens,
            })

        logger.debug(
            "models_selected",
            complexity=complexity.value,
            models=[m["model"] for m in models],
        )

        return models

    def get_models_for_prompt(
        self,
        prompt: str,
        context: Optional[dict] = None,
        task_type: Optional[TaskType] = None,
    ) -> list[dict]:
        """
        Convenience method: classify task and get appropriate models.

        Args:
            prompt: The prompt text
            context: Optional context dict
            task_type: Optional pre-defined task type

        Returns:
            list[dict]: List of model configurations
        """
        complexity = self.classify_task(prompt, context, task_type)
        return self.get_models(complexity)

    def get_primary_model(
        self,
        complexity: TaskComplexity,
    ) -> dict:
        """
        Get only the primary model for a complexity level.

        Args:
            complexity: Task complexity level

        Returns:
            dict: Primary model configuration
        """
        tier = self._tier_map[complexity]
        config = tier.primary
        return {
            "model": config.model,
            "provider": config.provider,
            "max_tokens": config.max_tokens,
        }

    def estimate_cost_ratio(self, complexity: TaskComplexity) -> float:
        """
        Estimate relative cost ratio compared to complex tier.

        Returns:
            float: Cost ratio (1.0 = complex tier cost)
        """
        # Approximate cost ratios based on typical pricing
        # Complex (Opus): 1.0x
        # Moderate (Sonnet): 0.3x
        # Simple (Haiku): 0.05x
        ratios = {
            TaskComplexity.COMPLEX: 1.0,
            TaskComplexity.MODERATE: 0.3,
            TaskComplexity.SIMPLE: 0.05,
        }
        return ratios.get(complexity, 1.0)


# Singleton instance
_router_instance: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get singleton model router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance


def reset_model_router() -> None:
    """Reset singleton router instance (for testing)"""
    global _router_instance
    _router_instance = None
