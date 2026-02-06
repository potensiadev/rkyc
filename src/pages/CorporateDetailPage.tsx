import { useParams, useNavigate } from "react-router-dom";
import { DynamicBackground, GlassCard } from "@/components/premium";
import { MainLayout } from "@/components/layout/MainLayout";
// Mock data imports removed
import {
  formatDate,
  getBankTransactionTypeLabel,
} from "@/data/signals";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import {
  ArrowLeft,
  Building2,
  Landmark,
  Users,
  Loader2,
  FileDown,
  RefreshCw,
  Globe,
  Factory,
  TrendingUp,
  Package,
  Shield,
  ExternalLink,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronDown,
  ChevronUp,
  FileText,
  Target,
  Zap,
  Search,
  FileWarning,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { useState, useEffect, useMemo, useCallback } from "react";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import { useCorporation, useSignals, useCorporationSnapshot, useCorpProfile, useCorpProfileDetail, useRefreshCorpProfile, useJobStatus, useLoanInsight } from "@/hooks/useApi";
import { toast } from "sonner";
import type { ProfileConfidence, CorpProfile } from "@/types/profile";
import { useQueryClient } from "@tanstack/react-query";
import { getCorporationReport } from "@/lib/api";
import { EvidenceBackedField } from "@/components/profile/EvidenceBackedField";
import { EvidenceMap } from "@/components/profile/EvidenceMap";
import { RiskIndicators } from "@/components/profile/RiskIndicators";

// Job 진행 단계 정의 (파이프라인 순서)
const JOB_STEPS = [
  { step: 'QUEUED', label: '대기 중', progress: 0 },
  { step: 'SNAPSHOT', label: '데이터 수집', progress: 10 },
  { step: 'DOC_INGEST', label: '문서 분석', progress: 20 },
  { step: 'PROFILING', label: '기업 프로파일링', progress: 35 },
  { step: 'EXTERNAL', label: '외부 정보 검색', progress: 50 },
  { step: 'CONTEXT', label: '컨텍스트 구성', progress: 60 },
  { step: 'SIGNAL', label: '시그널 추출', progress: 75 },
  { step: 'VALIDATION', label: '검증 중', progress: 85 },
  { step: 'INDEX', label: '인덱싱', progress: 90 },
  { step: 'INSIGHT', label: '인사이트 생성', progress: 95 },
  { step: 'DONE', label: '완료', progress: 100 },
];

function getJobProgress(currentStep: string | undefined): { progress: number; label: string } {
  if (!currentStep) return { progress: 5, label: '시작 중...' };
  const found = JOB_STEPS.find(s => s.step === currentStep);
  return found ? { progress: found.progress, label: found.label } : { progress: 5, label: currentStep };
}

// Confidence 배지 색상 헬퍼
function getConfidenceBadge(confidence: ProfileConfidence | undefined): { bg: string; text: string; label: string } {
  const map: Record<ProfileConfidence, { bg: string; text: string; label: string }> = {
    HIGH: { bg: 'bg-green-100', text: 'text-green-700', label: '신뢰도 높음' },
    MED: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '신뢰도 중간' },
    LOW: { bg: 'bg-orange-100', text: 'text-orange-700', label: '신뢰도 낮음' },
    NONE: { bg: 'bg-gray-100', text: 'text-gray-500', label: '데이터 없음' },
    CACHED: { bg: 'bg-blue-100', text: 'text-blue-700', label: '캐시 데이터' },
    STALE: { bg: 'bg-red-100', text: 'text-red-700', label: '만료됨' },
  };
  return map[confidence || 'NONE'] || map.NONE;
}

