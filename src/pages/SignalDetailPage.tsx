import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { 
  Signal, 
  Evidence,
  SIGNAL_TYPE_CONFIG, 
  SIGNAL_IMPACT_CONFIG, 
  SIGNAL_STRENGTH_CONFIG,
  CONFIDENCE_LEVEL_CONFIG,
  SOURCE_TYPE_CONFIG,
  EVIDENCE_SOURCE_TYPE_CONFIG,
  EVENT_CLASSIFICATION_CONFIG,
} from "@/types/signal";
import { 
  ArrowLeft, 
  Building2, 
  Factory, 
  Globe, 
  TrendingUp, 
  TrendingDown, 
  FileText,
  ExternalLink,
  Clock,
  Shield,
  Database,
  Tag,
  Info,
  Landmark,
  History
} from "lucide-react";
import { Button } from "@/components/ui/button";

// Extended signal type with loan relationship
interface ExtendedSignal extends Signal {
  aiSummary: string;
  evidences: Evidence[];
  hasLoanRelationship?: boolean;
  loanRiskInsight?: string;
  pastCaseStats?: {
    similarCases: number;
    shortTermOnly: number;
    escalatedToMidTerm: number;
  };
}

// Mock detailed signal data
const mockSignalDetails: Record<string, ExtendedSignal> = {
  "1": {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "124-81-00998",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다.",
    source: "연합뉴스",
    sourceUrl: "https://example.com",
    detectedAt: "2024-12-24 09:30",
    detailCategory: "인사/조직",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
    confidenceLevel: "high",
    sourceType: "external",
    eventClassification: "governance",
    hasLoanRelationship: true,
    loanRiskInsight: "해당 법인은 현재 기업 운영자금 대출이 실행 중인 상태입니다. 금번 시그널에서 감지된 조직 구조조정 검토 관련 정보는 법인의 내부 경영 상황 변화를 시사할 수 있는 요소로 참고될 수 있습니다. 구조조정이 실제 시행될 경우 단기적으로 비용 부담이 발생할 가능성이 있으며, 이에 따른 현금흐름 변화 여부를 모니터링할 필요가 있습니다. 다만, 해당 정보만으로 상환 능력에 대한 판단을 내릴 수 없으며, 추가적인 재무 자료 확인이 필요합니다.",
    pastCaseStats: {
      similarCases: 18,
      shortTermOnly: 11,
      escalatedToMidTerm: 4,
    },
    aiSummary: `삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다. 복수의 언론 보도에 따르면, 이번 조치는 글로벌 반도체 시장의 수요 변화에 대응하기 위한 전략적 결정으로 분석됩니다.

해당 시그널은 삼성전자를 직접 언급한 외부 뉴스 소스를 기반으로 생성되었습니다. 구조조정의 규모와 시기에 대한 구체적인 정보는 아직 공식 확인되지 않았으며, 회사 측의 공식 입장 발표가 필요한 상황입니다.

본 요약은 수집된 정보를 기반으로 한 참고용 자료이며, 투자 판단이나 의사결정을 위한 자료로 사용되어서는 안 됩니다.`,
    evidences: [
      {
        id: "e1",
        sourceType: "news",
        title: "삼성전자, 반도체 사업부 인력 구조조정 검토 착수",
        snippet: "삼성전자가 글로벌 반도체 시장 침체에 대응하기 위해 반도체 사업부의 인력 구조조정을 검토하고 있는 것으로 알려졌다.",
        sourceName: "연합뉴스",
        sourceUrl: "https://example.com/news1",
        publishedAt: "2024-12-24 08:00",
      },
      {
        id: "e2",
        sourceType: "news",
        title: "반도체 업계, 구조조정 바람...삼성전자도 예외 아냐",
        snippet: "글로벌 반도체 업계가 수요 둔화에 따른 구조조정에 나서고 있는 가운데, 삼성전자도 조직 효율화 방안을 검토 중인 것으로 전해졌다.",
        sourceName: "한국경제",
        sourceUrl: "https://example.com/news2",
        publishedAt: "2024-12-24 08:30",
      },
      {
        id: "e3",
        sourceType: "report",
        title: "2024년 4분기 반도체 산업 전망 리포트",
        snippet: "주요 반도체 기업들의 비용 절감 노력이 강화되고 있으며, 인력 효율화가 주요 과제로 부상하고 있습니다.",
        sourceName: "한국반도체산업협회",
        sourceUrl: "https://example.com/report1",
        publishedAt: "2024-12-20",
      },
      {
        id: "e4",
        sourceType: "disclosure",
        title: "삼성전자 2024년 3분기 실적 공시",
        snippet: "반도체 부문 영업이익이 전년 동기 대비 감소하였으며, 시장 상황에 따른 전략적 대응을 지속할 예정입니다.",
        sourceName: "금융감독원 전자공시",
        sourceUrl: "https://example.com/dart1",
        publishedAt: "2024-11-15",
      },
      {
        id: "e5",
        sourceType: "news",
        title: "삼성전자 노조 반발 예고...구조조정 검토에 긴장",
        snippet: "삼성전자 노동조합이 구조조정 검토 보도에 대해 반발 입장을 밝혔다.",
        sourceName: "매일경제",
        sourceUrl: "https://example.com/news3",
        publishedAt: "2024-12-24 09:00",
      },
    ],
  },
  "7": {
    id: "7",
    corporationName: "SK하이닉스",
    corporationId: "105-81-11111",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    summary: "생성형 AI 확산에 따라 고대역폭 메모리(HBM) 수요가 급증하고 있습니다.",
    source: "한국반도체산업협회",
    detectedAt: "2024-12-24 05:00",
    detailCategory: "기술 동향",
    relevanceNote: "SK하이닉스는 HBM 시장 점유율 1위 기업입니다.",
    relatedCorporations: ["삼성전자", "마이크론"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 8,
    confidenceLevel: "high",
    sourceType: "mixed",
    eventClassification: "market_shift",
    aiSummary: `생성형 AI 기술의 급속한 확산에 따라 고대역폭 메모리(HBM) 수요가 전례 없는 수준으로 급증하고 있습니다. 주요 AI 칩 제조사들의 수요 증가로 인해 HBM 공급 부족 현상이 지속되고 있으며, 이는 관련 기업들의 사업 기회로 작용할 수 있습니다.

SK하이닉스는 현재 글로벌 HBM 시장에서 약 50% 이상의 점유율을 보유하고 있어, 해당 산업 동향의 직접적인 영향권에 있는 것으로 분석됩니다. 삼성전자, 마이크론 등 경쟁사들도 생산 능력 확대에 나서고 있습니다.

본 정보는 산업 전반의 동향을 요약한 참고 자료이며, 개별 기업의 실적이나 주가를 전망하기 위한 자료가 아닙니다.`,
    evidences: [
      {
        id: "e1",
        sourceType: "report",
        title: "2024년 HBM 시장 분석 보고서",
        snippet: "HBM 시장 규모가 2024년 전년 대비 3배 이상 성장할 것으로 전망됩니다. AI 데이터센터 수요가 주요 성장 동력입니다.",
        sourceName: "한국반도체산업협회",
        sourceUrl: "https://example.com/report1",
        publishedAt: "2024-12-15",
      },
      {
        id: "e2",
        sourceType: "news",
        title: "엔비디아, HBM 공급 확보에 총력...SK하이닉스와 협력 강화",
        snippet: "엔비디아가 차세대 AI 칩에 필요한 HBM 확보를 위해 SK하이닉스와의 협력을 강화하고 있다.",
        sourceName: "전자신문",
        sourceUrl: "https://example.com/news1",
        publishedAt: "2024-12-22",
      },
      {
        id: "e3",
        sourceType: "disclosure",
        title: "SK하이닉스 HBM 생산시설 증설 투자 결정 공시",
        snippet: "이천 및 청주 사업장에 HBM 생산 능력 확대를 위한 추가 투자를 결정하였습니다.",
        sourceName: "금융감독원 전자공시",
        sourceUrl: "https://example.com/dart1",
        publishedAt: "2024-12-01",
      },
    ],
  },
};

function getSignalTypeIcon(category: Signal["signalCategory"]) {
  switch (category) {
    case "direct":
      return Building2;
    case "industry":
      return Factory;
    case "environment":
      return Globe;
  }
}

function getImpactIcon(impact: Signal["impact"]) {
  switch (impact) {
    case "risk":
      return TrendingDown;
    case "opportunity":
      return TrendingUp;
    case "neutral":
      return FileText;
  }
}

function getEvidenceIcon(sourceType: Evidence["sourceType"]) {
  switch (sourceType) {
    case "news":
      return FileText;
    case "disclosure":
      return Database;
    case "report":
      return FileText;
    case "regulation":
      return Shield;
    case "internal":
      return Database;
  }
}

export default function SignalDetailPage() {
  const { signalId } = useParams();
  const navigate = useNavigate();

  const signal = mockSignalDetails[signalId || "1"] || mockSignalDetails["1"];
  
  const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
  const impactConfig = SIGNAL_IMPACT_CONFIG[signal.impact];
  const strengthConfig = SIGNAL_STRENGTH_CONFIG[signal.impactStrength];
  const confidenceConfig = CONFIDENCE_LEVEL_CONFIG[signal.confidenceLevel || "medium"];
  const sourceTypeConfig = SOURCE_TYPE_CONFIG[signal.sourceType || "external"];
  const eventConfig = signal.eventClassification 
    ? EVENT_CLASSIFICATION_CONFIG[signal.eventClassification] 
    : null;
  
  const TypeIcon = getSignalTypeIcon(signal.signalCategory);
  const ImpactIcon = getImpactIcon(signal.impact);

  return (
    <MainLayout>
      <div className="max-w-4xl">
        {/* Back navigation */}
        <Button 
          variant="ghost" 
          className="mb-4 -ml-2 text-muted-foreground hover:text-foreground"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          시그널 목록으로 돌아가기
        </Button>

        {/* Header Section */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          {/* Corporation Name */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <button 
                onClick={() => {
                  const corporateKey = signal.corporationName === "삼성전자" ? "samsung" : 
                                       signal.corporationName === "SK하이닉스" ? "skhynix" : 
                                       signal.corporationName === "현대자동차" ? "hyundai" : "samsung";
                  navigate(`/corporates/${corporateKey}`);
                }}
                className="text-left hover:opacity-80 transition-opacity"
              >
                <h1 className="text-2xl font-semibold text-foreground mb-1 hover:text-primary transition-colors">
                  {signal.corporationName}
                </h1>
                <p className="text-sm text-muted-foreground">{signal.corporationId}</p>
              </button>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              {signal.detectedAt}
            </div>
          </div>

          {/* Signal Title */}
          <h2 className="text-lg font-medium text-foreground mb-4">
            {signal.title}
          </h2>

          {/* Meta badges */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Signal Type */}
            <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
              <TypeIcon className="w-4 h-4" />
              {typeConfig.label}
            </div>

            {/* Impact Direction */}
            <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium ${impactConfig.bgClass} ${impactConfig.colorClass}`}>
              <ImpactIcon className="w-4 h-4" />
              영향: {impactConfig.label}
            </div>

            {/* Impact Strength */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-muted text-foreground">
              영향 강도: {strengthConfig.label}
            </div>

            {/* Confidence Level */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-muted">
              <span className="text-muted-foreground">신뢰도:</span>
              <span className={confidenceConfig.colorClass}>{confidenceConfig.label}</span>
            </div>

            {/* Source Type */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-muted text-foreground">
              출처: {sourceTypeConfig.label}
            </div>
          </div>
        </div>

        {/* Section 1: AI Signal Summary */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Info className="w-4 h-4 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground">AI 시그널 요약</h3>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">참고용</span>
          </div>
          
          <div className="prose prose-sm max-w-none">
            {signal.aiSummary?.split("\n\n").map((paragraph, idx) => (
              <p key={idx} className="text-sm text-foreground leading-relaxed mb-3 last:mb-0">
                {paragraph}
              </p>
            ))}
          </div>

          {/* Relevance note for industry/environment signals */}
          {signal.relevanceNote && (
            <div className="mt-4 p-3 bg-accent rounded-md">
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">관련성 참고: </span>
                {signal.relevanceNote}
              </p>
            </div>
          )}

          {/* Related corporations for industry signals */}
          {signal.relatedCorporations && signal.relatedCorporations.length > 0 && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              <span className="text-sm text-muted-foreground">관련 기업:</span>
              {signal.relatedCorporations.map((corp, idx) => (
                <span 
                  key={idx}
                  className="text-xs px-2 py-1 rounded-md bg-secondary text-secondary-foreground"
                >
                  {corp}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: Supporting Evidence */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-info/10 flex items-center justify-center">
              <Database className="w-4 h-4 text-info" />
            </div>
            <h3 className="text-lg font-medium text-foreground">근거 자료</h3>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {signal.evidences?.length || 0}건
            </span>
          </div>

          <div className="space-y-3">
            {signal.evidences?.map((evidence) => {
              const evidenceConfig = EVIDENCE_SOURCE_TYPE_CONFIG[evidence.sourceType];
              const EvidenceIcon = getEvidenceIcon(evidence.sourceType);

              return (
                <div 
                  key={evidence.id}
                  className="p-4 bg-secondary/50 rounded-lg border border-border hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {/* Source type badge */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium ${evidenceConfig.colorClass}`}>
                          <EvidenceIcon className="w-3 h-3" />
                          {evidenceConfig.label}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {evidence.publishedAt}
                        </span>
                      </div>

                      {/* Title */}
                      <h4 className="text-sm font-medium text-foreground mb-1">
                        {evidence.title}
                      </h4>

                      {/* Snippet */}
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {evidence.snippet}
                      </p>

                      {/* Source name */}
                      <p className="text-xs text-muted-foreground mt-2">
                        출처: {evidence.sourceName}
                      </p>
                    </div>

                    {/* External link */}
                    {evidence.sourceUrl && (
                      <a 
                        href={evidence.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 w-8 h-8 flex items-center justify-center rounded-md bg-muted hover:bg-accent transition-colors"
                      >
                        <ExternalLink className="w-4 h-4 text-muted-foreground" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 3: Standardized Event Classification */}
        {eventConfig && (
          <div className="bg-card rounded-lg border border-border p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-signal-environment/10 flex items-center justify-center">
                <Tag className="w-4 h-4 text-signal-environment" />
              </div>
              <h3 className="text-lg font-medium text-foreground">표준 이벤트 분류</h3>
            </div>

            <div className="flex items-center gap-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/10 border border-primary/20">
                <Tag className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-primary">{eventConfig.label}</span>
              </div>
              <p className="text-sm text-muted-foreground">{eventConfig.description}</p>
            </div>
          </div>
        )}

        {/* Conditional Panel: Loan Risk Insight */}
        {signal.hasLoanRelationship && 
         signal.impact === "risk" && 
         (signal.impactStrength === "high" || signal.impactStrength === "medium") && 
         signal.loanRiskInsight && (
          <div className="bg-muted/30 rounded-lg border border-border p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
                <Landmark className="w-4 h-4 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground">여신 리스크 인사이트</h3>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">참고용</span>
            </div>

            <p className="text-sm text-foreground leading-relaxed mb-4">
              {signal.loanRiskInsight}
            </p>

            <div className="pt-3 border-t border-border">
              <p className="text-xs text-muted-foreground">
                본 인사이트는 참고용으로만 제공됩니다. 최종 판단 및 조치는 담당자가 수행합니다.
              </p>
            </div>
          </div>
        )}

        {/* Insight Memory Panel */}
        {signal.pastCaseStats && (
          <div className="bg-muted/30 rounded-lg border border-border p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
                <History className="w-4 h-4 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground">인사이트 메모리 (과거 사례 참고)</h3>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">참고용</span>
            </div>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-foreground">
                동일 산업 내 유사 사례 (최근 12개월): <span className="font-medium">{signal.pastCaseStats.similarCases}건</span>
              </p>
              <p className="text-sm text-foreground">
                단기 영향으로 종결된 사례: <span className="font-medium">{signal.pastCaseStats.shortTermOnly}건</span>
              </p>
              <p className="text-sm text-foreground">
                중기 관리로 확대된 사례: <span className="font-medium">{signal.pastCaseStats.escalatedToMidTerm}건</span>
              </p>
            </div>

            <div className="pt-3 border-t border-border">
              <p className="text-xs text-muted-foreground">
                본 정보는 과거 사례를 요약한 것으로, 예측이나 권고를 의미하지 않습니다.
              </p>
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="bg-muted/50 rounded-lg border border-border p-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-medium">안내:</span> 본 시그널 정보는 AI가 수집한 공개 정보를 기반으로 생성된 참고용 자료입니다. 
            투자 판단, 여신 심사, 또는 기타 의사결정에 직접 활용하기 위한 자료가 아니며, 
            실제 업무 판단은 담당자의 추가 검토와 내부 절차에 따라 진행되어야 합니다. 
            본 시스템은 자동화된 추천이나 조치를 수행하지 않습니다.
          </p>
        </div>
      </div>
    </MainLayout>
  );
}