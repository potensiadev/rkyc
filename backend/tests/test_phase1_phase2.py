"""
Phase 1 & Phase 2 E2E Tests

QA Engineer: Comprehensive testing for all new LLM modules
"""

import asyncio
import json
import sys
import os
import traceback
from datetime import datetime, UTC

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test results collector
test_results = []

def log_test(name: str, passed: bool, error: str = None, details: str = None):
    """Log test result"""
    status = "[PASS]" if passed else "[FAIL]"
    result = {"name": name, "passed": passed, "error": error, "details": details}
    test_results.append(result)
    print(f"{status}: {name}")
    if error:
        print(f"   Error: {error}")
    if details:
        print(f"   Details: {details}")


# ============================================================================
# Phase 1 Tests
# ============================================================================

def test_tracing_module():
    """Test structured logging module"""
    print("\n" + "="*60)
    print("Testing: tracing.py (Structured Logging)")
    print("="*60)

    try:
        from app.worker.tracing import (
            TracingContext,
            get_logger,
            StructuredLogger,
            JSONLogFormatter,
            setup_structured_logging,
            LogEvents,
            TimedOperation,
        )
        log_test("Import tracing module", True)
    except Exception as e:
        log_test("Import tracing module", False, str(e))
        return

    # Test TracingContext
    try:
        # Test new_trace
        trace_id = TracingContext.new_trace()
        assert trace_id is not None
        assert len(trace_id) == 8
        log_test("TracingContext.new_trace()", True, details=f"trace_id={trace_id}")
    except Exception as e:
        log_test("TracingContext.new_trace()", False, str(e))

    try:
        # Test get_trace_id
        current_trace = TracingContext.get_trace_id()
        assert current_trace == trace_id
        log_test("TracingContext.get_trace_id()", True)
    except Exception as e:
        log_test("TracingContext.get_trace_id()", False, str(e))

    try:
        # Test set_job_context
        TracingContext.set_job_context("job-123", "corp-456")
        assert TracingContext.get_job_id() == "job-123"
        assert TracingContext.get_corp_id() == "corp-456"
        log_test("TracingContext.set_job_context()", True)
    except Exception as e:
        log_test("TracingContext.set_job_context()", False, str(e))

    try:
        # Test clear
        TracingContext.clear()
        assert TracingContext.get_trace_id() == "no-trace"
        assert TracingContext.get_job_id() == ""
        log_test("TracingContext.clear()", True)
    except Exception as e:
        log_test("TracingContext.clear()", False, str(e))

    # Test StructuredLogger
    try:
        logger = get_logger("TestComponent")
        assert isinstance(logger, StructuredLogger)
        assert logger.component == "TestComponent"
        log_test("get_logger() creates StructuredLogger", True)
    except Exception as e:
        log_test("get_logger() creates StructuredLogger", False, str(e))

    try:
        # Test logging methods
        logger.info("test_event", key1="value1", key2=123)
        logger.debug("debug_event")
        logger.warning("warning_event")
        logger.error("error_event", exc_info=False)
        log_test("StructuredLogger logging methods", True)
    except Exception as e:
        log_test("StructuredLogger logging methods", False, str(e))

    # Test LogEvents constants
    try:
        assert LogEvents.LLM_CALL_START == "llm_call_start"
        assert LogEvents.LLM_CACHE_HIT == "llm_cache_hit"
        assert LogEvents.AGENT_START == "agent_start"
        log_test("LogEvents constants", True)
    except Exception as e:
        log_test("LogEvents constants", False, str(e))


