-- ============================================
-- rKYC Seed Data v2.0 (UUID Fixed)
-- PRD 14장, 19장 기준
-- 6개 기업 + Signal 3종 + Evidence 분리
-- ============================================

-- ============================================
-- 1. INDUSTRY MASTER (업종 마스터)
-- ============================================

INSERT INTO industry_master (industry_code, industry_name, industry_group, is_sensitive, tags) VALUES
('C10', '식품 제조업', 'MANUFACTURING', FALSE, ARRAY['food', 'consumer', 'agriculture']),
('C21', '의약품 제조업', 'MANUFACTURING', TRUE, ARRAY['pharma', 'healthcare', 'biotech']),
('C26', '전자부품 제조업', 'MANUFACTURING', FALSE, ARRAY['electronics', 'semiconductor', 'tech']),
('C29', '기계장비 제조업', 'MANUFACTURING', FALSE, ARRAY['machinery', 'equipment', 'industrial']),
('D35', '전기/가스 공급업', 'OTHER', TRUE, ARRAY['utility', 'energy', 'infrastructure']),
('F41', '종합건설업', 'CONSTRUCTION', FALSE, ARRAY['construction', 'realestate', 'infrastructure']);

-- ============================================
-- 2. CORP (기업 마스터) - 6개
-- ============================================

INSERT INTO corp (corp_id, corp_reg_no, corp_name, biz_no, industry_code, ceo_name) VALUES
-- 실제 기업 (2개)
('8001-3719240', '134511-0004412', '엠케이전자', '123-45-67890', 'C26', '김명규'),
('8000-7647330', '110111-0012345', '동부건설', '234-56-78901', 'F41', '박동호'),
-- 가상 기업 (4개)
('4028-1234567', '180111-0123456', '전북식품', '345-67-89012', 'C10', '이정민'),
('6201-2345678', '200111-0234567', '광주정밀기계', '456-78-90123', 'C29', '최광수'),
('4301-3456789', '180211-0345678', '익산바이오텍', '567-89-01234', 'C21', '박바이오'),
('6701-4567890', '200311-0456789', '나주태양에너지', '678-90-12345', 'D35', '송태양');

-- ============================================
-- 3. INTERNAL SNAPSHOT (PRD 7장 스키마 준수)
-- ============================================

-- 엠케이전자 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('11111111-0001-0001-0001-000000000001', '8001-3719240', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "8001-3719240",
    "corp_reg_no": "134511-0004412",
    "corp_name": "엠케이전자",
    "biz_no": "123-45-67890",
    "industry_code": "C26",
    "ceo_name": "김명규",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-11-15",
      "internal_risk_grade": "MED"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": false },
    "relationship_since": "2020-01-01"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 1200000000,
      "overdue_flag": false,
      "risk_grade_internal": "MED"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE"],
    "collateral_summary": { "collateral_count": 1 }
  },
  "derived_hints": {
    "industry_group": "MANUFACTURING",
    "is_sensitive_industry": false
  }
}', 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2');

-- 동부건설 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('22222222-0001-0001-0001-000000000001', '8000-7647330', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "8000-7647330",
    "corp_reg_no": "110111-0012345",
    "corp_name": "동부건설",
    "biz_no": "234-56-78901",
    "industry_code": "F41",
    "ceo_name": "박동호",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-10-20",
      "internal_risk_grade": "HIGH"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": true },
    "relationship_since": "2018-06-15"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 5800000000,
      "overdue_flag": true,
      "risk_grade_internal": "HIGH"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE", "DEPOSIT"],
    "collateral_summary": { "collateral_count": 3 }
  },
  "derived_hints": {
    "industry_group": "CONSTRUCTION",
    "is_sensitive_industry": false
  }
}', 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3');

