import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Globe } from "lucide-react";

// Supabase corp 테이블 기준 ENVIRONMENT 시그널 (seed_v2.sql 참조)
const mockEnvironmentSignals: Signal[] = [
  {
    id: "00000024-0001-0001-0001-000000000024",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "미중 반도체 규제 강화, 수출 통제 확대 전망",
    summary: "미국 정부의 대중국 반도체 수출 규제가 강화되면서 글로벌 반도체 공급망 재편이 가속화되고 있습니다. 국내 전자부품 제조업체에도 영향이 예상됩니다.",
    source: "산업통상자원부",
    detectedAt: "2시간 전",
    detailCategory: "정책/규제 변화",
    relevanceNote: "엠케이전자는 반도체 장비 수출 비중이 높아 미중 규제 변화의 간접적 영향을 받을 수 있습니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 4,
  },
  {
    id: "00000025-0001-0001-0001-000000000025",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "review",
    title: "정부 부동산 PF 구조조정 방안 발표 예정",
    summary: "정부가 부동산 프로젝트 파이낸싱(PF) 부실 문제 해결을 위한 구조조정 방안을 발표할 예정입니다. 건설업계 전반에 영향을 미칠 것으로 예상됩니다.",
    source: "금융위원회",
    detectedAt: "3시간 전",
    detailCategory: "정책/규제 변화",
    relevanceNote: "동부건설은 PF 사업 비중이 높아 정책 변화에 따른 직접적 영향이 예상됩니다.",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
  },
  {
    id: "00000026-0001-0001-0001-000000000026",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "environment",
    signalSubType: "macro",
    status: "new",
    title: "한중 FTA 추가 협상 개시, 농산물 관세 인하 논의",
    summary: "한중 FTA 추가 협상이 개시되어 농산물 및 식품 관세 인하가 논의되고 있습니다. 국내 식품제조업체의 원가 절감 기회로 작용할 수 있습니다.",
    source: "외교부",
    detectedAt: "4시간 전",
    detailCategory: "정책/규제 변화",
    relevanceNote: "전북식품은 중국산 원자재 수입 비중이 높아 관세 인하의 수혜가 예상됩니다.",
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 3,
  },
  {
    id: "00000027-0001-0001-0001-000000000027",
    corporationName: "삼성전자",
    corporationId: "4301-3456789",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "review",
    title: "식약처 바이오시밀러 허가 심사 기준 강화 예고",
    summary: "식품의약품안전처가 바이오시밀러 허가 심사 기준 강화를 예고했습니다. 임상 데이터 요구 수준이 높아질 전망이며, 개발 일정에 영향을 미칠 수 있습니다.",
    source: "식품의약품안전처",
    detectedAt: "5시간 전",
    detailCategory: "정책/규제 변화",
    relevanceNote: "삼성전자은 바이오시밀러 개발 중으로, 허가 기준 강화의 직접적 영향을 받을 수 있습니다.",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 4,
  },
  {
    id: "00000028-0001-0001-0001-000000000028",
    corporationName: "휴림로봇",
    corporationId: "6701-4567890",
    signalCategory: "environment",
    signalSubType: "regulatory",
    status: "resolved",
    title: "RE100 이행 로드맵 확정, 신재생에너지 투자 확대",
    summary: "정부가 RE100(재생에너지 100%) 이행 로드맵을 확정하여 기업들의 신재생에너지 사용 의무가 강화됩니다. 태양광 발전 사업자에게 긍정적 전망입니다.",
    source: "산업통상자원부",
    detectedAt: "어제",
    detailCategory: "정책/규제 변화",
    relevanceNote: "휴림로봇는 태양광 발전 사업자로, RE100 정책 확대의 직접적 수혜가 예상됩니다.",
    impact: "opportunity",
    impactStrength: "high",
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