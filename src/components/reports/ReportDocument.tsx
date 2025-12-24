import { Separator } from "@/components/ui/separator";
import { getCorporationById, getCorporationByName, Corporation } from "@/data/corporations";
import { 
  getSignalsByCorporationId, 
  getAllEvidencesForCorporation, 
  getCorporationSignalCounts,
  formatDate,
} from "@/data/signals";
import { getInsightMemoryByCorporationId } from "@/data/insightMemory";
import { Signal, SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG, Evidence } from "@/types/signal";

interface ReportDocumentProps {
  corporationId: string;
  sectionsToShow?: {
    summary: boolean;
    companyOverview: boolean;
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
    signalTypeSummary: true,
    signalTimeline: true,
    evidenceSummary: true,
    loanInsight: true,
    insightMemory: true,
    disclaimer: true,
  }
}: ReportDocumentProps) => {
  // 중앙화된 데이터 소스에서 기업 정보 조회
  const corporation = getCorporationById(corporationId);
  
  if (!corporation) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        기업 정보를 찾을 수 없습니다.
      </div>
    );
  }

  // 중앙화된 데이터 소스에서 시그널 조회
  const signals = getSignalsByCorporationId(corporationId);
  const signalCounts = getCorporationSignalCounts(corporationId);
  const evidences = getAllEvidencesForCorporation(corporationId);
  const insightMemory = getInsightMemoryByCorporationId(corporationId);

  // 시그널 타임라인 (최신순)
  const timelineSignals = [...signals].sort((a, b) => 
    new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime()
  );

  // 시그널 유형별 그룹화
  const directSignals = signals.filter(s => s.signalCategory === "direct");
  const industrySignals = signals.filter(s => s.signalCategory === "industry");
  const environmentSignals = signals.filter(s => s.signalCategory === "environment");

  // 영향 구분별 그룹화
  const getImpactLabel = (signals: Signal[]): string => {
    const riskCount = signals.filter(s => s.impact === "risk").length;
    const oppCount = signals.filter(s => s.impact === "opportunity").length;
    const neutralCount = signals.filter(s => s.impact === "neutral").length;
    
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
  const getEvidenceTypeLabel = (type: Evidence["sourceType"]): string => {
    const labels: Record<string, string> = {
      news: "뉴스",
      disclosure: "공시",
      report: "리포트",
      regulation: "정책",
      internal: "내부",
    };
    return labels[type] || type;
  };

  return (
    <div className="bg-white text-foreground font-sans">
      {/* Report Header / Cover */}
      <div className="border-b-2 border-border pb-8 mb-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">
            RKYC 기업 시그널 분석 보고서 (참고용)
          </h1>
          <div className="text-lg font-semibold text-foreground mb-6">
            {corporation.name}
          </div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>보고서 생성일: {currentDate}</p>
            <p>생성 시스템: RKYC (Really Know Your Customer Intelligence)</p>
          </div>
          <div className="mt-6 inline-block px-4 py-2 bg-muted rounded text-sm text-muted-foreground">
            본 보고서는 참고 및 검토용 자료입니다.
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      {sectionsToShow.summary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            요약 (Executive Summary)
          </h2>
          <div className="text-sm text-muted-foreground space-y-3 leading-relaxed">
            <p>
              본 보고서는 {corporation.name}에 대해 RKYC 시스템이 최근 감지한 시그널을 요약한 참고 자료입니다.
            </p>
            <p>
              보고 기간 동안 직접 시그널 {signalCounts.direct}건, 산업 시그널 {signalCounts.industry}건, 
              환경 시그널 {signalCounts.environment}건이 감지되었습니다. 
              {signals.length > 0 && "해당 시그널들은 기업의 사업 활동, 산업 동향, 거시경제 환경과 관련되어 있습니다."}
            </p>
            <p>
              본 자료는 담당자의 검토를 위해 제공되며, 감지된 시그널의 맥락과 근거를 함께 정리하였습니다.
            </p>
            <p>
              아래 내용은 자동화된 시그널 감지 결과를 정리한 것으로, 해석 및 판단은 담당자의 검토가 필요합니다.
            </p>
          </div>
        </section>
      )}

      {/* Company Overview */}
      {sectionsToShow.companyOverview && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            기업 개요
          </h2>
          <div className="text-sm space-y-2">
            <div className="flex">
              <span className="w-32 text-muted-foreground">기업명</span>
              <span className="text-foreground">{corporation.name}</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">사업자등록번호</span>
              <span className="text-foreground">{corporation.businessNumber}</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">업종</span>
              <span className="text-foreground">{corporation.industry}</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">주요 사업</span>
              <span className="text-foreground">{corporation.mainBusiness}</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">당행 거래 여부</span>
              <span className="text-foreground">{corporation.hasLoanRelationship ? "여신 보유" : "해당 없음"}</span>
            </div>
          </div>
        </section>
      )}

      {/* Signal Summary by Type */}
      {sectionsToShow.signalTypeSummary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            시그널 유형별 요약
          </h2>
          
          <div className="space-y-6">
            {/* Direct Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2">직접 시그널</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.direct}건</p>
                {directSignals.length > 0 ? (
                  <p>{directSignals[0].summary}</p>
                ) : (
                  <p>감지된 직접 시그널이 없습니다.</p>
                )}
                <p>영향 구분: {getImpactLabel(directSignals)}</p>
              </div>
            </div>

            {/* Industry Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2">산업 시그널</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.industry}건</p>
                {industrySignals.length > 0 ? (
                  <p>{industrySignals[0].summary}</p>
                ) : (
                  <p>감지된 산업 시그널이 없습니다.</p>
                )}
                <p>영향 구분: {getImpactLabel(industrySignals)}</p>
              </div>
            </div>

            {/* Environment Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2">환경 시그널</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: {signalCounts.environment}건</p>
                {environmentSignals.length > 0 ? (
                  <p>{environmentSignals[0].summary}</p>
                ) : (
                  <p>감지된 환경 시그널이 없습니다.</p>
                )}
                <p>영향 구분: {getImpactLabel(environmentSignals)}</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-muted-foreground mt-4 italic">
            위 요약은 참고용이며, 우선순위 또는 해석을 포함하지 않습니다.
          </p>
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
                <div key={signal.id} className="flex text-sm border-b border-border/50 pb-3 last:border-0">
                  <span className="w-28 text-muted-foreground shrink-0">
                    {formatDate(signal.detectedAt)}
                  </span>
                  <span className="w-16 text-muted-foreground shrink-0">
                    {SIGNAL_TYPE_CONFIG[signal.signalCategory].label.replace(" 시그널", "")}
                  </span>
                  <span className="text-foreground">{signal.title}</span>
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
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            주요 근거 요약
          </h2>
          {evidences.length > 0 ? (
            <div className="space-y-3">
              {evidences.slice(0, 5).map((evidence) => (
                <div key={evidence.id} className="flex text-sm border-b border-border/50 pb-3 last:border-0">
                  <span className="w-36 text-muted-foreground shrink-0">{evidence.sourceName}</span>
                  <span className="w-16 text-muted-foreground shrink-0">
                    {getEvidenceTypeLabel(evidence.sourceType)}
                  </span>
                  <span className="text-foreground">{evidence.title}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">수집된 근거가 없습니다.</p>
          )}
        </section>
      )}

      {/* Loan Reference Insight - Conditional */}
      {corporation.hasLoanRelationship && sectionsToShow.loanInsight && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            여신 참고 관점 요약
          </h2>
          <div className="text-sm text-muted-foreground space-y-3 leading-relaxed">
            <p>
              해당 기업은 당행 여신 거래가 있는 기업으로, 최근 감지된 시그널은 
              여신 관리 관점에서 참고할 수 있는 정보를 포함하고 있습니다.
            </p>
            {signals.length > 0 && (
              <p>
                {directSignals.length > 0 && "직접 시그널로 감지된 기업 활동 정보와 "}
                {industrySignals.length > 0 && "산업 시그널로 감지된 업종 동향은 "}
                해당 기업의 사업 환경 변화를 이해하는 데 참고될 수 있습니다.
              </p>
            )}
            <p className="italic text-xs">
              본 내용은 참고 정보이며, 여신 관련 조치나 권고를 포함하지 않습니다.
            </p>
          </div>
        </section>
      )}

      {/* Insight Memory */}
      {sectionsToShow.insightMemory && insightMemory && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            과거 사례 참고 (Insight Memory)
          </h2>
          <div className="text-sm text-muted-foreground space-y-2">
            <div className="flex">
              <span className="w-40">유사 사례 건수</span>
              <span className="text-foreground">{insightMemory.similarCaseCount}건</span>
            </div>
            <div className="flex">
              <span className="w-40">일반적 영향 분류</span>
              <span className="text-foreground">{insightMemory.impactClassification} 영향</span>
            </div>
            <p className="mt-3 text-xs italic">
              위 정보는 과거 유사 시그널 사례를 참고용으로 제공하며, 현재 상황에 대한 예측이나 판단을 의미하지 않습니다.
            </p>
          </div>
        </section>
      )}

      {/* Disclaimer */}
      {sectionsToShow.disclaimer && (
        <section className="mt-12 pt-6 border-t-2 border-border">
          <div className="bg-muted p-4 rounded text-xs text-muted-foreground leading-relaxed">
            본 보고서는 RKYC 시스템이 감지한 시그널을 기반으로 생성된 참고 자료입니다. 
            자동 판단, 점수화, 예측 또는 조치를 의미하지 않으며, 
            최종 판단은 담당자 및 관련 조직의 책임 하에 이루어집니다.
          </div>
        </section>
      )}
    </div>
  );
};

export default ReportDocument;