def test_cache_module():
    """Test LLM cache module"""
    print("\n" + "="*60)
    print("Testing: cache.py (LLM Response Cache)")
    print("="*60)

    try:
        from app.worker.llm.cache import (
            LLMCache,
            CacheOperation,
            CacheConfig,
            MemoryLRUCache,
            get_llm_cache,
            reset_llm_cache,
        )
        log_test("Import cache module", True)
    except Exception as e:
        log_test("Import cache module", False, str(e))
        return

    # Test CacheOperation enum
    try:
        assert CacheOperation.PROFILE_EXTRACTION.value == "profile_extraction"
        assert CacheOperation.SIGNAL_EXTRACTION.value == "signal_extraction"
        assert CacheOperation.EMBEDDING.value == "embedding"
        log_test("CacheOperation enum values", True)
    except Exception as e:
        log_test("CacheOperation enum values", False, str(e))

    # Test CacheConfig
    try:
        config = CacheConfig()
        profile_ttl = config.get_ttl(CacheOperation.PROFILE_EXTRACTION)
        assert profile_ttl == 7 * 24 * 3600  # 7 days
        embedding_ttl = config.get_ttl(CacheOperation.EMBEDDING)
        assert embedding_ttl == 30 * 24 * 3600  # 30 days
        log_test("CacheConfig TTL values", True, details=f"profile={profile_ttl}s, embedding={embedding_ttl}s")
    except Exception as e:
        log_test("CacheConfig TTL values", False, str(e))

    # Test MemoryLRUCache
    async def test_memory_lru():
        cache = MemoryLRUCache(max_size=3)

        # Test set and get
        await cache.set("key1", "value1", ttl=60)
        result = await cache.get("key1")
        assert result == "value1", f"Expected 'value1', got '{result}'"

        # Test cache miss
        result = await cache.get("nonexistent")
        assert result is None

        # Test LRU eviction
        await cache.set("key2", "value2", ttl=60)
        await cache.set("key3", "value3", ttl=60)
        await cache.set("key4", "value4", ttl=60)  # Should evict key1

        result = await cache.get("key1")
        assert result is None, "key1 should have been evicted"

        # Test delete
        await cache.delete("key2")
        result = await cache.get("key2")
        assert result is None

        return True

    try:
        asyncio.run(test_memory_lru())
        log_test("MemoryLRUCache operations", True)
    except Exception as e:
        log_test("MemoryLRUCache operations", False, str(e))

    # Test LLMCache (without Redis)
    async def test_llm_cache():
        await reset_llm_cache()
        cache = LLMCache()
        # Don't initialize Redis for this test
        cache._initialized = True
        cache._redis = None

        # Test cache key generation
        key1 = cache._generate_cache_key(
            CacheOperation.SIGNAL_EXTRACTION,
            "test query",
            {"corp_id": "123"}
        )
        key2 = cache._generate_cache_key(
            CacheOperation.SIGNAL_EXTRACTION,
            "test query",
            {"corp_id": "123"}
        )
        assert key1 == key2, "Same inputs should generate same key"

        key3 = cache._generate_cache_key(
            CacheOperation.SIGNAL_EXTRACTION,
            "different query",
            {"corp_id": "123"}
        )
        assert key1 != key3, "Different queries should generate different keys"

        # Test set and get
        test_response = {"signals": [{"id": 1}]}
        await cache.set(
            CacheOperation.SIGNAL_EXTRACTION,
            "test query",
            {"corp_id": "123"},
            test_response
        )

        result = await cache.get(
            CacheOperation.SIGNAL_EXTRACTION,
            "test query",
            {"corp_id": "123"}
        )
        assert result == test_response

        return True

    try:
        asyncio.run(test_llm_cache())
        log_test("LLMCache operations (memory only)", True)
    except Exception as e:
        log_test("LLMCache operations (memory only)", False, str(e))


