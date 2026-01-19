-- ============================================
-- 데이터 애널리스트 확인용 검증 쿼리
-- Corp Data Sync Verification
-- 실행일: 2026-01-19
-- ============================================

-- ============================================
-- 1. 기대 데이터 (Expected Data)
-- ============================================
/*
| corp_id       | corp_name    | biz_no        | ceo_name | industry_code |
|---------------|--------------|---------------|----------|---------------|
| 4301-3456789  | 삼성전자     | 124-81-00998  | 전영현   | C21           |
| 6201-2345678  | 광주정밀기계 | 415-02-96323  | 강성우   | C29           |
| 4028-1234567  | 전북식품     | 418-01-55362  | 강동구   | C10           |
| 6701-4567890  | 휴림로봇     | 109-81-60401  | 김봉관   | D35           |
| 8000-7647330  | 동부건설     | 824-87-03495  | 윤진오   | F41           |
| 8001-3719240  | 엠케이전자   | 135-81-06406  | 현기진   | C26           |
*/

-- ============================================
-- 2. corp 테이블 검증
-- ============================================
SELECT
    '2. corp 테이블 검증' as test_name,
    corp_id,
    corp_name,
    biz_no,
    ceo_name,
    industry_code
FROM corp
ORDER BY corp_id;

-- ============================================
-- 3. rkyc_signal_index corp_name 검증 (Denormalized)
-- ============================================
SELECT
    '3. signal_index corp_name 검증' as test_name,
    corp_id,
    corp_name,
    COUNT(*) as signal_count
FROM rkyc_signal_index
GROUP BY corp_id, corp_name
ORDER BY corp_id;

-- ============================================
-- 4. rkyc_internal_snapshot JSON 내 기업정보 검증
-- ============================================
SELECT
    '4. snapshot JSON 검증' as test_name,
    corp_id,
    snapshot_json->'corp'->>'corp_name' as json_corp_name,
    snapshot_json->'corp'->>'biz_no' as json_biz_no,
    snapshot_json->'corp'->>'ceo_name' as json_ceo_name,
    snapshot_json->'corp'->>'industry_code' as json_industry_code
FROM rkyc_internal_snapshot
ORDER BY corp_id;

-- ============================================
-- 5. 전체 데이터 일관성 검증 (Cross-Table Check)
-- ============================================
SELECT
    '5. 데이터 일관성 검증' as test_name,
    c.corp_id,
    c.corp_name as corp_table,
    si.corp_name as signal_index,
    s.snapshot_json->'corp'->>'corp_name' as snapshot_json,
    CASE
        WHEN c.corp_name = COALESCE(si.corp_name, c.corp_name)
         AND c.corp_name = COALESCE(s.snapshot_json->'corp'->>'corp_name', c.corp_name)
        THEN '✅ OK'
        ELSE '❌ MISMATCH'
    END as status
FROM corp c
LEFT JOIN (
    SELECT DISTINCT corp_id, corp_name
    FROM rkyc_signal_index
) si ON c.corp_id = si.corp_id
LEFT JOIN rkyc_internal_snapshot s ON c.corp_id = s.corp_id
ORDER BY c.corp_id;

-- ============================================
-- 6. CEO Name 일관성 검증
-- ============================================
SELECT
    '6. CEO 일관성 검증' as test_name,
    c.corp_id,
    c.corp_name,
    c.ceo_name as corp_ceo,
    s.snapshot_json->'corp'->>'ceo_name' as snapshot_ceo,
    CASE
        WHEN c.ceo_name = s.snapshot_json->'corp'->>'ceo_name'
        THEN '✅ OK'
        ELSE '❌ MISMATCH'
    END as status
FROM corp c
LEFT JOIN rkyc_internal_snapshot s ON c.corp_id = s.corp_id
ORDER BY c.corp_id;

-- ============================================
-- 7. Biz No 일관성 검증
-- ============================================
SELECT
    '7. Biz No 일관성 검증' as test_name,
    c.corp_id,
    c.corp_name,
    c.biz_no as corp_biz_no,
    s.snapshot_json->'corp'->>'biz_no' as snapshot_biz_no,
    CASE
        WHEN c.biz_no = s.snapshot_json->'corp'->>'biz_no'
        THEN '✅ OK'
        ELSE '❌ MISMATCH'
    END as status
FROM corp c
LEFT JOIN rkyc_internal_snapshot s ON c.corp_id = s.corp_id
ORDER BY c.corp_id;

-- ============================================
-- 8. Signal/Evidence Count 검증
-- ============================================
SELECT
    '8. Signal/Evidence 수량 검증' as test_name,
    c.corp_id,
    c.corp_name,
    COUNT(DISTINCT sig.signal_id) as signal_count,
    COUNT(e.evidence_id) as total_evidence_count
FROM corp c
LEFT JOIN rkyc_signal sig ON c.corp_id = sig.corp_id
LEFT JOIN rkyc_evidence e ON sig.signal_id = e.signal_id
GROUP BY c.corp_id, c.corp_name
ORDER BY c.corp_id;

-- ============================================
-- 9. Dashboard Summary 검증
-- ============================================
SELECT
    '9. Dashboard Summary 검증' as test_name,
    counts_json,
    top_signals
FROM rkyc_dashboard_summary;

-- ============================================
-- 10. 최종 요약 (Summary Report)
-- ============================================
SELECT
    '10. 최종 요약' as test_name,
    (SELECT COUNT(*) FROM corp) as total_corps,
    (SELECT COUNT(*) FROM rkyc_signal) as total_signals,
    (SELECT COUNT(*) FROM rkyc_evidence) as total_evidences,
    (SELECT COUNT(*) FROM rkyc_internal_snapshot) as total_snapshots,
    (SELECT COUNT(*) FROM rkyc_signal_index) as total_signal_indexes;

-- ============================================
-- EXPECTED RESULTS (기대 결과)
-- ============================================
/*
✅ 검증 통과 조건:

1. corp 테이블: 6개 기업, 모두 이미지 데이터와 일치
2. signal_index: 각 corp_name이 corp 테이블과 동일
3. snapshot JSON: corp 정보가 corp 테이블과 동일
4. 전체 일관성: 모든 ✅ OK
5. CEO 일관성: 모든 ✅ OK
6. Biz No 일관성: 모든 ✅ OK
7. Signal 수량:
   - 엠케이전자: 5개
   - 동부건설: 6개
   - 전북식품: 5개
   - 광주정밀기계: 4개
   - 삼성전자: 5개
   - 휴림로봇: 4개
   - 총합: 29개
8. Dashboard Summary: top_signals에 삼성전자 포함 (익산바이오텍 X)
9. 총 수량: 6 corps, 29 signals, 29 evidences, 6 snapshots, 29 indexes
*/
