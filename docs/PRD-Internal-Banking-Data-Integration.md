# PRD: Internal Banking Data Integration

## 문서 정보
| 항목 | 내용 |
|------|------|
| 버전 | v1.0 |
| 작성일 | 2026-02-09 |
| 작성자 | PM / Tech Lead |
| 상태 | Draft |

---

## 1. Executive Summary

### 1.1 목적
은행이 보유한 **기업 거래 내부 데이터**를 Corp Detail 페이지에 시각화하고, LLM Signal Extraction 시 컨텍스트로 활용하여 **리스크/영업 기회 인사이트 정확도**를 향상시킨다.

### 1.2 배경
현재 `rkyc_internal_snapshot`은 기본적인 KYC 정보만 포함. 실제 은행 업무에서 중요한 **여신/수신/카드/담보/무역금융** 데이터가 누락되어 LLM이 피상적인 시그널만 생성.

### 1.3 기대 효과
| 항목 | Before | After |
|------|--------|-------|
| Signal 정확도 | 외부 뉴스 기반 | 내부 데이터 + 외부 뉴스 |
| 영업 기회 탐지 | 없음 | 판관비, 유산스, 담보 기반 |
| 리스크 조기 경보 | 뉴스 후행 | 수신 감소, 연체 선행 지표 |

---

## 2. Data Architecture

### 2.1 데이터 구조 개요

```
rkyc_internal_snapshot (기존)
└── snapshot_json
    ├── corp (기본 정보)
    ├── credit (여신 요약) ← 확장
    ├── collateral (담보 요약) ← 확장
    └── derived_hints

rkyc_banking_data (신규) ← 상세 시계열 데이터
├── loan_exposure (여신 상세)
├── deposit_trend (수신 추이)
├── card_usage (법인카드)
├── collateral_detail (담보 상세)
├── trade_finance (무역금융)
└── financial_statements (재무제표 3년)
```

### 2.2 신규 테이블: `rkyc_banking_data`

```sql
CREATE TABLE rkyc_banking_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),

    -- 메타데이터
    data_date DATE NOT NULL,  -- 기준일
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- JSON 데이터 블록
    loan_exposure JSONB,           -- 여신 현황
    deposit_trend JSONB,           -- 수신 추이
    card_usage JSONB,              -- 법인카드
    collateral_detail JSONB,       -- 담보 상세
    trade_finance JSONB,           -- 무역금융
    financial_statements JSONB,    -- 재무제표 (DART)

    -- 인덱스용
    UNIQUE(corp_id, data_date)
);

CREATE INDEX idx_banking_data_corp ON rkyc_banking_data(corp_id);
CREATE INDEX idx_banking_data_date ON rkyc_banking_data(data_date DESC);
```

---

## 3. JSON Schema 상세

### 3.1 loan_exposure (여신 현황)

```json
{
  "as_of_date": "2026-01-31",
  "total_exposure_krw": 12000000000,
  "yearly_trend": [
    {"year": 2024, "secured": 5000, "unsecured": 2000, "fx": 1000, "total": 8000},
    {"year": 2025, "secured": 6000, "unsecured": 2500, "fx": 1500, "total": 10000},
    {"year": 2026, "secured": 7000, "unsecured": 3000, "fx": 2000, "total": 12000}
  ],
  "composition": {
    "secured_loan": {"amount": 7000000000, "ratio": 58.3},
    "unsecured_loan": {"amount": 3000000000, "ratio": 25.0},
    "fx_loan": {"amount": 2000000000, "ratio": 16.7}
  },
  "risk_indicators": {
    "overdue_flag": false,
    "overdue_days": 0,
    "watch_list": false
  }
}
```

### 3.2 deposit_trend (수신 추이)

