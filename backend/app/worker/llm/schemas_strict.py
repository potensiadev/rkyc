"""
Strict Signal Schemas (Sprint 1)

Pydantic models for strict signal validation with:
- Required fields enforcement
- Enum validation
- retrieval_confidence tracking
- Evidence validation
- Length constraints

Author: Silicon Valley Senior PM
Version: 1.0.0
Date: 2026-02-08
"""

from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import re


# =============================================================================
# ENUMS
# =============================================================================

class SignalType(str, Enum):
    DIRECT = "DIRECT"
    INDUSTRY = "INDUSTRY"
    ENVIRONMENT = "ENVIRONMENT"


class EventType(str, Enum):
    # DIRECT event types (8)
    KYC_REFRESH = "KYC_REFRESH"
    INTERNAL_RISK_GRADE_CHANGE = "INTERNAL_RISK_GRADE_CHANGE"
    OVERDUE_FLAG_ON = "OVERDUE_FLAG_ON"
    LOAN_EXPOSURE_CHANGE = "LOAN_EXPOSURE_CHANGE"
    COLLATERAL_CHANGE = "COLLATERAL_CHANGE"
    OWNERSHIP_CHANGE = "OWNERSHIP_CHANGE"
    GOVERNANCE_CHANGE = "GOVERNANCE_CHANGE"
    FINANCIAL_STATEMENT_UPDATE = "FINANCIAL_STATEMENT_UPDATE"
    # INDUSTRY event type (1)
    INDUSTRY_SHOCK = "INDUSTRY_SHOCK"
    # ENVIRONMENT event type (1)
    POLICY_REGULATION_CHANGE = "POLICY_REGULATION_CHANGE"


class ImpactDirection(str, Enum):
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    NEUTRAL = "NEUTRAL"


class ImpactStrength(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class RetrievalConfidence(str, Enum):
    """
    Indicates how the information was extracted from source.

    - VERBATIM: Copied directly from source (highest trust)
    - PARAPHRASED: Rephrased for clarity but factually same
    - INFERRED: Derived from context (requires confidence_reason)
    """
    VERBATIM = "VERBATIM"
    PARAPHRASED = "PARAPHRASED"
    INFERRED = "INFERRED"


class EvidenceType(str, Enum):
    INTERNAL_FIELD = "INTERNAL_FIELD"
    DOC = "DOC"
    EXTERNAL = "EXTERNAL"


class RefType(str, Enum):
    SNAPSHOT_KEYPATH = "SNAPSHOT_KEYPATH"
    DOC_PAGE = "DOC_PAGE"
    URL = "URL"


# =============================================================================
# FORBIDDEN PATTERNS
# =============================================================================

FORBIDDEN_PATTERNS = [
    # 단정적 표현
    "반드시", "무조건", "확실히", "틀림없이", "분명히",
    "당연히", "필연적으로", "절대적으로", "명백히",
    # 예측/전망
    "예상됨", "예상된다", "전망됨", "전망된다",
    "예측됨", "예측된다",
    "~할 것이다", "~일 것이다",
    # 추정
    "추정됨", "추정된다", "것으로 보인다", "것으로 보임",
    # 불확실성
    "약 ", "대략 ", "정도 ", "가량 ", "내외 ",
    "일반적으로", "통상적으로",
    # 즉시성
    "즉시", "당장", "시급히", "긴급",
    # 과장
    "매우 심각", "극심한", "엄청난",
    "급격히", "급속히", "폭발적",
]


def contains_forbidden_pattern(text: str) -> Optional[str]:
    """Check if text contains any forbidden pattern. Returns matched pattern or None."""
    text_lower = text.lower() if text else ""
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in text_lower:
            return pattern
    return None


# =============================================================================
# EVIDENCE SCHEMA
# =============================================================================

class EvidenceStrictSchema(BaseModel):
    """
    Strict evidence schema with required fields.

    All evidence must have:
    - evidence_type: Where the data came from
    - ref_type: How to reference the source
    - ref_value: The actual reference (keypath, URL, page)
    - snippet: Extracted text from source
    """
    evidence_type: EvidenceType = Field(
        ...,
        description="Type of evidence source"
    )
    ref_type: RefType = Field(
        ...,
        description="Type of reference"
    )
    ref_value: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Reference value (keypath, URL, or page number)"
    )
    snippet: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Extracted text from source (20-100 chars recommended)"
    )
    source_credibility: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Source credibility score (0-100)"
    )

    @field_validator('ref_value')
    @classmethod
    def validate_ref_value(cls, v: str, info) -> str:
        """Validate ref_value based on ref_type."""
        # ref_type is available via info.data for cross-field validation
        # But we'll do basic validation here
        if not v or not v.strip():
            raise ValueError("ref_value cannot be empty")
        return v.strip()

    @field_validator('snippet')
    @classmethod
    def validate_snippet(cls, v: str) -> str:
        """Validate snippet is not empty and reasonable length."""
        if not v or len(v.strip()) < 10:
            raise ValueError("snippet must be at least 10 characters")
        return v.strip()


