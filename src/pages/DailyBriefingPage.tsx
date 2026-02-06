import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Calendar,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Loader2,
  ChevronRight,
  Clock,
  FileText,
  Zap,
  Globe,
  Building2,
  CheckCircle2,
  Sparkles,
  BarChart3,
  Factory,
} from "lucide-react";
import { Signal, SIGNAL_TYPE_CONFIG } from "@/types/signal";
import { useSignals, useDashboardSummary } from "@/hooks/useApi";
import { useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  DynamicBackground,
  GlassCard,
  Sparkline,
  StatusBadge,
  Tag,
} from "@/components/premium";
import { motion } from "framer-motion";

function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();
  const weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const weekday = weekdays[today.getDay()];
  return `${weekday}, ${month} / ${day}, ${year}`;
}

function getRelativeTime(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Executive Summary Stat Card
function StatCard({
  icon: Icon,
  label,
  value,
  delta,
  variant = "default",
  trendData,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  delta?: number;
  variant?: "brand" | "danger" | "warning" | "success" | "default";
  trendData?: number[];
}) {
  const colors = {
    brand: "text-indigo-500",
    danger: "text-rose-500",
    warning: "text-amber-500",
    success: "text-emerald-500",
    default: "text-slate-500",
  };

  const sparklineColors = {
    brand: "#6366f1",
    danger: "#f43f5e",
    warning: "#f59e0b",
    success: "#10b981",
    default: "#94a3b8",
  };

  return (
    <GlassCard className="p-5 flex flex-col justify-between h-full relative overflow-hidden group">
      <div className="flex justify-between items-start mb-2">
        <div className={cn("p-2 rounded-lg bg-slate-50 group-hover:bg-white transition-colors", colors[variant])}>
          <Icon className="w-5 h-5" />
        </div>
        {delta !== undefined && (
          <div className={cn("flex items-center gap-0.5 text-xs font-bold px-2 py-1 rounded-full bg-slate-50",
            delta > 0 ? "text-rose-500" : delta < 0 ? "text-emerald-500" : "text-slate-400" // Accounting for Risk logic: +Risk is bad
          )}>
            {delta > 0 ? <ArrowUpRight className="w-3 h-3" /> : delta < 0 ? <ArrowDownRight className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            <span>{Math.abs(delta)}</span>
          </div>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
        <div className="flex items-end justify-between">
          <h3 className="text-3xl font-bold text-slate-800 tracking-tight">{value}</h3>
          {trendData && (
            <div className="w-16 h-8 opacity-50 group-hover:opacity-100 transition-opacity pb-1">
              <Sparkline data={trendData} color={sparklineColors[variant]} height={30} />
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// Urgent Action Card (긴급 조치 필요) - Enhanced
function UrgentSignalCard({
  signal,
  onClick,
}: {
  signal: Signal;
  onClick: () => void;
}) {
  return (
    <GlassCard
      className="cursor-pointer hover:shadow-lg transition-all border-l-4 border-l-rose-500 bg-gradient-to-r from-rose-50/50 to-white/60 group"
      onClick={onClick}
    >
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <StatusBadge variant="danger" className="animate-pulse">URGENT ACTION</StatusBadge>
            <span className="text-xs text-slate-400 font-mono">
              {getRelativeTime(signal.detectedAt)}
            </span>
          </div>
          <div className="p-1.5 rounded-full bg-white text-rose-500 shadow-sm opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1">
            <ChevronRight className="w-4 h-4" />
          </div>
        </div>

        <div className="flex items-center gap-2 mb-2">
          <Building2 className="w-4 h-4 text-slate-400" />
          <h3 className="font-bold text-slate-800">{signal.corporationName}</h3>
        </div>

        <h4 className="text-lg font-bold text-slate-900 mb-2 leading-tight group-hover:text-rose-600 transition-colors">
          {signal.title}
        </h4>
        <p className="text-sm text-slate-600 mb-4 line-clamp-2 leading-relaxed">
          {signal.summary}
        </p>

        {/* AI Recommendation Box */}
        <div className="flex gap-3 p-3 bg-white/60 rounded-xl border border-rose-100 backdrop-blur-sm">
          <Sparkles className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-rose-700 uppercase mb-0.5">AI Recommendation</p>
            <p className="text-xs text-slate-600 leading-snug">
              Immediate review required. Contact relationship manager and assess exposure.
            </p>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

// Standard Signal Card
function SignalCard({
  signal,
  onClick,
  variant = "risk",
}: {
  signal: Signal;
  onClick: () => void;
  variant?: "risk" | "opportunity" | "neutral";
}) {
  const accentColors = {
    risk: "border-l-rose-500",
    opportunity: "border-l-emerald-500",
    neutral: "border-l-slate-300",
  };

  const typeConfig = SIGNAL_TYPE_CONFIG?.[signal.signalCategory];

  return (
    <GlassCard
      className={cn(
        "cursor-pointer hover:bg-white/80 transition-all border-l-4 group flex flex-col md:flex-row gap-4 p-4 items-start md:items-center",
        accentColors[variant]
      )}
      onClick={onClick}
    >
      <div className="flex-1 w-full">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-500 flex items-center gap-1">
              <Building2 className="w-3 h-3" /> {signal.corporationName}
            </span>
            <Tag className="text-[9px] py-0 px-1.5 h-4 bg-slate-100/50 border-slate-200 text-slate-500">
              {typeConfig?.label || "General"}
            </Tag>
          </div>
          <span className="text-[10px] text-slate-400 font-medium">
            {getRelativeTime(signal.detectedAt)}
          </span>
        </div>

        <h4 className="font-bold text-slate-800 mb-1 group-hover:text-indigo-700 transition-colors">
          {signal.title}
        </h4>
        <p className="text-sm text-slate-500 line-clamp-1">
          {signal.summary}
        </p>
      </div>

      {/* Right Action / Meta Area */}
      <div className="flex items-center justify-between w-full md:w-auto md:ml-4 pl-0 md:pl-4 md:border-l border-slate-100 gap-4">
        <div className="flex items-center gap-1 text-slate-400 text-xs font-medium min-w-[60px]">
          <FileText className="w-3.5 h-3.5" />
          <span>{signal.evidenceCount} Evd.</span>
        </div>
        <div className="p-1.5 rounded-full bg-slate-50 text-slate-300 group-hover:text-indigo-500 group-hover:bg-indigo-50 transition-all">
          <ChevronRight className="w-4 h-4" />
        </div>
      </div>
    </GlassCard>
  );
}

// Section Header with Modern Typography
function SectionHeader({
  icon: Icon,
  title,
  count,
  iconColor,
  onViewAll,
  subtitle,
}: {
  icon: React.ElementType;
  title: string;
  count: number;
  iconColor?: string;
  onViewAll?: () => void;
  subtitle?: string;
}) {
  return (
    <div className="flex items-end justify-between mb-5 mt-8 pb-2 border-b border-slate-200/50">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Icon className={cn("w-5 h-5", iconColor || "text-slate-400")} />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{subtitle || "Section"}</span>
        </div>
        <div className="flex items-baseline gap-3">
          <h2 className="text-xl font-bold text-slate-800">{title}</h2>
          <StatusBadge variant="neutral" className="px-2 py-0.5 text-xs text-slate-500 bg-slate-100 border-slate-200">
            {count}
          </StatusBadge>
        </div>
      </div>
      {onViewAll && (
        <Button variant="ghost" size="sm" onClick={onViewAll} className="text-xs font-medium text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50">
          View All
          <ChevronRight className="w-3 h-3 ml-1" />
        </Button>
      )}
    </div>
  );
}

export default function DailyBriefingPage() {
  const navigate = useNavigate();
  const { data: signals = [], isLoading: signalsLoading } = useSignals({ limit: 100 });
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();

  const {
    urgentSignals,
    riskSignals,
    opportunitySignals,
    industryEnvironmentSignals,
  } = useMemo(() => {
    // 긴급 조치: HIGH + RISK
    const urgent = signals.filter(
      (s) => s.impact === "risk" && s.impactStrength === "high" && s.status === "new"
    );

    // 주요 위험: RISK (긴급 제외)
    const urgentIds = new Set(urgent.map((s) => s.id));
    const risk = signals
      .filter((s) => s.impact === "risk" && !urgentIds.has(s.id))
      .slice(0, 5);

    // 기회
    const opportunity = signals.filter((s) => s.impact === "opportunity").slice(0, 4);

    // 업종/환경 동향
    const shownIds = new Set([
      ...urgent.map((s) => s.id),
      ...risk.map((s) => s.id),
      ...opportunity.map((s) => s.id),
    ]);
    const industryEnv = signals
      .filter(
        (s) =>
          !shownIds.has(s.id) &&
          (s.signalCategory === "industry" || s.signalCategory === "environment")
      )
      .slice(0, 4);

    return {
      urgentSignals: urgent.slice(0, 3),
      riskSignals: risk,
      opportunitySignals: opportunity,
      industryEnvironmentSignals: industryEnv,
    };
  }, [signals]);

  const handleSignalClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
  };

  const isLoading = signalsLoading || summaryLoading;

  if (isLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-100px)] gap-4">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
          <p className="text-slate-500 font-medium animate-pulse">Generating Daily Intelligence...</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-6xl mx-auto space-y-8 relative z-10 pb-20">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8"
        >
          <div>
            <div className="flex items-center gap-2 text-indigo-600 font-medium mb-1">
              <Sparkles className="w-4 h-4" />
              <span className="text-xs uppercase tracking-widest">Intelligence Briefing</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 tracking-tight">Daily Briefing</h1>
            <p className="text-slate-500 mt-1 font-mono text-sm">{getTodayDate()}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="bg-white/50 backdrop-blur-sm border-slate-200">
              <Calendar className="w-4 h-4 mr-2 text-slate-500" />
              History
            </Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700 shadow-lg shadow-indigo-500/25">
              <FileText className="w-4 h-4 mr-2" />
              Export Report
            </Button>
          </div>
        </motion.div>

        {/* KPI Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <StatCard
            icon={Zap}
            label="Urgent Action"
            value={urgentSignals.length}
            delta={urgentSignals.length > 0 ? urgentSignals.length : undefined}
            variant="danger"
            trendData={[0, 1, 0, 2, 1, 1, urgentSignals.length]} // Mock
          />
          <StatCard
            icon={AlertTriangle}
            label="New Risks"
            value={summary?.new_signals || 0}
            variant="warning"
            trendData={[5, 8, 5, 12, 8, 10, summary?.new_signals || 0]} // Mock
          />
          <StatCard
            icon={TrendingDown}
            label="Total Risks"
            value={summary?.risk_signals || 0}
            variant="default"
            trendData={[20, 22, 18, 25, 23, 24, summary?.risk_signals || 0]} // Mock
          />
          <StatCard
            icon={TrendingUp}
            label="Opportunities"
            value={summary?.opportunity_signals || 0}
            variant="success"
            trendData={[2, 3, 2, 5, 3, 6, summary?.opportunity_signals || 0]} // Mock
          />
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Content Column (Main) */}
          <div className="lg:col-span-8 space-y-8">
            {/* Urgent Actions */}
            {urgentSignals.length > 0 && (
              <motion.section
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="space-y-4"
              >
                <SectionHeader
                  icon={Zap}
                  subtitle="PRIORITY"
                  title="Required Actions"
                  count={urgentSignals.length}
                  iconColor="text-rose-500"
                  onViewAll={() => navigate("/signals/direct")}
                />
                <div className="grid grid-cols-1 gap-4">
                  {urgentSignals.map((signal) => (
                    <UrgentSignalCard
                      key={signal.id}
                      signal={signal}
                      onClick={() => handleSignalClick(signal.id)}
                    />
                  ))}
                </div>
              </motion.section>
            )}

            {/* Risk Signals */}
            {riskSignals.length > 0 && (
              <motion.section
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="space-y-3"
              >
                <SectionHeader
                  icon={AlertTriangle}
                  subtitle="RISK MONITORING"
                  title="Key Risk Signals"
                  count={riskSignals.length}
                  iconColor="text-amber-500"
                  onViewAll={() => navigate("/signals/direct")}
                />
                {riskSignals.map((signal) => (
                  <SignalCard
                    key={signal.id}
                    signal={signal}
                    onClick={() => handleSignalClick(signal.id)}
                    variant="risk"
                  />
                ))}
              </motion.section>
            )}
          </div>

          {/* Right Side Column */}
          <div className="lg:col-span-4 space-y-8">
            {/* Opportunity Signals */}
            {opportunitySignals.length > 0 && (
              <motion.section
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
                className="space-y-3"
              >
                <SectionHeader
                  icon={TrendingUp}
                  subtitle="GROWTH"
                  title="Opportunities"
                  count={opportunitySignals.length}
                  iconColor="text-emerald-500"
                />
                {opportunitySignals.map((signal) => (
                  <SignalCard
                    key={signal.id}
                    signal={signal}
                    onClick={() => handleSignalClick(signal.id)}
                    variant="opportunity"
                  />
                ))}
              </motion.section>
            )}

            {/* Industry & Environment Trends */}
            {industryEnvironmentSignals.length > 0 && (
              <motion.section
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="space-y-3"
              >
                <SectionHeader
                  icon={Globe}
                  subtitle="MACRO"
                  title="Industry Trends"
                  count={industryEnvironmentSignals.length}
                  iconColor="text-indigo-400"
                  onViewAll={() => navigate("/signals/industry")}
                />
                {industryEnvironmentSignals.map((signal) => (
                  <SignalCard
                    key={signal.id}
                    signal={signal}
                    onClick={() => handleSignalClick(signal.id)}
                    variant="neutral"
                  />
                ))}
              </motion.section>
            )}
          </div>
        </div>

        {/* Empty State */}
        {signals.length === 0 && (
          <div className="text-center py-20">
            <GlassCard className="inline-flex flex-col items-center p-10 max-w-md">
              <CheckCircle2 className="w-16 h-16 text-emerald-500 mb-6" />
              <h3 className="text-xl font-bold text-slate-800 mb-2">
                All Clear for Today
              </h3>
              <p className="text-slate-500 leading-relaxed">
                No active signals detected. We will notify you immediately if any significant changes occur.
              </p>
            </GlassCard>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
