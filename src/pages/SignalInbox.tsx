import { useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { useSignals, useSignalStats, useLoanInsightSummaries, ApiLoanInsightSummary } from "@/hooks/useApi";
import {
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  Beaker,
  Settings
} from "lucide-react";
import {
  DynamicBackground,
  GlassCard,
  Sparkline,
  StatusBadge
} from "@/components/premium";

import { GroupedSignalCard } from "@/components/dashboard/GroupedSignalCard";

interface KPICardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: string;
  colorClass?: string;
  trendData?: number[]; // Add trend data for sparkline
  sparklineColor?: string;
}

function KPICard({ icon: Icon, label, value, trend, colorClass = "text-primary", trendData, sparklineColor }: KPICardProps) {
  return (
    <GlassCard className="p-5 flex flex-col justify-between h-32">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
          <div className="flex items-center gap-2">
            <span className="text-3xl font-mono font-bold text-slate-900">{value}</span>
          </div>
        </div>
        <div className={`p-2 rounded-xl bg-slate-50 border border-slate-100 ${colorClass}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {trendData ? (
        <div className="h-8 w-full mt-2">
          <Sparkline data={trendData} color={sparklineColor || "#6366f1"} height={30} />
        </div>
      ) : (
        trend && <span className="text-xs font-medium text-slate-400 mt-2">{trend}</span>
      )}
    </GlassCard>
  );
}

export default function SignalInbox() {
  const navigate = useNavigate();
  const [activeStatus, setActiveStatus] = useState<"all" | "new" | "review" | "resolved">("all");

  // API에서 데이터 로드
  const { data: signals = [], isLoading, error } = useSignals();
  const { data: stats } = useSignalStats();
  const { data: insightSummaries } = useLoanInsightSummaries();

  // corp_id -> insight summary 맵 생성
  const insightMap = useMemo(() => {
    const map = new Map<string, ApiLoanInsightSummary>();
    if (insightSummaries?.insights) {
      insightSummaries.insights.forEach((insight) => {
        map.set(insight.corp_id, insight);
      });
    }
    return map;
  }, [insightSummaries]);

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus, signals]);

  // 기업별로 시그널 그룹핑
  const groupedSignals = useMemo(() => {
    const groups = new Map<string, typeof filteredSignals>();
    filteredSignals.forEach((signal) => {
      const corpId = signal.corporationId;
      if (!groups.has(corpId)) {
        groups.set(corpId, []);
      }
      groups.get(corpId)!.push(signal);
    });
    // Map을 배열로 변환하고 시그널 수 기준 정렬
    return Array.from(groups.entries())
      .map(([corpId, sigs]) => ({
        corporationId: corpId,
        corporationName: sigs[0].corporationName,
        signals: sigs,
      }))
      .sort((a, b) => b.signals.length - a.signals.length);
  }, [filteredSignals]);

  const counts = useMemo(() => ({
    all: stats?.total || signals.length,
    new: stats?.new || signals.filter(s => s.status === "new").length,
    review: stats?.review || signals.filter(s => s.status === "review").length,
    resolved: stats?.resolved || signals.filter(s => s.status === "resolved").length,
    todayNew: stats?.new || signals.filter(s => s.status === "new").length,
    riskHigh7d: stats?.risk || signals.filter(s => s.impact === "risk").length,
    opportunity7d: stats?.opportunity || signals.filter(s => s.impact === "opportunity").length,
    loanEligible: 0,
  }), [signals, stats]);

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
        <DynamicBackground />
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
        <DynamicBackground />
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

        {/* Demo Mode Banner */}
        {import.meta.env.VITE_DEMO_MODE === 'true' && (
          <div className="mb-6 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <Beaker className="w-5 h-5 text-purple-500" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Demo Mode 활성화</p>
                  <p className="text-sm text-muted-foreground">AI 분석을 실행하려면 설정 페이지로 이동하세요</p>
                </div>
              </div>
              <Link
                to="/settings"
                className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
              >
                <Settings className="w-4 h-4" />
                분석 실행하기
              </Link>
            </div>
          </div>
        )}

        {/* KPI Cards - Kept as "Satellites" */}
        <div className="grid grid-cols-4 gap-4 mb-10">
          <KPICard icon={AlertCircle} label="금일 신규 시그널" value={counts.todayNew} trend="오늘" colorClass="text-indigo-500" trendData={[2, 4, 3, 5, 4, 6, counts.todayNew]} sparklineColor="#6366f1" />
          <KPICard icon={TrendingDown} label="위험 시그널 (7일)" value={counts.riskHigh7d} trend="최근 7일" colorClass="text-rose-500" trendData={[5, 6, 8, 7, 9, 8, counts.riskHigh7d]} sparklineColor="#f43f5e" />
          <KPICard icon={TrendingUp} label="기회 시그널 (7일)" value={counts.opportunity7d} trend="최근 7일" colorClass="text-emerald-500" trendData={[2, 3, 2, 4, 3, 5, counts.opportunity7d]} sparklineColor="#10b981" />
          <KPICard icon={Lightbulb} label="여신 거래 법인" value={counts.loanEligible} trend="참고용" colorClass="text-amber-500" />
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

        {/* 2. Grouped Signal Cards by Corporation */}
        <div className="space-y-4">
          {groupedSignals.map((group) => (
            <GroupedSignalCard
              key={group.corporationId}
              corporationId={group.corporationId}
              corporationName={group.corporationName}
              signals={group.signals}
              loanInsight={insightMap.get(group.corporationId)}
              onSignalClick={handleRowClick}
              onCorporationClick={(id) => navigate(`/corporates/${id}`)}
            />
          ))}
        </div>

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