// 금액 포맷팅 헬퍼
function formatKRW(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조원`;
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(0)}억원`;
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(0)}만원`;
  return `${value.toLocaleString()}원`;
}

export default function CorporateDetailPage() {
  const { corpId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [refreshStatus, setRefreshStatus] = useState<'idle' | 'running' | 'done' | 'failed' | 'timeout'>('idle');

  // API 훅 사용
  const { data: corporation, isLoading: isLoadingCorp } = useCorporation(corpId || "");
  const { data: apiSignals, isLoading: isLoadingSignals } = useSignals({ corp_id: corpId });
  const { data: snapshot, isLoading: isLoadingSnapshot } = useCorporationSnapshot(corpId || "");
  const { data: profile, isLoading: isLoadingProfile, error: profileError, refetch: refetchProfile } = useCorpProfile(corpId || "");
  // 상세 프로필 (field_provenance 포함) - 기본 뷰 / 상세 뷰 토글용
  // P1-3 Fix: Add error handling for profileDetail
  const { data: profileDetail, error: profileDetailError, refetch: refetchProfileDetail } = useCorpProfileDetail(corpId || "");
  // Loan Insight (사전 생성된 AI 분석)
  const { data: loanInsight, isLoading: isLoadingLoanInsight, error: loanInsightError } = useLoanInsight(corpId || "");
  const refreshProfile = useRefreshCorpProfile();
  const [showDetailedView, setShowDetailedView] = useState(false);

  // 보고서 데이터 프리페칭 (hover 시 미리 로드)
  const prefetchReport = () => {
    if (corpId) {
      queryClient.prefetchQuery({
        queryKey: ['report', corpId],
        queryFn: () => getCorporationReport(corpId),
        staleTime: 10 * 60 * 1000, // 10분
      });
    }
  };

  // Job 타임아웃 핸들러
  const handleJobTimeout = useCallback(() => {
    setRefreshStatus('timeout');
    setRefreshJobId(null);
    toast.error("작업 시간 초과", {
      description: "분석 작업이 2분을 초과했습니다. 잠시 후 다시 시도해주세요.",
    });
  }, []);

  // Job 상태 폴링
  const { data: jobStatus } = useJobStatus(refreshJobId || '', {
    enabled: !!refreshJobId && refreshStatus === 'running',
    onTimeout: handleJobTimeout,
  });

  // Job 완료 시 프로필 + Loan Insight 다시 로드
  useEffect(() => {
    if (jobStatus?.status === 'DONE') {
      setRefreshStatus('done');
      setRefreshJobId(null);
      // 프로필 쿼리 무효화하여 다시 로드 (기본 + 상세)
      queryClient.invalidateQueries({ queryKey: ['corporation', corpId, 'profile'] });
      queryClient.invalidateQueries({ queryKey: ['corporation', corpId, 'profile', 'detail'] });
      // Loan Insight도 갱신
      queryClient.invalidateQueries({ queryKey: ['loan-insight', corpId] });
      toast.success("분석 완료", {
        description: "기업 정보가 성공적으로 갱신되었습니다.",
      });
    } else if (jobStatus?.status === 'FAILED') {
      setRefreshStatus('failed');
      setRefreshJobId(null);
      toast.error("분석 실패", {
        description: "기업 정보 갱신 중 오류가 발생했습니다.",
      });
    }
  }, [jobStatus?.status, queryClient, corpId]);

  // 정보 갱신 버튼 핸들러
  const handleRefreshProfile = async () => {
    if (!corpId) return;
    setRefreshStatus('running');
    toast.info("분석 시작", {
      description: "기업 정보 갱신을 시작합니다...",
    });

    try {
      const result = await refreshProfile.mutateAsync(corpId);
      if (result.status === 'QUEUED' && result.job_id) {
        setRefreshJobId(result.job_id);
      } else if (result.status === 'FAILED') {
        setRefreshStatus('failed');
        toast.error("분석 실패", {
          description: "기업 정보 갱신에 실패했습니다. 잠시 후 다시 시도해주세요.",
        });
      }
    } catch (error) {
      console.error('Profile refresh failed:', error);
      setRefreshStatus('failed');
      toast.error("분석 실패", {
        description: error instanceof Error ? error.message : "네트워크 오류가 발생했습니다.",
      });
    }
  };

  // 통합 로딩 상태 계산
  const loadingState = useMemo(() => {
    const states = [
      { name: '기업 정보', loading: isLoadingCorp, done: !!corporation },
      { name: '시그널', loading: isLoadingSignals, done: !!apiSignals },
      { name: '스냅샷', loading: isLoadingSnapshot, done: !!snapshot },
      { name: 'AI 분석', loading: isLoadingLoanInsight, done: !!loanInsight },
    ];
    const loadingItems = states.filter(s => s.loading);
    const doneCount = states.filter(s => s.done).length;
    const progress = Math.round((doneCount / states.length) * 100);
    return {
      isInitialLoading: isLoadingCorp,
      loadingItems,
      progress,
      currentItem: loadingItems[0]?.name || '완료',
    };
  }, [isLoadingCorp, isLoadingSignals, isLoadingSnapshot, isLoadingLoanInsight, corporation, apiSignals, snapshot, loanInsight]);

  // 초기 로딩 상태 (기업 정보)
  if (loadingState.isInitialLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="h-[calc(100vh-100px)] flex items-center justify-center relative z-10 px-4">
          <GlassCard className="p-12 w-full max-w-[520px] flex flex-col items-center gap-10 border-t-4 border-t-indigo-500 shadow-2xl backdrop-blur-2xl">

            {/* Icon & Title */}
            <div className="flex flex-col items-center gap-6 text-center">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-500/30 blur-2xl rounded-full scale-150" />
                <div className="relative bg-white/80 backdrop-blur-sm p-5 rounded-2xl shadow-xl border border-white/50 ring-1 ring-indigo-50">
                  <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                </div>
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">AI 분석 진행 중</h2>
                <p className="text-slate-500 text-lg font-medium">
                  <span className="font-semibold text-indigo-600">{corpId}</span>의 데이터를 종합 분석하고 있습니다.
                </p>
              </div>
            </div>

            {/* Progress Section */}
            <div className="w-full space-y-4">
              <div className="flex justify-between items-end px-1">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                  <span className="text-sm font-semibold text-slate-700">
                    {loadingState.currentItem}
                  </span>
                </div>
                <span className="text-sm font-bold text-indigo-600 font-mono tracking-wider">
                  {loadingState.progress}%
                </span>
              </div>

              <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden shadow-inner ring-1 ring-slate-200/50">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-indigo-400 rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                  style={{ width: `${loadingState.progress}%` }}
                >
                  <div className="absolute inset-0 w-full h-full bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.5)_50%,transparent_100%)] animate-[shimmer_1.5s_infinite]" />
                </div>
              </div>

              <p className="text-xs text-center text-slate-400 mt-4 leading-relaxed">
                글로벌 뉴스, 재무 데이터, 공급망 리스크 등<br />수천 개의 데이터 포인트를 실시간으로 교차 검증 중입니다.
              </p>
            </div>
          </GlassCard>
        </div>
      </MainLayout>
    );
  }

  if (!corporation) {
    return (
      <MainLayout>
        <div className="text-center py-16">
          <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">기업 정보를 찾을 수 없습니다.</p>
          <Button variant="outline" onClick={() => navigate(-1)} className="mt-4">
            돌아가기
          </Button>
        </div>
      </MainLayout>
    );
  }

  // API 시그널 카운트
  const signalCounts = apiSignals ? {
    direct: apiSignals.filter(s => s.signalCategory === 'direct').length,
    industry: apiSignals.filter(s => s.signalCategory === 'industry').length,
    environment: apiSignals.filter(s => s.signalCategory === 'environment').length,
  } : { direct: 0, industry: 0, environment: 0 };

  const currentDate = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* ============================================================ */}
        {/* Sticky Context Bar (개선안 C) */}
        {/* ============================================================ */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 -mx-4 px-4 py-2 mb-4 border-b border-border">
          {/* Row 1: Navigation + Title + Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                onClick={() => navigate(-1)}
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">{corporation.name}</span>
                <span className="text-muted-foreground">│</span>
                <span className="text-sm text-muted-foreground">시그널 분석 보고서</span>
                <span className="text-muted-foreground">│</span>
                <span className="text-xs text-muted-foreground">{currentDate}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5"
                onClick={() => setShowPreviewModal(true)}
                onMouseEnter={prefetchReport}
                onFocus={prefetchReport}
              >
                <FileDown className="w-3.5 h-3.5" />
                PDF
              </Button>
            </div>
          </div>
          {/* Row 2: Disclaimer Banner */}
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded px-3 py-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
            <span>본 보고서는 참고용이며 최종 심사 의견을 대체하지 않습니다.</span>
          </div>
        </div>

        {/* Report Document Style */}
        <div className="bg-card rounded-lg border border-border p-8 space-y-8">

          {/* Executive Summary - LLM 생성 또는 Fallback */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center justify-between">
              <span>요약 (Executive Summary)</span>
              {loanInsight?.insight && (
                <span className={`text-xs px-2 py-1 rounded ${loanInsight.insight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border border-red-200' :
                    loanInsight.insight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border border-orange-200' :
                      loanInsight.insight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border border-green-200' :
                        loanInsight.insight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border border-blue-200' :
                          'bg-gray-50 text-gray-600 border border-gray-200'
                  }`}>
                  {loanInsight.insight.stance.label}
                </span>
              )}
            </h2>
            <div className="text-sm text-muted-foreground space-y-2 leading-relaxed">
              {/* LLM 생성 Executive Summary 우선 사용 */}
              {loanInsight?.insight?.executive_summary ? (
                <p className="text-foreground">{loanInsight.insight.executive_summary}</p>
              ) : (
                /* Fallback: 기존 하드코딩 템플릿 */
                <>
                  <p>
                    <strong className="text-foreground">{corporation.name}</strong>은(는) {corporation.industry} 분야에서
                    사업을 영위하는 기업입니다.
                    {corporation.headquarters ? ` 본사는 ${corporation.headquarters}에 소재하고 있습니다.` : ''}
                  </p>
                  {corporation.bankRelationship.hasRelationship && (
                    <p>
                      당행과는 여신 {corporation.bankRelationship.loanBalance}, 수신 {corporation.bankRelationship.depositBalance} 규모의
                      거래 관계를 유지하고 있습니다.
                    </p>
                  )}
                </>
              )}
              {/* 시그널 카운트는 항상 표시 */}
              <p className="text-xs text-muted-foreground">
                탐지된 시그널: 직접 {signalCounts.direct}건, 산업 {signalCounts.industry}건, 환경 {signalCounts.environment}건
              </p>
            </div>
          </section>

          <Separator />

          {/* Company Profile */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              기업 개요
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex"><span className="w-28 text-muted-foreground">기업명</span><span>{corporation.name}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">사업자등록번호</span><span>{corporation.businessNumber || '-'}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">업종</span><span>{corporation.industry}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">업종코드</span><span>{corporation.industryCode}</span></div>
                {corporation.bizType && <div className="flex"><span className="w-28 text-muted-foreground">업태</span><span>{corporation.bizType}</span></div>}
              </div>
              <div className="space-y-2">
                <div className="flex"><span className="w-28 text-muted-foreground">대표이사</span><span>{corporation.ceo}</span></div>
                {corporation.corpRegNo && <div className="flex"><span className="w-28 text-muted-foreground">법인등록번호</span><span>{corporation.corpRegNo}</span></div>}
                {corporation.foundedYear > 0 && <div className="flex"><span className="w-28 text-muted-foreground">설립년도</span><span>{corporation.foundedYear}년</span></div>}
                {corporation.headquarters && <div className="flex"><span className="w-28 text-muted-foreground">본사 소재지</span><span>{corporation.headquarters}</span></div>}
                <div className="flex"><span className="w-28 text-muted-foreground">사업자 유형</span><span>{corporation.isCorporation ? '법인사업자' : '개인사업자'}</span></div>
              </div>
            </div>
          </section>

          <Separator />

          {/* Bank Relationship - 2행 압축 레이아웃 */}
          {(snapshot?.snapshot_json?.credit?.has_loan || corporation.bankRelationship.hasRelationship) && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
                <Landmark className="w-4 h-4" />
                당행 거래 현황
              </h2>
              {/* 연체 시 전체 카드에 경고 스타일 */}
              <div className={`rounded-lg border ${snapshot?.snapshot_json?.credit?.loan_summary?.overdue_flag ? 'border-red-200 bg-red-50/30' : 'border-border bg-muted/30'}`}>
                {/* 1행: 금액 정보 + 담보 */}
                <div className="flex items-center justify-between px-4 py-3 text-sm border-b border-border/50">
                  <div className="flex items-center gap-6">
                    <div>
                      <span className="text-muted-foreground text-xs">수신</span>
                      <span className="ml-2 font-medium">{corporation.bankRelationship.depositBalance || "-"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs">여신</span>
                      <span className="ml-2 font-medium">
                        {snapshot?.snapshot_json?.credit?.loan_summary?.total_exposure_krw
                          ? `${(snapshot.snapshot_json.credit.loan_summary.total_exposure_krw / 100000000).toFixed(0)}억원`
                          : corporation.bankRelationship.loanBalance || "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs">외환</span>
                      <span className="ml-2 font-medium">{corporation.bankRelationship.fxTransactions || "-"}</span>
                    </div>
                  </div>
                  {/* 담보 정보 (한글화) */}
                  {snapshot?.snapshot_json?.collateral?.has_collateral && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">담보</span>
                      {snapshot.snapshot_json.collateral.total_collateral_value_krw && (
                        <span className="font-medium">
                          {`${(snapshot.snapshot_json.collateral.total_collateral_value_krw / 100000000).toFixed(0)}억원`}
                        </span>
                      )}
                      <div className="flex gap-1">
                        {snapshot.snapshot_json.collateral.collateral_types?.map((type, i) => {
                          const typeMap: Record<string, string> = {
                            'REAL_ESTATE': '부동산',
                            'DEPOSIT': '예금',
                            'SECURITIES': '유가증권',
                            'INVENTORY': '재고',
                            'EQUIPMENT': '기계설비',
                            'RECEIVABLES': '매출채권',
                            'GUARANTEE': '보증',
                          };
                          return (
                            <span key={i} className="text-xs bg-muted px-1.5 py-0.5 rounded">
                              {typeMap[type] || type}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
                {/* 2행: 상태 배지들 + 갱신일 */}
                <div className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {/* KYC 상태 */}
                    {snapshot?.snapshot_json?.corp?.kyc_status && (
                      <>
                        <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.is_kyc_completed
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                          }`}>
                          {snapshot.snapshot_json.corp.kyc_status.is_kyc_completed ? 'KYC완료' : 'KYC미완료'}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'HIGH'
                          ? 'bg-red-100 text-red-700'
                          : snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'MED'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-green-100 text-green-700'
                          }`}>
                          {snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'HIGH' ? '고위험' :
                            snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'MED' ? '중위험' : '저위험'}
                        </span>
                      </>
                    )}
                    {/* 연체 발생 */}
                    {snapshot?.snapshot_json?.credit?.loan_summary?.overdue_flag && (
                      <span className="px-2 py-0.5 rounded text-xs bg-red-500 text-white font-medium">
                        연체발생
                      </span>
                    )}
                    {/* 부가서비스 */}
                    {corporation.bankRelationship.retirementPension && (
                      <span className="text-xs text-muted-foreground">퇴직연금</span>
                    )}
                    {corporation.bankRelationship.payrollService && (
                      <span className="text-xs text-muted-foreground">급여이체</span>
                    )}
                    {corporation.bankRelationship.corporateCard && (
                      <span className="text-xs text-muted-foreground">법인카드</span>
                    )}
                  </div>
                  {/* 갱신일 */}
                  {snapshot?.snapshot_json?.corp?.kyc_status?.last_kyc_updated && (
                    <span className="text-xs text-muted-foreground">
                      갱신: {snapshot.snapshot_json.corp.kyc_status.last_kyc_updated}
                    </span>
                  )}
                </div>
              </div>
            </section>
          )}

          <Separator />

          {/* ============================================================ */}
          {/* Loan Insight Section - AI 여신 참고 의견 (조건부: 여신 유무 확인) */}
          {/* ============================================================ */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileWarning className="w-4 h-4" />
                여신 참고 관점 요약 (AI Risk Opinion)
              </span>
              {loanInsight?.insight && (
                <span className={`text-xs px-2 py-1 rounded ${loanInsight.insight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border border-red-200' :
                    loanInsight.insight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border border-orange-200' :
                      loanInsight.insight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border border-green-200' :
                        loanInsight.insight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border border-blue-200' :
                          'bg-gray-50 text-gray-600 border border-gray-200'
                  }`}>
                  {loanInsight.insight.stance.label}
                </span>
              )}
            </h2>

            {isLoadingLoanInsight ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
                <span className="text-sm text-muted-foreground">여신 정보를 확인하는 중...</span>
              </div>
            ) : loanInsight && !loanInsight.has_loan ? (
              /* 여신이 없는 경우 */
              <div className="bg-gray-50 rounded-lg p-6 text-center border border-gray-200">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
                  <FileWarning className="w-6 h-6 text-gray-400" />
                </div>
                <p className="text-sm font-medium text-gray-600">당행 여신이 없습니다</p>
                <p className="text-xs text-muted-foreground mt-1">해당 기업에 대한 여신 거래가 없어 AI 분석이 제공되지 않습니다.</p>
              </div>
            ) : loanInsight && loanInsight.has_loan && !loanInsight.insight ? (
              /* 여신은 있지만 분석이 아직 안 된 경우 */
              <div className="bg-blue-50 rounded-lg p-6 text-center border border-blue-200">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-3" />
                <p className="text-sm font-medium text-blue-700">분석 중입니다</p>
                <p className="text-xs text-blue-600 mt-1">
                  여신 금액: {((loanInsight.total_exposure_krw || 0) / 100000000).toFixed(1)}억원
                </p>
                <p className="text-xs text-muted-foreground mt-2">잠시 후 페이지를 새로고침해 주세요.</p>
              </div>
            ) : loanInsight?.insight ? (
              <div className="bg-slate-50 rounded-lg p-5 border border-slate-200 space-y-5">
                {/* 2x2 Grid: 리스크/기회 요인 */}
                <div className="grid grid-cols-2 gap-6">
                  {/* Risk Drivers */}
                  <div>
                    <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center">
                      <AlertTriangle className="w-4 h-4 mr-2" />
                      핵심 리스크 요인
                    </h3>
                    <ul className="space-y-2">
                      {loanInsight.insight.key_risks.length > 0 ? (
                        loanInsight.insight.key_risks.map((risk, idx) => (
                          <li key={idx} className="text-sm text-foreground/80 flex items-start">
                            <span className="text-red-500 mr-2">•</span>
                            {risk}
                          </li>
                        ))
                      ) : (
                        <li className="text-sm text-muted-foreground italic">식별된 심각한 리스크가 없습니다.</li>
                      )}
                    </ul>
                  </div>

                  {/* Key Opportunities */}
                  <div>
                    <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center">
                      <TrendingUp className="w-4 h-4 mr-2" />
                      핵심 기회 요인
                    </h3>
                    <ul className="space-y-2">
                      {(loanInsight.insight.key_opportunities?.length > 0) ? (
                        loanInsight.insight.key_opportunities.map((opp, idx) => (
                          <li key={idx} className="text-sm text-foreground/80 flex items-start">
                            <span className="text-green-500 mr-2">•</span>
                            {opp}
                          </li>
                        ))
                      ) : (
                        <li className="text-sm text-muted-foreground italic">식별된 기회 요인이 없습니다.</li>
                      )}
                    </ul>
                  </div>
                </div>

                {/* Mitigating Factors - 상쇄 요인이 있을 때만 표시 */}
                {loanInsight.insight.mitigating_factors.length > 0 && (
                  <div className="pt-4 border-t border-slate-200">
                    <h3 className="text-sm font-semibold text-blue-700 mb-3 flex items-center">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      리스크 상쇄 요인
                    </h3>
                    <ul className="space-y-2">
                      {loanInsight.insight.mitigating_factors.map((factor, idx) => (
                        <li key={idx} className="text-sm text-foreground/80 flex items-start">
                          <span className="text-blue-500 mr-2">•</span>
                          {factor}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Items */}
                <div className="pt-4 border-t border-slate-200">
                  <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center">
                    <Search className="w-4 h-4 mr-2" />
                    심사역 확인 체크리스트
                  </h3>
                  <div className="space-y-2 bg-white p-3 rounded border border-slate-200">
                    {loanInsight.insight.action_items.length > 0 ? (
                      loanInsight.insight.action_items.map((item, idx) => (
                        <div key={idx} className="flex items-start text-sm">
                          <div className="mr-3 pt-0.5">
                            <div className="w-4 h-4 border-2 border-slate-300 rounded-sm"></div>
                          </div>
                          <span className="text-foreground/90">{item}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">추가 확인이 필요한 특이사항이 없습니다.</p>
                    )}
                  </div>
                </div>

                {/* Metadata */}
                <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-slate-200">
                  <span>
                    시그널 {loanInsight.insight.signal_count}건 분석 (위험 {loanInsight.insight.risk_count}, 기회 {loanInsight.insight.opportunity_count})
                  </span>
                  <span className="flex items-center gap-2">
                    {loanInsight.insight.is_fallback && (
                      <span className="text-orange-500">Rule-based</span>
                    )}
                    {loanInsight.insight.generation_model && (
                      <span>모델: {loanInsight.insight.generation_model}</span>
                    )}
                    <span>생성: {new Date(loanInsight.insight.generated_at).toLocaleDateString('ko-KR')}</span>
                  </span>
                </div>

                <p className="italic text-xs text-muted-foreground text-right">
                  * 본 의견은 AI 모델이 생성한 참고 자료이며, 은행의 공식 심사 의견을 대체하지 않습니다.
                </p>
              </div>
            ) : null}
          </section>

          <Separator />

          {/* ============================================================ */}
          {/* Corp Profile Section - 기업 인텔리전스 (방안 3: 2단 레이아웃) */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Zap className="w-4 h-4" />
                기업 인텔리전스
              </h2>
              <div className="flex items-center gap-2">
                {profile && profile.profile_confidence !== 'LOW' && (
                  <span className={`text-xs px-2 py-1 rounded ${getConfidenceBadge(profile.profile_confidence).bg} ${getConfidenceBadge(profile.profile_confidence).text}`}>
                    {getConfidenceBadge(profile.profile_confidence).label}
                  </span>
                )}
                {refreshStatus === 'running' && (
                  <span className="text-xs text-blue-600 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    분석 중...
                  </span>
                )}
                {refreshStatus === 'done' && (
                  <span className="text-xs text-green-600 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    완료
                  </span>
                )}
                {refreshStatus === 'failed' && (
                  <span className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    실패
                  </span>
                )}
                {/* 기본/상세 뷰 토글 */}
                {profile && (
                  <Button
                    variant={showDetailedView ? "default" : "outline"}
                    size="sm"
                    className="gap-1"
                    onClick={() => setShowDetailedView(!showDetailedView)}
                  >
                    <FileText className="w-3 h-3" />
                    {showDetailedView ? '기본 뷰' : '상세 뷰'}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={handleRefreshProfile}
                  disabled={refreshProfile.isPending || isLoadingProfile || refreshStatus === 'running'}
                >
                  <RefreshCw className={`w-3 h-3 ${(refreshProfile.isPending || refreshStatus === 'running') ? 'animate-spin' : ''}`} />
                  정보 갱신
                </Button>
              </div>
            </div>

            {(isLoadingProfile || refreshStatus === 'running') ? (
              <div className="flex flex-col items-center justify-center py-8 px-4">
                {refreshStatus === 'running' ? (
                  <>
                    {/* Progress Bar with Step Info */}
                    <div className="w-full max-w-md mb-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-foreground">
                          {getJobProgress(jobStatus?.progress?.step).label}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {getJobProgress(jobStatus?.progress?.step).progress}%
                        </span>
                      </div>
                      <Progress
                        value={getJobProgress(jobStatus?.progress?.step).progress}
                        className="h-2"
                      />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>AI가 기업 정보를 분석하고 있습니다...</span>
                    </div>
                    <span className="text-xs text-muted-foreground mt-2">
                      약 30초~1분 정도 소요될 수 있습니다.
                    </span>
                  </>
                ) : (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mb-2" />
                    <span className="text-sm text-muted-foreground">
                      외부 정보를 불러오는 중...
                    </span>
                  </>
                )}
              </div>
            ) : profileError ? (
              <div className="flex flex-col items-center justify-center py-8 text-sm text-muted-foreground">
                {/* @ts-ignore - error structure may vary */}
                {(profileError as any)?.response?.data?.detail?.error_code === 'PROFILE_NOT_FOUND' ||
                  (profileError as any)?.message?.includes('404') ? (
                  <>
                    <AlertCircle className="w-5 h-5 mb-2 text-orange-500" />
                    <span>외부 정보가 아직 생성되지 않았습니다.</span>
                    <span className="text-xs mt-1">"정보 갱신" 버튼을 클릭하여 생성해 주세요.</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-5 h-5 mb-2 text-red-500" />
                    <span>외부 정보를 불러오는 중 오류가 발생했습니다.</span>
                    <span className="text-xs mt-1">잠시 후 다시 시도해 주세요.</span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() => refetchProfile()}
                    >
                      다시 시도
                    </Button>
                  </>
                )}
              </div>
            ) : profile ? (
              <div className="space-y-4">
                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                {/* 사업 개요 (Full Width) */}
                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-2">사업 개요</h3>
                  {profile.business_summary ? (
                    <p className="text-sm text-muted-foreground leading-relaxed">{profile.business_summary}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">-</p>
                  )}
                  {/* 핵심 지표 inline */}
                  <div className="mt-3 pt-3 border-t border-slate-200 flex flex-wrap items-center gap-6 text-sm">
                    <div>
                      <span className="text-muted-foreground">연간 매출</span>
                      <span className="ml-2 font-medium">{profile.revenue_krw ? formatKRW(profile.revenue_krw) : '-'}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">수출 비중</span>
                      <span className="ml-2 font-medium">{typeof profile.export_ratio_pct === 'number' ? `${profile.export_ratio_pct}%` : '-'}</span>
                    </div>
                    {profile.employee_count && (
                      <div>
                        <span className="text-muted-foreground">임직원수</span>
                        <span className="ml-2 font-medium">{profile.employee_count.toLocaleString()}명</span>
                      </div>
                    )}
                    {profile.business_model && (
                      <div>
                        <span className="text-muted-foreground">비즈니스</span>
                        <span className="ml-2 font-medium">{profile.business_model}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                {/* 2단 레이아웃: 밸류체인 | 시장 포지션 */}
                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                <div className="grid grid-cols-2 gap-4">
                  {/* 좌측: 밸류체인 */}
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-4">
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <Package className="w-4 h-4 text-slate-500" />
                      밸류체인
                    </h3>

                    {/* 공급사 */}
                    <div>
                      <span className="text-xs text-muted-foreground">공급사</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.supply_chain?.key_suppliers?.length > 0 ? (
                          profile.supply_chain.key_suppliers.map((s, i) => (
                            <span key={i} className="text-xs bg-white border px-2 py-0.5 rounded">{s}</span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 고객사 */}
                    <div>
                      <span className="text-xs text-muted-foreground">고객사</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.key_customers?.length > 0 ? (
                          profile.key_customers.map((c, i) => (
                            <span key={i} className="text-xs bg-white border px-2 py-0.5 rounded">{c}</span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 원자재 */}
                    <div>
                      <span className="text-xs text-muted-foreground">주요 원자재</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.key_materials?.length > 0 ? (
                          profile.key_materials.map((m, i) => (
                            <span key={i} className="text-xs bg-white border px-2 py-0.5 rounded">{m}</span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 단일 조달처 위험 */}
                    {profile.supply_chain?.single_source_risk?.length > 0 && (
                      <div className="pt-2 border-t border-slate-200">
                        <span className="text-xs text-red-600 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          단일 조달처 위험
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {profile.supply_chain.single_source_risk.map((r, i) => (
                            <span key={i} className="text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded">{r}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 국가 비중 */}
                    <div className="pt-2 border-t border-slate-200">
                      <span className="text-xs text-muted-foreground">공급 국가 비중</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.keys(profile.supply_chain?.supplier_countries || {}).length > 0 ? (
                          Object.entries(profile.supply_chain!.supplier_countries).map(([country, pct]) => (
                            <span key={country} className="text-xs bg-orange-50 text-orange-700 px-2 py-0.5 rounded">
                              {country} {pct}%
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 우측: 시장 포지션 */}
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-4">
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <Target className="w-4 h-4 text-slate-500" />
                      시장 포지션
                    </h3>

                    {/* 경쟁사 */}
                    <div>
                      <span className="text-xs text-muted-foreground">경쟁사</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.competitors?.length > 0 ? (
                          profile.competitors.map((c, i) => (
                            <span key={i} className="text-xs bg-white border px-2 py-0.5 rounded">{c.name}</span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 거시 요인 */}
                    <div className="pt-2 border-t border-slate-200">
                      <span className="text-xs text-muted-foreground">거시 요인</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.macro_factors?.length > 0 ? (
                          profile.macro_factors.map((f, i) => (
                            <span
                              key={i}
                              className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${f.impact === 'POSITIVE' ? 'bg-green-50 text-green-700 border border-green-200' :
                                  f.impact === 'NEGATIVE' ? 'bg-red-50 text-red-700 border border-red-200' :
                                    'bg-slate-100 text-slate-700 border border-slate-200'
                                }`}
                            >
                              {f.impact === 'POSITIVE' && <TrendingUp className="w-3 h-3" />}
                              {f.impact === 'NEGATIVE' && <AlertTriangle className="w-3 h-3" />}
                              {f.factor}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 주요 주주 */}
                    <div className="pt-2 border-t border-slate-200">
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        주요 주주
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {profile.shareholders?.length > 0 ? (
                          profile.shareholders.map((sh, i) => (
                            <span key={i} className="text-xs bg-white border px-2 py-0.5 rounded">
                              {sh.name} ({sh.ownership_pct}%)
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </div>

                    {/* 해외 사업 */}
                    {(profile.overseas_business?.subsidiaries?.length > 0 || profile.overseas_business?.manufacturing_countries?.length > 0) && (
                      <div className="pt-2 border-t border-slate-200">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Factory className="w-3 h-3" />
                          해외 사업
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {profile.overseas_business?.subsidiaries?.map((sub, i) => (
                            <span key={i} className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded">
                              {sub.name} ({sub.country})
                            </span>
                          ))}
                          {profile.overseas_business?.manufacturing_countries?.map((c, i) => (
                            <span key={`mfg-${i}`} className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded">
                              생산: {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                {/* 글로벌 노출 (Full Width) */}
                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                {profile.country_exposure && Object.keys(profile.country_exposure).length > 0 && (
                  <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                    <Globe className="w-4 h-4 text-blue-600 flex-shrink-0" />
                    <span className="text-sm text-blue-900 font-medium">글로벌 노출:</span>
                    <div className="flex gap-2">
                      {Object.entries(profile.country_exposure).map(([country, pct]) => (
                        <span key={country} className="text-sm text-blue-700">
                          {country} {pct}%
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                {/* 출처 & 메타데이터 (Collapsed Footer) */}
                {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
                <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
                  <div className="flex items-center gap-3">
                    {profile.source_urls?.length > 0 && (
                      <span className="flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" />
                        출처 {profile.source_urls.length}개
                      </span>
                    )}
                    <span>갱신: {profile.fetched_at ? new Date(profile.fetched_at).toLocaleDateString('ko-KR') : '-'}</span>
                    {profile.expires_at && (
                      <span>만료: {new Date(profile.expires_at).toLocaleDateString('ko-KR')}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {profile.is_fallback && (
                      <span className="text-orange-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Fallback
                      </span>
                    )}
                    {profile.consensus_metadata?.fallback_layer !== undefined && profile.consensus_metadata.fallback_layer !== 0 && (
                      <span className="text-xs bg-slate-100 px-2 py-0.5 rounded">
                        {typeof profile.consensus_metadata.fallback_layer === 'string'
                          ? profile.consensus_metadata.fallback_layer.replace(/_/g, ' ')
                          : `Layer ${profile.consensus_metadata.fallback_layer}`}
                      </span>
                    )}
                  </div>
                </div>

                {/* ============================================================ */}
                {/* 상세 뷰: Evidence Map + Risk Indicators */}
                {/* ============================================================ */}
                {showDetailedView && (
                  <div className="space-y-6 pt-4 border-t border-border">
                    <EvidenceMap
                      fieldProvenance={profileDetail?.field_provenance || {}}
                      fieldConfidences={profileDetail?.field_confidences || {}}
                      sourceUrls={profileDetail?.source_urls || []}
                      consensusMetadata={profileDetail?.consensus_metadata ? {
                        perplexity_success: profileDetail.consensus_metadata.perplexity_success,
                        gemini_success: profileDetail.consensus_metadata.gemini_success,
                        claude_success: profileDetail.consensus_metadata.claude_success,
                        total_fields: profileDetail.consensus_metadata.total_fields,
                        matched_fields: profileDetail.consensus_metadata.matched_fields,
                        discrepancy_fields: profileDetail.consensus_metadata.discrepancy_fields,
                        fallback_layer: profileDetail.consensus_metadata.fallback_layer,
                      } : undefined}
                    />

                    {profileDetail && (
                      <RiskIndicators
                        profile={profileDetail as unknown as CorpProfile}
                        industryCode={corporation?.industryCode}
                      />
                    )}

                    {profileDetail && (
                      <div className="p-3 bg-muted/30 rounded-lg">
                        <div className="text-xs text-muted-foreground space-y-1">
                          <div className="flex items-center gap-4">
                            <span>추출 모델: {profileDetail.extraction_model || '-'}</span>
                            <span>프롬프트 버전: {profileDetail.extraction_prompt_version || '-'}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span>생성: {profileDetail.created_at ? new Date(profileDetail.created_at).toLocaleString('ko-KR') : '-'}</span>
                            <span>수정: {profileDetail.updated_at ? new Date(profileDetail.updated_at).toLocaleString('ko-KR') : '-'}</span>
                          </div>
                          {profileDetail.validation_warnings && profileDetail.validation_warnings.length > 0 && (
                            <div className="mt-2 text-orange-600">
                              검증 경고: {profileDetail.validation_warnings.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : null}
          </section>

          {/* Disclaimer */}
          <div className="mt-8 pt-6 border-t-2 border-border">
            <div className="bg-muted p-4 rounded text-xs text-muted-foreground leading-relaxed">
              본 보고서는 RKYC 시스템이 감지한 시그널을 기반으로 생성된 참고 자료입니다.
              자동 판단, 점수화, 예측 또는 조치를 의미하지 않으며,
              최종 판단은 담당자 및 관련 조직의 책임 하에 이루어집니다.
            </div>
          </div>
        </div>
      </div>

      <ReportPreviewModal
        open={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        corporationId={corporation.id}
      />
    </MainLayout>
  );
}
