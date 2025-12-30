-- rKYC Seed Data
-- 6개 기업 (2 실제 + 4 가상) + 시그널 데이터
-- PRD 추가 지침서 기반

-- ============================================
-- CORPORATIONS (6개)
-- ============================================

-- 1. 엠케이전자 (실제 사업자번호)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    '8001371924',  -- 800-13-71924
    '엠케이전자',
    'MK Electronics',
    'active',
    '전자부품 제조업',
    'C26',
    450,
    '1998-03-15',
    '김명규',
    '경기도 화성시 동탄산단로 123',
    '반도체 및 전자부품 전문 제조기업. 주요 제품: LED 드라이버 IC, 전력관리 IC'
);

-- 2. 동부건설 (실제 사업자번호)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e',
    '8000764733',  -- 800-07-64733
    '동부건설',
    'Dongbu Construction',
    'watch',
    '종합건설업',
    'F41',
    1200,
    '1969-07-01',
    '박동호',
    '서울특별시 강남구 테헤란로 432',
    '주거/상업/공공시설 건설 전문. 최근 부동산 시장 침체로 관심 대상 지정'
);

-- 3. 전북식품 (가상)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f',
    '4101234567',  -- 가상 번호
    '전북식품',
    'Jeonbuk Foods',
    'active',
    '식품 제조업',
    'C10',
    280,
    '2005-09-20',
    '이정민',
    '전라북도 전주시 덕진구 산업로 567',
    '전통 발효식품 및 건강기능식품 제조. 주요 제품: 고추장, 된장, 프로바이오틱스'
);

-- 4. 광주정밀기계 (가상)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'd4e5f6a7-b8c9-7d8e-1f2a-3b4c5d6e7f8a',
    '6201234567',  -- 가상 번호
    '광주정밀기계',
    'Gwangju Precision Machinery',
    'active',
    '산업용 기계 제조업',
    'C29',
    150,
    '2010-04-10',
    '최광수',
    '광주광역시 광산구 첨단산단로 890',
    'CNC 공작기계 및 정밀금형 제조. 자동차 및 항공 부품 가공 전문'
);

-- 5. 익산바이오텍 (가상)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'e5f6a7b8-c9d0-8e9f-2a3b-4c5d6e7f8a9b',
    '4301234567',  -- 가상 번호
    '익산바이오텍',
    'Iksan Biotech',
    'active',
    '의약품 제조업',
    'C21',
    320,
    '2012-11-05',
    '박바이오',
    '전라북도 익산시 왕궁면 바이오산단로 234',
    '바이오의약품 및 진단키트 제조. mRNA 백신 기술 보유'
);

-- 6. 나주태양에너지 (가상)
INSERT INTO corporations (
    id, biz_no, corp_name, corp_name_en, status, industry, industry_code,
    employee_count, established_date, ceo_name, address, description
) VALUES (
    'f6a7b8c9-d0e1-9f0a-3b4c-5d6e7f8a9b0c',
    '6701234567',  -- 가상 번호
    '나주태양에너지',
    'Naju Solar Energy',
    'active',
    '태양광 발전업',
    'D35',
    85,
    '2015-06-15',
    '송태양',
    '전라남도 나주시 빛가람동 에너지로 456',
    '태양광 발전소 운영 및 ESS 솔루션 제공. 신재생에너지 전문'
);

-- ============================================
-- SIGNALS (Pre-seeded for Demo)
-- ============================================

