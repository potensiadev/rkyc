import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { Signal, SignalStatus } from "@/types/signal";
import { Factory, Loader2 } from "lucide-react";
import { useSignals } from "@/hooks/useApi";

export default function IndustrySignalPage() {
  const navigate = useNavigate();
  const { data: signals = [], isLoading } = useSignals({ signal_type: 'INDUSTRY' });
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      if (signal.signalCategory !== 'industry') return false;
      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus, signals]);

  const counts = useMemo(() => {
    const industrySignals = signals.filter(s => s.signalCategory === 'industry');
    return {
      all: industrySignals.length,
      new: industrySignals.filter(s => s.status === "new").length,
      review: industrySignals.filter(s => s.status === "review").length,
      resolved: industrySignals.filter(s => s.status === "resolved").length,
    };
  }, [signals]);

  const handleViewDetail = (signal: Signal) => {
    navigate(`/signals/${signal.id}`);
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
        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {filteredSignals.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                onViewDetail={handleViewDetail}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && filteredSignals.length === 0 && (
          <div className="text-center py-16 bg-card rounded-lg border border-border">
            <p className="text-muted-foreground">선택한 조건에 해당하는 산업 시그널이 없습니다.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
