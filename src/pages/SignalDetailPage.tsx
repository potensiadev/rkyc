import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Loader2,
  FileText,
  ExternalLink,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Building2,
  Calendar,
  Check,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Globe,
  ChevronRight,
  Brain,
  Link as LinkIcon,
  BarChart3,
  Percent,
  Info,
  Sparkles,
  AlertCircle,
  History,
  Landmark,
  Target,
  ClipboardList,
} from "lucide-react";
import {
  useSignalDetail,
  useSignalEnrichedDetail,
  useUpdateSignalStatus,
  useDismissSignal,
  useCorpProfile,
  useSignals,
  ApiEnrichedEvidence,
  ApiSimilarCase,
  ApiRelatedSignal,
  ApiCorpContext,
  ApiVerification,
  ApiImpactAnalysis,
} from "@/hooks/useApi";
import { toast } from "sonner";
import {
  DynamicBackground,
  GlassCard,
  StatusBadge,
  Tag,
  ContextualHighlight,
} from "@/components/premium";
import { motion } from "framer-motion";
import {
  getSignalTypeLabel,
  getImpactDirectionLabel,
  getStrengthLabel,
} from "@/types/signal";

// Signal Status Config
const STATUS_CONFIG: Record<string, { label: string; variant: "brand" | "neutral" | "danger" | "warning" | "success" }> = {
  NEW: { label: "신규", variant: "brand" },
  REVIEWED: { label: "검토 완료", variant: "success" },
  DISMISSED: { label: "기각", variant: "neutral" },
};

// 소스 신뢰도 아이콘
const CredibilityIcon = ({ credibility }: { credibility: string | null }) => {
  switch (credibility) {
    case "OFFICIAL":
      return <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />;
    case "MAJOR_MEDIA":
      return <Shield className="w-3.5 h-3.5 text-blue-500" />;
    case "MINOR_MEDIA":
      return <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />;
    default:
      return <ShieldQuestion className="w-3.5 h-3.5 text-slate-400" />;
  }
};

// 숫자 포맷팅
const formatNumber = (num: number | null | undefined): string => {
  if (num === null || num === undefined) return "-";
  if (num >= 1e12) return `${(num / 1e12).toFixed(1)}조`;
  if (num >= 1e8) return `${(num / 1e8).toFixed(1)}억`;
  if (num >= 1e4) return `${(num / 1e4).toFixed(0)}만`;
  return num.toLocaleString();
};

