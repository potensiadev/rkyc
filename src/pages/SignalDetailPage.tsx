import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  Tag,
  Check,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Users,
  Globe,
  Factory,
  Briefcase,
  ChevronRight,
  Sparkles,
  History,
  Link as LinkIcon,
  BarChart3,
  Percent,
  Info,
  Brain,
  Target,
  AlertCircle,
} from "lucide-react";
import {
  useSignalDetail,
  useSignalEnrichedDetail,
  useUpdateSignalStatus,
  useDismissSignal,
  useCorpProfile,
  useSignals,
  ApiSignalDetail,
  ApiEvidence,
  ApiEnrichedEvidence,
  ApiSimilarCase,
  ApiRelatedSignal,
  ApiCorpContext,
  ApiVerification,
  ApiImpactAnalysis,
} from "@/hooks/useApi";

// Signal Status 뱃지 설정
const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  NEW: { label: "신규", variant: "default" },
  REVIEWED: { label: "검토 완료", variant: "secondary" },
  DISMISSED: { label: "기각", variant: "outline" },
};

// 소스 신뢰도 아이콘
const CredibilityIcon = ({ credibility }: { credibility: string | null }) => {
  switch (credibility) {
    case "OFFICIAL":
      return <ShieldCheck className="w-4 h-4 text-green-600" />;
    case "MAJOR_MEDIA":
      return <Shield className="w-4 h-4 text-blue-500" />;
    case "MINOR_MEDIA":
      return <ShieldAlert className="w-4 h-4 text-yellow-500" />;
    default:
      return <ShieldQuestion className="w-4 h-4 text-gray-400" />;
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

  // 기본 Signal Detail API (안정적)
  const { data: basicSignal, isLoading: basicLoading, error: basicError } = useSignalDetail(signalId || "");

  // Enriched Detail API (선택적 - 실패해도 OK)
  const { data: enrichedData } = useSignalEnrichedDetail(signalId || "");

  // Corp Profile (선택적) - corp_id가 있을 때만 쿼리
  const { data: corpProfile } = useCorpProfile(basicSignal?.corp_id ?? "");

  // 관련 시그널 (같은 기업) - corp_id가 있을 때만 쿼리
  const { data: relatedSignals } = useSignals(
    basicSignal?.corp_id
      ? { corp_id: basicSignal.corp_id, limit: 6 } // 현재 시그널 제외용으로 1개 더
      : undefined
  );

  const updateStatus = useUpdateSignalStatus();
  const dismissMutation = useDismissSignal();

  // 기본 API 기준으로 로딩/에러 처리
  const isLoading = basicLoading;
  const error = basicError;

  // 데이터 병합: enriched가 있으면 사용, 없으면 basic 사용
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

  // 로딩 상태
  if (isLoading) {
    return (
      <MainLayout>
        <div className="h-[calc(100vh-100px)] flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-muted-foreground">시그널 정보를 불러오는 중...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  // 에러 상태
  if (error || !signal) {
    return (
      <MainLayout>
        <div className="h-[calc(100vh-100px)] flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <AlertTriangle className="w-8 h-8 text-destructive" />
            <p className="text-destructive">시그널을 찾을 수 없습니다.</p>
            <Button variant="outline" onClick={() => navigate(-1)}>
              돌아가기
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  // 신뢰도 점수 계산
  const matchingScore = signal.confidence === "HIGH" ? 92 : signal.confidence === "MED" ? 75 : 45;

  // 상태 변경 핸들러
  const handleMarkReviewed = () => {
    if (!signalId) return;
    updateStatus.mutate({ signalId, status: "REVIEWED" });
  };

  const handleDismiss = () => {
    if (!signalId || !dismissReason.trim()) return;
    dismissMutation.mutate(
      { signalId, reason: dismissReason },
      {
        onSuccess: () => {
          setDismissDialogOpen(false);
          setDismissReason("");
        },
      }
    );
  };

  const currentStatus = signal.signal_status || "NEW";
  const statusConfig = STATUS_CONFIG[currentStatus];

  return (
    <MainLayout>
      <div className="h-[calc(100vh-100px)] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="gap-2" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-4 h-4" /> 뒤로가기
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold">{signal.title}</h1>
                <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                <Link to={`/corporations/${signal.corp_id}`} className="hover:underline">
                  {signal.corp_name}
                </Link>
                {" · "}감지일시: {new Date(signal.detected_at).toLocaleString("ko-KR")}
              </p>
            </div>
          </div>

          {/* 상태 변경 버튼 */}
          {currentStatus === "NEW" && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="gap-2"
                onClick={handleMarkReviewed}
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                검토 완료
              </Button>
              <Button
                variant="outline"
                className="gap-2 text-destructive hover:text-destructive"
                onClick={() => setDismissDialogOpen(true)}
              >
                <XCircle className="w-4 h-4" />
                기각
              </Button>
            </div>
          )}
        </div>

        {/* Full Page Content - 2 Column Layout */}
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left Column - Main Content (2/3) */}
            <div className="lg:col-span-2 space-y-4">
              {/* 기업 정보 헤더 + 요약 */}
              <Card className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h2 className="text-xl font-bold">{signal.corp_name}</h2>
                      <Badge variant={signal.impact_direction === "RISK" ? "destructive" : signal.impact_direction === "OPPORTUNITY" ? "default" : "secondary"}>
                        {signal.impact_direction === "RISK" ? "리스크" : signal.impact_direction === "OPPORTUNITY" ? "기회" : "중립"}
                      </Badge>
                      <Badge variant="outline">{signal.impact_strength}</Badge>
                    </div>
                    <p className="text-muted-foreground">{signal.summary}</p>
                  </div>
                  {/* Score Ring */}
                  <div className="relative w-20 h-20 flex items-center justify-center shrink-0 ml-4">
                    <svg className="w-full h-full -rotate-90">
                      <circle cx="40" cy="40" r="32" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-muted" />
                      <circle
                        cx="40" cy="40" r="32"
                        stroke="currentColor"
                        strokeWidth="6"
                        fill="transparent"
                        className={signal.impact_direction === "RISK" ? "text-red-500" : signal.impact_direction === "OPPORTUNITY" ? "text-green-500" : "text-blue-500"}
                        strokeDasharray="201"
                        strokeDashoffset={201 - (201 * matchingScore) / 100}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-lg font-bold">{matchingScore}</span>
                      <span className="text-[9px] text-muted-foreground font-medium">SCORE</span>
                    </div>
                  </div>
                </div>

                {/* Signal Meta Grid */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                    <Building2 className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-[10px] text-muted-foreground">기업</p>
                      <p className="text-sm font-medium truncate">{signal.corp_name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                    <Tag className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-[10px] text-muted-foreground">유형</p>
                      <p className="text-sm font-medium">{signal.signal_type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-[10px] text-muted-foreground">감지일</p>
                      <p className="text-sm font-medium">{new Date(signal.detected_at).toLocaleDateString("ko-KR")}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                    {signal.impact_direction === "RISK" ? (
                      <TrendingDown className="w-4 h-4 text-red-500" />
                    ) : signal.impact_direction === "OPPORTUNITY" ? (
                      <TrendingUp className="w-4 h-4 text-green-500" />
                    ) : (
                      <Minus className="w-4 h-4 text-gray-500" />
                    )}
                    <div>
                      <p className="text-[10px] text-muted-foreground">영향</p>
                      <p className={`text-sm font-medium ${signal.impact_direction === "RISK" ? "text-red-500" : signal.impact_direction === "OPPORTUNITY" ? "text-green-500" : ""}`}>
                        {signal.impact_direction === "RISK" ? "리스크" : signal.impact_direction === "OPPORTUNITY" ? "기회" : "중립"}
                      </p>
                    </div>
                  </div>
                </div>
              </Card>

              {/* 분석 근거 (LLM Reasoning) */}
              {signal.analysis_reasoning && (
                <Card className="p-6">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-500" />
                    AI 분석 근거
                    {signal.llm_model && (
                      <span className="text-xs text-muted-foreground font-normal">({signal.llm_model})</span>
                    )}
                  </h3>
                  <div className="p-4 bg-purple-50 dark:bg-purple-950/20 rounded-lg border border-purple-100 dark:border-purple-900">
                    <p className="text-sm leading-relaxed">{signal.analysis_reasoning}</p>
                  </div>
                </Card>
              )}

              {/* 근거 자료 (Evidence) */}
              {signal.evidences && signal.evidences.length > 0 && (
                <Card className="p-6">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    근거 자료 ({signal.evidences.length}건)
                  </h3>
                  <div className="space-y-3">
                    {signal.evidences.map((evidence) => (
                      <EvidenceCard key={evidence.evidence_id} evidence={evidence} />
                    ))}
                  </div>
                </Card>
              )}

              {/* 소스 검증 결과 */}
              {signal.verifications && signal.verifications.length > 0 && (
                <Card className="p-6">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-green-600" />
                    소스 검증 결과
                  </h3>
                  <div className="space-y-2">
                    {signal.verifications.map((v) => (
                      <VerificationItem key={v.id} verification={v} />
                    ))}
                  </div>
                </Card>
              )}

              {/* 영향도 분석 */}
              {signal.impact_analysis && signal.impact_analysis.length > 0 && (
                <Card className="p-6">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-blue-500" />
                    영향도 분석
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {signal.impact_analysis.map((impact) => (
                      <ImpactCard key={impact.id} impact={impact} />
                    ))}
                  </div>
                </Card>
              )}

              {/* 인사이트 발췌 */}
              {signal.insight_excerpt && (
                <Card className="p-6">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-yellow-500" />
                    인사이트
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{signal.insight_excerpt}</p>
                </Card>
              )}
            </div>

            {/* Right Column - Context (1/3) */}
            <div className="space-y-4">
              {/* 기업 컨텍스트 - Corp Profile API에서 가져온 데이터 사용 */}
              {(signal.corp_context || corpProfile) && (
                <Card className="p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                    <Building2 className="w-4 h-4" />
                    기업 프로필
                  </h3>
                  {signal.corp_context ? (
                    <CorpContextCard context={signal.corp_context} />
                  ) : corpProfile ? (
                    <CorpProfileCard profile={corpProfile} corpId={signal.corp_id} />
                  ) : null}
                </Card>
              )}

              {/* 유사 과거 케이스 */}
              {signal.similar_cases && signal.similar_cases.length > 0 && (
                <Card className="p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                    <History className="w-4 h-4" />
                    유사 과거 케이스
                  </h3>
                  <div className="space-y-2">
                    {signal.similar_cases.map((c) => (
                      <SimilarCaseItem key={c.id} caseData={c} />
                    ))}
                  </div>
                </Card>
              )}

              {/* 관련 시그널 - API 또는 직접 조회한 데이터 */}
              {((signal.related_signals && signal.related_signals.length > 0) ||
                (relatedSignals && relatedSignals.filter(s => s.id !== signalId).length > 0)) && (
                <Card className="p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                    <LinkIcon className="w-4 h-4" />
                    관련 시그널
                  </h3>
                  <div className="space-y-2">
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
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 기각 사유 입력 다이얼로그 */}
      <Dialog open={dismissDialogOpen} onOpenChange={setDismissDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>시그널 기각</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-2">
              기각 사유를 입력해주세요. 이 정보는 향후 분석 개선에 활용됩니다.
            </p>
            <Textarea
              placeholder="예: 이미 처리된 건, 오탐 등"
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDismissDialogOpen(false)}>
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={handleDismiss}
              disabled={!dismissReason.trim() || dismissMutation.isPending}
            >
              {dismissMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              기각 처리
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}

// ============================================================
// Sub Components
// ============================================================

// Evidence 카드
function EvidenceCard({ evidence }: { evidence: ApiEnrichedEvidence }) {
  const credibilityLabel = {
    OFFICIAL: "공식 출처",
    MAJOR_MEDIA: "주요 언론",
    MINOR_MEDIA: "일반 뉴스",
    UNKNOWN: "미확인",
  }[evidence.source_credibility || "UNKNOWN"];

  const typeLabel = {
    INTERNAL_FIELD: "내부 데이터",
    DOC: "문서",
    EXTERNAL: "외부 소스",
  }[evidence.evidence_type];

  return (
    <div className="p-3 bg-muted/50 rounded-lg border border-border">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <CredibilityIcon credibility={evidence.source_credibility} />
          <span className="text-xs font-medium">{credibilityLabel}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">{typeLabel}</span>
          {evidence.is_primary_source && (
            <Badge variant="outline" className="text-[10px] py-0 px-1">1차 출처</Badge>
          )}
        </div>
        {evidence.verification_status === "VERIFIED" && (
          <Badge variant="secondary" className="text-[10px] py-0">
            <Check className="w-3 h-3 mr-1" /> 검증됨
          </Badge>
        )}
      </div>

      {evidence.snippet && (
        <p className="text-sm text-muted-foreground mb-2 line-clamp-2">{evidence.snippet}</p>
      )}

      {evidence.ref_type === "URL" && evidence.ref_value && (
        <a
          href={evidence.ref_value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary flex items-center gap-1 hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          {evidence.source_domain || "원문 보기"}
        </a>
      )}

      {evidence.ref_type === "SNAPSHOT_KEYPATH" && (
        <div className="text-xs text-muted-foreground flex items-center gap-1">
          <Info className="w-3 h-3" />
          내부 데이터: {evidence.ref_value}
        </div>
      )}
    </div>
  );
}

// 검증 결과 아이템
function VerificationItem({ verification }: { verification: ApiVerification }) {
  const statusConfig = {
    VERIFIED: { icon: <ShieldCheck className="w-4 h-4 text-green-600" />, label: "검증됨", color: "text-green-600" },
    PARTIAL: { icon: <Shield className="w-4 h-4 text-yellow-500" />, label: "부분 검증", color: "text-yellow-600" },
    UNVERIFIED: { icon: <ShieldQuestion className="w-4 h-4 text-gray-400" />, label: "미검증", color: "text-gray-500" },
    CONFLICTING: { icon: <ShieldAlert className="w-4 h-4 text-red-500" />, label: "불일치", color: "text-red-500" },
  }[verification.verification_status];

  return (
    <div className="flex items-center justify-between p-2 bg-muted/30 rounded">
      <div className="flex items-center gap-2">
        {statusConfig.icon}
        <span className="text-sm">{verification.source_name || "출처"}</span>
      </div>
      <span className={`text-xs font-medium ${statusConfig.color}`}>{statusConfig.label}</span>
    </div>
  );
}

// 영향도 분석 카드
function ImpactCard({ impact }: { impact: ApiImpactAnalysis }) {
  const typeLabel = {
    FINANCIAL: "재무 영향",
    CREDIT: "신용 영향",
    OPERATIONAL: "운영 영향",
    REGULATORY: "규제 영향",
  }[impact.analysis_type];

  const directionIcon = {
    INCREASE: <TrendingUp className="w-4 h-4 text-green-500" />,
    DECREASE: <TrendingDown className="w-4 h-4 text-red-500" />,
    STABLE: <Minus className="w-4 h-4 text-gray-500" />,
  }[impact.impact_direction || "STABLE"];

  return (
    <div className="p-3 bg-muted/50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-muted-foreground">{typeLabel}</span>
        {directionIcon}
      </div>
      <p className="text-sm font-medium mb-1">{impact.metric_name}</p>
      {impact.impact_percentage !== null && (
        <div className="flex items-center gap-1">
          <Percent className="w-3 h-3 text-muted-foreground" />
          <span className={`text-sm ${impact.impact_direction === "INCREASE" ? "text-green-600" : impact.impact_direction === "DECREASE" ? "text-red-600" : ""}`}>
            {impact.impact_percentage > 0 ? "+" : ""}{impact.impact_percentage}%
          </span>
        </div>
      )}
      {impact.industry_percentile && (
        <p className="text-xs text-muted-foreground mt-1">
          업종 내 상위 {100 - impact.industry_percentile}%
        </p>
      )}
      {impact.reasoning && (
        <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{impact.reasoning}</p>
      )}
    </div>
  );
}

// 기업 컨텍스트 카드
function CorpContextCard({ context }: { context: ApiCorpContext }) {
  return (
    <div className="space-y-3">
      {/* 기본 정보 */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-xs text-muted-foreground">업종</p>
          <p className="font-medium">{context.industry_name || context.industry_code}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">매출</p>
          <p className="font-medium">{formatNumber(context.revenue_krw)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">수출 비중</p>
          <p className="font-medium">{context.export_ratio_pct ? `${context.export_ratio_pct}%` : "-"}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">임직원</p>
          <p className="font-medium">{context.employee_count?.toLocaleString() || "-"}명</p>
        </div>
      </div>

      {/* 리스크 지표 */}
      <div className="pt-2 border-t">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">내부 등급</span>
          <Badge variant={context.internal_risk_grade === "HIGH" ? "destructive" : context.internal_risk_grade === "MED" ? "default" : "secondary"}>
            {context.internal_risk_grade || "-"}
          </Badge>
        </div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">공급망 리스크</span>
          <Badge variant={context.supply_chain_risk === "HIGH" ? "destructive" : context.supply_chain_risk === "MED" ? "default" : "secondary"}>
            {context.supply_chain_risk || "-"}
          </Badge>
        </div>
        {context.overdue_flag && (
          <div className="flex items-center gap-1 text-red-500 text-xs">
            <AlertCircle className="w-3 h-3" />
            연체 이력 있음
          </div>
        )}
      </div>

      {/* 국가 노출 */}
      {context.country_exposure && context.country_exposure.length > 0 && (
        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground mb-1">국가별 노출</p>
          <div className="flex flex-wrap gap-1">
            {context.country_exposure.slice(0, 5).map((country) => (
              <Badge key={country} variant="outline" className="text-[10px] py-0">
                <Globe className="w-3 h-3 mr-1" />
                {country}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 프로필 링크 */}
      <Link
        to={`/corporations/${context.corp_id}`}
        className="flex items-center justify-between p-2 bg-muted/50 rounded text-sm hover:bg-muted transition-colors"
      >
        <span>기업 상세 보기</span>
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

// 유사 케이스 아이템
function SimilarCaseItem({ caseData }: { caseData: ApiSimilarCase }) {
  const similarityPercent = Math.round(caseData.similarity_score * 100);

  return (
    <div className="p-2 bg-muted/30 rounded text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium truncate">{caseData.corp_name || "Unknown"}</span>
        <Badge variant="outline" className="text-[10px] py-0">
          {similarityPercent}% 유사
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground line-clamp-2">{caseData.summary || "-"}</p>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-[10px] text-muted-foreground">{caseData.signal_type}</span>
        <span className="text-[10px] text-muted-foreground">·</span>
        <span className="text-[10px] text-muted-foreground">{caseData.event_type}</span>
      </div>
    </div>
  );
}

// 관련 시그널 아이템
function RelatedSignalItem({ signal }: { signal: ApiRelatedSignal }) {
  const relationLabel = {
    SAME_CORP: "동일 기업",
    SAME_INDUSTRY: "동일 업종",
    CAUSAL: "인과관계",
    TEMPORAL: "시간적 연관",
  }[signal.relation_type];

  return (
    <Link
      to={`/signals/${signal.signal_id}`}
      className="block p-2 bg-muted/30 rounded text-sm hover:bg-muted transition-colors"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium truncate">{signal.title}</span>
        <Badge variant={signal.impact_direction === "RISK" ? "destructive" : signal.impact_direction === "OPPORTUNITY" ? "default" : "secondary"} className="text-[10px] py-0">
          {signal.impact_direction === "RISK" ? "리스크" : signal.impact_direction === "OPPORTUNITY" ? "기회" : "중립"}
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-muted-foreground">{relationLabel}</span>
        <span className="text-[10px] text-muted-foreground">·</span>
        <span className="text-[10px] text-muted-foreground">{signal.corp_name}</span>
      </div>
    </Link>
  );
}

// 기업 프로필 카드 (Corp Profile API에서 가져온 데이터용)
function CorpProfileCard({ profile, corpId }: { profile: {
  corp_id: string;
  business_summary?: string | null;
  revenue_krw?: number | null;
  export_ratio_pct?: number | null;
  employee_count?: number | null;
  country_exposure?: string[] | null;
  confidence?: string | null;
}; corpId: string }) {
  return (
    <div className="space-y-3">
      {/* 사업 요약 */}
      {profile.business_summary && (
        <div>
          <p className="text-xs text-muted-foreground mb-1">사업 개요</p>
          <p className="text-sm line-clamp-3">{profile.business_summary}</p>
        </div>
      )}

      {/* 기본 정보 */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-xs text-muted-foreground">매출</p>
          <p className="font-medium">{formatNumber(profile.revenue_krw)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">수출 비중</p>
          <p className="font-medium">{profile.export_ratio_pct ? `${profile.export_ratio_pct}%` : "-"}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">임직원</p>
          <p className="font-medium">{profile.employee_count?.toLocaleString() || "-"}명</p>
        </div>
        {profile.confidence && (
          <div>
            <p className="text-xs text-muted-foreground">신뢰도</p>
            <Badge variant={profile.confidence === "HIGH" ? "default" : profile.confidence === "MED" ? "secondary" : "outline"} className="text-[10px]">
              {profile.confidence}
            </Badge>
          </div>
        )}
      </div>

      {/* 국가 노출 */}
      {profile.country_exposure && profile.country_exposure.length > 0 && (
        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground mb-1">국가별 노출</p>
          <div className="flex flex-wrap gap-1">
            {profile.country_exposure.slice(0, 5).map((country) => (
              <Badge key={country} variant="outline" className="text-[10px] py-0">
                <Globe className="w-3 h-3 mr-1" />
                {country}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 프로필 링크 */}
      <Link
        to={`/corporations/${corpId}`}
        className="flex items-center justify-between p-2 bg-muted/50 rounded text-sm hover:bg-muted transition-colors"
      >
        <span>기업 상세 보기</span>
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

// 단순 관련 시그널 아이템 (기본 Signal API에서 가져온 데이터용 - Signal 타입 사용)
function SimpleRelatedSignalItem({ signal }: { signal: {
  id: string;
  title: string;
  signalCategory: string;
  detailCategory: string;
  impact: string;
  impactStrength: string;
  detectedAt: string;
  corporationName: string;
} }) {
  return (
    <Link
      to={`/signals/${signal.id}`}
      className="block p-2 bg-muted/30 rounded text-sm hover:bg-muted transition-colors"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium truncate">{signal.title}</span>
        <Badge variant={signal.impact === "risk" ? "destructive" : signal.impact === "opportunity" ? "default" : "secondary"} className="text-[10px] py-0">
          {signal.impact === "risk" ? "리스크" : signal.impact === "opportunity" ? "기회" : "중립"}
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-muted-foreground">{signal.detailCategory}</span>
        <span className="text-[10px] text-muted-foreground">·</span>
        <span className="text-[10px] text-muted-foreground">{new Date(signal.detectedAt).toLocaleDateString("ko-KR")}</span>
      </div>
    </Link>
  );
}