# =============================================================================
# QUANTITATIVE DATA SCHEMA
# =============================================================================

class QuantitativeDataSchema(BaseModel):
    """
    Optional quantitative data extracted from evidence.

    Helps track which numbers came from which sources.
    """
    metric: str = Field(
        ...,
        max_length=50,
        description="Metric name (e.g., 매출액, 영업이익, 연체금액)"
    )
    value: float = Field(
        ...,
        description="Numeric value"
    )
    unit: str = Field(
        ...,
        max_length=20,
        description="Unit (e.g., 억원, %, 일)"
    )
    source: str = Field(
        ...,
        max_length=50,
        description="Source reference (e.g., evidence[0])"
    )


# =============================================================================
# SIGNAL SCHEMA
# =============================================================================

class SignalStrictSchema(BaseModel):
    """
    Strict signal schema with all required fields and validation.

    Key features:
    - All required fields enforced
    - Enum validation
    - retrieval_confidence tracking
    - Length constraints
    - Forbidden pattern checking
    - Cross-field validation
    """
    signal_type: SignalType = Field(
        ...,
        description="Type of signal (DIRECT/INDUSTRY/ENVIRONMENT)"
    )
    event_type: EventType = Field(
        ...,
        description="Specific event type (10 types total)"
    )
    impact_direction: ImpactDirection = Field(
        ...,
        description="Direction of impact (RISK/OPPORTUNITY/NEUTRAL)"
    )
    impact_strength: ImpactStrength = Field(
        ...,
        description="Strength of impact (HIGH/MED/LOW)"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level based on source tier"
    )
    retrieval_confidence: RetrievalConfidence = Field(
        ...,
        description="How information was extracted (VERBATIM/PARAPHRASED/INFERRED)"
    )
    confidence_reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Required when retrieval_confidence is INFERRED"
    )
    title: str = Field(
        ...,
        min_length=10,
        max_length=50,
        description="Signal title (max 50 chars, must include corp_name)"
    )
    summary: str = Field(
        ...,
        min_length=50,
        max_length=300,
        description="Signal summary (80-200 chars, must include quantitative info)"
    )
    evidence: List[EvidenceStrictSchema] = Field(
        ...,
        min_length=1,
        description="At least 1 evidence required"
    )
    quantitative_data: Optional[List[QuantitativeDataSchema]] = Field(
        None,
        description="Optional quantitative data tracking"
    )

    # Metadata fields (auto-filled during processing)
    corp_id: Optional[str] = None
    corp_name: Optional[str] = None
    snapshot_version: Optional[int] = None
    event_signature: Optional[str] = None
    extracted_by: Optional[str] = None
    needs_review: Optional[bool] = None
    review_reason: Optional[str] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title doesn't contain forbidden patterns."""
        forbidden = contains_forbidden_pattern(v)
        if forbidden:
            raise ValueError(f"Title contains forbidden pattern: '{forbidden}'")
        return v.strip()

    @field_validator('summary')
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Validate summary doesn't contain forbidden patterns."""
        forbidden = contains_forbidden_pattern(v)
        if forbidden:
            raise ValueError(f"Summary contains forbidden pattern: '{forbidden}'")
        return v.strip()

    @model_validator(mode='after')
    def validate_cross_fields(self) -> 'SignalStrictSchema':
        """Cross-field validation."""

        # 1. INFERRED requires confidence_reason
        if self.retrieval_confidence == RetrievalConfidence.INFERRED:
            if not self.confidence_reason:
                raise ValueError(
                    "confidence_reason is required when retrieval_confidence is INFERRED"
                )

        # 2. Validate signal_type matches event_type
        direct_events = {
            EventType.KYC_REFRESH,
            EventType.INTERNAL_RISK_GRADE_CHANGE,
            EventType.OVERDUE_FLAG_ON,
            EventType.LOAN_EXPOSURE_CHANGE,
            EventType.COLLATERAL_CHANGE,
            EventType.OWNERSHIP_CHANGE,
            EventType.GOVERNANCE_CHANGE,
            EventType.FINANCIAL_STATEMENT_UPDATE,
        }
        industry_events = {EventType.INDUSTRY_SHOCK}
        environment_events = {EventType.POLICY_REGULATION_CHANGE}

        if self.signal_type == SignalType.DIRECT:
            if self.event_type not in direct_events:
                raise ValueError(
                    f"DIRECT signal cannot have event_type {self.event_type}"
                )
        elif self.signal_type == SignalType.INDUSTRY:
            if self.event_type not in industry_events:
                raise ValueError(
                    f"INDUSTRY signal must have event_type INDUSTRY_SHOCK"
                )
        elif self.signal_type == SignalType.ENVIRONMENT:
            if self.event_type not in environment_events:
                raise ValueError(
                    f"ENVIRONMENT signal must have event_type POLICY_REGULATION_CHANGE"
                )

        # 3. HIGH confidence requires VERBATIM or high-tier source
        if self.confidence == ConfidenceLevel.HIGH:
            if self.retrieval_confidence == RetrievalConfidence.INFERRED:
                raise ValueError(
                    "HIGH confidence cannot have INFERRED retrieval_confidence"
                )

        return self

    def check_corp_name_in_text(self, corp_name: str) -> list[str]:
        """Check if corp_name appears in title and summary. Returns list of issues."""
        issues = []
        if corp_name:
            if corp_name not in self.title:
                issues.append(f"Corp name '{corp_name}' not in title")
            if corp_name not in self.summary:
                issues.append(f"Corp name '{corp_name}' not in summary")
        return issues


