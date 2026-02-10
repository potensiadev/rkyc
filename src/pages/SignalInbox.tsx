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
  Settings,
  CheckCircle,
  XCircle,
  Filter,
  Eye,
  EyeOff,
  Activity,
  ArrowUpRight
} from "lucide-react";
import {
  DynamicBackground,
  StatusBadge
} from "@/components/premium";
import { motion, AnimatePresence } from "framer-motion";
import { SignalStatus } from "@/types/signal";
import { Tiny } from "@ant-design/charts";

import { GroupedSignalCard } from "@/components/dashboard/GroupedSignalCard";

// KPI Card Component using AntV Tiny.Area
interface KPICardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: string;
  trendLabel?: string;
  colorTheme: 'indigo' | 'emerald' | 'rose' | 'amber';
  data: number[];
}

function KPICard({ icon: Icon, label, value, trend, trendLabel, colorTheme, data }: KPICardProps) {
  const themeColors = {
    indigo: { text: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-100", stroke: "#6366f1", fill: "l(270) 0:#ffffff 0.5:#c7d2fe 1:#6366f1" },
    emerald: { text: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100", stroke: "#10b981", fill: "l(270) 0:#ffffff 0.5:#a7f3d0 1:#10b981" },
    rose: { text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100", stroke: "#e11d48", fill: "l(270) 0:#ffffff 0.5:#fecdd3 1:#e11d48" },
    amber: { text: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100", stroke: "#d97706", fill: "l(270) 0:#ffffff 0.5:#fde68a 1:#d97706" },
  };

  const colors = themeColors[colorTheme];

  const config = {
    height: 40,
    autoFit: true,
    data,
    smooth: true,
    areaStyle: {
      fill: colors.fill,
    },
    line: {
      color: colors.stroke,
    }
  };

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className={`group relative overflow-hidden rounded-2xl bg-white border border-slate-200/60 p-5 shadow-sm hover:shadow-lg hover:border-${colorTheme}-200/60 transition-all duration-300`}
    >
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className={`p-2 rounded-xl ${colors.bg} ${colors.text} ring-1 ring-inset ${colors.border}`}>
          <Icon className="w-5 h-5" />
        </div>
        {trend && (
          <span className="flex items-center gap-1 text-[10px] font-semibold bg-slate-100 px-2 py-1 rounded-full text-slate-600">
            {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trendLabel}
          </span>
        )}
      </div>

      <div className="relative z-10">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{label}</p>
        <div className="flex items-baseline gap-2">
          <h3 className="text-3xl font-bold text-slate-900 tracking-tight">{value}</h3>
        </div>
      </div>

      {/* Chart Container */}
      <div className="absolute bottom-0 left-0 right-0 h-16 opacity-60 group-hover:opacity-100 transition-opacity">
        <div className="w-full h-full px-0 safe-chart-container">
          <Tiny.Area {...config} />
        </div>
      </div>
    </motion.div>
  );
}

// 상태 필터 타입
type StatusFilter = "all" | "active" | SignalStatus;

export default function SignalInbox() {
  const navigate = useNavigate();

  // 상태 필터: 기본값 "active" (NEW + REVIEWED, DISMISSED 숨김)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");

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

  // 상태 필터 적용
  const filteredSignals = useMemo(() => {
    if (statusFilter === "all") return signals;
    if (statusFilter === "active") {
      // active = NEW + REVIEWED (DISMISSED 제외)
      return signals.filter(s => s.status !== "dismissed");
    }
    // 특정 상태만 필터
    return signals.filter(s => s.status === statusFilter);
  }, [signals, statusFilter]);

  // 최근 분석한 기업 ID (해커톤 시연용 우선 표시)
  const lastAnalyzedCorpId = sessionStorage.getItem('lastAnalyzedCorpId');

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
        // Calculate max impact order for sorting: Risk High > Risk > Opp > Neutral
        sortWeight: sigs.reduce((max, s) => {
          let w = 0;
          if (s.impact === 'risk') w = 10;
          if (s.impact === 'risk' && s.impactStrength === 'high') w = 20;
          if (s.impact === 'opportunity') w = 5;
          return Math.max(max, w);
        }, 0),
        // 최근 분석한 기업은 맨 위에 표시 (해커톤 시연용)
        isLastAnalyzed: corpId === lastAnalyzedCorpId
      }))
      .sort((a, b) => {
        // 최근 분석한 기업 우선
        if (a.isLastAnalyzed && !b.isLastAnalyzed) return -1;
        if (!a.isLastAnalyzed && b.isLastAnalyzed) return 1;
        // 그 다음 risk, 시그널 수로 정렬
        return b.sortWeight - a.sortWeight || b.signals.length - a.signals.length;
      });
  }, [filteredSignals, lastAnalyzedCorpId]);

  const counts = useMemo(() => ({
    todayNew: stats?.new || signals.filter(s => s.status === "new").length,
    reviewed: stats?.reviewed || signals.filter(s => s.status === "reviewed").length,
    dismissed: stats?.dismissed || signals.filter(s => s.status === "dismissed").length,
    riskHigh7d: stats?.risk || signals.filter(s => s.impact === "risk").length,
    opportunity7d: stats?.opportunity || signals.filter(s => s.impact === "opportunity").length,
  }), [signals, stats]);

  // Click row -> go to signal detail
  const handleRowClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
  };

  // Styles for Filter Tabs
  const getTabStyle = (key: StatusFilter) =>
    `flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${statusFilter === key
      ? "bg-slate-900 text-white shadow-lg shadow-slate-900/20 scale-105"
      : "bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900 border border-slate-200/60"
    }`;

  if (isLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="flex justify-center items-center h-[80vh]">
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
            <p className="text-slate-400 font-medium">Loading Intelligence...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-10 pb-24 relative z-10">

        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
              Signal Intelligence
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-xs font-bold border border-emerald-100 tracking-wide uppercase">
                System Active
              </span>
            </h1>
            <p className="text-slate-500 mt-2 text-lg">
              Real-time risk monitoring and opportunity detection.
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
            <div className="flex items-center gap-3 bg-white p-1 rounded-xl border border-slate-200 shadow-sm">
              <button
                onClick={() => setStatusFilter("active")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${statusFilter === 'active' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Active Only
              </button>
              <div className="w-px h-4 bg-slate-200" />
              <button
                onClick={() => setStatusFilter("all")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${statusFilter === 'all' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}
              >
                All History
              </button>
            </div>
          </motion.div>
        </div>

        {/* Demo Mode Banner */}
        {import.meta.env.VITE_DEMO_MODE === 'true' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-indigo-600 rounded-2xl p-4 text-white shadow-xl shadow-indigo-500/20 flex flex-col sm:flex-row items-center justify-between gap-4 overflow-hidden relative"
          >
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20" />
            <div className="flex items-center gap-3 relative z-10">
              <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                <Beaker className="w-5 h-5" />
              </div>
              <div className="font-medium">
                Demo Environment Active <span className="text-indigo-200 text-sm ml-2 font-normal">Simulated data stream</span>
              </div>
            </div>
            <Link to="/settings" className="relative z-10 flex items-center gap-2 px-4 py-2 bg-white text-indigo-700 rounded-lg font-bold text-sm hover:bg-indigo-50 transition-colors">
              <Settings className="w-4 h-4" /> Configure
            </Link>
          </motion.div>
        )}

        {/* KPI Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5"
        >
          <KPICard
            icon={Activity}
            label="New Signals"
            value={counts.todayNew}
            colorTheme="indigo"
            trend="up"
            trendLabel="+12%"
            data={[15, 22, 18, 28, 24, 32, 45, 38, 42, Math.max(counts.todayNew * 5, 20)]}
          />
          <KPICard
            icon={TrendingDown}
            label="Risk Alerts"
            value={counts.riskHigh7d}
            colorTheme="rose"
            trend="up"
            trendLabel="+5%"
            data={[8, 12, 10, 15, 14, 18, 12, 16, 20, Math.max(counts.riskHigh7d * 3, 15)]}
          />
          <KPICard
            icon={TrendingUp}
            label="Opportunities"
            value={counts.opportunity7d}
            colorTheme="emerald"
            trend="up"
            trendLabel="+8%"
            data={[5, 8, 12, 10, 15, 18, 22, 25, 28, Math.max(counts.opportunity7d * 4, 20)]}
          />
          <KPICard
            icon={CheckCircle}
            label="Reviewed"
            value={counts.reviewed}
            colorTheme="amber"
            trend="up"
            trendLabel="+24%"
            data={[20, 25, 28, 30, 32, 35, 38, 42, 45, Math.max(counts.reviewed * 2, 40)]}
          />
        </motion.div>

        {/* Filter Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="sticky top-4 z-30"
        >
          <div className="bg-white/80 backdrop-blur-xl border border-slate-200/60 p-1.5 rounded-2xl shadow-lg shadow-slate-200/50 flex flex-nowrap overflow-x-auto no-scrollbar gap-2">
            <button onClick={() => setStatusFilter("active")} className={getTabStyle("active")}>
              <Activity className="w-4 h-4" /> Active Pulse
            </button>
            <button onClick={() => setStatusFilter("new")} className={getTabStyle("new")}>
              <AlertCircle className="w-4 h-4" /> New
              <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded textxs">{counts.todayNew}</span>
            </button>
            <button onClick={() => setStatusFilter("reviewed")} className={getTabStyle("reviewed")}>
              <CheckCircle className="w-4 h-4" /> Reviewed
            </button>
            <button onClick={() => setStatusFilter("dismissed")} className={getTabStyle("dismissed")}>
              <EyeOff className="w-4 h-4" /> Dismissed
            </button>
          </div>
        </motion.div>

        {/* Signal List */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="space-y-6"
        >
          <AnimatePresence>
            {groupedSignals.map((group, index) => (
              <motion.div
                key={group.corporationId}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + (index * 0.05) }}
                className={group.isLastAnalyzed ? "relative" : ""}
              >
                {group.isLastAnalyzed && (
                  <div className="absolute -top-3 left-4 z-10">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-400 text-white shadow-lg shadow-amber-400/40">
                      <Lightbulb className="w-3 h-3 fill-white" />
                      Just Added
                    </span>
                  </div>
                )}
                <div className={group.isLastAnalyzed ? "ring-2 ring-amber-400/50 rounded-2xl shadow-[0_0_30px_rgba(251,191,36,0.2)]" : ""}>
                  <GroupedSignalCard
                    corporationId={group.corporationId}
                    corporationName={group.corporationName}
                    signals={group.signals}
                    loanInsight={insightMap.get(group.corporationId)}
                    onSignalClick={handleRowClick}
                    onCorporationClick={(id) => navigate(`/corporations/${id}`, { state: { corpName: group.corporationName } })}
                  />
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredSignals.length === 0 && (
            <div className="flex flex-col items-center justify-center py-32 text-center rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50/50">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <Filter className="w-8 h-8 text-slate-300" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">No Signals Found</h3>
              <p className="text-slate-500 mt-1 max-w-sm">
                No signals match your current status filter. Try clearing filters or checking back later.
              </p>
              <button onClick={() => setStatusFilter("all")} className="mt-6 text-indigo-600 font-semibold text-sm hover:underline">
                View All History
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </MainLayout>
  );
}
