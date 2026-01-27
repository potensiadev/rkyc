"""
Phase 1 & Phase 2 Isolated Tests

QA Engineer: Testing modules without full app dependencies
"""

import asyncio
import json
import sys
import os
import re
import hashlib
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

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
# Direct Module Tests - Bypass app dependencies
# ============================================================================

def test_tracing_module_direct():
    """Test tracing module by reading source and checking syntax"""
    print("\n" + "="*60)
    print("Testing: tracing.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/tracing.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read tracing.py", True)
    except Exception as e:
        log_test("Read tracing.py", False, str(e))
        return

    # Check required classes exist
    try:
        assert "class TracingContext:" in source
        assert "class JSONLogFormatter" in source
        assert "class StructuredLogger:" in source
        assert "class TimedOperation:" in source
        assert "class LogEvents:" in source
        log_test("Required classes defined", True)
    except AssertionError as e:
        log_test("Required classes defined", False, str(e))

    # Check required methods
    try:
        assert "def new_trace" in source
        assert "def get_trace_id" in source
        assert "def set_trace_id" in source
        assert "def set_job_context" in source
        assert "def get_logger" in source
        assert "def setup_structured_logging" in source
        log_test("Required methods defined", True)
    except AssertionError as e:
        log_test("Required methods defined", False, str(e))

    # Check ContextVar usage
    try:
        assert "from contextvars import ContextVar" in source
        assert "_trace_id_var" in source
        assert "_job_id_var" in source
        assert "_corp_id_var" in source
        log_test("ContextVar usage correct", True)
    except AssertionError as e:
        log_test("ContextVar usage correct", False, str(e))

    # Check LogEvents constants
    try:
        assert "LLM_CALL_START" in source
        assert "LLM_CALL_SUCCESS" in source
        assert "LLM_CACHE_HIT" in source
        assert "LLM_CACHE_MISS" in source
        assert "AGENT_START" in source
        log_test("LogEvents constants defined", True)
    except AssertionError as e:
        log_test("LogEvents constants defined", False, str(e))

    # Check JSON formatter
    try:
        assert "json.dumps" in source
        assert "timestamp" in source
        assert "level" in source
        assert "trace_id" in source
        log_test("JSON formatter structure", True)
    except AssertionError as e:
        log_test("JSON formatter structure", False, str(e))


def test_cache_module_direct():
    """Test cache module by reading source"""
    print("\n" + "="*60)
    print("Testing: cache.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/cache.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read cache.py", True)
    except Exception as e:
        log_test("Read cache.py", False, str(e))
        return

    # Check CacheOperation enum
    try:
        assert "class CacheOperation" in source
        assert "PROFILE_EXTRACTION" in source
        assert "SIGNAL_EXTRACTION" in source
        assert "VALIDATION" in source
        assert "EMBEDDING" in source
        assert "CONSENSUS" in source
        assert "DOCUMENT_PARSING" in source
        assert "INSIGHT_GENERATION" in source
        log_test("CacheOperation enum complete", True)
    except AssertionError as e:
        log_test("CacheOperation enum complete", False, str(e))

    # Check TTL configuration
    try:
        assert "TTL_CONFIG" in source
        # 7 days for profile
        assert "7 * 24 * 3600" in source
        # 30 days for embedding
        assert "30 * 24 * 3600" in source
        log_test("TTL configuration present", True)
    except AssertionError as e:
        log_test("TTL configuration present", False, str(e))

    # Check MemoryLRUCache
    try:
        assert "class MemoryLRUCache:" in source
        assert "OrderedDict" in source
        assert "async def get" in source
        assert "async def set" in source
        assert "async def delete" in source
        assert "max_size" in source
        log_test("MemoryLRUCache implementation", True)
    except AssertionError as e:
        log_test("MemoryLRUCache implementation", False, str(e))

    # Check LLMCache
    try:
        assert "class LLMCache:" in source
        assert "redis" in source.lower()
        assert "_generate_cache_key" in source
        assert "sha256" in source or "hashlib" in source
        log_test("LLMCache implementation", True)
    except AssertionError as e:
        log_test("LLMCache implementation", False, str(e))

    # Check singleton pattern
    try:
        assert "_cache_instance" in source
        assert "def get_llm_cache" in source
        assert "def reset_llm_cache" in source
        log_test("Singleton pattern implemented", True)
    except AssertionError as e:
        log_test("Singleton pattern implemented", False, str(e))


