import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Globe } from "lucide-react";

const mockEnvironmentSignals: Signal[] = [
  {
    id: "6",
    corporationName: "포스코홀딩스",
    corporationId: "102-81-45678",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "미국 철강 관세 인상 발표, 수출 기업 영향 전망",
    summary: "미국 정부가 철강 및 알루미늄에 대한 추가 관세 부과를 발표했습니다. 해당 조치는 한국 철강 수출 기업들의 미국 시장 경쟁력에 영향을 미칠 수 있습니다. (검토용 요약)",
    source: "외교부",
    detectedAt: "3시간 전",
    detailCategory: "무역 정책",
    relevanceNote: "포스코홀딩스는 미국 수출 비중이 약 15%로, 관세 정책 변화에 따른 수익성 영향 검토가 필요할 수 있습니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 4,
  },
  {
    id: "8",
    corporationName: "한국전력공사",
    corporationId: "120-81-99999",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "review",
    title: "정부, 전기요금 체계 개편안 발표 예정",
    summary: "정부가 내년 상반기 전기요금 체계 전면 개편안을 발표할 예정입니다. 산업용 요금 조정 및 시간대별 차등 요금제 도입이 검토되고 있습니다. (정책 동향 요약)",
    source: "산업통상자원부",
    detectedAt: "5시간 전",
    detailCategory: "에너지 정책",
    relevanceNote: "한국전력공사의 수익 구조 및 재무 상태에 직접적 영향을 미칠 수 있는 정책 변화입니다.",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 3,
  },
];

export default function EnvironmentSignalPage() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return mockEnvironmentSignals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus]);

  const counts = useMemo(() => ({
    all: mockEnvironmentSignals.length,
    new: mockEnvironmentSignals.filter(s => s.status === "new").length,
    review: mockEnvironmentSignals.filter(s => s.status === "review").length,
    resolved: mockEnvironmentSignals.filter(s => s.status === "resolved").length,
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
            <div className="w-10 h-10 rounded-lg bg-signal-environment/10 flex items-center justify-center">
              <Globe className="w-5 h-5 text-signal-environment" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">환경 시그널</h1>
              <p className="text-muted-foreground text-sm">
                외부 환경 변화에 따른 거시적 참고 정보를 검토합니다.
              </p>
            </div>
          </div>
        </div>

        {/* Signal type explanation banner */}
        <div className="bg-muted/50 rounded-lg border border-border px-4 py-3 mb-6">
          <p className="text-sm text-muted-foreground">
            정책, 규제, 거시 환경 등 외부 요인 기준 시그널입니다.
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
                <span className={`ml-2 ${activeStatus === filter.id ? "text-signal-environment" : "text-muted-foreground"}`}>
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
            <p className="text-muted-foreground">선택한 조건에 해당하는 환경 시그널이 없습니다.</p>
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