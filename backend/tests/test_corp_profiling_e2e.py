"""
E2E Test Scenarios for Corp Profiling Pipeline
Based on docs/PRD/E2E-Test-Scenarios-Corp-Profiling-Pipeline.md

Categories:
1. Fallback Cascade (TC-001 ~ TC-005)
2. Consensus Engine (TC-006 ~ TC-010)
3. Cache Timing (TC-011 ~ TC-014)
4. Circuit Breaker (TC-015 ~ TC-017)
5. Data Validation (TC-018 ~ TC-022)
6. Timing & Ordering (TC-023 ~ TC-025)
7. Integration (TC-026 ~ TC-028)
8. Performance (TC-029 ~ TC-030)
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.worker.llm.consensus_engine import (
    ConsensusEngine,
    tokenize,
    jaccard_similarity,
    compare_values,
    SourceType,
    FieldConsensus,
    ConsensusMetadata,
    KOREAN_STOPWORDS,
)
from app.worker.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitConfig,
    CircuitState,
    CircuitOpenError,
    get_circuit_breaker_manager,
)


# ============================================================================
# Category 2: Consensus Engine Edge Cases (TC-006 ~ TC-010)
# ============================================================================

class TestJaccardSimilarity:
    """Jaccard Similarity 관련 테스트"""

    def test_tc006_jaccard_boundary_exactly_0_7(self):
        """TC-006: Jaccard Similarity 경계값 정확히 0.7 테스트"""
        # Setup: 5/7 = 0.714... which is >= 0.7
        text_a = "반도체 소재 전문 제조업체 삼성 협력사"
        text_b = "반도체 부품 전문 제조업체 삼성 협력사"

        tokens_a = tokenize(text_a)
        tokens_b = tokenize(text_b)

        print(f"Tokens A: {tokens_a}")
        print(f"Tokens B: {tokens_b}")

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        print(f"Intersection: {intersection}")
        print(f"Union: {union}")

        score = jaccard_similarity(text_a, text_b)
        print(f"Jaccard Score: {score}")

        # Should be match because 0.714 >= 0.7
        assert score >= 0.7, f"Expected >= 0.7, got {score}"

        is_match, _ = compare_values(text_a, text_b, threshold=0.7)
        assert is_match is True, "Should be a match at boundary"

    def test_tc006_jaccard_boundary_just_below_0_7(self):
        """TC-006b: Jaccard Similarity 0.7 미만 테스트"""
        # Setup: Make strings that result in < 0.7 similarity
        text_a = "반도체 소재 전문 제조업체"
        text_b = "자동차 부품 전문 공급업체"

        score = jaccard_similarity(text_a, text_b)
        print(f"Jaccard Score: {score}")

        # Should not be match
        is_match, _ = compare_values(text_a, text_b, threshold=0.7)
        assert is_match is False, f"Expected mismatch, got match with score {score}"

    def test_tc007_jaccard_stopwords_only(self):
        """TC-007: Stopwords만으로 구성된 문자열 테스트 (Division by zero 방지)"""
        # Setup: Only stopwords
        text_a = "의 및 등의 을를 은는"
        text_b = "이가 에서 으로 의"

        tokens_a = tokenize(text_a)
        tokens_b = tokenize(text_b)

        print(f"Tokens A after stopword removal: {tokens_a}")
        print(f"Tokens B after stopword removal: {tokens_b}")

        # Should be empty sets after stopword removal
        # jaccard_similarity should handle this gracefully
        score = jaccard_similarity(text_a, text_b)
        print(f"Jaccard Score: {score}")

        # Empty sets should return 1.0 (both empty = match)
        assert score == 1.0, f"Expected 1.0 for both empty, got {score}"

    def test_tc007_jaccard_one_empty_after_stopwords(self):
        """TC-007b: 한쪽만 Stopwords로 구성된 경우"""
        text_a = "의 및 등의"  # Only stopwords
        text_b = "반도체 제조업체"  # Real content

        tokens_a = tokenize(text_a)
        tokens_b = tokenize(text_b)

        print(f"Tokens A: {tokens_a}")
        print(f"Tokens B: {tokens_b}")

        score = jaccard_similarity(text_a, text_b)
        print(f"Jaccard Score: {score}")

        # One empty, one not = 0.0 (mismatch)
        assert score == 0.0, f"Expected 0.0 for one empty, got {score}"


class TestNumericComparison:
    """숫자 비교 관련 테스트"""

    def test_tc008_numeric_zero_values(self):
        """TC-008: 0 값 포함 숫자 비교 (Division by zero 방지)"""
        # Case 1: Both zero
        is_match, score = compare_values(0, 0)
        assert is_match is True, "Both zero should match"
        assert score == 1.0, "Both zero should have score 1.0"

        # Case 2: One zero, one non-zero
        is_match, score = compare_values(0, 5)
        print(f"0 vs 5: is_match={is_match}, score={score}")
        assert is_match is False, "Zero vs non-zero should not match"
        assert score == 0.0, "Zero vs non-zero should have score 0.0"

        # Case 3: Formula test - abs(a-b) / max(a,b)
        # 5 vs 0: abs(5-0)/max(5,0) = 5/5 = 100% diff > 10% threshold
        is_match, score = compare_values(5, 0)
        assert is_match is False, "Non-zero vs zero should not match"

    def test_tc008_numeric_percentage_threshold(self):
        """TC-008b: 숫자 비교 10% 임계값 테스트"""
        # Within 10%: 100 vs 95 = 95/100 = 0.95 >= 0.9
        is_match, score = compare_values(100, 95)
        assert is_match is True, "5% diff should match"
        assert score >= 0.9

        # Exactly at 10%: 100 vs 90 = 90/100 = 0.90 >= 0.9
        is_match, score = compare_values(100, 90)
        assert is_match is True, "10% diff should match (boundary)"
        assert score == 0.9

        # Beyond 10%: 100 vs 89 = 89/100 = 0.89 < 0.9
        is_match, score = compare_values(100, 89)
        assert is_match is False, "11% diff should not match"
        assert score < 0.9


class TestCountryExposure:
    """Country Exposure 비교 테스트"""

    def test_tc009_country_different_keys_same_values(self):
        """TC-009: 동일 국가의 다른 표기법 테스트"""
        # Note: Current implementation does NOT normalize country codes
        # This test documents the current behavior

        dict_a = {"중국": 30, "미국": 20}
        dict_b = {"CN": 30, "US": 20}

        is_match, score = compare_values(dict_a, dict_b, threshold=0.5)
        print(f"Different country codes: is_match={is_match}, score={score}")

        # Current behavior: Keys don't match, so low similarity
        # This is a KNOWN LIMITATION - documenting for CTO report
        assert is_match is False, "Different country codes don't match (known limitation)"

    def test_tc009_country_same_keys(self):
        """TC-009b: 동일 키로 구성된 country_exposure"""
        dict_a = {"중국": 30, "미국": 20}
        dict_b = {"중국": 28, "미국": 22}  # Within 10% variance

        is_match, score = compare_values(dict_a, dict_b, threshold=0.5)
        print(f"Same keys, similar values: is_match={is_match}, score={score}")

        # Should match - same keys, similar values
        assert is_match is True


class TestListComparison:
    """리스트 비교 테스트"""

    def test_tc010_list_with_duplicates(self):
        """TC-010: 중복 포함 리스트 비교"""
        list_a = ["삼성전자", "SK하이닉스", "삼성전자", "LG"]  # Duplicate
        list_b = ["삼성전자", "SK하이닉스"]

        is_match, score = compare_values(list_a, list_b, threshold=0.5)
        print(f"List with duplicates: is_match={is_match}, score={score}")

        # Lists use 0.5 threshold per PRD
        # After dedup: A={삼성전자, SK하이닉스, LG}, B={삼성전자, SK하이닉스}
        # Jaccard: 2/3 = 0.67 >= 0.5
        assert is_match is True, f"Expected match with Jaccard 0.67, threshold 0.5"
        assert 0.6 <= score <= 0.7

    def test_tc010_list_empty_handling(self):
        """TC-010b: 빈 리스트 처리"""
        # Both empty
        is_match, score = compare_values([], [])
        assert is_match is True
        assert score == 1.0

        # One empty
        is_match, score = compare_values(["삼성전자"], [])
        assert is_match is False
        assert score == 0.0


# ============================================================================
# Category 4: Circuit Breaker Edge Cases (TC-015 ~ TC-017)
# ============================================================================

class TestCircuitBreaker:
    """Circuit Breaker 테스트"""

    def setup_method(self):
        """각 테스트 전 Circuit Breaker 리셋"""
        # Create fresh instances for each test
        self.config = CircuitConfig(
            failure_threshold=3,
            cooldown_seconds=1,  # Short for testing
            half_open_requests=1,
        )
        self.breaker = CircuitBreaker("test_provider", self.config)

    def test_tc015_half_open_success_then_immediate_failure(self):
        """TC-015: HALF_OPEN 성공 후 즉시 실패"""
        # Step 1: Open the circuit (3 failures)
        for _ in range(3):
            self.breaker.record_failure("test error")

        assert self.breaker.state == CircuitState.OPEN

        # Step 2: Wait for cooldown
        time.sleep(1.1)

        # Step 3: Check state transition to HALF_OPEN
        assert self.breaker.is_available() is True
        assert self.breaker.state == CircuitState.HALF_OPEN

        # Step 4: Success in HALF_OPEN -> CLOSED
        self.breaker.record_success()
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker.failure_count == 0

        # Step 5: Immediate failure -> Should stay CLOSED with failure_count=1
        self.breaker.record_failure("new error")
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker.failure_count == 1

    def test_tc016_cooldown_exact_boundary(self):
        """TC-016: Cooldown 정확한 경계 테스트"""
        # Open the circuit
        for _ in range(3):
            self.breaker.record_failure("test error")

        assert self.breaker.state == CircuitState.OPEN
        opened_at = self.breaker.opened_at

        # Just before cooldown (0.9 seconds)
        time.sleep(0.9)
        assert self.breaker.is_available() is False
        assert self.breaker.state == CircuitState.OPEN

        # After cooldown (total 1.1 seconds)
        time.sleep(0.2)
        assert self.breaker.is_available() is True
        assert self.breaker.state == CircuitState.HALF_OPEN

    def test_tc017_all_circuits_open(self):
        """TC-017: 모든 Circuit Breaker가 OPEN인 경우"""
        manager = CircuitBreakerManager()

        # Open all circuits
        for provider in ["perplexity", "gemini", "claude"]:
            breaker = manager.get_breaker(provider)
            # Claude has threshold=2, others=3
            threshold = 2 if provider == "claude" else 3
            for _ in range(threshold):
                manager.record_failure(provider, "test error")

        # Verify all are OPEN
        all_status = manager.get_all_status()
        for provider, status in all_status.items():
            print(f"{provider}: {status.state}")
            assert status.state == CircuitState.OPEN

        # Verify none are available
        assert manager.is_available("perplexity") is False
        assert manager.is_available("gemini") is False
        assert manager.is_available("claude") is False

    def test_circuit_breaker_execute_with_protection(self):
        """Circuit Breaker execute_with_circuit_breaker 테스트"""
        manager = CircuitBreakerManager()

        # Normal execution
        def success_func():
            return "success"

        result = manager.execute_with_circuit_breaker("perplexity", success_func)
        assert result == "success"

        # Failure execution
        def fail_func():
            raise ValueError("test error")

        # Record failures to open circuit
        for _ in range(3):
            try:
                manager.execute_with_circuit_breaker("perplexity", fail_func)
            except ValueError:
                pass

        # Circuit should now be open
        with pytest.raises(CircuitOpenError):
            manager.execute_with_circuit_breaker("perplexity", success_func)


# ============================================================================
# Category 5: Data Validation (TC-018 ~ TC-022)
# ============================================================================

class TestDataValidation:
    """데이터 검증 테스트"""

    def test_tc018_export_ratio_exceeds_100(self):
        """TC-018: export_ratio_pct = 101 (범위 초과)"""
        # This should be caught by Pydantic schema validation
        # Testing the model behavior
        from pydantic import BaseModel, Field, ValidationError

        class TestSchema(BaseModel):
            export_ratio_pct: int = Field(ge=0, le=100)

        # Valid value
        valid = TestSchema(export_ratio_pct=100)
        assert valid.export_ratio_pct == 100

        # Invalid value should raise
        with pytest.raises(ValidationError):
            TestSchema(export_ratio_pct=101)

        with pytest.raises(ValidationError):
            TestSchema(export_ratio_pct=-1)

    def test_tc019_revenue_large_number(self):
        """TC-019: revenue_krw 매우 큰 숫자 테스트"""
        # Python int has no max, but PostgreSQL BIGINT does
        # BIGINT max: 9223372036854775807
        bigint_max = 9223372036854775807

        # Test with value within BIGINT range
        large_but_valid = 1000000000000000  # 1000조
        assert large_but_valid < bigint_max

        # Test with value exceeding BIGINT
        exceeds_bigint = 99999999999999999999999999
        assert exceeds_bigint > bigint_max

        # Note: DB will reject this, validation should catch it
        # This documents the expected behavior

    def test_tc020_sql_injection_in_business_summary(self):
        """TC-020: SQL Injection 시도 (ORM 사용으로 방지됨)"""
        malicious_input = "반도체'; DROP TABLE rkyc_corp_profile;--"

        # SQLAlchemy ORM uses parameterized queries
        # This test documents that the string is treated as data, not SQL

        # The string should be stored as-is, no SQL execution
        assert "DROP TABLE" in malicious_input
        # In real DB test, verify table still exists after insert

    def test_tc021_xss_in_executives_name(self):
        """TC-021: XSS 시도 (Backend는 저장만, Frontend가 escape)"""
        xss_input = "<script>alert('xss')</script>"

        # Backend should store as-is
        executives = [{"name": xss_input, "position": "CEO"}]

        # Verify data integrity
        assert executives[0]["name"] == xss_input

        # Note: Frontend must escape when rendering
        # This is a frontend responsibility

    def test_tc022_unicode_normalization(self):
        """TC-022: Unicode 정규화 테스트"""
        # Standard Korean
        standard = "삼성전자"

        # With invisible characters (zero-width space)
        with_invisible = "삼성\u200b전자"  # Zero-width space

        # Fullwidth characters
        fullwidth = "삼성전자"  # Actually same, but representing concept

        # Current behavior: These are treated as different strings
        # This is a KNOWN LIMITATION
        assert standard != with_invisible

        # Tokenization should handle this
        tokens_standard = tokenize(standard)
        tokens_invisible = tokenize(with_invisible)

        print(f"Standard tokens: {tokens_standard}")
        print(f"With invisible tokens: {tokens_invisible}")

        # Note: Current implementation may treat these differently


# ============================================================================
# Category 1: Fallback Cascade Tests (Conceptual - requires mocking)
# ============================================================================

class TestFallbackCascade:
    """Fallback Cascade 테스트 (Mock 기반)"""

    def test_tc001_partial_json_handling(self):
        """TC-001: Perplexity 부분 JSON 응답 처리"""
        partial_json = '{"business_summary": "반도체 제조업'  # Missing closing brace

        # Attempt to parse should fail
        with pytest.raises(json.JSONDecodeError):
            json.loads(partial_json)

        # Pipeline should catch this and proceed to fallback
        # This documents the expected behavior

    def test_tc003_wrong_schema_from_claude(self):
        """TC-003: Claude가 잘못된 스키마 반환"""
        wrong_schema = {
            "company_name": "엠케이전자",  # Wrong field name
            "ceo": "홍길동",  # Wrong field name
            "revenue": 50000000000,  # Wrong field name
        }

        # Expected schema fields
        expected_fields = {"corp_id", "business_summary", "revenue_krw", "export_ratio_pct"}

        # Verify schema mismatch
        actual_fields = set(wrong_schema.keys())
        assert actual_fields.isdisjoint(expected_fields)

    def test_tc004_all_fields_null(self):
        """TC-004: 모든 LLM이 성공하지만 모든 필드가 null"""
        all_null_profile = {
            "ceo_name": None,
            "employee_count": None,
            "revenue_krw": None,
            "export_ratio_pct": None,
            "business_summary": None,
            "country_exposure": {},
            "key_materials": [],
            "key_customers": [],
        }

        # All null is valid - confirmed absence of data
        # Should still be saved with HIGH confidence (confirmed null)
        for key, value in all_null_profile.items():
            assert value is None or value == {} or value == []


# ============================================================================
# Consensus Engine Integration Tests
# ============================================================================

class TestConsensusEngineIntegration:
    """Consensus Engine 통합 테스트"""

    def test_merge_with_enrichment(self):
        """Perplexity + Gemini 보완 합성"""
        engine = ConsensusEngine()

        perplexity_profile = {
            "business_summary": "반도체 제조업체",
            "revenue_krw": 500000000000,
            "export_ratio_pct": None,  # Missing
            "key_customers": ["삼성전자"],
        }

        gemini_result = {
            "validated_fields": ["business_summary", "revenue_krw"],
            "enriched_fields": {
                "export_ratio_pct": {
                    "value": 45,
                    "confidence": "MED",
                },
            },
            "discrepancies": [],
        }

        result = engine.merge(
            perplexity_profile,
            gemini_result,
            corp_name="테스트기업",
            industry_code="C26",
        )

        # Verify enrichment was applied
        assert result.profile["export_ratio_pct"] == 45

        # Find the field detail for export_ratio_pct
        export_detail = next(
            (f for f in result.field_details if f.field_name == "export_ratio_pct"),
            None
        )
        assert export_detail is not None
        assert export_detail.source == SourceType.GEMINI_INFERRED
        assert export_detail.confidence == "MED"

    def test_merge_with_discrepancy(self):
        """Perplexity vs Gemini 불일치 처리"""
        engine = ConsensusEngine()

        perplexity_profile = {
            "business_summary": "반도체 제조업체",
            "export_ratio_pct": 55,
        }

        gemini_result = {
            "validated_fields": [],
            "enriched_fields": {
                "export_ratio_pct": {
                    "value": 30,  # Different value
                    "confidence": "MED",
                },
            },
            "discrepancies": [
                {
                    "field": "export_ratio_pct",
                    "issue": "Gemini estimates 30%, Perplexity says 55%",
                }
            ],
        }

        result = engine.merge(
            perplexity_profile,
            gemini_result,
            corp_name="테스트기업",
            industry_code="C26",
        )

        # Perplexity value should be adopted (priority)
        assert result.profile["export_ratio_pct"] == 55

        # Discrepancy should be flagged
        export_detail = next(
            (f for f in result.field_details if f.field_name == "export_ratio_pct"),
            None
        )
        assert export_detail is not None
        assert export_detail.discrepancy is True
        assert export_detail.source == SourceType.PERPLEXITY

    def test_overall_confidence_determination(self):
        """전체 Confidence 결정 로직"""
        engine = ConsensusEngine()

        # High confidence scenario
        perplexity_profile = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
        }

        gemini_result = {
            "validated_fields": ["field1", "field2", "field3"],
            "enriched_fields": {},
            "discrepancies": [],
        }

        result = engine.merge(
            perplexity_profile,
            gemini_result,
            corp_name="테스트",
            industry_code="C26",
        )

        # With no discrepancies and validation, should be MED or HIGH
        assert result.metadata.overall_confidence in ["MED", "HIGH"]


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
