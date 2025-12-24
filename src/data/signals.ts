// 중앙화된 시그널 데이터
// 모든 화면에서 동일한 시그널 정보를 사용합니다.
// 전북/광주 지역 법인 고객 기반

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
    corporationId: "1",
    corporationName: "전북식품",
    date: "2024-12-15",
    type: "loan",
    title: "운영자금 대출 10억원 추가 실행",
    amount: "10억원",
  },
  {
    id: "bt2",
    corporationId: "1",
    corporationName: "전북식품",
    date: "2024-11-20",
    type: "fx",
    title: "수출 대금 결제 (미국 수입사)",
    amount: "USD 850,000",
  },
  {
    id: "bt3",
    corporationId: "2",
    corporationName: "광주정밀기계",
    date: "2024-12-10",
    type: "loan",
    title: "시설자금 대출 20억원 실행",
    amount: "20억원",
  },
  {
    id: "bt4",
    corporationId: "3",
    corporationName: "익산바이오텍",
    date: "2024-12-01",
    type: "pension",
    title: "퇴직연금 가입 (DC형)",
  },
  {
    id: "bt5",
    corporationId: "5",
    corporationName: "군산조선기자재",
    date: "2024-11-28",
    type: "fx",
    title: "수입 신용장 개설",
    amount: "EUR 1,200,000",
  },
  {
    id: "bt6",
    corporationId: "8",
    corporationName: "광주모빌리티",
    date: "2024-12-18",
    type: "loan",
    title: "R&D 자금 대출 50억원 실행",
    amount: "50억원",
  },
];