# =============================================================================
# SIGNAL LIST SCHEMA
# =============================================================================

class SignalsResponseSchema(BaseModel):
    """
    Response schema containing list of signals.

    Empty signals list is valid when no signals detected.
    """
    signals: List[SignalStrictSchema] = Field(
        default_factory=list,
        description="List of extracted signals (empty if none)"
    )


# =============================================================================
# VALIDATION HELPER
# =============================================================================

def validate_signal_dict(
    signal_dict: dict,
    context: dict,
) -> tuple[bool, list[str], Optional[SignalStrictSchema]]:
    """
    Validate a signal dictionary and return validation result.

    Args:
        signal_dict: Raw signal dictionary from LLM
        context: Context with corp_name, corp_id, etc.

    Returns:
        tuple of (is_valid, errors, validated_signal or None)
    """
    errors = []

    try:
        # Try to parse with Pydantic
        signal = SignalStrictSchema(**signal_dict)

        # Additional checks
        corp_name = context.get("corp_name", "")
        corp_name_issues = signal.check_corp_name_in_text(corp_name)
        if corp_name_issues:
            errors.extend(corp_name_issues)

        # Fill metadata
        signal.corp_id = context.get("corp_id")
        signal.corp_name = corp_name
        signal.snapshot_version = context.get("snapshot_version")

        if errors:
            return False, errors, None

        return True, [], signal

    except Exception as e:
        errors.append(str(e))
        return False, errors, None


def validate_signals_response(
    response_dict: dict,
    context: dict,
) -> tuple[list[SignalStrictSchema], list[dict]]:
    """
    Validate a signals response and return valid signals + rejected signals.

    Args:
        response_dict: Raw response dictionary from LLM ({"signals": [...]})
        context: Context with corp_name, corp_id, etc.

    Returns:
        tuple of (valid_signals, rejected_signals with reasons)
    """
    valid_signals = []
    rejected = []

    signals_list = response_dict.get("signals", [])

    for i, signal_dict in enumerate(signals_list):
        is_valid, errors, validated = validate_signal_dict(signal_dict, context)

        if is_valid and validated:
            valid_signals.append(validated)
        else:
            rejected.append({
                "index": i,
                "signal": signal_dict,
                "errors": errors,
            })

    return valid_signals, rejected


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Enums
    "SignalType",
    "EventType",
    "ImpactDirection",
    "ImpactStrength",
    "ConfidenceLevel",
    "RetrievalConfidence",
    "EvidenceType",
    "RefType",
    # Schemas
    "EvidenceStrictSchema",
    "QuantitativeDataSchema",
    "SignalStrictSchema",
    "SignalsResponseSchema",
    # Functions
    "validate_signal_dict",
    "validate_signals_response",
    "contains_forbidden_pattern",
    # Constants
    "FORBIDDEN_PATTERNS",
]