-- 전북식품 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('33333333-0001-0001-0001-000000000001', '4028-1234567', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "4028-1234567",
    "corp_reg_no": "180111-0123456",
    "corp_name": "전북식품",
    "biz_no": "345-67-89012",
    "industry_code": "C10",
    "ceo_name": "이정민",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-09-10",
      "internal_risk_grade": "LOW"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": false },
    "relationship_since": "2019-03-20"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 800000000,
      "overdue_flag": false,
      "risk_grade_internal": "LOW"
    }
  },
  "collateral": {
    "has_collateral": false,
    "collateral_types": [],
    "collateral_summary": { "collateral_count": 0 }
  },
  "derived_hints": {
    "industry_group": "MANUFACTURING",
    "is_sensitive_industry": false
  }
}', 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4');

-- 광주정밀기계 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('44444444-0001-0001-0001-000000000001', '6201-2345678', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "6201-2345678",
    "corp_reg_no": "200111-0234567",
    "corp_name": "광주정밀기계",
    "biz_no": "456-78-90123",
    "industry_code": "C29",
    "ceo_name": "최광수",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-08-05",
      "internal_risk_grade": "MED"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": false },
    "relationship_since": "2021-05-10"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 500000000,
      "overdue_flag": false,
      "risk_grade_internal": "MED"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["MACHINERY"],
    "collateral_summary": { "collateral_count": 2 }
  },
  "derived_hints": {
    "industry_group": "MANUFACTURING",
    "is_sensitive_industry": false
  }
}', 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5');

-- 익산바이오텍 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('55555555-0001-0001-0001-000000000001', '4301-3456789', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "4301-3456789",
    "corp_reg_no": "180211-0345678",
    "corp_name": "익산바이오텍",
    "biz_no": "567-89-01234",
    "industry_code": "C21",
    "ceo_name": "박바이오",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-11-01",
      "internal_risk_grade": "MED"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": true },
    "relationship_since": "2022-02-15"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 2500000000,
      "overdue_flag": false,
      "risk_grade_internal": "MED"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["PATENT", "REAL_ESTATE"],
    "collateral_summary": { "collateral_count": 4 }
  },
  "derived_hints": {
    "industry_group": "MANUFACTURING",
    "is_sensitive_industry": true
  }
}', 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6');

-- 나주태양에너지 Snapshot
INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash) VALUES
('66666666-0001-0001-0001-000000000001', '6701-4567890', 1, '{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "6701-4567890",
    "corp_reg_no": "200311-0456789",
    "corp_name": "나주태양에너지",
    "biz_no": "678-90-12345",
    "industry_code": "D35",
    "ceo_name": "송태양",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-07-20",
      "internal_risk_grade": "LOW"
    }
  },
  "relationship": {
    "has_relationship": true,
    "products": { "deposit": true, "loan": true, "fx": false },
    "relationship_since": "2023-01-10"
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 1500000000,
      "overdue_flag": false,
      "risk_grade_internal": "LOW"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["SOLAR_PANEL", "LAND"],
    "collateral_summary": { "collateral_count": 5 }
  },
  "derived_hints": {
    "industry_group": "OTHER",
    "is_sensitive_industry": true
  }
}', 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1');

-- ============================================
-- 4. SNAPSHOT LATEST (최신 포인터)
-- ============================================

