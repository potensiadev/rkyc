# PRD: Internal Banking Data Integration

## 문서 정보
| 항목 | 내용 |
|------|------|
| 버전 | v1.1 |
| 작성일 | 2026-02-09 |
| 수정일 | 2026-02-09 |
| 작성자 | PM / Tech Lead |
| 상태 | Draft |
| 변경사항 | v1.1 - 리스크 시그널 섹션 추가 |

---

## 1. Executive Summary

### 1.1 목적
은행이 보유한 **기업 거래 내부 데이터**를 Corp Detail 페이지에 시각화하고, LLM Signal Extraction 시 컨텍스트로 활용하여 **리스크 조기 경보** 및 **영업 기회 인사이트 정확도**를 향상시킨다.

### 1.2 배경
현재 `rkyc_internal_snapshot`은 기본적인 KYC 정보만 포함. 실제 은행 업무에서 중요한 **여신/수신/카드/담보/무역금융** 데이터가 누락되어 LLM이 피상적인 시그널만 생성.

### 1.3 기대 효과
| 항목 | Before | After |
|------|--------|-------|
| **리스크 탐지** | 뉴스 후행 (이미 발생) | 내부 데이터 선행 지표 (사전 경고) |
| **영업 기회** | 없음 | 판관비, 유산스, 담보 기반 탐지 |
| **Signal 정확도** | 외부 뉴스 기반 | 내부 데이터 + 외부 뉴스 교차 검증 |

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
    "overdue_amount": 0,
    "watch_list": false,
    "watch_list_reason": null,
    "internal_grade": "A2",
    "grade_change": null,
    "next_review_date": "2026-06-30"
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
  "min_balance_6m": 2500000000,
  "max_balance_6m": 3500000000,
  "trend": "INCREASING",
  "volatility": "LOW",
  "large_withdrawal_alerts": []
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
  "avg_monthly_usage": 55857000,
  "usage_trend": "STABLE",
  "anomaly_flags": []
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
        "appraiser": "한국감정원",
        "next_appraisal_date": "2026-06-15",
        "market_trend": "STABLE"
      },
      "loan_amount": 5100000000,
      "ltv_ratio": 60.0,
      "nearby_development": {
        "project_name": "문수로 우회도로",
        "distance_km": 1.2,
        "impact": "HIGH",
        "description": "2.71km 왕복 4차로, 9,490세대 배후",
        "expected_completion": "2028-12",
        "status": "APPROVED"
      },
      "risk_factors": []
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
        "appraiser": "한국감정원",
        "next_appraisal_date": "2026-09-20",
        "market_trend": "INCREASING"
      },
      "loan_amount": 1920000000,
      "ltv_ratio": 60.0,
      "nearby_development": {
        "project_name": "동해역~동해항 연결도로",
        "distance_km": 0.8,
        "impact": "MEDIUM",
        "description": "437m 도로, KTX 연계 물류 활성화",
        "expected_completion": "2025-11",
        "status": "UNDER_CONSTRUCTION"
      },
      "risk_factors": []
    }
  ],
  "total_collateral_value": 11700000000,
  "total_loan_against": 7020000000,
  "avg_ltv": 60.0,
  "high_ltv_collaterals": [],
  "expiring_appraisals": []
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
    "avg_collection_days": 45,
    "overdue_receivables_usd": 0,
    "major_countries": ["US", "JP", "DE", "CN"],
    "country_concentration": {"US": 35, "JP": 28, "DE": 22, "CN": 15}
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
    "major_countries": ["CN", "TW", "JP"],
    "country_concentration": {"CN": 52, "TW": 30, "JP": 18}
  },
  "usance": {
    "limit_usd": 2000000,
    "utilized_usd": 850000,
    "utilization_rate": 42.5,
    "avg_tenor_days": 90,
    "upcoming_maturities": []
  },
  "fx_exposure": {
    "net_position_usd": 490000,
    "hedge_ratio": 35.0,
    "hedge_instruments": ["forward"],
    "var_1d_usd": 15000
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
      "current_assets": 18000000000,
      "current_liabilities": 12000000000,
      "debt_ratio": 164.7,
      "current_ratio": 150.0,
      "interest_coverage": 4.2
    },
    "2024": {
      "assets": 52000000000,
      "liabilities": 31000000000,
      "equity": 21000000000,
      "revenue": 71000000000,
      "operating_income": 5600000000,
      "net_income": 4100000000,
      "current_assets": 21000000000,
      "current_liabilities": 14000000000,
      "debt_ratio": 147.6,
      "current_ratio": 150.0,
      "interest_coverage": 4.8
    },
    "2025": {
      "assets": 58000000000,
      "liabilities": 33000000000,
      "equity": 25000000000,
      "revenue": 78000000000,
      "operating_income": 6200000000,
      "net_income": 4800000000,
      "current_assets": 24000000000,
      "current_liabilities": 15000000000,
      "debt_ratio": 132.0,
      "current_ratio": 160.0,
      "interest_coverage": 5.5
    }
  },
  "yoy_growth": {
    "revenue": 9.9,
    "operating_income": 10.7,
    "net_income": 17.1
  },
  "financial_health": "GOOD"
}
```

---

## 4. 리스크 시그널 탐지 규칙 (Risk Signals)

### 4.1 여신 리스크 (Loan Exposure Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| `overdue_flag = true` | 🔴 HIGH | DIRECT | **연체 발생**: {overdue_days}일 연체, 연체금액 {overdue_amount}원 |
| `overdue_days >= 30` | 🔴 HIGH | DIRECT | **장기연체 경보**: 30일 이상 연체, 신용등급 하락 위험 |
| `watch_list = true` | 🟠 MED | DIRECT | **Watch List 등재**: 사유 - {watch_list_reason} |
| `internal_grade 하락` | 🟠 MED | DIRECT | **내부등급 하향**: {prev_grade} → {current_grade} |
| `unsecured_ratio > 50%` | 🟡 LOW | DIRECT | **신용대출 비중 과다**: 담보 없이 50% 이상 노출 |
| `fx_loan_ratio > 30%` + 환율 변동성 | 🟠 MED | DIRECT | **외화대출 환위험**: 외화대출 비중 {ratio}%, 환율 변동성 증가 |
| `next_review_date` 임박 (30일 이내) | 🟡 LOW | DIRECT | **여신 심사 기한 도래**: {days}일 후 정기심사 예정 |

### 4.2 수신 리스크 (Deposit Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| `trend = DECREASING` + 3개월 연속 | 🟠 MED | DIRECT | **수신 이탈 징후**: 3개월 연속 잔액 감소, 자금 유출 가능성 |
| 현재 잔액 < 6개월 평균의 70% | 🟠 MED | DIRECT | **급격한 수신 감소**: 평균 대비 {ratio}% 수준으로 하락 |
| `large_withdrawal_alerts` 존재 | 🟡 LOW | DIRECT | **대규모 출금 감지**: {date}에 {amount}원 출금 |
| `volatility = HIGH` | 🟡 LOW | DIRECT | **수신 변동성 확대**: 자금 흐름 불안정 |

### 4.3 법인카드 리스크 (Card Usage Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| 월 사용액 > 평균의 200% | 🟠 MED | DIRECT | **비정상 카드 사용**: 평균 대비 {ratio}% 급증, 비용 통제 필요 |
| `entertainment > 30%` | 🟡 LOW | DIRECT | **접대비 과다**: 접대비 비중 {ratio}%, 비용 효율성 점검 권고 |
| `utilization_rate > 90%` | 🟡 LOW | DIRECT | **카드 한도 소진 임박**: 소진률 {ratio}% |
| `anomaly_flags` 존재 | 🟠 MED | DIRECT | **이상 거래 감지**: {anomaly_description} |

### 4.4 담보 리스크 (Collateral Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| `ltv_ratio > 80%` | 🔴 HIGH | DIRECT | **LTV 과다**: 담보 {id} LTV {ratio}%, 추가 담보 확보 필요 |
| `ltv_ratio > 70%` | 🟠 MED | DIRECT | **LTV 주의**: 담보 {id} LTV {ratio}%, 모니터링 강화 |
| `next_appraisal_date` 경과 | 🟠 MED | DIRECT | **재감정 기한 도과**: 담보 {id} 감정 만료, 재감정 필요 |
| `market_trend = DECREASING` | 🟠 MED | DIRECT | **담보가치 하락 우려**: {location} 부동산 시세 하락 추세 |
| 인프라 개발 `status = CANCELLED` | 🟠 MED | ENVIRONMENT | **인프라 사업 취소**: {project_name} 취소, 담보가치 영향 |
| 인프라 개발 `status = DELAYED` | 🟡 LOW | ENVIRONMENT | **인프라 사업 지연**: {project_name} 지연, 담보가치 상승 지연 |

### 4.5 무역금융 리스크 (Trade Finance Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| `overdue_receivables_usd > 0` | 🔴 HIGH | DIRECT | **수출대금 회수 지연**: ${amount} 미회수, 부실채권 위험 |
| `avg_collection_days > 90` | 🟠 MED | DIRECT | **수출대금 회수 장기화**: 평균 {days}일, 현금흐름 악화 |
| `usance_utilization > 90%` | 🟠 MED | DIRECT | **유산스 한도 소진 임박**: 이용률 {ratio}% |
| `hedge_ratio < 30%` + 환율 변동성 | 🔴 HIGH | ENVIRONMENT | **환헤지 부족**: 헷지 비율 {ratio}%, 환율 급변 시 손실 위험 |
| 특정 국가 집중도 > 50% | 🟠 MED | INDUSTRY | **국가 집중 리스크**: {country} 의존도 {ratio}%, 지정학적 리스크 |
| 중국 집중도 > 40% | 🟠 MED | ENVIRONMENT | **중국 리스크**: 중국 의존도 {ratio}%, 미중 갈등 영향 |
| `upcoming_maturities` 7일 이내 | 🟡 LOW | DIRECT | **유산스 만기 임박**: {days}일 후 ${amount} 만기 도래 |

### 4.6 재무제표 리스크 (Financial Statement Risk)

| 조건 | 심각도 | 시그널 타입 | 시그널 내용 |
|------|--------|------------|------------|
| `debt_ratio > 300%` | 🔴 HIGH | DIRECT | **과다 부채**: 부채비율 {ratio}%, 재무건전성 심각 |
| `debt_ratio > 200%` | 🟠 MED | DIRECT | **부채비율 주의**: 부채비율 {ratio}%, 재무구조 개선 필요 |
| 부채비율 YoY +50%p 이상 증가 | 🔴 HIGH | DIRECT | **부채 급증**: 부채비율 {prev}% → {current}% 급등 |
| `current_ratio < 100%` | 🔴 HIGH | DIRECT | **유동성 위기**: 유동비율 {ratio}%, 단기 지급능력 부족 |
| `current_ratio < 120%` | 🟠 MED | DIRECT | **유동성 주의**: 유동비율 {ratio}%, 운전자금 관리 필요 |
| `interest_coverage < 1.5` | 🔴 HIGH | DIRECT | **이자보상 부족**: 이자보상배율 {ratio}배, 이자 지급 능력 위험 |
| `net_income < 0` | 🔴 HIGH | DIRECT | **당기순손실**: {amount}원 적자, 수익성 악화 |
| 매출 YoY -20% 이상 감소 | 🔴 HIGH | DIRECT | **매출 급감**: 전년 대비 {ratio}% 감소, 사업 위축 |
| 매출 YoY -10% 이상 감소 | 🟠 MED | DIRECT | **매출 감소**: 전년 대비 {ratio}% 감소 |
| 영업이익 YoY -30% 이상 감소 | 🔴 HIGH | DIRECT | **수익성 악화**: 영업이익 전년 대비 {ratio}% 감소 |
| `financial_health = CRITICAL` | 🔴 HIGH | DIRECT | **재무 위험 경보**: 복합 재무지표 악화, 긴급 점검 필요 |

---

## 5. 영업 기회 시그널 탐지 규칙 (Opportunity Signals)

### 5.1 여신 기회 (Loan Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| `internal_grade 상향` | DIRECT | **등급 상향**: 금리 인하 또는 한도 증액 제안 |
| `unsecured_ratio < 30%` + 우량등급 | DIRECT | **신용대출 여력**: 담보 의존도 낮고 등급 우수, 신용한도 확대 제안 |
| 여신 잔액 증가 추세 + 정상 | DIRECT | **우량 성장 기업**: 추가 시설자금 또는 운전자금 제안 |

### 5.2 수신 기회 (Deposit Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| `trend = INCREASING` + 3개월 연속 | DIRECT | **수신 증가 기업**: VIP 예금 상품 또는 자산관리 서비스 제안 |
| 현재 잔액 > 6개월 평균의 150% | DIRECT | **유동성 풍부**: 단기 고금리 예금 또는 MMF 제안 |
| `volatility = LOW` + 고잔액 | DIRECT | **안정적 예치**: 장기 정기예금 또는 특판 상품 제안 |

### 5.3 법인카드 기회 (Card Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| `travel > 30%` | DIRECT | **출장 多 기업**: 항공마일리지 법인카드 크로스셀 |
| `utilization_rate > 70%` | DIRECT | **카드 한도 증액**: 이용 실적 우수, 한도 상향 제안 |
| `fuel > 20%` | DIRECT | **차량 多 기업**: 주유 할인 법인카드 또는 차량 리스 제안 |
| 월 사용액 증가 추세 | DIRECT | **성장 기업**: 추가 카드 발급 또는 한도 증액 제안 |

### 5.4 담보 기회 (Collateral Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| 인프라 개발 `impact = HIGH` + `status = APPROVED/UNDER_CONSTRUCTION` | DIRECT | **담보 재감정**: 인프라 개발 수혜, 재감정 시 LTV 여유 → 추가 대출 |
| `market_trend = INCREASING` | DIRECT | **담보가치 상승**: 재감정 권유, 추가 여신 가능 |
| `ltv_ratio < 50%` | DIRECT | **LTV 여유**: 추가 담보대출 또는 한도 증액 가능 |
| 다수 담보 보유 + 분산 지역 | DIRECT | **담보 포트폴리오 우수**: 종합 부동산 자문 서비스 제안 |

### 5.5 무역금융 기회 (Trade Finance Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| `usance_utilization < 50%` + 수입 증가 | DIRECT | **유산스 한도 확대**: 수입 증가세, 유산스 한도 상향 제안 |
| `hedge_ratio < 50%` | DIRECT | **환헤지 상품 제안**: 헤지 비율 낮음, 선물환/옵션 제안 |
| 수출대금 증가 추세 | DIRECT | **수출금융 확대**: 수출 호조, 수출채권 매입 한도 확대 제안 |
| 다양한 국가 분산 | DIRECT | **글로벌 뱅킹**: 해외 네트워크 활용 서비스 제안 |

### 5.6 재무제표 기회 (Financial Opportunity)

| 조건 | 시그널 타입 | 영업 기회 |
|------|------------|----------|
| 매출 YoY +20% 이상 성장 | DIRECT | **고성장 기업**: 시설투자 자금 또는 M&A 자문 제안 |
| `debt_ratio` 개선 + 순이익 증가 | DIRECT | **재무구조 개선**: 금리 인하 협상 또는 차환 제안 |
| `current_ratio > 200%` | DIRECT | **유동성 풍부**: 여유자금 운용 상품 제안 |
| `interest_coverage > 5` | DIRECT | **이자 부담 낮음**: 적정 레버리지 활용 제안 |
| `financial_health = EXCELLENT` | DIRECT | **프라임 고객**: VIP 패키지 및 우대 금리 제안 |

---

## 6. LLM Context Integration

### 6.1 기존 Internal Snapshot 확장

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
      "risk_grade_internal": "A2"
    },
    "banking_data_ref": "2026-01-31"
  },
  "collateral": {
    "has_collateral": true,
    "collateral_summary": {
      "total_value": 11700000000,
      "total_loan_against": 7020000000,
      "avg_ltv": 60.0
    },
    "banking_data_ref": "2026-01-31"
  },
  "derived_hints": {
    "risk_signals": [
      "외화 헷지 비율 35% - 환위험 노출",
      "중국 수입 의존도 52% - 지정학적 리스크"
    ],
    "opportunity_signals": [
      "담보 COL-001 인근 인프라 개발 - 재감정 권고",
      "유산스 이용률 42% - 한도 확대 제안",
      "법인카드 출장비 35% - 마일리지 카드 크로스셀"
    ]
  }
}
```

