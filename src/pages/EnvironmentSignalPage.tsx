import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { SignalCard } from "@/components/signals/SignalCard";
import { Signal, SignalStatus } from "@/types/signal";
import { Globe, Loader2, Info } from "lucide-react";
import { useSignals } from "@/hooks/useApi";
import {
  DynamicBackground,
  StatusBadge
} from "@/components/premium";
import { motion } from "framer-motion";

export default function EnvironmentSignalPage() {
  const navigate = useNavigate();
  const { data: signals = [], isLoading } = useSignals({ signal_type: 'ENVIRONMENT' });
  const [activeStatus, setActiveStatus] = useState<SignalStatus | "all">("all");

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      // Ensure we only show environment signals (redundant if API filters, but safe)
      if (signal.signalCategory !== 'environment') return false;

      if (activeStatus !== "all" && signal.status !== activeStatus) return false;
      return true;
    });
  }, [activeStatus, signals]);

  const counts = useMemo(() => {
    const environmentSignals = signals.filter(s => s.signalCategory === 'environment');
    return {
      all: environmentSignals.length,
      new: environmentSignals.filter(s => s.status === "new").length,
      review: environmentSignals.filter(s => s.status === "review").length,
      resolved: environmentSignals.filter(s => s.status === "resolved").length,
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

  if (isLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="flex justify-center items-center h-[calc(100vh-100px)]">
          <Loader2 className="w-10 h-10 animate-spin text-emerald-500" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-6xl mx-auto pb-20 relative z-10">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 pt-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center shadow-sm">
              <Globe className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Macro Environment</h1>
                <StatusBadge variant="neutral" className="bg-white/50 backdrop-blur-sm">Global Watch</StatusBadge>
              </div>
              <p className="text-slate-500 font-medium">
                Macroeconomic indicators, regulatory changes, and geopolitical events.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Info Banner */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-emerald-50/50 backdrop-blur-md rounded-xl border border-emerald-100 px-5 py-4 mb-8 flex items-start gap-3"
        >
          <Info className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-emerald-900 leading-relaxed font-medium">
            Environment signals cover external factors such as policy shifts, exchange rate volatility, and global market trends. Essential for stress testing and scenario planning.
          </p>
        </motion.div>

        {/* Status filters */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6"
        >
          <div className="flex items-center gap-1 bg-white/50 backdrop-blur-sm rounded-lg p-1.5 border border-slate-200/60 shadow-sm w-full sm:w-auto overflow-x-auto">
            {statusFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveStatus(filter.id as SignalStatus | "all")}
                className={`
                  px-4 py-2 rounded-md text-sm font-bold transition-all whitespace-nowrap
                  ${activeStatus === filter.id
                    ? "bg-white text-emerald-600 shadow-md ring-1 ring-slate-100"
                    : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                  }
                `}
              >
                {filter.label}
                <span className={`ml-2 text-xs opacity-80 ${activeStatus === filter.id ? "text-emerald-400" : "text-slate-400"}`}>
                  {filter.count}
                </span>
              </button>
            ))}
          </div>

          <select className="text-sm border border-slate-200 rounded-lg px-4 py-2.5 bg-white/80 text-slate-700 font-medium focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none w-full sm:w-auto cursor-pointer">
            <option value="recent">Sort by: Recent</option>
            <option value="corporation">Sort by: Company</option>
          </select>
        </motion.div>

        {/* Signal list */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-3"
        >
          {filteredSignals.map((signal, index) => (
            <motion.div
              key={signal.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + (index * 0.05) }}
            >
              <SignalCard
                signal={signal}
                onViewDetail={handleViewDetail}
              />
            </motion.div>
          ))}
        </motion.div>

        {/* Empty state */}
        {filteredSignals.length === 0 && (
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-50 mb-4">
              <Globe className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-700 mb-1">No Environment Signals Found</h3>
            <p className="text-slate-400">There are no signals matching your current filters.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
