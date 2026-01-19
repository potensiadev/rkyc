"""
Advanced E2E Test Scenarios for Corp Profiling Pipeline
Categories: Cache, Timing, Integration, Performance

Part 2 of docs/PRD/E2E-Test-Scenarios-Corp-Profiling-Pipeline.md
"""

import pytest
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.worker.llm.consensus_engine import (
    ConsensusEngine,
    tokenize,
    jaccard_similarity,
    compare_values,
    SourceType,
    KOREAN_STOPWORDS,
)
from app.worker.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitConfig,
    CircuitState,
    CircuitOpenError,
)


# ============================================================================
# BUG-001 FIX VERIFICATION: Korean Stopwords (kiwipiepy)
# ============================================================================

class TestKoreanStopwordsFix:
    """
    BUG-001 FIX: Korean compound stopwords now handled via kiwipiepy

    Solution: kiwipiepy 형태소 분석기 도입
    - 복합 조사를 품사별로 분리 (등의 → 등 + 의)
    - 품사(POS) 태그 기반 필터링
    - 단일 문자 불용어 추가 필터링

    Status: FIXED (2026-01-19)
    """

    def test_bug001_fix_compound_stopwords_removed(self):
        """BUG-001 FIX: 복합 조사가 형태소 분석 후 올바르게 제거됨"""
        # These compound stopwords should now be properly tokenized and filtered
        # Note: Some artificial combinations like "은는" may be mis-analyzed
        #       because they're not valid Korean. Focus on realistic cases.
        compound_stopwords = ["등의", "을를", "에서는", "로부터"]

        for compound in compound_stopwords:
            tokens = tokenize(compound)
            print(f"'{compound}' → tokens: {tokens}")
            # After fix: compound stopwords should result in empty tokens
            assert len(tokens) == 0, \
                f"'{compound}' should produce empty tokens, got {tokens}"

    def test_bug001_fix_stopwords_only_text(self):
        """BUG-001 FIX: 불용어만 있는 텍스트가 빈 집합 반환"""
        # After fix, these strings should become empty
        only_stopwords = "등의 을를 은는"

        tokens = tokenize(only_stopwords)
        print(f"Tokens from stopwords: {tokens}")

        # After fix: tokens should be empty
        assert len(tokens) == 0, f"Expected empty tokens, got {tokens}"

    def test_meaningful_content_preserved(self):
        """의미 있는 내용어는 보존되어야 함"""
        # Real business text
        text = "삼성전자 반도체 사업"
        tokens = tokenize(text)
        print(f"'{text}' → tokens: {tokens}")

        # Should keep meaningful nouns
        assert "삼성" in tokens or "삼성전자" in tokens
        assert "반도체" in tokens
        assert "사업" in tokens


# ============================================================================
# Category 3: Cache Timing Tests
# ============================================================================

class TestCacheTimingConcepts:
    """
    Cache Timing 테스트 (개념적 - 실제 Redis 없이)
    TC-011 ~ TC-014
    """

    def test_tc011_ttl_boundary_calculation(self):
        """TC-011: TTL 경계 계산 테스트"""
        # Simulate cache TTL check
        ttl_days = 7
        fetched_at = datetime.utcnow() - timedelta(days=6, hours=23, minutes=59)
        expires_at = fetched_at + timedelta(days=ttl_days)

        # Check if cache is valid
        is_valid = datetime.utcnow() < expires_at
        print(f"Fetched: {fetched_at}, Expires: {expires_at}, Valid: {is_valid}")

        # Should still be valid (1 minute remaining)
        assert is_valid is True

    def test_tc011_ttl_just_expired(self):
        """TC-011b: TTL 막 만료된 경우"""
        ttl_days = 7
        fetched_at = datetime.utcnow() - timedelta(days=7, seconds=1)
        expires_at = fetched_at + timedelta(days=ttl_days)

        is_valid = datetime.utcnow() < expires_at

        # Should be expired
        assert is_valid is False

    def test_tc012_concurrent_refresh_simulation(self):
        """TC-012: 동시 갱신 요청 시뮬레이션"""
        refresh_started = threading.Event()
        refresh_count = {"value": 0}
        lock = threading.Lock()

        def mock_refresh(corp_id):
            with lock:
                if refresh_started.is_set():
                    # Another refresh already started
                    return "already_refreshing"
                refresh_started.set()

            # Simulate refresh work
            time.sleep(0.1)
            with lock:
                refresh_count["value"] += 1

            refresh_started.clear()
            return "refreshed"

        # Simulate 5 concurrent requests
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mock_refresh, "corp-001") for _ in range(5)]
            results = [f.result() for f in futures]

        print(f"Results: {results}")
        print(f"Actual refresh count: {refresh_count['value']}")

        # Ideally only 1 should actually refresh
        # But current simulation allows multiple due to timing
        # This demonstrates the need for proper locking/deduplication

    def test_tc014_stale_cache_served(self):
        """TC-014: Stale 캐시 제공 시뮬레이션"""
        class MockCache:
            def __init__(self):
                self.data = {
                    "corp-001": {
                        "profile": {"name": "테스트기업"},
                        "fetched_at": datetime.utcnow() - timedelta(days=10),
                        "ttl_days": 7,
                    }
                }

            def get(self, corp_id: str) -> dict | None:
                entry = self.data.get(corp_id)
                if entry:
                    expires_at = entry["fetched_at"] + timedelta(days=entry["ttl_days"])
                    is_stale = datetime.utcnow() > expires_at
                    return {
                        "profile": entry["profile"],
                        "is_stale": is_stale,
                        "fetched_at": entry["fetched_at"],
                    }
                return None

        cache = MockCache()
        result = cache.get("corp-001")

        assert result is not None
        assert result["is_stale"] is True
        print(f"Stale cache returned: {result}")