INSERT INTO rkyc_internal_snapshot_latest (corp_id, snapshot_id, snapshot_version, snapshot_hash) VALUES
('8001-3719240', '11111111-0001-0001-0001-000000000001', 1, 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'),
('8000-7647330', '22222222-0001-0001-0001-000000000001', 1, 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3'),
('4028-1234567', '33333333-0001-0001-0001-000000000001', 1, 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'),
('6201-2345678', '44444444-0001-0001-0001-000000000001', 1, 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5'),
('4301-3456789', '55555555-0001-0001-0001-000000000001', 1, 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6'),
('6701-4567890', '66666666-0001-0001-0001-000000000001', 1, 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1');

-- ============================================
-- 5. EXTERNAL EVENTS (산업/환경 이벤트)
-- ============================================

-- 산업 이벤트: 반도체 업황 (C26 영향)
INSERT INTO rkyc_external_event (event_id, source_type, title, summary, url, url_hash, publisher, published_at, tags, event_type, event_signature) VALUES
('eeeeeeee-0001-0001-0001-000000000001', 'NEWS', '글로벌 반도체 수요 둔화 지속...업계 구조조정 가속화',
'글로벌 반도체 시장의 수요 둔화가 2025년 상반기까지 지속될 것으로 전망됨. 메모리 반도체 가격 하락으로 인해 부품업체들의 실적 악화 우려가 커지고 있음.',
'https://www.etnews.com/20241220000123', 'a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1', '전자신문', '2024-12-20 09:00:00+09',
ARRAY['semiconductor', 'C26', 'market', 'slowdown'], 'INDUSTRY_SHOCK', 'b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1');

-- 산업 이벤트: 건설업 PF 위기 (F41 영향)
INSERT INTO rkyc_external_event (event_id, source_type, title, summary, url, url_hash, publisher, published_at, tags, event_type, event_signature) VALUES
('eeeeeeee-0002-0001-0001-000000000001', 'NEWS', '건설업 PF 대출 부실 우려 확대...중견사 유동성 위기',
'부동산 PF(프로젝트 파이낸싱) 부실 우려가 확산되면서 중견 건설사들의 유동성 위기가 가시화되고 있음. 금융당국은 건설업 전반에 대한 모니터링을 강화할 예정.',
'https://www.hankyung.com/economy/article/2024122012345', 'a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2', '한국경제', '2024-12-18 10:30:00+09',
ARRAY['construction', 'F41', 'PF', 'liquidity'], 'INDUSTRY_SHOCK', 'b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2');

-- 산업 이벤트: 식품 관세 (C10 영향)
INSERT INTO rkyc_external_event (event_id, source_type, title, summary, url, url_hash, publisher, published_at, tags, event_type, event_signature) VALUES
('eeeeeeee-0003-0001-0001-000000000001', 'NEWS', '미국, 한국산 식품에 25% 관세 부과 예고',
'미국 무역대표부가 한국산 가공식품에 대해 25% 관세를 부과할 예정이라고 발표. 수출 비중이 높은 식품 기업들의 수익성 악화가 우려됨.',
'https://www.yonhapnews.co.kr/bulletin/2024/12/19/news123', 'a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3', '연합뉴스', '2024-12-19 14:00:00+09',
ARRAY['tariff', 'food', 'C10', 'export', 'US'], 'INDUSTRY_SHOCK', 'b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3');

-- 환경 이벤트: 바이오 규제 강화 (C21 영향)
INSERT INTO rkyc_external_event (event_id, source_type, title, summary, url, url_hash, publisher, published_at, tags, event_type, event_signature) VALUES
('eeeeeeee-0004-0001-0001-000000000001', 'POLICY', '식약처, 바이오의약품 임상시험 규제 대폭 강화',
'식품의약품안전처가 바이오의약품 임상시험에 대한 규제를 대폭 강화하는 가이드라인을 발표. 임상 데이터 검증 기준이 강화되어 개발 일정 지연 가능성 있음.',
'https://www.mfds.go.kr/brd/m_99/view.do?seq=48123', 'a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4', '식품의약품안전처', '2024-12-15 11:00:00+09',
ARRAY['regulation', 'pharma', 'C21', 'clinical', 'FDA'], 'POLICY_REGULATION_CHANGE', 'b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4');

-- 환경 이벤트: 신재생에너지 정책 (D35 영향)
INSERT INTO rkyc_external_event (event_id, source_type, title, summary, url, url_hash, publisher, published_at, tags, event_type, event_signature) VALUES
('eeeeeeee-0005-0001-0001-000000000001', 'POLICY', 'REC 가격 안정화 정책 발표...태양광 발전사 수익성 개선 기대',
'산업통상자원부가 신재생에너지 공급인증서(REC) 가격 안정화를 위한 정책을 발표. 태양광 발전사업자들의 수익성 개선이 기대됨.',
'https://www.motie.go.kr/motie/ms/nt/gosi/bbs/bbsView.do?bbs_seq_n=123456', 'a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5', '산업통상자원부', '2024-12-17 09:30:00+09',
ARRAY['REC', 'solar', 'D35', 'policy', 'renewable'], 'POLICY_REGULATION_CHANGE', 'b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5');

-- ============================================
-- 6. EXTERNAL EVENT TARGETS (기업-이벤트 매핑)
-- ============================================

INSERT INTO rkyc_external_event_target (event_id, corp_id, match_basis, score_hint) VALUES
('eeeeeeee-0001-0001-0001-000000000001', '8001-3719240', 'INDUSTRY_CODE', 100),
('eeeeeeee-0002-0001-0001-000000000001', '8000-7647330', 'INDUSTRY_CODE', 100),
('eeeeeeee-0003-0001-0001-000000000001', '4028-1234567', 'INDUSTRY_CODE', 100),
('eeeeeeee-0004-0001-0001-000000000001', '4301-3456789', 'INDUSTRY_CODE', 100),
('eeeeeeee-0005-0001-0001-000000000001', '6701-4567890', 'INDUSTRY_CODE', 100);

-- ============================================
-- 7. SIGNALS (DIRECT / INDUSTRY / ENVIRONMENT)
-- ============================================

-- =========== 엠케이전자 (5개 Signal) ===========

-- DIRECT: 여신 노출 유지
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000001-0001-0001-0001-000000000001', '8001-3719240', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1', 1, 'NEUTRAL', 'MED', 'HIGH',
'총 여신 노출 12억원 유지 중. 전분기 대비 변동 없음. 현재 신용등급 MED 유지.');

-- DIRECT: 내부 등급 유지
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000002-0001-0001-0001-000000000001', '8001-3719240', 'DIRECT', 'INTERNAL_RISK_GRADE_CHANGE',
'c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2', 1, 'NEUTRAL', 'LOW', 'HIGH',
'내부 리스크 등급 MED 유지. 최근 KYC 갱신 완료(2024-11-15). 특이사항 없음.');

-- DIRECT: 담보 현황
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000003-0001-0001-0001-000000000001', '8001-3719240', 'DIRECT', 'COLLATERAL_CHANGE',
'c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3', 1, 'NEUTRAL', 'LOW', 'HIGH',
'부동산 담보 1건 유지. 담보 가치 변동 없음. LTV 비율 정상 범위 내.');

-- INDUSTRY: 반도체 업황 영향
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000004-0001-0001-0001-000000000001', '8001-3719240', 'INDUSTRY', 'INDUSTRY_SHOCK',
'c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4', 1, 'RISK', 'MED', 'MED',
'글로벌 반도체 수요 둔화로 인한 매출 감소 가능성 있음. 주요 고객사 발주량 모니터링 필요.');

-- ENVIRONMENT: 미중 무역분쟁 영향
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000005-0001-0001-0001-000000000001', '8001-3719240', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5', 1, 'RISK', 'LOW', 'LOW',
'미중 무역분쟁 장기화 시 공급망 영향 가능성 있음. 현재 직접적 영향은 제한적으로 판단됨.');

-- =========== 동부건설 (6개 Signal) ===========

-- DIRECT: 연체 플래그 활성화 (위험!)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000006-0001-0001-0001-000000000001', '8000-7647330', 'DIRECT', 'OVERDUE_FLAG_ON',
'c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6c6', 1, 'RISK', 'HIGH', 'HIGH',
'연체 플래그 활성화됨. 총 여신 58억원 중 일부 연체 발생. 즉시 모니터링 강화 권고.');

