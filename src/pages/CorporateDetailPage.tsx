import { useParams, useNavigate } from "react-router-dom";
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
import { useState, useEffect } from "react";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import { useCorporation, useSignals, useCorporationSnapshot, useCorpProfile, useCorpProfileDetail, useRefreshCorpProfile, useJobStatus, useLoanInsight } from "@/hooks/useApi";
import type { ProfileConfidence, CorpProfile } from "@/types/profile";
import { useQueryClient } from "@tanstack/react-query";
import { getCorporationReport } from "@/lib/api";
import { EvidenceBackedField } from "@/components/profile/EvidenceBackedField";
import { EvidenceMap } from "@/components/profile/EvidenceMap";
import { RiskIndicators } from "@/components/profile/RiskIndicators";

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
  const { corporateId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [refreshStatus, setRefreshStatus] = useState<'idle' | 'running' | 'done' | 'failed'>('idle');

  // API 훅 사용
  const { data: corporation, isLoading: isLoadingCorp } = useCorporation(corporateId || "");
  const { data: apiSignals, isLoading: isLoadingSignals } = useSignals({ corp_id: corporateId });
  const { data: snapshot, isLoading: isLoadingSnapshot } = useCorporationSnapshot(corporateId || "");
  const { data: profile, isLoading: isLoadingProfile, error: profileError, refetch: refetchProfile } = useCorpProfile(corporateId || "");
  // 상세 프로필 (field_provenance 포함) - 기본 뷰 / 상세 뷰 토글용
  // P1-3 Fix: Add error handling for profileDetail
  const { data: profileDetail, error: profileDetailError, refetch: refetchProfileDetail } = useCorpProfileDetail(corporateId || "");
  // Loan Insight (사전 생성된 AI 분석)
  const { data: loanInsight, isLoading: isLoadingLoanInsight, error: loanInsightError } = useLoanInsight(corporateId || "");
  const refreshProfile = useRefreshCorpProfile();
  const [showDetailedView, setShowDetailedView] = useState(false);

  // 보고서 데이터 프리페칭 (hover 시 미리 로드)
  const prefetchReport = () => {
    if (corporateId) {
      queryClient.prefetchQuery({
        queryKey: ['report', corporateId],
        queryFn: () => getCorporationReport(corporateId),
        staleTime: 10 * 60 * 1000, // 10분
      });
    }
  };

  // Job 상태 폴링
  const { data: jobStatus } = useJobStatus(refreshJobId || '', {
    enabled: !!refreshJobId && refreshStatus === 'running',
  });

  // Job 완료 시 프로필 + Loan Insight 다시 로드
  useEffect(() => {
    if (jobStatus?.status === 'DONE') {
      setRefreshStatus('done');
      setRefreshJobId(null);
      // 프로필 쿼리 무효화하여 다시 로드 (기본 + 상세)
      queryClient.invalidateQueries({ queryKey: ['corporation', corporateId, 'profile'] });
      queryClient.invalidateQueries({ queryKey: ['corporation', corporateId, 'profile', 'detail'] });
      // Loan Insight도 갱신
      queryClient.invalidateQueries({ queryKey: ['loan-insight', corporateId] });
    } else if (jobStatus?.status === 'FAILED') {
      setRefreshStatus('failed');
      setRefreshJobId(null);
    }
  }, [jobStatus?.status, queryClient, corporateId]);

  // 정보 갱신 버튼 핸들러
  const handleRefreshProfile = async () => {
    if (!corporateId) return;
    setRefreshStatus('running');

    try {
      const result = await refreshProfile.mutateAsync(corporateId);
      if (result.status === 'QUEUED' && result.job_id) {
        setRefreshJobId(result.job_id);
      } else if (result.status === 'FAILED') {
        setRefreshStatus('failed');
      }
    } catch (error) {
      console.error('Profile refresh failed:', error);
      setRefreshStatus('failed');
    }
  };

  // 로딩 상태
  if (isLoadingCorp) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-primary mr-2" />
          <span className="text-muted-foreground">기업 정보를 불러오는 중...</span>
        </div>
      </MainLayout>
    );
  }

  if (!corporation) {
    return (
      <MainLayout>
        <div className="text-center py-16">
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
        {/* Back & Actions */}
        <div className="flex items-center justify-between mb-4">
          <Button
            variant="ghost"
            className="-ml-2 text-muted-foreground hover:text-foreground"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            이전 페이지
          </Button>
          <Button
            size="sm"
            className="gap-2"
            onClick={() => setShowPreviewModal(true)}
            onMouseEnter={prefetchReport}
            onFocus={prefetchReport}
          >
            <FileDown className="w-4 h-4" />
            PDF 내보내기
          </Button>
        </div>

        {/* Report Document Style */}
        <div className="bg-card rounded-lg border border-border p-8 space-y-8">

          {/* Report Header */}
          <div className="text-center border-b border-border pb-6">
            <h1 className="text-xl font-bold text-foreground mb-2">
              RKYC 기업 시그널 분석 보고서 (참고용)
            </h1>
            <div className="text-lg font-semibold text-foreground mb-4">{corporation.name}</div>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>보고서 생성일: {currentDate}</p>
              <p>생성 시스템: RKYC (Really Know Your Customer Intelligence)</p>
            </div>
            <div className="mt-4 inline-block px-3 py-1.5 bg-muted rounded text-xs text-muted-foreground">
              본 보고서는 참고 및 검토용 자료입니다.
            </div>
          </div>

          {/* Executive Summary - LLM 생성 또는 Fallback */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center justify-between">
              <span>요약 (Executive Summary)</span>
              {loanInsight && (
                <span className={`text-xs px-2 py-1 rounded ${
                  loanInsight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border border-red-200' :
                  loanInsight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border border-orange-200' :
                  loanInsight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border border-green-200' :
                  loanInsight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border border-blue-200' :
                  'bg-gray-50 text-gray-600 border border-gray-200'
                }`}>
                  {loanInsight.stance.label}
                </span>
              )}
            </h2>
            <div className="text-sm text-muted-foreground space-y-2 leading-relaxed">
              {/* LLM 생성 Executive Summary 우선 사용 */}
              {loanInsight?.executive_summary ? (
                <p className="text-foreground">{loanInsight.executive_summary}</p>
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
          {/* Loan Insight Section - AI 여신 참고 의견 */}
          {/* ============================================================ */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileWarning className="w-4 h-4" />
                여신 참고 관점 요약 (AI Risk Opinion)
              </span>
              {loanInsight && (
                <span className={`text-xs px-2 py-1 rounded ${
                  loanInsight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border border-red-200' :
                  loanInsight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border border-orange-200' :
                  loanInsight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border border-green-200' :
                  loanInsight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border border-blue-200' :
                  'bg-gray-50 text-gray-600 border border-gray-200'
                }`}>
                  {loanInsight.stance.label}
                </span>
              )}
            </h2>

            {isLoadingLoanInsight ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
                <span className="text-sm text-muted-foreground">AI 분석 결과를 불러오는 중...</span>
              </div>
            ) : loanInsightError ? (
              <div className="bg-muted/30 rounded-lg p-4 text-center">
                <AlertCircle className="w-5 h-5 text-orange-500 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">AI 분석이 아직 생성되지 않았습니다.</p>
                <p className="text-xs text-muted-foreground mt-1">"정보 갱신" 버튼을 클릭하면 자동 생성됩니다.</p>
              </div>
            ) : loanInsight ? (
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
                      {loanInsight.key_risks.length > 0 ? (
                        loanInsight.key_risks.map((risk, idx) => (
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
                      {(loanInsight.key_opportunities?.length > 0) ? (
                        loanInsight.key_opportunities.map((opp, idx) => (
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
                {loanInsight.mitigating_factors.length > 0 && (
                  <div className="pt-4 border-t border-slate-200">
                    <h3 className="text-sm font-semibold text-blue-700 mb-3 flex items-center">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      리스크 상쇄 요인
                    </h3>
                    <ul className="space-y-2">
                      {loanInsight.mitigating_factors.map((factor, idx) => (
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
                    {loanInsight.action_items.length > 0 ? (
                      loanInsight.action_items.map((item, idx) => (
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
                    시그널 {loanInsight.signal_count}건 분석 (위험 {loanInsight.risk_count}, 기회 {loanInsight.opportunity_count})
                  </span>
                  <span className="flex items-center gap-2">
                    {loanInsight.is_fallback && (
                      <span className="text-orange-500">Rule-based</span>
                    )}
                    {loanInsight.generation_model && (
                      <span>모델: {loanInsight.generation_model}</span>
                    )}
                    <span>생성: {new Date(loanInsight.generated_at).toLocaleDateString('ko-KR')}</span>
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
          {/* Corp Profile Section (PRD v1.2) - 근거 강화 */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Globe className="w-4 h-4" />
                외부 정보 프로필
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
              <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mb-2" />
                <span className="text-sm text-muted-foreground">
                  {refreshStatus === 'running' ? '프로필 생성 중...' : '외부 정보를 불러오는 중...'}
                </span>
                {refreshStatus === 'running' && jobStatus && (
                  <span className="text-xs text-muted-foreground mt-1">
                    {jobStatus.progress?.step || '대기 중'}
                  </span>
                )}
              </div>
            ) : profileError ? (
              // P2-3 Fix: error_code 기반 에러 분기
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
              <div className="space-y-6">
                {/* Business Summary - P0-2 Fix: 빈 섹션 '정보 없음' 메시지 */}
                <div className="bg-muted/30 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-muted-foreground" />
                    사업 개요
                  </h3>
                  {profile.business_summary ? (
                    <p className="text-sm text-muted-foreground leading-relaxed">{profile.business_summary}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">정보 없음</p>
                  )}
                </div>

                {/* Basic Info Grid - P0-2 Fix: typeof로 안전한 NULL 체크 */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-2">
                    <div className="flex">
                      <span className="w-28 flex-shrink-0 text-muted-foreground">연간 매출</span>
                      <span className="font-medium">{profile.revenue_krw ? formatKRW(profile.revenue_krw) : '-'}</span>
                    </div>
                    <div className="flex">
                      <span className="w-28 flex-shrink-0 text-muted-foreground">수출 비중</span>
                      <span className="font-medium">{typeof profile.export_ratio_pct === 'number' ? `${profile.export_ratio_pct}%` : '-'}</span>
                    </div>
                    <div className="flex">
                      <span className="w-28 flex-shrink-0 text-muted-foreground">임직원 수</span>
                      <span>{profile.employee_count ? `${profile.employee_count.toLocaleString()}명` : '-'}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex">
                      <span className="w-28 flex-shrink-0 text-muted-foreground">본사 위치</span>
                      <span>{profile.headquarters || '-'}</span>
                    </div>
                  </div>
                </div>

                {/* Business Model - 긴 텍스트를 위한 별도 섹션 */}
                {profile.business_model && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">비즈니스 모델</span>
                    <p className="mt-1 text-foreground leading-relaxed">{profile.business_model}</p>
                  </div>
                )}

                {/* Country Exposure - P0-2 Fix: 빈 섹션 처리 */}
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-muted-foreground" />
                    국가별 노출
                  </h3>
                  {profile.country_exposure && Object.keys(profile.country_exposure).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(profile.country_exposure).map(([country, pct]) => (
                        <span key={country} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                          {country} {pct}%
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">정보 없음</p>
                  )}
                </div>

                {/* Supply Chain - P0-2 Fix: 빈 섹션 처리 */}
                <div className="bg-muted/30 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
                    <Package className="w-4 h-4 text-muted-foreground" />
                    공급망 정보
                  </h3>
                  {profile.supply_chain && (profile.supply_chain.key_suppliers?.length > 0 || Object.keys(profile.supply_chain.supplier_countries || {}).length > 0) ? (
                    <div className="space-y-3">
                      {profile.supply_chain.key_suppliers.length > 0 && (
                        <div>
                          <span className="text-xs text-muted-foreground">주요 공급사</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {profile.supply_chain.key_suppliers.map((supplier, i) => (
                              <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{supplier}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {Object.keys(profile.supply_chain.supplier_countries).length > 0 && (
                        <div>
                          <span className="text-xs text-muted-foreground">공급사 국가 비중</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {Object.entries(profile.supply_chain.supplier_countries).map(([country, pct]) => (
                              <span key={country} className="text-xs bg-orange-50 text-orange-700 px-2 py-0.5 rounded">
                                {country} {pct}%
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {profile.supply_chain.single_source_risk.length > 0 && (
                        <div>
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <AlertCircle className="w-3 h-3 text-red-500" />
                            단일 조달처 위험
                          </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {profile.supply_chain.single_source_risk.map((item, i) => (
                              <span key={i} className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded">{item}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {typeof profile.supply_chain.material_import_ratio_pct === 'number' && (
                        <div className="text-xs">
                          <span className="text-muted-foreground">원자재 수입 비율: </span>
                          <span className="font-medium">{profile.supply_chain.material_import_ratio_pct}%</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">정보 없음</p>
                  )}
                </div>

                {/* Overseas Business - P0-2 Fix: 빈 섹션 처리 */}
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Factory className="w-4 h-4 text-muted-foreground" />
                    해외 사업
                  </h3>
                  {profile.overseas_business && (profile.overseas_business.subsidiaries?.length > 0 || profile.overseas_business.manufacturing_countries?.length > 0) ? (
                    <>
                    {profile.overseas_business.subsidiaries?.length > 0 && (
                      <div className="mb-2">
                        <span className="text-xs text-muted-foreground">해외 법인</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {profile.overseas_business.subsidiaries.map((sub, i) => (
                            <span key={i} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded">
                              {sub.name} ({sub.country})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {profile.overseas_business.manufacturing_countries?.length > 0 && (
                      <div>
                        <span className="text-xs text-muted-foreground">생산 국가</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {profile.overseas_business.manufacturing_countries.map((country, i) => (
                            <span key={i} className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded">{country}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">정보 없음</p>
                  )}
                </div>

                {/* Key Materials & Customers - P0-2 Fix: 빈 섹션 '정보 없음' */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-foreground mb-2">주요 원자재</h3>
                    {profile.key_materials?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {profile.key_materials.map((mat, i) => (
                          <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{mat}</span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">정보 없음</p>
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-foreground mb-2">주요 고객사</h3>
                    {profile.key_customers?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {profile.key_customers.map((cust, i) => (
                          <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{cust}</span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">정보 없음</p>
                    )}
                  </div>
                </div>

                {/* Competitors & Macro Factors - P0-2 Fix: 빈 섹션 '정보 없음' */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-muted-foreground" />
                      경쟁사
                    </h3>
                    {profile.competitors?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {profile.competitors.map((comp, i) => (
                          <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{comp.name}</span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">정보 없음</p>
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-foreground mb-2">거시 요인</h3>
                    {profile.macro_factors?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {profile.macro_factors.map((factor, i) => (
                          <span
                            key={i}
                            className={`text-xs px-2 py-0.5 rounded ${
                              factor.impact === 'POSITIVE' ? 'bg-green-50 text-green-700' :
                              factor.impact === 'NEGATIVE' ? 'bg-red-50 text-red-700' :
                              'bg-gray-50 text-gray-700'
                            }`}
                          >
                            {factor.factor}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">정보 없음</p>
                    )}
                  </div>
                </div>

                {/* Shareholders - P0-2 Fix: 빈 섹션 '정보 없음' */}
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Users className="w-4 h-4 text-muted-foreground" />
                    주요 주주
                  </h3>
                  {profile.shareholders?.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {profile.shareholders.map((sh, i) => (
                        <span key={i} className="text-xs bg-muted px-2 py-1 rounded">
                          {sh.name} ({sh.ownership_pct}%)
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">정보 없음</p>
                  )}
                </div>

                {/* Source URLs & Metadata */}
                <div className="pt-3 border-t border-border">
                  <h3 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    출처
                  </h3>
                  {profile.source_urls?.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {profile.source_urls.slice(0, 5).map((url, i) => (
                        <a
                          key={i}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline truncate max-w-[200px]"
                        >
                          {url.replace(/^https?:\/\//, '').split('/')[0]}
                        </a>
                      ))}
                      {profile.source_urls.length > 5 && (
                        <span className="text-xs text-muted-foreground">+{profile.source_urls.length - 5}개</span>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">출처 정보 없음</p>
                  )}
                  <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                    {/* P1-2 Fix: NULL 체크 및 '만료일 없음' 표시 */}
                    <span>갱신: {profile.fetched_at ? new Date(profile.fetched_at).toLocaleDateString('ko-KR') : '-'}</span>
                    <span>만료: {profile.expires_at ? new Date(profile.expires_at).toLocaleDateString('ko-KR') : '만료일 없음'}</span>
                    {profile.is_fallback && (
                      <span className="text-orange-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Fallback 데이터
                      </span>
                    )}
                    {profile.consensus_metadata?.fallback_layer !== undefined && profile.consensus_metadata.fallback_layer > 0 && (
                      <span className="text-xs text-muted-foreground">
                        Layer {profile.consensus_metadata.fallback_layer}
                      </span>
                    )}
                  </div>
                </div>

                {/* ============================================================ */}
                {/* 상세 뷰: Evidence Map + Risk Indicators */}
                {/* ============================================================ */}
                {showDetailedView && (
                  <div className="space-y-6 pt-4 border-t border-border">
                    {/* P1-3 Fix: Show EvidenceMap even if profileDetail is loading or has error */}
                    {/* Evidence Map - 근거-주장 연결 */}
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

                    {/* Risk Indicators - 조기경보 + 체크리스트 */}
                    {profileDetail && (
                      <RiskIndicators
                        profile={profileDetail as unknown as CorpProfile}
                        industryCode={corporation?.industryCode}
                      />
                    )}

                    {/* 메타데이터 상세 */}
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
