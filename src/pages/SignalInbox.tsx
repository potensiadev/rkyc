import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Signal, SignalStatus, SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG, SIGNAL_STRENGTH_CONFIG } from "@/types/signal";
import { 
  AlertCircle, 
  TrendingUp, 
  TrendingDown, 
  Lightbulb, 
  Building2, 
  Factory, 
  Globe,
  FileText,
  Clock
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const mockSignals: Signal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "124-81-00998",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다.",
    source: "연합뉴스",
    sourceUrl: "https://example.com",
    detectedAt: "10분 전",
    detailCategory: "인사/조직",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
  },
  {
    id: "2",
    corporationName: "현대자동차",
    corporationId: "101-81-15555",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "현대자동차 2024년 3분기 영업이익 전년 대비 15% 감소",
    summary: "현대자동차의 2024년 3분기 영업이익이 전년 동기 대비 15% 감소한 것으로 잠정 집계되었습니다.",
    source: "금융감독원 전자공시",
    detectedAt: "25분 전",
    detailCategory: "실적/재무",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 3,
  },
  {
    id: "3",
    corporationName: "카카오",
    corporationId: "120-81-47521",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "공정거래위원회, 카카오 플랫폼 독점 관련 조사 착수",
    summary: "공정거래위원회가 카카오의 플랫폼 시장 지배력 남용 혐의에 대한 본격적인 조사에 착수했습니다.",
    source: "공정거래위원회",
    detectedAt: "1시간 전",
    detailCategory: "규제/법률",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 4,
  },
  {
    id: "4",
    corporationName: "LG에너지솔루션",
    corporationId: "110-81-12345",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "전기차 배터리 산업 전반 수요 둔화 조짐",
    summary: "글로벌 전기차 시장의 성장 속도가 예상보다 더딘 것으로 나타나, 배터리 산업 전반에 영향이 관찰되고 있습니다.",
    source: "한국에너지공단",
    detectedAt: "2시간 전",
    detailCategory: "시장 동향",
    relevanceNote: "LG에너지솔루션은 글로벌 2차전지 시장 점유율 상위 기업입니다.",
    relatedCorporations: ["삼성SDI", "SK온", "CATL"],
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 6,
  },
  {
    id: "5",
    corporationName: "네이버",
    corporationId: "220-81-62517",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "resolved",
    title: "네이버, AI 스타트업 인수 완료 공시",
    summary: "네이버가 국내 AI 스타트업 인수를 공식 완료했습니다. 검토 완료.",
    source: "전자공시시스템",
    detectedAt: "어제",
    detailCategory: "인수합병",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 2,
  },
  {
    id: "6",
    corporationName: "포스코홀딩스",
    corporationId: "102-81-45678",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "미국 철강 관세 인상 발표, 수출 기업 영향 관련 정보",
    summary: "미국 정부가 철강 및 알루미늄에 대한 추가 관세 부과를 발표했습니다.",
    source: "외교부",
    detectedAt: "3시간 전",
    detailCategory: "무역 정책",
    relevanceNote: "포스코홀딩스는 미국 수출 비중이 약 15%입니다.",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 4,
  },
  {
    id: "7",
    corporationName: "SK하이닉스",
    corporationId: "105-81-11111",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    summary: "생성형 AI 확산에 따라 고대역폭 메모리(HBM) 수요가 급증하고 있습니다.",
    source: "한국반도체산업협회",
    detectedAt: "4시간 전",
    detailCategory: "기술 동향",
    relevanceNote: "SK하이닉스는 HBM 시장 점유율 1위 기업입니다.",
    relatedCorporations: ["삼성전자", "마이크론"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 8,
  },
  {
    id: "8",
    corporationName: "한국전력공사",
    corporationId: "120-81-99999",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "review",
    title: "정부, 전기요금 체계 개편안 발표 예정",
    summary: "정부가 내년 상반기 전기요금 체계 전면 개편안을 발표할 예정입니다.",
    source: "산업통상자원부",
    detectedAt: "5시간 전",
    detailCategory: "에너지 정책",
    relevanceNote: "한국전력공사의 수익 구조에 직접적 영향을 미칠 수 있습니다.",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 3,
  },
];

interface KPICardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: string;
  colorClass?: string;
  bgClass?: string;
}

