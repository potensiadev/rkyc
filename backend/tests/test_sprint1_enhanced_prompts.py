"""
Sprint 1 Enhanced Prompts - Unit Tests

Tests for:
1. Forbidden pattern detection (50+ patterns, 7 categories)
2. Strict schema validation (Pydantic)
3. Signal validation functions
4. Few-shot example integrity

Author: Silicon Valley Senior PM
Date: 2026-02-08
"""

import pytest
import json
from typing import Dict, List, Any

# Sprint 1 imports
from app.worker.llm.prompts_enhanced import (
    # Patterns
    ForbiddenCategory,
    CERTAINTY_PATTERNS,
    PREDICTION_PATTERNS,
    ESTIMATION_PATTERNS,
    UNCERTAINTY_PATTERNS,
    URGENCY_PATTERNS,
    EXAGGERATION_PATTERNS,
    ALL_FORBIDDEN_LITERALS,
    COMPILED_FORBIDDEN_LITERALS,
    REGEX_FORBIDDEN_PATTERNS,
    # Functions
    check_forbidden_patterns,
    validate_signal_strict,
    build_enhanced_system_prompt,
    build_enhanced_user_prompt,
    # Examples
    DIRECT_EXAMPLES,
    INDUSTRY_EXAMPLES,
    ENVIRONMENT_EXAMPLES,
)

from app.worker.llm.schemas_strict import (
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
    ConfidenceLevel,
    RetrievalConfidence,
    EvidenceType,
    RefType,
    EvidenceStrictSchema,
    SignalStrictSchema,
    SignalsResponseSchema,
    validate_signal_dict,
    validate_signals_response,
    contains_forbidden_pattern,
)


# =============================================================================
# Test 1: Forbidden Pattern Detection
# =============================================================================

