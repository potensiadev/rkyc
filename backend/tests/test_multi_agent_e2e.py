"""
Multi-Agent Signal Extraction E2E Tests (Sprint 1-4)

This test suite validates the complete functionality of the Multi-Agent
Signal Extraction architecture as specified in ADR-009.

Sprint 1: Perplexity + Gemini 병렬 실행, LLM Usage Tracking
Sprint 2: 3-Agent 분할 (Direct/Industry/Environment)
Sprint 3: Cross-Validation, Graceful Degradation, Concurrency Limit
Sprint 4: Celery group() 분산 실행
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import TimeoutError as FuturesTimeoutError

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return {
        "corp_id": "8001-3719240",
        "corp_name": "엠케이전자",
        "industry_code": "C26",
        "industry_name": "전자부품 제조업",
        "trace_id": "test_trace_001",
        "snapshot_json": {
            "schema_version": "v1.0",
            "corp": {
                "corp_id": "8001-3719240",
                "kyc_status": {
                    "is_kyc_completed": True,
                    "last_kyc_updated": "2024-11-15",
                    "internal_risk_grade": "MED"
                }
            },
            "credit": {
                "has_loan": True,
                "loan_summary": {
                    "total_exposure_krw": 1200000000,
                    "overdue_flag": False,
                    "risk_grade_internal": "MED"
                }
            }
        },
        "external_events": [
            {
                "event_id": "ext_001",
                "event_type": "NEWS",
                "title": "엠케이전자 신규 반도체 생산라인 증설",
                "summary": "엠케이전자가 500억원을 투자하여 신규 생산라인을 증설한다고 발표했다.",
                "source_url": "https://news.example.com/article/123",
                "published_at": "2026-01-20"
            }
        ],
        "industry_events": [
            {
                "event_id": "ind_001",
                "event_type": "INDUSTRY_NEWS",
                "title": "반도체 업종 전반 수요 증가 전망",
                "summary": "글로벌 반도체 수요가 2026년 하반기부터 회복세를 보일 것으로 전망된다.",
                "source_url": "https://industry.example.com/report/456"
            }
        ],
        "policy_events": [
            {
                "event_id": "pol_001",
                "event_type": "REGULATION",
                "title": "반도체 산업 지원 정책 발표",
                "summary": "정부가 반도체 산업 육성을 위한 세제 혜택 및 R&D 지원 정책을 발표했다.",
                "source_url": "https://policy.example.com/news/789"
            }
        ]
    }


@pytest.fixture
def sample_signals():
    """Sample signals for deduplication/validation testing."""
    return [
        {
            "signal_type": "DIRECT",
            "event_type": "LOAN_EXPOSURE_CHANGE",
            "impact_direction": "RISK",
            "impact_strength": "MED",
            "confidence": "HIGH",
            "title": "여신 노출 증가",
            "summary": "총 여신 노출이 12억원으로 확인됨",
            "evidence": [
                {
                    "evidence_type": "INTERNAL_FIELD",
                    "ref_type": "SNAPSHOT_KEYPATH",
                    "ref_value": "/credit/loan_summary/total_exposure_krw"
                }
            ],
            "extracted_by": "direct_agent"
        },
        {
            "signal_type": "INDUSTRY",
            "event_type": "INDUSTRY_SHOCK",
            "impact_direction": "OPPORTUNITY",
            "impact_strength": "MED",
            "confidence": "MED",
            "title": "반도체 업종 수요 회복",
            "summary": "반도체 업종 전체적으로 수요 회복 전망",
            "evidence": [
                {
                    "evidence_type": "EXTERNAL",
                    "ref_type": "URL",
                    "ref_value": "https://industry.example.com/report/456"
                }
            ],
            "extracted_by": "industry_agent"
        },
        {
            "signal_type": "ENVIRONMENT",
            "event_type": "POLICY_REGULATION_CHANGE",
            "impact_direction": "OPPORTUNITY",
            "impact_strength": "HIGH",
            "confidence": "HIGH",
            "title": "반도체 산업 지원 정책",
            "summary": "정부 세제 혜택 및 R&D 지원 정책 발표",
            "evidence": [
                {
                    "evidence_type": "EXTERNAL",
                    "ref_type": "URL",
                    "ref_value": "https://policy.example.com/news/789"
                }
            ],
            "extracted_by": "environment_agent"
        }
    ]


# =============================================================================
# Sprint 1 Tests: Perplexity + Gemini 병렬 실행, LLM Usage Tracking
# =============================================================================

class TestSprint1:
    """Sprint 1: 병렬 실행 및 Usage Tracking 테스트."""

    def test_usage_tracker_singleton_thread_safety(self):
        """P1-2 Fix: LLMUsageTracker 싱글톤 스레드 안전성 테스트."""
        from app.worker.llm.usage_tracker import (
            get_usage_tracker, reset_usage_tracker, LLMUsageTracker
        )

        # Reset first
        reset_usage_tracker()

        instances = []
        errors = []

        def get_instance():
            try:
                tracker = get_usage_tracker()
                instances.append(id(tracker))
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = [threading.Thread(target=get_instance) for _ in range(20)]

        # Start all threads simultaneously
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All instances should be the same (singleton)
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(set(instances)) == 1, "Multiple singleton instances created"

        # Cleanup
        reset_usage_tracker()

    def test_usage_tracker_log_usage(self):
        """Usage tracking 로깅 테스트."""
        from app.worker.llm.usage_tracker import (
            get_usage_tracker, reset_usage_tracker, log_llm_usage
        )

        reset_usage_tracker()
        tracker = get_usage_tracker()

        # Log some usage
        log = log_llm_usage(
            provider="claude",
            model="claude-opus-4-5-20251101",
            agent_name="test_agent",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=2500,
            corp_id="8001-3719240",
            stage="SIGNAL"
        )

        # Verify log
        assert log.provider == "claude"
        assert log.input_tokens == 1000
        assert log.output_tokens == 500
        assert log.total_tokens == 1500
        assert log.cost_usd > 0  # Should calculate cost

        # Check totals
        totals = tracker.get_totals()
        assert totals["calls"] == 1
        assert totals["tokens"] == 1500

        reset_usage_tracker()

    def test_usage_tracker_summary(self):
        """P1-6 Fix: Usage summary timestamp 비교 테스트."""
        from app.worker.llm.usage_tracker import (
            get_usage_tracker, reset_usage_tracker, log_llm_usage
        )

        reset_usage_tracker()
        tracker = get_usage_tracker()

        # Log multiple usages
        for i in range(5):
            log_llm_usage(
                provider="claude",
                model="claude-opus-4-5-20251101",
                agent_name=f"agent_{i}",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                latency_ms=1000
            )

        # Get summary for last 60 minutes
        summary = tracker.get_summary(last_n_minutes=60)

        assert summary.total_calls == 5
        assert summary.success_count == 5
        assert summary.failure_count == 0
        assert summary.total_tokens > 0
        assert len(summary.by_provider) > 0
        assert len(summary.by_agent) == 5

        reset_usage_tracker()

    def test_token_pricing_calculation(self):
        """토큰 비용 계산 테스트."""
        from app.worker.llm.usage_tracker import LLMUsageLog, TOKEN_PRICING

        # Claude Opus 4.5 pricing
        log = LLMUsageLog(
            trace_id="test",
            provider="claude",
            model="claude-opus-4-5-20251101",
            agent_name="test",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=1_000_000,
            total_tokens=2_000_000,
            latency_ms=1000
        )

        cost = log.calculate_cost()

        # Expected: (1M * 15 / 1M) + (1M * 75 / 1M) = 15 + 75 = 90
        assert cost == 90.0


# =============================================================================
# Sprint 2 Tests: 3-Agent 분할
# =============================================================================

class TestSprint2:
    """Sprint 2: 3-Agent 분할 테스트."""

    def test_direct_agent_initialization(self):
        """DirectSignalAgent 초기화 테스트."""
        from app.worker.pipelines.signal_agents.direct_agent import DirectSignalAgent

        agent = DirectSignalAgent()

        assert agent.AGENT_NAME == "direct_signal_agent"
        assert agent.SIGNAL_TYPE == "DIRECT"
        assert len(agent.ALLOWED_EVENT_TYPES) == 8
        assert "OVERDUE_FLAG_ON" in agent.ALLOWED_EVENT_TYPES
        assert "LOAN_EXPOSURE_CHANGE" in agent.ALLOWED_EVENT_TYPES

    def test_industry_agent_initialization(self):
        """IndustrySignalAgent 초기화 테스트."""
        from app.worker.pipelines.signal_agents.industry_agent import IndustrySignalAgent

        agent = IndustrySignalAgent()

        assert agent.AGENT_NAME == "industry_signal_agent"
        assert agent.SIGNAL_TYPE == "INDUSTRY"
        assert "INDUSTRY_SHOCK" in agent.ALLOWED_EVENT_TYPES

    def test_environment_agent_initialization(self):
        """EnvironmentSignalAgent 초기화 테스트."""
        from app.worker.pipelines.signal_agents.environment_agent import EnvironmentSignalAgent

        agent = EnvironmentSignalAgent()

        assert agent.AGENT_NAME == "environment_signal_agent"
        assert agent.SIGNAL_TYPE == "ENVIRONMENT"
        assert "POLICY_REGULATION_CHANGE" in agent.ALLOWED_EVENT_TYPES

    def test_base_agent_validation(self, sample_context):
        """BaseSignalAgent 검증 로직 테스트."""
        from app.worker.pipelines.signal_agents.base import (
            FORBIDDEN_WORDS, MAX_TITLE_LENGTH, MAX_SUMMARY_LENGTH
        )

        # Check forbidden words defined
        assert len(FORBIDDEN_WORDS) > 0
        assert "반드시" in FORBIDDEN_WORDS
        assert "즉시" in FORBIDDEN_WORDS

        # Check length limits
        assert MAX_TITLE_LENGTH == 50
        assert MAX_SUMMARY_LENGTH == 200

    def test_agent_event_type_mapping(self):
        """각 Agent의 event_type 매핑 테스트."""
        from app.worker.pipelines.signal_agents.direct_agent import DirectSignalAgent
        from app.worker.pipelines.signal_agents.industry_agent import IndustrySignalAgent
        from app.worker.pipelines.signal_agents.environment_agent import EnvironmentSignalAgent

        direct = DirectSignalAgent()
        industry = IndustrySignalAgent()
        environment = EnvironmentSignalAgent()

        # DIRECT: 8 event types
        direct_types = {
            "KYC_REFRESH", "INTERNAL_RISK_GRADE_CHANGE", "OVERDUE_FLAG_ON",
            "LOAN_EXPOSURE_CHANGE", "COLLATERAL_CHANGE", "OWNERSHIP_CHANGE",
            "GOVERNANCE_CHANGE", "FINANCIAL_STATEMENT_UPDATE"
        }
        assert direct.ALLOWED_EVENT_TYPES == direct_types

        # INDUSTRY: 1 event type
        assert "INDUSTRY_SHOCK" in industry.ALLOWED_EVENT_TYPES

        # ENVIRONMENT: 1 event type
        assert "POLICY_REGULATION_CHANGE" in environment.ALLOWED_EVENT_TYPES


# =============================================================================
# Sprint 3 Tests: Cross-Validation, Graceful Degradation, Concurrency Limit
# =============================================================================

class TestSprint3:
    """Sprint 3: 품질 및 안정성 기능 테스트."""

    def test_orchestrator_initialization(self):
        """SignalAgentOrchestrator 초기화 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import (
            SignalAgentOrchestrator, reset_signal_orchestrator
        )

        reset_signal_orchestrator()

        orchestrator = SignalAgentOrchestrator(
            parallel_mode=True,
            max_workers=3,
            enable_concurrency_limit=True,
            agent_timeout=60.0
        )

        assert orchestrator.parallel_mode is True
        assert orchestrator.max_workers == 3
        assert orchestrator.agent_timeout == 60.0
        assert orchestrator._concurrency_limiter is not None

        orchestrator.close()

    def test_concurrency_limiter_singleton(self):
        """P0-1, P2-4 Fix: ProviderConcurrencyLimiter 싱글톤 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import (
            ProviderConcurrencyLimiter, get_concurrency_limiter
        )

        limiter1 = get_concurrency_limiter()
        limiter2 = get_concurrency_limiter()

        assert limiter1 is limiter2, "Should return same singleton instance"

    def test_concurrency_limiter_acquire_release(self):
        """P0-2 Fix: Concurrency limiter acquire/release 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import get_concurrency_limiter

        limiter = get_concurrency_limiter()

        # Acquire slot
        acquired = limiter.acquire("claude", timeout=5.0)
        assert acquired is True

        # Check usage
        usage = limiter.get_usage()
        assert usage["claude"]["current"] >= 1

        # Release slot
        limiter.release("claude")

        # Usage should decrease
        usage_after = limiter.get_usage()
        assert usage_after["claude"]["current"] < usage["claude"]["current"]

    def test_deduplication_logic(self, sample_signals):
        """시그널 중복 제거 로직 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        # Add duplicate signal with lower confidence
        duplicate = sample_signals[0].copy()
        duplicate["confidence"] = "LOW"
        signals = sample_signals + [duplicate]

        deduplicated = orchestrator._deduplicate_signals(signals)

        # Should have 3 unique signals (duplicate removed)
        assert len(deduplicated) == 3

        # Higher confidence should be kept
        direct_signal = next(s for s in deduplicated if s["signal_type"] == "DIRECT")
        assert direct_signal["confidence"] == "HIGH"

        orchestrator.close()

    def test_cross_validation_empty_input(self):
        """P1-4 Fix: 빈 입력에 대한 cross-validation 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        # Test with empty list
        validated, conflicts = orchestrator._cross_validate_signals_enhanced([], {})

        assert validated == []
        assert conflicts == []

        orchestrator.close()

    def test_cross_validation_with_signals(self, sample_signals, sample_context):
        """Cross-validation 로직 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        validated, conflicts = orchestrator._cross_validate_signals_enhanced(
            sample_signals, sample_context
        )

        # All sample signals should pass validation
        assert len(validated) == 3

        orchestrator.close()

    def test_graceful_degradation_fallback(self, sample_context):
        """Graceful degradation fallback 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        # Modify context to trigger fallback
        context = sample_context.copy()
        context["snapshot_json"]["credit"]["loan_summary"]["overdue_flag"] = True

        fallback_signals = orchestrator._apply_direct_fallback(context)

        # Should generate overdue signal
        assert len(fallback_signals) >= 1
        overdue_signal = next(
            (s for s in fallback_signals if s["event_type"] == "OVERDUE_FLAG_ON"),
            None
        )
        assert overdue_signal is not None
        assert overdue_signal["is_fallback"] is True

        orchestrator.close()

    def test_agent_status_timeout_classification(self):
        """P1-1 Fix: AgentStatus.TIMEOUT 분류 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import AgentStatus

        assert AgentStatus.TIMEOUT.value == "timeout"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.SUCCESS.value == "success"
        assert AgentStatus.SKIPPED.value == "skipped"

    def test_is_better_signal_confidence_handling(self):
        """P2-2 Fix: confidence 비교 로직 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        # Test with various confidence values
        high = {"confidence": "HIGH", "evidence": [{}]}
        med = {"confidence": "MED", "evidence": [{}]}
        low = {"confidence": "LOW", "evidence": [{}]}
        none_conf = {"confidence": None, "evidence": [{}]}
        empty_conf = {"confidence": "", "evidence": [{}]}
        medium_alt = {"confidence": "MEDIUM", "evidence": [{}]}  # Alternative spelling

        # HIGH > MED
        assert orchestrator._is_better_signal(high, med) is True
        assert orchestrator._is_better_signal(med, high) is False

        # MED > LOW
        assert orchestrator._is_better_signal(med, low) is True

        # Any > None
        assert orchestrator._is_better_signal(low, none_conf) is True
        assert orchestrator._is_better_signal(low, empty_conf) is True

        # MEDIUM == MED (alternative spelling)
        assert orchestrator._is_better_signal(medium_alt, med) is False
        assert orchestrator._is_better_signal(med, medium_alt) is False

        orchestrator.close()

    def test_korean_tokenization(self):
        """P2-1 Fix: 한글 토큰화 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        orchestrator = SignalAgentOrchestrator()

        signals = [
            {"title": "엠케이전자 신규 투자 발표", "signal_type": "DIRECT"},
            {"title": "삼성전자 반도체 생산 확대", "signal_type": "DIRECT"},
        ]

        groups = orchestrator._group_signals_by_content(signals)

        # Should create groups based on Korean words
        assert len(groups) >= 1

        orchestrator.close()


# =============================================================================
# Sprint 4 Tests: Celery group() 분산 실행
# =============================================================================

class TestSprint4:
    """Sprint 4: Celery 분산 실행 테스트."""

    def test_celery_task_creation(self):
        """Celery 태스크 생성 테스트."""
        # This test verifies the task creation function exists
        from app.worker.pipelines.signal_agents.orchestrator import create_celery_tasks

        # Function should exist and be callable
        assert callable(create_celery_tasks)

    def test_orchestrator_metadata_serialization(self):
        """P2-3 Fix: OrchestratorMetadata 직렬화 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import OrchestratorMetadata

        metadata = OrchestratorMetadata(
            total_raw_signals=10,
            deduplicated_count=8,
            validated_count=7,
            conflicts_detected=1,
            needs_review_count=2,
            processing_time_ms=5000,
            partial_failure=True,
            failed_agents=["industry"],
            agent_results={"direct": {"status": "success"}}
        )

        # Test to_dict() method
        d = metadata.to_dict()

        assert d["total_raw_signals"] == 10
        assert d["deduplicated_count"] == 8
        assert d["validated_count"] == 7
        assert d["partial_failure"] is True
        assert "industry" in d["failed_agents"]
        assert "direct" in d["agent_results"]

    def test_agent_result_serialization(self):
        """P3-1 Fix: AgentResult 직렬화 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import AgentResult, AgentStatus

        result = AgentResult(
            agent_name="direct",
            status=AgentStatus.SUCCESS,
            signals=[{"title": "test"}],
            execution_time_ms=1000,
            retry_count=0
        )

        d = result.to_dict()

        assert d["agent_name"] == "direct"
        assert d["status"] == "success"  # Enum converted to value
        assert len(d["signals"]) == 1
        assert d["execution_time_ms"] == 1000

    def test_cross_validation_result_serialization(self):
        """P3-2 Fix: CrossValidationResult 직렬화 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import CrossValidationResult

        result = CrossValidationResult(
            signal={"title": "test signal"},
            is_valid=True,
            needs_review=False
        )

        d = result.to_dict()

        assert d["signal"]["title"] == "test signal"
        assert d["is_valid"] is True
        assert d["needs_review"] is False

    def test_execute_distributed_function_exists(self):
        """execute_distributed 함수 존재 확인."""
        from app.worker.pipelines.signal_agents.orchestrator import execute_distributed

        assert callable(execute_distributed)

    def test_orchestrator_context_manager(self):
        """P1-3 Fix: Orchestrator context manager 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import SignalAgentOrchestrator

        with SignalAgentOrchestrator() as orchestrator:
            assert orchestrator._executor is not None

        # After context exit, executor should be None
        assert orchestrator._executor is None

    def test_singleton_management(self):
        """싱글톤 관리 함수 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import (
            get_signal_orchestrator, reset_signal_orchestrator
        )

        reset_signal_orchestrator()

        orch1 = get_signal_orchestrator()
        orch2 = get_signal_orchestrator()

        assert orch1 is orch2, "Should return same singleton"

        reset_signal_orchestrator()

        orch3 = get_signal_orchestrator()
        assert orch3 is not orch1, "After reset, should create new instance"

        reset_signal_orchestrator()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """통합 테스트."""

    def test_full_orchestrator_flow_mock(self, sample_context):
        """전체 Orchestrator 플로우 테스트 (Mock LLM)."""
        from app.worker.pipelines.signal_agents.orchestrator import (
            SignalAgentOrchestrator, reset_signal_orchestrator
        )

        reset_signal_orchestrator()

        # Create orchestrator with sequential mode for predictable testing
        orchestrator = SignalAgentOrchestrator(
            parallel_mode=False,
            enable_concurrency_limit=False
        )

        # Mock the agent execute methods
        mock_signals = [
            {
                "signal_type": "DIRECT",
                "event_type": "LOAN_EXPOSURE_CHANGE",
                "impact_direction": "RISK",
                "impact_strength": "MED",
                "confidence": "HIGH",
                "title": "테스트 시그널",
                "summary": "테스트 요약",
                "evidence": [{"evidence_type": "INTERNAL_FIELD", "ref_type": "SNAPSHOT_KEYPATH", "ref_value": "/test"}]
            }
        ]

        with patch.object(orchestrator.direct_agent, 'execute', return_value=mock_signals):
            with patch.object(orchestrator.industry_agent, 'execute', return_value=[]):
                with patch.object(orchestrator.environment_agent, 'execute', return_value=[]):
                    signals, metadata = orchestrator.execute(sample_context)

        # Verify results
        assert metadata.total_raw_signals >= 1
        assert metadata.partial_failure is False
        # processing_time_ms can be 0 for very fast mock execution
        assert metadata.processing_time_ms >= 0

        orchestrator.close()
        reset_signal_orchestrator()

    def test_orchestrator_partial_failure_handling(self, sample_context):
        """부분 실패 처리 테스트."""
        from app.worker.pipelines.signal_agents.orchestrator import (
            SignalAgentOrchestrator, reset_signal_orchestrator
        )

        reset_signal_orchestrator()

        orchestrator = SignalAgentOrchestrator(
            parallel_mode=False,
            enable_concurrency_limit=False
        )

        # Mock one agent to fail
        with patch.object(orchestrator.direct_agent, 'execute', side_effect=Exception("Test error")):
            with patch.object(orchestrator.industry_agent, 'execute', return_value=[]):
                with patch.object(orchestrator.environment_agent, 'execute', return_value=[]):
                    signals, metadata = orchestrator.execute(sample_context)

        # Should have partial failure
        assert metadata.partial_failure is True
        assert "direct" in metadata.failed_agents

        orchestrator.close()
        reset_signal_orchestrator()

    def test_logging_consistency(self, sample_context, caplog):
        """P2-5 Fix: 로그 메시지 일관성 테스트."""
        import logging
        from app.worker.pipelines.signal_agents.orchestrator import (
            SignalAgentOrchestrator, reset_signal_orchestrator
        )

        reset_signal_orchestrator()

        with caplog.at_level(logging.INFO):
            orchestrator = SignalAgentOrchestrator(
                parallel_mode=False,
                enable_concurrency_limit=False
            )

            with patch.object(orchestrator.direct_agent, 'execute', return_value=[]):
                with patch.object(orchestrator.industry_agent, 'execute', return_value=[]):
                    with patch.object(orchestrator.environment_agent, 'execute', return_value=[]):
                        orchestrator.execute(sample_context)

        # Check logs contain corp_id and trace_id
        log_text = caplog.text
        assert "corp_id=" in log_text
        assert "trace_id=" in log_text

        orchestrator.close()
        reset_signal_orchestrator()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
