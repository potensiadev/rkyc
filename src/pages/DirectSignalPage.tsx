import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Building2 } from "lucide-react";

// Supabase corp 테이블 기준 DIRECT 시그널 (seed_v2.sql 참조)
const mockDirectSignals: Signal[] = [
  {
    id: "00000001-0001-0001-0001-000000000001",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "엠케이전자 내부 신용등급 MED→HIGH 상향 조정",
    summary: "엠케이전자의 내부 신용등급이 MED에서 HIGH로 상향 조정되었습니다. 최근 반도체 수출 증가에 따른 재무 건전성 개선이 반영된 것으로 분석됩니다.",
    source: "내부 리스크 시스템",
    detectedAt: "15분 전",
    detailCategory: "신용등급 변경",
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 3,
  },
  {
    id: "00000002-0001-0001-0001-000000000002",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "동부건설 여신 노출 12억 → 18억원 증가",
    summary: "동부건설의 총 여신 노출이 12억원에서 18억원으로 50% 증가했습니다. 신규 PF 사업 참여에 따른 것으로, 담보 상태 모니터링이 필요합니다.",
    source: "여신관리시스템",
    detectedAt: "30분 전",
    detailCategory: "여신 노출 변화",
    impact: "risk",
    impactStrength: "medium",
    evidenceCount: 4,
  },
  {
    id: "00000003-0001-0001-0001-000000000003",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "전북식품 KYC 갱신 기한 도래 (30일 이내)",
    summary: "전북식품의 정기 KYC 갱신 기한이 30일 이내로 도래합니다. 최근 재무제표 및 주주구성 변동 여부 확인이 필요합니다.",
    source: "KYC 모니터링 시스템",
    detectedAt: "1시간 전",
    detailCategory: "KYC 갱신",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 2,
  },
  {
    id: "00000004-0001-0001-0001-000000000004",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "new",
    title: "광주정밀기계 대표이사 변경 공시",
    summary: "광주정밀기계의 대표이사가 최광수에서 신임 대표로 변경되었습니다. 경영진 교체에 따른 사업 전략 변화 가능성이 있습니다.",
    source: "전자공시시스템",
    detectedAt: "2시간 전",
    detailCategory: "지배구조 변화",
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 3,
  },
  {
    id: "00000005-0001-0001-0001-000000000005",
    corporationName: "익산바이오텍",
    corporationId: "4301-3456789",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "review",
    title: "익산바이오텍 연체 플래그 활성화",
    summary: "익산바이오텍의 연체 플래그가 활성화되었습니다. R&D 투자 확대에 따른 일시적 유동성 악화로 추정되나, 상세 검토가 필요합니다.",
    source: "여신관리시스템",
    detectedAt: "3시간 전",
    detailCategory: "연체 감지",
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 5,
  },
  {
    id: "00000006-0001-0001-0001-000000000006",
    corporationName: "나주태양에너지",
    corporationId: "6701-4567890",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "resolved",
    title: "나주태양에너지 담보가치 15% 상승 확인",
    summary: "나주태양에너지가 담보로 제공한 태양광 발전소 부지의 감정평가 결과, 담보가치가 15% 상승한 것으로 확인되었습니다.",
    source: "담보평가시스템",
    detectedAt: "어제",
    detailCategory: "담보 가치 변화",
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