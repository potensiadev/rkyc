E2E Test Scenarios: Corp Profiling Pipeline for ENVIRONMENT Signal Enhancement                                  
  Executive Summary

  This document outlines comprehensive E2E test scenarios and 30 edge cases for the Corp Profiling Pipeline. The
   testing strategy covers the complete lifecycle from profile creation through conditional query execution to  
  signal generation with evidence.

  ---
  Test Environment Requirements
  ┌───────────────┬───────────────────────────────────────────────────────────┐
  │   Component   │                        Requirement                        │
  ├───────────────┼───────────────────────────────────────────────────────────┤
  │ Database      │ PostgreSQL 15+ with pgvector extension                    │
  ├───────────────┼───────────────────────────────────────────────────────────┤
  │ External APIs │ Perplexity API (mock available), LLM API (mock available) │
  ├───────────────┼───────────────────────────────────────────────────────────┤
  │ Test Data     │ 6 seed corporations + synthetic test data                 │
  ├───────────────┼───────────────────────────────────────────────────────────┤
  │ Concurrency   │ Support for parallel job execution testing                │
  └───────────────┴───────────────────────────────────────────────────────────┘
  ---
  E2E Test Scenarios

  Scenario 1: Happy Path - Full Profile Creation & Signal Generation

  Description: End-to-end flow from profile creation to ENVIRONMENT signal generation with proper grounding.    

  Preconditions:
  - Corporation 8001-3719240 (엠케이전자) exists in DB
  - No existing profile or profile is expired
  - Perplexity API accessible

  Test Steps:
  1. Trigger analysis job for corp_id 8001-3719240
  2. Verify PROFILING stage executes before EXTERNAL stage
  3. Verify Perplexity unified query is called
  4. Verify LLM structures response into Profile JSON
  5. Verify profile is saved to rkyc_corp_profile
  6. Verify conditional queries are selected based on profile attributes
  7. Verify ENVIRONMENT signals are generated with CORP_PROFILE evidence

  Expected Results:
  - Profile created with profile_confidence = HIGH/MED
  - export_ratio_pct >= 30 triggers FX_RISK, TRADE_BLOC queries
  - Evidence records contain evidence_type = CORP_PROFILE
  - Evidence ref_value contains JSON paths like /export_ratio_pct

  Acceptance Criteria:
  - Profile saved within 30 seconds
  - At least 3 ENVIRONMENT risk categories activated
  - All generated signals have at least 1 CORP_PROFILE evidence

  ---
  Scenario 2: Profile Cache Hit - Skip External Fetch

  Description: When valid cached profile exists, skip Perplexity API call.

  Preconditions:
  - Corporation 8001-3719240 has valid profile (fetched_at < expires_at)
  - expires_at is 3 days in future

  Test Steps:
  1. Trigger analysis job for corp_id 8001-3719240
  2. Monitor Perplexity API calls
  3. Verify profile cache hit in logs
  4. Verify PROFILING stage uses cached data

  Expected Results:
  - Zero Perplexity API calls made
  - PROFILING stage completes < 1 second
  - Cached profile data used for conditional query selection

  Acceptance Criteria:
  - No external API calls when cache valid
  - Cache hit rate > 80% for repeated analyses within 7 days

  ---
  Scenario 3: Profile TTL Expiration - Refresh Flow

  Description: Expired profile triggers fresh Perplexity search.

  Preconditions:
  - Corporation has profile with expires_at in the past

  Test Steps:
  1. Trigger analysis job
  2. Verify cache miss due to TTL expiration
  3. Verify new Perplexity search executed
  4. Verify old profile retained (for audit)
  5. Verify new profile saved with updated fetched_at

  Expected Results:
  - New profile record created
  - Old profile remains (not deleted)
  - updated_at timestamp refreshed

  ---
  Scenario 4: Conditional Query Selection - Export Heavy Corporation

  Description: High export ratio (>=30%) activates FX_RISK and TRADE_BLOC queries.

  Preconditions:
  - Profile with export_ratio_pct = 60

  Test Steps:
  1. Run conditional query selector with profile
  2. Verify FX_RISK category activated
  3. Verify TRADE_BLOC category activated
  4. Execute ENVIRONMENT queries
  5. Verify signals reference export ratio in evidence

  Expected Results:
  - FX_RISK signals generated with evidence snippet "수출 비중 60%"
  - Trade bloc related signals properly grounded

  ---
  Scenario 5: Conditional Query Selection - China Exposure

  Description: China exposure triggers GEOPOLITICAL, SUPPLY_CHAIN, REGULATION queries.

  Preconditions:
  - Profile with country_exposure = {"중국": 20, "미국": 30}

  Test Steps:
  1. Parse country_exposure JSON
  2. Detect "중국" key
  3. Activate GEOPOLITICAL, SUPPLY_CHAIN, REGULATION categories
  4. Generate grounded signals

  Expected Results:
  - All three categories produce signals
  - Evidence includes /country_exposure/중국
  - Signal description references specific China exposure percentage

  ---
  Scenario 6: Fallback Profile - Perplexity Search Failure

  Description: When Perplexity API fails, create industry-based default profile.

  Preconditions:
  - Perplexity API returns 5xx error
  - Corporation has industry_code = C26

  Test Steps:
  1. Trigger analysis job
  2. Perplexity API mock returns 503
  3. Verify fallback profile creation
  4. Verify is_fallback = true flag set
  5. Verify profile_confidence = LOW
  6. Verify basic ENVIRONMENT queries still run

  Expected Results:
  - Profile created with is_fallback = true
  - Business summary = "반도체 제조업 업체"
  - Confidence = LOW
  - Pipeline does not fail completely

  ---
  Scenario 7: Fallback Profile - Zero Search Results

  Description: Perplexity returns no results for obscure company.

  Preconditions:
  - Corporation TEST-OBSCURE-001 with no web presence
  - Perplexity returns empty results

  Test Steps:
  1. Trigger analysis
  2. Perplexity returns { "results": [] }
  3. Verify search_failed = true in profile
  4. Verify industry fallback applied
  5. Log warning for manual review

  Expected Results:
  - Profile with search_failed = true
  - Fallback profile confidence = LOW
  - Alert/log generated for ops team

  ---
  Scenario 8: API Endpoint - GET Profile

  Description: Retrieve corporation profile via REST API.

  Test Steps:
  1. GET /api/v1/corporations/8001-3719240/profile
  2. Verify response schema matches specification
  3. Verify is_expired calculated field

  Expected Results:
  {
    "corp_id": "8001-3719240",
    "business_summary": "...",
    "export_ratio_pct": 60,
    "country_exposure": {"중국": 20},
    "profile_confidence": "MED",
    "is_expired": false
  }

  ---
  Scenario 9: API Endpoint - Force Refresh Profile

  Description: Manual profile refresh bypassing cache.

  Test Steps:
  1. POST /api/v1/corporations/8001-3719240/profile/refresh
  2. Verify new Perplexity search triggered
  3. Verify profile updated regardless of TTL

  Expected Results:
  - New fetched_at timestamp
  - Fresh profile data
  - HTTP 200 with updated profile

  ---
  Scenario 10: Evidence Linkage - Multiple Profile Fields

  Description: Signal evidence references multiple profile fields.

  Test Steps:
  1. Generate signal for FX_RISK
  2. Profile has both export_ratio_pct=60 and country_exposure={"미국":30}
  3. Verify multiple evidence records created

  Expected Results:
  - Evidence 1: ref_value=/export_ratio_pct, snippet="수출 비중 60%"
  - Evidence 2: ref_value=/country_exposure/미국, snippet="미국 매출 30%"

  ---
  30 Edge Cases

  Category A: Input Validation (6 cases)
  ┌───────┬─────────────────────────────────┬────────────────────────────────┬─────────────────────────────────┐
  │   #   │            Edge Case            │             Input              │        Expected Behavior        │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-01 │ Invalid corp_id format          │ corp_id="INVALID"              │ Return 404, profile not created │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-02 │ Non-existent corporation        │ corp_id="9999-0000000"         │ Return 404, no profile attempt  │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-03 │ export_ratio_pct exceeds 100    │ LLM outputs                    │ Clamp to 100 or reject with     │
  │       │                                 │ export_ratio_pct=150           │ validation error                │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-04 │ Negative revenue_krw            │ LLM outputs                    │ Reject, set to null             │
  │       │                                 │ revenue_krw=-5000000000        │                                 │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-05 │ country_exposure with invalid   │ {"중국": 120}                  │ Clamp each value to 0-100 range │
  │       │ percentage                      │                                │                                 │
  ├───────┼─────────────────────────────────┼────────────────────────────────┼─────────────────────────────────┤
  │ EC-06 │ Empty business_summary          │ LLM returns                    │ Trigger fallback, flag for      │
  │       │                                 │ business_summary=""            │ review                          │
  └───────┴─────────────────────────────────┴────────────────────────────────┴─────────────────────────────────┘
  Category B: External API Failures (5 cases)
  ┌───────┬────────────────────────┬─────────────────────────────────┬─────────────────────────────────────────┐
  │   #   │       Edge Case        │            Scenario             │            Expected Behavior            │
  ├───────┼────────────────────────┼─────────────────────────────────┼─────────────────────────────────────────┤
  │ EC-07 │ Perplexity timeout     │ API hangs > 30 seconds          │ Cancel request, use fallback profile    │
  ├───────┼────────────────────────┼─────────────────────────────────┼─────────────────────────────────────────┤
  │ EC-08 │ Perplexity rate limit  │ Too many requests               │ Exponential backoff, retry 3x, then     │
  │       │ (429)                  │                                 │ fallback                                │
  ├───────┼────────────────────────┼─────────────────────────────────┼─────────────────────────────────────────┤
  │ EC-09 │ Perplexity partial     │ Connection drops mid-response   │ Detect incomplete JSON, retry once      │
  │       │ response               │                                 │                                         │
  ├───────┼────────────────────────┼─────────────────────────────────┼─────────────────────────────────────────┤
  │ EC-10 │ LLM hallucination      │ LLM returns unrealistic revenue │ Validator flags, reduce confidence to   │
  │       │ detection              │  (1경 원)                       │ LOW                                     │
  ├───────┼────────────────────────┼─────────────────────────────────┼─────────────────────────────────────────┤
  │ EC-11 │ LLM JSON parse failure │ Malformed JSON response         │ Retry with explicit JSON instruction,   │
  │       │                        │                                 │ then fallback                           │
  └───────┴────────────────────────┴─────────────────────────────────┴─────────────────────────────────────────┘
  Category C: Data Quality (5 cases)
  ┌───────┬─────────────────────────┬─────────────────────────────────────┬────────────────────────────────────┐
  │   #   │        Edge Case        │              Scenario               │         Expected Behavior          │
  ├───────┼─────────────────────────┼─────────────────────────────────────┼────────────────────────────────────┤
  │ EC-12 │ Homonym corporation     │ "삼성전자" matches Samsung          │ Use industry_code hint in query to │
  │       │ name                    │ Electronics AND other "삼성전자"    │  disambiguate                      │
  ├───────┼─────────────────────────┼─────────────────────────────────────┼────────────────────────────────────┤
  │ EC-13 │ Foreign company with    │ "한국IBM" returns IBM global data   │ Filter results with "한국"         │
  │       │ Korean name             │                                     │ keyword, validate industry         │
  ├───────┼─────────────────────────┼─────────────────────────────────────┼────────────────────────────────────┤
  │ EC-14 │ Defunct/merged company  │ Company merged 2 years ago          │ Detect "합병", "폐업" keywords,    │
  │       │                         │                                     │ set status=INACTIVE                │
  ├───────┼─────────────────────────┼─────────────────────────────────────┼────────────────────────────────────┤
  │ EC-15 │ Subsidiary vs parent    │ Search returns parent company       │ Validate company size aligns with  │
  │       │ data mix                │ financials                          │ expected scale                     │
  ├───────┼─────────────────────────┼─────────────────────────────────────┼────────────────────────────────────┤
  │ EC-16 │ Outdated information in │ Perplexity returns 3-year-old       │ Weight recent sources higher, note │
  │       │  search                 │ article                             │  data staleness                    │
  └───────┴─────────────────────────┴─────────────────────────────────────┴────────────────────────────────────┘
  Category D: Conditional Query Logic (5 cases)
  ┌───────┬──────────────────────┬────────────────────────────────────────────┬────────────────────────────────┐
  │   #   │      Edge Case       │                  Profile                   │   Expected Query Activation    │
  ├───────┼──────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ EC-17 │ All conditions met   │ export=60%, 중국=20%, materials=[steel],   │ ALL applicable categories (8+) │
  │       │                      │ overseas=[Vietnam]                         │  activated                     │
  ├───────┼──────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ EC-18 │ No conditions met    │ export=10%, country_exposure={},           │ Only industry-default queries  │
  │       │                      │ materials=[], overseas=[]                  │                                │
  ├───────┼──────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ EC-19 │ Borderline export    │ export_ratio_pct=29                        │ FX_RISK NOT activated          │
  │       │ ratio                │                                            │ (threshold is 30)              │
  ├───────┼──────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ EC-20 │ Multiple conflicting │ country_exposure={"중국":30, "미국":40,    │ All three country-specific     │
  │       │  countries           │ "러시아":10}                               │ query sets activated           │
  ├───────┼──────────────────────┼────────────────────────────────────────────┼────────────────────────────────┤
  │ EC-21 │ Industry mismatch    │ industry_code=A01 (농업) but profile       │ Log warning, use industry_code │
  │       │                      │ suggests manufacturing                     │  as authority                  │
  └───────┴──────────────────────┴────────────────────────────────────────────┴────────────────────────────────┘
  Category E: Caching & Concurrency (4 cases)
  #: EC-22
  Edge Case: Concurrent profile requests
  Scenario: Two jobs for same corp_id triggered simultaneously
  Expected Behavior: One wins, other uses cached result (no duplicate fetch)
  ────────────────────────────────────────
  #: EC-23
  Edge Case: Profile refresh during read
  Scenario: GET profile while refresh in progress
  Expected Behavior: Return stale profile, not partial data
  ────────────────────────────────────────
  #: EC-24
  Edge Case: TTL boundary condition
  Scenario: Profile expires exactly at request time
  Expected Behavior: Treat as expired, trigger refresh
  ────────────────────────────────────────
  #: EC-25
  Edge Case: Cache poisoning attempt
  Scenario: Direct DB manipulation of profile
  Expected Behavior: Validate profile hash/signature before use
  Category F: Evidence Generation (5 cases)
  #: EC-26
  Edge Case: Profile with all null optional fields
  Scenario: Only business_summary and profile_confidence present
  Expected Behavior: Evidence generated only for non-null fields
  ────────────────────────────────────────
  #: EC-27
  Edge Case: Deeply nested country_exposure
  Scenario: country_exposure={"아시아":{"중국":20,"베트남":10}}
  Expected Behavior: Flatten or reject nested structure
  ────────────────────────────────────────
  #: EC-28
  Edge Case: Unicode in key_materials
  Scenario: key_materials=["실리콘 웨이퍼", "リチウム電池"]
  Expected Behavior: Handle mixed Unicode, preserve in evidence
  ────────────────────────────────────────
  #: EC-29
  Edge Case: Evidence for fallback profile
  Scenario: Fallback profile used
  Expected Behavior: Evidence marked with is_fallback_derived=true
  ────────────────────────────────────────
  #: EC-30
  Edge Case: Signal confidence inheritance
  Scenario: Profile confidence=LOW
  Expected Behavior: Signal confidence cannot exceed profile confidence
  ---
  Edge Case Test Implementation Details

  EC-01: Invalid corp_id Format

  def test_invalid_corp_id_format():
      """Profile API should reject invalid corp_id format"""
      # Arrange
      invalid_corp_ids = [
          "INVALID",           # No dash
          "12345678901234567890",  # Too long
          "",                  # Empty
          "8001-371924A",      # Contains letter
          None,                # Null
      ]

      # Act & Assert
      for corp_id in invalid_corp_ids:
          response = client.get(f"/api/v1/corporations/{corp_id}/profile")
          assert response.status_code in [400, 404, 422]
          assert "profile_id" not in response.json()

  EC-07: Perplexity Timeout Handling

  @pytest.mark.asyncio
  async def test_perplexity_timeout_triggers_fallback():
      """When Perplexity times out, fallback profile should be created"""
      # Arrange
      with patch('app.worker.pipelines.corp_profiling.perplexity_search') as mock:
          mock.side_effect = asyncio.TimeoutError()

      # Act
      profile = await CorpProfilingPipeline().execute(
          corp_id="8001-3719240",
          corp_name="엠케이전자",
          industry_code="C26"
      )

      # Assert
      assert profile.is_fallback is True
      assert profile.search_failed is True
      assert profile.profile_confidence == ConfidenceLevel.LOW
      assert profile.business_summary == "반도체 제조업 업체"

  EC-12: Homonym Corporation Disambiguation

  def test_homonym_corporation_disambiguation():
      """Corporations with same name should be disambiguated by industry"""
      # Arrange
      # "대한전자" exists in both C26 (반도체) and G47 (소매)

      # Act
      profile_c26 = profiling_pipeline.execute(
          corp_name="대한전자",
          industry_code="C26"
      )

      profile_g47 = profiling_pipeline.execute(
          corp_name="대한전자",
          industry_code="G47"
      )

      # Assert
      assert profile_c26.business_summary != profile_g47.business_summary
      assert "반도체" in profile_c26.business_summary.lower() or "전자" in profile_c26.business_summary
      # Perplexity query should include industry hint
      mock_perplexity.assert_called_with(
          query=contains("반도체") | contains("C26")
      )

  EC-17: All Conditions Met - Maximum Query Activation

  def test_all_conditions_maximum_query_activation():
      """Profile meeting all conditions should activate all query categories"""
      # Arrange
      profile = CorpProfile(
          corp_id="8001-3719240",
          business_summary="글로벌 반도체 제조업체",
          export_ratio_pct=75,
          country_exposure={"중국": 25, "미국": 40, "베트남": 10},
          key_materials=["실리콘 웨이퍼", "PCB", "희토류"],
          overseas_operations=["베트남 하노이 공장", "중국 선전 R&D"],
          profile_confidence=ConfidenceLevel.HIGH,
      )

      # Act
      activated_categories = query_selector.select_categories(profile, "C26")

      # Assert
      expected_categories = {
          "FX_RISK",           # export >= 30%
          "TRADE_BLOC",        # export >= 30%, 미국
          "GEOPOLITICAL",      # 중국, 미국, overseas
          "SUPPLY_CHAIN",      # 중국, materials
          "REGULATION",        # 중국, 미국
          "COMMODITY",         # materials not empty
          "PANDEMIC_HEALTH",   # overseas not empty
          "POLITICAL_INSTABILITY",  # overseas
          "CYBER_TECH",        # C26
      }

      assert activated_categories >= expected_categories
      assert len(activated_categories) >= 8

  EC-22: Concurrent Profile Requests Race Condition

  @pytest.mark.asyncio
  async def test_concurrent_profile_requests_no_duplicate_fetch():
      """Concurrent requests for same corp should not duplicate API calls"""
      # Arrange
      perplexity_call_count = 0

      async def mock_perplexity(*args, **kwargs):
          nonlocal perplexity_call_count
          perplexity_call_count += 1
          await asyncio.sleep(0.5)  # Simulate API latency
          return {"results": [...]}

      with patch('perplexity_search', mock_perplexity):
          # Act - Fire 5 concurrent requests
          tasks = [
              CorpProfilingPipeline().execute("8001-3719240", "엠케이전자", "C26")
              for _ in range(5)
          ]
          profiles = await asyncio.gather(*tasks)

      # Assert
      assert perplexity_call_count == 1  # Only one actual API call
      assert all(p.profile_id == profiles[0].profile_id for p in profiles)

  EC-30: Signal Confidence Inheritance

  def test_signal_confidence_capped_by_profile_confidence():
      """Signal confidence should not exceed profile confidence"""
      # Arrange
      profile = CorpProfile(
          corp_id="8001-3719240",
          profile_confidence=ConfidenceLevel.LOW,  # LOW confidence
          is_fallback=True,
      )

      # Act
      signals = signal_generator.generate_environment_signals(
          profile=profile,
          external_events=[mock_high_confidence_event]
      )

      # Assert
      for signal in signals:
          assert signal.confidence <= ConfidenceLevel.LOW
          # Even if external event has HIGH confidence, signal is capped at LOW

  ---
  Test Data Requirements

  Required Test Corporations
  ┌──────────────────┬──────────────┬───────────────┬───────────────────────┐
  │     corp_id      │  corp_name   │ industry_code │     Test Purpose      │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ 8001-3719240     │ 엠케이전자   │ C26           │ Standard happy path   │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ 8000-7647330     │ 동부건설     │ F41           │ Construction industry │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ TEST-EXPORT-HIGH │ 수출중공업   │ C29           │ export_ratio=85%      │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ TEST-CHINA-HEAVY │ 중국무역상사 │ G46           │ 중국 exposure=70%     │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ TEST-OBSCURE-001 │ 무명상사     │ G47           │ No web presence       │
  ├──────────────────┼──────────────┼───────────────┼───────────────────────┤
  │ TEST-MERGED-001  │ 합병기업     │ C26           │ Defunct company       │
  └──────────────────┴──────────────┴───────────────┴───────────────────────┘
  Required Mock Responses

  1. Perplexity Success Response - Full profile data
  2. Perplexity Empty Response - { "results": [] }
  3. Perplexity Timeout - 30s+ delay
  4. LLM Malformed JSON - Invalid JSON output
  5. LLM Hallucinated Data - Unrealistic values

  ---
  Performance Benchmarks
  ┌─────────────────────────────┬────────────────────┬─────────────────────────────────┐
  │           Metric            │       Target       │       Measurement Method        │
  ├─────────────────────────────┼────────────────────┼─────────────────────────────────┤
  │ Profile creation time       │ < 30 seconds       │ End-to-end with real Perplexity │
  ├─────────────────────────────┼────────────────────┼─────────────────────────────────┤
  │ Cache hit latency           │ < 100ms            │ DB query only                   │
  ├─────────────────────────────┼────────────────────┼─────────────────────────────────┤
  │ Conditional query selection │ < 10ms             │ In-memory logic                 │
  ├─────────────────────────────┼────────────────────┼─────────────────────────────────┤
  │ Evidence generation         │ < 500ms per signal │ Including DB writes             │
  ├─────────────────────────────┼────────────────────┼─────────────────────────────────┤
  │ Concurrent requests         │ 10 jobs/minute     │ Load test with k6               │
  └─────────────────────────────┴────────────────────┴─────────────────────────────────┘
  ---
  Regression Test Suite

  Ensure these existing behaviors remain unchanged:

  1. ENVIRONMENT signals without profile - Legacy signals still generated
  2. Signal index denormalization - Dashboard queries unaffected
  3. Evidence type backward compatibility - Existing evidence types work
  4. Job status transitions - QUEUED → RUNNING → DONE flow preserved
  5. 8-stage pipeline order - PROFILING inserted correctly between DOC_INGEST and EXTERNAL

  ---
  Sign-off Checklist
  ┌───────────────────────────────┬────────────┬─────────┬────────┐
  │           Category            │ Test Count │  Owner  │ Status │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ E2E Scenarios                 │ 10         │ QA Lead │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - Input Validation │ 6          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - API Failures     │ 5          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - Data Quality     │ 5          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - Query Logic      │ 5          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - Concurrency      │ 4          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Edge Cases - Evidence         │ 5          │ QA      │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Performance Benchmarks        │ 5          │ DevOps  │ ⬜     │
  ├───────────────────────────────┼────────────┼─────────┼────────┤
  │ Regression Suite              │ 5          │ QA      │ ⬜     │
  └───────────────────────────────┴────────────┴─────────┴────────┘
  ---
  Document Version: 1.0
  Created: 2026-01-19
  Author: Senior QA Engineer (Banking/SaaS Specialist)
