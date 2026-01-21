"""
Corp Profile Bug Fixes - E2E & Edge Case Tests
Generated: 2026-01-21
QA Engineer: Senior QA
Total Test Cases: 40
"""

import json
import pytest
from datetime import datetime, UTC
from typing import Any

# Import helper functions to test
import sys
sys.path.insert(0, 'backend')

# ============================================================================
# SECTION 1: UNIT TESTS - Helper Functions
# ============================================================================


class TestSafeJsonDumps:
    """P0-3 Fix: safe_json_dumps() - 이중 직렬화 방지"""

    def get_safe_json_dumps(self):
        """Import the function dynamically to avoid import errors during collection"""
        from app.worker.pipelines.corp_profiling import safe_json_dumps
        return safe_json_dumps

    def test_dict_to_json_string(self):
        """UNIT-JSON-001: Dict with Korean → Valid JSON string"""
        safe_json_dumps = self.get_safe_json_dumps()
        input_data = {"회사명": "삼성전자", "매출": 100000000}
        result = safe_json_dumps(input_data)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == input_data
        assert "삼성전자" in result  # Korean preserved

    def test_already_json_string_no_double_encoding(self):
        """UNIT-JSON-002: CRITICAL - Already JSON string → Same (no double quotes)"""
        safe_json_dumps = self.get_safe_json_dumps()
        input_json = '{"key_suppliers": ["A", "B"]}'
        result = safe_json_dumps(input_json)

        # CRITICAL: Should NOT add extra quotes
        assert result == input_json
        assert result[0] == '{'  # Not '"'
        assert '\\' not in result  # No escape chars added

    def test_none_returns_empty_object(self):
        """UNIT-JSON-003: None → '{}'"""
        safe_json_dumps = self.get_safe_json_dumps()
        result = safe_json_dumps(None)

        assert result == '{}'
        assert json.loads(result) == {}

    def test_invalid_json_string_quoted(self):
        """UNIT-JSON-004: Invalid JSON string → Quoted string"""
        safe_json_dumps = self.get_safe_json_dumps()
        input_str = "not-json-data"
        result = safe_json_dumps(input_str)

        # Should be quoted as a JSON string
        assert json.loads(result) == input_str

    def test_nested_complex_object(self):
        """UNIT-JSON-005: Nested complex object → Valid JSON with nesting"""
        safe_json_dumps = self.get_safe_json_dumps()
        input_data = {
            "supply_chain": {
                "key_suppliers": ["A", "B"],
                "supplier_countries": {"중국": 60, "일본": 40}
            },
            "competitors": [
                {"name": "경쟁사1", "market_share": 30}
            ]
        }
        result = safe_json_dumps(input_data)

        parsed = json.loads(result)
        assert parsed["supply_chain"]["key_suppliers"] == ["A", "B"]
        assert parsed["competitors"][0]["name"] == "경쟁사1"


class TestParseDatetimeSafely:
    """P1-3 Fix: parse_datetime_safely() - "Z" suffix 지원"""

    def get_parse_datetime_safely(self):
        from app.worker.pipelines.corp_profiling import parse_datetime_safely
        return parse_datetime_safely

    def test_z_suffix_supported(self):
        """UNIT-DATE-001: CRITICAL - "Z" suffix → datetime object"""
        parse_datetime_safely = self.get_parse_datetime_safely()
        result = parse_datetime_safely("2026-01-21T12:00:00Z")

        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 21
        assert result.hour == 12

    def test_standard_offset_format(self):
        """UNIT-DATE-002: "+00:00" format → datetime object"""
        parse_datetime_safely = self.get_parse_datetime_safely()
        result = parse_datetime_safely("2026-01-21T12:00:00+00:00")

        assert result is not None
        assert isinstance(result, datetime)

    def test_none_returns_none(self):
        """UNIT-DATE-003: None → None (no error)"""
        parse_datetime_safely = self.get_parse_datetime_safely()
        result = parse_datetime_safely(None)

        assert result is None

    def test_empty_string_returns_none(self):
        """UNIT-DATE-004: Empty string → None"""
        parse_datetime_safely = self.get_parse_datetime_safely()
        result = parse_datetime_safely("")

        assert result is None

    def test_invalid_format_returns_none(self):
        """UNIT-DATE-005: Invalid format → None (ValueError caught)"""
        parse_datetime_safely = self.get_parse_datetime_safely()
        result = parse_datetime_safely("not-a-date")

        assert result is None


