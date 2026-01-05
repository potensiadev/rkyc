// 중앙화된 시그널 데이터
// Supabase rkyc_signal 테이블 기준 (seed_v2.sql)
// 모든 화면에서 동일한 시그널 정보를 사용합니다.

import { Signal, SignalCategory, SignalStatus, SignalImpact, Evidence } from "@/types/signal";

// 은행 거래 이벤트 (통합 타임라인용)
export interface BankTransaction {
  id: string;
  corporationId: string;
  corporationName: string;
  date: string;
  type: "loan" | "deposit" | "fx" | "pension" | "payroll" | "card";
  title: string;
  amount?: string;
}

export const BANK_TRANSACTIONS: BankTransaction[] = [
  {
    id: "bt1",
    corporationId: "4028-1234567",
    corporationName: "전북식품",
    date: "2024-12-15",
    type: "loan",
    title: "운영자금 대출 추가 실행",
    amount: "2억원",
  },
  {
    id: "bt2",
    corporationId: "4028-1234567",
    corporationName: "전북식품",
    date: "2024-11-20",
    type: "fx",
    title: "수출 대금 결제 (미국 수입사)",
    amount: "USD 850,000",
  },
  {
    id: "bt3",
    corporationId: "6201-2345678",
    corporationName: "광주정밀기계",
    date: "2024-12-10",
    type: "loan",
    title: "시설자금 대출 실행",
    amount: "3억원",
  },
  {
    id: "bt4",
    corporationId: "4301-3456789",
    corporationName: "삼성전자",
    date: "2024-12-01",
    type: "pension",
    title: "퇴직연금 가입 (DC형)",
  },
  {
    id: "bt5",
    corporationId: "8001-3719240",
    corporationName: "엠케이전자",
    date: "2024-11-28",
    type: "fx",
    title: "수입 신용장 개설",
    amount: "USD 500,000",
  },
  {
    id: "bt6",
    corporationId: "8000-7647330",
    corporationName: "동부건설",
    date: "2024-12-18",
    type: "loan",
    title: "PF 대출 신규 실행",
    amount: "20억원",
  },
];

