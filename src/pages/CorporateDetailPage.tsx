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
  Link2,
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
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useState, useEffect } from "react";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import { useCorporation, useSignals, useCorporationSnapshot, useCorpProfile, useRefreshCorpProfile, useJobStatus } from "@/hooks/useApi";
import type { ProfileConfidence } from "@/types/profile";
import { useQueryClient } from "@tanstack/react-query";

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
  const refreshProfile = useRefreshCorpProfile();

  // Job 상태 폴링
  const { data: jobStatus } = useJobStatus(refreshJobId || '', {
    enabled: !!refreshJobId && refreshStatus === 'running',
  });

  // Job 완료 시 프로필 다시 로드
  useEffect(() => {
    if (jobStatus?.status === 'DONE') {
      setRefreshStatus('done');
      setRefreshJobId(null);
      // 프로필 쿼리 무효화하여 다시 로드
      queryClient.invalidateQueries({ queryKey: ['corporation', corporateId, 'profile'] });
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
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-2">
              <Link2 className="w-4 h-4" />
              공유 링크
            </Button>
            <Button size="sm" className="gap-2" onClick={() => setShowPreviewModal(true)}>
              <FileDown className="w-4 h-4" />
              PDF 내보내기
            </Button>
          </div>
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

          {/* Executive Summary */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border">
              요약 (Executive Summary)
            </h2>
            <div className="text-sm text-muted-foreground space-y-2 leading-relaxed">
              <p>
                <strong className="text-foreground">{corporation.name}</strong>은(는) {corporation.industry} 분야에서
                사업을 영위하는 기업입니다.
                {corporation.headquarters ? `본사는 ${corporation.headquarters}에 소재하고 있습니다.` : ''}
              </p>
              {corporation.bankRelationship.hasRelationship && (
                <p>
                  당행과는 여신 {corporation.bankRelationship.loanBalance}, 수신 {corporation.bankRelationship.depositBalance} 규모의
                  거래 관계를 유지하고 있습니다.
                  {corporation.bankRelationship.fxTransactions && ` 외환 거래 규모는 ${corporation.bankRelationship.fxTransactions}입니다.`}
                </p>
              )}
              <p>
                최근 직접 시그널 {signalCounts.direct}건, 산업 시그널 {signalCounts.industry}건,
                환경 시그널 {signalCounts.environment}건이 감지되었습니다.
              </p>
              <p>아래 내용은 담당자의 검토를 위해 정리된 참고 자료입니다.</p>
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

          {/* Bank Relationship - Snapshot API 데이터 사용 */}
          {(snapshot?.snapshot_json?.credit?.has_loan || corporation.bankRelationship.hasRelationship) && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
                <Landmark className="w-4 h-4" />
                당행 거래 현황
              </h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">수신 잔액</div>
                  <div className="font-medium">{corporation.bankRelationship.depositBalance || "-"}</div>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">여신 잔액</div>
                  <div className="font-medium">
                    {snapshot?.snapshot_json?.credit?.loan_summary?.total_exposure_krw
                      ? `${(snapshot.snapshot_json.credit.loan_summary.total_exposure_krw / 100000000).toFixed(0)}억원`
                      : corporation.bankRelationship.loanBalance || "-"}
                  </div>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">외환 거래</div>
                  <div className="font-medium">{corporation.bankRelationship.fxTransactions || "-"}</div>
                </div>
              </div>
              {/* 담보 정보 (Snapshot API) */}
              {snapshot?.snapshot_json?.collateral?.has_collateral && (
                <div className="mt-3 p-3 bg-muted/30 rounded">
                  <div className="text-xs text-muted-foreground mb-2">담보 현황</div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="font-medium">
                      {snapshot.snapshot_json.collateral.total_collateral_value_krw
                        ? `${(snapshot.snapshot_json.collateral.total_collateral_value_krw / 100000000).toFixed(0)}억원`
                        : "-"}
                    </span>
                    <div className="flex gap-1">
                      {snapshot.snapshot_json.collateral.collateral_types?.map((type, i) => (
                        <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{type}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {/* KYC 상태 (Snapshot API) */}
              {snapshot?.snapshot_json?.corp?.kyc_status && (
                <div className="mt-3 p-3 bg-muted/30 rounded">
                  <div className="text-xs text-muted-foreground mb-2">KYC 상태</div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.is_kyc_completed
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}>
                      {snapshot.snapshot_json.corp.kyc_status.is_kyc_completed ? 'KYC 완료' : 'KYC 미완료'}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'HIGH'
                        ? 'bg-red-100 text-red-700'
                        : snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'MED'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                      내부등급: {snapshot.snapshot_json.corp.kyc_status.internal_risk_grade}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      최종 갱신: {snapshot.snapshot_json.corp.kyc_status.last_kyc_updated}
                    </span>
                  </div>
                </div>
              )}
              <div className="flex gap-2 mt-3">
                {corporation.bankRelationship.retirementPension && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">퇴직연금</span>
                )}
                {corporation.bankRelationship.payrollService && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">급여이체</span>
                )}
                {corporation.bankRelationship.corporateCard && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">법인카드</span>
                )}
                {snapshot?.snapshot_json?.credit?.loan_summary?.overdue_flag && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">연체 발생</span>
                )}
              </div>
            </section>
          )}

          <Separator />

          {/* ============================================================ */}
          {/* Corp Profile Section (PRD v1.2) */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Globe className="w-4 h-4" />
                외부 정보 프로필
              </h2>
              <div className="flex items-center gap-2">
                {profile && (
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
                      <span className="w-28 text-muted-foreground">연간 매출</span>
                      <span className="font-medium">{profile.revenue_krw ? formatKRW(profile.revenue_krw) : '-'}</span>
                    </div>
                    <div className="flex">
                      <span className="w-28 text-muted-foreground">수출 비중</span>
                      <span className="font-medium">{typeof profile.export_ratio_pct === 'number' ? `${profile.export_ratio_pct}%` : '-'}</span>
                    </div>
                    <div className="flex">
                      <span className="w-28 text-muted-foreground">임직원 수</span>
                      <span>{profile.employee_count ? `${profile.employee_count.toLocaleString()}명` : '-'}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex">
                      <span className="w-28 text-muted-foreground">비즈니스 모델</span>
                      <span>{profile.business_model || '-'}</span>
                    </div>
                    <div className="flex">
                      <span className="w-28 text-muted-foreground">본사 위치</span>
                      <span>{profile.headquarters || '-'}</span>
                    </div>
                  </div>
                </div>

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
