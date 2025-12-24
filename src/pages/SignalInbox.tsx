import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { SignalStats } from "@/components/signals/SignalStats";
import { SignalDetailPanel } from "@/components/signals/SignalDetailPanel";
import { Signal, SignalCategory, SignalStatus } from "@/types/signal";

const mockSignals: Signal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "124-81-00998",
    signalCategory: "direct",
    signalSubType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다. 이번 조치는 글로벌 반도체 시장의 수요 변화에 대응하기 위한 전략적 결정으로 분석됩니다. (참고용 요약)",
    source: "연합뉴스",
    sourceUrl: "https://example.com",
    detectedAt: "10분 전",
    detailCategory: "인사/조직",
  },
  {
    id: "2",
    corporationName: "현대자동차",
    corporationId: "101-81-15555",
    signalCategory: "direct",
    signalSubType: "financial",
    status: "new",
    title: "현대자동차 2024년 3분기 영업이익 전년 대비 15% 감소",
    summary: "현대자동차의 2024년 3분기 영업이익이 전년 동기 대비 15% 감소한 것으로 잠정 집계되었습니다. 주요 원인으로 원자재 가격 상승과 환율 변동이 지목되고 있습니다. (검토용 자료)",
    source: "금융감독원 전자공시",
    detectedAt: "25분 전",
    detailCategory: "실적/재무",
  },
  {
    id: "3",
    corporationName: "카카오",
    corporationId: "120-81-47521",
    signalCategory: "direct",
    signalSubType: "regulatory",
    status: "review",
    title: "공정거래위원회, 카카오 플랫폼 독점 관련 조사 착수",
    summary: "공정거래위원회가 카카오의 플랫폼 시장 지배력 남용 혐의에 대한 본격적인 조사에 착수했습니다. 조사 결과에 따라 시정명령 또는 과징금 부과 가능성이 있습니다. (참고 정보)",
    source: "공정거래위원회",
    detectedAt: "1시간 전",
    detailCategory: "규제/법률",
  },
  {
    id: "4",
    corporationName: "LG에너지솔루션",
    corporationId: "110-81-12345",
    signalCategory: "industry",
    signalSubType: "market",
    status: "review",
    title: "전기차 배터리 산업 전반 수요 둔화 조짐",
    summary: "글로벌 전기차 시장의 성장 속도가 예상보다 더딘 것으로 나타나면서, 배터리 산업 전반에 영향을 미칠 수 있다는 분석이 제기되고 있습니다. 관련 기업 검토가 필요합니다. (요약 자료)",
    source: "한국에너지공단",
    detectedAt: "2시간 전",
    detailCategory: "시장 동향",
    relevanceNote: "LG에너지솔루션은 글로벌 2차전지 시장 점유율 상위 기업으로, 업계 전반의 수요 변화에 직접적 영향을 받을 수 있습니다.",
    relatedCorporations: ["삼성SDI", "SK온", "CATL"],
  },
  {
    id: "5",
    corporationName: "네이버",
    corporationId: "220-81-62517",
    signalCategory: "direct",
    signalSubType: "governance",
    status: "resolved",
    title: "네이버, AI 스타트업 인수 완료 공시",
    summary: "네이버가 국내 AI 스타트업 인수를 공식 완료했습니다. 이번 인수를 통해 네이버는 AI 검색 및 추천 기술 역량을 강화할 것으로 예상됩니다. 검토 완료. (참고)",
    source: "전자공시시스템",
    detectedAt: "어제",
    detailCategory: "인수합병",
  },
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
  },
];

export default function SignalInbox() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");
  const [activeCategory, setActiveCategory] = useState<SignalCategory | "all">("all");

  const filteredSignals = useMemo(() => {
    return mockSignals.filter((signal) => {
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      if (activeCategory !== "all" && signal.signalCategory !== activeCategory) return false;
      return true;
    });
  }, [activeStatus, activeCategory]);

  const counts = useMemo(() => ({
    all: mockSignals.length,
    new: mockSignals.filter(s => s.status === "new").length,
    review: mockSignals.filter(s => s.status === "review").length,
    resolved: mockSignals.filter(s => s.status === "resolved").length,
    direct: mockSignals.filter(s => s.signalCategory === "direct").length,
    industry: mockSignals.filter(s => s.signalCategory === "industry").length,
    environment: mockSignals.filter(s => s.signalCategory === "environment").length,
  }), []);

  const handleViewDetail = (signal: Signal) => {
    setSelectedSignal(signal);
    setDetailOpen(true);
  };

  return (
    <MainLayout>
      <div className="max-w-6xl">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">시그널 인박스</h1>
          <p className="text-muted-foreground mt-1">
            AI가 감지한 기업 관련 시그널을 검토하세요. 모든 내용은 참고용으로 제공됩니다.
          </p>
        </div>

        {/* Stats */}
        <SignalStats />

        {/* Filters */}
        <SignalFilters 
          activeStatus={activeStatus}
          activeCategory={activeCategory}
          onStatusChange={setActiveStatus}
          onCategoryChange={setActiveCategory}
          counts={counts}
        />

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
            <p className="text-muted-foreground">선택한 조건에 해당하는 시그널이 없습니다.</p>
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
