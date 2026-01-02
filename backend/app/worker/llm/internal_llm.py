"""
Internal LLM Interface and Implementations
보안 아키텍처: 내부 민감 데이터 전용 LLM

Phase 1 (MVP): 외부 API 사용 (GPT-3.5, Claude Haiku) + 인터페이스 추상화
Phase 2 (Pilot): Private Cloud LLM (Azure OpenAI, AWS Bedrock)
Phase 3 (Production): On-Premise LLM (Llama 3, Solar)
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any

import litellm
from litellm import completion

from app.core.config import settings
from app.worker.llm.exceptions import (
    AllProvidersFailedError,
    InvalidResponseError,
)

logger = logging.getLogger(__name__)


class InternalLLMProvider(Enum):
    """Internal LLM 제공자 (교체 가능)"""
    MVP_OPENAI = "mvp_openai"          # Phase 1: GPT-3.5-turbo (저비용)
    MVP_ANTHROPIC = "mvp_anthropic"    # Phase 1: Claude 3 Haiku (경량)
    AZURE_OPENAI = "azure_openai"      # Phase 2: Azure OpenAI (국내 리전)
    AWS_BEDROCK = "aws_bedrock"        # Phase 2: AWS Bedrock Claude
    ONPREM_LLAMA = "onprem_llama"      # Phase 3: Llama 3 (On-Premise)
    ONPREM_SOLAR = "onprem_solar"      # Phase 3: Upstage Solar


class DataClassification(Enum):
    """데이터 분류"""
    PUBLIC = "PUBLIC"           # 공개 데이터 (뉴스, 공시)
    INTERNAL = "INTERNAL"       # 내부 민감 데이터 (KYC, 여신)
    SEMI_PUBLIC = "SEMI_PUBLIC" # 준공개 (공시 재무제표 vs 제출 재무제표)


class InternalLLMBase(ABC):
    """
    Internal LLM 추상 인터페이스

    모든 Internal LLM 구현체는 이 인터페이스를 따름
    → Phase 전환 시 구현체만 교체하면 됨

    🔒 보안 요구사항:
    - 데이터가 은행 네트워크 외부로 나가지 않음 (Phase 3)
    - 모든 처리 로그 감사 추적 가능
    - 개인식별정보(PII) 마스킹 옵션
    """

    @property
    @abstractmethod
    def provider(self) -> InternalLLMProvider:
        """현재 Provider 반환"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """사용 중인 모델 이름"""
        pass

    @abstractmethod
    def analyze_snapshot(self, snapshot_json: dict) -> dict:
        """
        내부 Snapshot 분석 → Direct Signal 후보 생성

        Args:
            snapshot_json: PRD 7장 스키마의 Internal Snapshot JSON

        Returns:
            dict: {
                "potential_signals": list[dict],  # 시그널 후보
                "risk_indicators": list[dict],    # 리스크 지표
                "analysis_summary": str           # 분석 요약
            }
        """
        pass

    @abstractmethod
    def extract_document_facts(
        self,
        image_base64: str,
        doc_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        문서 이미지에서 구조화된 정보 추출 (Vision)

        Args:
            image_base64: Base64 인코딩된 문서 이미지
            doc_type: 문서 타입 (BIZ_REG, REGISTRY, etc.)
            system_prompt: 시스템 프롬프트
            user_prompt: 문서 타입별 추출 프롬프트

        Returns:
            dict: 추출된 구조화 정보 (PRD 14.4 fact 스키마)
        """
        pass

    @abstractmethod
    def generate_signals(
        self,
        internal_context: dict,
        external_intel: list[dict],
        system_prompt: str,
        user_prompt: str,
    ) -> list[dict]:
        """
        Internal + External 결합하여 최종 시그널 생성

        Args:
            internal_context: 내부 데이터 (Snapshot + Doc Facts)
            external_intel: External LLM이 적재한 외부 인텔리전스
            system_prompt: 시그널 추출 시스템 프롬프트
            user_prompt: 포맷된 사용자 프롬프트

        Returns:
            list[dict]: 시그널 목록
        """
        pass

    @abstractmethod
    def validate_signal(self, signal: dict) -> dict:
        """
        시그널 검증 (근거 확인, 표현 검토)

        Args:
            signal: 검증할 시그널

        Returns:
            dict: 검증된 시그널 (또는 수정된 시그널)
        """
        pass

    @abstractmethod
    def generate_insight(
        self,
        signals: list[dict],
        context: dict,
        similar_cases: list[dict] = None,
    ) -> str:
        """
        최종 인사이트 요약 생성

        Args:
            signals: 검증된 시그널 목록
            context: 통합 컨텍스트
            similar_cases: 유사 과거 케이스 (벡터 검색 결과)

        Returns:
            str: 생성된 인사이트 요약 (한국어)
        """
        pass