// Supabase rkyc_signal 기준 시그널 데이터 (29개)
export const SIGNALS: Signal[] = [
  // =========== 엠케이전자 (5개 Signal) ===========
  {
    id: "00000001-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 노출 12억원 유지 중",
    summary: "총 여신 노출 12억원 유지 중. 전분기 대비 변동 없음. 현재 신용등급 MED 유지.",
    source: "내부 시스템",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "여신",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e1",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 1,200,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000002-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "내부 리스크 등급 MED 유지",
    summary: "내부 리스크 등급 MED 유지. 최근 KYC 갱신 완료(2024-11-15). 특이사항 없음.",
    source: "내부 시스템",
    detectedAt: "2024-12-19T10:00:00",
    detailCategory: "등급",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "risk_grade",
    evidences: [
      {
        id: "e2",
        sourceType: "internal",
        title: "리스크 등급 정보",
        snippet: "내부 리스크 등급: MED",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "00000003-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "부동산 담보 1건 유지",
    summary: "부동산 담보 1건 유지. 담보 가치 변동 없음. LTV 비율 정상 범위 내.",
    source: "내부 시스템",
    detectedAt: "2024-12-18T11:00:00",
    detailCategory: "담보",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "collateral",
    evidences: [
      {
        id: "e3",
        sourceType: "internal",
        title: "담보 정보",
        snippet: "담보 건수: 1",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-18",
      },
    ],
  },
  {
    id: "00000004-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "글로벌 반도체 수요 둔화로 인한 매출 감소 가능성",
    summary: "글로벌 반도체 수요 둔화로 인한 매출 감소 가능성 있음. 주요 고객사 발주량 모니터링 필요.",
    source: "전자신문",
    sourceUrl: "https://www.etnews.com/20241220000123",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "엠케이전자는 전자부품 제조업체로 반도체 업황에 직접 영향을 받습니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e4",
        sourceType: "news",
        title: "글로벌 반도체 수요 둔화 지속",
        snippet: "글로벌 반도체 수요 둔화가 2025년 상반기까지 지속될 것으로 전망",
        sourceName: "전자신문",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000005-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "미중 무역분쟁 장기화 시 공급망 영향 가능성",
    summary: "미중 무역분쟁 장기화 시 공급망 영향 가능성 있음. 현재 직접적 영향은 제한적으로 판단됨.",
    source: "연합뉴스",
    detectedAt: "2024-12-15T14:00:00",
    detailCategory: "정책/규제",
    impact: "risk",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "low",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e5",
        sourceType: "news",
        title: "미중 무역분쟁 관련 뉴스",
        snippet: "미중 무역분쟁 관련 뉴스",
        sourceName: "연합뉴스",
        publishedAt: "2024-12-15",
      },
    ],
  },

  // =========== 동부건설 (6개 Signal) ===========
  {
    id: "00000006-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "연체 플래그 활성화됨 - 즉시 모니터링 강화 권고",
    summary: "연체 플래그 활성화됨. 총 여신 58억원 중 일부 연체 발생. 즉시 모니터링 강화 권고.",
    source: "내부 시스템",
    detectedAt: "2024-12-24T08:00:00",
    detailCategory: "연체",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "overdue",
    evidences: [
      {
        id: "e6",
        sourceType: "internal",
        title: "연체 플래그 정보",
        snippet: "연체 플래그: true",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "00000007-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "내부 리스크 등급 HIGH로 상향 조정됨",
    summary: "내부 리스크 등급 HIGH로 상향 조정됨. 연체 발생 및 업황 악화에 따른 조치.",
    source: "내부 시스템",
    detectedAt: "2024-12-23T10:00:00",
    detailCategory: "등급",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "risk_grade",
    evidences: [
      {
        id: "e7",
        sourceType: "internal",
        title: "리스크 등급 정보",
        snippet: "내부 리스크 등급: HIGH",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "00000008-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 노출 58억원 - 건설업 평균 대비 높은 수준",
    summary: "총 여신 노출 58억원. 건설업 평균 대비 높은 수준. 여신 집중도 관리 필요.",
    source: "내부 시스템",
    detectedAt: "2024-12-22T09:00:00",
    detailCategory: "여신",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e8",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 5,800,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-22",
      },
    ],
  },
  {
    id: "00000009-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "review",
    title: "담보 3건 확보 중 - 담보 커버리지 검토 필요",
    summary: "담보 3건(부동산 2, 예금 1) 확보 중. 담보 커버리지 검토 필요.",
    source: "내부 시스템",
    detectedAt: "2024-12-21T11:00:00",
    detailCategory: "담보",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "collateral",
    evidences: [
      {
        id: "e9",
        sourceType: "internal",
        title: "담보 정보",
        snippet: "담보 유형: 부동산, 예금",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-21",
      },
    ],
  },
  {
    id: "00000010-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "건설업 PF 부실 우려 확대 - 유동성 위기 가능성",
    summary: "건설업 PF 부실 우려 확대. 유동성 위기 가능성 높음. 긴밀한 모니터링 필요.",
    source: "한국경제",
    sourceUrl: "https://www.hankyung.com/economy/article/2024122012345",
    detectedAt: "2024-12-18T10:30:00",
    detailCategory: "산업 동향",
    relevanceNote: "동부건설은 종합건설업체로 PF 부실 위험에 직접 노출됩니다.",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e10",
        sourceType: "news",
        title: "건설업 PF 대출 부실 우려 확대",
        snippet: "건설업 PF 대출 부실 우려 확대...중견사 유동성 위기",
        sourceName: "한국경제",
        publishedAt: "2024-12-18",
      },
    ],
  },
  {
    id: "00000011-0001-0001-0001-000000000001",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "review",
    title: "고금리 기조 지속 시 이자 부담 가중 예상",
    summary: "고금리 기조 지속 시 이자 부담 가중 예상. 금융비용 증가로 수익성 악화 가능성 있음.",
    source: "금융위원회",
    detectedAt: "2024-12-10T14:00:00",
    detailCategory: "정책/규제",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e11",
        sourceType: "news",
        title: "고금리 기조 지속 전망",
        snippet: "고금리 기조 지속 전망",
        sourceName: "금융위원회",
        publishedAt: "2024-12-10",
      },
    ],
  },

  // =========== 전북식품 (5개 Signal) ===========
  {
    id: "00000012-0001-0001-0001-000000000001",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 8억원 유지 - 안정적인 상환 이력",
    summary: "총 여신 8억원 유지. 안정적인 상환 이력. 신용 리스크 낮음.",
    source: "내부 시스템",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "여신",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e12",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 800,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000013-0001-0001-0001-000000000001",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "내부 리스크 등급 LOW 유지 - 우량 고객",
    summary: "내부 리스크 등급 LOW 유지. 우량 고객으로 분류. 추가 여신 검토 가능.",
    source: "내부 시스템",
    detectedAt: "2024-12-19T10:00:00",
    detailCategory: "등급",
    impact: "opportunity",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "risk_grade",
    evidences: [
      {
        id: "e13",
        sourceType: "internal",
        title: "리스크 등급 정보",
        snippet: "내부 리스크 등급: LOW",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "00000014-0001-0001-0001-000000000001",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "KYC 정보 최근 갱신 완료",
    summary: "KYC 정보 최근 갱신 완료(2024-09-10). 특이사항 없음.",
    source: "내부 시스템",
    detectedAt: "2024-09-10T09:00:00",
    detailCategory: "KYC",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "kyc_refresh",
    evidences: [
      {
        id: "e14",
        sourceType: "internal",
        title: "KYC 갱신 정보",
        snippet: "KYC 갱신일: 2024-09-10",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-09-10",
      },
    ],
  },
  {
    id: "00000015-0001-0001-0001-000000000001",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "미국 식품 관세 인상 시 수출 매출 영향 가능성",
    summary: "미국 식품 관세 인상 시 수출 매출 영향 가능성 있음. 수출 비중 확인 필요.",
    source: "연합뉴스",
    sourceUrl: "https://www.yonhapnews.co.kr/bulletin/2024/12/19/news123",
    detectedAt: "2024-12-19T14:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "전북식품은 식품 제조업체로 미국 수출 비중이 있습니다.",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e15",
        sourceType: "news",
        title: "미국, 한국산 식품에 25% 관세 부과 예고",
        snippet: "미국, 한국산 식품에 25% 관세 부과 예고",
        sourceName: "연합뉴스",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "00000016-0001-0001-0001-000000000001",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "review",
    title: "농산물 원자재 가격 상승 추세",
    summary: "농산물 원자재 가격 상승 추세. 원가 부담 증가 가능성 있으나 영향은 제한적으로 판단됨.",
    source: "농림축산식품부",
    detectedAt: "2024-12-01T10:00:00",
    detailCategory: "원자재",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "low",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e16",
        sourceType: "report",
        title: "농산물 원자재 가격 동향",
        snippet: "농산물 원자재 가격 동향",
        sourceName: "농림축산식품부",
        publishedAt: "2024-12-01",
      },
    ],
  },

  // =========== 광주정밀기계 (4개 Signal) ===========
  {
    id: "00000017-0001-0001-0001-000000000001",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 5억원 유지 - 정상 상환 중",
    summary: "총 여신 5억원 유지. 정상 상환 중. 특이사항 없음.",
    source: "내부 시스템",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "여신",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e17",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 500,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000018-0001-0001-0001-000000000001",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "기계설비 담보 2건 유지 - 감가상각 재평가 필요",
    summary: "기계설비 담보 2건 유지. 감가상각에 따른 담보가치 재평가 검토 필요.",
    source: "내부 시스템",
    detectedAt: "2024-12-18T11:00:00",
    detailCategory: "담보",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "collateral",
    evidences: [
      {
        id: "e18",
        sourceType: "internal",
        title: "담보 정보",
        snippet: "담보 유형: 기계설비",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-18",
      },
    ],
  },
  {
    id: "00000019-0001-0001-0001-000000000001",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "전기차 전환 가속화로 내연기관 부품 수요 감소 추세",
    summary: "전기차 전환 가속화로 내연기관 부품 수요 감소 추세. 사업 포트폴리오 다각화 필요성 있음.",
    source: "한국자동차산업협회",
    detectedAt: "2024-12-15T10:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "광주정밀기계는 자동차 부품용 정밀 금형 제조업체입니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e19",
        sourceType: "news",
        title: "전기차 전환 가속화 뉴스",
        snippet: "전기차 전환 가속화 뉴스",
        sourceName: "한국자동차산업협회",
        publishedAt: "2024-12-15",
      },
    ],
  },
  {
    id: "00000020-0001-0001-0001-000000000001",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "review",
    title: "탄소중립 정책 강화 추세 - 중장기 설비 투자 필요",
    summary: "탄소중립 정책 강화 추세. 중장기적으로 설비 투자 필요성 있으나 당장의 영향은 제한적.",
    source: "환경부",
    detectedAt: "2024-12-10T09:00:00",
    detailCategory: "정책/규제",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "low",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e20",
        sourceType: "regulation",
        title: "탄소중립 정책 관련",
        snippet: "탄소중립 정책 관련",
        sourceName: "환경부",
        publishedAt: "2024-12-10",
      },
    ],
  },

  // =========== 삼성전자 (5개 Signal) ===========
  {
    id: "00000021-0001-0001-0001-000000000001",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 25억원 - R&D 투자 확대에 따른 운영자금 수요",
    summary: "총 여신 25억원. R&D 투자 확대에 따른 운영자금 수요 증가. 상환 능력 양호.",
    source: "내부 시스템",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "여신",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e21",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 2,500,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000022-0001-0001-0001-000000000001",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "내부 리스크 등급 MED 유지 - 바이오 업종 R&D 리스크",
    summary: "내부 리스크 등급 MED 유지. 바이오 업종 특성상 R&D 리스크 존재.",
    source: "내부 시스템",
    detectedAt: "2024-12-19T10:00:00",
    detailCategory: "등급",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "risk_grade",
    evidences: [
      {
        id: "e22",
        sourceType: "internal",
        title: "리스크 등급 정보",
        snippet: "내부 리스크 등급: MED",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "00000023-0001-0001-0001-000000000001",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "특허 담보 2건, 부동산 2건 확보 - 담보력 강화 가능성",
    summary: "특허 담보 2건, 부동산 2건 확보. 특허 가치 상승에 따른 담보력 강화 가능성 있음.",
    source: "내부 시스템",
    detectedAt: "2024-12-18T11:00:00",
    detailCategory: "담보",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "internal",
    eventClassification: "collateral",
    evidences: [
      {
        id: "e23",
        sourceType: "internal",
        title: "담보 정보",
        snippet: "담보 유형: 특허, 부동산",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-18",
      },
    ],
  },
  {
    id: "00000024-0001-0001-0001-000000000001",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "바이오 업종 전반의 투자심리 위축",
    summary: "바이오 업종 전반의 투자심리 위축. 단기 자금조달 환경 악화 가능성 있음.",
    source: "바이오산업협회",
    detectedAt: "2024-12-18T10:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "삼성전자는 의약품 제조업체입니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e24",
        sourceType: "news",
        title: "바이오 업종 투자심리 위축",
        snippet: "바이오 업종 투자심리 위축",
        sourceName: "바이오산업협회",
        publishedAt: "2024-12-18",
      },
    ],
  },
  {
    id: "00000025-0001-0001-0001-000000000001",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "new",
    title: "식약처 임상시험 규제 강화 발표 - 개발 일정 지연 가능성",
    summary: "식약처 임상시험 규제 강화 발표. 신약 개발 일정 지연 및 비용 증가 가능성 높음.",
    source: "식품의약품안전처",
    sourceUrl: "https://www.mfds.go.kr/brd/m_99/view.do?seq=48123",
    detectedAt: "2024-12-15T11:00:00",
    detailCategory: "정책/규제",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e25",
        sourceType: "regulation",
        title: "식약처, 바이오의약품 임상시험 규제 대폭 강화",
        snippet: "식약처, 바이오의약품 임상시험 규제 대폭 강화",
        sourceName: "식품의약품안전처",
        publishedAt: "2024-12-15",
      },
    ],
  },

  // =========== 휴림로봇 (4개 Signal) ===========
  {
    id: "00000026-0001-0001-0001-000000000001",
    corporationName: "휴림로봇",
    corporationId: "6701-4567890",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "총 여신 15억원 - 발전 수익으로 안정적 상환 중",
    summary: "총 여신 15억원. 설비 투자 자금. 발전 수익으로 안정적 상환 중.",
    source: "내부 시스템",
    detectedAt: "2024-12-20T09:00:00",
    detailCategory: "여신",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "loan_exposure",
    evidences: [
      {
        id: "e26",
        sourceType: "internal",
        title: "내부 여신 데이터",
        snippet: "총 여신 노출: 1,500,000,000원",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "00000027-0001-0001-0001-000000000001",
    corporationName: "휴림로봇",
    corporationId: "6701-4567890",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "new",
    title: "내부 리스크 등급 LOW - 정부 정책 수혜 업종",
    summary: "내부 리스크 등급 LOW. 정부 정책 수혜 업종으로 안정적 수익 기대.",
    source: "내부 시스템",
    detectedAt: "2024-12-19T10:00:00",
    detailCategory: "등급",
    impact: "opportunity",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "internal",
    eventClassification: "risk_grade",
    evidences: [
      {
        id: "e27",
        sourceType: "internal",
        title: "리스크 등급 정보",
        snippet: "내부 리스크 등급: LOW",
        sourceName: "내부 Snapshot",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "00000028-0001-0001-0001-000000000001",
    corporationName: "휴림로봇",
    corporationId: "6701-4567890",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "태양광 시장 경쟁 심화 - 기존 발전소 운영으로 영향 제한적",
    summary: "태양광 시장 경쟁 심화. 그러나 기존 발전소 운영 기반으로 영향은 제한적.",
    source: "에너지경제연구원",
    detectedAt: "2024-12-12T10:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "휴림로봇은 태양광 발전 사업자입니다.",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 1,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "industry_shock",
    evidences: [
      {
        id: "e28",
        sourceType: "news",
        title: "태양광 시장 경쟁 현황",
        snippet: "태양광 시장 경쟁 현황",
        sourceName: "에너지경제연구원",
        publishedAt: "2024-12-12",
      },
    ],
  },
  {
    id: "00000029-0001-0001-0001-000000000001",
    corporationName: "휴림로봇",
    corporationId: "6701-4567890",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "new",
    title: "REC 가격 안정화 정책 발표 - 수익성 개선 기대",
    summary: "REC 가격 안정화 정책 발표. 수익성 개선 기대. 긍정적 영향 전망.",
    source: "산업통상자원부",
    sourceUrl: "https://www.motie.go.kr/motie/ms/nt/gosi/bbs/bbsView.do?bbs_seq_n=123456",
    detectedAt: "2024-12-17T09:30:00",
    detailCategory: "정책/규제",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 1,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e29",
        sourceType: "regulation",
        title: "REC 가격 안정화 정책 발표",
        snippet: "REC 가격 안정화 정책 발표...태양광 발전사 수익성 개선 기대",
        sourceName: "산업통상자원부",
        publishedAt: "2024-12-17",
      },
    ],
  },
];

// 시그널 조회 함수들
export const getSignalById = (id: string): Signal | undefined => {
  return SIGNALS.find(signal => signal.id === id);
};

export const getSignalsByCorporationId = (corporationId: string): Signal[] => {
  return SIGNALS.filter(signal => signal.corporationId === corporationId);
};

export const getSignalsByCorporationName = (name: string): Signal[] => {
  return SIGNALS.filter(signal => signal.corporationName === name);
};

export const getSignalsByCategory = (category: SignalCategory): Signal[] => {
  return SIGNALS.filter(signal => signal.signalCategory === category);
};

export const getSignalsByStatus = (status: SignalStatus): Signal[] => {
  return SIGNALS.filter(signal => signal.status === status);
};

export const getSignalsByImpact = (impact: SignalImpact): Signal[] => {
  return SIGNALS.filter(signal => signal.impact === impact);
};

// 통계 계산 함수들
export const getSignalCounts = () => {
  const today = new Date().toISOString().split('T')[0];
  return {
    total: SIGNALS.length,
    new: SIGNALS.filter(s => s.status === "new").length,
    review: SIGNALS.filter(s => s.status === "review").length,
    resolved: SIGNALS.filter(s => s.status === "resolved").length,
    todayNew: SIGNALS.filter(s => s.status === "new" && s.detectedAt.startsWith(today)).length,
    risk: SIGNALS.filter(s => s.impact === "risk").length,
    opportunity: SIGNALS.filter(s => s.impact === "opportunity").length,
    neutral: SIGNALS.filter(s => s.impact === "neutral").length,
    direct: SIGNALS.filter(s => s.signalCategory === "direct").length,
    industry: SIGNALS.filter(s => s.signalCategory === "industry").length,
    environment: SIGNALS.filter(s => s.signalCategory === "environment").length,
  };
};

export const getCorporationSignalCounts = (corporationId: string) => {
  const signals = getSignalsByCorporationId(corporationId);
  return {
    total: signals.length,
    direct: signals.filter(s => s.signalCategory === "direct").length,
    industry: signals.filter(s => s.signalCategory === "industry").length,
    environment: signals.filter(s => s.signalCategory === "environment").length,
    risk: signals.filter(s => s.impact === "risk").length,
    opportunity: signals.filter(s => s.impact === "opportunity").length,
    neutral: signals.filter(s => s.impact === "neutral").length,
  };
};

// 시그널 타임라인 (최신순 정렬)
export const getSignalTimeline = (corporationId?: string): Signal[] => {
  let signals = corporationId
    ? getSignalsByCorporationId(corporationId)
    : SIGNALS;

  return signals.sort((a, b) =>
    new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime()
  );
};

// 통합 타임라인 (시그널 + 은행 거래)
export interface IntegratedTimelineItem {
  id: string;
  date: string;
  type: "signal" | "bank";
  title: string;
  category?: string;
  impact?: SignalImpact;
  bankTransactionType?: BankTransaction["type"];
}

export const getIntegratedTimeline = (corporationId: string): IntegratedTimelineItem[] => {
  const signals = getSignalsByCorporationId(corporationId);
  const transactions = BANK_TRANSACTIONS.filter(t => t.corporationId === corporationId);

  const signalItems: IntegratedTimelineItem[] = signals.map(s => ({
    id: s.id,
    date: s.detectedAt.split('T')[0],
    type: "signal" as const,
    title: s.title,
    category: s.signalCategory,
    impact: s.impact,
  }));

  const transactionItems: IntegratedTimelineItem[] = transactions.map(t => ({
    id: t.id,
    date: t.date,
    type: "bank" as const,
    title: t.title,
    bankTransactionType: t.type,
  }));

  return [...signalItems, ...transactionItems].sort((a, b) =>
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};

// 근거 수집 (기업별)
export const getAllEvidencesForCorporation = (corporationId: string): Evidence[] => {
  const signals = getSignalsByCorporationId(corporationId);
  const evidences: Evidence[] = [];

  signals.forEach(signal => {
    if (signal.evidences) {
      evidences.push(...signal.evidences);
    }
  });

  return evidences;
};

// 상대 시간 표시
export const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return date.toLocaleDateString('ko-KR');
};

// 날짜 포맷팅
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

// 은행 거래 타입 레이블
export const getBankTransactionTypeLabel = (type: BankTransaction["type"]): string => {
  const labels: Record<BankTransaction["type"], string> = {
    loan: "여신",
    deposit: "수신",
    fx: "외환",
    pension: "퇴직연금",
    payroll: "급여",
    card: "카드",
  };
  return labels[type];
};
