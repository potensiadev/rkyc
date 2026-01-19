# Peaky E2E Test Scenarios: Corp Profiling Pipeline

**Document Version**: v1.0
**Created**: 2026-01-19
**Author**: Senior QA Engineer (Silicon Valley, Banking/SaaS Specialist)
**Related PRD**: PRD-Corp-Profiling-Pipeline.md

---

## Overview

These tests target the hidden failure modes, race conditions, and edge cases that typically escape standard QA. Each scenario is designed to break the system in production-realistic ways.

---

## Category 1: Fallback Cascade Torture Tests

### TC-001: Perplexity Fails Mid-Response (Partial JSON)

**Objective**: Verify graceful handling when Perplexity returns truncated response

**Setup**:
- Mock Perplexity to return: `{"business_summary": "반도체 제조업`, (missing closing brace)
- Valid Gemini, Valid Claude

**Steps**:
1. Trigger profile for `8001-3719240`
2. Observe JSON parse failure handling
3. Verify fallback layer progression

**Expected**:
- Layer 1 marks as FAILED (not SUCCESS with corrupt data)
- No partial data persisted to DB
- `error_messages` contains "JSON parse error"
- Pipeline proceeds to Layer 4 (Perplexity is required)

**Peaky Edge**: Many systems will try to "fix" malformed JSON and create garbage data.

---

### TC-002: Gemini Succeeds But Returns Empty Validation

**Objective**: Verify behavior when Gemini responds successfully but provides no value

**Setup**:
```json
{
  "validation": {},
  "enrichment": {},
  "discrepancies": []
}
```

**Steps**:
1. Trigger profile
2. Verify Gemini marked as "success" in consensus_metadata
3. Verify pipeline continues without Gemini contribution

**Expected**:
- `gemini_success: true` (API call succeeded)
- `gemini_called: true`
- Profile built from Perplexity only
- `overall_confidence: MED` (no cross-validation possible)

**Peaky Edge**: Empty response ≠ failure. System should not fallback unnecessarily.

---

### TC-003: Claude Returns Valid JSON But Wrong Schema

**Objective**: Verify schema validation catches structure mismatch

**Setup**:
- Claude returns:
```json
{
  "company_name": "엠케이전자",
  "ceo": "홍길동",
  "revenue": 50000000000
}
```
(Missing required fields, wrong field names)

**Steps**:
1. Trigger profile
2. Observe schema validation failure
3. Verify Layer 3 fallback triggers

**Expected**:
- Layer 2 fails schema validation
- `error_messages` contains "Schema validation failed"
- Layer 3 (Rule-Based) takes over
- Perplexity data directly normalized

**Peaky Edge**: Valid JSON ≠ valid profile. Schema validation must be strict.

---

### TC-004: All LLMs Return Success But All Fields Are Null

**Objective**: Verify handling of "successful nothing"

**Setup**:
```json
{
  "ceo_name": null,
  "employee_count": null,
  "revenue_krw": null,
  "export_ratio_pct": null,
  "business_summary": null,
  ...
}
```

**Steps**:
1. Trigger profile for obscure company with no public info
2. Verify all-null profile is accepted
3. Check confidence assignment

**Expected**:
- Profile saved with all nulls
- `overall_confidence: HIGH` (confirmed absence of data)
- `consensus_metadata.fields_matched` includes null-null matches
- NO hallucination of default values

**Peaky Edge**: null is valid data. System should not invent data when none exists.

---

### TC-005: Circuit Breaker Opens During Active Request

**Objective**: Verify in-flight requests when circuit opens

**Setup**:
- Perplexity has 2 failures already
- Start profile request (Perplexity call in flight)
- Inject 3rd failure while request is pending

**Steps**:
1. Start corp profile for A
2. While A's Perplexity call is pending, trigger B which fails Perplexity
3. Circuit opens
4. A's request returns (late success)

**Expected**:
- A's request should complete (already in-flight)
- Circuit should be OPEN after A completes
- B should have used fallback
- Next request C should see OPEN circuit

**Peaky Edge**: Race between in-flight requests and circuit state changes.

---

## Category 2: Consensus Engine Edge Cases

### TC-006: Jaccard Similarity Boundary - Exactly 0.7

**Objective**: Verify behavior at exact threshold

**Setup**:
- Perplexity: `"반도체 소재 전문 제조업체 삼성 협력사"`
- Gemini validation claims different: `"반도체 부품 전문 제조업체 삼성 협력사"`

