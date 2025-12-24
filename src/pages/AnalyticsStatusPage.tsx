import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { 
  Radio, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Building2,
  Factory,
  Globe,
  ChevronRight
} from "lucide-react";

interface KpiCard {
  id: string;
  title: string;
  value: number;
  icon: React.ElementType;
}

const kpiCards: KpiCard[] = [
  {
    id: "detected-today",
    title: "오늘 감지된 시그널",
    value: 24,
    icon: Radio,
  },
  {
    id: "pending-review",
    title: "검토 대기 시그널",
    value: 18,
    icon: Clock,
  },
  {
    id: "in-review",
    title: "검토 중 시그널",
    value: 5,
    icon: AlertCircle,
  },
  {
    id: "completed",
    title: "검토 완료 시그널",
    value: 142,
    icon: CheckCircle2,
  },
];

interface SignalTypeData {
  id: string;
  label: string;
  count: number;
  icon: React.ElementType;
  colorClass: string;
}

const signalTypeData: SignalTypeData[] = [
  {
    id: "direct",
    label: "직접 시그널",
    count: 45,
    icon: Building2,
    colorClass: "bg-primary/20",
  },
  {
    id: "industry",
    label: "산업 시그널",
    count: 78,
    icon: Factory,
    colorClass: "bg-accent",
  },
  {
    id: "environment",
    label: "환경 시그널",
    count: 43,
    icon: Globe,
    colorClass: "bg-muted",
  },
];

interface ImpactData {
  id: string;
  label: string;
  count: number;
  dotClass: string;
}

const impactData: ImpactData[] = [
  { id: "risk", label: "위험", count: 32, dotClass: "bg-destructive/60" },
  { id: "opportunity", label: "기회", count: 28, dotClass: "bg-primary/60" },
  { id: "reference", label: "참고", count: 106, dotClass: "bg-muted-foreground/40" },
];

interface ProcessingFlowData {
  id: string;
  label: string;
  count: number;
}

const processingFlowData: ProcessingFlowData[] = [
  { id: "new", label: "신규", count: 18 },
  { id: "in-progress", label: "검토 중", count: 5 },
  { id: "completed", label: "검토 완료", count: 142 },
];

interface RecentSignal {
  id: string;
  corporateName: string;
  signalType: "direct" | "industry" | "environment";
  impact: "risk" | "opportunity" | "reference";
  detectedAt: string;
}

const recentSignals: RecentSignal[] = [
  {
    id: "sig-1",
    corporateName: "삼성전자",
    signalType: "industry",
    impact: "opportunity",
    detectedAt: "10분 전",
  },
  {
    id: "sig-2",
    corporateName: "현대자동차",
    signalType: "environment",
    impact: "risk",
    detectedAt: "25분 전",
  },
  {
    id: "sig-3",
    corporateName: "카카오",
    signalType: "direct",
    impact: "risk",
    detectedAt: "1시간 전",
  },
  {
    id: "sig-4",
    corporateName: "LG에너지솔루션",
    signalType: "industry",
    impact: "reference",
    detectedAt: "2시간 전",
  },
];

const signalTypeLabels = {
  direct: "직접",
  industry: "산업",
  environment: "환경",
};

const signalTypeStyles = {
  direct: "bg-primary/10 text-primary",
  industry: "bg-accent text-accent-foreground",
  environment: "bg-muted text-muted-foreground",
};

const impactLabels = {
  risk: "위험",
  opportunity: "기회",
  reference: "참고",
};

const impactStyles = {
  risk: "bg-destructive/10 text-destructive/80",
  opportunity: "bg-primary/10 text-primary",
  reference: "bg-muted text-muted-foreground",
};