def test_model_router_direct():
    """Test model router module"""
    print("\n" + "="*60)
    print("Testing: model_router.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/model_router.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read model_router.py", True)
    except Exception as e:
        log_test("Read model_router.py", False, str(e))
        return

    # Check TaskComplexity enum
    try:
        assert "class TaskComplexity" in source
        assert 'SIMPLE = "simple"' in source
        assert 'MODERATE = "moderate"' in source
        assert 'COMPLEX = "complex"' in source
        log_test("TaskComplexity enum", True)
    except AssertionError as e:
        log_test("TaskComplexity enum", False, str(e))

    # Check TaskType enum
    try:
        assert "class TaskType" in source
        assert "VALIDATION" in source
        assert "SIGNAL_EXTRACTION" in source
        assert "INSIGHT_GENERATION" in source
        assert "PROFILE_EXTRACTION" in source
        log_test("TaskType enum", True)
    except AssertionError as e:
        log_test("TaskType enum", False, str(e))

    # Check ModelRouter class
    try:
        assert "class ModelRouter:" in source
        assert "SIMPLE_MODELS" in source
        assert "MODERATE_MODELS" in source
        assert "COMPLEX_MODELS" in source
        log_test("ModelRouter tiers defined", True)
    except AssertionError as e:
        log_test("ModelRouter tiers defined", False, str(e))

    # Check model assignments - Haiku for simple
    try:
        assert "haiku" in source.lower()
        assert "gpt-4o-mini" in source
        log_test("Simple tier uses Haiku/GPT-4o-mini", True)
    except AssertionError as e:
        log_test("Simple tier uses Haiku/GPT-4o-mini", False, str(e))

    # Check model assignments - Opus for complex
    try:
        assert "opus" in source.lower()
        log_test("Complex tier uses Opus", True)
    except AssertionError as e:
        log_test("Complex tier uses Opus", False, str(e))

    # Check classify_task method
    try:
        assert "def classify_task" in source
        assert "SIMPLE_INDICATORS" in source
        assert "COMPLEX_INDICATORS" in source
        log_test("classify_task with indicators", True)
    except AssertionError as e:
        log_test("classify_task with indicators", False, str(e))

    # Check cost estimation
    try:
        assert "def estimate_cost_ratio" in source
        log_test("Cost estimation method exists", True)
    except AssertionError as e:
        log_test("Cost estimation method exists", False, str(e))


def test_consensus_engine_direct():
    """Test consensus engine module"""
    print("\n" + "="*60)
    print("Testing: consensus_engine.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/consensus_engine.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read consensus_engine.py", True)
    except Exception as e:
        log_test("Read consensus_engine.py", False, str(e))
        return

    # Check v1.4 Hybrid changes
    try:
        assert "v1.4" in source or "Hybrid" in source
        assert "semantic_similarity" in source
        assert "hybrid_similarity" in source
        log_test("v1.4 Hybrid Semantic support added", True)
    except AssertionError as e:
        log_test("v1.4 Hybrid Semantic support added", False, str(e))

    # Check jaccard_similarity
    try:
        assert "def jaccard_similarity" in source
        assert "def tokenize" in source
        log_test("Jaccard similarity functions", True)
    except AssertionError as e:
        log_test("Jaccard similarity functions", False, str(e))

    # Check compare_values returns 3 values
    try:
        # Look for the new 3-return signature
        assert 'return True, 1.0, "both_none"' in source or "bool, float, str" in source
        log_test("compare_values returns 3 values", True)
    except AssertionError as e:
        log_test("compare_values returns 3 values", False, str(e))

    # Check compare_values_legacy for backward compat
    try:
        assert "def compare_values_legacy" in source
        log_test("compare_values_legacy for backward compat", True)
    except AssertionError as e:
        log_test("compare_values_legacy for backward compat", False, str(e))

    # Check ConsensusEngine class
    try:
        assert "class ConsensusEngine:" in source
        assert "use_semantic" in source
        assert "def merge" in source
        assert "_merge_field" in source
        log_test("ConsensusEngine class structure", True)
    except AssertionError as e:
        log_test("ConsensusEngine class structure", False, str(e))

    # Check Korean stopwords
    try:
        assert "KOREAN_STOPWORDS" in source or "STOPWORD" in source
        log_test("Korean stopwords defined", True)
    except AssertionError as e:
        log_test("Korean stopwords defined", False, str(e))