```
Tokens A: {반도체, 소재, 전문, 제조업체, 삼성, 협력사} = 6
Tokens B: {반도체, 부품, 전문, 제조업체, 삼성, 협력사} = 6
Intersection: {반도체, 전문, 제조업체, 삼성, 협력사} = 5
Union: {반도체, 소재, 부품, 전문, 제조업체, 삼성, 협력사} = 7
Jaccard: 5/7 = 0.714...
```

**Expected**:
- 0.714 >= 0.7 → MATCH
- No discrepancy flag
- Perplexity value adopted

**Peaky Edge**: Floating point comparison at boundary. Should use `>=` not `>`.

---

### TC-007: Jaccard With Korean Stopwords Only

**Objective**: Verify stopword-only strings don't crash

**Setup**:
- String A: `"의 및 등의 을를 은는"`
- String B: `"이가 에서 으로 의"`

**Steps**:
1. Run Jaccard similarity

**Expected**:
- Both token sets become empty after stopword removal
- Return 0.0 (not division by zero error)
- Treat as MISMATCH

**Peaky Edge**: Edge case where stopword removal leaves nothing.

---

### TC-008: Numeric Comparison With Zero Values

**Objective**: Verify division-by-zero protection in percentage diff

**Setup**:
- Perplexity: `export_ratio_pct: 0`
- Gemini: `export_ratio_pct: 5`
- Formula: `abs(a - b) / max(a, b)` = `5 / 5` = 100%

**Steps**:
1. Run consensus comparison

**Expected**:
- Should NOT match (100% diff > 10% threshold)
- discrepancy_fields includes "export_ratio_pct"
- Perplexity value (0) adopted

**Peaky Edge**: Zero handling in percentage calculations.

---

### TC-009: Country Exposure With Identical Values But Different Keys

**Objective**: Verify country code normalization

**Setup**:
- Perplexity: `{"중국": 30, "China": 20, "CN": 10}`
- Gemini: `{"CN": 30, "US": 20, "미국": 10}`

**Steps**:
1. Run consensus for country_exposure

**Expected**:
- System should normalize country codes before comparison
- "중국", "China", "CN" → same country
- "미국", "US", "USA" → same country
- OR explicitly fail with configuration error

**Peaky Edge**: Inconsistent country code formats from LLMs.

---

### TC-010: List Comparison With Duplicates

**Objective**: Verify duplicate handling in Jaccard for lists

**Setup**:
- Perplexity key_customers: `["삼성전자", "SK하이닉스", "삼성전자", "LG"]`
- Gemini key_customers: `["삼성전자", "SK하이닉스"]`

**Steps**:
1. Run Jaccard comparison

**Expected**:
- Duplicates should be deduplicated before comparison
- Perplexity unique: {삼성전자, SK하이닉스, LG} = 3
- Gemini unique: {삼성전자, SK하이닉스} = 2
- Intersection: 2, Union: 3
- Jaccard: 2/3 = 0.67 >= 0.5 (list threshold) → MATCH

**Peaky Edge**: Different thresholds for different field types.

---

## Category 3: Cache Timing Torture

### TC-011: Cache Expires During Processing

**Objective**: Verify behavior when cache expires mid-pipeline

**Setup**:
- Cache TTL set to 7 days
- Profile fetched_at = exactly 7 days ago minus 1 second
- Pipeline takes 5 seconds to complete

**Steps**:
1. Request profile at T=0 (cache valid by 1 second)
2. Cache lookup succeeds, returns cached
3. Background refresh triggered
4. At T=2, cache technically expires
5. Concurrent request at T=3

**Expected**:
- Request 1: Gets cached data immediately
- Request 2: Should ALSO get cached data (serving stale is OK)
- Background refresh should complete and update
- No duplicate parallel refreshes

**Peaky Edge**: TTL race condition between check and serve.

---

### TC-012: Concurrent Refresh Race Condition

**Objective**: Verify only one refresh runs for same corp_id

**Setup**:
- Cache expired for corp `8001-3719240`
- 5 concurrent requests arrive simultaneously

**Steps**:
1. Fire 5 parallel GET /profile requests
2. Observe Celery task queue
3. Verify LLM API call count

**Expected**:
- Only 1 Celery task created
- 4 requests wait for the 1 task to complete
- Perplexity called exactly once
- All 5 requests get same result

**Peaky Edge**: Task deduplication under concurrent load.

---

### TC-013: Cache Write Failure After Successful LLM

