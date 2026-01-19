import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Calendar,
  TrendingDown,
  TrendingUp,
  FileText,
  AlertTriangle,
  ArrowUpRight,
  Loader2
} from "lucide-react";
import { Signal } from "@/types/signal";
import { useSignals } from "@/hooks/useApi";
import { useMemo } from "react";

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
  // Fetch all recent signals
  const { data: signals = [], isLoading } = useSignals({ limit: 50 });

  const { riskSignals, opportunitySignals, referenceSignals } = useMemo(() => {
    const risk = signals.filter(s => s.impact === 'risk').slice(0, 3);
    const opportunity = signals.filter(s => s.impact === 'opportunity').slice(0, 3);
    // Reference: Business/Environment/Industry signals that are neutral or just not in the top risk/opp lists
    // For now, let's grab Industry/Environment signals that aren't already shown
    const shownIds = new Set([...risk.map(s => s.id), ...opportunity.map(s => s.id)]);

    const reference = signals
      .filter(s => !shownIds.has(s.id))
      .filter(s => s.signalCategory === 'industry' || s.signalCategory === 'environment' || s.impact === 'neutral')
      .slice(0, 4);

    return { riskSignals: risk, opportunitySignals: opportunity, referenceSignals: reference };
  }, [signals]);

  const handleSignalClick = (signalId: string) => {
    navigate(`/signals/${signalId}`);
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </MainLayout>
    );
  }

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
            {riskSignals.length > 0 ? (
              riskSignals.map((signal) => (
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
                    <p className="text-sm text-muted-foreground line-clamp-2">{signal.summary}</p>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-sm text-muted-foreground p-4 bg-muted/30 rounded-lg border border-border border-dashed text-center">
                감지된 위험 시그널이 없습니다.
              </div>
            )}
          </div>
        </section>

        {/* Opportunity Signals */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <h2 className="text-lg font-semibold">기회(Opportunity) 시그널</h2>
          </div>

          <div className="grid gap-4">
            {opportunitySignals.length > 0 ? (
              opportunitySignals.map((signal) => (
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
                    <p className="text-sm text-muted-foreground line-clamp-2">{signal.summary}</p>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-sm text-muted-foreground p-4 bg-muted/30 rounded-lg border border-border border-dashed text-center">
                감지된 기회 시그널이 없습니다.
              </div>
            )}
          </div>
        </section>

        {/* Reference Events */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-zinc-500" />
            <h2 className="text-lg font-semibold">참고(Reference) 이슈</h2>
          </div>

          <div className="grid gap-4">
            {referenceSignals.length > 0 ? (
              referenceSignals.map((signal) => (
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
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{signal.summary}</p>
                    <div className="mt-2 flex gap-2">
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">{signal.corporationName}</span>
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">{signal.signalCategory}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground p-4 bg-muted/30 rounded-lg border border-border border-dashed text-center">
                추가적인 참고 이슈가 없습니다.
              </div>
            )}
          </div>
        </section>

      </div>
    </MainLayout>
  );
}