export const SIGNALS: Signal[] = [
  {
    id: "1",
    corporationName: "전북식품",
    corporationId: "1",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "전북식품, 미국 대형 유통망 입점 계약 체결",
    summary: "전북식품이 미국 코스트코 전 매장 입점 계약을 체결한 것으로 확인되었습니다. 수출 물량 확대가 예상됩니다.",
    source: "전북일보",
    sourceUrl: "https://example.com",
    detectedAt: "2024-12-24T09:50:00",
    detailCategory: "사업 확장",
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "investment_ma",
    aiSummary: "전북식품이 미국 대형 유통망 입점 계약을 체결했습니다. 이는 수출 규모 확대와 매출 성장에 긍정적 영향을 미칠 수 있습니다.",
    evidences: [
      {
        id: "e1",
        sourceType: "news",
        title: "전북식품, 코스트코 전 매장 입점 확정",
        snippet: "전북 대표 식품기업 전북식품이 미국 코스트코...",
        sourceName: "전북일보",
        publishedAt: "2024-12-24",
      },
      {
        id: "e2",
        sourceType: "disclosure",
        title: "주요 수출 계약 체결 공시",
        snippet: "미국 소재 대형 유통업체와 연간 공급 계약 체결",
        sourceName: "금융감독원 전자공시",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "2",
    corporationName: "광주정밀기계",
    corporationId: "2",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "광주정밀기계, 현대차 신규 부품 공급 계약 수주",
    summary: "광주정밀기계가 현대자동차 전기차 플랫폼용 핵심 부품 5년 장기공급 계약을 체결했습니다.",
    source: "광주매일신문",
    detectedAt: "2024-12-24T09:35:00",
    detailCategory: "수주/계약",
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 4,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "financial_change",
    evidences: [
      {
        id: "e3",
        sourceType: "news",
        title: "광주정밀기계, 현대차 전기차 부품 공급사 선정",
        snippet: "광주정밀기계가 현대자동차 전기차 플랫폼...",
        sourceName: "광주매일신문",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "3",
    corporationName: "익산바이오텍",
    corporationId: "3",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "익산바이오텍, 신규 동물용 의약품 품목 허가 취득",
    summary: "익산바이오텍이 개발한 신규 동물용 백신 2종이 농림축산검역본부 품목허가를 취득했습니다.",
    source: "농림축산검역본부",
    detectedAt: "2024-12-24T09:00:00",
    detailCategory: "인허가",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 2,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "regulation",
    evidences: [
      {
        id: "e4",
        sourceType: "regulation",
        title: "동물용 의약품 품목허가 고시",
        snippet: "익산바이오텍 동물용 백신 2종 품목허가",
        sourceName: "농림축산검역본부",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "4",
    corporationName: "나주태양에너지",
    corporationId: "4",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "태양광 모듈 가격 급락, 업계 수익성 압박 지속",
    summary: "중국산 태양광 모듈 가격 하락이 지속되며 국내 태양광 업계 전반의 수익성 악화가 우려되고 있습니다.",
    source: "한국에너지공단",
    detectedAt: "2024-12-24T08:00:00",
    detailCategory: "시장 동향",
    relevanceNote: "나주태양에너지는 태양광 모듈 제조 비중이 매출의 60%를 차지합니다.",
    relatedCorporations: ["한화큐셀", "현대에너지솔루션"],
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e5",
        sourceType: "report",
        title: "2024년 태양광 산업 동향 보고서",
        snippet: "중국산 모듈 가격 하락으로 국내 업계 수익성 압박",
        sourceName: "한국에너지공단",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "5",
    corporationName: "군산조선기자재",
    corporationId: "5",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "new",
    title: "군산조선기자재, HD한국조선해양과 합작법인 설립 추진",
    summary: "군산조선기자재와 HD한국조선해양이 친환경 선박 부품 생산을 위한 합작법인 설립을 협의 중입니다.",
    source: "전자공시시스템",
    detectedAt: "2024-12-23T10:00:00",
    detailCategory: "투자/제휴",
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "investment_ma",
    evidences: [
      {
        id: "e6",
        sourceType: "disclosure",
        title: "합작법인 설립 검토 공시",
        snippet: "HD한국조선해양과 친환경 선박부품 JV 설립 협의",
        sourceName: "전자공시시스템",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "6",
    corporationName: "무안물류",
    corporationId: "6",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "전남 서남권 물류 인프라 확충 계획 발표",
    summary: "전라남도가 무안국제공항 화물터미널 확장 및 항만 연계 물류단지 조성 계획을 발표했습니다.",
    source: "전라남도",
    detectedAt: "2024-12-24T07:00:00",
    detailCategory: "인프라 정책",
    relevanceNote: "무안물류는 무안국제공항 인근에 주요 물류시설을 운영하고 있습니다.",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 2,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e7",
        sourceType: "regulation",
        title: "전남 서남권 물류 인프라 확충 계획",
        snippet: "무안국제공항 화물터미널 확장 및 항만 연계",
        sourceName: "전라남도",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "7",
    corporationName: "광주모빌리티",
    corporationId: "8",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "전기차 배터리 팩 수요 급증, 국내 부품업체 수주 호조",
    summary: "글로벌 전기차 시장 성장에 따라 국내 배터리 팩 및 BMS 제조업체들의 수주가 크게 증가하고 있습니다.",
    source: "한국자동차산업협회",
    detectedAt: "2024-12-24T06:00:00",
    detailCategory: "시장 동향",
    relevanceNote: "광주모빌리티는 배터리 팩 및 BMS 전문 제조업체입니다.",
    relatedCorporations: ["SK온", "삼성SDI"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 6,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e8",
        sourceType: "report",
        title: "전기차 부품 산업 동향 분석",
        snippet: "배터리 팩 수요 급증, 국내 업체 수주 호조",
        sourceName: "한국자동차산업협회",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "8",
    corporationName: "정읍농산",
    corporationId: "7",
    signalCategory: "industry",
    signalSubType: "regulatory",
    status: "review",
    title: "친환경 농산물 인증 기준 강화 예고",
    summary: "농림축산식품부가 친환경 농산물 인증 기준을 강화하는 개정안을 예고했습니다.",
    source: "농림축산식품부",
    detectedAt: "2024-12-24T05:00:00",
    detailCategory: "농업 정책",
    relevanceNote: "정읍농산은 친환경 유기농 농산물 전문 생산업체입니다.",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 2,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e9",
        sourceType: "regulation",
        title: "친환경 농산물 인증 기준 강화 예고",
        snippet: "친환경 인증 심사 기준 강화 개정안",
        sourceName: "농림축산식품부",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "9",
    corporationName: "전북식품",
    corporationId: "1",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "K-푸드 수출 호조, 발효식품 수요 증가",
    summary: "K-푸드 열풍에 따라 김치, 장류 등 전통 발효식품의 글로벌 수요가 지속 증가하고 있습니다.",
    source: "한국농수산식품유통공사",
    detectedAt: "2024-12-22T10:00:00",
    detailCategory: "시장 동향",
    relevanceNote: "전북식품은 김치 수출 전문 기업으로 북미 시장 점유율이 높습니다.",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 4,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e10",
        sourceType: "report",
        title: "K-푸드 수출 동향 보고서",
        snippet: "전통 발효식품 수출 전년비 25% 증가",
        sourceName: "한국농수산식품유통공사",
        publishedAt: "2024-12-22",
      },
    ],
  },
  {
    id: "10",
    corporationName: "광주정밀기계",
    corporationId: "2",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "review",
    title: "원자재 가격 상승세 지속, 철강재 조달 비용 증가",
    summary: "글로벌 원자재 가격 상승이 지속되며 기계부품 제조업체들의 원가 부담이 증가하고 있습니다.",
    source: "한국철강협회",
    detectedAt: "2024-12-19T14:00:00",
    detailCategory: "원자재",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e11",
        sourceType: "report",
        title: "철강재 가격 동향 분석",
        snippet: "철강재 가격 전월비 5% 상승",
        sourceName: "한국철강협회",
        publishedAt: "2024-12-19",
      },
    ],
  },
  {
    id: "11",
    corporationName: "광주모빌리티",
    corporationId: "8",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "광주모빌리티, 기아 EV9용 배터리팩 공급사 선정",
    summary: "광주모빌리티가 기아 EV9 북미 생산분 배터리팩 단독 공급사로 선정되었습니다.",
    source: "광주경제",
    detectedAt: "2024-12-20T11:00:00",
    detailCategory: "수주/계약",
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "financial_change",
    evidences: [
      {
        id: "e12",
        sourceType: "news",
        title: "광주모빌리티, 기아 EV9 배터리팩 공급",
        snippet: "기아 EV9 북미 생산분 배터리팩 단독 공급",
        sourceName: "광주경제",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "12",
    corporationName: "군산조선기자재",
    corporationId: "5",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "친환경 선박 수주 급증, 조선 기자재 업황 호조",
    summary: "IMO 환경 규제 강화로 친환경 선박 수주가 급증하며 조선 기자재 업계가 호황을 맞고 있습니다.",
    source: "한국조선해양기자재산업협회",
    detectedAt: "2024-12-21T09:00:00",
    detailCategory: "산업 동향",
    relevanceNote: "군산조선기자재는 친환경 선박 부품 전문 제조업체입니다.",
    relatedCorporations: ["HD한국조선해양", "삼성중공업"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 4,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e13",
        sourceType: "report",
        title: "조선 기자재 산업 동향",
        snippet: "친환경 선박 수주 증가로 기자재 업황 호조",
        sourceName: "한국조선해양기자재산업협회",
        publishedAt: "2024-12-21",
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
