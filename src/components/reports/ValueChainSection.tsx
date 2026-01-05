// 가치사슬망 섹션 컴포넌트
import { ValueChain } from "@/data/valueChain";
import { ArrowRight, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface ValueChainSectionProps {
  valueChain: ValueChain;
}

const ValueChainSection = ({ valueChain }: ValueChainSectionProps) => {
  const getImpactIcon = (impact: "positive" | "negative" | "neutral") => {
    switch (impact) {
      case "positive":
        return <TrendingUp className="w-3 h-3 text-green-600 inline" />;
      case "negative":
        return <TrendingDown className="w-3 h-3 text-red-600 inline" />;
      default:
        return <Minus className="w-3 h-3 text-gray-500 inline" />;
    }
  };

  const getImpactColor = (impact: "positive" | "negative" | "neutral") => {
    switch (impact) {
      case "positive":
        return "text-green-700 bg-green-50";
      case "negative":
        return "text-red-700 bg-red-50";
      default:
        return "text-gray-700 bg-gray-50";
    }
  };

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-foreground mb-4 pb-2 border-b border-border">
        가치사슬망
      </h2>

      {/* 산업 개요 */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-foreground mb-2">산업 구조 및 비즈니스 모델</h3>
        <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line bg-muted/30 p-4 rounded">
          {valueChain.industryOverview}
        </div>
        <div className="mt-2 text-sm">
          <span className="text-muted-foreground">비즈니스 모델: </span>
          <span className="text-foreground font-medium">{valueChain.businessModel}</span>
        </div>
      </div>

      {/* 공급-당사-수요 플로우 다이어그램 */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-foreground mb-3">공급망 구조</h3>
        <div className="flex items-stretch gap-2 text-xs">
          {/* 공급 측 */}
          <div className="flex-1 border border-border rounded p-3 bg-blue-50/50">
            <div className="font-medium text-blue-800 mb-2 text-center">공급 (Upstream)</div>
            <div className="space-y-1">
              {valueChain.suppliers.slice(0, 4).map((supplier, idx) => (
                <div key={idx} className="flex justify-between text-muted-foreground">
                  <span className="truncate">{supplier.name}</span>
                  <span className="text-blue-600 shrink-0 ml-1">{supplier.share}</span>
                </div>
              ))}
              {valueChain.suppliers.length > 4 && (
                <div className="text-muted-foreground/60 text-center">외 {valueChain.suppliers.length - 4}개</div>
              )}
            </div>
          </div>

          {/* 화살표 */}
          <div className="flex items-center">
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
          </div>

          {/* 당사 */}
          <div className="w-24 border-2 border-primary rounded p-3 bg-primary/5 flex flex-col justify-center items-center">
            <div className="font-semibold text-primary text-center">당사</div>
            <div className="text-[10px] text-muted-foreground text-center mt-1">제조/가공</div>
          </div>

          {/* 화살표 */}
          <div className="flex items-center">
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
          </div>

          {/* 수요 측 */}
          <div className="flex-1 border border-border rounded p-3 bg-green-50/50">
            <div className="font-medium text-green-800 mb-2 text-center">수요 (Downstream)</div>
            <div className="space-y-1">
              {valueChain.customers.map((customer, idx) => (
                <div key={idx} className="flex justify-between text-muted-foreground">
                  <span className="truncate">{customer.name}</span>
                  <span className="text-green-600 shrink-0 ml-1">{customer.share}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 경쟁 현황 */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-foreground mb-2">경쟁 현황 (Top Players)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 font-medium text-muted-foreground">기업명</th>
                <th className="text-right py-2 font-medium text-muted-foreground">시장점유율</th>
                <th className="text-right py-2 font-medium text-muted-foreground">매출규모</th>
                <th className="text-left py-2 pl-3 font-medium text-muted-foreground">비고</th>
              </tr>
            </thead>
            <tbody>
              {valueChain.competitors.map((competitor, idx) => (
                <tr
                  key={idx}
                  className={`border-b border-border/50 ${competitor.note?.includes("당사") ? "bg-primary/5 font-medium" : ""}`}
                >
                  <td className="py-2 text-foreground">{competitor.name}</td>
                  <td className="py-2 text-right text-foreground">{competitor.marketShare}</td>
                  <td className="py-2 text-right text-muted-foreground">{competitor.revenue}</td>
                  <td className="py-2 pl-3 text-muted-foreground">{competitor.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 매크로 환경 요인 */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-foreground mb-2">매크로 환경 요인</h3>
        <div className="space-y-2">
          {valueChain.macroFactors.map((factor, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-2 text-xs p-2 rounded ${getImpactColor(factor.impact)}`}
            >
              <span className="shrink-0 mt-0.5">{getImpactIcon(factor.impact)}</span>
              <div>
                <span className="font-medium">[{factor.category}]</span>{" "}
                <span>{factor.description}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted-foreground italic">
        위 가치사슬망 정보는 산업 분석 참고용이며, 실제 거래 관계와 다를 수 있습니다.
      </p>
    </section>
  );
};

export default ValueChainSection;
