import { useNavigate } from "react-router-dom";
import {
  Radio,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building2,
  Factory,
  Globe,
  ChevronRight,
  Loader2,
  Activity,
  BarChart3,
  PieChart,
  Zap
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { useSignals } from "@/hooks/useApi";
import { formatRelativeTime } from "@/data/signals";
import {
  DynamicBackground,
  GlassCard,
  Sparkline,
  StatusBadge,
  Tag
} from "@/components/premium";
import { motion } from "framer-motion";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// Mock Weekly Trend Data for Sparklines
const MOCK_TRENDS = {
  today: [12, 19, 15, 22, 28, 24, 32],
  pending: [5, 8, 12, 7, 9, 10, 15],
  review: [3, 5, 4, 6, 8, 7, 5],
  completed: [10, 15, 20, 18, 25, 30, 42]
};

export default function AnalyticsStatusPage() {
  const navigate = useNavigate();
  const { data: signals = [], isLoading } = useSignals();
  const [activeTab, setActiveTab] = useState<'overview' | 'trends'>('overview');

  // Dynamic KPI Calculation
  const kpiData = useMemo(() => {
    return {
      today: signals.filter(s => {
        const date = new Date(s.detectedAt);
        const today = new Date();
        return date.getDate() === today.getDate() &&
          date.getMonth() === today.getMonth() &&
          date.getFullYear() === today.getFullYear();
      }).length,
      pending: signals.filter(s => s.status === 'new').length,
      inReview: signals.filter(s => s.status === 'review').length,
      completed: signals.filter(s => s.status === 'resolved').length
    };
  }, [signals]);

  const kpiCards = [
    {
      id: "detected-today",
      title: "Signals Today",
      value: kpiData.today,
      icon: Radio,
      trendData: MOCK_TRENDS.today,
      color: "brand",
      trendLabel: "+12% vs yesterday"
    },
    {
      id: "pending-review",
      title: "Pending Review",
      value: kpiData.pending,
      icon: Clock,
      trendData: MOCK_TRENDS.pending,
      color: "warning",
      trendLabel: "Needs attention"
    },
    {
      id: "in-review",
      title: "In Progress",
      value: kpiData.inReview,
      icon: Activity,
      trendData: MOCK_TRENDS.review,
      color: "info",
      trendLabel: "Active analysis"
    },
    {
      id: "completed",
      title: "Resolved",
      value: kpiData.completed,
      icon: CheckCircle2,
      trendData: MOCK_TRENDS.completed,
      color: "success",
      trendLabel: "Completion rate up"
    },
  ];

  // Dynamic Signal Type Distribution
  const typeCounts = {
    direct: signals.filter(s => s.signalCategory === 'direct').length,
    industry: signals.filter(s => s.signalCategory === 'industry').length,
    environment: signals.filter(s => s.signalCategory === 'environment').length,
  };
  const totalSignals = signals.length || 1;

  const signalTypeData = [
    {
      id: "direct",
      label: "Direct",
      count: typeCounts.direct,
      icon: Building2,
      color: "indigo",
      desc: "Company-specific events"
    },
    {
      id: "industry",
      label: "Industry",
      count: typeCounts.industry,
      icon: Factory,
      color: "cyan",
      desc: "Sector-wide trends"
    },
    {
      id: "environment",
      label: "Macro",
      count: typeCounts.environment,
      icon: Globe,
      color: "emerald",
      desc: "Economic & regulatory"
    },
  ];

  // Dynamic Impact Assessment
  const impactCounts = {
    risk: signals.filter(s => s.impact === 'risk').length,
    opportunity: signals.filter(s => s.impact === 'opportunity').length,
    neutral: signals.filter(s => s.impact === 'neutral').length,
  };

  // Recent Signals (Sorted by date)
  const recentSignals = [...signals]
    .sort((a, b) => new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime())
    .slice(0, 10);

  // Helper for KPI colors
  const getKpiColor = (variant: string) => {
    switch (variant) {
      case 'brand': return { text: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-100', spark: '#4f46e5' };
      case 'warning': return { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100', spark: '#d97706' };
      case 'success': return { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100', spark: '#10b981' };
      case 'info': return { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100', spark: '#2563eb' };
      default: return { text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-100', spark: '#64748b' };
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-100px)]">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
          <p className="text-slate-500 font-medium animate-pulse">Calculating Analytics...</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-7xl mx-auto space-y-8 relative z-10 pb-20">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-8"
        >
          <div>
            <div className="flex items-center gap-2 text-indigo-600 font-medium mb-1">
              <Activity className="w-4 h-4" />
              <span className="text-xs uppercase tracking-widest">System Status</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 tracking-tight">Analytics Dashboard</h1>
            <p className="text-slate-500 mt-1 max-w-2xl">
              Real-time overview of signal processing, risk distribution, and system performance.
            </p>
          </div>

          <div className="bg-white/50 backdrop-blur-sm p-1 rounded-xl border border-slate-200/50 flex gap-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === 'overview' ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-800"
              )}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('trends')}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === 'trends' ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-800"
              )}
            >
              Trends
            </button>
          </div>
        </motion.div>

        {/* KPI Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5"
        >
          {kpiCards.map((card) => {
            const style = getKpiColor(card.color);
            const Icon = card.icon;
            return (
              <GlassCard key={card.id} className="p-5 flex flex-col justify-between h-36 group hover:scale-[1.02] transition-transform">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">{card.title}</p>
                    <h3 className="text-3xl font-bold text-slate-800 tracking-tight">{card.value}</h3>
                  </div>
                  <div className={cn("p-2.5 rounded-xl transition-colors", style.bg, style.text)}>
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-auto pt-2">
                  <div className="flex items-end justify-between">
                    <span className="text-[10px] font-medium text-slate-400">{card.trendLabel}</span>
                    <div className="w-20 h-8 opacity-50 group-hover:opacity-100 transition-opacity">
                      <Sparkline data={card.trendData} color={style.spark} height={32} />
                    </div>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Left Column: Charts & Stats */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-1 space-y-6"
          >
            {/* Visual Distribution */}
            <GlassCard className="p-6">
              <div className="flex items-center gap-2 mb-6">
                <PieChart className="w-5 h-5 text-indigo-500" />
                <h3 className="font-bold text-slate-800">Signal Composition</h3>
              </div>

              <div className="space-y-6">
                {signalTypeData.map((item) => {
                  const percentage = totalSignals > 0 ? Math.round((item.count / totalSignals) * 100) : 0;
                  const Icon = item.icon;
                  return (
                    <div key={item.id} className="group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg bg-${item.color}-50 text-${item.color}-600`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="font-bold text-slate-700 text-sm">{item.label}</p>
                            <p className="text-[10px] text-slate-400">{item.desc}</p>
                          </div>
                        </div>
                        <span className="font-mono font-bold text-slate-600">{percentage}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full bg-${item.color}-500 transition-all duration-1000 ease-out`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>

            {/* Impact Summary */}
            <GlassCard className="p-6 bg-gradient-to-b from-white/80 to-slate-50/50">
              <div className="flex items-center gap-2 mb-5">
                <Zap className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-slate-800">Impact Analysis</h3>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-100 flex flex-col items-center justify-center text-center">
                  <span className="text-2xl font-bold text-rose-600 mb-1">{impactCounts.risk}</span>
                  <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wide">Risk</span>
                </div>
                <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100 flex flex-col items-center justify-center text-center">
                  <span className="text-2xl font-bold text-emerald-600 mb-1">{impactCounts.opportunity}</span>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wide">Oppty</span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-100 border border-slate-200 flex flex-col items-center justify-center text-center">
                  <span className="text-2xl font-bold text-slate-600 mb-1">{impactCounts.neutral}</span>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Neutral</span>
                </div>
              </div>
            </GlassCard>
          </motion.div>

          {/* Right Column: Recent Feed */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="lg:col-span-2"
          >
            <GlassCard className="h-full min-h-[500px] flex flex-col overflow-hidden">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-white/50 backdrop-blur-sm sticky top-0 z-10">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-indigo-500" />
                  <h3 className="font-bold text-slate-800">Live Activity Feed</h3>
                </div>
                <StatusBadge variant="neutral" className="animate-pulse">Live Updating</StatusBadge>
              </div>

              <div className="flex-1 overflow-y-auto max-h-[600px] p-2 space-y-2">
                {recentSignals.map((signal) => {
                  // Determine style based on category/impact
                  const isDirect = signal.signalCategory === 'direct';
                  const isRisk = signal.impact === 'risk';

                  return (
                    <div
                      key={signal.id}
                      className="group p-4 rounded-xl hover:bg-white hover:shadow-md transition-all border border-transparent hover:border-slate-100 cursor-pointer flex items-center justify-between"
                      onClick={() => navigate(`/signals/${signal.id}`)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={cn(
                          "w-12 h-12 rounded-2xl flex items-center justify-center transition-colors",
                          isDirect ? "bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
                        )}>
                          {isDirect ? <Building2 className="w-6 h-6" /> : <Globe className="w-6 h-6" />}
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-700 group-hover:text-indigo-600 transition-colors text-sm mb-0.5 line-clamp-1">{signal.title}</h4>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-500">{signal.corporationName}</span>
                            <span className="text-[9px] text-slate-300">|</span>
                            <span className="text-xs text-slate-400">{formatRelativeTime(signal.detectedAt)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {isRisk ? (
                          <Tag className="bg-rose-50 text-rose-600 border-rose-100">RISK</Tag>
                        ) : (
                          <Tag className="bg-emerald-50 text-emerald-600 border-emerald-100">OPP</Tag>
                        )}
                        <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>
          </motion.div>
        </div>
      </div>
    </MainLayout>
  );
}