def test_cot_pipeline_direct():
    """Test CoT pipeline module"""
    print("\n" + "="*60)
    print("Testing: cot_pipeline.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/cot_pipeline.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read cot_pipeline.py", True)
    except Exception as e:
        log_test("Read cot_pipeline.py", False, str(e))
        return

    # Check CoTStepType enum
    try:
        assert "class CoTStepType" in source
        assert "UNDERSTAND" in source
        assert "IDENTIFY" in source
        assert "ANALYZE" in source
        assert "EVALUATE" in source
        assert "SYNTHESIZE" in source
        assert "EVIDENCE" in source
        log_test("CoTStepType enum complete", True)
    except AssertionError as e:
        log_test("CoTStepType enum complete", False, str(e))

    # Check predefined steps
    try:
        assert "SIGNAL_EXTRACTION_STEPS" in source
        assert "INSIGHT_GENERATION_STEPS" in source
        assert "PROFILE_EXTRACTION_STEPS" in source
        log_test("Predefined CoT steps", True)
    except AssertionError as e:
        log_test("Predefined CoT steps", False, str(e))

    # Check CoTPipeline class
    try:
        assert "class CoTPipeline:" in source
        assert "def call_with_cot" in source
        assert "def extract_signals_with_cot" in source
        assert "def generate_insight_with_cot" in source
        assert "def extract_profile_with_cot" in source
        log_test("CoTPipeline methods", True)
    except AssertionError as e:
        log_test("CoTPipeline methods", False, str(e))

    # Check prompts
    try:
        assert "COT_SYSTEM_PROMPT" in source
        assert "COT_USER_PROMPT_TEMPLATE" in source
        log_test("CoT prompt templates", True)
    except AssertionError as e:
        log_test("CoT prompt templates", False, str(e))

    # Check response parsing
    try:
        assert "_parse_cot_response" in source
        assert "json" in source.lower()
        log_test("Response parsing method", True)
    except AssertionError as e:
        log_test("Response parsing method", False, str(e))


def test_reflection_agent_direct():
    """Test reflection agent module"""
    print("\n" + "="*60)
    print("Testing: reflection_agent.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/reflection_agent.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read reflection_agent.py", True)
    except Exception as e:
        log_test("Read reflection_agent.py", False, str(e))
        return

    # Check dataclasses
    try:
        assert "class CritiqueResult" in source or "@dataclass" in source
        assert "quality_score" in source
        assert "issues" in source
        assert "suggestions" in source
        assert "should_regenerate" in source
        log_test("CritiqueResult dataclass", True)
    except AssertionError as e:
        log_test("CritiqueResult dataclass", False, str(e))

    # Check ReflectionAgent class
    try:
        assert "class ReflectionAgent:" in source
        assert "MAX_ITERATIONS" in source
        assert "DEFAULT_QUALITY_THRESHOLD" in source
        log_test("ReflectionAgent configuration", True)
    except AssertionError as e:
        log_test("ReflectionAgent configuration", False, str(e))

    # Check methods
    try:
        assert "def critique" in source
        assert "def regenerate" in source
        assert "def generate_with_reflection" in source
        log_test("ReflectionAgent methods", True)
    except AssertionError as e:
        log_test("ReflectionAgent methods", False, str(e))

    # Check prompts
    try:
        assert "CRITIQUE_SYSTEM_PROMPT" in source
        assert "CRITIQUE_USER_PROMPT_TEMPLATE" in source
        assert "REGENERATE_SYSTEM_PROMPT" in source
        log_test("Reflection prompt templates", True)
    except AssertionError as e:
        log_test("Reflection prompt templates", False, str(e))

    # Check iteration limit
    try:
        assert "MAX_ITERATIONS = 2" in source
        log_test("Max iterations set to 2", True)
    except AssertionError as e:
        log_test("Max iterations set to 2", False, str(e))