### 6.2 LLM Prompt에 Banking Data 주입

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
- 연체여부: {'⚠️ 있음 ({} 일)'.format(banking_data['loan_exposure']['risk_indicators']['overdue_days']) if banking_data['loan_exposure']['risk_indicators']['overdue_flag'] else '없음'}
- 내부등급: {banking_data['loan_exposure']['risk_indicators']['internal_grade']}
- Watch List: {'⚠️ 등재 - {}'.format(banking_data['loan_exposure']['risk_indicators']['watch_list_reason']) if banking_data['loan_exposure']['risk_indicators']['watch_list'] else '미등재'}

## 2. 수신 현황
- 현재 잔액: {banking_data['deposit_trend']['current_balance']:,}원
- 6개월 평균: {banking_data['deposit_trend']['avg_balance_6m']:,}원
- 추세: {banking_data['deposit_trend']['trend']} {'⚠️' if banking_data['deposit_trend']['trend'] == 'DECREASING' else ''}
- 변동성: {banking_data['deposit_trend']['volatility']}

## 3. 법인카드
- 월평균 이용액: {banking_data['card_usage']['avg_monthly_usage']:,}원
- 출장비 비중: {banking_data['card_usage']['category_breakdown']['travel']}%
- 접대비 비중: {banking_data['card_usage']['category_breakdown']['entertainment']}%
- 한도 소진률: {banking_data['card_usage']['utilization_rate']}%