-- DIRECT: 내부 등급 HIGH
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000007-0001-0001-0001-000000000001', '8000-7647330', 'DIRECT', 'INTERNAL_RISK_GRADE_CHANGE',
'c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7', 1, 'RISK', 'HIGH', 'HIGH',
'내부 리스크 등급 HIGH로 상향 조정됨. 연체 발생 및 업황 악화에 따른 조치.');

-- DIRECT: 여신 노출 대규모
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000008-0001-0001-0001-000000000001', '8000-7647330', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8', 1, 'RISK', 'HIGH', 'HIGH',
'총 여신 노출 58억원. 건설업 평균 대비 높은 수준. 여신 집중도 관리 필요.');

-- DIRECT: 담보 현황
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000009-0001-0001-0001-000000000001', '8000-7647330', 'DIRECT', 'COLLATERAL_CHANGE',
'c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9', 1, 'NEUTRAL', 'MED', 'HIGH',
'담보 3건(부동산 2, 예금 1) 확보 중. 담보 커버리지 검토 필요.');

-- INDUSTRY: 건설 PF 위기
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000010-0001-0001-0001-000000000001', '8000-7647330', 'INDUSTRY', 'INDUSTRY_SHOCK',
'd0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0', 1, 'RISK', 'HIGH', 'HIGH',
'건설업 PF 부실 우려 확대. 유동성 위기 가능성 높음. 긴밀한 모니터링 필요.');