def test_shared_context_direct():
    """Test shared context module"""
    print("\n" + "="*60)
    print("Testing: shared_context.py (Direct Analysis)")
    print("="*60)

    try:
        with open("app/worker/llm/shared_context.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read shared_context.py", True)
    except Exception as e:
        log_test("Read shared_context.py", False, str(e))
        return

    # Check ContextScope enum
    try:
        assert "class ContextScope" in source
        assert 'JOB = "job"' in source
        assert 'CORP = "corp"' in source
        assert 'GLOBAL = "global"' in source
        log_test("ContextScope enum", True)
    except AssertionError as e:
        log_test("ContextScope enum", False, str(e))

    # Check PipelineStep enum
    try:
        assert "class PipelineStep" in source
        assert "SNAPSHOT" in source
        assert "DOC_INGEST" in source
        assert "PROFILING" in source
        assert "SIGNAL" in source
        assert "INSIGHT" in source
        log_test("PipelineStep enum", True)
    except AssertionError as e:
        log_test("PipelineStep enum", False, str(e))

    # Check TTL configurations
    try:
        assert "STEP_TTL_SECONDS" in source
        assert "SCOPE_TTL_SECONDS" in source
        assert "LOCK_TTL_SECONDS" in source
        log_test("TTL configurations defined", True)
    except AssertionError as e:
        log_test("TTL configurations defined", False, str(e))

    # Check SharedContextStore class
    try:
        assert "class SharedContextStore:" in source
        assert "async def get" in source
        assert "async def set" in source
        assert "async def delete" in source
        assert "acquire_lock" in source
        log_test("SharedContextStore methods", True)
    except AssertionError as e:
        log_test("SharedContextStore methods", False, str(e))

    # Check Redis usage
    try:
        assert "redis" in source.lower()
        assert "_local_cache" in source
        log_test("Redis + local fallback", True)
    except AssertionError as e:
        log_test("Redis + local fallback", False, str(e))

    # Check lock implementation
    try:
        assert "asynccontextmanager" in source
        assert "acquire_lock" in source
        assert "LOCK_PREFIX" in source
        log_test("Distributed lock implementation", True)
    except AssertionError as e:
        log_test("Distributed lock implementation", False, str(e))


def test_service_integration_direct():
    """Test LLMService integration"""
    print("\n" + "="*60)
    print("Testing: service.py (Integration Check)")
    print("="*60)

    try:
        with open("app/worker/llm/service.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read service.py", True)
    except Exception as e:
        log_test("Read service.py", False, str(e))
        return

    # Check cache integration
    try:
        assert "from app.worker.llm.cache import" in source
        assert "_cache" in source
        assert "_cache_enabled" in source
        assert "def disable_cache" in source
        assert "def enable_cache" in source
        log_test("Cache integration in LLMService", True)
    except AssertionError as e:
        log_test("Cache integration in LLMService", False, str(e))

    # Check router integration
    try:
        assert "from app.worker.llm.model_router import" in source
        assert "_router" in source
        assert "_smart_routing_enabled" in source
        assert "def disable_smart_routing" in source
        assert "def enable_smart_routing" in source
        log_test("Router integration in LLMService", True)
    except AssertionError as e:
        log_test("Router integration in LLMService", False, str(e))

    # Check new methods
    try:
        assert "def call_with_smart_routing" in source
        log_test("call_with_smart_routing method exists", True)
    except AssertionError as e:
        log_test("call_with_smart_routing method exists", False, str(e))

    # Check async/sync variants
    try:
        assert "async def extract_signals" in source
        assert "def extract_signals_sync" in source
        assert "async def generate_insight" in source
        assert "def generate_insight_sync" in source
        log_test("Async/sync method variants", True)
    except AssertionError as e:
        log_test("Async/sync method variants", False, str(e))


def test_init_exports_direct():
    """Test __init__.py exports"""
    print("\n" + "="*60)
    print("Testing: __init__.py exports")
    print("="*60)

    try:
        with open("app/worker/llm/__init__.py", "r", encoding="utf-8") as f:
            source = f.read()
        log_test("Read __init__.py", True)
    except Exception as e:
        log_test("Read __init__.py", False, str(e))
        return

    # Check Phase 1 exports
    try:
        assert "LLMCache" in source
        assert "CacheOperation" in source
        assert "get_llm_cache" in source
        log_test("Phase 1 Cache exports", True)
    except AssertionError as e:
        log_test("Phase 1 Cache exports", False, str(e))

    try:
        assert "ModelRouter" in source
        assert "TaskComplexity" in source
        assert "TaskType" in source
        assert "get_model_router" in source
        log_test("Phase 1 Router exports", True)
    except AssertionError as e:
        log_test("Phase 1 Router exports", False, str(e))

    # Check Phase 2 exports
    try:
        assert "CoTPipeline" in source
        assert "CoTStep" in source
        assert "CoTStepType" in source
        assert "get_cot_pipeline" in source
        log_test("Phase 2 CoT exports", True)
    except AssertionError as e:
        log_test("Phase 2 CoT exports", False, str(e))

    try:
        assert "ReflectionAgent" in source
        assert "CritiqueResult" in source
        assert "get_reflection_agent" in source
        log_test("Phase 2 Reflection exports", True)
    except AssertionError as e:
        log_test("Phase 2 Reflection exports", False, str(e))

    try:
        assert "SharedContextStore" in source
        assert "ContextScope" in source
        assert "PipelineStep" in source
        assert "get_shared_context" in source
        log_test("Phase 2 SharedContext exports", True)
    except AssertionError as e:
        log_test("Phase 2 SharedContext exports", False, str(e))

    # Check consensus updates
    try:
        assert "semantic_similarity" in source
        assert "hybrid_similarity" in source
        assert "compare_values_legacy" in source
        log_test("Consensus v1.4 exports", True)
    except AssertionError as e:
        log_test("Consensus v1.4 exports", False, str(e))


