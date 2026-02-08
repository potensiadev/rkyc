"""
Sprint 2 Agent Integration Tests

Tests for:
1. Agent prompt generation with Sprint 1 enhancements
2. Agent validation integration
3. Signal extraction flow

Author: Silicon Valley Senior PM
Date: 2026-02-08
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.worker.pipelines.signal_agents.direct_agent import DirectSignalAgent
from app.worker.pipelines.signal_agents.industry_agent import IndustrySignalAgent
from app.worker.pipelines.signal_agents.environment_agent import EnvironmentSignalAgent
from app.worker.pipelines.signal_agents.base import (
    BaseSignalAgent,
    BUFFETT_LIBRARIAN_PERSONA,
    FORBIDDEN_WORDS,
    FORBIDDEN_PATTERNS,
    check_forbidden_patterns,
)


# =============================================================================
# Test 1: Agent Prompt Generation
# =============================================================================

class TestDirectAgentPrompts:
    """Test DirectSignalAgent prompt generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = DirectSignalAgent()

    def test_system_prompt_contains_v2_principles(self):
        """Test system prompt includes V2_CORE_PRINCIPLES."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Hallucination Zero Tolerance" in prompt
        assert "Closed-World Assumption" in prompt

    def test_system_prompt_contains_direct_examples(self):
        """Test system prompt includes DIRECT examples."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Sprint 1: 16" in prompt
        assert "OVERDUE_FLAG_ON" in prompt

    def test_system_prompt_contains_persona(self):
        """Test system prompt includes Risk Manager persona."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Risk Manager" in prompt or "박준혁" in prompt

    def test_system_prompt_contains_strict_schema(self):
        """Test system prompt includes strict JSON schema."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "retrieval_confidence" in prompt
        assert "VERBATIM" in prompt

    def test_system_prompt_contains_chain_of_verification(self):
        """Test system prompt includes Chain-of-Verification."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Chain-of-Verification" in prompt or "CoV" in prompt

    def test_system_prompt_contains_rejection_examples(self):
        """Test system prompt includes rejection examples."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        # Check for rejection case indicators
        assert "금지" in prompt or "거부" in prompt

    def test_user_prompt_contains_data_sources(self):
        """Test user prompt includes data source sections."""
        context = {
            "corp_name": "엠케이전자",
            "corp_reg_no": "135-81-06406",
            "industry_name": "전자부품제조업",
            "snapshot_json": {"corp": {"corp_id": "8001-3719240"}},
            "direct_events": [],
            "document_facts": [],
        }
        prompt = self.agent.get_user_prompt(context)
        assert "엠케이전자" in prompt
        assert "스냅샷" in prompt or "snapshot" in prompt.lower()


class TestIndustryAgentPrompts:
    """Test IndustrySignalAgent prompt generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = IndustrySignalAgent()

    def test_system_prompt_contains_v2_principles(self):
        """Test system prompt includes V2_CORE_PRINCIPLES."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Hallucination Zero Tolerance" in prompt

    def test_system_prompt_contains_industry_examples(self):
        """Test system prompt includes INDUSTRY examples."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Sprint 1: 10" in prompt
        assert "INDUSTRY_SHOCK" in prompt

    def test_system_prompt_contains_ib_persona(self):
        """Test system prompt includes IB Manager persona."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "IB Manager" in prompt or "김서연" in prompt

    def test_system_prompt_industry_shock_criteria(self):
        """Test system prompt includes INDUSTRY_SHOCK criteria."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "산업 전체" in prompt or "업계" in prompt


class TestEnvironmentAgentPrompts:
    """Test EnvironmentSignalAgent prompt generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = EnvironmentSignalAgent()

    def test_system_prompt_contains_v2_principles(self):
        """Test system prompt includes V2_CORE_PRINCIPLES."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Hallucination Zero Tolerance" in prompt

    def test_system_prompt_contains_environment_examples(self):
        """Test system prompt includes ENVIRONMENT examples."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        assert "Sprint 1: 11" in prompt
        assert "POLICY_REGULATION_CHANGE" in prompt

    def test_system_prompt_contains_11_categories(self):
        """Test system prompt includes all 11 environment categories."""
        prompt = self.agent.get_system_prompt("엠케이전자", "전자부품제조업")
        categories = [
            "FX_RISK", "TRADE_BLOC", "GEOPOLITICAL", "SUPPLY_CHAIN",
            "REGULATION", "COMMODITY", "PANDEMIC_HEALTH",
            "POLITICAL_INSTABILITY", "CYBER_TECH", "ENERGY_SECURITY", "FOOD_SECURITY"
        ]
        for category in categories:
            assert category in prompt, f"Missing category: {category}"

    def test_relevant_categories_export_ratio(self):
        """Test _get_relevant_categories with high export ratio."""
        categories = self.agent._get_relevant_categories(
            export_ratio=50,
            country_exposure=["중국"],
            key_materials=["반도체"],
            overseas_ops=[{"country": "베트남"}],
            industry_code="C26"
        )
        assert "FX_RISK" in categories
        assert "TRADE_BLOC" in categories
        assert "GEOPOLITICAL" in categories
        assert "CYBER_TECH" in categories  # C26 = 반도체

    def test_relevant_categories_food_industry(self):
        """Test _get_relevant_categories for food industry."""
        categories = self.agent._get_relevant_categories(
            export_ratio=10,
            country_exposure=[],
            key_materials=[],
            overseas_ops=[],
            industry_code="C10"  # 식품
        )
        assert "FOOD_SECURITY" in categories


