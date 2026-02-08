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
} from "lucide-react";
import {
  DynamicBackground,
  GlassCard,
  Sparkline,
  StatusBadge
} from "@/components/premium";
import { motion } from "framer-motion";
import { SignalStatus, SIGNAL_STATUS_CONFIG } from "@/types/signal";

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
      <div className="max-w-[1600px] mx-auto p-6 space-y-8">

        {/* Demo Mode Banner */}
        {import.meta.env.VITE_DEMO_MODE === 'true' && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4"
          >
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
          </motion.div>
        )}

        {/* KPI Cards - 상태별 통계 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <KPICard icon={AlertCircle} label="신규 시그널" value={counts.todayNew} trend="미검토" colorClass="text-indigo-500" trendData={[2, 4, 3, 5, 4, 6, counts.todayNew]} sparklineColor="#6366f1" />
          <KPICard icon={CheckCircle} label="검토 완료" value={counts.reviewed} trend="처리됨" colorClass="text-emerald-500" trendData={[1, 2, 2, 3, 3, 4, counts.reviewed]} sparklineColor="#10b981" />
          <KPICard icon={TrendingDown} label="위험 시그널" value={counts.riskHigh7d} trend="주의 필요" colorClass="text-rose-500" trendData={[5, 6, 8, 7, 9, 8, counts.riskHigh7d]} sparklineColor="#f43f5e" />
          <KPICard icon={TrendingUp} label="기회 시그널" value={counts.opportunity7d} trend="긍정적" colorClass="text-emerald-500" trendData={[2, 3, 2, 4, 3, 5, counts.opportunity7d]} sparklineColor="#10b981" />
        </motion.div>

        {/* 상태 필터 탭 + 정렬 옵션 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        >
          {/* 상태 필터 탭 */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
            <button
              onClick={() => setStatusFilter("active")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                statusFilter === "active"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              활성
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded-full">
                {signals.filter(s => s.status !== "dismissed").length}
              </span>
            </button>
            <button
              onClick={() => setStatusFilter("new")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                statusFilter === "new"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              신규
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded-full">
                {counts.todayNew}
              </span>
            </button>
            <button
              onClick={() => setStatusFilter("reviewed")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                statusFilter === "reviewed"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <CheckCircle className="w-3.5 h-3.5" />
              검토 완료
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full">
                {counts.reviewed}
              </span>
            </button>
            <button
              onClick={() => setStatusFilter("dismissed")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                statusFilter === "dismissed"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <EyeOff className="w-3.5 h-3.5" />
              기각
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 text-slate-600 rounded-full">
                {counts.dismissed}
              </span>
            </button>
            <button
              onClick={() => setStatusFilter("all")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                statusFilter === "all"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              전체
            </button>
          </div>

          {/* 정렬 옵션 */}
          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:ring-2 focus:ring-primary/20 outline-none">
            <option value="recent">최신순</option>
            <option value="impact">영향도순</option>
            <option value="corporation">기업명순</option>
          </select>
        </motion.div>

        {/* 2. Grouped Signal Cards by Corporation */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          {groupedSignals.map((group, index) => (
            <motion.div
              key={group.corporationId}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + (index * 0.05) }}
              className={group.isLastAnalyzed ? "ring-2 ring-amber-400 ring-offset-2 rounded-xl" : ""}
            >
              {group.isLastAnalyzed && (
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 border border-amber-200">
                    <Lightbulb className="w-3 h-3" />
                    방금 분석 완료
                  </span>
                </div>
              )}
              <GroupedSignalCard
                corporationId={group.corporationId}
                corporationName={group.corporationName}
                signals={group.signals}
                loanInsight={insightMap.get(group.corporationId)}
                onSignalClick={handleRowClick}
                onCorporationClick={(id) => navigate(`/corporations/${id}`, { state: { corpName: group.corporationName } })}
              />
            </motion.div>
          ))}
        </motion.div>

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
