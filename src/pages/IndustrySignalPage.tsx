import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Factory, Info } from "lucide-react";

const mockIndustrySignals: Signal[] = [
  {
    id: "4",
    corporationName: "LG에너지솔루션",
    corporationId: "110-81-12345",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "전기차 배터리 산업 전반 수요 둔화 조짐",
    summary: "글로벌 전기차 시장의 성장 속도가 예상보다 더딘 것으로 나타나면서, 배터리 산업 전반에 영향을 미칠 수 있습니다. (요약 자료)",
    source: "한국에너지공단",
    detectedAt: "2시간 전",
    detailCategory: "시장 동향",
    relevanceNote: "LG에너지솔루션은 글로벌 2차전지 시장 점유율 상위 기업으로, 업계 전반의 수요 변화에 직접적 영향을 받을 수 있습니다.",
    relatedCorporations: ["삼성SDI", "SK온", "CATL"],
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 6,
  },
  {
    id: "7",
    corporationName: "SK하이닉스",
    corporationId: "105-81-11111",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    summary: "생성형 AI 확산에 따라 고대역폭 메모리(HBM) 수요가 급증하고 있으며, 주요 반도체 기업들의 생산 능력 확대가 요구되고 있습니다. (산업 동향 요약)",
    source: "한국반도체산업협회",
    detectedAt: "4시간 전",
    detailCategory: "기술 동향",
    relevanceNote: "SK하이닉스는 HBM 시장 점유율 1위 기업으로, 해당 산업 동향의 직접적 수혜 가능성이 있습니다.",
    relatedCorporations: ["삼성전자", "마이크론"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 8,
  },
];

export default function IndustrySignalPage() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return mockIndustrySignals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus]);

  const counts = useMemo(() => ({
    all: mockIndustrySignals.length,
    new: mockIndustrySignals.filter(s => s.status === "new").length,
    review: mockIndustrySignals.filter(s => s.status === "review").length,
    resolved: mockIndustrySignals.filter(s => s.status === "resolved").length,
  }), []);

  const handleViewDetail = (signal: Signal) => {
    setSelectedSignal(signal);
    setDetailOpen(true);
  };

  const statusFilters = [
    { id: "all", label: "전체", count: counts.all },
    { id: "new", label: "신규", count: counts.new },
    { id: "review", label: "검토중", count: counts.review },
    { id: "resolved", label: "완료", count: counts.resolved },
  ];

  return (
    <MainLayout>
      <div className="max-w-6xl">
        {/* Page header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-signal-industry/10 flex items-center justify-center">
              <Factory className="w-5 h-5 text-signal-industry" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">산업 시그널</h1>
              <p className="text-muted-foreground text-sm">
                산업 전반에 영향을 미칠 수 있는 시그널을 검토합니다.
              </p>
            </div>
          </div>
        </div>

        {/* Signal type explanation */}
        <div className="bg-card rounded-lg border border-signal-industry/30 p-5 mb-6">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-signal-industry/10 flex items-center justify-center shrink-0">
              <Info className="w-4 h-4 text-signal-industry" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-foreground mb-1">산업 시그널 안내</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                산업 시그널은 동일 산업 전반에 영향을 미칠 수 있는 
                산업 리포트, 업계 뉴스, 시장 동향 정보를 기반으로 생성된 참고 신호입니다. 
                개별 법인을 단정적으로 판단하기 위한 정보는 아닙니다.
              </p>
            </div>
          </div>
        </div>

        {/* Status filters */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
            {statusFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveStatus(filter.id as SignalStatus | "all")}
                className={`
                  px-4 py-2 rounded-md text-sm font-medium transition-colors
                  ${activeStatus === filter.id
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                  }
                `}
              >
                {filter.label}
                <span className={`ml-2 ${activeStatus === filter.id ? "text-signal-industry" : "text-muted-foreground"}`}>
                  {filter.count}
                </span>
              </button>
            ))}
          </div>

          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
            <option value="recent">최신순</option>
            <option value="corporation">기업명순</option>
          </select>
        </div>

        {/* Signal list */}
        <div className="space-y-3">
          {filteredSignals.map((signal) => (
            <SignalCard 
              key={signal.id} 
              signal={signal}
              onViewDetail={handleViewDetail}
            />
          ))}
        </div>

        {/* Empty state */}
        {filteredSignals.length === 0 && (
          <div className="text-center py-16 bg-card rounded-lg border border-border">
            <p className="text-muted-foreground">선택한 조건에 해당하는 산업 시그널이 없습니다.</p>
          </div>
        )}

        {/* Signal detail panel */}
        <SignalDetailPanel 
          signal={selectedSignal}
          open={detailOpen}
          onClose={() => setDetailOpen(false)}
        />
      </div>
    </MainLayout>
  );
}