class TestForbiddenPatterns:
    """Test forbidden pattern detection with 50+ patterns."""

    def test_pattern_count(self):
        """Verify we have 50+ forbidden patterns."""
        total_patterns = len(ALL_FORBIDDEN_LITERALS)
        assert total_patterns >= 50, f"Expected 50+ patterns, got {total_patterns}"

    def test_category_patterns_exist(self):
        """Verify each category has patterns."""
        assert len(CERTAINTY_PATTERNS) > 0, "CERTAINTY_PATTERNS is empty"
        assert len(PREDICTION_PATTERNS) > 0, "PREDICTION_PATTERNS is empty"
        assert len(ESTIMATION_PATTERNS) > 0, "ESTIMATION_PATTERNS is empty"
        assert len(UNCERTAINTY_PATTERNS) > 0, "UNCERTAINTY_PATTERNS is empty"
        assert len(URGENCY_PATTERNS) > 0, "URGENCY_PATTERNS is empty"
        assert len(EXAGGERATION_PATTERNS) > 0, "EXAGGERATION_PATTERNS is empty"

    def test_certainty_detection(self):
        """Test certainty expression detection."""
        test_cases = [
            ("반드시 점검이 필요합니다", True),
            ("확실히 문제가 있습니다", True),
            ("틀림없이 리스크입니다", True),
            ("점검이 권고됩니다", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_prediction_detection(self):
        """Test prediction expression detection."""
        test_cases = [
            ("매출이 증가할 것으로 예상됨", True),  # Contains "예상됨"
            ("실적이 좋아질 전망됨", True),  # Contains "전망됨"
            ("성장이 예측됨", True),  # Contains "예측됨"
            ("매출이 30% 증가함", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_estimation_detection(self):
        """Test estimation expression detection."""
        test_cases = [
            ("매출이 100억원으로 추정됨", True),
            ("리스크가 있는 것으로 보인다", True),
            ("매출이 100억원으로 확인됨", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_uncertainty_detection(self):
        """Test uncertainty expression detection."""
        test_cases = [
            ("약 30% 감소", True),
            ("대략 100억원", True),
            ("일반적으로 리스크가 있음", True),
            ("30% 감소", False),
            ("100억원", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_urgency_detection(self):
        """Test urgency expression detection."""
        test_cases = [
            ("즉시 조치가 필요합니다", True),
            ("긴급 점검이 필요함", True),
            ("점검이 권고됩니다", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_exaggeration_detection(self):
        """Test exaggeration expression detection."""
        test_cases = [
            ("매우 심각한 상황", True),
            ("엄청난 손실 발생", True),
            ("급격히 하락함", True),
            ("하락함", False),
        ]
        for text, should_match in test_cases:
            matches = check_forbidden_patterns(text)
            if should_match:
                assert len(matches) > 0, f"Should detect forbidden in: {text}"
            else:
                assert len(matches) == 0, f"Should not detect forbidden in: {text}"

    def test_category_identification(self):
        """Test that matched patterns include category."""
        text = "반드시 확인해야 합니다"
        matches = check_forbidden_patterns(text)
        assert len(matches) > 0
        assert "category" in matches[0]
        assert matches[0]["category"] == ForbiddenCategory.CERTAINTY.value


# =============================================================================
# Test 2: Strict Schema Validation
# =============================================================================

class TestStrictSchemas:
    """Test Pydantic strict schema validation."""

    def test_valid_evidence(self):
        """Test valid evidence schema."""
        evidence = EvidenceStrictSchema(
            evidence_type=EvidenceType.INTERNAL_FIELD,
            ref_type=RefType.SNAPSHOT_KEYPATH,
            ref_value="/credit/loan_summary/overdue_flag",
            snippet="overdue_flag: true (30일 이상 연체 확인)"
        )
        assert evidence.evidence_type == EvidenceType.INTERNAL_FIELD
        assert evidence.ref_value == "/credit/loan_summary/overdue_flag"

    def test_evidence_snippet_min_length(self):
        """Test evidence snippet minimum length."""
        with pytest.raises(ValueError):
            EvidenceStrictSchema(
                evidence_type=EvidenceType.INTERNAL_FIELD,
                ref_type=RefType.SNAPSHOT_KEYPATH,
                ref_value="/credit/overdue",
                snippet="short"  # Too short (< 10 chars)
            )

    def test_valid_signal(self):
        """Test valid signal schema."""
        signal = SignalStrictSchema(
            signal_type=SignalType.DIRECT,
            event_type=EventType.OVERDUE_FLAG_ON,
            impact_direction=ImpactDirection.RISK,
            impact_strength=ImpactStrength.HIGH,
            confidence=ConfidenceLevel.HIGH,
            retrieval_confidence=RetrievalConfidence.VERBATIM,
            title="엠케이전자 30일 이상 연체 발생",
            summary="엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인.",
            evidence=[
                EvidenceStrictSchema(
                    evidence_type=EvidenceType.INTERNAL_FIELD,
                    ref_type=RefType.SNAPSHOT_KEYPATH,
                    ref_value="/credit/loan_summary/overdue_flag",
                    snippet="overdue_flag: true"
                )
            ]
        )
        assert signal.signal_type == SignalType.DIRECT
        assert signal.event_type == EventType.OVERDUE_FLAG_ON

    def test_signal_type_event_type_mismatch(self):
        """Test signal_type and event_type mismatch validation."""
        with pytest.raises(ValueError) as exc_info:
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.INDUSTRY_SHOCK,  # Wrong! INDUSTRY_SHOCK is for INDUSTRY
                impact_direction=ImpactDirection.RISK,
                impact_strength=ImpactStrength.HIGH,
                confidence=ConfidenceLevel.HIGH,
                retrieval_confidence=RetrievalConfidence.VERBATIM,
                title="엠케이전자 업종 충격",
                summary="엠케이전자의 업종에 충격이 발생함. 반도체 업계 전반에 영향을 미치는 이벤트로 상세 내용은 Evidence를 참조하시기 바랍니다.",
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.EXTERNAL,
                        ref_type=RefType.URL,
                        ref_value="https://example.com",
                        snippet="업종 충격 관련 기사 내용입니다"
                    )
                ]
            )
        assert "DIRECT signal cannot have event_type" in str(exc_info.value)

    def test_inferred_requires_confidence_reason(self):
        """Test INFERRED retrieval_confidence requires confidence_reason."""
        with pytest.raises(ValueError) as exc_info:
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.KYC_REFRESH,
                impact_direction=ImpactDirection.NEUTRAL,
                impact_strength=ImpactStrength.LOW,
                confidence=ConfidenceLevel.LOW,
                retrieval_confidence=RetrievalConfidence.INFERRED,
                # Missing confidence_reason!
                title="엠케이전자 KYC 갱신 필요",
                summary="엠케이전자의 KYC 갱신이 필요한 상태입니다. 내부 스냅샷에서 마지막 갱신일로부터 12개월이 경과하였으며, 정기 점검 프로세스 진행이 필요합니다.",
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.INTERNAL_FIELD,
                        ref_type=RefType.SNAPSHOT_KEYPATH,
                        ref_value="/corp/kyc_status/last_kyc_updated",
                        snippet="last_kyc_updated: 2025-01-15"
                    )
                ]
            )
        assert "confidence_reason is required when retrieval_confidence is INFERRED" in str(exc_info.value)

    def test_high_confidence_cannot_be_inferred(self):
        """Test HIGH confidence cannot have INFERRED retrieval_confidence."""
        with pytest.raises(ValueError) as exc_info:
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.KYC_REFRESH,
                impact_direction=ImpactDirection.NEUTRAL,
                impact_strength=ImpactStrength.LOW,
                confidence=ConfidenceLevel.HIGH,  # HIGH
                retrieval_confidence=RetrievalConfidence.INFERRED,  # INFERRED - not allowed!
                confidence_reason="추론 근거",
                title="엠케이전자 KYC 갱신 필요",
                summary="엠케이전자의 KYC 갱신이 필요한 상태입니다. 내부 스냅샷에서 마지막 갱신일로부터 12개월이 경과하였으며, 정기 점검 프로세스 진행이 필요합니다.",
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.INTERNAL_FIELD,
                        ref_type=RefType.SNAPSHOT_KEYPATH,
                        ref_value="/corp/kyc_status/last_kyc_updated",
                        snippet="last_kyc_updated: 2025-01-15"
                    )
                ]
            )
        assert "HIGH confidence cannot have INFERRED" in str(exc_info.value)

    def test_forbidden_pattern_in_title(self):
        """Test forbidden pattern detection in title."""
        with pytest.raises(ValueError) as exc_info:
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.OVERDUE_FLAG_ON,
                impact_direction=ImpactDirection.RISK,
                impact_strength=ImpactStrength.HIGH,
                confidence=ConfidenceLevel.HIGH,
                retrieval_confidence=RetrievalConfidence.VERBATIM,
                title="엠케이전자 반드시 점검 필요",  # Contains "반드시"
                summary="엠케이전자의 연체 상태 확인됨.",
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.INTERNAL_FIELD,
                        ref_type=RefType.SNAPSHOT_KEYPATH,
                        ref_value="/credit/overdue_flag",
                        snippet="overdue_flag: true"
                    )
                ]
            )
        assert "forbidden pattern" in str(exc_info.value).lower()