```json
{
  "monthly_balance": [
    {"month": "2025-07", "balance": 2500000000},
    {"month": "2025-08", "balance": 2800000000},
    {"month": "2025-09", "balance": 2600000000},
    {"month": "2025-10", "balance": 3100000000},
    {"month": "2025-11", "balance": 2900000000},
    {"month": "2025-12", "balance": 3200000000},
    {"month": "2026-01", "balance": 3500000000}
  ],
  "current_balance": 3500000000,
  "avg_balance_6m": 2943000000,
  "trend": "INCREASING"
}
```

### 3.3 card_usage (법인카드)

```json
{
  "monthly_usage": [
    {"month": "2025-07", "amount": 45000000, "tx_count": 234},
    {"month": "2025-08", "amount": 52000000, "tx_count": 267},
    {"month": "2025-09", "amount": 48000000, "tx_count": 245},
    {"month": "2025-10", "amount": 61000000, "tx_count": 312},
    {"month": "2025-11", "amount": 58000000, "tx_count": 298},
    {"month": "2025-12", "amount": 72000000, "tx_count": 356},
    {"month": "2026-01", "amount": 55000000, "tx_count": 278}
  ],
  "category_breakdown": {
    "travel": 35.2,
    "entertainment": 22.1,
    "office_supplies": 18.5,
    "fuel": 12.3,
    "others": 11.9
  },
  "card_limit": 100000000,
  "utilization_rate": 55.0,
  "opportunity_signals": [
    "출장비 비중 35% - 항공마일리지 카드 제안 가능",
    "한도 소진률 55% - 한도 증액 제안 가능"
  ]
}
```

### 3.4 collateral_detail (담보 상세)

```json
{
  "collaterals": [
    {
      "id": "COL-001",
      "type": "REAL_ESTATE",
      "description": "울산 남구 무거동 공장부지",
      "location": {
        "address": "울산광역시 남구 무거동 123-45",
        "coordinates": {"lat": 35.5384, "lng": 129.2569}
      },
      "appraisal": {
        "value": 8500000000,
        "date": "2024-06-15",
        "appraiser": "한국감정원"
      },
      "loan_amount": 5100000000,
      "ltv_ratio": 60.0,
      "nearby_development": {
        "project_name": "문수로 우회도로",
        "distance_km": 1.2,
        "impact": "HIGH",
        "description": "2.71km 왕복 4차로, 9,490세대 배후",
        "expected_completion": "2028-12"
      }
    },
    {
      "id": "COL-002",
      "type": "REAL_ESTATE",
      "description": "강원 동해시 물류창고",
      "location": {
        "address": "강원도 동해시 송정동 456-78",
        "coordinates": {"lat": 37.5244, "lng": 129.1142}
      },
      "appraisal": {
        "value": 3200000000,
        "date": "2024-09-20",
        "appraiser": "한국감정원"
      },
      "loan_amount": 1920000000,
      "ltv_ratio": 60.0,
      "nearby_development": {
        "project_name": "동해역~동해항 연결도로",
        "distance_km": 0.8,
        "impact": "MEDIUM",
        "description": "437m 도로, KTX 연계 물류 활성화",
        "expected_completion": "2025-11"
      }
    }
  ],
  "total_collateral_value": 11700000000,
  "total_loan_against": 7020000000,
  "avg_ltv": 60.0,
  "reappraisal_opportunities": [
    "COL-001: 문수로 우회도로 착공 시 재감정 권고 (예상 +15%)"
  ]
}
```

### 3.5 trade_finance (무역금융)