class MVPInternalLLM(InternalLLMBase):
    """
    Phase 1: MVP용 Internal LLM 구현

    실제로는 외부 API를 사용하지만,
    InternalLLMBase 인터페이스로 추상화

    ⚠️ MVP 제약:
    - 실 고객 데이터 사용 금지 (가상 데이터만)
    - 대회 시연용으로만 활용
    """

    # MVP 모델 설정 (저비용 + 빠른 응답)
    TEXT_MODELS = [
        {"model": "gpt-3.5-turbo", "provider": "openai"},
        {"model": "claude-3-haiku-20240307", "provider": "anthropic"},
    ]

    # Vision 모델 (문서 OCR)
    VISION_MODELS = [
        {"model": "gpt-4o-mini", "provider": "openai"},
        {"model": "claude-sonnet-4-20250514", "provider": "anthropic"},
    ]

    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0
    MAX_DELAY = 30.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self):
        self._provider = InternalLLMProvider.MVP_OPENAI
        self._model_name = "gpt-3.5-turbo"
        self._configure_api_keys()

    @property
    def provider(self) -> InternalLLMProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    def _configure_api_keys(self):
        """API 키 설정"""
        # Internal LLM용 별도 키가 있으면 사용, 없으면 기본 키 사용
        internal_openai_key = os.getenv("INTERNAL_LLM_OPENAI_KEY", settings.OPENAI_API_KEY)
        internal_anthropic_key = os.getenv("INTERNAL_LLM_ANTHROPIC_KEY", settings.ANTHROPIC_API_KEY)

        if internal_openai_key:
            litellm.openai_key = internal_openai_key
        if internal_anthropic_key:
            litellm.anthropic_key = internal_anthropic_key

    def _call_with_retry(
        self,
        messages: list[dict],
        models: list[dict],
        response_format: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """재시도 로직이 포함된 LLM 호출"""
        errors = []

        for model_config in models:
            model = model_config["model"]
            provider = model_config["provider"]

            for attempt in range(self.MAX_RETRIES):
                try:
                    logger.info(f"[Internal LLM] Calling {model} (attempt {attempt + 1})")

                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }

                    if response_format:
                        kwargs["response_format"] = response_format

                    response = completion(**kwargs)
                    content = response.choices[0].message.content

                    self._model_name = model
                    logger.info(f"[Internal LLM] Success from {model}")

                    return content

                except Exception as e:
                    errors.append({"model": model, "error": str(e)})
                    logger.warning(f"[Internal LLM] {model} failed: {e}")

                    if attempt < self.MAX_RETRIES - 1:
                        delay = min(
                            self.INITIAL_DELAY * (self.BACKOFF_MULTIPLIER ** attempt),
                            self.MAX_DELAY,
                        )
                        time.sleep(delay)

        raise AllProvidersFailedError(
            message=f"[Internal LLM] All providers failed",
            errors=errors,
        )

    def analyze_snapshot(self, snapshot_json: dict) -> dict:
        """
        [MVP 구현] Snapshot 분석하여 리스크 지표 추출
        """
        system_prompt = """You are a senior risk analyst at a Korean bank.
Analyze the internal snapshot data and identify potential risk indicators.
Focus on:
1. KYC status changes
2. Credit grade changes
3. Loan exposure changes
4. Collateral changes
5. Overdue flags

Return JSON with structure:
{
    "potential_signals": [{"type": "...", "reason": "..."}],
    "risk_indicators": [{"indicator": "...", "severity": "HIGH/MED/LOW"}],
    "analysis_summary": "..."
}
"""
        user_prompt = f"""Analyze this internal snapshot data:

```json
{json.dumps(snapshot_json, ensure_ascii=False, indent=2)}
```

Identify any risk indicators or potential signal triggers.
Respond in Korean for analysis_summary."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self._call_with_retry(
            messages=messages,
            models=self.TEXT_MODELS,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "potential_signals": [],
                "risk_indicators": [],
                "analysis_summary": result[:500],
            }

    def extract_document_facts(
        self,
        image_base64: str,
        doc_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        [MVP 구현] Vision LLM으로 문서에서 정보 추출
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        result = self._call_with_retry(
            messages=messages,
            models=self.VISION_MODELS,
            max_tokens=4096,
        )

        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise InvalidResponseError(
                message=f"Failed to parse document extraction: {e}",
                raw_response=result[:500],
            )

    def generate_signals(
        self,
        internal_context: dict,
        external_intel: list[dict],
        system_prompt: str,
        user_prompt: str,
    ) -> list[dict]:
        """
        [MVP 구현] 내부+외부 데이터 결합하여 시그널 생성
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self._call_with_retry(
            messages=messages,
            models=self.TEXT_MODELS,
            response_format={"type": "json_object"},
            max_tokens=4096,
        )

        try:
            parsed = json.loads(result)
            signals = parsed.get("signals", [])
            logger.info(f"[Internal LLM] Extracted {len(signals)} signals")
            return signals
        except json.JSONDecodeError:
            logger.error("[Internal LLM] Failed to parse signals response")
            return []

    def validate_signal(self, signal: dict) -> dict:
        """
        [MVP 구현] 시그널 검증 (간단한 규칙 기반)
        """
        # MVP에서는 기존 ValidationPipeline에 위임
        # Phase 2/3에서 LLM 기반 검증으로 확장 가능
        return signal

    def generate_insight(
        self,
        signals: list[dict],
        context: dict,
        similar_cases: list[dict] = None,
    ) -> str:
        """
        [MVP 구현] 인사이트 요약 생성
        """
        from app.worker.llm.prompts import INSIGHT_GENERATION_PROMPT

        # 시그널 요약 빌드
        signal_summary = self._build_signal_summary(signals)

        user_prompt = INSIGHT_GENERATION_PROMPT.format(
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            signal_count=len(signals),
            signals_summary=signal_summary,
        )

        # 유사 케이스 추가
        if similar_cases:
            cases_text = self._format_similar_cases(similar_cases)
            user_prompt += f"\n\n### 유사 과거 케이스 참고\n{cases_text}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior risk analyst providing executive briefings. "
                    "Generate concise, actionable insights in Korean. "
                    "Use probabilistic language: '~로 추정됨', '~가능성 있음', '검토 권고'. "
                    "Avoid definitive statements."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        return self._call_with_retry(
            messages=messages,
            models=self.TEXT_MODELS,
            temperature=0.3,
            max_tokens=1000,
        ).strip()

    def _build_signal_summary(self, signals: list[dict]) -> str:
        """시그널 요약 텍스트 생성"""
        lines = []

        risk_signals = [s for s in signals if s.get("impact_direction") == "RISK"]
        opp_signals = [s for s in signals if s.get("impact_direction") == "OPPORTUNITY"]

        if risk_signals:
            lines.append(f"## 리스크 시그널 ({len(risk_signals)}건)")
            for s in risk_signals:
                strength = s.get("impact_strength", "MED")
                lines.append(f"- [{strength}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        if opp_signals:
            lines.append(f"\n## 기회 시그널 ({len(opp_signals)}건)")
            for s in opp_signals:
                strength = s.get("impact_strength", "MED")
                lines.append(f"- [{strength}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        return "\n".join(lines)

    def _format_similar_cases(self, cases: list[dict]) -> str:
        """유사 케이스 포맷팅"""
        lines = []
        for i, case in enumerate(cases, 1):
            similarity_pct = int(case.get("similarity", 0) * 100)
            lines.append(
                f"{i}. [{case.get('signal_type', 'N/A')}] {case.get('event_type', 'N/A')} "
                f"(유사도 {similarity_pct}%)\n"
                f"   - 업종: {case.get('industry_code', 'N/A')}\n"
                f"   - 요약: {case.get('summary', 'N/A')[:100]}..."
            )
        return "\n".join(lines)


class AzureInternalLLM(InternalLLMBase):
    """
    Phase 2: Azure OpenAI 기반 Internal LLM

    데이터가 Azure 국내 리전에서만 처리됨
    (추후 구현 예정)
    """

    def __init__(self):
        self._provider = InternalLLMProvider.AZURE_OPENAI
        self._model_name = "gpt-4"
        # Azure 설정은 환경변수에서 로드
        self._endpoint = os.getenv("INTERNAL_LLM_AZURE_ENDPOINT", "")
        self._deployment = os.getenv("INTERNAL_LLM_AZURE_DEPLOYMENT", "gpt-4")
        self._api_version = os.getenv("INTERNAL_LLM_AZURE_API_VERSION", "2024-02-15-preview")

    @property
    def provider(self) -> InternalLLMProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    def analyze_snapshot(self, snapshot_json: dict) -> dict:
        raise NotImplementedError("Phase 2 - Azure OpenAI implementation pending")

    def extract_document_facts(self, image_base64: str, doc_type: str,
                               system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError("Phase 2 - Azure OpenAI implementation pending")

    def generate_signals(self, internal_context: dict, external_intel: list[dict],
                         system_prompt: str, user_prompt: str) -> list[dict]:
        raise NotImplementedError("Phase 2 - Azure OpenAI implementation pending")

    def validate_signal(self, signal: dict) -> dict:
        raise NotImplementedError("Phase 2 - Azure OpenAI implementation pending")

    def generate_insight(self, signals: list[dict], context: dict,
                         similar_cases: list[dict] = None) -> str:
        raise NotImplementedError("Phase 2 - Azure OpenAI implementation pending")


class OnPremLlamaLLM(InternalLLMBase):
    """
    Phase 3: On-Premise Llama 3 기반 Internal LLM

    완전 자체 인프라에서 운영
    (추후 구현 예정)
    """

    def __init__(self):
        self._provider = InternalLLMProvider.ONPREM_LLAMA
        self._model_name = "meta-llama/Llama-3.1-70B-Instruct"
        # vLLM 서버 엔드포인트
        self._endpoint = os.getenv("INTERNAL_LLM_ONPREM_ENDPOINT", "http://internal-llm.bank.local:8000")

    @property
    def provider(self) -> InternalLLMProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    def analyze_snapshot(self, snapshot_json: dict) -> dict:
        raise NotImplementedError("Phase 3 - On-Premise Llama implementation pending")

    def extract_document_facts(self, image_base64: str, doc_type: str,
                               system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError("Phase 3 - On-Premise Llama implementation pending")

    def generate_signals(self, internal_context: dict, external_intel: list[dict],
                         system_prompt: str, user_prompt: str) -> list[dict]:
        raise NotImplementedError("Phase 3 - On-Premise Llama implementation pending")

    def validate_signal(self, signal: dict) -> dict:
        raise NotImplementedError("Phase 3 - On-Premise Llama implementation pending")

    def generate_insight(self, signals: list[dict], context: dict,
                         similar_cases: list[dict] = None) -> str:
        raise NotImplementedError("Phase 3 - On-Premise Llama implementation pending")


def get_internal_llm() -> InternalLLMBase:
    """
    Factory: 환경 변수에 따라 Internal LLM 인스턴스 반환

    INTERNAL_LLM_PROVIDER 환경변수로 제어:
    - mvp_openai (기본값) → MVPInternalLLM
    - azure_openai → AzureInternalLLM
    - onprem_llama → OnPremLlamaLLM
    """
    provider = os.getenv("INTERNAL_LLM_PROVIDER", "mvp_openai").lower()

    if provider == "mvp_openai" or provider == "mvp_anthropic":
        return MVPInternalLLM()
    elif provider == "azure_openai":
        return AzureInternalLLM()
    elif provider == "onprem_llama":
        return OnPremLlamaLLM()
    else:
        logger.warning(f"Unknown Internal LLM provider: {provider}, using MVP")
        return MVPInternalLLM()
