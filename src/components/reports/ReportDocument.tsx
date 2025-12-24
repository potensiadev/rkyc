import { Separator } from "@/components/ui/separator";

interface ReportDocumentProps {
  companyName?: string;
  showLoanSection?: boolean;
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
  companyName = "삼성전자", 
  showLoanSection = true,
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
  const currentDate = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  const timelineEvents = [
    { date: "2024-12-20", type: "직접", summary: "분기 실적 발표 - 매출 전년 대비 12% 증가" },
    { date: "2024-12-18", type: "산업", summary: "반도체 업종 수출 규제 완화 발표" },
    { date: "2024-12-15", type: "환경", summary: "글로벌 금리 인하 기조 확대" },
    { date: "2024-12-10", type: "직접", summary: "신규 사업 부문 투자 계획 공시" },
  ];

  const evidenceItems = [
    { source: "금융감독원 전자공시", type: "공시", description: "2024년 3분기 연결재무제표 제출" },
    { source: "연합뉴스", type: "뉴스", description: "삼성전자 반도체 부문 실적 개선 보도" },
    { source: "산업통상자원부", type: "정책", description: "반도체 산업 지원 정책 발표" },
    { source: "한국은행", type: "리포트", description: "2024년 4분기 경제전망 보고서" },
  ];

  return (
    <div className="bg-white text-foreground font-sans">
      {/* Report Header / Cover */}
      <div className="border-b-2 border-border pb-8 mb-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">
            RKYC 기업 시그널 분석 보고서 (참고용)
          </h1>
          <div className="text-lg font-semibold text-foreground mb-6">
            {companyName}
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
              본 보고서는 {companyName}에 대해 RKYC 시스템이 최근 감지한 시그널을 요약한 참고 자료입니다.
            </p>
            <p>
              보고 기간 동안 직접 시그널 2건, 산업 시그널 1건, 환경 시그널 1건이 감지되었습니다. 
              해당 시그널들은 기업의 실적 발표, 산업 정책 변화, 거시경제 동향과 관련되어 있습니다.
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
              <span className="text-foreground">{companyName}</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">업종</span>
              <span className="text-foreground">전자·반도체</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">주요 사업</span>
              <span className="text-foreground">반도체, 스마트폰, 디스플레이 제조 및 판매</span>
            </div>
            <div className="flex">
              <span className="w-32 text-muted-foreground">당행 거래 여부</span>
              <span className="text-foreground">{showLoanSection ? "여신 보유" : "해당 없음"}</span>
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
                <p>감지 건수: 2건</p>
                <p>해당 기업의 실적 발표 및 사업 계획 관련 공시가 감지되었습니다.</p>
                <p>영향 구분: 참고</p>
              </div>
            </div>

            {/* Industry Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2">산업 시그널</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: 1건</p>
                <p>반도체 업종 관련 정책 변화가 감지되었습니다.</p>
                <p>영향 구분: 기회</p>
              </div>
            </div>

            {/* Environment Signals */}
            <div className="pl-4 border-l-2 border-primary/30">
              <h3 className="text-sm font-medium text-foreground mb-2">환경 시그널</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>감지 건수: 1건</p>
                <p>글로벌 금리 동향 변화가 감지되었습니다.</p>
                <p>영향 구분: 참고</p>
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
          <div className="space-y-3">
            {timelineEvents.map((event, index) => (
              <div key={index} className="flex text-sm border-b border-border/50 pb-3 last:border-0">
                <span className="w-28 text-muted-foreground shrink-0">{event.date}</span>
                <span className="w-16 text-muted-foreground shrink-0">{event.type}</span>
                <span className="text-foreground">{event.summary}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Supporting Evidence */}
      {sectionsToShow.evidenceSummary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            주요 근거 요약
          </h2>
          <div className="space-y-3">
            {evidenceItems.map((item, index) => (
              <div key={index} className="flex text-sm border-b border-border/50 pb-3 last:border-0">
                <span className="w-36 text-muted-foreground shrink-0">{item.source}</span>
                <span className="w-16 text-muted-foreground shrink-0">{item.type}</span>
                <span className="text-foreground">{item.description}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Loan Reference Insight - Conditional */}
      {showLoanSection && sectionsToShow.loanInsight && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            여신 참고 관점 요약
          </h2>
          <div className="text-sm text-muted-foreground space-y-3 leading-relaxed">
            <p>
              해당 기업은 당행 여신 거래가 있는 기업으로, 최근 감지된 시그널은 
              여신 관리 관점에서 참고할 수 있는 정보를 포함하고 있습니다.
            </p>
            <p>
              직접 시그널로 감지된 실적 발표 내용과 산업 시그널로 감지된 정책 변화는 
              해당 기업의 사업 환경 변화를 이해하는 데 참고될 수 있습니다.
            </p>
            <p className="italic text-xs">
              본 내용은 참고 정보이며, 여신 관련 조치나 권고를 포함하지 않습니다.
            </p>
          </div>
        </section>
      )}

      {/* Insight Memory */}
      {sectionsToShow.insightMemory && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
            과거 사례 참고 (Insight Memory)
          </h2>
          <div className="text-sm text-muted-foreground space-y-2">
            <div className="flex">
              <span className="w-40">유사 사례 건수</span>
              <span className="text-foreground">3건</span>
            </div>
            <div className="flex">
              <span className="w-40">일반적 영향 분류</span>
              <span className="text-foreground">단기 영향</span>
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