export default function SignalDetailPage() {
  const { signalId } = useParams();
  const navigate = useNavigate();
  const [dismissDialogOpen, setDismissDialogOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");

  const { data: basicSignal, isLoading: basicLoading, error: basicError } = useSignalDetail(signalId || "");
  const { data: enrichedData } = useSignalEnrichedDetail(signalId || "");
  const { data: corpProfile } = useCorpProfile(basicSignal?.corp_id ?? "");
  const { data: relatedSignals } = useSignals(
    basicSignal?.corp_id
      ? { corp_id: basicSignal.corp_id, limit: 6 }
      : undefined
  );

  const updateStatus = useUpdateSignalStatus();
  const dismissMutation = useDismissSignal();

  const isLoading = basicLoading;
  const error = basicError;

  const signal = enrichedData || (basicSignal ? {
    ...basicSignal,
    analysis_reasoning: null,
    llm_model: null,
    corp_context: null,
    similar_cases: [],
    verifications: [],
    impact_analysis: [],
    related_signals: [],
    insight_excerpt: null,
  } : null);

  if (isLoading) {
    return (
      <MainLayout>
        <div className="h-[calc(100vh-100px)] flex items-center justify-center">
          <DynamicBackground />
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
            <p className="text-slate-500 font-medium animate-pulse">Analyzing Signal Data...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error || !signal) {
    return (
      <MainLayout>
        <div className="h-[calc(100vh-100px)] flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <AlertTriangle className="w-12 h-12 text-rose-400" />
            <p className="text-slate-600 text-lg font-medium">Signal Not Found</p>
            <Button variant="outline" onClick={() => navigate(-1)}>
              Go Back
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }


  const currentStatus = signal.signal_status || "NEW";
  const statusConfig = STATUS_CONFIG[currentStatus] || STATUS_CONFIG.NEW;

  const handleMarkReviewed = () => {
    if (!signalId) return;
    updateStatus.mutate(
      { signalId, status: "REVIEWED" },
      {
        onSuccess: () => toast.success("검토 완료", { description: "시그널이 검토 완료 처리되었습니다." }),
        onError: (error) => toast.error("처리 실패", { description: "시그널 상태 변경에 실패했습니다. 다시 시도해주세요." }),
      }
    );
  };

  const handleDismiss = () => {
    if (!signalId || !dismissReason.trim()) return;
    dismissMutation.mutate(
      { signalId, reason: dismissReason },
      {
        onSuccess: () => {
          setDismissDialogOpen(false);
          setDismissReason("");
          toast.success("기각 완료", { description: "시그널이 기각 처리되었습니다." });
        },
        onError: (error) => toast.error("처리 실패", { description: "시그널 기각에 실패했습니다. 다시 시도해주세요." }),
      }
    );
  };

  // Safe impact strength getter
  const impactStrength = signal.impact_strength || "MEDIUM";

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="relative min-h-[calc(100vh-100px)] flex flex-col max-w-7xl mx-auto z-10">

        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4"
        >
          <div className="space-y-2">
            <Button
              variant="ghost"
              className="pl-0 gap-2 text-slate-500 hover:text-slate-800 hover:bg-transparent"
              onClick={() => navigate("/")}
            >
              <ArrowLeft className="w-4 h-4" /> Back to Inbox
            </Button>

            <div className="flex items-center gap-3">
              <StatusBadge variant={statusConfig.variant}>{statusConfig.label}</StatusBadge>
              <div className="h-4 w-px bg-slate-200" />
              <span className="text-sm font-mono text-slate-400">{new Date(signal.detected_at).toLocaleString("ko-KR")}</span>
            </div>

            <h1 className="text-3xl md:text-5xl font-bold text-slate-900 tracking-tight leading-tight max-w-4xl">
              {signal.title}
            </h1>

            <div className="flex items-center gap-2 text-sm text-slate-500 pt-2">
              <Building2 className="w-4 h-4 text-slate-400" />
              <Link to={`/corporations/${signal.corp_id}`} className="font-semibold hover:text-indigo-600 transition-colors underline decoration-slate-200 underline-offset-4">
                {signal.corp_name}
              </Link>
              <span>·</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-500 font-medium text-xs">{getSignalTypeLabel(signal.signal_type)}</span>
            </div>
          </div>

          {/* Action Buttons */}
          {currentStatus === "NEW" && (
            <div className="flex items-center gap-3 self-start md:self-center">
              <Button
                variant="outline"
                className="h-10 px-5 rounded-full border-slate-200 bg-white/50 backdrop-blur-sm text-slate-600 hover:bg-white hover:text-rose-600 hover:border-rose-200 transition-all font-medium shadow-sm"
                onClick={() => setDismissDialogOpen(true)}
              >
                <XCircle className="w-4 h-4 mr-2" />
                Dismiss
              </Button>
              <Button
                className="h-10 px-6 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20 transition-all font-medium"
                onClick={handleMarkReviewed}
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                Mark as Verified
              </Button>
            </div>
          )}
        </motion.div>

        {/* Content Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-20">

          {/* Main Column (8) */}
          <div className="lg:col-span-8 space-y-6">

            {/* Executive Summary Card */}
            <GlassCard className="p-8 relative overflow-hidden group border-0 ring-1 ring-slate-200/50 shadow-xl shadow-indigo-500/5">
              {/* Background Glow */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50/50 rounded-full blur-3xl -z-10 opacity-50 group-hover:opacity-100 transition-opacity" />

              <div className="flex items-start justify-between gap-6">
                <div className="space-y-4 flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-indigo-50 rounded-lg">
                      <Sparkles className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-slate-900 leading-none">Executive Summary</h2>
                      <p className="text-xs text-slate-400 font-medium mt-1">AI-generated insight based on collected evidence</p>
                    </div>
                  </div>

                  <div className="bg-white/50 backdrop-blur-sm rounded-2xl p-6 border border-indigo-50/50 shadow-sm">
                    <p className="text-slate-700 leading-relaxed text-lg font-medium">
                      {signal.summary}
                    </p>
                  </div>

                  {/* Context Tags */}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {signal.impact_direction && (
                      <Tag className={signal.impact_direction === 'RISK' ? 'bg-rose-50 text-rose-600 border-rose-100 px-3 py-1 text-xs' : 'bg-emerald-50 text-emerald-600 border-emerald-100 px-3 py-1 text-xs'}>
                        {getImpactDirectionLabel(signal.impact_direction)}
                        {impactStrength && <span className="opacity-60 mx-1">|</span>}
                        {impactStrength && getStrengthLabel(impactStrength)}
                      </Tag>
                    )}
                    {signal.insight_excerpt && (
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-medium">
                        <Brain className="w-3 h-3" />
                        AI Focus: {signal.insight_excerpt.substring(0, 30)}...
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </GlassCard>

            {/* 1. Deep Dive Grid: Impact vs Reasoning */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

              {/* Left Column: Impact Metrics (5/12) */}
              <div className="lg:col-span-5 space-y-4">
                <div className="flex items-center gap-2 px-1">
                  <BarChart3 className="w-4 h-4 text-slate-500" />
                  <h3 className="text-sm font-bold text-slate-900">Impact Analysis</h3>
                </div>
                {signal.impact_analysis && signal.impact_analysis.length > 0 ? (
                  <div className="space-y-4">
                    {signal.impact_analysis.map((impact) => (
                      <ImpactCard key={impact.id} impact={impact} />
                    ))}
                  </div>
                ) : (
                  <GlassCard className="p-6 text-center text-slate-400 text-sm">
                    No quantitative impact analysis available.
                  </GlassCard>
                )}
              </div>

              {/* 2. Reasoning & Evidence (Reasoning Process + Supporting Evidence) */}
              {(signal.analysis_reasoning || (signal.evidences && signal.evidences.length > 0)) && (
                <div className="lg:col-span-7 bg-slate-50/80 rounded-2xl border border-slate-200/60 p-6 space-y-8 shadow-sm">

                  {/* Reasoning */}
                  {signal.analysis_reasoning && (
                    <div className="space-y-3">
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center gap-2">
                        <Brain className="w-3.5 h-3.5 text-slate-400" />
                        Reasoning Process
                      </h3>
                      <div className="prose prose-sm prose-slate max-w-none text-slate-700">
                        <ContextualHighlight text={signal.analysis_reasoning} reason="AI Logic" />
                      </div>
                    </div>
                  )}

                  {/* Evidence - Integrated visually */}
                  {signal.evidences && signal.evidences.length > 0 && (
                    <div className="space-y-3 border-t border-slate-200 pt-6">
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        Supporting Evidence ({signal.evidences.length})
                      </h3>
                      <div className="grid grid-cols-1 gap-3">
                        {signal.evidences.map((evidence) => (
                          <EvidenceCard key={evidence.evidence_id} evidence={evidence} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 3. Bank Perspective (Moved to bottom) */}
              {signal.bank_interpretation && (
                <GlassCard className="p-7 border border-slate-200 shadow-sm bg-white">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                      <div className="p-1.5 bg-slate-100 rounded-md">
                        <Landmark className="w-4 h-4 text-slate-600" />
                      </div>
                      Bank's Perspective
                    </h3>
                    {signal.portfolio_impact && (
                      <span className={`text-xs font-bold px-3 py-1 rounded-full border ${signal.portfolio_impact === 'HIGH' ? 'bg-rose-50 text-rose-700 border-rose-100' :
                        signal.portfolio_impact === 'MED' ? 'bg-amber-50 text-amber-700 border-amber-100' :
                          'bg-slate-50 text-slate-600 border-slate-100'
                        }`}>
                        Impact: {signal.portfolio_impact}
                      </span>
                    )}
                  </div>

                  <div className="pl-4 border-l-2 border-slate-100 ml-2">
                    <p className="text-slate-700 leading-relaxed text-base mb-6">
                      {signal.bank_interpretation}
                    </p>
                  </div>

                  {signal.recommended_action && (
                    <div className="flex items-start gap-4 p-5 rounded-xl bg-slate-50 border border-slate-100">
                      <div className={`p-2.5 rounded-full shrink-0 ${signal.action_priority === 'URGENT' ? 'bg-rose-100 text-rose-600' :
                        signal.action_priority === 'NORMAL' ? 'bg-amber-100 text-amber-600' :
                          'bg-slate-200 text-slate-500'
                        }`}>
                        {signal.action_priority === 'URGENT' ? (
                          <AlertCircle className="w-5 h-5" />
                        ) : signal.action_priority === 'NORMAL' ? (
                          <Target className="w-5 h-5" />
                        ) : (
                          <ClipboardList className="w-5 h-5" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Recommended Action</span>
                          {signal.action_priority && (
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${signal.action_priority === 'URGENT' ? 'bg-rose-100 text-rose-700' :
                              signal.action_priority === 'NORMAL' ? 'bg-amber-100 text-amber-700' :
                                'bg-slate-200 text-slate-600'
                              }`}>
                              {signal.action_priority}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-800 font-semibold mt-1">{signal.recommended_action}</p>
                      </div>
                    </div>
                  )}
                </GlassCard>
              )}
            </div>
          </div>

          {/* Side Column (4) */}
          <div className="lg:col-span-4 space-y-6">
            {/* Corp Profile */}
            {(signal.corp_context || corpProfile) && (
              <GlassCard className="p-0 overflow-hidden border border-slate-100 shadow-lg shadow-slate-200/50">
                <div className="p-4 border-b border-slate-50 bg-slate-50/50 flex items-center justify-between backdrop-blur-sm">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2 text-sm">
                    <Building2 className="w-3.5 h-3.5 text-slate-500" />
                    Corporate Profile
                  </h3>
                  <Link to={`/corporations/${signal.corp_id}`} className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors flex items-center gap-1 group">
                    Details <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>
                <div className="p-5">
                  {signal.corp_context ? (
                    <CorpContextCard context={signal.corp_context} />
                  ) : corpProfile ? (
                    <CorpProfileCard profile={corpProfile} corpId={signal.corp_id} />
                  ) : null}
                </div>
              </GlassCard>
            )}

            {/* Related Signals */}
            {((signal.related_signals && signal.related_signals.length > 0) ||
              (relatedSignals && relatedSignals.filter(s => s.id !== signalId).length > 0)) && (
                <GlassCard className="p-6">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                    <LinkIcon className="w-4 h-4 text-slate-400" />
                    Related Signals
                  </h3>
                  <div className="space-y-1">
                    {signal.related_signals && signal.related_signals.length > 0 ? (
                      signal.related_signals.slice(0, 5).map((rel) => (
                        <RelatedSignalItem key={rel.signal_id} signal={rel} />
                      ))
                    ) : relatedSignals ? (
                      relatedSignals
                        .filter(s => s.id !== signalId)
                        .slice(0, 5)
                        .map((s) => (
                          <SimpleRelatedSignalItem key={s.id} signal={s} />
                        ))
                    ) : null}
                  </div>
                </GlassCard>
              )}
          </div>
        </div>
      </div>

      {/* Dismiss Dialog */}
      <Dialog open={dismissDialogOpen} onOpenChange={setDismissDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Dismiss Signal</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-slate-500 mb-3">
              Please provide a reason for dismissing this signal. This helps improve future accuracy.
            </p>
            <Textarea
              placeholder="e.g., False positive, Already mitigated, Irrelevant..."
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              rows={3}
              className="resize-none focus:ring-indigo-500"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDismissDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDismiss}
              disabled={!dismissReason.trim() || dismissMutation.isPending}
            >
              {dismissMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Confirm Dismissal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}

// ============================================================
// Sub Components (Refactored)
// ============================================================

function EvidenceCard({ evidence }: { evidence: ApiEnrichedEvidence }) {
  const credibilityLabel = {
    OFFICIAL: "Official",
    MAJOR_MEDIA: "Major Media",
    MINOR_MEDIA: "Media",
    UNKNOWN: "Unknown",
  }[evidence.source_credibility || "UNKNOWN"];

  const typeLabel = evidence.evidence_type;

  return (
    <GlassCard className="p-4 bg-white hover:bg-slate-50/50 transition-all border border-slate-100 shadow-sm group">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusBadge variant="neutral" className="py-0 px-2 h-5 text-[10px] font-semibold border-slate-200 bg-slate-100 text-slate-500 group-hover:bg-white transition-colors">
            {typeLabel}
          </StatusBadge>
          <div className="h-3 w-px bg-slate-200" />
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <CredibilityIcon credibility={evidence.source_credibility} />
            <span>{credibilityLabel}</span>
          </div>
        </div>
        {evidence.verification_status === "VERIFIED" && (
          <div className="flex items-center gap-1 text-emerald-600 text-[10px] font-bold uppercase tracking-wider bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
            <Check className="w-3 h-3" /> Verified
          </div>
        )}
      </div>

      {evidence.snippet && (
        <p className="text-sm text-slate-700 mb-3 leading-relaxed font-medium">{evidence.snippet}</p>
      )}

      {evidence.ref_type === "URL" && evidence.ref_value && (
        <a
          href={evidence.ref_value}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1.5 rounded-md"
        >
          <ExternalLink className="w-3 h-3" />
          {evidence.source_domain || "View Source"}
        </a>
      )}

      {evidence.ref_type === "SNAPSHOT_KEYPATH" && (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1.5 rounded-md">
          <Info className="w-3 h-3" />
          Internal: {evidence.ref_value}
        </span>
      )}
    </GlassCard>
  );
}

function ImpactCard({ impact }: { impact: ApiImpactAnalysis }) {
  const directionIcon = {
    INCREASE: <TrendingUp className="w-4 h-4 text-rose-500" />,
    DECREASE: <TrendingDown className="w-4 h-4 text-emerald-500" />, // Context dependent usually
    STABLE: <Minus className="w-4 h-4 text-slate-400" />,
  }[impact.impact_direction || "STABLE"];

  return (
    <GlassCard className="p-5 flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-50 px-2 py-1 rounded">{impact.analysis_type}</span>
        <div className="p-1.5 bg-slate-50 rounded-lg">
          {directionIcon}
        </div>
      </div>
      <div>
        <p className="text-base font-bold text-slate-800 leading-tight mb-2">{impact.metric_name}</p>
        <div className="flex items-baseline gap-2">
          {impact.impact_percentage !== null && (
            <span className={`text-2xl font-mono font-bold tracking-tight ${impact.impact_percentage > 0 ? "text-rose-600" : "text-emerald-600"}`}>
              {impact.impact_percentage > 0 ? "+" : ""}{impact.impact_percentage}%
            </span>
          )}
          {impact.industry_percentile && (
            <span className="text-xs text-slate-400 font-medium">
              Top {100 - impact.industry_percentile}%
            </span>
          )}
        </div>
      </div>
      {impact.reasoning && (
        <p className="text-xs text-slate-500 mt-4 pt-3 border-t border-slate-100 line-clamp-2 leading-relaxed">
          {impact.reasoning}
        </p>
      )}
    </GlassCard>
  );
}

function CorpContextCard({ context }: { context: ApiCorpContext }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-y-4 gap-x-2">
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-semibold">Industry</p>
          <p className="text-sm font-bold text-slate-700 truncate">{context.industry_name || context.industry_code}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-semibold">Revenue</p>
          <p className="text-sm font-bold text-slate-700">{formatNumber(context.revenue_krw)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-semibold">Employees</p>
          <p className="text-sm font-bold text-slate-700">{context.employee_count?.toLocaleString() || "-"}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-semibold">Export %</p>
          <p className="text-sm font-bold text-slate-700">{context.export_ratio_pct ? `${context.export_ratio_pct}%` : "-"}</p>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-100 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500 font-medium">내부 등급</span>
          <StatusBadge variant={context.internal_risk_grade === "HIGH" ? "danger" : context.internal_risk_grade === "MED" ? "warning" : "success"} className="h-5 text-[10px] px-2">
            {getStrengthLabel(context.internal_risk_grade) || "-"}
          </StatusBadge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500 font-medium">공급망 리스크</span>
          <StatusBadge variant={context.supply_chain_risk === "HIGH" ? "danger" : context.supply_chain_risk === "MED" ? "warning" : "neutral"} className="h-5 text-[10px] px-2">
            {getStrengthLabel(context.supply_chain_risk) || "-"}
          </StatusBadge>
        </div>
        {context.overdue_flag && (
          <div className="flex items-center gap-2 p-2 bg-rose-50 rounded text-xs text-rose-600 font-bold border border-rose-100">
            <AlertCircle className="w-3.5 h-3.5" /> 연체 이력
          </div>
        )}
      </div>

      {context.country_exposure && context.country_exposure.length > 0 && (
        <div className="pt-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-2 font-semibold">국가별 노출</p>
          <div className="flex flex-wrap gap-1.5">
            {context.country_exposure.slice(0, 5).map((country) => (
              <Tag key={country} className="text-[10px] py-0.5 border-slate-200">
                {country}
              </Tag>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CorpProfileCard({ profile, corpId }: { profile: any; corpId: string }) {
  // Fallback wrapper for simpler profile data if full context unavailable
  return <CorpContextCard context={{
    ...profile,
    industry_name: "Manufacturing", // Mock or derived
    internal_risk_grade: "LOW",
    supply_chain_risk: "LOW"
  }} />
}

function RelatedSignalItem({ signal }: { signal: ApiRelatedSignal }) {
  const relationLabel = {
    SAME_CORP: "Same Corp",
    SAME_INDUSTRY: "Same Industry",
    CAUSAL: "Causal",
    TEMPORAL: "Temporal",
  }[signal.relation_type] || signal.relation_type;

  return (
    <Link
      to={`/signals/${signal.signal_id}`}
      className="group block p-3 rounded-xl hover:bg-white hover:shadow-md transition-all border border-transparent hover:border-slate-100"
    >
      <div className="flex items-start justify-between gap-3 mb-1">
        <span className="font-bold text-sm text-slate-700 group-hover:text-indigo-700 line-clamp-1 flex-1 transition-colors">
          {signal.title}
        </span>
        <Tag className={signal.impact_direction === "RISK" ? "bg-rose-50 text-rose-600 border-rose-100 text-[9px] h-5 py-0 px-1.5" : "bg-emerald-50 text-emerald-600 border-emerald-100 text-[9px] h-5 py-0 px-1.5"}>
          {signal.impact_direction === "RISK" ? "위험" : "기회"}
        </Tag>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-[9px] font-bold text-indigo-500 bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 rounded">{relationLabel}</span>
        <span className="text-[10px] text-slate-300">|</span>
        <span className="text-[10px] text-slate-500 font-medium">{signal.corp_name}</span>
      </div>
    </Link>
  );
}

function SimpleRelatedSignalItem({ signal }: { signal: any }) {
  return (
    <Link
      to={`/signals/${signal.id}`}
      className="group block p-3 rounded-xl hover:bg-white hover:shadow-md transition-all border border-transparent hover:border-slate-100"
    >
      <div className="flex items-start justify-between gap-3 mb-1">
        <span className="font-bold text-sm text-slate-700 group-hover:text-indigo-700 line-clamp-1 flex-1 transition-colors">
          {signal.title}
        </span>
        <Tag className={signal.impact === "risk" ? "bg-rose-50 text-rose-600 border-rose-100 text-[9px] h-5 py-0 px-1.5" : "bg-emerald-50 text-emerald-600 border-emerald-100 text-[9px] h-5 py-0 px-1.5"}>
          {signal.impact === "risk" ? "위험" : "기회"}
        </Tag>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-[9px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded">관련</span>
        <span className="text-[10px] text-slate-300">|</span>
        <span className="text-[10px] text-slate-500 font-medium">{signal.corporationName}</span>
      </div>
    </Link>
  );
}