```json
{
  "export": {
    "monthly_receivables": [
      {"month": "2025-07", "amount_usd": 1200000},
      {"month": "2025-08", "amount_usd": 1350000},
      {"month": "2025-09", "amount_usd": 1180000},
      {"month": "2025-10", "amount_usd": 1420000},
      {"month": "2025-11", "amount_usd": 1380000},
      {"month": "2025-12", "amount_usd": 1550000},
      {"month": "2026-01", "amount_usd": 1480000}
    ],
    "current_receivables_usd": 1480000,
    "major_countries": ["US", "JP", "DE", "CN"]
  },
  "import": {
    "monthly_payables": [
      {"month": "2025-07", "amount_usd": 800000},
      {"month": "2025-08", "amount_usd": 920000},
      {"month": "2025-09", "amount_usd": 850000},
      {"month": "2025-10", "amount_usd": 980000},
      {"month": "2025-11", "amount_usd": 910000},
      {"month": "2025-12", "amount_usd": 1050000},
      {"month": "2026-01", "amount_usd": 990000}
    ],
    "current_payables_usd": 990000,
    "major_countries": ["CN", "TW", "JP"]
  },
  "usance": {
    "limit_usd": 2000000,
    "utilized_usd": 850000,
    "utilization_rate": 42.5,
    "avg_tenor_days": 90
  },
  "fx_exposure": {
    "net_position_usd": 490000,
    "hedge_ratio": 35.0,
    "opportunity_signal": "헷지 비율 35% - 환헤지 상품 제안 가능"
  }
}
```

### 3.6 financial_statements (재무제표 - DART 연동)

```json
{
  "source": "DART",
  "last_updated": "2026-01-15",
  "years": {
    "2023": {
      "assets": 45000000000,
      "liabilities": 28000000000,
      "equity": 17000000000,
      "revenue": 62000000000,
      "operating_income": 4800000000,
      "net_income": 3200000000,
      "debt_ratio": 164.7
    },
    "2024": {
      "assets": 52000000000,
      "liabilities": 31000000000,
      "equity": 21000000000,
      "revenue": 71000000000,
      "operating_income": 5600000000,
      "net_income": 4100000000,
      "debt_ratio": 147.6
    },
    "2025": {
      "assets": 58000000000,
      "liabilities": 33000000000,
      "equity": 25000000000,
      "revenue": 78000000000,
      "operating_income": 6200000000,
      "net_income": 4800000000,
      "debt_ratio": 132.0
    }
  },
  "yoy_growth": {
    "revenue": 9.9,
    "operating_income": 10.7,
    "net_income": 17.1
  }
}
```

---

## 4. LLM Context Integration

### 4.1 기존 Internal Snapshot 확장

현재 `snapshot_json`에 banking_data 참조 추가:

```json
{
  "schema_version": "v2.0",
  "corp": { ... },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 12000000000,
      "overdue_flag": false,
      "risk_grade_internal": "MED"
    },
    "banking_data_ref": "2026-01-31"
  },
  "collateral": {
    "has_collateral": true,
    "collateral_summary": {
      "total_value": 11700000000,
      "total_loan_against": 7020000000
    },
    "banking_data_ref": "2026-01-31"
  },
  "derived_hints": {
    "opportunity_signals": [
      "담보 COL-001 인근 인프라 개발 - 재감정 권고",
      "유산스 이용률 42% - 한도 확대 제안",
      "법인카드 출장비 35% - 마일리지 카드 크로스셀"
    ],
    "risk_signals": [
      "외화 헷지 비율 35% - 환위험 노출"
    ]
  }
}
```

### 4.2 LLM Prompt에 Banking Data 주입

**signal_extraction.py 수정:**

