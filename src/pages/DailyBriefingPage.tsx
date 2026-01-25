import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  Lightbulb,
} from "lucide-react";
import { Signal } from "@/types/signal";
import { useSignals, useDashboardSummary } from "@/hooks/useApi";
import { useMemo } from "react";
import { cn } from "@/lib/utils";

function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  const weekday = weekdays[today.getDay()];
  return `${year}년 ${month}월 ${day}일 (${weekday})`;
}

function getRelativeTime(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

// Executive Summary Stat Card
function StatCard({
  icon: Icon,
  label,
  value,
  delta,
  variant = "default",
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  delta?: number;
  variant?: "default" | "danger" | "warning" | "success";
}) {
  const variantStyles = {
    default: "bg-card border-border",
    danger: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-900",
    warning: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-900",
    success: "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-900",
  };

  const iconStyles = {
    default: "text-muted-foreground",
    danger: "text-red-600 dark:text-red-400",
    warning: "text-amber-600 dark:text-amber-400",
    success: "text-green-600 dark:text-green-400",
  };

  return (
    <div className={cn("p-4 rounded-xl border", variantStyles[variant])}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={cn("w-4 h-4", iconStyles[variant])} />
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-bold text-foreground">{value}</span>
        {delta !== undefined && (
          <div className="flex items-center gap-0.5 text-xs">
            {delta > 0 ? (
              <>
                <ArrowUpRight className="w-3 h-3 text-red-500" />
                <span className="text-red-500">+{delta}</span>
              </>
            ) : delta < 0 ? (
              <>
                <ArrowDownRight className="w-3 h-3 text-green-500" />
                <span className="text-green-500">{delta}</span>
              </>
            ) : (
              <>
                <Minus className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">0</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Urgent Action Card (긴급 조치 필요)
function UrgentSignalCard({
  signal,
  onClick,
}: {
  signal: Signal;
  onClick: () => void;
}) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-all border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-950/20"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">{signal.corporationName}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="text-[10px] font-bold">
              HIGH
            </Badge>
            <Badge variant="outline" className="text-[10px] text-red-600 border-red-300 dark:text-red-400">
              RISK
            </Badge>
          </div>
        </div>

        <h3 className="font-semibold text-foreground mb-2 line-clamp-1">{signal.title}</h3>
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{signal.summary}</p>

        {/* Actionable Hint */}
        <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-950/30 rounded-lg mb-3">
          <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-800 dark:text-amber-300">
            권장: 해당 기업 담당자에게 상황 확인 및 리스크 평가 검토
          </p>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {getRelativeTime(signal.detectedAt)}
            </span>
            <span className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {signal.evidenceCount}건 근거
            </span>
          </div>
          <Button size="sm" variant="outline" className="h-7 text-xs">
            상세 보기
            <ChevronRight className="w-3 h-3 ml-1" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Standard Signal Card with left color bar
function SignalCard({
  signal,
  onClick,
  variant = "risk",
}: {
  signal: Signal;
  onClick: () => void;
  variant?: "risk" | "opportunity" | "neutral";
}) {
  const borderColors = {
    risk: "border-l-red-500",
    opportunity: "border-l-green-500",
    neutral: "border-l-slate-400",
  };

  const badgeVariants = {
    risk: { variant: "destructive" as const, label: "RISK" },
    opportunity: { variant: "default" as const, label: "OPP", className: "bg-green-600" },
    neutral: { variant: "secondary" as const, label: "REF" },
  };

  const categoryIcons = {
    direct: Building2,
    industry: Globe,
    environment: TrendingUp,
  };

  const CategoryIcon = categoryIcons[signal.signalCategory] || FileText;

  return (
    <div
      className={cn(
        "flex items-start gap-4 p-4 border rounded-lg bg-card hover:bg-muted/50 transition-colors cursor-pointer border-l-4",
        borderColors[variant]
      )}
      onClick={onClick}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{signal.corporationName}</span>
            <Badge
              variant={badgeVariants[variant].variant}
              className={cn("text-[10px]", badgeVariants[variant].className)}
            >
              {badgeVariants[variant].label}
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">{getRelativeTime(signal.detectedAt)}</span>
        </div>

        <h4 className="font-medium text-foreground mb-1 line-clamp-1">{signal.title}</h4>
        <p className="text-sm text-muted-foreground line-clamp-2">{signal.summary}</p>

        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <CategoryIcon className="w-3 h-3" />
            {signal.signalCategory === "direct"
              ? "직접"
              : signal.signalCategory === "industry"
              ? "산업"
              : "환경"}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            {signal.evidenceCount}건
          </span>
        </div>
      </div>

      <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
    </div>
  );
}

// Section Header
function SectionHeader({
  icon: Icon,
  title,
  count,
  iconColor,
  onViewAll,
}: {
  icon: React.ElementType;
  title: string;
  count: number;
  iconColor: string;
  onViewAll?: () => void;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon className={cn("w-5 h-5", iconColor)} />
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <Badge variant="secondary" className="text-xs">
          {count}
        </Badge>
      </div>
      {onViewAll && (
        <Button variant="ghost" size="sm" onClick={onViewAll} className="text-xs">
          모두 보기
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
    reviewedTodayCount,
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

    // 업종/환경 동향 (neutral 또는 industry/environment 타입)
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

    // 오늘 검토 완료
    const today = new Date().toDateString();
    const reviewedToday = signals.filter((s) => {
      if (s.status !== "review" && s.status !== "resolved") return false;
      // detectedAt 기준으로 오늘 검토된 것으로 간주 (실제로는 reviewed_at 필요)
      return true;
    }).length;

    return {
      urgentSignals: urgent.slice(0, 3),
      riskSignals: risk,
      opportunitySignals: opportunity,
      industryEnvironmentSignals: industryEnv,
      reviewedTodayCount: reviewedToday,
    };
  }, [signals]);

  const handleSignalClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
  };

  const isLoading = signalsLoading || summaryLoading;

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-4xl space-y-8">
        {/* Header */}
        <div className="mb-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">일일 브리핑</h1>
              <p className="text-sm text-muted-foreground">{getTodayDate()}</p>
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <section>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              icon={Zap}
              label="긴급 조치"
              value={urgentSignals.length}
              delta={urgentSignals.length > 0 ? urgentSignals.length : undefined}
              variant="danger"
            />
            <StatCard
              icon={AlertTriangle}
              label="신규 시그널"
              value={summary?.new_signals || 0}
              variant="warning"
            />
            <StatCard
              icon={TrendingDown}
              label="위험 시그널"
              value={summary?.risk_signals || 0}
              variant="default"
            />
            <StatCard
              icon={TrendingUp}
              label="기회 시그널"
              value={summary?.opportunity_signals || 0}
              variant="success"
            />
          </div>
        </section>

        {/* Urgent Actions */}
        {urgentSignals.length > 0 && (
          <section>
            <SectionHeader
              icon={Zap}
              title="긴급 조치 필요"
              count={urgentSignals.length}
              iconColor="text-red-500"
              onViewAll={() => navigate("/signals/direct")}
            />
            <div className="space-y-3">
              {urgentSignals.map((signal) => (
                <UrgentSignalCard
                  key={signal.id}
                  signal={signal}
                  onClick={() => handleSignalClick(signal.id)}
                />
              ))}
            </div>
          </section>
        )}

        {/* Risk Signals */}
        {riskSignals.length > 0 && (
          <section>
            <SectionHeader
              icon={AlertTriangle}
              title="주요 위험 시그널"
              count={riskSignals.length}
              iconColor="text-amber-500"
              onViewAll={() => navigate("/signals/direct")}
            />
            <div className="space-y-2">
              {riskSignals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onClick={() => handleSignalClick(signal.id)}
                  variant="risk"
                />
              ))}
            </div>
          </section>
        )}

        {/* Opportunity Signals */}
        {opportunitySignals.length > 0 && (
          <section>
            <SectionHeader
              icon={TrendingUp}
              title="성장 기회"
              count={opportunitySignals.length}
              iconColor="text-green-500"
            />
            <div className="space-y-2">
              {opportunitySignals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onClick={() => handleSignalClick(signal.id)}
                  variant="opportunity"
                />
              ))}
            </div>
          </section>
        )}

        {/* Industry & Environment Trends */}
        {industryEnvironmentSignals.length > 0 && (
          <section>
            <SectionHeader
              icon={Globe}
              title="업종/환경 동향"
              count={industryEnvironmentSignals.length}
              iconColor="text-slate-500"
              onViewAll={() => navigate("/signals/industry")}
            />
            <div className="space-y-2">
              {industryEnvironmentSignals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onClick={() => handleSignalClick(signal.id)}
                  variant="neutral"
                />
              ))}
            </div>
          </section>
        )}

        {/* Empty State */}
        {signals.length === 0 && (
          <div className="text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              모든 시그널을 검토했습니다
            </h3>
            <p className="text-muted-foreground">
              새로운 시그널이 감지되면 알려드리겠습니다.
            </p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
