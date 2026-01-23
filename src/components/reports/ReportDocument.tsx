import { Separator } from "@/components/ui/separator";
import { useCorporationReport } from "@/hooks/useApi";
import {
  formatDate,
} from "@/data/signals";
import { Signal, SIGNAL_TYPE_CONFIG, Evidence } from "@/types/signal";
import { Loader2, AlertTriangle, Info, CheckCircle, Search, FileText } from "lucide-react";
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

const ReportDocument = ({
  corporationId,
  sectionsToShow = {
    summary: true,
    companyOverview: true,
    valueChain: false,
    signalTypeSummary: true,
    signalTimeline: true,
    evidenceSummary: true,
    loanInsight: true,
    insightMemory: false,
    disclaimer: true,
  }
}: ReportDocumentProps) => {
  // Use new Report API hook
  const { data: report, isLoading } = useCorporationReport(corporationId);

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

        {/* Signal Summary Skeleton */}
        <div className="mb-8 space-y-4">
          <div className="h-6 bg-muted rounded w-1/4" />
          <div className="space-y-4 pl-4 border-l-2 border-muted">
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-4 bg-muted rounded w-full" />
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-4 bg-muted rounded w-5/6" />
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-4 bg-muted rounded w-4/5" />
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

  if (!report) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        분석 리포트 생성에 실패했습니다. (No Data)
      </div>
    );
  }

  const { corporation, summary_stats, signals, evidence_list, loan_insight } = report;

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

  // 영향 구분별 그룹화 Helper (API types vs Frontend types mixing here, handling simple string checks)
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
      // sub-mappings if needed from frontend types
      news: "뉴스",
      disclosure: "공시",
      report: "리포트",
      regulation: "정책",
      internal: "내부",
    };
    // fallback if API returns new codes
    if (type === "INTERNAL_FIELD") return "내부";
    return labels[type] || type;
  };

  return (
    <div className="report-document bg-white text-foreground font-sans print:p-0" style={{ fontFamily: 'Pretendard, "Malgun Gothic", "맑은 고딕", sans-serif' }}>
      {/* Report Header / Cover */}
      <div className="border-b-2 border-border pb-8 mb-8 break-inside-avoid">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">
            rKYC 기업 시그널 분석 보고서
          </h1>
          <div className="text-lg font-semibold text-foreground mb-6">
            {corporation.name}
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
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            요약 (Executive Summary)
          </h2>
          <div className="text-sm text-muted-foreground space-y-3 leading-relaxed">
            <p>
              본 보고서는 {corporation.name}에 대해 rKYC 시스템이 감지한 총 {summary_stats.total}건의 시그널을 분석한 결과입니다.
            </p>
            <p>
              직접 시그널 {summary_stats.direct}건, 산업 시그널 {summary_stats.industry}건,
              환경 시그널 {summary_stats.environment}건이 감지되었으며,
              이 중 <span className="text-risk font-medium font-bold">위험 요인 {summary_stats.risk}건</span>,
              <span className="text-opportunity font-medium font-bold"> 기회 요인 {summary_stats.opportunity}건</span>입니다.
            </p>
            <p>
              아래 내용은 실시간 수집된 데이터와 AI 분석 모델(Claude Opus/Gemini Pro)을 통해 생성되었습니다.
            </p>
          </div>
        </section>
      )}

      {/* Company Overview */}
      {sectionsToShow.companyOverview && (
        <section className="mb-8 break-inside-avoid">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            기업 개요
          </h2>
          <div className="text-sm space-y-2">
            <div className="flex">
              <span className="w-32 text-muted-foreground">기업명</span>
              <span className="text-foreground font-medium">{corporation.name}</span>
            </div>
            {corporation.business_number && (
              <div className="flex">
                <span className="w-32 text-muted-foreground">사업자등록번호</span>
                <span className="text-foreground">{corporation.business_number}</span>
              </div>
            )}
            <div className="flex">
              <span className="w-32 text-muted-foreground">업종</span>
              <span className="text-foreground">{corporation.industry} ({corporation.industry_code})</span>
            </div>
            {corporation.has_loan && (
              <div className="flex">
                <span className="w-32 text-muted-foreground">당행 거래 여부</span>
                <span className="text-foreground font-medium text-blue-600">여신 보유 중</span>
              </div>
            )}
            {corporation.internal_rating && (
              <div className="flex">
                <span className="w-32 text-muted-foreground">내부 등급</span>
                <span className="text-foreground">{corporation.internal_rating}</span>
              </div>
            )}
          </div>
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
                    {/* Only show short summary here if timeline is verbose setting, but keeping clean for now */}
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

      {/* Loan Reference Insight - AI Risk Manager Opinion */}
      {(corporation.has_loan || sectionsToShow.loanInsight) && loan_insight && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border flex items-center justify-between">
            <span>여신 참고 관점 요약 (AI Risk Opinion)</span>
            <Badge
              variant="outline"
              className={`
                ${loan_insight.stance.level === 'CAUTION' ? 'bg-red-50 text-red-600 border-red-200' : ''}
                ${loan_insight.stance.level === 'MONITORING' ? 'bg-orange-50 text-orange-600 border-orange-200' : ''}
                ${loan_insight.stance.level === 'STABLE' ? 'bg-green-50 text-green-600 border-green-200' : ''}
                ${loan_insight.stance.level === 'POSITIVE' ? 'bg-blue-50 text-blue-600 border-blue-200' : ''}
              `}
            >
              {loan_insight.stance.label}
            </Badge>
          </h2>

          <div className="bg-slate-50 rounded-lg p-5 border border-slate-200 space-y-6">

            {/* Narrative */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-2">종합 소견</h3>
              <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                {loan_insight.narrative}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {/* Risk Drivers */}
              <div>
                <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  핵심 리스크 요인
                </h3>
                <ul className="space-y-2">
                  {loan_insight.key_risks.length > 0 ? (
                    loan_insight.key_risks.map((risk, idx) => (
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

              {/* Mitigating Factors */}
              <div>
                <h3 className="text-sm font-semibold text-blue-700 mb-3 flex items-center">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  리스크 상쇄/기회 요인
                </h3>
                <ul className="space-y-2">
                  {loan_insight.mitigating_factors.length > 0 ? (
                    loan_insight.mitigating_factors.map((factor, idx) => (
                      <li key={idx} className="text-sm text-foreground/80 flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        {factor}
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-muted-foreground italic">특이 상쇄 요인이 없습니다.</li>
                  )}
                </ul>
              </div>
            </div>

            <Separator />

            {/* Action Items */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center">
                <Search className="w-4 h-4 mr-2" />
                심사역 확인 체크리스트
              </h3>
              <div className="space-y-2 bg-white p-3 rounded border border-slate-200">
                {loan_insight.action_items.length > 0 ? (
                  loan_insight.action_items.map((item, idx) => (
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

          </div>

          <p className="italic text-xs text-muted-foreground mt-4 text-right">
            * 본 의견은 AI 모델이 생성한 참고 자료이며, 은행의 공식 심사 의견을 대체하지 않습니다.
          </p>
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
