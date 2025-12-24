import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard, SignalType, SignalStatus } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { SignalStats } from "@/components/signals/SignalStats";

interface Signal {
  id: string;
  corporationName: string;
  corporationId: string;
  signalType: SignalType;
  status: SignalStatus;
  title: string;
  summary: string;
  source: string;
  detectedAt: string;
  category: string;
}

const mockSignals: Signal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    corporationId: "124-81-00998",
    signalType: "news",
    status: "new",
    title: "삼성전자, 반도체 사업부 대규모 인력 구조조정 검토",
    summary: "삼성전자가 반도체 사업부의 경쟁력 강화를 위해 대규모 인력 재배치를 검토 중인 것으로 알려졌습니다. 이번 조치는 글로벌 반도체 시장의 수요 변화에 대응하기 위한 전략적 결정으로 분석됩니다. (참고용 요약)",
    source: "연합뉴스",
    detectedAt: "10분 전",
    category: "인사/조직",
  },
  {
    id: "2",
    corporationName: "현대자동차",
    corporationId: "101-81-15555",
    signalType: "financial",
    status: "new",
    title: "현대자동차 2024년 3분기 영업이익 전년 대비 15% 감소",
    summary: "현대자동차의 2024년 3분기 영업이익이 전년 동기 대비 15% 감소한 것으로 잠정 집계되었습니다. 주요 원인으로 원자재 가격 상승과 환율 변동이 지목되고 있습니다. (검토용 자료)",
    source: "금융감독원 전자공시",
    detectedAt: "25분 전",
    category: "실적/재무",
  },
  {
    id: "3",
    corporationName: "카카오",
    corporationId: "120-81-47521",
    signalType: "regulatory",
    status: "review",
    title: "공정거래위원회, 카카오 플랫폼 독점 관련 조사 착수",
    summary: "공정거래위원회가 카카오의 플랫폼 시장 지배력 남용 혐의에 대한 본격적인 조사에 착수했습니다. 조사 결과에 따라 시정명령 또는 과징금 부과 가능성이 있습니다. (참고 정보)",
    source: "공정거래위원회",
    detectedAt: "1시간 전",
    category: "규제/법률",
  },
  {
    id: "4",
    corporationName: "LG에너지솔루션",
    corporationId: "110-81-12345",
    signalType: "industry",
    status: "review",
    title: "전기차 배터리 산업 전반 수요 둔화 조짐",
    summary: "글로벌 전기차 시장의 성장 속도가 예상보다 더딘 것으로 나타나면서, 배터리 산업 전반에 영향을 미칠 수 있다는 분석이 제기되고 있습니다. 관련 기업 검토가 필요합니다. (요약 자료)",
    source: "한국에너지공단",
    detectedAt: "2시간 전",
    category: "시장 동향",
  },
  {
    id: "5",
    corporationName: "네이버",
    corporationId: "220-81-62517",
    signalType: "news",
    status: "resolved",
    title: "네이버, AI 스타트업 인수 완료 공시",
    summary: "네이버가 국내 AI 스타트업 인수를 공식 완료했습니다. 이번 인수를 통해 네이버는 AI 검색 및 추천 기술 역량을 강화할 것으로 예상됩니다. 검토 완료. (참고)",
    source: "전자공시시스템",
    detectedAt: "어제",
    category: "인수합병",
  },
];

export default function SignalInbox() {
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
        <SignalFilters />

        {/* Signal list */}
        <div className="space-y-3">
          {mockSignals.map((signal) => (
            <SignalCard key={signal.id} {...signal} />
          ))}
        </div>

        {/* Empty state placeholder */}
        {mockSignals.length === 0 && (
          <div className="text-center py-16 bg-card rounded-lg border border-border">
            <p className="text-muted-foreground">현재 검토가 필요한 시그널이 없습니다.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
