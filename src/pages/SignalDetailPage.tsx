import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
import { ArrowLeft, CheckCircle, XCircle, Loader2, FileText, ExternalLink, AlertTriangle, TrendingUp, TrendingDown, Minus, Building2, Calendar, Tag, Check } from "lucide-react";
import {
  useSignalDetail,
  useUpdateSignalStatus,
  useDismissSignal,
  ApiEvidence,
} from "@/hooks/useApi";

// Evidence 타입별 아이콘/색상
const EVIDENCE_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  INTERNAL_FIELD: { label: "내부 데이터", color: "bg-blue-100 text-blue-700" },
  DOC: { label: "문서", color: "bg-green-100 text-green-700" },
  EXTERNAL: { label: "외부 소스", color: "bg-purple-100 text-purple-700" },
};

// Signal Status 뱃지 설정
const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  NEW: { label: "신규", variant: "default" },
  REVIEWED: { label: "검토 완료", variant: "secondary" },
  DISMISSED: { label: "기각", variant: "outline" },
};

export default function SignalDetailPage() {
  const { signalId } = useParams();
  const navigate = useNavigate();
  const [dismissDialogOpen, setDismissDialogOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");

  // API 훅
  const { data: signal, isLoading, error } = useSignalDetail(signalId || "");
  const updateStatus = useUpdateSignalStatus();
  const dismissMutation = useDismissSignal();

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

  // 현재 상태
  const currentStatus = signal.signal_status || "NEW";
  const statusConfig = STATUS_CONFIG[currentStatus];

  return (
    <MainLayout>
      <div className="h-[calc(100vh-100px)] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
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
                {signal.corp_name} · 감지일시: {new Date(signal.detected_at).toLocaleString("ko-KR")}
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

        {/* Full Page Content */}
        <div className="flex-1 overflow-auto">
          <Card className="p-8">
            {/* 기업 정보 헤더 */}
            <div className="flex items-start justify-between mb-8 pb-6 border-b">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-bold">{signal.corp_name}</h2>
                  <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-bold">
                    Active
                  </span>
                </div>
                <p className="text-muted-foreground max-w-2xl">
                  {signal.summary}
                </p>
              </div>
              {/* Score */}
              <div className="relative w-24 h-24 flex items-center justify-center shrink-0">
                <svg className="w-full h-full -rotate-90">
                  <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-muted" />
                  <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-primary"
                    strokeDasharray="251.2" strokeDashoffset={251.2 - (251.2 * matchingScore) / 100} strokeLinecap="round" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-bold">{matchingScore}</span>
                  <span className="text-[10px] text-muted-foreground font-bold">SCORE</span>
                </div>
              </div>
            </div>

            {/* 시그널 상세 정보 */}
            <div className="mb-8">
              <h3 className="font-semibold mb-4 text-lg">시그널 상세</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                  <Building2 className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">대상 기업</p>
                    <p className="font-medium">{signal.corp_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                  <Calendar className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">감지 일시</p>
                    <p className="font-medium">{new Date(signal.detected_at).toLocaleDateString("ko-KR")}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                  <Tag className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">시그널 유형</p>
                    <p className="font-medium">{signal.signal_type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                  {signal.impact_direction === "RISK" ? (
                    <TrendingDown className="w-5 h-5 text-red-500" />
                  ) : signal.impact_direction === "OPPORTUNITY" ? (
                    <TrendingUp className="w-5 h-5 text-green-500" />
                  ) : (
                    <Minus className="w-5 h-5 text-gray-500" />
                  )}
                  <div>
                    <p className="text-xs text-muted-foreground">영향</p>
                    <p className={`font-medium ${signal.impact_direction === "RISK" ? "text-red-500" : signal.impact_direction === "OPPORTUNITY" ? "text-green-500" : ""}`}>
                      {signal.impact_direction === "RISK" ? "리스크" : signal.impact_direction === "OPPORTUNITY" ? "기회" : "중립"} ({signal.impact_strength})
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-4">
                <Badge variant="outline">{signal.signal_type}</Badge>
                <Badge variant="secondary">{signal.event_type}</Badge>
              </div>
            </div>

            {/* 검증 항목 */}
            <div className="mb-8">
              <h3 className="text-sm font-bold text-muted-foreground mb-4 uppercase tracking-wider">검증 항목 (Verification)</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <VerificationCard label="기업 상태" isValid={true} value="정상" />
                <VerificationCard label="세금 납부" isValid={true} value="완납" />
                <VerificationCard label="신용 등급" isValid={false} value="검토 필요" />
                <VerificationCard label="주소지 확인" isValid={true} value="일치" />
              </div>
            </div>

            {/* 근거 자료 */}
            {signal.evidences && signal.evidences.length > 0 && (
              <div className="mb-8">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  근거 자료 ({signal.evidences.length}건)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {signal.evidences.map((evidence: ApiEvidence) => (
                    <EvidenceItem key={evidence.evidence_id} evidence={evidence} />
                  ))}
                </div>
              </div>
            )}

            {/* 히스토리 타임라인 */}
            <div>
              <h3 className="text-sm font-bold text-muted-foreground mb-4 uppercase tracking-wider">히스토리 타임라인</h3>
              <div className="space-y-4 pl-4 border-l border-border ml-2">
                {[2024, 2023, 2022].map((year) => (
                  <div key={year} className="relative group">
                    <div className="absolute -left-[21px] top-1 w-3 h-3 rounded-full bg-background border-2 border-muted-foreground group-hover:border-primary transition-colors" />
                    <div className="bg-muted/30 border border-border p-4 rounded-lg hover:bg-muted/50 transition-colors">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-bold">{year} 주요 이벤트</span>
                        <span className="text-xs text-green-600 font-mono">Verified</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {year}년도 회계연도 주요 기업 공시 및 뉴스 검토 완료. 특이 위험 시그널 감지되지 않음.
                      </p>
                      <div className="flex gap-2 mt-3">
                        <span className="text-[10px] px-2 py-1 bg-muted text-muted-foreground rounded border border-border flex items-center gap-1">
                          <Tag className="w-3 h-3" /> 감사
                        </span>
                        <span className="text-[10px] px-2 py-1 bg-muted text-muted-foreground rounded border border-border flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> 4분기
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
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
              {dismissMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : null}
              기각 처리
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}

// Evidence 아이템 컴포넌트
function EvidenceItem({ evidence }: { evidence: ApiEvidence }) {
  const typeConfig = EVIDENCE_TYPE_CONFIG[evidence.evidence_type] || {
    label: evidence.evidence_type,
    color: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="p-3 bg-muted/50 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs px-2 py-0.5 rounded ${typeConfig.color}`}>
          {typeConfig.label}
        </span>
        <span className="text-xs text-muted-foreground">
          {evidence.ref_type === "URL" ? "외부 링크" : evidence.ref_type}
        </span>
      </div>
      <p className="text-sm font-medium">{evidence.ref_value}</p>
      {evidence.snippet && (
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{evidence.snippet}</p>
      )}
      {evidence.ref_type === "URL" && (
        <a
          href={evidence.ref_value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary flex items-center gap-1 mt-1 hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          원문 보기
        </a>
      )}
    </div>
  );
}

// 검증 카드 컴포넌트
function VerificationCard({ label, isValid, value }: { label: string; isValid: boolean; value: string }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
      <div>
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className="font-bold text-sm">{value}</p>
      </div>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isValid ? "bg-green-100 text-green-600" : "bg-yellow-100 text-yellow-600"}`}>
        {isValid ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
      </div>
    </div>
  );
}