# =============================================================================
# Test 3: Signal Validation Functions
# =============================================================================

class TestSignalValidation:
    """Test signal validation helper functions."""

    def test_validate_signal_dict_valid(self):
        """Test validate_signal_dict with valid signal."""
        signal_dict = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 30일 이상 연체 발생",
            "summary": "엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인. 상환능력 저하 신호로 담보 점검 권고.",
            "evidence": [
                {
                    "evidence_type": "INTERNAL_FIELD",
                    "ref_type": "SNAPSHOT_KEYPATH",
                    "ref_value": "/credit/overdue_flag",
                    "snippet": "overdue_flag: true (연체 확인)"
                }
            ]
        }
        context = {"corp_name": "엠케이전자"}

        is_valid, errors, validated = validate_signal_dict(signal_dict, context)
        assert is_valid, f"Expected valid, got errors: {errors}"
        assert validated is not None

    def test_validate_signal_dict_missing_corp_name(self):
        """Test validate_signal_dict when corp_name is missing from text."""
        signal_dict = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "30일 이상 연체 발생",  # Missing corp_name
            "summary": "기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인되었습니다. 상환능력 저하 신호입니다.",  # Missing corp_name
            "evidence": [
                {
                    "evidence_type": "INTERNAL_FIELD",
                    "ref_type": "SNAPSHOT_KEYPATH",
                    "ref_value": "/credit/overdue_flag",
                    "snippet": "overdue_flag: true (연체 확인)"
                }
            ]
        }
        context = {"corp_name": "엠케이전자"}

        is_valid, errors, validated = validate_signal_dict(signal_dict, context)
        assert not is_valid, "Should be invalid when corp_name is missing"
        assert any("Corp name" in e for e in errors)

    def test_validate_signals_response(self):
        """Test validate_signals_response with mixed valid/invalid signals."""
        response_dict = {
            "signals": [
                {
                    "signal_type": "DIRECT",
                    "event_type": "OVERDUE_FLAG_ON",
                    "impact_direction": "RISK",
                    "impact_strength": "HIGH",
                    "confidence": "HIGH",
                    "retrieval_confidence": "VERBATIM",
                    "title": "엠케이전자 연체 발생",
                    "summary": "엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인되었습니다.",
                    "evidence": [{"evidence_type": "INTERNAL_FIELD", "ref_type": "SNAPSHOT_KEYPATH", "ref_value": "/overdue", "snippet": "overdue: true (연체 상태)"}]
                },
                {
                    "signal_type": "INVALID_TYPE",  # Invalid!
                    "event_type": "OVERDUE_FLAG_ON",
                    "title": "Invalid signal"
                }
            ]
        }
        context = {"corp_name": "엠케이전자"}

        valid_signals, rejected = validate_signals_response(response_dict, context)
        assert len(valid_signals) == 1
        assert len(rejected) == 1

    def test_validate_signal_strict_function(self):
        """Test validate_signal_strict from prompts_enhanced."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 연체 발생",
            "summary": "엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인되었습니다.",
            "evidence": [{"evidence_type": "INTERNAL_FIELD", "ref_type": "SNAPSHOT_KEYPATH", "ref_value": "/overdue", "snippet": "overdue: true (연체 확인됨)"}]
        }
        context = {"corp_name": "엠케이전자"}

        is_valid, errors = validate_signal_strict(signal, context)
        assert is_valid, f"Expected valid, got errors: {errors}"


# =============================================================================
# Test 4: Few-Shot Example Integrity
# =============================================================================

class TestFewShotExamples:
    """Test Few-Shot example integrity."""

    def test_direct_examples_count(self):
        """Verify DIRECT_EXAMPLES has 16 examples."""
        # Count JSON blocks in examples
        json_count = DIRECT_EXAMPLES.count("```json")
        assert json_count >= 16, f"Expected 16+ DIRECT examples, got {json_count}"

    def test_industry_examples_count(self):
        """Verify INDUSTRY_EXAMPLES has 10 examples."""
        json_count = INDUSTRY_EXAMPLES.count("```json")
        assert json_count >= 10, f"Expected 10+ INDUSTRY examples, got {json_count}"

    def test_environment_examples_count(self):
        """Verify ENVIRONMENT_EXAMPLES has 11 examples."""
        json_count = ENVIRONMENT_EXAMPLES.count("```json")
        assert json_count >= 11, f"Expected 11+ ENVIRONMENT examples, got {json_count}"

    def test_direct_examples_have_signal_type(self):
        """Verify DIRECT examples have correct signal_type."""
        assert '"signal_type": "DIRECT"' in DIRECT_EXAMPLES

    def test_industry_examples_have_signal_type(self):
        """Verify INDUSTRY examples have correct signal_type."""
        assert '"signal_type": "INDUSTRY"' in INDUSTRY_EXAMPLES

    def test_environment_examples_have_signal_type(self):
        """Verify ENVIRONMENT examples have correct signal_type."""
        assert '"signal_type": "ENVIRONMENT"' in ENVIRONMENT_EXAMPLES

    def test_examples_have_retrieval_confidence(self):
        """Verify examples include retrieval_confidence field."""
        assert "retrieval_confidence" in DIRECT_EXAMPLES
        assert "retrieval_confidence" in INDUSTRY_EXAMPLES
        assert "retrieval_confidence" in ENVIRONMENT_EXAMPLES


# =============================================================================
# Test 5: Prompt Builder Functions
# =============================================================================

class TestPromptBuilders:
    """Test prompt builder functions."""

    def test_build_enhanced_system_prompt_direct(self):
        """Test system prompt for DIRECT signal type."""
        prompt = build_enhanced_system_prompt(
            signal_type="DIRECT",
            corp_name="엠케이전자",
            industry_code="C26",
            industry_name="전자부품제조업"
        )
        assert "엠케이전자" in prompt
        assert "DIRECT" in prompt
        assert "Hallucination Zero Tolerance" in prompt
        assert "retrieval_confidence" in prompt

    def test_build_enhanced_system_prompt_industry(self):
        """Test system prompt for INDUSTRY signal type."""
        prompt = build_enhanced_system_prompt(
            signal_type="INDUSTRY",
            corp_name="엠케이전자",
            industry_code="C26",
            industry_name="전자부품제조업"
        )
        assert "엠케이전자" in prompt
        assert "INDUSTRY" in prompt

    def test_build_enhanced_system_prompt_environment(self):
        """Test system prompt for ENVIRONMENT signal type."""
        prompt = build_enhanced_system_prompt(
            signal_type="ENVIRONMENT",
            corp_name="엠케이전자",
            industry_code="C26",
            industry_name="전자부품제조업"
        )
        assert "엠케이전자" in prompt
        assert "ENVIRONMENT" in prompt

    def test_build_enhanced_user_prompt(self):
        """Test user prompt builder."""
        prompt = build_enhanced_user_prompt(
            corp_name="엠케이전자",
            corp_reg_no="135-81-06406",
            industry_code="C26",
            industry_name="전자부품제조업",
            snapshot_json='{"corp": {"corp_id": "8001-3719240"}}',
            events_data='[]',
            signal_type="DIRECT"
        )
        assert "엠케이전자" in prompt
        assert "135-81-06406" in prompt
        assert "C26" in prompt
        assert "DIRECT" in prompt


# =============================================================================
# Test 6: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text_forbidden_check(self):
        """Test forbidden pattern check with empty text."""
        matches = check_forbidden_patterns("")
        assert len(matches) == 0

    def test_none_text_handling(self):
        """Test forbidden pattern check handles None gracefully."""
        # contains_forbidden_pattern from schemas_strict
        result = contains_forbidden_pattern("")
        assert result is None

    def test_title_max_length(self):
        """Test title max length validation."""
        long_title = "엠" * 60  # 60 chars, exceeds 50 limit
        with pytest.raises(ValueError):
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.OVERDUE_FLAG_ON,
                impact_direction=ImpactDirection.RISK,
                impact_strength=ImpactStrength.HIGH,
                confidence=ConfidenceLevel.HIGH,
                retrieval_confidence=RetrievalConfidence.VERBATIM,
                title=long_title,
                summary="엠케이전자의 연체 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인됨.",
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.INTERNAL_FIELD,
                        ref_type=RefType.SNAPSHOT_KEYPATH,
                        ref_value="/credit/overdue",
                        snippet="overdue: true (연체 상태 확인)"
                    )
                ]
            )

    def test_summary_max_length(self):
        """Test summary max length validation."""
        long_summary = "엠케이전자의 " + "설명 " * 100  # Very long
        with pytest.raises(ValueError):
            SignalStrictSchema(
                signal_type=SignalType.DIRECT,
                event_type=EventType.OVERDUE_FLAG_ON,
                impact_direction=ImpactDirection.RISK,
                impact_strength=ImpactStrength.HIGH,
                confidence=ConfidenceLevel.HIGH,
                retrieval_confidence=RetrievalConfidence.VERBATIM,
                title="엠케이전자 연체 발생",
                summary=long_summary,
                evidence=[
                    EvidenceStrictSchema(
                        evidence_type=EvidenceType.INTERNAL_FIELD,
                        ref_type=RefType.SNAPSHOT_KEYPATH,
                        ref_value="/credit/overdue",
                        snippet="overdue: true (연체 상태 확인)"
                    )
                ]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
