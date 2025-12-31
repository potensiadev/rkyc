import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Calendar,
  TrendingDown,
  TrendingUp,
  FileText,
  AlertTriangle,
  ArrowUpRight
} from "lucide-react";
import { Signal } from "@/types/signal";

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
];

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
      <div className="max-w-4xl space-y-8">
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
          <p className="text-muted-foreground">
            오늘 감지된 주요 시그널과 놓쳐서는 안 될 중요 이슈를 정리해 드립니다.
          </p>
        </div>

        {/* Risk Signals */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-semibold">주요 위험(Risk) 시그널</h2>
          </div>

          <div className="grid gap-4">
            {todayRiskSignals.map((signal) => (
              <Card
                key={signal.id}
                className="cursor-pointer hover:border-red-400/50 transition-colors"
                onClick={() => handleSignalClick(signal.id)}
              >
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-medium text-muted-foreground">{signal.corporationName}</span>
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] rounded font-bold dark:bg-red-900/30 dark:text-red-400">RISK</span>
                  </div>
                  <CardTitle className="text-base leading-tight">{signal.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{signal.summary}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Opportunity Signals */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <h2 className="text-lg font-semibold">기회(Opportunity) 시그널</h2>
          </div>

          <div className="grid gap-4">
            {todayOpportunitySignals.map((signal) => (
              <Card
                key={signal.id}
                className="cursor-pointer hover:border-green-400/50 transition-colors"
                onClick={() => handleSignalClick(signal.id)}
              >
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-medium text-muted-foreground">{signal.corporationName}</span>
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] rounded font-bold dark:bg-green-900/30 dark:text-green-400">OPPORTUNITY</span>
                  </div>
                  <CardTitle className="text-base leading-tight">{signal.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{signal.summary}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Reference Events */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-zinc-500" />
            <h2 className="text-lg font-semibold">참고(Reference) 이슈</h2>
          </div>

          <div className="grid gap-4">
            {referenceEvents.map((signal) => (
              <div
                key={signal.id}
                className="flex items-start gap-4 p-4 border border-border rounded-lg bg-card hover:bg-muted/50 transition-colors cursor-pointer"
                onClick={() => handleSignalClick(signal.id)}
              >
                <div className="mt-1">
                  <ArrowUpRight className="w-4 h-4 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground">{signal.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{signal.summary}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </MainLayout>
  );
}