-- ENVIRONMENT: 금리 정책 영향
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000011-0001-0001-0001-000000000001', '8000-7647330', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'd1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1', 1, 'RISK', 'MED', 'MED',
'고금리 기조 지속 시 이자 부담 가중 예상. 금융비용 증가로 수익성 악화 가능성 있음.');

-- =========== 전북식품 (5개 Signal) ===========

-- DIRECT: 여신 현황 양호
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000012-0001-0001-0001-000000000001', '4028-1234567', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'd2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2', 1, 'NEUTRAL', 'LOW', 'HIGH',
'총 여신 8억원 유지. 안정적인 상환 이력. 신용 리스크 낮음.');

-- DIRECT: 내부 등급 LOW (양호)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000013-0001-0001-0001-000000000001', '4028-1234567', 'DIRECT', 'INTERNAL_RISK_GRADE_CHANGE',
'd3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3', 1, 'OPPORTUNITY', 'LOW', 'HIGH',
'내부 리스크 등급 LOW 유지. 우량 고객으로 분류. 추가 여신 검토 가능.');

-- DIRECT: KYC 갱신 완료
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000014-0001-0001-0001-000000000001', '4028-1234567', 'DIRECT', 'KYC_REFRESH',
'd4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4', 1, 'NEUTRAL', 'LOW', 'HIGH',
'KYC 정보 최근 갱신 완료(2024-09-10). 특이사항 없음.');

-- INDUSTRY: 식품 관세 영향
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000015-0001-0001-0001-000000000001', '4028-1234567', 'INDUSTRY', 'INDUSTRY_SHOCK',
'd5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5', 1, 'RISK', 'HIGH', 'MED',
'미국 식품 관세 인상 시 수출 매출 영향 가능성 있음. 수출 비중 확인 필요.');

-- ENVIRONMENT: 농산물 가격 변동
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000016-0001-0001-0001-000000000001', '4028-1234567', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'd6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6d6', 1, 'RISK', 'MED', 'LOW',
'농산물 원자재 가격 상승 추세. 원가 부담 증가 가능성 있으나 영향은 제한적으로 판단됨.');

-- =========== 광주정밀기계 (4개 Signal) ===========

-- DIRECT: 여신 현황
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000017-0001-0001-0001-000000000001', '6201-2345678', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'd7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7d7', 1, 'NEUTRAL', 'LOW', 'HIGH',
'총 여신 5억원 유지. 정상 상환 중. 특이사항 없음.');