-- 엠케이전자 시그널 (3개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    'financial',
    3,
    '매출채권 회전율 악화 추세',
    '최근 3분기 연속 매출채권 회전율이 하락하는 추세가 관찰됨. 2024년 1분기 6.2회에서 3분기 4.8회로 감소. 주요 거래처의 결제 지연 가능성이 있는 것으로 추정됨.',
    '[{"url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20241115000123", "source": "DART", "title": "분기보고서 (2024.09)", "date": "2024-11-15"}]',
    'new',
    'llm'
),
(
    '11111111-1111-1111-1111-111111111112',
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    'operational',
    2,
    '핵심 인력 이직 보도',
    '업계 매체에 따르면 R&D 부문 핵심 인력 3명이 경쟁사로 이직한 것으로 보도됨. 해당 인력은 차세대 전력관리 IC 개발 프로젝트를 담당했던 것으로 알려짐.',
    '[{"url": "https://www.etnews.com/20241120000456", "source": "전자신문", "title": "엠케이전자 R&D 핵심인력 이탈...기술유출 우려", "date": "2024-11-20"}]',
    'new',
    'llm'
),
(
    '11111111-1111-1111-1111-111111111113',
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    'market',
    2,
    '주요 고객사 발주 감소 전망',
    '반도체 업황 둔화로 주요 고객사인 삼성전자와 SK하이닉스의 발주량이 감소할 것으로 전망됨. 업계 전문가들은 2025년 상반기까지 보수적 전망을 유지하고 있음.',
    '[{"url": "https://www.sedaily.com/NewsView/2D1ABCDEF", "source": "서울경제", "title": "반도체 업황 둔화 장기화...부품업체 실적 악화 우려", "date": "2024-11-18"}]',
    'reviewed',
    'llm'
);

-- 동부건설 시그널 (2개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '22222222-2222-2222-2222-222222222221',
    'b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e',
    'financial',
    4,
    '유동성 위기 가능성',
    '부동산 PF 대출 만기 도래에 따른 유동성 압박이 우려됨. 2025년 1분기 만기 도래 PF 대출 규모가 약 3,000억원으로 추정되며, 현재 현금성 자산으로는 전액 상환이 어려울 것으로 분석됨.',
    '[{"url": "https://www.hankyung.com/economy/article/2024112012345", "source": "한국경제", "title": "동부건설 등 중견 건설사 PF 대출 만기 도래...유동성 주의보", "date": "2024-11-20"}, {"url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20241115000456", "source": "DART", "title": "반기보고서 (2024.06)", "date": "2024-08-14"}]',
    'new',
    'llm'
),
(
    '22222222-2222-2222-2222-222222222222',
    'b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e',
    'legal',
    3,
    '하도급 대금 미지급 분쟁',
    '협력업체 3곳이 하도급 대금 미지급을 이유로 민사소송을 제기한 것으로 확인됨. 총 청구 금액은 약 45억원 규모이며, 건설산업기본법 위반 가능성도 검토 중인 것으로 보도됨.',
    '[{"url": "https://www.mk.co.kr/news/business/10873456", "source": "매일경제", "title": "동부건설 하도급 대금 분쟁...협력사 집단 소송", "date": "2024-11-15"}]',
    'new',
    'llm'
);

-- 전북식품 시그널 (4개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '33333333-3333-3333-3333-333333333331',
    'c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f',
    'reputational',
    4,
    '식품 위생 관련 행정처분',
    '전라북도 식품안전과로부터 제조시설 위생 기준 미달로 영업정지 15일 처분을 받은 것으로 확인됨. 발효 숙성실의 온도 관리 미흡이 주요 사유로 지적됨.',
    '[{"url": "https://www.jb.go.kr/food/board/123456", "source": "전라북도청", "title": "식품제조업소 행정처분 현황 (2024.11)", "date": "2024-11-10"}]',
    'confirmed',
    'llm'
),
(
    '33333333-3333-3333-3333-333333333332',
    'c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f',
    'operational',
    2,
    '원자재 가격 상승 압박',
    '고추, 대두 등 주요 원자재 가격이 전년 대비 15-20% 상승함에 따라 원가 부담이 증가하고 있는 것으로 분석됨. 판매가 인상이 어려운 상황에서 수익성 악화가 우려됨.',
    '[{"url": "https://www.krei.re.kr/krei/researchReportView.do?key=123", "source": "한국농촌경제연구원", "title": "2024년 4분기 농산물 가격 동향", "date": "2024-11-01"}]',
    'new',
    'llm'
),
(
    '33333333-3333-3333-3333-333333333333',
    'c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f',
    'market',
    2,
    '대형마트 입점 계약 종료',
    '주요 판매처인 이마트와의 입점 계약이 2024년 말 종료 예정이며, 재계약 여부가 불확실한 것으로 파악됨. 해당 매출 비중이 전체의 약 25%를 차지하는 것으로 추정됨.',
    '[{"url": "internal_report", "source": "내부 검토", "title": "주요 거래처 계약 현황", "date": "2024-11-05"}]',
    'reviewed',
    'manual'
),
(
    '33333333-3333-3333-3333-333333333334',
    'c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f',
    'financial',
    1,
    '정부 보조금 지원 확정',
    '농림축산식품부의 전통식품 산업 육성 지원사업에 선정되어 3년간 총 15억원의 보조금을 지원받게 됨. 시설 현대화 및 R&D 투자에 활용 예정.',
    '[{"url": "https://www.mafra.go.kr/bbs/mafra/68/328456/artclView.do", "source": "농림축산식품부", "title": "2025년 전통식품 산업 육성사업 선정 결과", "date": "2024-11-22"}]',
    'confirmed',
    'llm'
);