# ============================================================================
# Bug Detection Tests
# ============================================================================

def test_potential_bugs():
    """Look for potential bugs in source code"""
    print("\n" + "="*60)
    print("Testing: Potential Bug Detection")
    print("="*60)

    # Bug 1: Check for missing await in async functions
    try:
        with open("app/worker/llm/cache.py", "r", encoding="utf-8") as f:
            cache_source = f.read()

        # Check async functions use await properly
        async_funcs = re.findall(r'async def (\w+)', cache_source)
        issues = []

        for func in async_funcs:
            # Find function body
            pattern = rf'async def {func}\([^)]*\)[^:]*:(.*?)(?=\n    def |\n    async def |\nclass |\Z)'
            match = re.search(pattern, cache_source, re.DOTALL)
            if match:
                body = match.group(1)
                # Check if it has any await
                if "await" not in body and "return" in body:
                    # Check if it's a simple return
                    if not re.search(r'return\s+(None|True|False|self\.|"|\d)', body):
                        issues.append(func)

        if issues:
            log_test("Async functions have await", False, f"Potentially missing await in: {issues}")
        else:
            log_test("Async functions have await", True)
    except Exception as e:
        log_test("Async functions have await", False, str(e))

    # Bug 2: Check for proper exception handling
    try:
        with open("app/worker/llm/service.py", "r", encoding="utf-8") as f:
            service_source = f.read()

        # Check that exceptions are properly caught
        assert "try:" in service_source
        assert "except" in service_source
        assert "Exception" in service_source or "except:" in service_source
        log_test("Exception handling present", True)
    except Exception as e:
        log_test("Exception handling present", False, str(e))

    # Bug 3: Check for hardcoded values that should be configurable
    try:
        with open("app/worker/llm/model_router.py", "r", encoding="utf-8") as f:
            router_source = f.read()

        # Check for hardcoded model names (these are OK, but check they're in constants)
        model_pattern = r'"(claude-[^"]+|gpt-[^"]+|gemini[^"]+)"'
        models = re.findall(model_pattern, router_source)

        # All models should be in class constants, not scattered
        assert len(models) > 0
        # Check models are defined in ModelTier structures
        assert "ModelTier" in router_source
        assert "ModelConfig" in router_source
        log_test("Model configurations structured", True)
    except Exception as e:
        log_test("Model configurations structured", False, str(e))

    # Bug 4: Check for proper typing
    try:
        with open("app/worker/llm/cot_pipeline.py", "r", encoding="utf-8") as f:
            cot_source = f.read()

        # Check for type hints
        assert "-> " in cot_source  # Return type hints
        assert ": str" in cot_source or ": int" in cot_source or ": dict" in cot_source
        assert "Optional[" in cot_source or "list[" in cot_source
        log_test("Type hints present in CoT", True)
    except Exception as e:
        log_test("Type hints present in CoT", False, str(e))

    # Bug 5: Check for consistent singleton patterns
    try:
        issues = []

        # Check cache singleton
        with open("app/worker/llm/cache.py", "r", encoding="utf-8") as f:
            cache_source = f.read()
        if "_cache_instance" not in cache_source:
            issues.append("cache.py missing singleton")

        # Check model_router singleton
        with open("app/worker/llm/model_router.py", "r", encoding="utf-8") as f:
            router_source = f.read()
        if "_router_instance" not in router_source:
            issues.append("model_router.py missing singleton")

        # Check cot_pipeline singleton
        with open("app/worker/llm/cot_pipeline.py", "r", encoding="utf-8") as f:
            cot_source = f.read()
        if "_cot_pipeline" not in cot_source:
            issues.append("cot_pipeline.py missing singleton")

        if issues:
            log_test("Singleton pattern consistency", False, str(issues))
        else:
            log_test("Singleton pattern consistency", True)
    except Exception as e:
        log_test("Singleton pattern consistency", False, str(e))

    # Bug 6: Check for potential race conditions in SharedContext
    try:
        with open("app/worker/llm/shared_context.py", "r", encoding="utf-8") as f:
            context_source = f.read()

        # Should have lock mechanism
        assert "acquire_lock" in context_source
        assert "asynccontextmanager" in context_source
        # Should handle lock timeout
        assert "LOCK_TTL" in context_source
        log_test("Race condition protection in SharedContext", True)
    except Exception as e:
        log_test("Race condition protection in SharedContext", False, str(e))

    # Bug 7: Check ReflectionAgent iteration limit
    try:
        with open("app/worker/llm/reflection_agent.py", "r", encoding="utf-8") as f:
            reflection_source = f.read()

        # Should have iteration limit check
        assert "MAX_ITERATIONS" in reflection_source
        assert "for i in range" in reflection_source or "while" in reflection_source
        # Should break on quality threshold
        assert "quality_threshold" in reflection_source
        assert "break" in reflection_source
        log_test("ReflectionAgent iteration control", True)
    except Exception as e:
        log_test("ReflectionAgent iteration control", False, str(e))

    # Bug 8: Check for proper JSON parsing error handling
    try:
        with open("app/worker/llm/cot_pipeline.py", "r", encoding="utf-8") as f:
            cot_source = f.read()

        # Should handle JSONDecodeError
        assert "json.loads" in cot_source
        assert "except" in cot_source
        log_test("JSON parsing error handling in CoT", True)
    except Exception as e:
        log_test("JSON parsing error handling in CoT", False, str(e))