-- DIRECT: 담보 변동
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000018-0001-0001-0001-000000000001', '6201-2345678', 'DIRECT', 'COLLATERAL_CHANGE',
'd8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8', 1, 'NEUTRAL', 'LOW', 'HIGH',
'기계설비 담보 2건 유지. 감가상각에 따른 담보가치 재평가 검토 필요.');

-- INDUSTRY: 자동차 부품 수요 변화
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000019-0001-0001-0001-000000000001', '6201-2345678', 'INDUSTRY', 'INDUSTRY_SHOCK',
'd9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9d9', 1, 'RISK', 'MED', 'MED',
'전기차 전환 가속화로 내연기관 부품 수요 감소 추세. 사업 포트폴리오 다각화 필요성 있음.');

-- ENVIRONMENT: 탄소중립 정책
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000020-0001-0001-0001-000000000001', '6201-2345678', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0', 1, 'NEUTRAL', 'LOW', 'LOW',
'탄소중립 정책 강화 추세. 중장기적으로 설비 투자 필요성 있으나 당장의 영향은 제한적.');

-- =========== 익산바이오텍 (5개 Signal) ===========

-- DIRECT: 여신 현황
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000021-0001-0001-0001-000000000001', '4301-3456789', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1', 1, 'NEUTRAL', 'MED', 'HIGH',
'총 여신 25억원. R&D 투자 확대에 따른 운영자금 수요 증가. 상환 능력 양호.');

-- DIRECT: 내부 등급 MED
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000022-0001-0001-0001-000000000001', '4301-3456789', 'DIRECT', 'INTERNAL_RISK_GRADE_CHANGE',
'e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2', 1, 'NEUTRAL', 'MED', 'HIGH',
'내부 리스크 등급 MED 유지. 바이오 업종 특성상 R&D 리스크 존재.');

-- DIRECT: 담보 현황 (특허 포함)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000023-0001-0001-0001-000000000001', '4301-3456789', 'DIRECT', 'COLLATERAL_CHANGE',
'e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3', 1, 'OPPORTUNITY', 'MED', 'MED',
'특허 담보 2건, 부동산 2건 확보. 특허 가치 상승에 따른 담보력 강화 가능성 있음.');

-- INDUSTRY: 바이오 업종 변동성
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000024-0001-0001-0001-000000000001', '4301-3456789', 'INDUSTRY', 'INDUSTRY_SHOCK',
'e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4', 1, 'RISK', 'MED', 'MED',
'바이오 업종 전반의 투자심리 위축. 단기 자금조달 환경 악화 가능성 있음.');

-- ENVIRONMENT: 식약처 규제 강화
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000025-0001-0001-0001-000000000001', '4301-3456789', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5', 1, 'RISK', 'HIGH', 'HIGH',
'식약처 임상시험 규제 강화 발표. 신약 개발 일정 지연 및 비용 증가 가능성 높음.');

-- =========== 나주태양에너지 (4개 Signal) ===========

-- DIRECT: 여신 현황
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000026-0001-0001-0001-000000000001', '6701-4567890', 'DIRECT', 'LOAN_EXPOSURE_CHANGE',
'e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6', 1, 'NEUTRAL', 'MED', 'HIGH',
'총 여신 15억원. 설비 투자 자금. 발전 수익으로 안정적 상환 중.');

-- DIRECT: 내부 등급 LOW (양호)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000027-0001-0001-0001-000000000001', '6701-4567890', 'DIRECT', 'INTERNAL_RISK_GRADE_CHANGE',
'e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7', 1, 'OPPORTUNITY', 'LOW', 'HIGH',
'내부 리스크 등급 LOW. 정부 정책 수혜 업종으로 안정적 수익 기대.');