**Objective**: Verify response when cache write fails

**Setup**:
- Redis connection drops after LLM calls succeed
- Profile data ready to cache

**Steps**:
1. Trigger profile
2. LLM calls succeed
3. Mock Redis write failure
4. Observe response

**Expected**:
- API should still return successful profile
- Profile should be written to PostgreSQL
- Warning logged for cache failure
- Next request will re-query (cache miss)

**Peaky Edge**: Cache is not critical path. Failure should not fail request.

---

### TC-014: STALE Cache Served While Refresh Fails

**Objective**: Verify stale cache behavior when refresh fails

**Setup**:
- Cache exists but is 10 days old (stale)
- All LLMs are down (Circuit Breakers OPEN)

**Steps**:
1. Request profile
2. Cache check returns stale data
3. Background refresh attempted but fails
4. Verify response

**Expected**:
- Return stale cached data immediately
- `overall_confidence: STALE`
- Background refresh fails gracefully
- No error returned to user
- `consensus_metadata.fallback_layer: "LAYER_4"`

**Peaky Edge**: Degraded state should be transparent but functional.

---

## Category 4: Circuit Breaker Edge Cases

### TC-015: HALF_OPEN State Success Then Immediate Failure

**Objective**: Verify state transition edge case

**Setup**:
- Perplexity circuit in HALF_OPEN
- Next request succeeds (should transition to CLOSED)
- Immediately following request fails

**Steps**:
1. Verify circuit is HALF_OPEN
2. Request 1: Perplexity succeeds → CLOSED
3. Request 2: Perplexity fails
4. Verify circuit state

**Expected**:
- After request 1: CLOSED, failures=0
- After request 2: CLOSED, failures=1
- NOT immediately OPEN (need 3 consecutive failures)

**Peaky Edge**: Single failure after HALF_OPEN success should not re-open.

---

### TC-016: Circuit Breaker Cooldown Exact Boundary

**Objective**: Verify timing precision at cooldown end

**Setup**:
- Perplexity circuit OPEN at T=0
- Cooldown = 300 seconds
- Request at T=299.9

**Steps**:
1. Open circuit at T=0
2. Request at T=299.9 seconds
3. Request at T=300.0 seconds
4. Request at T=300.1 seconds

**Expected**:
- T=299.9: Circuit still OPEN, fallback used
- T=300.0: Circuit transitions to HALF_OPEN
- T=300.1: HALF_OPEN, test request sent

**Peaky Edge**: Exact boundary timing with floating point seconds.

---

### TC-017: All Three Circuits Open Simultaneously

**Objective**: Verify Layer 4 is reached when all providers fail

**Setup**:
- Perplexity: OPEN
- Gemini: OPEN
- Claude: OPEN

**Steps**:
1. Trigger profile
2. Observe layer progression

**Expected**:
- Layer 0: Cache miss
- Layer 1: Skip (Perplexity OPEN)
- Layer 1.5: Skip (Gemini OPEN, but also no Perplexity data)
- Layer 2: Skip (Claude OPEN)
- Layer 3: Cannot run (no data to merge)
- Layer 4: Return minimal profile or stale cache
- `fallback_layer: "LAYER_4"`
- `overall_confidence: NONE`

**Peaky Edge**: Complete external failure scenario.

---

## Category 5: Data Validation Attacks

### TC-018: export_ratio_pct = 101

**Objective**: Verify constraint validation on DB write

**Setup**:
- LLM returns `export_ratio_pct: 101`

**Steps**:
1. Trigger profile
2. Observe validation

**Expected**:
- DB has CHECK constraint: `export_ratio_pct >= 0 AND <= 100`
- Should be caught BEFORE DB write
- Clamp to 100 or reject with error
- NOT silently inserted

**Peaky Edge**: LLM can return invalid data. Must validate.

---

### TC-019: revenue_krw Exceeds BIGINT

**Objective**: Verify handling of astronomically large numbers

**Setup**:
- LLM returns `revenue_krw: 99999999999999999999999999` (exceeds BIGINT max)

**Steps**:
1. Trigger profile
2. Observe handling

**Expected**:
- Validation catches overflow BEFORE DB write
- Set to null or max safe value
- Log warning
- Profile still saved with other valid fields

**Peaky Edge**: LLM numerical hallucination.

---

### TC-020: SQL Injection via business_summary

**Objective**: Verify input sanitization

**Setup**:
- LLM returns: `business_summary: "반도체'; DROP TABLE rkyc_corp_profile;--"`

