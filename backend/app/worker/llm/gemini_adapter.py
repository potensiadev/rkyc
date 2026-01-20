"""
Gemini Adapter for Layer 1.5 Validation

PRD v1.2 결정 사항:
- Gemini는 검색 불가 (검색 → 검증/보완 역할로 변경)
- Perplexity 결과 검증 + 생성형 보완 (GEMINI_INFERRED)
- 교차 검증을 통한 신뢰도 향상
"""

import json
import logging
from typing import Optional
from datetime import datetime

import litellm
from litellm import completion

from app.core.config import settings
from app.worker.llm.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """
    Gemini Validation Adapter (Layer 1.5)

    역할:
    - Perplexity 검색 결과 검증
    - 누락된 필드 생성형 보완 (source: GEMINI_INFERRED)
    - 불일치 필드 discrepancy 표시

    제한:
    - 웹 검색 불가 (검색은 Perplexity 전담)
    - 검증/보완만 수행
    """

    MODEL = "gemini/gemini-3-pro-preview"
    MAX_RETRIES = 2
    TIMEOUT = 30.0

    def __init__(self):
        self._configure_api_key()

    def _configure_api_key(self):
        """Gemini API 키 설정"""
        import os
        api_key = os.getenv("GOOGLE_API_KEY", settings.GOOGLE_API_KEY)
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

    def search(self, query: str) -> dict:
        """
        Gemini는 검색 불가

        Raises:
            NotImplementedError: Gemini는 검색 기능을 지원하지 않음
        """
        raise NotImplementedError(
            "Gemini는 검색 불가. "
            "검색은 Perplexity를 사용하세요. "
            "Gemini는 validate() 메서드로 검증/보완만 수행합니다."
        )

    def validate(
        self,
        perplexity_result: dict,
        corp_name: str,
        industry_name: str,
    ) -> dict:
        """
        Perplexity 검색 결과 검증 및 보완

        Args:
            perplexity_result: Perplexity에서 추출한 프로필
            corp_name: 기업명
            industry_name: 업종명

        Returns:
            dict: 검증 및 보완된 프로필
                - validated_fields: 검증된 필드 목록
                - enriched_fields: 보완된 필드 (source: GEMINI_INFERRED)
                - discrepancies: 불일치 필드 목록
        """
        system_prompt = self._build_validation_prompt()
        user_prompt = self._build_user_prompt(perplexity_result, corp_name, industry_name)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = completion(
                model=self.MODEL,
                messages=messages,
                temperature=1.0,  # Gemini 3 requires temperature=1.0 to avoid infinite loops
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # 모든 enriched 필드에 source 표시
            if "enriched_fields" in result:
                for field_name, field_data in result["enriched_fields"].items():
                    if isinstance(field_data, dict):
                        field_data["source"] = "GEMINI_INFERRED"
                    else:
                        result["enriched_fields"][field_name] = {
                            "value": field_data,
                            "source": "GEMINI_INFERRED",
                            "confidence": "LOW",  # 생성형 보완은 기본 LOW
                        }

            logger.info(
                f"[Gemini] Validation complete: "
                f"validated={len(result.get('validated_fields', []))}, "
                f"enriched={len(result.get('enriched_fields', {}))}, "
                f"discrepancies={len(result.get('discrepancies', []))}"
            )

            return result

        except Exception as e:
            logger.error(f"[Gemini] Validation failed: {e}")
            return {
                "validated_fields": [],
                "enriched_fields": {},
                "discrepancies": [],
                "error": str(e),
            }

    def enrich_missing_fields(
        self,
        profile: dict,
        corp_name: str,
        industry_name: str,
    ) -> dict:
        """
        누락된 필드 생성형 보완

        Args:
            profile: 현재 프로필 (null 필드 포함)
            corp_name: 기업명
            industry_name: 업종명

        Returns:
            dict: 보완된 필드 (source: GEMINI_INFERRED)
        """
        # null인 필드 식별
        null_fields = [
            key for key, value in profile.items()
            if value is None or value == [] or value == {}
        ]

        if not null_fields:
            return {}

        system_prompt = """당신은 한국 기업 정보 전문가입니다.

## 역할
주어진 기업명과 업종을 바탕으로 누락된 필드를 추론합니다.

## 중요 규칙
1. 추론된 값은 반드시 `source: "GEMINI_INFERRED"`로 표시
2. 확신 없는 정보는 null 유지
3. 업종 일반론만으로 추론하지 말 것
4. 추론 근거가 있는 경우에만 값 제공

## 신뢰도 기준
- LOW: 업종 기반 추정 (기본값)
- MED: 공개된 일반 정보 기반
- HIGH: 사용 금지 (생성형 보완은 HIGH 불가)

## 출력 형식
{
  "field_name": {
    "value": <추론된 값 또는 null>,
    "source": "GEMINI_INFERRED",
    "confidence": "LOW" | "MED",
    "reasoning": "추론 근거 (1문장)"
  }
}

null 필드만 포함하세요. 기존 값이 있는 필드는 수정하지 마세요."""

        user_prompt = f"""기업: {corp_name}
업종: {industry_name}

누락된 필드: {json.dumps(null_fields, ensure_ascii=False)}

현재 프로필:
{json.dumps(profile, ensure_ascii=False, indent=2)}

위 기업의 누락된 필드를 추론하여 보완해주세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = completion(
                model=self.MODEL,
                messages=messages,
                temperature=1.0,  # Gemini 3 requires temperature=1.0 to avoid infinite loops
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            enriched = json.loads(content)

            # 모든 필드에 source 강제 표시
            for field_name, field_data in enriched.items():
                if isinstance(field_data, dict):
                    field_data["source"] = "GEMINI_INFERRED"
                    if "confidence" not in field_data:
                        field_data["confidence"] = "LOW"

            return enriched

        except Exception as e:
            logger.error(f"[Gemini] Enrichment failed: {e}")
            return {}

    def _build_validation_prompt(self) -> str:
        """검증 시스템 프롬프트 생성"""
        return """당신은 금융기관 기업심사 전문가입니다.

## 역할
Perplexity 검색 결과를 검증하고 보완합니다.

## 검증 규칙
1. 논리적 일관성 검사 (수출비중 + 국내비중 = 100%)
2. 범위 검사 (0% <= 비중 <= 100%)
3. 누락 필드 식별
4. 의심스러운 값 플래그

## 보완 규칙
1. 누락된 필드는 공개 정보 기반으로 추론 가능한 경우에만 보완
2. 보완된 값은 반드시 `source: "GEMINI_INFERRED"` 표시
3. 불확실한 경우 null 유지

## 불일치(discrepancy) 처리
- 범위 초과 값
- 논리적 모순
- 명백한 오류

## 출력 형식
{
  "validated_fields": ["검증 통과한 필드명 목록"],
  "enriched_fields": {
    "field_name": {
      "value": <값>,
      "source": "GEMINI_INFERRED",
      "confidence": "LOW" | "MED",
      "reasoning": "추론 근거"
    }
  },
  "discrepancies": [
    {
      "field": "필드명",
      "issue": "문제 설명",
      "original_value": <원본 값>,
      "suggested_action": "수정 권고"
    }
  ],
  "validation_notes": "전반적인 검증 소견"
}"""

    def _build_user_prompt(
        self,
        perplexity_result: dict,
        corp_name: str,
        industry_name: str,
    ) -> str:
        """검증 사용자 프롬프트 생성"""
        return f"""## 검증 대상
기업명: {corp_name}
업종: {industry_name}

## Perplexity 검색 결과
{json.dumps(perplexity_result, ensure_ascii=False, indent=2)}

위 검색 결과를 검증하고, 누락된 필드를 보완해주세요."""


# Singleton instance
_gemini_adapter: Optional[GeminiAdapter] = None


def get_gemini_adapter() -> GeminiAdapter:
    """Gemini Adapter 싱글톤 인스턴스 반환"""
    global _gemini_adapter
    if _gemini_adapter is None:
        _gemini_adapter = GeminiAdapter()
    return _gemini_adapter