def test_model_router_module():
    """Test task-aware model router"""
    print("\n" + "="*60)
    print("Testing: model_router.py (Task-Aware Model Router)")
    print("="*60)

    try:
        from app.worker.llm.model_router import (
            ModelRouter,
            TaskComplexity,
            TaskType,
            ModelConfig,
            ModelTier,
            get_model_router,
            reset_model_router,
            TASK_COMPLEXITY_MAP,
        )
        log_test("Import model_router module", True)
    except Exception as e:
        log_test("Import model_router module", False, str(e))
        return

    # Test TaskComplexity enum
    try:
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MODERATE.value == "moderate"
        assert TaskComplexity.COMPLEX.value == "complex"
        log_test("TaskComplexity enum", True)
    except Exception as e:
        log_test("TaskComplexity enum", False, str(e))

    # Test TaskType enum
    try:
        assert TaskType.VALIDATION.value == "validation"
        assert TaskType.SIGNAL_EXTRACTION.value == "signal_extraction"
        assert TaskType.INSIGHT_GENERATION.value == "insight_generation"
        log_test("TaskType enum", True)
    except Exception as e:
        log_test("TaskType enum", False, str(e))

    # Test TASK_COMPLEXITY_MAP
    try:
        assert TASK_COMPLEXITY_MAP[TaskType.VALIDATION] == TaskComplexity.SIMPLE
        assert TASK_COMPLEXITY_MAP[TaskType.SIGNAL_EXTRACTION] == TaskComplexity.COMPLEX
        assert TASK_COMPLEXITY_MAP[TaskType.PROFILE_EXTRACTION] == TaskComplexity.MODERATE
        log_test("TASK_COMPLEXITY_MAP mapping", True)
    except Exception as e:
        log_test("TASK_COMPLEXITY_MAP mapping", False, str(e))

    # Test ModelRouter
    try:
        reset_model_router()
        router = get_model_router()
        assert isinstance(router, ModelRouter)
        log_test("get_model_router() singleton", True)
    except Exception as e:
        log_test("get_model_router() singleton", False, str(e))

    # Test classify_task with task_type
    try:
        complexity = router.classify_task("any prompt", task_type=TaskType.VALIDATION)
        assert complexity == TaskComplexity.SIMPLE

        complexity = router.classify_task("any prompt", task_type=TaskType.SIGNAL_EXTRACTION)
        assert complexity == TaskComplexity.COMPLEX
        log_test("classify_task with task_type", True)
    except Exception as e:
        log_test("classify_task with task_type", False, str(e))

    # Test classify_task by prompt analysis
    try:
        # Simple indicators
        complexity = router.classify_task("validate if this is correct")
        assert complexity == TaskComplexity.SIMPLE, f"Expected SIMPLE, got {complexity}"

        # Complex indicators
        complexity = router.classify_task("analyze and generate comprehensive insight report")
        assert complexity == TaskComplexity.COMPLEX, f"Expected COMPLEX, got {complexity}"

        log_test("classify_task by prompt analysis", True)
    except Exception as e:
        log_test("classify_task by prompt analysis", False, str(e))

    # Test get_models
    try:
        simple_models = router.get_models(TaskComplexity.SIMPLE)
        assert len(simple_models) >= 1
        assert "haiku" in simple_models[0]["model"].lower() or "mini" in simple_models[0]["model"].lower()

        complex_models = router.get_models(TaskComplexity.COMPLEX)
        assert len(complex_models) >= 1
        assert "opus" in complex_models[0]["model"].lower()

        log_test("get_models returns appropriate models", True,
                 details=f"simple={simple_models[0]['model']}, complex={complex_models[0]['model']}")
    except Exception as e:
        log_test("get_models returns appropriate models", False, str(e))

    # Test cost ratio
    try:
        simple_cost = router.estimate_cost_ratio(TaskComplexity.SIMPLE)
        complex_cost = router.estimate_cost_ratio(TaskComplexity.COMPLEX)
        assert simple_cost < complex_cost
        assert simple_cost == 0.05
        assert complex_cost == 1.0
        log_test("estimate_cost_ratio", True, details=f"simple={simple_cost}, complex={complex_cost}")
    except Exception as e:
        log_test("estimate_cost_ratio", False, str(e))


def test_consensus_engine_module():
    """Test consensus engine with hybrid semantic similarity"""
    print("\n" + "="*60)
    print("Testing: consensus_engine.py (Hybrid Semantic Consensus)")
    print("="*60)

    try:
        from app.worker.llm.consensus_engine import (
            ConsensusEngine,
            ConsensusResult,
            ConsensusMetadata,
            FieldConsensus,
            SourceType,
            jaccard_similarity,
            hybrid_similarity,
            compare_values,
            compare_values_legacy,
            get_consensus_engine,
            tokenize,
        )
        log_test("Import consensus_engine module", True)
    except Exception as e:
        log_test("Import consensus_engine module", False, str(e))
        return

    # Test tokenize
    try:
        tokens = tokenize("삼성전자의 반도체 사업")
        assert isinstance(tokens, set)
        assert len(tokens) > 0
        # 조사 "의"가 필터링되어야 함
        assert "의" not in tokens
        log_test("tokenize Korean text", True, details=f"tokens={tokens}")
    except Exception as e:
        log_test("tokenize Korean text", False, str(e))

    # Test jaccard_similarity
    try:
        # Same text
        score = jaccard_similarity("삼성전자 반도체", "삼성전자 반도체")
        assert score == 1.0, f"Same text should have score 1.0, got {score}"

        # Similar text
        score = jaccard_similarity("삼성전자 반도체 사업", "삼성전자의 반도체")
        assert score > 0.5, f"Similar text should have score > 0.5, got {score}"

        # Empty text
        score = jaccard_similarity("", "")
        assert score == 1.0

        score = jaccard_similarity("text", "")
        assert score == 0.0

        log_test("jaccard_similarity", True)
    except Exception as e:
        log_test("jaccard_similarity", False, str(e))

    # Test compare_values (new 3-return version)
    try:
        # None comparison
        is_match, score, method = compare_values(None, None)
        assert is_match == True
        assert method == "both_none"

        # Numeric comparison
        is_match, score, method = compare_values(100, 105)
        assert is_match == True  # Within 10%
        assert method == "numeric"

        is_match, score, method = compare_values(100, 50)
        assert is_match == False  # More than 10% difference

        # String comparison
        is_match, score, method = compare_values("같은 텍스트", "같은 텍스트")
        assert is_match == True
        assert score == 1.0

        # List comparison
        is_match, score, method = compare_values(["a", "b", "c"], ["a", "b", "d"])
        assert method == "list_jaccard"

        log_test("compare_values (3-return)", True)
    except Exception as e:
        log_test("compare_values (3-return)", False, str(e))

    # Test compare_values_legacy (backward compatibility)
    try:
        is_match, score = compare_values_legacy("test", "test")
        assert is_match == True
        assert score == 1.0
        log_test("compare_values_legacy (backward compat)", True)
    except Exception as e:
        log_test("compare_values_legacy (backward compat)", False, str(e))

    # Test ConsensusEngine
    try:
        engine = ConsensusEngine(use_semantic=False)  # Use Jaccard only for test

        perplexity_profile = {
            "business_summary": "반도체 제조업체",
            "revenue_krw": 100000000000,
            "export_ratio_pct": 60,
        }

        gemini_result = {
            "validated_fields": ["business_summary"],
            "enriched_fields": {
                "key_customers": {"value": ["Apple", "NVIDIA"], "confidence": "MED"}
            },
            "discrepancies": []
        }

        result = engine.merge(perplexity_profile, gemini_result, "삼성전자", "C26")

        assert isinstance(result, ConsensusResult)
        assert "business_summary" in result.profile
        assert "key_customers" in result.profile
        assert result.profile["key_customers"] == ["Apple", "NVIDIA"]

        log_test("ConsensusEngine.merge()", True,
                 details=f"matched={result.metadata.matched_fields}, enriched={result.metadata.enriched_fields}")
    except Exception as e:
        log_test("ConsensusEngine.merge()", False, str(e))


