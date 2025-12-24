// 중앙화된 시그널 데이터
// 모든 화면에서 동일한 시그널 정보를 사용합니다.

import { Signal, SignalCategory, SignalStatus, SignalImpact, Evidence } from "@/types/signal";

export const SIGNALS: Signal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "1",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다.",
    source: "연합뉴스",
    sourceUrl: "https://example.com",
    detectedAt: "2024-12-24T09:50:00",
    detailCategory: "인사/조직",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "governance",
    aiSummary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다. 해당 정보는 언론 보도를 기반으로 수집되었으며, 공식 확인은 필요합니다.",
    evidences: [
      {
        id: "e1",
        sourceType: "news",
        title: "삼성전자 반도체 인력 구조조정 검토",
        snippet: "삼성전자가 반도체 사업부 경쟁력 강화를 위해...",
        sourceName: "연합뉴스",
        publishedAt: "2024-12-24",
      },
      {
        id: "e2",
        sourceType: "disclosure",
        title: "삼성전자 2024년 3분기 실적 발표",
        snippet: "분기 실적 발표 - 매출 전년 대비 12% 증가",
        sourceName: "금융감독원 전자공시",
        publishedAt: "2024-12-20",
      },
    ],
  },
  {
    id: "2",
    corporationName: "현대자동차",
    corporationId: "2",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "현대자동차 2024년 3분기 영업이익 전년 대비 15% 감소",
    summary: "현대자동차의 2024년 3분기 영업이익이 전년 동기 대비 15% 감소한 것으로 잠정 집계되었습니다.",
    source: "금융감독원 전자공시",
    detectedAt: "2024-12-24T09:35:00",
    detailCategory: "실적/재무",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "financial_change",
    evidences: [
      {
        id: "e3",
        sourceType: "disclosure",
        title: "현대자동차 2024년 3분기 실적 공시",
        snippet: "영업이익 전년 동기 대비 15% 감소",
        sourceName: "금융감독원 전자공시",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "3",
    corporationName: "카카오",
    corporationId: "3",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "공정거래위원회, 카카오 플랫폼 독점 관련 조사 착수",
    summary: "공정거래위원회가 카카오의 플랫폼 시장 지배력 남용 혐의에 대한 본격적인 조사에 착수했습니다.",
    source: "공정거래위원회",
    detectedAt: "2024-12-24T09:00:00",
    detailCategory: "규제/법률",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 4,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "regulation",
    evidences: [
      {
        id: "e4",
        sourceType: "regulation",
        title: "공정거래위원회 조사 착수 발표",
        snippet: "카카오 플랫폼 시장 지배력 남용 혐의 조사",
        sourceName: "공정거래위원회",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "4",
    corporationName: "LG에너지솔루션",
    corporationId: "4",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "전기차 배터리 산업 전반 수요 둔화 조짐",
    summary: "글로벌 전기차 시장의 성장 속도가 예상보다 더딘 것으로 나타나, 배터리 산업 전반에 영향이 관찰되고 있습니다.",
    source: "한국에너지공단",
    detectedAt: "2024-12-24T08:00:00",
    detailCategory: "시장 동향",
    relevanceNote: "LG에너지솔루션은 글로벌 2차전지 시장 점유율 상위 기업입니다.",
    relatedCorporations: ["삼성SDI", "SK온", "CATL"],
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 6,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e5",
        sourceType: "report",
        title: "글로벌 전기차 시장 동향 보고서",
        snippet: "전기차 시장 성장 속도 둔화 분석",
        sourceName: "한국에너지공단",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "5",
    corporationName: "네이버",
    corporationId: "5",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "resolved",
    title: "네이버, AI 스타트업 인수 완료 공시",
    summary: "네이버가 국내 AI 스타트업 인수를 공식 완료했습니다. 검토 완료.",
    source: "전자공시시스템",
    detectedAt: "2024-12-23T10:00:00",
    detailCategory: "인수합병",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 2,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "investment_ma",
    evidences: [
      {
        id: "e6",
        sourceType: "disclosure",
        title: "네이버 AI 스타트업 인수 완료 공시",
        snippet: "AI 기술 역량 강화를 위한 인수 완료",
        sourceName: "전자공시시스템",
        publishedAt: "2024-12-23",
      },
    ],
  },
  {
    id: "6",
    corporationName: "포스코홀딩스",
    corporationId: "6",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "미국 철강 관세 인상 발표, 수출 기업 영향 관련 정보",
    summary: "미국 정부가 철강 및 알루미늄에 대한 추가 관세 부과를 발표했습니다.",
    source: "외교부",
    detectedAt: "2024-12-24T07:00:00",
    detailCategory: "무역 정책",
    relevanceNote: "포스코홀딩스는 미국 수출 비중이 약 15%입니다.",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 4,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e7",
        sourceType: "regulation",
        title: "미국 철강 관세 인상 발표",
        snippet: "철강 및 알루미늄 추가 관세 부과",
        sourceName: "외교부",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "7",
    corporationName: "SK하이닉스",
    corporationId: "7",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    summary: "생성형 AI 확산에 따라 고대역폭 메모리(HBM) 수요가 급증하고 있습니다.",
    source: "한국반도체산업협회",
    detectedAt: "2024-12-24T06:00:00",
    detailCategory: "기술 동향",
    relevanceNote: "SK하이닉스는 HBM 시장 점유율 1위 기업입니다.",
    relatedCorporations: ["삼성전자", "마이크론"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 8,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "market_shift",
    evidences: [
      {
        id: "e8",
        sourceType: "report",
        title: "AI 반도체 시장 동향 분석",
        snippet: "HBM 수요 급증 및 공급 부족 전망",
        sourceName: "한국반도체산업협회",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "8",
    corporationName: "한국전력공사",
    corporationId: "8",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "review",
    title: "정부, 전기요금 체계 개편안 발표 예정",
    summary: "정부가 내년 상반기 전기요금 체계 전면 개편안을 발표할 예정입니다.",
    source: "산업통상자원부",
    detectedAt: "2024-12-24T05:00:00",
    detailCategory: "에너지 정책",
    relevanceNote: "한국전력공사의 수익 구조에 직접적 영향을 미칠 수 있습니다.",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 3,
    confidenceLevel: "medium",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e9",
        sourceType: "regulation",
        title: "전기요금 체계 개편안 예고",
        snippet: "내년 상반기 전면 개편안 발표 예정",
        sourceName: "산업통상자원부",
        publishedAt: "2024-12-24",
      },
    ],
  },
  {
    id: "9",
    corporationName: "삼성전자",
    corporationId: "1",
    signalCategory: "industry",
    signalSubType: "regulatory",
    status: "new",
    title: "반도체 업종 수출 규제 완화 발표",
    summary: "정부가 반도체 업종에 대한 수출 규제 완화 정책을 발표했습니다.",
    source: "산업통상자원부",
    detectedAt: "2024-12-22T10:00:00",
    detailCategory: "산업 정책",
    relevanceNote: "삼성전자는 반도체 수출 비중이 높은 기업입니다.",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 3,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e10",
        sourceType: "regulation",
        title: "반도체 수출 규제 완화 발표",
        snippet: "반도체 업종 수출 규제 완화 정책",
        sourceName: "산업통상자원부",
        publishedAt: "2024-12-22",
      },
    ],
  },
  {
    id: "10",
    corporationName: "삼성전자",
    corporationId: "1",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "review",
    title: "글로벌 금리 인하 기조 확대",
    summary: "주요국 중앙은행들이 금리 인하 기조를 확대하고 있습니다.",
    source: "한국은행",
    detectedAt: "2024-12-19T14:00:00",
    detailCategory: "거시경제",
    impact: "neutral",
    impactStrength: "low",
    evidenceCount: 2,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "policy_change",
    evidences: [
      {
        id: "e11",
        sourceType: "report",
        title: "글로벌 금리 동향 보고서",
        snippet: "주요국 금리 인하 기조 분석",
        sourceName: "한국은행",
        publishedAt: "2024-12-19",
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