# =============================================================================
# Test 2: Agent Validation Integration
# =============================================================================

class TestAgentValidation:
    """Test agent validation with Sprint 1 integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.direct_agent = DirectSignalAgent()

    def test_forbidden_patterns_imported(self):
        """Test that check_forbidden_patterns is imported in base.py."""
        # This tests the import works
        from app.worker.pipelines.signal_agents.base import check_forbidden_patterns
        matches = check_forbidden_patterns("반드시 확인해야 합니다")
        assert len(matches) > 0

    def test_agent_has_allowed_event_types(self):
        """Test agents have correct allowed event types."""
        assert "OVERDUE_FLAG_ON" in self.direct_agent.ALLOWED_EVENT_TYPES
        assert "KYC_REFRESH" in self.direct_agent.ALLOWED_EVENT_TYPES
        assert len(self.direct_agent.ALLOWED_EVENT_TYPES) == 8

        industry_agent = IndustrySignalAgent()
        assert "INDUSTRY_SHOCK" in industry_agent.ALLOWED_EVENT_TYPES
        assert len(industry_agent.ALLOWED_EVENT_TYPES) == 1

        env_agent = EnvironmentSignalAgent()
        assert "POLICY_REGULATION_CHANGE" in env_agent.ALLOWED_EVENT_TYPES
        assert len(env_agent.ALLOWED_EVENT_TYPES) == 1

    def test_agent_signal_type(self):
        """Test agents have correct signal type."""
        assert self.direct_agent.SIGNAL_TYPE == "DIRECT"
        assert IndustrySignalAgent().SIGNAL_TYPE == "INDUSTRY"
        assert EnvironmentSignalAgent().SIGNAL_TYPE == "ENVIRONMENT"


# =============================================================================
# Test 3: Signal Enrichment
# =============================================================================

class TestSignalEnrichment:
    """Test signal enrichment with Sprint 1 validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = DirectSignalAgent()
        self.context = {
            "corp_id": "8001-3719240",
            "corp_name": "엠케이전자",
            "snapshot_version": 1,
            "snapshot_json": {
                "credit": {
                    "loan_summary": {
                        "overdue_flag": True
                    }
                }
            },
            "direct_events": [],
        }

    def test_enrich_valid_signal(self):
        """Test enrichment of valid signal."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 30일 연체",
            "summary": "엠케이전자의 연체 확인됨. 스냅샷 overdue_flag=true.",
            "evidence": [{
                "evidence_type": "INTERNAL_FIELD",
                "ref_type": "SNAPSHOT_KEYPATH",
                "ref_value": "/credit/loan_summary/overdue_flag",
                "snippet": "overdue_flag: true"
            }]
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is not None
        assert enriched["corp_id"] == "8001-3719240"
        assert enriched["extracted_by"] == "direct_signal_agent"
        assert "event_signature" in enriched

    def test_reject_forbidden_pattern_in_title(self):
        """Test rejection of signal with forbidden pattern in title."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 반드시 점검 필요",  # Contains "반드시"
            "summary": "엠케이전자의 연체 확인됨.",
            "evidence": [{
                "evidence_type": "INTERNAL_FIELD",
                "ref_type": "SNAPSHOT_KEYPATH",
                "ref_value": "/credit/loan_summary/overdue_flag",
                "snippet": "overdue_flag: true"
            }]
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is None  # Should be rejected

    def test_reject_forbidden_pattern_in_summary(self):
        """Test rejection of signal with forbidden pattern in summary."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 연체 발생",
            "summary": "엠케이전자의 약 30% 연체가 예상됨.",  # Contains "약" and "예상"
            "evidence": [{
                "evidence_type": "INTERNAL_FIELD",
                "ref_type": "SNAPSHOT_KEYPATH",
                "ref_value": "/credit/loan_summary/overdue_flag",
                "snippet": "overdue_flag: true"
            }]
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is None  # Should be rejected

    def test_reject_invalid_event_type(self):
        """Test rejection of signal with invalid event_type."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "INDUSTRY_SHOCK",  # Wrong for DIRECT agent
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 업종 충격",
            "summary": "엠케이전자의 업종에 충격 발생.",
            "evidence": [{
                "evidence_type": "EXTERNAL",
                "ref_type": "URL",
                "ref_value": "https://example.com",
                "snippet": "업종 충격 기사"
            }]
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is None  # Should be rejected

    def test_reject_missing_evidence(self):
        """Test rejection of signal without evidence."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "impact_direction": "RISK",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "retrieval_confidence": "VERBATIM",
            "title": "엠케이전자 연체 발생",
            "summary": "엠케이전자의 연체 확인됨.",
            "evidence": []  # Empty!
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is None  # Should be rejected

    def test_reject_inferred_without_reason(self):
        """Test rejection of INFERRED without confidence_reason."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "KYC_REFRESH",
            "impact_direction": "NEUTRAL",
            "impact_strength": "LOW",
            "confidence": "LOW",
            "retrieval_confidence": "INFERRED",
            # Missing confidence_reason!
            "title": "엠케이전자 KYC 갱신 필요",
            "summary": "엠케이전자의 KYC 갱신이 필요한 것으로 추론됨.",
            "evidence": [{
                "evidence_type": "INTERNAL_FIELD",
                "ref_type": "SNAPSHOT_KEYPATH",
                "ref_value": "/corp/kyc_status/last_kyc_updated",
                "snippet": "last_kyc_updated: 2025-01-15"
            }]
        }

        enriched = self.agent._enrich_signal(signal, self.context)
        assert enriched is None  # Should be rejected