-- 광주정밀기계 시그널 (2개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '44444444-4444-4444-4444-444444444441',
    'd4e5f6a7-b8c9-7d8e-1f2a-3b4c5d6e7f8a',
    'operational',
    3,
    '주요 설비 노후화 문제',
    '핵심 생산설비인 5축 CNC 가공기 2대의 노후화로 인해 불량률이 증가하고 있는 것으로 파악됨. 설비 교체 비용은 약 20억원으로 추정되나, 현재 투자 여력이 부족한 상황.',
    '[{"url": "internal_audit", "source": "내부 감사", "title": "생산설비 현황 점검 보고서", "date": "2024-10-30"}]',
    'new',
    'manual'
),
(
    '44444444-4444-4444-4444-444444444442',
    'd4e5f6a7-b8c9-7d8e-1f2a-3b4c5d6e7f8a',
    'market',
    2,
    '자동차 부품 수요 감소',
    '전기차 전환 가속화에 따라 내연기관 차량용 정밀 부품 수요가 감소하는 추세. 주요 고객인 현대모비스로부터의 발주량이 전년 대비 10% 감소한 것으로 확인됨.',
    '[{"url": "https://www.motorgraph.com/news/article/20241118123456", "source": "모터그래프", "title": "내연기관 부품업체 구조조정 본격화", "date": "2024-11-18"}]',
    'new',
    'llm'
);

-- 익산바이오텍 시그널 (3개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '55555555-5555-5555-5555-555555555551',
    'e5f6a7b8-c9d0-8e9f-2a3b-4c5d6e7f8a9b',
    'legal',
    4,
    '임상시험 데이터 조작 의혹',
    '식품의약품안전처 조사 결과, 신약 임상 3상 시험 데이터 일부에서 이상 징후가 발견되어 추가 조사가 진행 중인 것으로 보도됨. 회사 측은 단순 행정 착오라고 해명.',
    '[{"url": "https://www.bosa.co.kr/news/article/20241119000789", "source": "의학신문", "title": "익산바이오텍 임상시험 데이터 식약처 조사 착수", "date": "2024-11-19"}]',
    'new',
    'llm'
),
(
    '55555555-5555-5555-5555-555555555552',
    'e5f6a7b8-c9d0-8e9f-2a3b-4c5d6e7f8a9b',
    'financial',
    3,
    'R&D 비용 급증에 따른 영업손실',
    '신약 개발을 위한 R&D 투자 확대로 2024년 3분기 영업손실이 전년 동기 대비 150% 증가. 현금 소진율(burn rate)이 높아 추가 자금 조달이 필요할 것으로 전망됨.',
    '[{"url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20241114000789", "source": "DART", "title": "분기보고서 (2024.09)", "date": "2024-11-14"}]',
    'reviewed',
    'llm'
),
(
    '55555555-5555-5555-5555-555555555553',
    'e5f6a7b8-c9d0-8e9f-2a3b-4c5d6e7f8a9b',
    'reputational',
    2,
    'mRNA 기술 특허 분쟁',
    '모더나로부터 mRNA 플랫폼 기술 관련 특허 침해 경고장을 받은 것으로 확인됨. 현재 법률 검토 중이며, 라이선스 협상 또는 기술 우회 개발을 검토 중인 것으로 파악됨.',
    '[{"url": "https://www.biospectator.com/view/article/20241115000234", "source": "바이오스펙테이터", "title": "익산바이오텍, 모더나 특허 분쟁 휘말려", "date": "2024-11-15"}]',
    'new',
    'llm'
);