**Steps**:
1. Trigger profile
2. Verify DB integrity

**Expected**:
- String saved as-is (parameterized query)
- Table NOT dropped
- No SQL injection possible with ORM

**Peaky Edge**: Defense-in-depth against LLM-sourced injection.

---

### TC-021: XSS via executives[].name

**Objective**: Verify no XSS when displayed in frontend

**Setup**:
- LLM returns: `executives: [{"name": "<script>alert('xss')</script>", "position": "CEO"}]`

**Steps**:
1. Trigger profile
2. Fetch via API
3. Render in frontend

**Expected**:
- API returns raw string (backend doesn't sanitize display)
- Frontend MUST escape when rendering
- No script execution

**Peaky Edge**: Backend should store raw, frontend must escape.

---

### TC-022: Unicode Normalization Attack

**Objective**: Verify consistent handling of Unicode variants

**Setup**:
- Request 1: corp_name = `"삼성전자"` (standard)
- Request 2: corp_name = `"삼성전자"` (with invisible Unicode chars)
- Request 3: corp_name = `"삼성전자"` (fullwidth characters)

**Steps**:
1. Create profiles for all three
2. Check if deduplicated or treated as different

**Expected**:
- All should normalize to same canonical form
- Single profile, not three duplicates
- OR explicit rejection of non-standard Unicode

**Peaky Edge**: Unicode normalization for Korean text.

---

## Category 6: Timing & Ordering Attacks

### TC-023: Concurrent Requests for Different Corps - No Cross-Contamination

**Objective**: Verify request isolation under concurrent load

**Setup**:
- Two concurrent profile requests for DIFFERENT corps
- Corp A: Perplexity slow (5s)
- Corp B: Perplexity fast (1s)

**Steps**:
1. Request A starts at T=0
2. Request B starts at T=0.1
3. B completes at T=1.5
4. A completes at T=5.5
5. Verify no data mixing

**Expected**:
- A and B profiles are completely isolated
- No cross-contamination of corp data
- trace_ids are different and trackable

**Peaky Edge**: Request isolation under concurrent load.

---

### TC-024: Profile Update During Read

**Objective**: Verify read consistency during concurrent write

**Setup**:
- Profile exists for corp A
- Read request starts
- Update completes during read

**Steps**:
1. Start GET /profile (slow network, takes 2s)
2. POST /profile/refresh completes at T=1
3. GET response returns at T=2

**Expected**:
- GET returns consistent snapshot (either old or new, not mixed)
- No partial field updates visible
- PostgreSQL transaction isolation handles this

**Peaky Edge**: Read-write consistency.

---

### TC-025: Double Refresh Click

**Objective**: Verify debouncing of manual refresh

**Setup**:
- User clicks "정보 갱신" button rapidly 5 times

**Steps**:
1. Fire 5 POST /profile/refresh within 500ms
2. Observe behavior

**Expected**:
- Only 1 actual refresh triggered
- Subsequent requests return "already refreshing" or same task ID
- Rate limit applied: 429 if truly rapid
- Idempotent behavior

**Peaky Edge**: Prevent user-triggered API abuse.

---

## Category 7: Integration Edge Cases

### TC-026: Profile Refresh Triggers Signal Re-evaluation

**Objective**: Verify signal pipeline is notified of profile changes

**Setup**:
- Corp A has profile with `export_ratio_pct: 20%`
- ENVIRONMENT signals generated with this assumption
- Profile refresh changes to `export_ratio_pct: 45%`

**Steps**:
1. Initial profile with 20% export
2. Signal pipeline runs, no FX_RISK (< 30%)
3. Profile refreshes to 45%
4. Verify signal re-evaluation triggered

**Expected**:
- New profile should trigger conditional query re-selection
- FX_RISK, TRADE_BLOC now qualify
- New signals generated or existing updated
- Audit trail shows profile change → signal change

**Peaky Edge**: Profile changes should cascade to dependent signals.

---

### TC-027: Discrepancy Field Used in Evidence

**Objective**: Verify discrepancy handling in downstream evidence

**Setup**:
- Profile has `export_ratio_pct: 55` with `discrepancy: true`
- Signal uses this as evidence

**Steps**:
1. Profile with discrepancy field
2. Signal generated using discrepancy field
3. View signal detail

**Expected**:
- Evidence shows value with discrepancy indicator
- Signal confidence adjusted (MED not HIGH)
- UI shows warning icon on evidence

**Peaky Edge**: Discrepancy propagation through evidence chain.

---

### TC-028: Profile Deleted While Signals Reference It

**Objective**: Verify referential integrity handling

**Setup**:
- Profile exists for corp A
- Multiple signals reference profile fields as evidence
- Profile is deleted/replaced

**Steps**:
1. Create profile
2. Generate signals with profile evidence
3. Delete profile (admin action)
4. View signal detail

**Expected**:
- Signals should NOT be orphaned
- Evidence should show "Source no longer available" or cached value
- OR deletion should be blocked (FK constraint)

**Peaky Edge**: Data lifecycle management across tables.

---

## Category 8: Performance & Resource Edge Cases

### TC-029: Profile With Maximum JSONB Size

**Objective**: Verify handling of large nested JSON

**Setup**:
- Profile with:
  - 100 executives
  - 50 competitors
  - 200 macro_factors
  - 100 suppliers
  - Very long business_summary (10KB)

**Steps**:
1. Create oversized profile
2. Retrieve profile
3. Verify response time

**Expected**:
- Should either:
  - Accept with performance warning
  - Reject with size limit error
- Response time < 500ms for retrieval
- JSONB indexing still functional

**Peaky Edge**: Unbounded JSON growth.

---

### TC-030: Rate Limit Boundary - 10th Request in Minute

**Objective**: Verify exact rate limit enforcement

**Setup**:
- Rate limit: 10 refreshes per minute

**Steps**:
1. Fire 9 refresh requests in 59 seconds
2. Fire 10th request at second 59
3. Fire 11th request at second 59.5
4. Fire 12th request at second 61 (new minute window)

**Expected**:
- Requests 1-10: Accepted
- Request 11: Rejected (429)
- Request 12: Accepted (new window)

**Peaky Edge**: Rolling vs fixed window rate limiting.

---

## Summary Matrix

| Category | Test Count | Critical Bugs Targeted |
|----------|------------|----------------------|
| Fallback Cascade | 5 | Partial failures, schema mismatch |
| Consensus Engine | 5 | Boundary conditions, numeric edge cases |
| Cache Timing | 4 | Race conditions, stale data |
| Circuit Breaker | 3 | State transitions, timing |
| Data Validation | 5 | Injection, overflow, Unicode |
| Timing & Ordering | 3 | Concurrency, isolation |
| Integration | 3 | Cross-system cascade |
| Performance | 2 | Resource limits |

**Total: 30 Peaky Test Scenarios**

---

## Recommended Test Execution Priority

| Priority | Tests | Rationale |
|----------|-------|-----------|
| P0 (Blocking) | TC-001, TC-003, TC-017, TC-018, TC-020 | Data corruption, security |
| P1 (Critical) | TC-004, TC-006, TC-011, TC-012, TC-026 | Business logic correctness |
| P2 (High) | TC-002, TC-005, TC-015, TC-024, TC-027 | Edge case reliability |
| P3 (Medium) | Remaining | Completeness |

---

## Test Data Requirements

### Required Test Corporations

| corp_id | corp_name | Purpose |
|---------|-----------|---------|
| 8001-3719240 | 엠케이전자 | Standard happy path |
| TEST-OBSCURE-001 | 무명상사 | No public info (all null) |
| TEST-UNICODE-001 | 테스트유니코드 | Unicode edge cases |
| TEST-LARGE-001 | 대형데이터 | Large JSONB payloads |

### Required Mock Configurations

| Mock | Configuration |
|------|---------------|
| Perplexity Success | Full valid response |
| Perplexity Partial JSON | Truncated response |
| Perplexity Timeout | 30s+ delay |
| Gemini Empty | Valid but empty validation |
| Gemini Discrepancy | Different values |
| Claude Wrong Schema | Valid JSON, wrong fields |
| Redis Failure | Connection drop on write |

---

## Automation Notes

### Recommended Framework
- **Python**: pytest + pytest-asyncio
- **Mocking**: responses, aioresponses
- **Load Testing**: locust
- **E2E**: playwright (for frontend integration)

### Key Fixtures Needed
```python
@pytest.fixture
def mock_perplexity_partial_json():
    """Returns truncated JSON response"""
    ...

@pytest.fixture
def circuit_breaker_open_all():
    """Sets all circuit breakers to OPEN state"""
    ...

@pytest.fixture
def stale_cache_profile():
    """Creates a profile with 10-day-old cache"""
    ...
```

---

*Last Updated: 2026-01-19*
