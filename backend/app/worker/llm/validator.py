"""
OpenAI Validator for Corp Profile

v2.0 Layer 2: OpenAI 검증 전용 서비스
- Hallucination 검증
- 범위 검증 (숫자, 비율)
- 내부 일관성 검증
- Confidence Scoring

Note: OpenAI는 검색 기능이 없으므로 검증만 수행
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """검증 결과 심각도"""
    ERROR = "ERROR"      # 치명적 오류 (데이터 사용 불가)
    WARNING = "WARNING"  # 경고 (데이터 사용 가능하나 주의)
    INFO = "INFO"        # 정보 (참고용)


class ConfidenceLevel(str, Enum):
    """신뢰도 레벨"""
    HIGH = "HIGH"      # 90%+ 확신
    MEDIUM = "MEDIUM"  # 60-90% 확신
    LOW = "LOW"        # 60% 미만


@dataclass
class ValidationIssue:
    """검증 이슈"""
    field_name: str
    severity: ValidationSeverity
    message: str
    original_value: Any = None
    suggested_value: Any = None


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    confidence: ConfidenceLevel
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_profile: dict = field(default_factory=dict)
    validation_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence.value,
            "issues": [
                {
                    "field_name": i.field_name,
                    "severity": i.severity.value,
                    "message": i.message,
                    "original_value": i.original_value,
                    "suggested_value": i.suggested_value,
                }
                for i in self.issues
            ],
            "issue_counts": {
                "errors": len([i for i in self.issues if i.severity == ValidationSeverity.ERROR]),
                "warnings": len([i for i in self.issues if i.severity == ValidationSeverity.WARNING]),
            },
            "validation_metadata": self.validation_metadata,
        }


class OpenAIValidator:
    """
    OpenAI 기반 프로필 검증기

    v2.0 Layer 2 역할:
    - Hallucination 검증 (비정상 패턴 탐지)
    - 범위 검증 (숫자/비율 필드)
    - 내부 일관성 검증 (필드 간 논리 체크)
    - Confidence Scoring

    Note: 검색 기능 없음 - 검증만 수행
    """

    # 필드별 범위 규칙
    RANGE_RULES = {
        "revenue_krw": {"min": 1_000_000, "max": 100_000_000_000_000},  # 100만원 ~ 100조원
        "export_ratio_pct": {"min": 0, "max": 100},
        "employee_count": {"min": 1, "max": 1_000_000},
        "founded_year": {"min": 1900, "max": 2026},
        "domestic_ratio_pct": {"min": 0, "max": 100},
    }

    # 필수 필드
    REQUIRED_FIELDS = ["corp_name", "industry_code", "industry_name"]

    # Hallucination 탐지 패턴 (의심스러운 값)
    SUSPICIOUS_PATTERNS = [
        "I don't know",
        "I'm not sure",
        "cannot find",
        "no information",
        "N/A",
        "TBD",
        "unknown",
        "데이터 없음",
        "확인 불가",
        "정보 없음",
    ]

    def __init__(self):
        self._openai_client = None

    def validate(
        self,
        profile: dict,
        corp_name: str,
        industry_name: str,
        source: str = "UNKNOWN",
    ) -> ValidationResult:
        """
        프로필 검증 수행

        Args:
            profile: 검증할 프로필 딕셔너리
            corp_name: 기업명
            industry_name: 업종명
            source: 데이터 소스 (PERPLEXITY, GEMINI_FALLBACK 등)

        Returns:
            ValidationResult: 검증 결과
        """
        issues = []
        validated_profile = profile.copy() if profile else {}

        # 1. 필수 필드 검증
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in validated_profile or not validated_profile[field_name]:
                issues.append(ValidationIssue(
                    field_name=field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"필수 필드 누락: {field_name}",
                ))

        # 2. 범위 검증
        for field_name, rules in self.RANGE_RULES.items():
            if field_name in validated_profile and validated_profile[field_name] is not None:
                value = validated_profile[field_name]
                try:
                    num_value = float(value)
                    if num_value < rules["min"] or num_value > rules["max"]:
                        issues.append(ValidationIssue(
                            field_name=field_name,
                            severity=ValidationSeverity.WARNING,
                            message=f"범위 초과: {num_value} (허용: {rules['min']} ~ {rules['max']})",
                            original_value=value,
                            suggested_value=max(rules["min"], min(rules["max"], num_value)),
                        ))
                        # 범위 내로 조정
                        validated_profile[field_name] = max(rules["min"], min(rules["max"], num_value))
                except (ValueError, TypeError):
                    issues.append(ValidationIssue(
                        field_name=field_name,
                        severity=ValidationSeverity.WARNING,
                        message=f"숫자 변환 실패: {value}",
                        original_value=value,
                    ))

        # 3. Hallucination 탐지
        for field_name, value in validated_profile.items():
            if isinstance(value, str):
                for pattern in self.SUSPICIOUS_PATTERNS:
                    if pattern.lower() in value.lower():
                        issues.append(ValidationIssue(
                            field_name=field_name,
                            severity=ValidationSeverity.WARNING,
                            message=f"의심스러운 패턴 탐지: '{pattern}'",
                            original_value=value,
                        ))
                        # 의심스러운 값은 None으로 설정
                        validated_profile[field_name] = None
                        break

        # 4. 내부 일관성 검증
        consistency_issues = self._validate_consistency(validated_profile)
        issues.extend(consistency_issues)

        # 5. Confidence 계산
        confidence = self._calculate_confidence(validated_profile, issues, source)

        # 6. 유효성 판정
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        is_valid = error_count == 0

        logger.info(
            f"[Validator] {corp_name}: valid={is_valid}, confidence={confidence.value}, "
            f"errors={error_count}, warnings={len(issues) - error_count}"
        )

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            validated_profile=validated_profile,
            validation_metadata={
                "source": source,
                "corp_name": corp_name,
                "industry_name": industry_name,
                "total_fields": len([k for k in validated_profile.keys() if not k.startswith("_")]),
                "valid_fields": len([
                    k for k, v in validated_profile.items()
                    if not k.startswith("_") and v is not None
                ]),
            },
        )

    def _validate_consistency(self, profile: dict) -> list[ValidationIssue]:
        """내부 일관성 검증"""
        issues = []

        # 수출 비중 + 내수 비중 = 100%
        export_ratio = profile.get("export_ratio_pct")
        domestic_ratio = profile.get("domestic_ratio_pct")
        if export_ratio is not None and domestic_ratio is not None:
            try:
                total = float(export_ratio) + float(domestic_ratio)
                if abs(total - 100) > 5:  # 5% 오차 허용
                    issues.append(ValidationIssue(
                        field_name="export_ratio_pct + domestic_ratio_pct",
                        severity=ValidationSeverity.WARNING,
                        message=f"비율 합계 불일치: {total}% (예상: 100%)",
                        original_value={"export": export_ratio, "domestic": domestic_ratio},
                    ))
            except (ValueError, TypeError):
                pass

        # 수출 비중 있으면 해외 사업 정보도 있어야 함 (논리적 일관성)
        if export_ratio is not None and float(export_ratio) > 30:
            overseas = profile.get("overseas_business") or profile.get("overseas_operations")
            country_exposure = profile.get("country_exposure")
            if not overseas and not country_exposure:
                issues.append(ValidationIssue(
                    field_name="overseas_business",
                    severity=ValidationSeverity.INFO,
                    message=f"수출 비중 {export_ratio}%인데 해외 사업 정보 없음",
                ))

        return issues

    def _calculate_confidence(
        self,
        profile: dict,
        issues: list[ValidationIssue],
        source: str,
    ) -> ConfidenceLevel:
        """Confidence 계산"""
        # 기본 점수
        score = 100

        # 에러 개수만큼 감점
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == ValidationSeverity.WARNING])
        score -= error_count * 20
        score -= warning_count * 5

        # 필드 수에 따른 가점/감점
        total_fields = len([k for k in profile.keys() if not k.startswith("_")])
        valid_fields = len([
            k for k, v in profile.items()
            if not k.startswith("_") and v is not None
        ])

        if valid_fields < 5:
            score -= 30
        elif valid_fields < 10:
            score -= 15
        elif valid_fields >= 15:
            score += 10

        # 소스별 조정
        if source == "PERPLEXITY":
            score += 5  # Perplexity는 신뢰도 약간 높음
        elif source == "GEMINI_FALLBACK":
            score -= 5  # Fallback은 신뢰도 약간 낮음

        # 최종 레벨 결정
        if score >= 90:
            return ConfidenceLevel.HIGH
        elif score >= 60:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    async def validate_with_llm(
        self,
        profile: dict,
        corp_name: str,
        industry_name: str,
    ) -> ValidationResult:
        """
        OpenAI LLM을 사용한 고급 검증 (선택적)

        Note: 추가 비용 발생, 필요 시에만 사용
        """
        # 기본 검증 먼저 수행
        basic_result = self.validate(profile, corp_name, industry_name)

        # LLM 검증은 WARNING 이상일 때만 수행 (비용 절약)
        if len(basic_result.issues) == 0:
            return basic_result

        try:
            import litellm

            prompt = f"""다음 기업 프로필 데이터의 정확성을 검증해주세요.