-- INDUSTRY: 태양광 시장 경쟁
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000028-0001-0001-0001-000000000001', '6701-4567890', 'INDUSTRY', 'INDUSTRY_SHOCK',
'e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8', 1, 'NEUTRAL', 'LOW', 'MED',
'태양광 시장 경쟁 심화. 그러나 기존 발전소 운영 기반으로 영향은 제한적.');

-- ENVIRONMENT: REC 정책 변화 (호재)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, event_signature, snapshot_version, impact_direction, impact_strength, confidence, summary) VALUES
('00000029-0001-0001-0001-000000000001', '6701-4567890', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE',
'e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9', 1, 'OPPORTUNITY', 'MED', 'HIGH',
'REC 가격 안정화 정책 발표. 수익성 개선 기대. 긍정적 영향 전망.');

-- ============================================
-- 8. EVIDENCE (시그널별 근거)
-- ============================================

-- 엠케이전자 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000001-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 1,200,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000002-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/internal_risk_grade', '내부 리스크 등급: MED', '{"source": "internal_snapshot", "version": 1}'),
('00000003-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/collateral/collateral_summary/collateral_count', '담보 건수: 1', '{"source": "internal_snapshot", "version": 1}'),
('00000004-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1', '글로벌 반도체 수요 둔화가 2025년 상반기까지 지속될 것으로 전망', '{"published_at": "2024-12-20", "publisher": "전자신문"}'),
('00000005-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1', '미중 무역분쟁 관련 뉴스', '{"published_at": "2024-12-15"}');

-- 동부건설 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000006-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/overdue_flag', '연체 플래그: true', '{"source": "internal_snapshot", "version": 1, "severity": "HIGH"}'),
('00000007-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/internal_risk_grade', '내부 리스크 등급: HIGH', '{"source": "internal_snapshot", "version": 1}'),
('00000008-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 5,800,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000009-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/collateral/collateral_types', '담보 유형: 부동산, 예금', '{"source": "internal_snapshot", "version": 1}'),
('00000010-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2a2', '건설업 PF 대출 부실 우려 확대...중견사 유동성 위기', '{"published_at": "2024-12-18", "publisher": "한국경제"}'),
('00000011-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2', '고금리 기조 지속 전망', '{"published_at": "2024-12-10"}');

-- 전북식품 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000012-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 800,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000013-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/internal_risk_grade', '내부 리스크 등급: LOW', '{"source": "internal_snapshot", "version": 1}'),
('00000014-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/last_kyc_updated', 'KYC 갱신일: 2024-09-10', '{"source": "internal_snapshot", "version": 1}'),
('00000015-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3', '미국, 한국산 식품에 25% 관세 부과 예고', '{"published_at": "2024-12-19", "publisher": "연합뉴스"}'),
('00000016-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3', '농산물 원자재 가격 동향', '{"published_at": "2024-12-01"}');

-- 광주정밀기계 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000017-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 500,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000018-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/collateral/collateral_types', '담보 유형: 기계설비', '{"source": "internal_snapshot", "version": 1}'),
('00000019-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4', '전기차 전환 가속화 뉴스', '{"published_at": "2024-12-15"}'),
('00000020-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5', '탄소중립 정책 관련', '{"published_at": "2024-12-10"}');

-- 익산바이오텍 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000021-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 2,500,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000022-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/internal_risk_grade', '내부 리스크 등급: MED', '{"source": "internal_snapshot", "version": 1}'),
('00000023-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/collateral/collateral_types', '담보 유형: 특허, 부동산', '{"source": "internal_snapshot", "version": 1}'),
('00000024-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6f6', '바이오 업종 투자심리 위축', '{"published_at": "2024-12-18"}'),
('00000025-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4', '식약처, 바이오의약품 임상시험 규제 대폭 강화', '{"published_at": "2024-12-15", "publisher": "식품의약품안전처"}');