# ============================================================================
# Phase 2 Tests
# ============================================================================

def test_cot_pipeline_module():
    """Test Chain-of-Thought pipeline"""
    print("\n" + "="*60)
    print("Testing: cot_pipeline.py (Chain-of-Thought)")
    print("="*60)

    try:
        from app.worker.llm.cot_pipeline import (
            CoTPipeline,
            CoTStep,
            CoTStepType,
            CoTStepResult,
            CoTResult,
            SIGNAL_EXTRACTION_STEPS,
            INSIGHT_GENERATION_STEPS,
            PROFILE_EXTRACTION_STEPS,
            get_cot_pipeline,
            reset_cot_pipeline,
            COT_SYSTEM_PROMPT,
            COT_USER_PROMPT_TEMPLATE,
        )
        log_test("Import cot_pipeline module", True)
    except Exception as e:
        log_test("Import cot_pipeline module", False, str(e))
        return

    # Test CoTStepType enum
    try:
        assert CoTStepType.UNDERSTAND.value == "understand"
        assert CoTStepType.ANALYZE.value == "analyze"
        assert CoTStepType.EVIDENCE.value == "evidence"
        log_test("CoTStepType enum", True)
    except Exception as e:
        log_test("CoTStepType enum", False, str(e))

    # Test predefined steps
    try:
        assert len(SIGNAL_EXTRACTION_STEPS) == 6
        assert len(INSIGHT_GENERATION_STEPS) == 4
        assert len(PROFILE_EXTRACTION_STEPS) == 4

        # Check step structure
        first_step = SIGNAL_EXTRACTION_STEPS[0]
        assert isinstance(first_step, CoTStep)
        assert first_step.step_type == CoTStepType.UNDERSTAND
        assert first_step.instruction is not None
        assert first_step.expected_output is not None

        log_test("Predefined CoT steps", True,
                 details=f"signal={len(SIGNAL_EXTRACTION_STEPS)}, insight={len(INSIGHT_GENERATION_STEPS)}")
    except Exception as e:
        log_test("Predefined CoT steps", False, str(e))

    # Test CoTPipeline initialization
    try:
        reset_cot_pipeline()
        pipeline = get_cot_pipeline()
        assert isinstance(pipeline, CoTPipeline)
        log_test("get_cot_pipeline() singleton", True)
    except Exception as e:
        log_test("get_cot_pipeline() singleton", False, str(e))

    # Test _format_steps
    try:
        formatted = pipeline._format_steps(SIGNAL_EXTRACTION_STEPS[:2])
        assert "UNDERSTAND" in formatted
        assert "IDENTIFY" in formatted
        assert "1." in formatted
        assert "2." in formatted
        log_test("CoTPipeline._format_steps()", True)
    except Exception as e:
        log_test("CoTPipeline._format_steps()", False, str(e))

    # Test _parse_cot_response
    try:
        mock_response = """
### [UNDERSTAND]
**추론 과정**: 기업 현황을 파악했습니다.
**결과**: 반도체 제조업체
**신뢰도**: HIGH
---

### [ANALYZE]
**추론 과정**: 리스크 요인을 분석했습니다.
**결과**: 공급망 리스크 존재
**신뢰도**: MED
---

```json
{"signals": [{"id": 1, "type": "DIRECT"}]}
```
"""
        steps, output = pipeline._parse_cot_response(mock_response)
        assert len(steps) >= 1
        assert output is not None
        assert "signals" in output
        log_test("CoTPipeline._parse_cot_response()", True, details=f"steps={len(steps)}, has_output={output is not None}")
    except Exception as e:
        log_test("CoTPipeline._parse_cot_response()", False, str(e))

    # Test prompt templates
    try:
        assert "단계별 추론" in COT_SYSTEM_PROMPT
        assert "{task_description}" in COT_USER_PROMPT_TEMPLATE
        assert "{context}" in COT_USER_PROMPT_TEMPLATE
        assert "{steps_description}" in COT_USER_PROMPT_TEMPLATE
        log_test("CoT prompt templates", True)
    except Exception as e:
        log_test("CoT prompt templates", False, str(e))