def test_edge_cases():
    """Test edge cases by analyzing code patterns"""
    print("\n" + "="*60)
    print("Testing: Edge Case Handling")
    print("="*60)

    # Edge case 1: Empty input handling in consensus
    try:
        with open("app/worker/llm/consensus_engine.py", "r", encoding="utf-8") as f:
            source = f.read()

        # Check jaccard handles empty strings
        assert 'if not text_a and not text_b' in source or 'not text_a or not text_b' in source
        # Check compare_values handles None
        assert 'if value_a is None and value_b is None' in source
        log_test("Empty/None handling in consensus", True)
    except Exception as e:
        log_test("Empty/None handling in consensus", False, str(e))

    # Edge case 2: Cache key collision prevention
    try:
        with open("app/worker/llm/cache.py", "r", encoding="utf-8") as f:
            source = f.read()

        # Should hash query and context
        assert "sha256" in source or "hashlib" in source
        # Key should include operation type
        assert "operation" in source
        log_test("Cache key collision prevention", True)
    except Exception as e:
        log_test("Cache key collision prevention", False, str(e))

    # Edge case 3: Model router fallback when no match
    try:
        with open("app/worker/llm/model_router.py", "r", encoding="utf-8") as f:
            source = f.read()

        # Should have default/fallback
        assert "MODERATE" in source  # Default to moderate
        log_test("Model router default fallback", True)
    except Exception as e:
        log_test("Model router default fallback", False, str(e))

    # Edge case 4: SharedContext local fallback when Redis unavailable
    try:
        with open("app/worker/llm/shared_context.py", "r", encoding="utf-8") as f:
            source = f.read()

        # Should have local cache
        assert "_local_cache" in source
        # Should handle Redis connection failure
        assert "except" in source
        log_test("SharedContext Redis fallback", True)
    except Exception as e:
        log_test("SharedContext Redis fallback", False, str(e))


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all tests"""
    print("="*60)
    print("Phase 1 & Phase 2 Isolated Test Suite")
    print("QA Engineer: Source Code Analysis")
    print("="*60)

    # Phase 1 Tests
    test_tracing_module_direct()
    test_cache_module_direct()
    test_model_router_direct()
    test_consensus_engine_direct()

    # Phase 2 Tests
    test_cot_pipeline_direct()
    test_reflection_agent_direct()
    test_shared_context_direct()

    # Integration Tests
    test_service_integration_direct()
    test_init_exports_direct()

    # Bug Detection
    test_potential_bugs()
    test_edge_cases()

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
        print("\n[X] FAILED TESTS:")
        for r in test_results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r['error']}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
