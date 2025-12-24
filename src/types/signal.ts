// Signal Classification System
// Each signal type represents different analysis logic and evidence sources

export type SignalCategory = "direct" | "industry" | "environment";
export type SignalStatus = "new" | "review" | "resolved";
export type SignalSubType = "news" | "financial" | "regulatory" | "governance" | "market" | "macro";

export interface SignalTypeInfo {
  id: SignalCategory;
  label: string;
  description: string;
  analysisLogic: string;
  evidenceSources: string[];
  colorClass: string;
  bgClass: string;
  borderClass: string;
}

export const SIGNAL_TYPE_CONFIG: Record<SignalCategory, SignalTypeInfo> = {
  direct: {
    id: "direct",
    label: "직접 시그널",
    description: "해당 기업에서 직접 발생한 이벤트 및 공시 정보",
    analysisLogic: "기업이 직접 발표하거나, 해당 기업을 명시적으로 언급한 정보를 수집하여 요약합니다.",
    evidenceSources: [
      "금융감독원 전자공시 (DART)",
      "기업 공식 보도자료",
      "언론 보도 (기업 직접 언급)",
      "법원 판결문",
      "규제기관 제재 공시",
    ],
    colorClass: "text-signal-direct",
    bgClass: "bg-signal-direct/10",
    borderClass: "border-signal-direct/30",
  },
  industry: {
    id: "industry",
    label: "산업 시그널",
    description: "해당 기업이 속한 산업군 전반에 영향을 미치는 동향",
    analysisLogic: "동일 산업 내 주요 이벤트를 수집하고, 해당 기업과의 연관성을 참고용으로 제시합니다.",
    evidenceSources: [
      "산업별 협회 발표 자료",
      "업종 내 경쟁사 동향",
      "산업 규제 변화",
      "업종별 시장 리포트",
      "공급망 관련 뉴스",
    ],
    colorClass: "text-signal-industry",
    bgClass: "bg-signal-industry/10",
    borderClass: "border-signal-industry/30",
  },
  environment: {
    id: "environment",
    label: "환경 시그널",
    description: "거시경제, 정책, 글로벌 이슈 등 외부 환경 변화 정보",
    analysisLogic: "매크로 환경 변화를 모니터링하고, 해당 기업에 잠재적 영향이 있을 수 있는 정보를 참고용으로 제공합니다.",
    evidenceSources: [
      "정부 정책 발표",
      "중앙은행 금리 결정",
      "환율 및 원자재 가격",
      "글로벌 무역 이슈",
      "ESG/기후 관련 규제",
    ],
    colorClass: "text-signal-environment",
    bgClass: "bg-signal-environment/10",
    borderClass: "border-signal-environment/30",
  },
};

export const SIGNAL_SUBTYPE_CONFIG: Record<SignalSubType, { label: string; icon: string }> = {
  news: { label: "언론 보도", icon: "FileText" },
  financial: { label: "재무 변동", icon: "TrendingDown" },
  regulatory: { label: "규제/법률", icon: "Scale" },
  governance: { label: "지배구조", icon: "Users" },
  market: { label: "시장 동향", icon: "BarChart3" },
  macro: { label: "거시경제", icon: "Globe" },
};

export const SIGNAL_STATUS_CONFIG: Record<SignalStatus, { label: string; className: string }> = {
  new: { label: "신규", className: "status-new" },
  review: { label: "검토중", className: "status-review" },
  resolved: { label: "완료", className: "status-resolved" },
};

export interface Signal {
  id: string;
  corporationName: string;
  corporationId: string;
  signalCategory: SignalCategory;
  signalSubType: SignalSubType;
  status: SignalStatus;
  title: string;
  summary: string;
  source: string;
  sourceUrl?: string;
  detectedAt: string;
  detailCategory: string;
  relevanceNote?: string; // For industry/environment signals
  relatedCorporations?: string[]; // For industry signals
}