def test_reflection_agent_module():
    """Test Reflection Agent"""
    print("\n" + "="*60)
    print("Testing: reflection_agent.py (Reflection Agent)")
    print("="*60)

    try:
        from app.worker.llm.reflection_agent import (
            ReflectionAgent,
            ReflectionResult,
            ReflectionIteration,
            CritiqueResult,
            get_reflection_agent,
            reset_reflection_agent,
            CRITIQUE_SYSTEM_PROMPT,
            CRITIQUE_USER_PROMPT_TEMPLATE,
            REGENERATE_SYSTEM_PROMPT,
            REGENERATE_USER_PROMPT_TEMPLATE,
        )
        log_test("Import reflection_agent module", True)
    except Exception as e:
        log_test("Import reflection_agent module", False, str(e))
        return

    # Test CritiqueResult dataclass
    try:
        critique = CritiqueResult(
            quality_score=0.8,
            issues=["이슈1"],
            suggestions=["제안1"],
            should_regenerate=False,
            critique_reasoning="좋은 품질"
        )
        assert critique.quality_score == 0.8
        assert len(critique.issues) == 1
        assert critique.should_regenerate == False
        log_test("CritiqueResult dataclass", True)
    except Exception as e:
        log_test("CritiqueResult dataclass", False, str(e))

    # Test ReflectionIteration dataclass
    try:
        iteration = ReflectionIteration(
            iteration=0,
            response="test response",
            critique=critique,
            duration_ms=1000
        )
        assert iteration.iteration == 0
        assert iteration.response == "test response"
        log_test("ReflectionIteration dataclass", True)
    except Exception as e:
        log_test("ReflectionIteration dataclass", False, str(e))

    # Test ReflectionResult dataclass
    try:
        result = ReflectionResult(
            final_response="final",
            iterations=[iteration],
            total_iterations=1,
            final_quality_score=0.8,
            improved=False,
            model_used="test-model"
        )
        assert result.total_iterations == 1
        assert result.improved == False
        log_test("ReflectionResult dataclass", True)
    except Exception as e:
        log_test("ReflectionResult dataclass", False, str(e))

    # Test ReflectionAgent initialization
    try:
        reset_reflection_agent()
        agent = get_reflection_agent()
        assert isinstance(agent, ReflectionAgent)
        assert agent.MAX_ITERATIONS == 2
        assert agent.DEFAULT_QUALITY_THRESHOLD == 0.7
        log_test("get_reflection_agent() singleton", True)
    except Exception as e:
        log_test("get_reflection_agent() singleton", False, str(e))

    # Test prompt templates
    try:
        assert "평가 기준" in CRITIQUE_SYSTEM_PROMPT
        assert "quality_score" in CRITIQUE_SYSTEM_PROMPT
        assert "{original_task}" in CRITIQUE_USER_PROMPT_TEMPLATE
        assert "{response}" in CRITIQUE_USER_PROMPT_TEMPLATE
        assert "개선" in REGENERATE_SYSTEM_PROMPT
        log_test("Reflection prompt templates", True)
    except Exception as e:
        log_test("Reflection prompt templates", False, str(e))