# =============================================================================
# Test 4: Signature Computation
# =============================================================================

class TestSignatureComputation:
    """Test event signature computation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = DirectSignalAgent()

    def test_signature_computed(self):
        """Test signature is computed correctly."""
        signal = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "evidence": [
                {"ref_value": "/credit/overdue_flag"},
                {"ref_value": "https://example.com/news"}
            ]
        }

        signature = self.agent._compute_signature(signal)
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex length

    def test_same_signal_same_signature(self):
        """Test identical signals produce same signature."""
        signal1 = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "evidence": [{"ref_value": "/credit/overdue_flag"}]
        }
        signal2 = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "evidence": [{"ref_value": "/credit/overdue_flag"}]
        }

        sig1 = self.agent._compute_signature(signal1)
        sig2 = self.agent._compute_signature(signal2)
        assert sig1 == sig2

    def test_different_signal_different_signature(self):
        """Test different signals produce different signatures."""
        signal1 = {
            "signal_type": "DIRECT",
            "event_type": "OVERDUE_FLAG_ON",
            "evidence": [{"ref_value": "/credit/overdue_flag"}]
        }
        signal2 = {
            "signal_type": "DIRECT",
            "event_type": "KYC_REFRESH",
            "evidence": [{"ref_value": "/corp/kyc_status"}]
        }

        sig1 = self.agent._compute_signature(signal1)
        sig2 = self.agent._compute_signature(signal2)
        assert sig1 != sig2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