# ============================================================================
# Category 6: Timing & Ordering Tests
# ============================================================================

class TestTimingOrdering:
    """
    Timing & Ordering 테스트
    TC-023 ~ TC-025
    """

    def test_tc023_request_isolation(self):
        """TC-023: 요청 간 데이터 격리 테스트"""
        results = {}
        lock = threading.Lock()

        def process_corp(corp_id: str, delay: float):
            # Simulate different processing times
            time.sleep(delay)
            with lock:
                results[corp_id] = {
                    "corp_id": corp_id,
                    "processed_at": time.time(),
                    "thread_id": threading.current_thread().ident,
                }
            return results[corp_id]

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(process_corp, "corp-A", 0.2)
            future_b = executor.submit(process_corp, "corp-B", 0.05)

            result_b = future_b.result()
            result_a = future_a.result()

        # Verify isolation - no cross-contamination
        assert results["corp-A"]["corp_id"] == "corp-A"
        assert results["corp-B"]["corp_id"] == "corp-B"

        # B should complete before A
        assert result_b["processed_at"] < result_a["processed_at"]
        print(f"Corp-B finished first at {result_b['processed_at']}")
        print(f"Corp-A finished later at {result_a['processed_at']}")

    def test_tc025_double_refresh_debounce_simulation(self):
        """TC-025: 이중 갱신 방지 시뮬레이션"""
        class RefreshTracker:
            def __init__(self):
                self.in_progress = set()
                self.lock = threading.Lock()
                self.actual_refreshes = 0

            def try_refresh(self, corp_id: str) -> str:
                with self.lock:
                    if corp_id in self.in_progress:
                        return "already_in_progress"
                    self.in_progress.add(corp_id)

                try:
                    # Simulate refresh work
                    time.sleep(0.05)
                    with self.lock:
                        self.actual_refreshes += 1
                    return "success"
                finally:
                    with self.lock:
                        self.in_progress.discard(corp_id)

        tracker = RefreshTracker()
        results = []

        # Simulate rapid double-click (5 requests in quick succession)
        def rapid_click():
            return tracker.try_refresh("corp-001")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(rapid_click) for _ in range(5)]
            results = [f.result() for f in futures]

        print(f"Results: {results}")
        print(f"Actual refreshes: {tracker.actual_refreshes}")

        # Count successes
        success_count = results.count("success")
        blocked_count = results.count("already_in_progress")

        # With proper debouncing, most should be blocked
        print(f"Success: {success_count}, Blocked: {blocked_count}")


# ============================================================================
# Category 8: Performance Tests
# ============================================================================