## 4. 담보물 현황
{self._format_collaterals(banking_data['collateral_detail']['collaterals'])}
- 평균 LTV: {banking_data['collateral_detail']['avg_ltv']}% {'⚠️ 주의' if banking_data['collateral_detail']['avg_ltv'] > 70 else ''}

## 5. 무역금융
- 수출대금: ${banking_data['trade_finance']['export']['current_receivables_usd']:,}
- 수입대금: ${banking_data['trade_finance']['import']['current_payables_usd']:,}
- 연체 수출대금: ${banking_data['trade_finance']['export']['overdue_receivables_usd']:,} {'⚠️ 회수 지연' if banking_data['trade_finance']['export']['overdue_receivables_usd'] > 0 else ''}
- 유산스 이용률: {banking_data['trade_finance']['usance']['utilization_rate']}%
- 환헤지 비율: {banking_data['trade_finance']['fx_exposure']['hedge_ratio']}% {'⚠️ 환위험 노출' if banking_data['trade_finance']['fx_exposure']['hedge_ratio'] < 50 else ''}
- 중국 의존도 (수입): {banking_data['trade_finance']['import']['country_concentration'].get('CN', 0)}% {'⚠️ 지정학적 리스크' if banking_data['trade_finance']['import']['country_concentration'].get('CN', 0) > 40 else ''}