```python
def _build_llm_context(self, corp_id: str, snapshot: dict, banking_data: dict) -> str:
    """LLM에 전달할 통합 컨텍스트 생성"""

    context = f"""
# 기업 내부 데이터 (은행 보유, 100% Fact)

## 1. 여신 현황
- 총 여신잔액: {banking_data['loan_exposure']['total_exposure_krw']:,}원
- 구성: 담보대출 {banking_data['loan_exposure']['composition']['secured_loan']['ratio']}%,
       신용대출 {banking_data['loan_exposure']['composition']['unsecured_loan']['ratio']}%,
       외화대출 {banking_data['loan_exposure']['composition']['fx_loan']['ratio']}%
- 연체여부: {'있음 ⚠️' if banking_data['loan_exposure']['risk_indicators']['overdue_flag'] else '없음'}

## 2. 수신 현황
- 현재 잔액: {banking_data['deposit_trend']['current_balance']:,}원
- 6개월 평균: {banking_data['deposit_trend']['avg_balance_6m']:,}원
- 추세: {banking_data['deposit_trend']['trend']}

## 3. 법인카드
- 월평균 이용액: {sum(m['amount'] for m in banking_data['card_usage']['monthly_usage'][-6:]) / 6:,.0f}원
- 출장비 비중: {banking_data['card_usage']['category_breakdown']['travel']}%
- 한도 소진률: {banking_data['card_usage']['utilization_rate']}%

## 4. 담보물
{self._format_collaterals(banking_data['collateral_detail']['collaterals'])}

## 5. 무역금융
- 수출대금: ${banking_data['trade_finance']['export']['current_receivables_usd']:,}
- 수입대금: ${banking_data['trade_finance']['import']['current_payables_usd']:,}
- 유산스 이용률: {banking_data['trade_finance']['usance']['utilization_rate']}%
- 환헤지 비율: {banking_data['trade_finance']['fx_exposure']['hedge_ratio']}%

## 6. 재무제표 (DART 공시)
{self._format_financials(banking_data['financial_statements'])}

---
위 내부 데이터를 기반으로 리스크/기회 시그널을 분석하세요.
특히 담보 인근 인프라 개발, 유산스/카드 한도, 환헤지 관련 영업 기회를 탐지하세요.
"""
    return context
```

### 4.3 영업 기회 시그널 자동 생성 규칙

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| 담보 인근 인프라 impact=HIGH | DIRECT | 담보 재감정 → 추가 대출 |
| 카드 한도 소진률 > 70% | DIRECT | 카드 한도 증액 |
| 출장비 비중 > 30% | DIRECT | 마일리지 카드 발급 |
| 유산스 이용률 < 50% | DIRECT | 유산스 한도 확대 |
| 환헤지 비율 < 50% | DIRECT | 환헷지 상품 제안 |
| 수신 추세 DECREASING | DIRECT | 금리 우대 예금 제안 |

---

## 5. Frontend UI 설계

### 5.1 Corp Detail 페이지 섹션 추가

```
CorporateDetailPage
├── 기존 섹션들...
├── 📊 은행 거래 현황 (신규)
│   ├── 여신 현황 카드
│   │   ├── KPI: 총 여신잔액
│   │   ├── Donut Chart: 담보/신용/외화 구성
│   │   └── Line Chart: 연도별 추이
│   ├── 수신 현황 카드
│   │   ├── KPI: 현재 잔액
│   │   └── Area Chart: 월별 추이
│   ├── 법인카드 카드
│   │   ├── KPI: 월평균 이용액
│   │   ├── Bar Chart: 카테고리별
│   │   └── Line Chart: 월별 추이
│   ├── 담보물 현황 카드
│   │   ├── 담보 리스트 테이블
│   │   ├── LTV 게이지
│   │   └── 🏗️ 인프라 개발 배지
│   └── 무역금융 카드
│       ├── Line Chart: 수출입 추이
│       ├── Gauge: 유산스 이용률
│       └── Gauge: 환헤지 비율
└── 📈 재무제표 (신규)
    ├── 3개년 비교 테이블
    └── Bar Chart: 매출/영업이익/순이익
```

### 5.2 Recharts 컴포넌트

```typescript
// src/components/banking/LoanExposureChart.tsx
// src/components/banking/DepositTrendChart.tsx
// src/components/banking/CardUsageChart.tsx
// src/components/banking/CollateralTable.tsx
// src/components/banking/TradeFinanceChart.tsx
// src/components/banking/FinancialStatementsTable.tsx
```

---

## 6. API 설계

### 6.1 신규 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/corporations/{corp_id}/banking-data` | 최신 Banking Data 조회 |
| GET | `/corporations/{corp_id}/banking-data/history` | 이력 조회 |
| POST | `/corporations/{corp_id}/banking-data` | Banking Data 등록/갱신 |
| GET | `/corporations/{corp_id}/financial-statements` | DART 재무제표 조회 |

