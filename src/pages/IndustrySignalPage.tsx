import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalStatus } from "@/types/signal";
import { Factory } from "lucide-react";

// Supabase corp 테이블 기준 INDUSTRY 시그널 (seed_v2.sql 참조)
const mockIndustrySignals: Signal[] = [
  {
    id: "00000018-0001-0001-0001-000000000018",
    corporationName: "엠케이전자",
    corporationId: "8001-3719240",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "반도체 업종 전반 수출 호조, 전자부품 수요 증가 전망",
    summary: "글로벌 반도체 시장 회복세에 따라 전자부품 제조업(C26) 전반의 수출이 증가하고 있습니다. 엠케이전자는 해당 업종 소속으로, 긍정적 영향이 예상됩니다.",
    source: "한국반도체산업협회",
    detectedAt: "1시간 전",
    detailCategory: "산업 충격",
    relevanceNote: "엠케이전자는 전자부품제조업(C26) 소속 기업으로, 반도체 업황 개선의 수혜가 예상됩니다.",
    relatedCorporations: ["삼성전기", "LG이노텍"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 4,
  },
  {
    id: "00000019-0001-0001-0001-000000000019",
    corporationName: "동부건설",
    corporationId: "8000-7647330",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "건설업 PF 부실 우려 확대, 유동성 위험 경고",
    summary: "부동산 경기 침체로 인해 건설업(F41) 전반의 프로젝트 파이낸싱(PF) 부실 우려가 확대되고 있습니다. 중소 건설사 유동성 모니터링 강화가 권고됩니다.",
    source: "한국건설산업연구원",
    detectedAt: "2시간 전",
    detailCategory: "산업 충격",
    relevanceNote: "동부건설은 건설업(F41) 소속으로, PF 사업 비중이 높아 영향도 면밀한 검토가 필요합니다.",
    relatedCorporations: ["현대건설", "대우건설", "GS건설"],
    impact: "risk",
    impactStrength: "high",
    evidenceCount: 6,
  },
  {
    id: "00000020-0001-0001-0001-000000000020",
    corporationName: "전북식품",
    corporationId: "4028-1234567",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "식품제조업 원자재 가격 안정화 추세",
    summary: "농산물 및 식품 원자재 가격이 전년 대비 안정화되면서 식품제조업(C10)의 수익성 개선이 예상됩니다. 수출 경쟁력 회복 가능성도 있습니다.",
    source: "한국식품산업협회",
    detectedAt: "3시간 전",
    detailCategory: "산업 충격",
    relevanceNote: "전북식품은 식품제조업(C10) 소속으로, 원자재 가격 안정화의 수혜가 기대됩니다.",
    relatedCorporations: ["농심", "오뚜기", "CJ제일제당"],
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 3,
  },
  {
    id: "00000021-0001-0001-0001-000000000021",
    corporationName: "광주정밀기계",
    corporationId: "6201-2345678",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "자동차 산업 전환기, 기계장비 수주 변동성 확대",
    summary: "전기차 전환 가속화로 인해 기계장비제조업(C29)의 기존 내연기관 관련 수주가 감소하는 한편, 전기차 부품 장비 수요가 증가하고 있습니다.",
    source: "한국기계산업진흥회",
    detectedAt: "4시간 전",
    detailCategory: "산업 충격",
    relevanceNote: "광주정밀기계는 자동차 부품 장비 제조 비중이 높아 산업 전환기 영향을 받을 수 있습니다.",
    relatedCorporations: ["두산공작기계", "화천기계"],
    impact: "neutral",
    impactStrength: "medium",
    evidenceCount: 5,
  },
  {
    id: "00000022-0001-0001-0001-000000000022",
    corporationName: "익산바이오텍",
    corporationId: "4301-3456789",
    signalCategory: "industry",
    signalSubType: "market",
    status: "new",
    title: "바이오의약품 시장 성장세 지속, R&D 투자 확대",
    summary: "글로벌 바이오의약품 시장이 연평균 8% 성장을 지속하고 있으며, 국내 의약품제조업(C21)의 R&D 투자도 증가 추세입니다.",
    source: "한국바이오협회",
    detectedAt: "5시간 전",
    detailCategory: "산업 충격",
    relevanceNote: "익산바이오텍은 바이오시밀러 개발에 주력하고 있어 시장 성장의 수혜가 예상됩니다.",
    relatedCorporations: ["셀트리온", "삼성바이오로직스"],
    impact: "opportunity",
    impactStrength: "high",
    evidenceCount: 4,
  },
  {
    id: "00000023-0001-0001-0001-000000000023",
    corporationName: "나주태양에너지",
    corporationId: "6701-4567890",
    signalCategory: "industry",
    signalSubType: "market",
    status: "resolved",
    title: "신재생에너지 발전 비중 확대, 전기업 투자 증가",
    summary: "정부의 탄소중립 정책에 따라 신재생에너지 발전 비중이 확대되고 있으며, 전기업(D35) 전반의 설비 투자가 증가하고 있습니다.",
    source: "한국에너지공단",
    detectedAt: "어제",
    detailCategory: "산업 충격",
    relevanceNote: "나주태양에너지는 태양광 발전 사업자로, 정책적 수혜가 기대됩니다.",
    relatedCorporations: ["한화솔루션", "OCI"],
    impact: "opportunity",
    impactStrength: "medium",
    evidenceCount: 3,
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

        {/* Signal type explanation banner */}
        <div className="bg-muted/50 rounded-lg border border-border px-4 py-3 mb-6">
          <p className="text-sm text-muted-foreground">
            기업이 속한 산업 전반의 변화 및 동향 기준 시그널입니다.
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