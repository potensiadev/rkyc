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
      title: "금일 시그널",
      value: kpiData.today,
      icon: Radio,
      trendData: MOCK_TRENDS.today,
      color: "brand",
      trendLabel: "전일 대비 +12%"
    },
    {
      id: "pending-review",
      title: "검토 대기",
      value: kpiData.pending,
      icon: Clock,
      trendData: MOCK_TRENDS.pending,
      color: "warning",
      trendLabel: "확인 필요"
    },
    {
      id: "in-review",
      title: "검토중",
      value: kpiData.inReview,
      icon: Activity,
      trendData: MOCK_TRENDS.review,
      color: "info",
      trendLabel: "분석 진행중"
    },
    {
      id: "completed",
      title: "완료",
      value: kpiData.completed,
      icon: CheckCircle2,
      trendData: MOCK_TRENDS.completed,
      color: "success",
      trendLabel: "완료율 상승"
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
      label: "직접",
      count: typeCounts.direct,
      icon: Building2,
      color: "indigo",
      desc: "기업 특정 이벤트"
    },
    {
      id: "industry",
      label: "산업",
      count: typeCounts.industry,
      icon: Factory,
      color: "cyan",
      desc: "섹터 전반 동향"
    },
    {
      id: "environment",
      label: "환경",
      count: typeCounts.environment,
      icon: Globe,
      color: "emerald",
      desc: "거시경제 및 규제"
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
          <p className="text-slate-500 font-medium animate-pulse">분석 데이터 계산 중...</p>
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
            <h1 className="text-4xl font-bold text-slate-900 tracking-tight">분석 대시보드</h1>
            <p className="text-slate-500 mt-1 max-w-2xl word-keep-all">
              시그널 처리, 리스크 분포, 시스템 성능에 대한 실시간 개요를 확인합니다.
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
              개요 (Overview)
            </button>
            <button
              onClick={() => setActiveTab('trends')}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === 'trends' ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-800"
              )}
            >
              트렌드 (Trends)
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
            className="lg:col-span-2 space-y-6"
          >
            {/* Signal Category Distribution */}
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">시그널 유형 분포</h3>
                  <p className="text-sm text-slate-500">카테고리별 탐지된 시그널 현황</p>
                </div>
                <BarChart3 className="w-5 h-5 text-indigo-500" />
              </div>

              <div className="space-y-4">
                {signalTypeData.map((type) => {
                  const percentage = Math.round((type.count / totalSignals) * 100);
                  const Icon = type.icon;
                  return (
                    <div key={type.id} className="group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg bg-${type.color}-50 text-${type.color}-600`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-700">{type.label}</p>
                            <p className="text-xs text-slate-400">{type.desc}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-slate-800">{type.count}</p>
                          <p className="text-xs text-slate-400">{percentage}%</p>
                        </div>
                      </div>
                      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${percentage}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          className={`h-full bg-${type.color}-500 rounded-full`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>

            {/* Impact Analysis */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <GlassCard className="p-5 border-l-4 border-l-rose-500 bg-gradient-to-br from-rose-50/50 to-transparent">
                <div className="flex justify-between items-start mb-4">
                  <div className="bg-rose-100 p-2 rounded-full">
                    <AlertCircle className="w-5 h-5 text-rose-600" />
                  </div>
                  <StatusBadge variant="danger" className="bg-white">Risk Focus</StatusBadge>
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-1">{impactCounts.risk}</h3>
                <p className="text-sm text-slate-500 font-medium">부정적 영향 (Risk)</p>
                <div className="mt-3 text-xs text-rose-600 font-semibold bg-rose-50 inline-block px-2 py-1 rounded">
                  즉각적인 조치 필요
                </div>
              </GlassCard>

              <GlassCard className="p-5 border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50/50 to-transparent">
                <div className="flex justify-between items-start mb-4">
                  <div className="bg-emerald-100 p-2 rounded-full">
                    <Zap className="w-5 h-5 text-emerald-600" />
                  </div>
                  <StatusBadge variant="success" className="bg-white">Opportunity</StatusBadge>
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-1">{impactCounts.opportunity}</h3>
                <p className="text-sm text-slate-500 font-medium">긍정적 기회 (Opportunity)</p>
                <div className="mt-3 text-xs text-emerald-600 font-semibold bg-emerald-50 inline-block px-2 py-1 rounded">
                  영업 기회 포착
                </div>
              </GlassCard>
            </div>

          </motion.div>

          {/* Right Column: Recent Activity Log */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="lg:col-span-1"
          >
            <GlassCard className="h-full flex flex-col">
              <div className="p-6 border-b border-slate-100">
                <h3 className="text-lg font-bold text-slate-800">실시간 로그</h3>
                <p className="text-sm text-slate-500">최근 시스템 활동 내역</p>
              </div>
              <div className="flex-1 overflow-y-auto max-h-[500px] p-4 space-y-4 custom-scrollbar">
                {recentSignals.map((signal) => (
                  <div key={signal.id} onClick={() => navigate(`/signals/${signal.id}`)} className="group flex gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors border border-transparent hover:border-slate-100">
                    <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${signal.impact === 'risk' ? 'bg-rose-500' :
                        signal.impact === 'opportunity' ? 'bg-emerald-500' : 'bg-slate-400'
                      }`} />
                    <div>
                      <p className="text-xs font-bold text-slate-700 line-clamp-1 group-hover:text-indigo-600 mb-0.5">{signal.title}</p>
                      <p className="text-[10px] text-slate-400 mb-1.5">{signal.corporationName}</p>
                      <span className="text-[10px] text-slate-300 font-mono bg-slate-900 px-1.5 py-0.5 rounded">
                        {formatRelativeTime(signal.detectedAt)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t border-slate-100 text-center">
                <button className="text-xs font-bold text-indigo-500 hover:text-indigo-600 uppercase tracking-wider flex items-center justify-center gap-1 w-full py-2 hover:bg-indigo-50 rounded-lg transition-colors">
                  View All Logs <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </GlassCard>
          </motion.div>

        </div>

      </div>
    </MainLayout>
  );
}