### 6.2 Response Schema

```typescript
interface BankingDataResponse {
  corp_id: string;
  data_date: string;
  loan_exposure: LoanExposure;
  deposit_trend: DepositTrend;
  card_usage: CardUsage;
  collateral_detail: CollateralDetail;
  trade_finance: TradeFinance;
  financial_statements: FinancialStatements;
  opportunity_signals: string[];  // 자동 생성된 영업 기회
}
```

---

## 7. 구현 계획

### 7.1 Phase 1: 스키마 & Mock 데이터 (Day 1)
- [ ] `migration_v15_banking_data.sql` 작성
- [ ] 6개 시드 기업 Mock 데이터 JSON 생성
- [ ] Supabase 마이그레이션 적용

### 7.2 Phase 2: Backend API (Day 2)
- [ ] `models/banking_data.py` 작성
- [ ] `schemas/banking_data.py` 작성
- [ ] `endpoints/banking_data.py` 작성
- [ ] DART 재무제표 연동 (기존 dart_api.py 확장)

### 7.3 Phase 3: LLM Integration (Day 3)
- [ ] `signal_extraction.py` - banking data context 주입
- [ ] `prompts.py` - 영업 기회 탐지 프롬프트 추가
- [ ] 테스트 및 검증

### 7.4 Phase 4: Frontend UI (Day 4-5)
- [ ] Recharts 차트 컴포넌트 6개
- [ ] CorporateDetailPage 섹션 추가
- [ ] 반응형 레이아웃

---

## 8. 6개 시드 기업 Mock 데이터 매핑

| 기업 | corp_id | 특화 시나리오 |
|------|---------|--------------|
| 엠케이전자 | 8001-3719240 | 반도체 수출 호조, 유산스 활용 |
| 동부건설 | 8000-7647330 | 담보(울산) 인프라 개발 수혜 |
| 전북식품 | 4028-1234567 | 수신 증가 추세, 카드 한도 여유 |
| 광주정밀기계 | 6201-2345678 | 담보(동해) 물류 활성화 |
| 삼성전자 | 4301-3456789 | 대규모 여신, 환헤지 이슈 |
| 휴림로봇 | 6701-4567890 | 스타트업형, 신용대출 비중 高 |

---

## 9. 성공 지표

| 지표 | 목표 |
|------|------|
| 영업 기회 시그널 생성률 | 기업당 평균 3개 이상 |
| LLM 시그널 정확도 | 내부 데이터 기반 90% 이상 |
| UI 로딩 속도 | Banking Data 섹션 < 500ms |
| 사용자 만족도 | Demo 시연 시 긍정 피드백 |

---

## 10. 부록: 인프라 개발 정보 (담보 연계)

### 10.1 울산 남구 '문수로 우회도로'
- **위치**: 울산광역시 남구, 문수로 일대
- **규모**: 총연장 2.71km, 왕복 4차로
- **계획**: 제5차 대도시권 혼잡도로 개선계획(2026~2030) 포함
- **부동산 포인트**: 인근 9,490세대 규모 공동주택 개발, 트램 1호선 연계
- **담보 영향**: HIGH - 재감정 시 +15% 예상

### 10.2 강원 동해시 '동해역~동해항 연결도로'
- **위치**: 강원도 동해시 송정동
- **규모**: 연장 437m
- **계획**: 2025년 11월 말 개통 예정
- **부동산 포인트**: KTX 동해역-동해항 직접 연결, 물류·산업시설 활성화
- **담보 영향**: MEDIUM - 재감정 시 +8% 예상

### 10.3 제주 서귀포시 '도시우회도로'
- **위치**: 제주특별자치도 서귀포시 도심 일대
- **규모**: 미정 (공론화 진행 중)
- **계획**: 2026년 2월 시민 공론화 절차 본격화
- **부동산 포인트**: 도심 통과 교통 분산, 불확실성 존재
- **담보 영향**: LOW - 공론화 결과에 따라 변동
