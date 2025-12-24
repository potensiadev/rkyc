import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG, SIGNAL_STRENGTH_CONFIG } from "@/types/signal";
import { SIGNALS, formatRelativeTime } from "@/data/signals";
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

function getSignalTypeIcon(category: "direct" | "industry" | "environment") {
  switch (category) {
    case "direct": return Building2;
    case "industry": return Factory;
    case "environment": return Globe;
  }
}

function getImpactIcon(impact: "risk" | "opportunity" | "neutral") {
  switch (impact) {
    case "risk": return TrendingDown;
    case "opportunity": return TrendingUp;
    case "neutral": return FileText;
  }
}

export default function SignalInbox() {
  const navigate = useNavigate();
  const [activeStatus, setActiveStatus] = useState<"all" | "new" | "review" | "resolved">("all");

  const filteredSignals = useMemo(() => {
    return SIGNALS.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus]);

  const counts = useMemo(() => ({
    all: SIGNALS.length,
    new: SIGNALS.filter(s => s.status === "new").length,
    review: SIGNALS.filter(s => s.status === "review").length,
    resolved: SIGNALS.filter(s => s.status === "resolved").length,
    todayNew: SIGNALS.filter(s => s.status === "new").length,
    riskHigh7d: SIGNALS.filter(s => s.impact === "risk").length,
    opportunity7d: SIGNALS.filter(s => s.impact === "opportunity").length,
    loanEligible: 6,
  }), []);

  // Click company name -> go to corporate report
  const handleCompanyClick = (corporationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/corporates/${corporationId}`);
  };

  // Click row -> go to signal detail
  const handleRowClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
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
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">AI 감지 최신 RKYC 시그널</h1>
          <p className="text-muted-foreground mt-1">
            AI가 기업, 산업, 외부 환경 이벤트를 선제적으로 모니터링하여 검토가 필요한 시그널을 자동으로 도출합니다.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <KPICard icon={AlertCircle} label="금일 신규 시그널" value={counts.todayNew} trend="오늘" colorClass="text-signal-new" bgClass="bg-signal-new/10" />
          <KPICard icon={TrendingDown} label="위험 시그널 (7일)" value={counts.riskHigh7d} trend="최근 7일" colorClass="text-risk" bgClass="bg-risk/10" />
          <KPICard icon={TrendingUp} label="기회 시그널 (7일)" value={counts.opportunity7d} trend="최근 7일" colorClass="text-opportunity" bgClass="bg-opportunity/10" />
          <KPICard icon={Lightbulb} label="여신 거래 법인" value={counts.loanEligible} trend="참고용" colorClass="text-insight" bgClass="bg-insight/10" />
        </div>

        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
            {statusFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveStatus(filter.id as typeof activeStatus)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeStatus === filter.id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                {filter.label}
                <span className={`ml-2 ${activeStatus === filter.id ? "text-primary" : "text-muted-foreground"}`}>{filter.count}</span>
              </button>
            ))}
          </div>
          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground">
            <option value="recent">최신순</option>
            <option value="impact">영향도순</option>
            <option value="corporation">기업명순</option>
          </select>
        </div>

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
                  <TableRow key={signal.id} className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={() => handleRowClick(signal.id)}>
                    <TableCell>
                      <div 
                        className="font-medium text-foreground hover:text-primary hover:underline cursor-pointer"
                        onClick={(e) => handleCompanyClick(signal.corporationId, e)}
                      >
                        {signal.corporationName}
                      </div>
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
                      <span className={`text-xs font-medium ${signal.impactStrength === "high" ? "text-risk" : signal.impactStrength === "medium" ? "text-warning" : "text-muted-foreground"}`}>
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
                        {formatRelativeTime(signal.detectedAt)}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {filteredSignals.length === 0 && (
          <div className="text-center py-16 bg-card rounded-lg border border-border">
            <p className="text-muted-foreground">선택한 조건에 해당하는 시그널이 없습니다.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
