import { Separator } from "@/components/ui/separator";
import { useCorporationReport, useCorpProfile, useCorporation, useCorporationSnapshot, useLoanInsight, useBankingData } from "@/hooks/useApi";
import {
  formatDate,
} from "@/data/signals";
import { Signal, SIGNAL_TYPE_CONFIG, Evidence } from "@/types/signal";
import { Loader2, AlertTriangle, Info, CheckCircle, Search, FileText, Building2, Landmark, TrendingUp, Package, Target, Globe, Factory, Users, AlertCircle, FileWarning } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ReportDocumentProps {
  corporationId: string;
  sectionsToShow?: {
    summary: boolean;
    companyOverview: boolean;
    valueChain: boolean;
    signalTypeSummary: boolean;
    signalTimeline: boolean;
    evidenceSummary: boolean;
    loanInsight: boolean;
    insightMemory: boolean;
    disclaimer: boolean;
  };
}

// 금액 포맷팅 헬퍼
function formatKRW(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조원`;
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(0)}억원`;
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(0)}만원`;
  return `${value.toLocaleString()}원`;
}

const ReportDocument = ({
  corporationId,
  sectionsToShow = {
    summary: true,
    companyOverview: true,
    valueChain: true,
    signalTypeSummary: true,
    signalTimeline: true,
    evidenceSummary: true,
    loanInsight: true,
    insightMemory: false,
    disclaimer: true,
  }
}: ReportDocumentProps) => {
  // Use new Report API hook - includes error handling
  const { data: report, isLoading: isLoadingReport, error: reportError, refetch } = useCorporationReport(corporationId);
  // Profile API for Value Chain section
  const { data: profile } = useCorpProfile(corporationId);
  // Corporation detail for company overview (CEO, address, etc.)
  const { data: corporation, isLoading: isLoadingCorp } = useCorporation(corporationId);
  // Snapshot for bank relationship
  const { data: snapshot } = useCorporationSnapshot(corporationId);
  // Loan Insight (조건부)
  const { data: loanInsightData, isLoading: isLoadingLoanInsight } = useLoanInsight(corporationId);
  // Banking Data (수신 잔액 등)
  const { data: bankingData } = useBankingData(corporationId);

  const isLoading = isLoadingReport || isLoadingCorp;

  if (isLoading) {
    return (
      <div className="report-document bg-white text-foreground font-sans animate-pulse">
        {/* Header Skeleton */}
        <div className="border-b-2 border-border pb-8 mb-8">
          <div className="text-center space-y-4">
            <div className="h-8 bg-muted rounded w-3/4 mx-auto" />
            <div className="h-6 bg-muted rounded w-1/3 mx-auto" />
            <div className="space-y-2 mt-4">
              <div className="h-4 bg-muted rounded w-1/4 mx-auto" />
              <div className="h-4 bg-muted rounded w-1/3 mx-auto" />
            </div>
            <div className="h-10 bg-muted rounded w-2/3 mx-auto mt-6" />
          </div>
        </div>

        {/* Summary Skeleton */}
        <div className="mb-8 space-y-4">
          <div className="h-6 bg-muted rounded w-1/4" />
          <div className="h-4 bg-muted rounded w-full" />
          <div className="h-4 bg-muted rounded w-5/6" />
          <div className="h-4 bg-muted rounded w-4/5" />
        </div>

        {/* Company Overview Skeleton */}
        <div className="mb-8 space-y-4">
          <div className="h-6 bg-muted rounded w-1/5" />
          <div className="space-y-2">
            <div className="flex gap-4">
              <div className="h-4 bg-muted rounded w-20" />
              <div className="h-4 bg-muted rounded w-32" />
            </div>
            <div className="flex gap-4">
              <div className="h-4 bg-muted rounded w-20" />
              <div className="h-4 bg-muted rounded w-40" />
            </div>
            <div className="flex gap-4">
              <div className="h-4 bg-muted rounded w-20" />
              <div className="h-4 bg-muted rounded w-24" />
            </div>
          </div>
        </div>

        {/* Timeline Skeleton */}
        <div className="mb-8 space-y-4">
          <div className="h-6 bg-muted rounded w-1/4" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex gap-4 border-b border-muted pb-3">
                <div className="h-4 bg-muted rounded w-24" />
                <div className="h-4 bg-muted rounded w-16" />
                <div className="h-4 bg-muted rounded flex-1" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state handling
  if (reportError) {
    return (
      <div className="text-center py-8 space-y-4">
        <div className="text-red-500 flex items-center justify-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          리포트 데이터를 불러오는 중 오류가 발생했습니다.
        </div>
        <p className="text-sm text-muted-foreground">
          {(reportError as Error)?.message || 'Failed to fetch'}
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          다시 시도
        </button>
      </div>
    );
  }

  // No data after successful API call
  if (!report) {
    return (
      <div className="text-center py-8 space-y-4">
        <div className="text-muted-foreground">
          리포트 데이터가 없습니다.
        </div>
        <p className="text-sm text-muted-foreground">
          해당 기업의 분석이 아직 실행되지 않았을 수 있습니다.
        </p>
        <p className="text-xs text-muted-foreground">
          기업 상세 페이지에서 "분석 실행" 버튼을 클릭하여 분석을 시작해주세요.
        </p>
      </div>
    );
  }

  const { summary_stats, signals, evidence_list, loan_insight: reportLoanInsight, corp_profile } = report;
  // Use corporation from dedicated API for richer data, fallback to report
  const corpName = corporation?.name || report.corporation.name;
  const corpBizNo = corporation?.businessNumber || report.corporation.business_number;
  const corpIndustry = corporation?.industry || report.corporation.industry;
  const corpIndustryCode = corporation?.industryCode || report.corporation.industry_code;

  // Signal Counts
  const signalCounts = summary_stats;

  // 시그널 타임라인 (최신순)
  const timelineSignals = [...signals].sort((a, b) =>
    new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
  );

  // 시그널 유형별 그룹화
  const directSignals = signals.filter(s => s.signal_type === "DIRECT");
  const industrySignals = signals.filter(s => s.signal_type === "INDUSTRY");
  const environmentSignals = signals.filter(s => s.signal_type === "ENVIRONMENT");

  // 영향 구분별 그룹화 Helper
  const getImpactLabel = (signalsList: any[]): string => {
    const riskCount = signalsList.filter(s => s.impact_direction === "RISK").length;
    const oppCount = signalsList.filter(s => s.impact_direction === "OPPORTUNITY").length;
    const neutralCount = signalsList.filter(s => s.impact_direction === "NEUTRAL").length;

    const parts = [];
    if (riskCount > 0) parts.push("위험");
    if (oppCount > 0) parts.push("기회");
    if (neutralCount > 0) parts.push("참고");

    return parts.join(" / ") || "참고";
  };

  const currentDate = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  // Evidence 타입 레이블
  const getEvidenceTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      INTERNAL_FIELD: "내부 데이터",
      DOC: "문서",
      EXTERNAL: "외부",
      news: "뉴스",
      disclosure: "공시",
      report: "리포트",
      regulation: "정책",
      internal: "내부",
    };
    if (type === "INTERNAL_FIELD") return "내부";
    return labels[type] || type;
  };

  // Use loanInsight from dedicated API (has more fields) or fallback to report
  const loanInsight = loanInsightData?.insight || null;
  const hasLoan = loanInsightData?.has_loan ?? (snapshot?.snapshot_json?.credit?.has_loan || corporation?.bankRelationship?.hasRelationship || false);

  return (
    <div className="report-document bg-white text-foreground font-sans print:p-0" style={{ fontFamily: 'Pretendard, "Malgun Gothic", "맑은 고딕", sans-serif' }}>
      {/* Report Header / Cover */}
      <div className="border-b-2 border-border pb-8 mb-8 break-inside-avoid">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">
            rKYC 기업 시그널 분석 보고서
          </h1>
          <div className="text-lg font-semibold text-foreground mb-6">
            {corpName}
          </div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>보고서 생성일: {currentDate}</p>
            <p>생성 시스템: rKYC Intelligence (Auto-Analysis)</p>
          </div>
          <div className="mt-6 inline-block px-4 py-2 bg-muted rounded text-sm text-muted-foreground">
            본 보고서는 AI 분석 결과이며, 최종 여신 의사결정은 담당자의 검토가 필요합니다.
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      {sectionsToShow.summary && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border flex items-center justify-between">
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
          <div className="text-sm text-muted-foreground space-y-3 leading-relaxed">
            {/* LLM 생성 Executive Summary 우선 사용 */}
            {loanInsight?.executive_summary ? (
              <p className="text-foreground">{loanInsight.executive_summary}</p>
            ) : (
              <>
                <p>
                  본 보고서는 <strong className="text-foreground">{corpName}</strong>에 대해 rKYC 시스템이 감지한 총 {summary_stats.total}건의 시그널을 분석한 결과입니다.
                </p>
                <p>
                  직접 시그널 {summary_stats.direct}건, 산업 시그널 {summary_stats.industry}건,
                  환경 시그널 {summary_stats.environment}건이 감지되었으며,
                  이 중 <span className="text-red-600 font-medium">위험 요인 {summary_stats.risk}건</span>,
                  <span className="text-blue-600 font-medium"> 기회 요인 {summary_stats.opportunity}건</span>입니다.
                </p>
              </>
            )}
            <p className="text-xs">
              아래 내용은 실시간 수집된 데이터와 AI 분석 모델(Claude Opus/Gemini Pro)을 통해 생성되었습니다.
            </p>
          </div>
        </section>
      )}

      {/* Company Overview - CorporateDetailPage와 동일하게 */}
      {sectionsToShow.companyOverview && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            기업 개요
          </h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex"><span className="w-28 text-muted-foreground">기업명</span><span>{corpName}</span></div>
              <div className="flex"><span className="w-28 text-muted-foreground">사업자등록번호</span><span>{corpBizNo || '-'}</span></div>
              <div className="flex"><span className="w-28 text-muted-foreground">업종</span><span>{corpIndustry}</span></div>
              <div className="flex"><span className="w-28 text-muted-foreground">업종코드</span><span>{corpIndustryCode}</span></div>
              {corporation?.bizType && <div className="flex"><span className="w-28 text-muted-foreground">업태</span><span>{corporation.bizType}</span></div>}
            </div>
            <div className="space-y-2">
              <div className="flex"><span className="w-28 text-muted-foreground">대표이사</span><span>{corporation?.ceo || '-'}</span></div>
              {corporation?.corpRegNo && <div className="flex"><span className="w-28 text-muted-foreground">법인등록번호</span><span>{corporation.corpRegNo}</span></div>}
              {corporation?.foundedYear && corporation.foundedYear > 0 && <div className="flex"><span className="w-28 text-muted-foreground">설립년도</span><span>{corporation.foundedYear}년</span></div>}
              {corporation?.headquarters && <div className="flex"><span className="w-28 text-muted-foreground">본사 소재지</span><span>{corporation.headquarters}</span></div>}
              <div className="flex"><span className="w-28 text-muted-foreground">사업자 유형</span><span>{corporation?.isCorporation ? '법인사업자' : '개인사업자'}</span></div>
            </div>
          </div>
          {/* 주요 주주 */}
          {profile?.shareholders && profile.shareholders.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border">
              <div className="flex text-sm">
                <span className="w-28 text-muted-foreground shrink-0">주요 주주</span>
                <span>
                  {profile.shareholders.map((sh, i) => (
                    <span key={i}>
                      {sh.name} ({sh.ownership_pct}%)
                      {i < profile.shareholders.length - 1 && ', '}
                    </span>
                  ))}
                </span>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Bank Relationship - CorporateDetailPage와 동일하게 */}
      {(snapshot?.snapshot_json?.credit?.has_loan || bankingData) && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border flex items-center gap-2">
            <Landmark className="w-4 h-4" />
            당행 거래 현황
          </h2>
          <div className={`rounded-lg border ${snapshot?.snapshot_json?.credit?.loan_summary?.overdue_flag ? 'border-red-200 bg-red-50/30' : 'border-border bg-muted/30'}`}>
            {/* 1행: 금액 정보 + 담보 */}
            <div className="flex items-center justify-between px-4 py-3 text-sm border-b border-border/50">
              <div className="flex items-center gap-6">
                <div>
                  <span className="text-muted-foreground text-xs">수신</span>
                  <span className="ml-2 font-medium">
                    {(bankingData?.deposit_trend as any)?.current_balance
                      ? `${((bankingData.deposit_trend as any).current_balance / 100000000).toFixed(0)}억원`
                      : "-"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">여신</span>
                  <span className="ml-2 font-medium">
                    {snapshot?.snapshot_json?.credit?.loan_summary?.total_exposure_krw
                      ? `${(snapshot.snapshot_json.credit.loan_summary.total_exposure_krw / 100000000).toFixed(0)}억원`
                      : corporation?.bankRelationship?.loanBalance || "-"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">외환</span>
                  <span className="ml-2 font-medium">{corporation?.bankRelationship?.fxTransactions || "-"}</span>
                </div>
              </div>
              {/* 담보 정보 */}
              {snapshot?.snapshot_json?.collateral?.has_collateral && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-xs">담보</span>
                  {snapshot.snapshot_json.collateral.total_collateral_value_krw && (
                    <span className="font-medium">
                      {`${(snapshot.snapshot_json.collateral.total_collateral_value_krw / 100000000).toFixed(0)}억원`}
                    </span>
                  )}
                  <div className="flex gap-1">
                    {snapshot.snapshot_json.collateral.collateral_types?.map((type: string, i: number) => {
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

      {/* Loan Insight Section - CorporateDetailPage와 동일하게 */}
      {sectionsToShow.loanInsight && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileWarning className="w-4 h-4" />
              여신 참고 관점 요약 (AI Risk Opinion)
            </span>
            {loanInsight && (
              <Badge
                variant="outline"
                className={`
                  ${loanInsight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border-red-200' : ''}
                  ${loanInsight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border-orange-200' : ''}
                  ${loanInsight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border-green-200' : ''}
                  ${loanInsight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border-blue-200' : ''}
                `}
              >
                {loanInsight.stance.label}
              </Badge>
            )}
          </h2>

          {isLoadingLoanInsight ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
              <span className="text-sm text-muted-foreground">여신 정보를 확인하는 중...</span>
            </div>
          ) : !hasLoan ? (
            /* 여신이 없는 경우 */
            <div className="bg-gray-50 rounded-lg p-6 text-center border border-gray-200">
              <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
                <FileWarning className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-600">당행 여신이 없습니다</p>
              <p className="text-xs text-muted-foreground mt-1">해당 기업에 대한 여신 거래가 없어 AI 분석이 제공되지 않습니다.</p>
            </div>
          ) : hasLoan && !loanInsight ? (
            /* 여신은 있지만 분석이 아직 안 된 경우 */
            <div className="bg-blue-50 rounded-lg p-6 text-center border border-blue-200">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-blue-700">분석 중입니다</p>
              <p className="text-xs text-muted-foreground mt-2">잠시 후 페이지를 새로고침해 주세요.</p>
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
                    {loanInsight.key_risks && loanInsight.key_risks.length > 0 ? (
                      loanInsight.key_risks.map((risk: string, idx: number) => (
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
                    {loanInsight.key_opportunities && loanInsight.key_opportunities.length > 0 ? (
                      loanInsight.key_opportunities.map((opp: string, idx: number) => (
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

              {/* Mitigating Factors */}
              {loanInsight.mitigating_factors && loanInsight.mitigating_factors.length > 0 && (
                <div className="pt-4 border-t border-slate-200">
                  <h3 className="text-sm font-semibold text-blue-700 mb-3 flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    리스크 상쇄 요인
                  </h3>
                  <ul className="space-y-2">
                    {loanInsight.mitigating_factors.map((factor: string, idx: number) => (
                      <li key={idx} className="text-sm text-foreground/80 flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Separator />

              {/* Action Items */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center">
                  <Search className="w-4 h-4 mr-2" />
                  심사역 확인 체크리스트
                </h3>
                <div className="space-y-2 bg-white p-3 rounded border border-slate-200">
                  {loanInsight.action_items && loanInsight.action_items.length > 0 ? (
                    loanInsight.action_items.map((item: string, idx: number) => (
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
                  시그널 {loanInsight.signal_count || 0}건 분석 (위험 {loanInsight.risk_count || 0}, 기회 {loanInsight.opportunity_count || 0})
                </span>
                <span className="flex items-center gap-2">
                  {loanInsight.is_fallback && (
                    <span className="text-orange-500">Rule-based</span>
                  )}
                  {loanInsight.generation_model && (
                    <span>모델: {loanInsight.generation_model}</span>
                  )}
                  <span>생성: {loanInsight.generated_at ? new Date(loanInsight.generated_at).toLocaleDateString('ko-KR') : '-'}</span>
                </span>
              </div>

              <p className="italic text-xs text-muted-foreground text-right">
                * 본 의견은 AI 모델이 생성한 참고 자료이며, 은행의 공식 심사 의견을 대체하지 않습니다.
              </p>
            </div>
          ) : null}
        </section>
      )}

      {/* 기업 인텔리전스 - CorporateDetailPage와 동일하게 (2단 레이아웃) */}
      {sectionsToShow.valueChain && profile && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            기업 인텔리전스
          </h2>

          {/* 사업 개요 (Full Width) */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-4">
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

          {/* 2단 레이아웃: 밸류체인 | 시장 포지션 */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* 좌측: 밸류체인 */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
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
              {Object.keys(profile.supply_chain?.supplier_countries || {}).length > 0 && (
                <div className="pt-2 border-t border-slate-200">
                  <span className="text-xs text-muted-foreground">공급 국가 비중</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(profile.supply_chain!.supplier_countries).map(([country, pct]) => (
                      <span key={country} className="text-xs bg-orange-50 text-orange-700 px-2 py-0.5 rounded">
                        {country} {pct}%
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 우측: 시장 포지션 */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
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
                        className={`text-xs px-2 py-0.5 rounded ${
                          f.impact === 'POSITIVE' ? 'bg-green-50 text-green-700 border border-green-200' :
                          f.impact === 'NEGATIVE' ? 'bg-red-50 text-red-700 border border-red-200' :
                          'bg-slate-100 border border-slate-200'
                        }`}
                      >
                        {f.impact === 'POSITIVE' ? '↑ ' : f.impact === 'NEGATIVE' ? '↓ ' : ''}{f.factor}
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

          {/* 글로벌 노출 (Full Width) */}
          {profile.country_exposure && Object.keys(profile.country_exposure).length > 0 && (
            <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg mb-4">
              <Globe className="w-4 h-4 text-blue-600" />
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

          {/* 신뢰도 */}
          {profile.profile_confidence && (
            <div className="text-xs text-muted-foreground text-right">
              신뢰도: {profile.profile_confidence}
            </div>
          )}
        </section>
      )}

      {/* Signal Summary by Type */}
      {sectionsToShow.signalTypeSummary && (
        <section className="mb-8" style={{ pageBreakInside: 'avoid' }}>
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            시그널 유형별 요약
          </h2>

          <div className="space-y-6">
            {/* Direct Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2 flex items-center">
                <span className="w-2 h-2 rounded-full bg-primary mr-2"></span>
                직접 시그널 (기업 내부 이슈)
              </h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.direct}건</p>
                {directSignals.length > 0 ? (
                  <p>{directSignals[0].summary || directSignals[0].title}</p>
                ) : (
                  <p className="text-muted-foreground/50">감지된 직접 시그널이 없습니다.</p>
                )}
                <p className="text-xs mt-1 text-muted-foreground">영향 구분: {getImpactLabel(directSignals)}</p>
              </div>
            </div>

            {/* Industry Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2 flex items-center">
                <span className="w-2 h-2 rounded-full bg-orange-400 mr-2"></span>
                산업 시그널 (업황/경쟁)
              </h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.industry}건</p>
                {industrySignals.length > 0 ? (
                  <p>{industrySignals[0].summary || industrySignals[0].title}</p>
                ) : (
                  <p className="text-muted-foreground/50">감지된 산업 시그널이 없습니다.</p>
                )}
                <p className="text-xs mt-1 text-muted-foreground">영향 구분: {getImpactLabel(industrySignals)}</p>
              </div>
            </div>

            {/* Environment Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2 flex items-center">
                <span className="w-2 h-2 rounded-full bg-slate-400 mr-2"></span>
                환경 시그널 (거시/정책)
              </h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.environment}건</p>
                {environmentSignals.length > 0 ? (
                  <p>{environmentSignals[0].summary || environmentSignals[0].title}</p>
                ) : (
                  <p className="text-muted-foreground/50">감지된 환경 시그널이 없습니다.</p>
                )}
                <p className="text-xs mt-1 text-muted-foreground">영향 구분: {getImpactLabel(environmentSignals)}</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Signal Timeline */}
      {sectionsToShow.signalTimeline && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            시그널 타임라인
          </h2>
          {timelineSignals.length > 0 ? (
            <div className="space-y-3">
              {timelineSignals.map((signal) => (
                <div key={signal.signal_id} className="flex text-sm border-b border-border/50 pb-3 last:border-0">
                  <span className="w-32 text-muted-foreground shrink-0 text-xs">
                    {formatDate(signal.detected_at)}
                  </span>
                  <span className="w-24 text-muted-foreground shrink-0 text-xs font-medium">
                    {SIGNAL_TYPE_CONFIG[signal.signal_type?.toLowerCase() as any]?.label || signal.signal_type}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-foreground font-medium ${signal.impact_direction === 'RISK' ? 'text-red-600' : signal.impact_direction === 'OPPORTUNITY' ? 'text-blue-600' : ''}`}>
                        [{signal.impact_direction === 'RISK' ? '위험' : signal.impact_direction === 'OPPORTUNITY' ? '기회' : '중립'}]
                      </span>
                      <span className="text-foreground">{signal.title}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">감지된 시그널이 없습니다.</p>
          )}
        </section>
      )}

      {/* Supporting Evidence */}
      {sectionsToShow.evidenceSummary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border leading-none flex items-center justify-between">
            <span>주요 근거 요약</span>
            <span className="text-xs font-normal text-muted-foreground">총 {evidence_list.length}건 수집</span>
          </h2>
          {evidence_list && evidence_list.length > 0 ? (
            <div className="space-y-3 bg-slate-50 p-4 rounded-md border border-slate-100">
              {evidence_list.slice(0, 5).map((evidence) => (
                <div key={evidence.evidence_id} className="flex text-sm border-b border-slate-200 pb-3 last:border-0 last:pb-0">
                  <div className="w-8 shrink-0 flex items-start mt-0.5">
                    <FileText className="w-4 h-4 text-slate-400" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded">
                        {getEvidenceTypeLabel(evidence.evidence_type)}
                      </span>
                      <span className="text-xs text-slate-400">{formatDate(evidence.created_at)}</span>
                    </div>
                    <p className="text-foreground font-medium text-sm leading-snug">
                      "{evidence.snippet || evidence.ref_value}"
                    </p>
                    <p className="text-xs text-muted-foreground break-all">
                      출처: {evidence.ref_value}
                    </p>
                  </div>
                </div>
              ))}
              {evidence_list.length > 5 && (
                <div className="text-center pt-2">
                  <span className="text-xs text-muted-foreground">...외 {evidence_list.length - 5}건의 근거</span>
                </div>
              )}
            </div>
          ) : (
            <div className="py-4 text-center border border-dashed rounded-md">
              <p className="text-sm text-muted-foreground">수집된 근거가 없습니다.</p>
            </div>
          )}
        </section>
      )}

      {/* Disclaimer */}
      {sectionsToShow.disclaimer && (
        <section className="mt-12 pt-6 border-t-2 border-border" style={{ pageBreakInside: 'avoid' }}>
          <div className="bg-muted p-4 rounded text-xs text-muted-foreground leading-relaxed">
            본 보고서는 rKYC 시스템이 감지한 시그널을 기반으로 생성된 참고 자료입니다.
            자동 판단, 점수화, 예측 또는 조치를 의미하지 않으며,
            최종 판단은 담당자 및 관련 조직의 책임 하에 이루어집니다.
            <br /><br />
            데이터 출처: DART(전자공시), 주요 언론사 뉴스, 거시경제 지표 API
          </div>
        </section>
      )}
    </div>
  );
};

export default ReportDocument;