기업명: {corp_name}
업종: {industry_name}

프로필 데이터:
{json.dumps(profile, ensure_ascii=False, indent=2)}

검증 기준:
1. 숫자 값이 해당 업종에 합리적인지
2. 텍스트 내용이 해당 기업과 관련 있는지
3. 필드 간 논리적 일관성이 있는지

JSON 형식으로 응답:
{{
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "issues": [
    {{"field": "필드명", "severity": "ERROR|WARNING|INFO", "message": "설명"}}
  ],
  "overall_assessment": "전체 평가 한 줄"
}}"""

            response = await litellm.acompletion(
                model="gpt-4o-mini",  # 비용 효율적인 모델 사용
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            llm_result = json.loads(content)

            # LLM 결과 병합
            for issue_data in llm_result.get("issues", []):
                basic_result.issues.append(ValidationIssue(
                    field_name=issue_data.get("field", "unknown"),
                    severity=ValidationSeverity(issue_data.get("severity", "INFO")),
                    message=f"[LLM] {issue_data.get('message', '')}",
                ))

            # Confidence 재조정
            llm_confidence = llm_result.get("confidence", "MEDIUM")
            if llm_confidence == "LOW" and basic_result.confidence == ConfidenceLevel.HIGH:
                basic_result.confidence = ConfidenceLevel.MEDIUM
            elif llm_confidence == "HIGH" and basic_result.confidence == ConfidenceLevel.LOW:
                basic_result.confidence = ConfidenceLevel.MEDIUM

            basic_result.validation_metadata["llm_validated"] = True
            basic_result.validation_metadata["llm_assessment"] = llm_result.get("overall_assessment")

        except Exception as e:
            logger.warning(f"[Validator] LLM validation failed: {e}")
            basic_result.validation_metadata["llm_error"] = str(e)

        return basic_result


# ============================================================
# Singleton
# ============================================================

_validator_instance: Optional[OpenAIValidator] = None


def get_validator() -> OpenAIValidator:
    """OpenAIValidator 싱글톤"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = OpenAIValidator()
    return _validator_instance


def reset_validator() -> None:
    """싱글톤 리셋 (테스트용)"""
    global _validator_instance
    _validator_instance = None