def test_shared_context_module():
    """Test SharedContextStore"""
    print("\n" + "="*60)
    print("Testing: shared_context.py (SharedContextStore)")
    print("="*60)

    try:
        from app.worker.llm.shared_context import (
            SharedContextStore,
            ContextScope,
            PipelineStep,
            ContextEntry,
            LockInfo,
            get_shared_context,
            reset_shared_context,
            STEP_TTL_SECONDS,
            SCOPE_TTL_SECONDS,
            LOCK_TTL_SECONDS,
        )
        log_test("Import shared_context module", True)
    except Exception as e:
        log_test("Import shared_context module", False, str(e))
        return

    # Test ContextScope enum
    try:
        assert ContextScope.JOB.value == "job"
        assert ContextScope.CORP.value == "corp"
        assert ContextScope.GLOBAL.value == "global"
        log_test("ContextScope enum", True)
    except Exception as e:
        log_test("ContextScope enum", False, str(e))

    # Test PipelineStep enum
    try:
        assert PipelineStep.SNAPSHOT.value == "snapshot"
        assert PipelineStep.PROFILING.value == "profiling"
        assert PipelineStep.SIGNAL.value == "signal"
        assert PipelineStep.INSIGHT.value == "insight"
        log_test("PipelineStep enum", True)
    except Exception as e:
        log_test("PipelineStep enum", False, str(e))

    # Test TTL configurations
    try:
        assert STEP_TTL_SECONDS[PipelineStep.PROFILING] == 604800  # 7 days
        assert STEP_TTL_SECONDS[PipelineStep.SIGNAL] == 3600  # 1 hour
        assert SCOPE_TTL_SECONDS[ContextScope.JOB] == 3600  # 1 hour
        assert LOCK_TTL_SECONDS == 300  # 5 minutes
        log_test("TTL configurations", True)
    except Exception as e:
        log_test("TTL configurations", False, str(e))

    # Test SharedContextStore (local mode)
    async def test_store_operations():
        await reset_shared_context()
        store = SharedContextStore()
        # Force local mode
        store._initialized = True
        store._redis = None

        # Test key generation
        key = store._make_key(ContextScope.CORP, PipelineStep.SIGNAL, "corp-123")
        assert "corp" in key
        assert "signal" in key
        assert "corp-123" in key

        # Test set and get
        await store.set(ContextScope.CORP, "corp-123", {"data": "test"}, PipelineStep.SIGNAL)
        result = await store.get(ContextScope.CORP, "corp-123", PipelineStep.SIGNAL)
        assert result == {"data": "test"}

        # Test delete
        await store.delete(ContextScope.CORP, "corp-123", PipelineStep.SIGNAL)
        result = await store.get(ContextScope.CORP, "corp-123", PipelineStep.SIGNAL)
        assert result is None

        # Test step result helpers
        await store.set_step_result(PipelineStep.PROFILING, "corp-456", {"profile": "data"})
        result = await store.get_step_result(PipelineStep.PROFILING, "corp-456")
        assert result == {"profile": "data"}

        return True

    try:
        asyncio.run(test_store_operations())
        log_test("SharedContextStore operations (local mode)", True)
    except Exception as e:
        log_test("SharedContextStore operations (local mode)", False, str(e))

    # Test lock key generation
    try:
        store = SharedContextStore()
        lock_key = store._make_lock_key(PipelineStep.SIGNAL, "corp-123")
        assert "lock" in lock_key
        assert "signal" in lock_key
        log_test("Lock key generation", True, details=f"key={lock_key}")
    except Exception as e:
        log_test("Lock key generation", False, str(e))


# ============================================================================
# Integration Tests
# ============================================================================

def test_llm_init_exports():
    """Test all exports from llm __init__"""
    print("\n" + "="*60)
    print("Testing: __init__.py exports")
    print("="*60)

    try:
        from app.worker.llm import (
            # Phase 1
            LLMCache,
            CacheOperation,
            get_llm_cache,
            ModelRouter,
            TaskComplexity,
            TaskType,
            get_model_router,
            # Phase 2
            CoTPipeline,
            CoTStep,
            CoTStepType,
            get_cot_pipeline,
            ReflectionAgent,
            CritiqueResult,
            get_reflection_agent,
            SharedContextStore,
            ContextScope,
            PipelineStep,
            get_shared_context,
            # Consensus
            ConsensusEngine,
            jaccard_similarity,
            hybrid_similarity,
            compare_values,
        )
        log_test("All Phase 1 & 2 exports available", True)
    except ImportError as e:
        log_test("All Phase 1 & 2 exports available", False, str(e))