function KPICard({ icon: Icon, label, value, trend, colorClass = "text-primary", bgClass = "bg-accent" }: KPICardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg ${bgClass} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${colorClass}`} />
        </div>
        {trend && (
          <span className="text-xs text-muted-foreground">{trend}</span>
        )}
      </div>
      <p className="text-2xl font-semibold text-foreground">{value}</p>
      <p className="text-sm text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

function getSignalTypeIcon(category: Signal["signalCategory"]) {
  switch (category) {
    case "direct":
      return Building2;
    case "industry":
      return Factory;
    case "environment":
      return Globe;
  }
}

function getImpactIcon(impact: Signal["impact"]) {
  switch (impact) {
    case "risk":
      return TrendingDown;
    case "opportunity":
      return TrendingUp;
    case "neutral":
      return FileText;
  }
}

export default function SignalInbox() {
  const navigate = useNavigate();
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return mockSignals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus]);

  const counts = useMemo(() => ({
    all: mockSignals.length,
    new: mockSignals.filter(s => s.status === "new").length,
    review: mockSignals.filter(s => s.status === "review").length,
    resolved: mockSignals.filter(s => s.status === "resolved").length,
    todayNew: mockSignals.filter(s => s.status === "new").length,
    riskHigh7d: mockSignals.filter(s => s.impact === "risk").length,
    opportunity7d: mockSignals.filter(s => s.impact === "opportunity").length,
    loanEligible: 24,
  }), []);

  const handleViewDetail = (signal: Signal) => {
    navigate(`/signals/${signal.id}`);
  };

  const statusFilters = [
    { id: "all", label: "전체", count: counts.all },
    { id: "new", label: "신규", count: counts.new },
    { id: "review", label: "검토중", count: counts.review },
    { id: "resolved", label: "완료", count: counts.resolved },
  ];

  return (
    <MainLayout>
      <div className="max-w-7xl">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">AI 감지 최신 RKYC 시그널</h1>
          <p className="text-muted-foreground mt-1">
            AI가 기업, 산업, 외부 환경 이벤트를 선제적으로 모니터링하여 검토가 필요한 시그널을 자동으로 도출합니다.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <KPICard
            icon={AlertCircle}
            label="금일 신규 시그널"
            value={counts.todayNew}
            trend="오늘"
            colorClass="text-signal-new"
            bgClass="bg-signal-new/10"
          />
          <KPICard
            icon={TrendingDown}
            label="위험 시그널 (7일)"
            value={counts.riskHigh7d}
            trend="최근 7일"
            colorClass="text-risk"
            bgClass="bg-risk/10"
          />
          <KPICard
            icon={TrendingUp}
            label="기회 시그널 (7일)"
            value={counts.opportunity7d}
            trend="최근 7일"
            colorClass="text-opportunity"
            bgClass="bg-opportunity/10"
          />
          <KPICard
            icon={Lightbulb}
            label="여신 인사이트 대상 법인"
            value={counts.loanEligible}
            trend="참고용"
            colorClass="text-insight"
            bgClass="bg-insight/10"
          />
        </div>

        {/* Status filters */}
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
            {statusFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveStatus(filter.id as SignalStatus | "all")}
                className={`
                  px-4 py-2 rounded-md text-sm font-medium transition-colors
                  ${activeStatus === filter.id
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                  }
                `}
              >
                {filter.label}
                <span className={`ml-2 ${activeStatus === filter.id ? "text-primary" : "text-muted-foreground"}`}>
                  {filter.count}
                </span>
              </button>
            ))}
          </div>

          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
            <option value="recent">최신순</option>
            <option value="impact">영향도순</option>
            <option value="corporation">기업명순</option>
          </select>
        </div>

        {/* Signal Feed Table */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="w-[140px]">법인명</TableHead>
                <TableHead className="w-[100px]">시그널 유형</TableHead>
                <TableHead className="w-[80px]">영향</TableHead>
                <TableHead className="w-[80px]">영향 강도</TableHead>
                <TableHead>AI 요약 (참고용)</TableHead>
                <TableHead className="w-[80px] text-center">근거 수</TableHead>
                <TableHead className="w-[100px]">감지 시간</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSignals.map((signal) => {
                const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
                const impactConfig = SIGNAL_IMPACT_CONFIG[signal.impact];
                const strengthConfig = SIGNAL_STRENGTH_CONFIG[signal.impactStrength];
                const TypeIcon = getSignalTypeIcon(signal.signalCategory);
                const ImpactIcon = getImpactIcon(signal.impact);

                return (
                  <TableRow 
                    key={signal.id} 
                    className="cursor-pointer hover:bg-muted/30 transition-colors"
                    onClick={() => handleViewDetail(signal)}
                  >
                    <TableCell>
                      <div className="font-medium text-foreground">{signal.corporationName}</div>
                      <div className="text-xs text-muted-foreground">{signal.corporationId}</div>
                    </TableCell>
                    <TableCell>
                      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
                        <TypeIcon className="w-3 h-3" />
                        {typeConfig.label}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${impactConfig.bgClass} ${impactConfig.colorClass}`}>
                        <ImpactIcon className="w-3 h-3" />
                        {impactConfig.label}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`text-xs font-medium ${
                        signal.impactStrength === "high" 
                          ? "text-risk" 
                          : signal.impactStrength === "medium" 
                            ? "text-warning" 
                            : "text-muted-foreground"
                      }`}>
                        {strengthConfig.label}
                      </span>
                    </TableCell>
                    <TableCell>
                      <p className="text-sm text-foreground line-clamp-1">{signal.summary}</p>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-muted text-xs font-medium text-foreground">
                        {signal.evidenceCount}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {signal.detectedAt}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {/* Empty state */}
        {filteredSignals.length === 0 && (
          <div className="text-center py-16 bg-card rounded-lg border border-border">
            <p className="text-muted-foreground">선택한 조건에 해당하는 시그널이 없습니다.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}