-- 나주태양에너지 Evidence
INSERT INTO rkyc_evidence (signal_id, evidence_type, ref_type, ref_value, snippet, meta) VALUES
('00000026-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/credit/loan_summary/total_exposure_krw', '총 여신 노출: 1,500,000,000원', '{"source": "internal_snapshot", "version": 1}'),
('00000027-0001-0001-0001-000000000001', 'INTERNAL_FIELD', 'SNAPSHOT_KEYPATH', '/corp/kyc_status/internal_risk_grade', '내부 리스크 등급: LOW', '{"source": "internal_snapshot", "version": 1}'),
('00000028-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7', '태양광 시장 경쟁 현황', '{"published_at": "2024-12-12"}'),
('00000029-0001-0001-0001-000000000001', 'EXTERNAL', 'URL', 'a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5', 'REC 가격 안정화 정책 발표...태양광 발전사 수익성 개선 기대', '{"published_at": "2024-12-17", "publisher": "산업통상자원부"}');

-- ============================================
-- 9. SIGNAL INDEX (Dashboard 전용)
-- ============================================

INSERT INTO rkyc_signal_index (
    corp_id, corp_name, industry_code, signal_type, event_type,
    impact_direction, impact_strength, confidence, title, summary_short,
    evidence_count, detected_at, signal_id
)
SELECT
    s.corp_id,
    c.corp_name,
    c.industry_code,
    s.signal_type,
    s.event_type,
    s.impact_direction,
    s.impact_strength,
    s.confidence,
    LEFT(s.summary, 100) AS title,
    LEFT(s.summary, 200) AS summary_short,
    (SELECT COUNT(*) FROM rkyc_evidence e WHERE e.signal_id = s.signal_id),
    s.created_at,
    s.signal_id
FROM rkyc_signal s
JOIN corp c ON s.corp_id = c.corp_id;

-- ============================================
-- 10. DASHBOARD SUMMARY (초기 데이터)
-- ============================================

INSERT INTO rkyc_dashboard_summary (counts_json, top_signals) VALUES
('{
  "total_signals": 29,
  "by_type": {
    "DIRECT": 17,
    "INDUSTRY": 7,
    "ENVIRONMENT": 5
  },
  "by_direction": {
    "RISK": 14,
    "OPPORTUNITY": 4,
    "NEUTRAL": 11
  },
  "by_strength": {
    "HIGH": 7,
    "MED": 12,
    "LOW": 10
  }
}',
'[
  {"corp_name": "동부건설", "event_type": "OVERDUE_FLAG_ON", "impact": "RISK/HIGH"},
  {"corp_name": "동부건설", "event_type": "INDUSTRY_SHOCK", "impact": "RISK/HIGH"},
  {"corp_name": "익산바이오텍", "event_type": "POLICY_REGULATION_CHANGE", "impact": "RISK/HIGH"}
]');

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- 1. 기업 수 확인 (기대값: 6)
-- SELECT COUNT(*) AS corp_count FROM corp;

-- 2. Signal 타입별 분포 (기대값: DIRECT=17, INDUSTRY=7, ENVIRONMENT=5)
-- SELECT signal_type, COUNT(*) AS count FROM rkyc_signal GROUP BY signal_type;

-- 3. Evidence 연결 확인 (기대값: 결과 없음 = 모든 Signal에 Evidence 있음)
-- SELECT s.signal_id, COUNT(e.evidence_id) AS evidence_count
-- FROM rkyc_signal s
-- LEFT JOIN rkyc_evidence e ON s.signal_id = e.signal_id
-- GROUP BY s.signal_id
-- HAVING COUNT(e.evidence_id) = 0;

-- 4. Snapshot Latest 확인 (기대값: 6)
-- SELECT COUNT(*) FROM rkyc_internal_snapshot_latest;

-- 5. External Event Target 확인 (기대값: 5)
-- SELECT COUNT(*) FROM rkyc_external_event_target;

-- 6. event_type별 분포
-- SELECT event_type, COUNT(*) AS count FROM rkyc_signal GROUP BY event_type ORDER BY count DESC;