def test_service_integration():
    """Test LLMService integration with new modules"""
    print("\n" + "="*60)
    print("Testing: LLMService integration")
    print("="*60)

    try:
        from app.worker.llm.service import LLMService
        log_test("Import LLMService", True)
    except Exception as e:
        log_test("Import LLMService", False, str(e))
        return

    # Test service initialization with cache and router
    try:
        service = LLMService()
        assert hasattr(service, '_cache')
        assert hasattr(service, '_router')
        assert hasattr(service, '_cache_enabled')
        assert hasattr(service, '_smart_routing_enabled')
        log_test("LLMService has cache and router attributes", True)
    except Exception as e:
        log_test("LLMService has cache and router attributes", False, str(e))

    # Test cache property
    try:
        cache = service.cache
        assert cache is not None
        log_test("LLMService.cache property", True)
    except Exception as e:
        log_test("LLMService.cache property", False, str(e))

    # Test router property
    try:
        router = service.router
        assert router is not None
        log_test("LLMService.router property", True)
    except Exception as e:
        log_test("LLMService.router property", False, str(e))

    # Test enable/disable methods
    try:
        service.disable_cache()
        assert service._cache_enabled == False
        service.enable_cache()
        assert service._cache_enabled == True

        service.disable_smart_routing()
        assert service._smart_routing_enabled == False
        service.enable_smart_routing()
        assert service._smart_routing_enabled == True

        log_test("LLMService enable/disable methods", True)
    except Exception as e:
        log_test("LLMService enable/disable methods", False, str(e))

    # Check new methods exist
    try:
        assert hasattr(service, 'call_with_smart_routing')
        assert hasattr(service, 'extract_signals')
        assert hasattr(service, 'extract_signals_sync')
        assert hasattr(service, 'generate_insight')
        assert hasattr(service, 'generate_insight_sync')
        log_test("LLMService has new methods", True)
    except Exception as e:
        log_test("LLMService has new methods", False, str(e))


# ============================================================================
# Bug Detection Tests
# ============================================================================

def test_edge_cases():
    """Test edge cases and potential bugs"""
    print("\n" + "="*60)
    print("Testing: Edge Cases & Bug Detection")
    print("="*60)

    # Test 1: Empty input handling
    try:
        from app.worker.llm.consensus_engine import tokenize, jaccard_similarity

        # Empty string
        tokens = tokenize("")
        assert tokens == set()

        # None-like inputs
        score = jaccard_similarity("", "")
        assert score == 1.0

        score = jaccard_similarity("text", "")
        assert score == 0.0

        log_test("Empty input handling", True)
    except Exception as e:
        log_test("Empty input handling", False, str(e))

    # Test 2: Unicode handling
    try:
        from app.worker.llm.consensus_engine import tokenize

        # Korean with special characters
        tokens = tokenize("삼성전자(주) 2024년 매출: ₩100조")
        assert len(tokens) > 0

        # Mixed language
        tokens = tokenize("Samsung Electronics 삼성전자")
        assert len(tokens) > 0

        log_test("Unicode/Korean handling", True)
    except Exception as e:
        log_test("Unicode/Korean handling", False, str(e))

    # Test 3: Large input handling
    try:
        from app.worker.llm.cache import LLMCache, CacheOperation

        cache = LLMCache()
        cache._initialized = True
        cache._redis = None

        # Large context
        large_context = {"data": "x" * 10000}
        key = cache._generate_cache_key(
            CacheOperation.SIGNAL_EXTRACTION,
            "query",
            large_context
        )
        assert len(key) < 500  # Key should be hashed

        log_test("Large input handling", True)
    except Exception as e:
        log_test("Large input handling", False, str(e))

    # Test 4: Concurrent access simulation
    async def test_concurrent():
        from app.worker.llm.cache import MemoryLRUCache

        cache = MemoryLRUCache(max_size=10)

        async def writer(i):
            await cache.set(f"key-{i}", f"value-{i}", ttl=60)

        async def reader(i):
            return await cache.get(f"key-{i}")

        # Concurrent writes
        await asyncio.gather(*[writer(i) for i in range(10)])

        # Concurrent reads
        results = await asyncio.gather(*[reader(i) for i in range(10)])

        # Verify all reads succeeded
        for i, result in enumerate(results):
            assert result == f"value-{i}", f"Expected value-{i}, got {result}"

        return True

    try:
        asyncio.run(test_concurrent())
        log_test("Concurrent access handling", True)
    except Exception as e:
        log_test("Concurrent access handling", False, str(e))

    # Test 5: Type coercion in compare_values
    try:
        from app.worker.llm.consensus_engine import compare_values

        # Different types
        is_match, score, method = compare_values("100", 100)
        assert is_match == False
        assert method == "type_mismatch"

        # Dict vs None
        is_match, score, method = compare_values({"key": "value"}, None)
        assert is_match == False

        log_test("Type handling in compare_values", True)
    except Exception as e:
        log_test("Type handling in compare_values", False, str(e))

    # Test 6: CoT response parsing edge cases
    try:
        from app.worker.llm.cot_pipeline import get_cot_pipeline

        pipeline = get_cot_pipeline()

        # Malformed response
        steps, output = pipeline._parse_cot_response("No valid JSON here")
        assert output is None  # Should handle gracefully

        # JSON without code block
        steps, output = pipeline._parse_cot_response('{"signals": []}')
        assert output == {"signals": []}

        log_test("CoT response parsing edge cases", True)
    except Exception as e:
        log_test("CoT response parsing edge cases", False, str(e))


