import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { Signal, SignalStatus } from "@/types/signal";
import { Building2, Loader2 } from "lucide-react";
import { useSignals } from "@/hooks/useApi";

export default function DirectSignalPage() {
  const navigate = useNavigate();
  const { data: signals = [], isLoading } = useSignals({ signal_type: 'DIRECT' });
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      // Ensure we only show direct signals (redundant if API filters, but safe)
      if (signal.signalCategory !== 'direct') return false;

      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus, signals]);

  const counts = useMemo(() => {
    const directSignals = signals.filter(s => s.signalCategory === 'direct');
    return {
      all: directSignals.length,
      new: directSignals.filter(s => s.status === "new").length,
      review: directSignals.filter(s => s.status === "review").length,
      resolved: directSignals.filter(s => s.status === "resolved").length,
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
            <p className="text-muted-foreground">선택한 조건에 해당하는 직접 시그널이 없습니다.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
