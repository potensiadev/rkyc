import { TrendingUp, Clock, CheckCircle2, AlertCircle } from "lucide-react";

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtext: string;
  trend?: {
    value: string;
    positive: boolean;
  };
}

function StatCard({ icon: Icon, label, value, subtext, trend }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-5">
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        {trend && (
          <span className={`text-xs font-medium ${trend.positive ? "text-success" : "text-destructive"}`}>
            {trend.value}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl font-semibold text-foreground">{value}</p>
        <p className="text-sm font-medium text-foreground mt-1">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{subtext}</p>
      </div>
    </div>
  );
}

export function SignalStats() {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <StatCard
        icon={AlertCircle}
        label="신규 시그널"
        value={12}
        subtext="금일 감지됨"
        trend={{ value: "+3", positive: false }}
      />
      <StatCard
        icon={Clock}
        label="검토 대기"
        value={18}
        subtext="담당자 배정 필요"
      />
      <StatCard
        icon={CheckCircle2}
        label="금주 완료"
        value={23}
        subtext="이번 주 처리 건수"
        trend={{ value: "+15%", positive: true }}
      />
      <StatCard
        icon={TrendingUp}
        label="모니터링 기업"
        value={156}
        subtext="전체 관리 대상"
      />
    </div>
  );
}
