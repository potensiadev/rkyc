import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Building2 } from "lucide-react";

const mockDirectSignals: Signal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "124-81-00998",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다. (참고용 요약)",
    source: "연합뉴스",
    sourceUrl: "https://example.com",
    detectedAt: "10분 전",
    detailCategory: "인사/조직",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
  },
  {
    id: "2",
    corporationName: "현대자동차",
    corporationId: "101-81-15555",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "현대자동차 2024년 3분기 영업이익 전년 대비 15% 감소",
    summary: "현대자동차의 2024년 3분기 영업이익이 전년 동기 대비 15% 감소한 것으로 잠정 집계되었습니다. (검토용 자료)",
    source: "금융감독원 전자공시",
    detectedAt: "25분 전",
    detailCategory: "실적/재무",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 3,
  },
  {
    id: "3",
    corporationName: "카카오",
    corporationId: "120-81-47521",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "공정거래위원회, 카카오 플랫폼 독점 관련 조사 착수",
    summary: "공정거래위원회가 카카오의 플랫폼 시장 지배력 남용 혐의에 대한 본격적인 조사에 착수했습니다. (참고 정보)",
    source: "공정거래위원회",
    detectedAt: "1시간 전",
    detailCategory: "규제/법률",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 4,
  },
  {
    id: "5",
    corporationName: "네이버",
    corporationId: "220-81-62517",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "resolved",
    title: "네이버, AI 스타트업 인수 완료 공시",
    summary: "네이버가 국내 AI 스타트업 인수를 공식 완료했습니다. 검토 완료. (참고)",
    source: "전자공시시스템",
    detectedAt: "어제",
    detailCategory: "인수합병",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 2,
  },
];

export default function DirectSignalPage() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return mockDirectSignals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus]);

  const counts = useMemo(() => ({
    all: mockDirectSignals.length,
    new: mockDirectSignals.filter(s => s.status === "new").length,
    review: mockDirectSignals.filter(s => s.status === "review").length,
    resolved: mockDirectSignals.filter(s => s.status === "resolved").length,
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
            <div className="w-10 h-10 rounded-lg bg-signal-direct/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-signal-direct" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">직접 시그널</h1>
              <p className="text-muted-foreground text-sm">
                특정 법인과 직접적으로 관련된 시그널을 검토합니다.
              </p>
            </div>
          </div>
        </div>

        {/* Signal type explanation banner */}
        <div className="bg-muted/50 rounded-lg border border-border px-4 py-3 mb-6">
          <p className="text-sm text-muted-foreground">
            기업 내부 문서, 공시, 거래 등 직접 관련 이벤트 기준 시그널입니다.
          </p>
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
                <span className={`ml-2 ${activeStatus === filter.id ? "text-signal-direct" : "text-muted-foreground"}`}>
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
            <p className="text-muted-foreground">선택한 조건에 해당하는 직접 시그널이 없습니다.</p>
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