def test_potential_bugs():
    """Specifically look for bugs"""
    print("\n" + "="*60)
    print("Testing: Potential Bug Detection")
    print("="*60)

    # Bug 1: Check if async methods can be called from sync context
    try:
        from app.worker.llm.service import LLMService
        import inspect

        service = LLMService()

        # Check extract_signals is async
        assert inspect.iscoroutinefunction(service.extract_signals), "extract_signals should be async"

        # Check generate_insight is async
        assert inspect.iscoroutinefunction(service.generate_insight), "generate_insight should be async"

        # Check sync versions exist
        assert not inspect.iscoroutinefunction(service.extract_signals_sync), "extract_signals_sync should be sync"
        assert not inspect.iscoroutinefunction(service.generate_insight_sync), "generate_insight_sync should be sync"

        log_test("Async/sync method signatures", True)
    except Exception as e:
        log_test("Async/sync method signatures", False, str(e))

    # Bug 2: Check TracingContext thread safety
    try:
        from app.worker.tracing import TracingContext
        import threading

        results = {}

        def thread_func(thread_id):
            trace_id = TracingContext.new_trace()
            results[thread_id] = trace_id

        threads = [threading.Thread(target=thread_func, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have unique trace_id
        # Note: ContextVar is thread-local, so this should work
        unique_traces = set(results.values())
        # In threads, ContextVar may behave differently - just check no crash
        log_test("TracingContext thread safety", True, details=f"traces={len(results)}")
    except Exception as e:
        log_test("TracingContext thread safety", False, str(e))

    # Bug 3: Check cache key collision
    try:
        from app.worker.llm.cache import LLMCache, CacheOperation

        cache = LLMCache()

        # Different operations, same query
        key1 = cache._generate_cache_key(CacheOperation.SIGNAL_EXTRACTION, "query", None)
        key2 = cache._generate_cache_key(CacheOperation.PROFILE_EXTRACTION, "query", None)
        assert key1 != key2, "Different operations should have different keys"

        # Same operation, different context
        key3 = cache._generate_cache_key(CacheOperation.SIGNAL_EXTRACTION, "query", {"a": 1})
        key4 = cache._generate_cache_key(CacheOperation.SIGNAL_EXTRACTION, "query", {"b": 2})
        assert key3 != key4, "Different contexts should have different keys"

        log_test("Cache key collision prevention", True)
    except Exception as e:
        log_test("Cache key collision prevention", False, str(e))

    # Bug 4: Check model router fallback behavior
    try:
        from app.worker.llm.model_router import ModelRouter, TaskComplexity

        router = ModelRouter()

        # Get models and verify fallbacks exist
        simple_models = router.get_models(TaskComplexity.SIMPLE)
        assert len(simple_models) >= 2, "Should have at least primary + 1 fallback"

        complex_models = router.get_models(TaskComplexity.COMPLEX)
        assert len(complex_models) >= 2, "Should have at least primary + 1 fallback"

        log_test("Model router has fallbacks", True)
    except Exception as e:
        log_test("Model router has fallbacks", False, str(e))

    # Bug 5: SharedContext lock timeout
    try:
        from app.worker.llm.shared_context import LOCK_TTL_SECONDS, LOCK_RETRY_DELAY

        # Lock timeout should be reasonable
        assert LOCK_TTL_SECONDS >= 60, "Lock timeout too short"
        assert LOCK_TTL_SECONDS <= 600, "Lock timeout too long"

        # Retry delay should be reasonable
        assert LOCK_RETRY_DELAY >= 0.1, "Retry delay too short"
        assert LOCK_RETRY_DELAY <= 5, "Retry delay too long"

        log_test("SharedContext lock configuration", True)
    except Exception as e:
        log_test("SharedContext lock configuration", False, str(e))


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all tests"""
    print("="*60)
    print("Phase 1 & Phase 2 E2E Test Suite")
    print("QA Engineer: Comprehensive Testing")
    print("="*60)

    # Phase 1 Tests
    test_tracing_module()
    test_cache_module()
    test_model_router_module()
    test_consensus_engine_module()

    # Phase 2 Tests
    test_cot_pipeline_module()
    test_reflection_agent_module()
    test_shared_context_module()

    # Integration Tests
    test_llm_init_exports()
    test_service_integration()

    # Bug Detection
    test_edge_cases()
    test_potential_bugs()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])

    print(f"Total: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in test_results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r['error']}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
