import { Building2, Factory, Globe, Clock, CheckCircle2, AlertCircle } from "lucide-react";

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtext: string;
  trend?: {
    value: string;
    positive: boolean;
  };
  colorClass?: string;
}

function StatCard({ icon: Icon, label, value, subtext, trend, colorClass }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-5">
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-lg bg-accent flex items-center justify-center ${colorClass ? colorClass.replace('text-', 'bg-').replace(/\]$/, '/10]') : ''}`}>
          <Icon className={`w-5 h-5 ${colorClass || 'text-primary'}`} />
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
    <div className="grid grid-cols-6 gap-4 mb-6">
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
        icon={Building2}
        label="직접 시그널"
        value={5}
        subtext="기업 직접 관련"
        colorClass="text-signal-direct"
      />
      <StatCard
        icon={Factory}
        label="산업 시그널"
        value={2}
        subtext="산업 동향"
        colorClass="text-signal-industry"
      />
      <StatCard
        icon={Globe}
        label="환경 시그널"
        value={2}
        subtext="외부 환경 변화"
        colorClass="text-signal-environment"
      />
    </div>
  );
}