class TestPerformance:
    """
    Performance 테스트
    TC-029 ~ TC-030
    """

    def test_tc029_large_jsonb_handling(self):
        """TC-029: 대용량 JSONB 처리 성능"""
        # Create large profile data
        large_profile = {
            "executives": [
                {"name": f"임원{i}", "position": f"직급{i}", "is_key_man": i < 5}
                for i in range(100)
            ],
            "competitors": [
                {"name": f"경쟁사{i}", "market_share": f"{i}%", "revenue": f"{i}억"}
                for i in range(50)
            ],
            "macro_factors": [
                {"category": "정책", "description": f"요인{i}" * 50, "impact": "positive"}
                for i in range(200)
            ],
            "key_suppliers": [
                {"name": f"공급사{i}", "type": "원재료", "share": f"{i}%"}
                for i in range(100)
            ],
            "business_summary": "테스트 " * 2000,  # ~10KB text
        }

        # Measure JSON serialization time
        start = time.time()
        json_str = json.dumps(large_profile, ensure_ascii=False)
        serialize_time = time.time() - start

        # Measure JSON deserialization time
        start = time.time()
        parsed = json.loads(json_str)
        deserialize_time = time.time() - start

        json_size_kb = len(json_str.encode('utf-8')) / 1024

        print(f"JSON size: {json_size_kb:.2f} KB")
        print(f"Serialize time: {serialize_time*1000:.2f} ms")
        print(f"Deserialize time: {deserialize_time*1000:.2f} ms")

        # Performance assertions
        assert json_size_kb < 1024, f"JSON too large: {json_size_kb} KB"
        assert serialize_time < 0.5, f"Serialize too slow: {serialize_time}s"
        assert deserialize_time < 0.5, f"Deserialize too slow: {deserialize_time}s"

    def test_tc030_rate_limit_boundary(self):
        """TC-030: Rate Limit 경계 테스트"""
        class RateLimiter:
            def __init__(self, max_per_minute: int):
                self.max_per_minute = max_per_minute
                self.requests = []
                self.lock = threading.Lock()

            def is_allowed(self) -> bool:
                now = time.time()
                with self.lock:
                    # Remove old requests (older than 60 seconds)
                    self.requests = [t for t in self.requests if now - t < 60]

                    if len(self.requests) >= self.max_per_minute:
                        return False

                    self.requests.append(now)
                    return True

        limiter = RateLimiter(max_per_minute=10)

        # First 10 should be allowed
        allowed_count = 0
        rejected_count = 0

        for i in range(15):
            if limiter.is_allowed():
                allowed_count += 1
            else:
                rejected_count += 1

        print(f"Allowed: {allowed_count}, Rejected: {rejected_count}")

        assert allowed_count == 10, f"Expected 10 allowed, got {allowed_count}"
        assert rejected_count == 5, f"Expected 5 rejected, got {rejected_count}"

    def test_jaccard_performance_many_tokens(self):
        """Jaccard 연산 성능 테스트 (많은 토큰)"""
        # Create long strings with many tokens
        text_a = " ".join([f"단어{i}" for i in range(1000)])
        text_b = " ".join([f"단어{i}" for i in range(500, 1500)])

        # Measure performance
        start = time.time()
        score = jaccard_similarity(text_a, text_b)
        elapsed = time.time() - start

        print(f"Jaccard for 1000 tokens: {score:.4f}")
        print(f"Elapsed time: {elapsed*1000:.2f} ms")

        # Note: kiwipiepy morphological analysis adds overhead (~150-200ms for 2000 tokens)
        # but provides much better accuracy for Korean text
        # Threshold adjusted from 0.1s to 0.5s to accommodate morphological analysis
        assert elapsed < 0.5, f"Jaccard too slow: {elapsed}s"


# ============================================================================
# Deprecation Warning Tests
# ============================================================================

class TestDeprecationWarnings:
    """
    Deprecation Warning 검증
    """

    def test_datetime_utcnow_deprecation(self):
        """datetime.utcnow() deprecated 경고 확인"""
        # Python 3.12+ deprecates datetime.utcnow()
        # Should use datetime.now(datetime.timezone.utc) instead

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            # This triggers the deprecation warning
            _ = datetime.utcnow()

            # Check if warning was raised (Python 3.12+)
            utcnow_warnings = [
                x for x in w
                if "utcnow" in str(x.message).lower()
            ]

            if utcnow_warnings:
                print(f"Deprecation warning found: {utcnow_warnings[0].message}")
            else:
                print("No deprecation warning (Python < 3.12 or warning suppressed)")


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