## 6. 재무제표 (DART 공시)
{self._format_financials(banking_data['financial_statements'])}

---
위 내부 데이터를 기반으로 리스크/기회 시그널을 분석하세요.

### 리스크 탐지 포인트:
- 연체, Watch List, 등급 하락
- 수신 감소 추세, 대규모 출금
- LTV 과다, 담보가치 하락
- 환헤지 부족, 국가 집중 리스크
- 부채비율 악화, 유동성 위기, 적자 전환

### 영업 기회 탐지 포인트:
- 담보 인근 인프라 개발 수혜
- 유산스/카드 한도 여유
- 수신 증가 기업 VIP 상품
- 고성장 기업 시설투자 자금
"""
    return context
```

---

## 7. Frontend UI 설계

### 7.1 Corp Detail 페이지 섹션 추가

```
CorporateDetailPage
├── 기존 섹션들...
├── 🚨 리스크 알림 배너 (신규) - 조건 해당 시 상단 표시
│   └── 연체, Watch List, 환위험 등 HIGH 리스크 경고
├── 📊 은행 거래 현황 (신규)
│   ├── 여신 현황 카드
│   │   ├── KPI: 총 여신잔액 + 연체 배지
│   │   ├── Donut Chart: 담보/신용/외화 구성
│   │   ├── Line Chart: 연도별 추이
│   │   └── 리스크 지표 (등급, Watch List)
│   ├── 수신 현황 카드
│   │   ├── KPI: 현재 잔액 + 추세 화살표
│   │   ├── Area Chart: 월별 추이
│   │   └── 이탈 징후 경고 (해당 시)
│   ├── 법인카드 카드
│   │   ├── KPI: 월평균 이용액
│   │   ├── Bar Chart: 카테고리별
│   │   ├── Line Chart: 월별 추이
│   │   └── 이상 거래 경고 (해당 시)
│   ├── 담보물 현황 카드
│   │   ├── 담보 리스트 테이블 + LTV 게이지
│   │   ├── 🏗️ 인프라 개발 배지
│   │   └── ⚠️ 고 LTV 경고 (해당 시)
│   └── 무역금융 카드
│       ├── Line Chart: 수출입 추이
│       ├── Gauge: 유산스 이용률
│       ├── Gauge: 환헤지 비율 + 경고
│       └── 국가 집중 리스크 배지
└── 📈 재무제표 (신규)
    ├── 3개년 비교 테이블
    ├── Bar Chart: 매출/영업이익/순이익
    ├── 재무건전성 지표 (부채비율, 유동비율)
    └── 재무 위험 경고 (해당 시)
```

### 7.2 리스크 시각화 컬러 코드

| 심각도 | 컬러 | 사용처 |
|--------|------|--------|
| 🔴 HIGH | `red-500` / `#ef4444` | 연체, 적자, 유동성 위기 |
| 🟠 MED | `amber-500` / `#f59e0b` | Watch List, 수신 감소, 환위험 |
| 🟡 LOW | `yellow-400` / `#facc15` | 한도 소진, 비용 과다 |
| 🟢 GOOD | `green-500` / `#22c55e` | 정상, 우량 |
| 🔵 OPPORTUNITY | `blue-500` / `#3b82f6` | 영업 기회 |

---

## 8. API 설계

### 8.1 신규 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/corporations/{corp_id}/banking-data` | 최신 Banking Data 조회 |
| GET | `/corporations/{corp_id}/banking-data/history` | 이력 조회 |
| POST | `/corporations/{corp_id}/banking-data` | Banking Data 등록/갱신 |
| GET | `/corporations/{corp_id}/financial-statements` | DART 재무제표 조회 |
| GET | `/corporations/{corp_id}/risk-alerts` | 리스크 알림 목록 조회 |
| GET | `/corporations/{corp_id}/opportunity-signals` | 영업 기회 목록 조회 |

### 8.2 Response Schema

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
  risk_alerts: RiskAlert[];        // 자동 생성된 리스크 경고
  opportunity_signals: string[];   // 자동 생성된 영업 기회
}

interface RiskAlert {
  id: string;
  severity: 'HIGH' | 'MED' | 'LOW';
  category: 'LOAN' | 'DEPOSIT' | 'CARD' | 'COLLATERAL' | 'TRADE' | 'FINANCIAL';
  signal_type: 'DIRECT' | 'INDUSTRY' | 'ENVIRONMENT';
  title: string;
  description: string;
  recommended_action: string;
  detected_at: string;
}
```

---

## 9. 구현 계획

### 9.1 Phase 1: 스키마 & Mock 데이터 (Day 1)
- [ ] `migration_v15_banking_data.sql` 작성
- [ ] 6개 시드 기업 Mock 데이터 JSON 생성 (리스크 시나리오 포함)
- [ ] Supabase 마이그레이션 적용

### 9.2 Phase 2: Backend API (Day 2)
- [ ] `models/banking_data.py` 작성
- [ ] `schemas/banking_data.py` 작성
- [ ] `endpoints/banking_data.py` 작성
- [ ] 리스크/기회 시그널 자동 생성 로직
- [ ] DART 재무제표 연동 (기존 dart_api.py 확장)

### 9.3 Phase 3: LLM Integration (Day 3)
- [ ] `signal_extraction.py` - banking data context 주입
- [ ] `prompts.py` - 리스크/영업 기회 탐지 프롬프트 추가
- [ ] 테스트 및 검증

### 9.4 Phase 4: Frontend UI (Day 4-5)
- [ ] Recharts 차트 컴포넌트 6개
- [ ] 리스크 알림 배너 컴포넌트
- [ ] CorporateDetailPage 섹션 추가
- [ ] 반응형 레이아웃

---

## 10. 6개 시드 기업 Mock 데이터 시나리오

| 기업 | corp_id | 리스크 시나리오 | 영업 기회 시나리오 |
|------|---------|----------------|------------------|
| 엠케이전자 | 8001-3719240 | 환헤지 부족 (35%) | 수출 호조, 유산스 확대 |
| 동부건설 | 8000-7647330 | 부채비율 상승 (180%) | 담보(울산) 인프라 수혜 |
| 전북식품 | 4028-1234567 | 정상 (리스크 낮음) | 수신 증가, VIP 상품 |
| 광주정밀기계 | 6201-2345678 | 중국 의존도 52% | 담보(동해) 물류 활성화 |
| 삼성전자 | 4301-3456789 | 정상 (우량) | 대규모 시설투자 자금 |
| 휴림로봇 | 6701-4567890 | 신용대출 비중 高 (65%) | 스타트업 성장, 카드 확대 |

---

## 11. 성공 지표

| 지표 | 목표 |
|------|------|
| 리스크 시그널 탐지율 | 100% (모든 조건 해당 시 자동 생성) |
| 영업 기회 시그널 생성률 | 기업당 평균 3개 이상 |
| LLM 시그널 정확도 | 내부 데이터 기반 90% 이상 |
| 리스크 알림 응답 시간 | < 100ms |
| UI 로딩 속도 | Banking Data 섹션 < 500ms |
| 사용자 만족도 | Demo 시연 시 긍정 피드백 |

---

## 12. 부록: 인프라 개발 정보 (담보 연계)

### 12.1 울산 남구 '문수로 우회도로'
- **위치**: 울산광역시 남구, 문수로 일대
- **규모**: 총연장 2.71km, 왕복 4차로
- **계획**: 제5차 대도시권 혼잡도로 개선계획(2026~2030) 포함
- **부동산 포인트**: 인근 9,490세대 규모 공동주택 개발, 트램 1호선 연계
- **담보 영향**: HIGH - 재감정 시 +15% 예상

### 12.2 강원 동해시 '동해역~동해항 연결도로'
- **위치**: 강원도 동해시 송정동
- **규모**: 연장 437m
- **계획**: 2025년 11월 말 개통 예정
- **부동산 포인트**: KTX 동해역-동해항 직접 연결, 물류·산업시설 활성화
- **담보 영향**: MEDIUM - 재감정 시 +8% 예상

### 12.3 제주 서귀포시 '도시우회도로'
- **위치**: 제주특별자치도 서귀포시 도심 일대
- **규모**: 미정 (공론화 진행 중)
- **계획**: 2026년 2월 시민 공론화 절차 본격화
- **부동산 포인트**: 도심 통과 교통 분산, 불확실성 존재
- **담보 영향**: LOW - 공론화 결과에 따라 변동