-- 나주태양에너지 시그널 (1개)
INSERT INTO signals (
    id, corporation_id, category, severity, title, description, evidence, status, source
) VALUES
(
    '66666666-6666-6666-6666-666666666661',
    'f6a7b8c9-d0e1-9f0a-3b4c-5d6e7f8a9b0c',
    'market',
    2,
    'REC 가격 하락 영향',
    '신재생에너지 공급인증서(REC) 가격이 2024년 들어 30% 이상 하락하면서 매출 감소가 불가피한 상황. 다만 ESS 사업 확대로 일부 상쇄가 가능할 것으로 전망됨.',
    '[{"url": "https://www.electimes.com/article/20241120000567", "source": "전기신문", "title": "REC 가격 폭락...태양광 발전사업자 수익성 악화", "date": "2024-11-20"}]',
    'new',
    'llm'
);

-- ============================================
-- FINANCIAL SNAPSHOTS (샘플)
-- ============================================

-- 엠케이전자 재무 데이터
INSERT INTO financial_snapshots (
    corporation_id, fiscal_year, fiscal_quarter, revenue, operating_profit, net_income,
    total_assets, total_liabilities, total_equity, debt_ratio, current_ratio, roe, source
) VALUES
(
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    2024, 3,
    85000000000,   -- 850억
    6800000000,    -- 68억
    5100000000,    -- 51억
    120000000000,  -- 1200억
    48000000000,   -- 480억
    72000000000,   -- 720억
    0.6667,        -- 부채비율 66.67%
    1.85,          -- 유동비율
    0.0708,        -- ROE 7.08%
    'dart'
),
(
    'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d',
    2024, 2,
    92000000000,
    8280000000,
    6210000000,
    118000000000,
    45000000000,
    73000000000,
    0.6164,
    1.92,
    0.0851,
    'dart'
);

-- 동부건설 재무 데이터
INSERT INTO financial_snapshots (
    corporation_id, fiscal_year, fiscal_quarter, revenue, operating_profit, net_income,
    total_assets, total_liabilities, total_equity, debt_ratio, current_ratio, roe, source
) VALUES
(
    'b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e',
    2024, 2,
    580000000000,  -- 5800억
    -12000000000,  -- -120억 (영업손실)
    -18000000000,  -- -180억 (순손실)
    950000000000,  -- 9500억
    720000000000,  -- 7200억
    230000000000,  -- 2300억
    3.1304,        -- 부채비율 313%
    0.85,          -- 유동비율 (1 미만 - 위험)
    -0.0783,       -- ROE -7.83%
    'dart'
);

-- ============================================
-- DEMO USER (테스트용)
-- ============================================

-- 테스트 사용자 (실제 Supabase Auth 사용자 필요)
-- INSERT INTO users (id, email, name, role, is_active)
-- VALUES (
--     'demo-user-uuid-here',
--     'demo@rkyc.local',
--     '데모 사용자',
--     'analyst',
--     true
-- );

-- 테스트 사용자에게 모든 기업 할당
-- INSERT INTO user_corporation_assignments (user_id, corporation_id)
-- SELECT 'demo-user-uuid-here', id FROM corporations;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- 기업 수 확인
-- SELECT COUNT(*) AS corp_count FROM corporations;

-- 시그널 수 확인
-- SELECT corporation_id, COUNT(*) AS signal_count
-- FROM signals GROUP BY corporation_id;

-- 카테고리별 시그널 분포
-- SELECT category, severity, COUNT(*) AS count
-- FROM signals GROUP BY category, severity ORDER BY category, severity;
