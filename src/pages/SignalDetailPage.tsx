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
import { ArrowLeft, CheckCircle, XCircle, Loader2, FileText, ExternalLink, AlertTriangle } from "lucide-react";
import { AnalysisReport } from "@/components/detail/AnalysisReport";
import { DocViewer } from "@/components/detail/DocViewer";
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

        {/* Content Split */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
          {/* Left: Document View & Evidence */}
          <div className="h-full flex flex-col gap-4 overflow-hidden">
            {/* 문서 뷰어 */}
            <div className="flex-1 border rounded-lg bg-card overflow-hidden">
              <DocViewer
                sensitiveData={{ phone: "010-****", email: "****@****.**", rrn: "******-*******" }}
                documentText={`
[SIGNAL DETAIL]
Target: ${signal.corp_name} (${signal.corp_id})
Date: ${new Date(signal.detected_at).toLocaleString("ko-KR")}
Subject: ${signal.title}

1. OVERVIEW
Type: ${signal.signal_type} / ${signal.event_type}
Impact: ${signal.impact_direction} (${signal.impact_strength})
Confidence: ${signal.confidence}

2. SUMMARY
${signal.summary}

3. EVIDENCE COUNT: ${signal.evidence_count}
${signal.evidences?.map((e) => `- [${e.evidence_type}] ${e.ref_value}`).join("\n") || "No evidence attached."}
                `}
              />
            </div>

            {/* Evidence 목록 */}
            {signal.evidences && signal.evidences.length > 0 && (
              <Card className="p-4 max-h-48 overflow-y-auto">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  근거 자료 ({signal.evidences.length}건)
                </h3>
                <div className="space-y-2">
                  {signal.evidences.map((evidence: ApiEvidence) => (
                    <EvidenceItem key={evidence.evidence_id} evidence={evidence} />
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Right: Analysis */}
          <div className="h-full border rounded-lg bg-card overflow-hidden p-0">
            <AnalysisReport
              score={matchingScore}
              corporationName={signal.corp_name}
              summary={signal.summary_short || signal.summary}
              history={[]}
            />
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
