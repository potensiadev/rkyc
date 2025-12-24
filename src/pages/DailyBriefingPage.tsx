import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { 
  Calendar, 
  TrendingDown, 
  TrendingUp, 
  FileText,
  Building2,
  Factory,
  Globe,
  ChevronRight
} from "lucide-react";
import { Signal, SIGNAL_TYPE_CONFIG } from "@/types/signal";

interface BriefingSignal {
  id: string;
  corporationName: string;
  signalCategory: Signal["signalCategory"];
  title: string;
  summary: string;
}

// Mock data for today's briefing
const todayRiskSignals: BriefingSignal[] = [
  {
    id: "1",
    corporationName: "삼성전자",
    signalCategory: "direct",
    title: "반도체 사업부 대규모 인력 구조조정 검토",
    summary: "글로벌 반도체 시장 침체 대응을 위한 조직 효율화 방안 검토 중",
  },
  {
    id: "2",
    corporationName: "현대중공업",
    signalCategory: "direct",
    title: "수주 지연에 따른 일부 사업부 가동률 저하",
    summary: "조선 업황 불확실성으로 인한 신규 수주 지연 발생",
  },
  {
    id: "3",
    corporationName: "포스코",
    signalCategory: "environment",
    title: "철강 원자재 가격 급등, 마진 압박 우려",
    summary: "국제 철광석 가격 상승으로 원가 부담 증가 예상",
  },
];

const todayOpportunitySignals: BriefingSignal[] = [
  {
    id: "7",
    corporationName: "SK하이닉스",
    signalCategory: "industry",
    title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    summary: "생성형 AI 확산에 따른 고대역폭 메모리 수요 증가",
  },
  {
    id: "8",
    corporationName: "LG에너지솔루션",
    signalCategory: "direct",
    title: "북미 전기차 배터리 공장 가동 시작",
    summary: "미국 IRA 정책 수혜로 현지 생산 능력 확대",
  },
];

const referenceEvents: BriefingSignal[] = [
  {
    id: "10",
    corporationName: "산업 전반",
    signalCategory: "industry",
    title: "12월 수출입 동향: 반도체 수출 전년 대비 증가",
    summary: "산업통상자원부 발표, 반도체 수출액 15% 증가",
  },
  {
    id: "11",
    corporationName: "금융 환경",
    signalCategory: "environment",
    title: "한국은행 기준금리 동결 결정",
    summary: "물가 안정세 속 경기 불확실성 고려한 결정",
  },
  {
    id: "12",
    corporationName: "규제 환경",
    signalCategory: "environment",
    title: "금융위원회, 기업대출 건전성 관리 강화 예고",
    summary: "2025년 1분기 시행 예정, 세부 지침 추후 발표",
  },
];

function getSignalTypeIcon(category: Signal["signalCategory"]) {
  switch (category) {
    case "direct":
      return Building2;
    case "industry":
      return Factory;
    case "environment":
      return Globe;
  }
}

// Get today's date in Korean format
function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  const weekday = weekdays[today.getDay()];
  return `${year}년 ${month}월 ${day}일 (${weekday})`;
}

export default function DailyBriefingPage() {
  const navigate = useNavigate();

  const handleSignalClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
  };

  return (
    <MainLayout>
      <div className="max-w-4xl">
        {/* Header with Date */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{getTodayDate()}</p>
              <h1 className="text-2xl font-semibold text-foreground">일일 RKYC 브리핑</h1>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-3 pl-[52px]">
            오늘 감지된 주요 시그널을 요약합니다. 상세 검토가 필요한 항목은 해당 시그널을 선택하여 확인하세요.
          </p>
        </div>

        {/* Section 1: Today's Risk Signals */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-risk/10 flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-risk" />
            </div>
            <h2 className="text-lg font-medium text-foreground">금일 위험 시그널</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {todayRiskSignals.length}건
            </span>
          </div>

          <div className="bg-card rounded-lg border border-border divide-y divide-border">
            {todayRiskSignals.map((signal) => {
              const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
              const TypeIcon = getSignalTypeIcon(signal.signalCategory);

              return (
                <div
                  key={signal.id}
                  onClick={() => handleSignalClick(signal.id)}
                  className="p-4 hover:bg-secondary/30 cursor-pointer transition-colors group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-foreground">
                          {signal.corporationName}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
                          <TypeIcon className="w-3 h-3" />
                          {typeConfig.label}
                        </span>
                      </div>
                      <p className="text-sm text-foreground font-medium mb-1">
                        {signal.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {signal.summary}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1 group-hover:text-primary transition-colors" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 2: Today's Opportunity Signals */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-opportunity/10 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-opportunity" />
            </div>
            <h2 className="text-lg font-medium text-foreground">금일 기회 시그널</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {todayOpportunitySignals.length}건
            </span>
          </div>

          <div className="bg-card rounded-lg border border-border divide-y divide-border">
            {todayOpportunitySignals.map((signal) => {
              const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
              const TypeIcon = getSignalTypeIcon(signal.signalCategory);

              return (
                <div
                  key={signal.id}
                  onClick={() => handleSignalClick(signal.id)}
                  className="p-4 hover:bg-secondary/30 cursor-pointer transition-colors group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-foreground">
                          {signal.corporationName}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
                          <TypeIcon className="w-3 h-3" />
                          {typeConfig.label}
                        </span>
                      </div>
                      <p className="text-sm text-foreground font-medium mb-1">
                        {signal.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {signal.summary}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1 group-hover:text-primary transition-colors" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 3: Reference Events */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
              <FileText className="w-4 h-4 text-muted-foreground" />
            </div>
            <h2 className="text-lg font-medium text-foreground">참고 이벤트</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {referenceEvents.length}건
            </span>
          </div>

          <div className="bg-card rounded-lg border border-border divide-y divide-border">
            {referenceEvents.map((event) => {
              const typeConfig = SIGNAL_TYPE_CONFIG[event.signalCategory];
              const TypeIcon = getSignalTypeIcon(event.signalCategory);

              return (
                <div
                  key={event.id}
                  className="p-4 hover:bg-secondary/30 cursor-pointer transition-colors group"
                  onClick={() => handleSignalClick(event.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm text-muted-foreground">
                          {event.corporationName}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
                          <TypeIcon className="w-3 h-3" />
                          {typeConfig.label}
                        </span>
                      </div>
                      <p className="text-sm text-foreground font-medium mb-1">
                        {event.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {event.summary}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1 group-hover:text-primary transition-colors" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Footer note */}
        <div className="text-center py-6 border-t border-border">
          <p className="text-xs text-muted-foreground">
            본 브리핑은 AI가 자동으로 생성한 참고 자료입니다. 최종 판단은 담당자가 수행합니다.
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