export default function AnalyticsStatusPage() {
  const navigate = useNavigate();
  const totalSignalTypes = signalTypeData.reduce((sum, item) => sum + item.count, 0);

  return (
    <MainLayout>
      <div className="max-w-6xl space-y-6">
        {/* Page Header */}
        <div className="mb-2">
          <h1 className="text-2xl font-semibold text-foreground">분석 현황</h1>
          <p className="text-muted-foreground mt-1">
            RKYC 시스템이 감지·분석 중인 시그널 현황을 한눈에 확인할 수 있습니다.
            <br />
            모든 정보는 참고 및 검토용으로 제공됩니다.
          </p>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpiCards.map((card) => (
            <div
              key={card.id}
              className="bg-card rounded-lg border border-border p-5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{card.title}</p>
                  <p className="text-3xl font-semibold text-foreground mt-1">
                    {card.value}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-muted/50 flex items-center justify-center">
                  <card.icon className="w-5 h-5 text-muted-foreground" />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Signal Type Distribution */}
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="font-medium text-foreground mb-4">시그널 유형별 현황</h2>
            <div className="space-y-4">
              {signalTypeData.map((item) => {
                const percentage = Math.round((item.count / totalSignalTypes) * 100);
                return (
                  <div key={item.id}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <item.icon className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-foreground">{item.label}</span>
                      </div>
                      <span className="text-sm font-medium text-foreground">{item.count}</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${item.colorClass} rounded-full transition-all`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              총 {totalSignalTypes}건의 시그널이 분석 대상으로 등록되어 있습니다.
            </p>
          </div>

          {/* Impact Category Overview */}
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="font-medium text-foreground mb-4">영향 구분 현황</h2>
            <div className="space-y-3">
              {impactData.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between py-3 border-b border-border last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${item.dotClass}`} />
                    <span className="text-sm text-foreground">{item.label}</span>
                  </div>
                  <span className="text-lg font-medium text-foreground">{item.count}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              영향 구분은 시그널 내용에 따라 분류되며, 판단 기준이 아닙니다.
            </p>
          </div>
        </div>

        {/* Signal Processing Flow */}
        <div className="bg-card rounded-lg border border-border p-6">
          <h2 className="font-medium text-foreground mb-4">시그널 처리 흐름</h2>
          <div className="flex items-center justify-center gap-4 py-4">
            {processingFlowData.map((item, index) => (
              <div key={item.id} className="flex items-center gap-4">
                <div className="text-center min-w-[100px]">
                  <div className="w-16 h-16 mx-auto rounded-full bg-muted/50 border border-border flex items-center justify-center mb-2">
                    <span className="text-2xl font-semibold text-foreground">{item.count}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">{item.label}</span>
                </div>
                {index < processingFlowData.length - 1 && (
                  <ChevronRight className="w-5 h-5 text-muted-foreground/50" />
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">
            모든 시그널은 담당자 검토를 거쳐 처리됩니다.
          </p>
        </div>

        {/* Recently Detected Signals */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="font-medium text-foreground">최근 감지된 주요 시그널</h2>
            <p className="text-sm text-muted-foreground mt-0.5">최근 감지된 시그널 (참고용)</p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  법인명
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  시그널 유형
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  영향 구분
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  감지 시각
                </th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {recentSignals.map((signal) => (
                <tr
                  key={signal.id}
                  onClick={() => navigate(`/signals/${signal.id}`)}
                  className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors cursor-pointer group"
                >
                  <td className="px-6 py-4">
                    <span className="font-medium text-foreground">{signal.corporateName}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${signalTypeStyles[signal.signalType]}`}>
                      {signalTypeLabels[signal.signalType]}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${impactStyles[signal.impact]}`}>
                      {impactLabels[signal.impact]}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {signal.detectedAt}
                  </td>
                  <td className="px-6 py-4">
                    <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Compliance Disclaimer */}
        <p className="text-xs text-muted-foreground text-center py-4">
          본 화면의 모든 정보는 참고 및 검토용으로 제공되며,
          <br />
          자동 판단, 점수화, 또는 조치를 의미하지 않습니다.
        </p>
      </div>
    </MainLayout>
  );
}
