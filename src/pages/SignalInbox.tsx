import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { DemoPanel } from "@/components/demo/DemoPanel";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG, SIGNAL_STRENGTH_CONFIG } from "@/types/signal";
import { formatRelativeTime } from "@/data/signals";
import { useSignals, useSignalStats } from "@/hooks/useApi";
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

import { GravityGrid } from "@/components/dashboard/GravityGrid";
import { LevitatingCard } from "@/components/dashboard/LevitatingCard";

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

  // API에서 데이터 로드
  const { data: signals = [], isLoading, error } = useSignals();
  const { data: stats } = useSignalStats();

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus, signals]);

  const counts = useMemo(() => ({
    all: stats?.total || signals.length,
    new: stats?.new || signals.filter(s => s.status === "new").length,
    review: stats?.review || signals.filter(s => s.status === "review").length,
    resolved: stats?.resolved || signals.filter(s => s.status === "resolved").length,
    todayNew: stats?.new || signals.filter(s => s.status === "new").length,
    riskHigh7d: stats?.risk || signals.filter(s => s.impact === "risk").length,
    opportunity7d: stats?.opportunity || signals.filter(s => s.impact === "opportunity").length,
    loanEligible: 6,
  }), [signals, stats]);

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

  // 로딩 상태
  if (isLoading) {
    return (
      <MainLayout>
        <div className="max-w-7xl">
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">시그널 데이터를 불러오는 중...</p>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <MainLayout>
        <div className="max-w-7xl">
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center">
            <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
            <p className="text-destructive font-medium">데이터 로드 중 오류가 발생했습니다</p>
            <p className="text-sm text-muted-foreground mt-1">잠시 후 다시 시도해주세요</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-[1600px] mx-auto p-6">
        {/* Demo Panel (Demo Mode에서만 표시) */}
        {/* <DemoPanel /> */}

        {/* KPI Cards - Kept as "Satellites" */}
        <div className="grid grid-cols-4 gap-4 mb-10">
          <KPICard icon={AlertCircle} label="금일 신규 시그널" value={counts.todayNew} trend="오늘" colorClass="text-signal-new" bgClass="bg-signal-new/10" />
          <KPICard icon={TrendingDown} label="위험 시그널 (7일)" value={counts.riskHigh7d} trend="최근 7일" colorClass="text-risk" bgClass="bg-risk/10" />
          <KPICard icon={TrendingUp} label="기회 시그널 (7일)" value={counts.opportunity7d} trend="최근 7일" colorClass="text-opportunity" bgClass="bg-opportunity/10" />
          <KPICard icon={Lightbulb} label="여신 거래 법인" value={counts.loanEligible} trend="참고용" colorClass="text-insight" bgClass="bg-insight/10" />
        </div>

        {/* Filters and Title */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-1 bg-secondary/50 backdrop-blur-sm rounded-lg p-1 border border-border/50">
            {statusFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveStatus(filter.id as typeof activeStatus)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-300 ${activeStatus === filter.id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground hover:bg-background/50"}`}
              >
                {filter.label}
                <span className={`ml-2 ${activeStatus === filter.id ? "text-primary" : "text-muted-foreground"}`}>{filter.count}</span>
              </button>
            ))}
          </div>
          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:ring-2 focus:ring-primary/20 outline-none">
            <option value="recent">최신순</option>
            <option value="impact">영향도순</option>
            <option value="corporation">기업명순</option>
          </select>
        </div>

        {/* 2. Levitating Asset Grid */}
        <GravityGrid>
          {filteredSignals.map((signal, idx) => (
            <LevitatingCard
              key={signal.id}
              signal={signal}
              index={idx}
              onClick={handleRowClick}
            />
          ))}
        </GravityGrid>

        {filteredSignals.length === 0 && (
          <div className="text-center py-32 bg-card/30 rounded-2xl border border-dashed border-border/50">
            <p className="text-muted-foreground text-lg">선택한 조건에 해당하는 시그널이 없습니다.</p>
            <p className="text-sm text-muted-foreground/50 mt-2">다른 검색어나 필터를 시도해보세요.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