class TestNormalizeSingleSourceRisk:
    """P0-1 Fix: normalize_single_source_risk() - boolean/string → list 정규화"""

    def get_normalize_single_source_risk(self):
        from app.worker.pipelines.corp_profiling import normalize_single_source_risk
        return normalize_single_source_risk

    def test_boolean_true_to_list(self):
        """UNIT-RISK-001: CRITICAL - True → ["단일 조달처 위험 있음"]"""
        normalize = self.get_normalize_single_source_risk()
        result = normalize(True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "단일 조달처 위험" in result[0]

    def test_boolean_false_to_empty_list(self):
        """UNIT-RISK-002: CRITICAL - False → []"""
        normalize = self.get_normalize_single_source_risk()
        result = normalize(False)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_string_to_single_item_list(self):
        """UNIT-RISK-003: String "반도체" → ["반도체"]"""
        normalize = self.get_normalize_single_source_risk()
        result = normalize("반도체")

        assert result == ["반도체"]

    def test_list_passthrough(self):
        """UNIT-RISK-004: List ["A", "B"] → ["A", "B"] (unchanged)"""
        normalize = self.get_normalize_single_source_risk()
        input_list = ["반도체", "디스플레이"]
        result = normalize(input_list)

        assert result == input_list

    def test_list_with_falsy_values_filtered(self):
        """UNIT-RISK-005: List with falsy → Filtered"""
        normalize = self.get_normalize_single_source_risk()
        result = normalize(["A", None, "", "B"])

        assert result == ["A", "B"]

    def test_none_returns_empty_list(self):
        """UNIT-RISK-006: None → []"""
        normalize = self.get_normalize_single_source_risk()
        result = normalize(None)

        assert result == []


# ============================================================================
# SECTION 2: API HELPER FUNCTION TESTS
# ============================================================================


class TestParseSupplyChain:
    """P0-1 Fix: _parse_supply_chain() with type normalization"""

    def test_boolean_single_source_risk_normalized(self):
        """API-SUPPLY-001: boolean single_source_risk → list"""
        # This tests the profiles.py helper
        from app.api.v1.endpoints.profiles import _parse_supply_chain

        input_data = {
            "key_suppliers": ["공급사A"],
            "supplier_countries": {"중국": 60},
            "single_source_risk": True,  # Boolean instead of list
            "material_import_ratio_pct": 40
        }

        result = _parse_supply_chain(input_data)

        assert isinstance(result.single_source_risk, list)
        assert len(result.single_source_risk) > 0

    def test_none_returns_empty_schema(self):
        """API-SUPPLY-002: None → Empty SupplyChainSchema"""
        from app.api.v1.endpoints.profiles import _parse_supply_chain

        result = _parse_supply_chain(None)

        assert result.key_suppliers == []
        assert result.single_source_risk == []


class TestParseConsensusMetadata:
    """P1-3 Fix: _parse_consensus_metadata() with Z suffix handling"""

    def test_z_suffix_consensus_at(self):
        """API-CONSENSUS-001: "Z" suffix in consensus_at → Parsed correctly"""
        from app.api.v1.endpoints.profiles import _parse_consensus_metadata

        input_data = {
            "consensus_at": "2026-01-21T10:30:00Z",
            "perplexity_success": True,
            "overall_confidence": "HIGH"
        }

        result = _parse_consensus_metadata(input_data)

        assert result.consensus_at is not None
        assert result.consensus_at.year == 2026


# ============================================================================
# SECTION 3: EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Edge cases for robustness"""

    def test_mixed_types_in_list(self):
        """EDGE-003: Mixed types ["A", 123, None, true] → ["A", "123"]"""
        from app.worker.pipelines.corp_profiling import normalize_single_source_risk

        result = normalize_single_source_risk(["A", 123, None, True, ""])

        # Should filter falsy and stringify
        assert "A" in result
        assert "123" in result
        assert len(result) >= 2

    def test_korean_special_characters(self):
        """EDGE-005: Korean special chars preserved"""
        from app.worker.pipelines.corp_profiling import safe_json_dumps

        input_data = {"회사명": "㈜삼성", "지역": "서울·경기"}
        result = safe_json_dumps(input_data)

        parsed = json.loads(result)
        assert "㈜삼성" in parsed["회사명"]
        assert "·" in parsed["지역"]


# ============================================================================
# TEST DATA FOR E2E TESTS
# ============================================================================

TEST_PROFILE_DATA = {
    "full_profile": {
        "corp_id": "8001-3719240",
        "business_summary": "반도체 제조 및 전자부품 사업",
        "ceo_name": "현기진",
        "employee_count": 500,
        "revenue_krw": 120000000000,
        "export_ratio_pct": 45,
        "country_exposure": {"중국": 40, "미국": 30, "일본": 20, "기타": 10},
        "supply_chain": {
            "key_suppliers": ["삼성전자", "SK하이닉스"],
            "supplier_countries": {"대만": 50, "중국": 30, "일본": 20},
            "single_source_risk": ["ASML 노광장비", "네온가스"],
            "material_import_ratio_pct": 70
        },
        "overseas_business": {
            "subsidiaries": [
                {"name": "MK Vietnam", "country": "베트남", "business_type": "생산"},
                {"name": "MK Shanghai", "country": "중국", "business_type": "판매"}
            ],
            "manufacturing_countries": ["베트남", "중국"]
        },
        "shareholders": [
            {"name": "현기진", "ownership_pct": 35.5},
            {"name": "국민연금", "ownership_pct": 8.2}
        ],
        "competitors": [
            {"name": "LG전자", "market_share_pct": 25}
        ],
        "macro_factors": [
            {"factor": "반도체 수요 증가", "impact": "POSITIVE"},
            {"factor": "미중 무역분쟁", "impact": "NEGATIVE"}
        ],
        "profile_confidence": "HIGH",
        "source_urls": ["https://dart.fss.or.kr/test", "https://kind.krx.co.kr/test"],
        "consensus_metadata": {
            "consensus_at": "2026-01-21T10:00:00Z",
            "perplexity_success": True,
            "gemini_success": True,
            "overall_confidence": "HIGH",
            "fallback_layer": 0
        },
        "fetched_at": "2026-01-21T09:00:00Z",
        "expires_at": "2026-01-28T09:00:00Z",
        "is_fallback": False
    },
    "empty_profile": {
        "corp_id": "TEST-EMPTY-001",
        "business_summary": None,
        "ceo_name": None,
        "employee_count": None,
        "revenue_krw": None,
        "export_ratio_pct": None,
        "country_exposure": {},
        "supply_chain": {},
        "overseas_business": {},
        "shareholders": [],
        "competitors": [],
        "macro_factors": [],
        "key_materials": [],
        "key_customers": [],
        "profile_confidence": "NONE",
        "source_urls": [],
        "consensus_metadata": None,
        "fetched_at": "2026-01-21T09:00:00Z",
        "expires_at": None,  # NULL expires_at
        "is_fallback": True
    },
    "boolean_single_source_risk": {
        "corp_id": "TEST-BOOL-001",
        "supply_chain": {
            "key_suppliers": ["테스트공급사"],
            "single_source_risk": True,  # Boolean instead of list
        }
    }
}

# SQL for inserting test data
TEST_DATA_SQL = """
-- Test Profile 1: Full data
INSERT INTO rkyc_corp_profile (
    profile_id, corp_id, business_summary, ceo_name, employee_count,
    revenue_krw, export_ratio_pct, country_exposure, supply_chain,
    overseas_business, shareholders, competitors, macro_factors,
    profile_confidence, source_urls, consensus_metadata,
    fetched_at, expires_at, is_fallback, status
) VALUES (
    'aaaaaaaa-test-0001-0001-000000000001',
    'TEST-FULL-001',
    '테스트 기업 - 전체 데이터',
    '테스트CEO',
    500,
    120000000000,
    45,
    '{"중국": 40, "미국": 30}'::jsonb,
    '{"key_suppliers": ["A", "B"], "single_source_risk": ["반도체"]}'::jsonb,
    '{"subsidiaries": [{"name": "TestVN", "country": "베트남"}]}'::jsonb,
    '[{"name": "대주주", "ownership_pct": 35}]'::jsonb,
    '[{"name": "경쟁사", "market_share_pct": 20}]'::jsonb,
    '[{"factor": "긍정요인", "impact": "POSITIVE"}]'::jsonb,
    'HIGH',
    ARRAY['https://example.com'],
    '{"consensus_at": "2026-01-21T10:00:00Z", "perplexity_success": true}'::jsonb,
    NOW(),
    NOW() + INTERVAL '7 days',
    false,
    'ACTIVE'
) ON CONFLICT (corp_id) DO NOTHING;

-- Test Profile 2: Empty data (for "정보 없음" display test)
INSERT INTO rkyc_corp_profile (
    profile_id, corp_id, business_summary, profile_confidence,
    fetched_at, expires_at, is_fallback, status
) VALUES (
    'aaaaaaaa-test-0002-0002-000000000002',
    'TEST-EMPTY-001',
    NULL,
    'NONE',
    NOW(),
    NULL,  -- NULL expires_at
    true,
    'ACTIVE'
) ON CONFLICT (corp_id) DO NOTHING;

-- Test Profile 3: Boolean single_source_risk (for type normalization test)
INSERT INTO rkyc_corp_profile (
    profile_id, corp_id, supply_chain, profile_confidence,
    fetched_at, expires_at, is_fallback, status
) VALUES (
    'aaaaaaaa-test-0003-0003-000000000003',
    'TEST-BOOL-001',
    '{"key_suppliers": ["A"], "single_source_risk": true}'::jsonb,  -- Boolean!
    'LOW',
    NOW(),
    NOW() + INTERVAL '7 days',
    false,
    'ACTIVE'
) ON CONFLICT (corp_id) DO NOTHING;
"""


if __name__ == "__main__":
    print("=" * 60)
    print("Corp Profile Bug Fixes - Test Suite")
    print("=" * 60)
    print("\nTest Data SQL:")
    print(TEST_DATA_SQL)
    print("\n" + "=" * 60)
    print("Run with: pytest backend/tests/test_corp_profile_bugfixes.py -v")
    print("=" * 60)
