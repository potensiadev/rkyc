import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Signal, SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  FileText,
  Building2,
  Factory,
  Globe,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ApiLoanInsightSummary } from "@/hooks/useApi";
import { StatusBadge, Tag } from "@/components/premium";

interface GroupedSignalCardProps {
  corporationId: string;
  corporationName: string;
  signals: (Signal & { summary?: string; evidenceCount?: number })[];
  loanInsight?: ApiLoanInsightSummary;
  onSignalClick: (id: string) => void;
  onCorporationClick: (id: string) => void;
}

// Helper icons
const TypeIcons = {
  direct: Building2,
  industry: Factory,
  environment: Globe,
};

const ImpactIcons = {
  risk: TrendingDown,
  opportunity: TrendingUp,
  neutral: FileText,
};

export function GroupedSignalCard({
  corporationId,
  corporationName,
  signals,
  loanInsight,
  onSignalClick,
  onCorporationClick,
}: GroupedSignalCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Map stance to StatusBadge variant
  const getStanceVariant = (level: string) => {
    switch (level) {
      case 'CAUTION': return 'danger';
      case 'MONITORING': return 'warning';
      case 'STABLE': return 'success';
      case 'POSITIVE': return 'brand';
      default: return 'neutral';
    }
  };

  const stanceVariant = loanInsight ? getStanceVariant(loanInsight.stance_level) : null;
  const stanceLabel = loanInsight?.stance_label || "No Insight";

  // 시그널 통계
  const riskCount = signals.filter((s) => s.impact === "risk").length;
  const oppCount = signals.filter((s) => s.impact === "opportunity").length;
  const hasHighRisk = signals.some((s) => s.impact === "risk" && s.impactStrength === "high");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "relative rounded-3xl bg-white/70 backdrop-blur-xl border border-white/50 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden transition-all duration-300",
        hasHighRisk ? "shadow-[0_0_20px_rgba(244,63,94,0.1)] border-rose-100" : "hover:shadow-[0_8px_30px_-8px_rgba(0,0,0,0.08)] hover:bg-white/90"
      )}
    >
      {/* ============================================================ */}
      {/* Group Header - 기업 정보 (1회만 표시) */}
      {/* ============================================================ */}
      <div
        className={cn(
          "p-4 cursor-pointer transition-colors border-b border-transparent",
          isExpanded ? "border-slate-100/50" : ""
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          {/* Left: 기업 정보 */}
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <div
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg shadow-sm transition-colors",
                hasHighRisk
                  ? "bg-rose-50 text-rose-600 border border-rose-100"
                  : "bg-indigo-50 text-indigo-600 border border-indigo-100"
              )}
            >
              {corporationName.charAt(0)}
            </div>

            {/* Name + ID */}
            <div>
              <div className="flex items-center gap-2">
                <h3
                  className="text-base font-bold text-slate-800 hover:text-indigo-600 cursor-pointer transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCorporationClick(corporationId);
                  }}
                >
                  {corporationName}
                </h3>
                {loanInsight && (
                  <StatusBadge variant={stanceVariant as any} className="h-5 px-1.5 text-[10px]">{stanceLabel}</StatusBadge>
                )}
                {hasHighRisk && (
                  <StatusBadge variant="danger" className="animate-pulse h-5 px-1.5 text-[10px]">고위험</StatusBadge>
                )}
              </div>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">{corporationId}</p>
            </div>
          </div>

          {/* Right: 시그널 카운트 + 확장 아이콘 */}
          <div className="flex items-center gap-6">
            {/* 시그널 통계 */}
            <div className="flex items-center gap-3 text-xs font-medium">
              {riskCount > 0 && (
                <div className="flex flex-col items-center">
                  <span className="text-rose-500 font-bold text-base leading-none">{riskCount}</span>
                  <span className="text-rose-400/80 text-[9px] uppercase font-semibold">Risk</span>
                </div>
              )}
              {oppCount > 0 && (
                <div className="flex flex-col items-center">
                  <span className="text-emerald-500 font-bold text-base leading-none">{oppCount}</span>
                  <span className="text-emerald-400/80 text-[9px] uppercase font-semibold">Opp</span>
                </div>
              )}
              {(riskCount === 0 && oppCount === 0) && (
                <span className="text-slate-400 text-[10px]">No Signals</span>
              )}
            </div>

            {/* 확장/축소 */}
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="w-7 h-7 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </motion.div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* Signal List - 개별 시그널 (압축) */}
      {/* ============================================================ */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-slate-50/30"
          >
            <div className="flex flex-col gap-1 p-2">
              {signals.slice(0, 3).map((signal) => {
                const TypeIcon = TypeIcons[signal.signalCategory] || Building2;
                const ImpactIcon = ImpactIcons[signal.impact] || FileText;
                const typeConfig = SIGNAL_TYPE_CONFIG?.[signal.signalCategory];
                const isRisk = signal.impact === "risk";
                const isOpp = signal.impact === "opportunity";

                return (
                  <div
                    key={signal.id}
                    className="relative group p-2.5 rounded-lg hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-100 transition-all cursor-pointer flex items-center gap-3"
                    onClick={() => onSignalClick(signal.id)}
                  >
                    {/* Impact Indicator (Dot + Icon) */}
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                      isRisk ? "bg-rose-50 text-rose-500 group-hover:bg-rose-100" :
                        isOpp ? "bg-emerald-50 text-emerald-500 group-hover:bg-emerald-100" :
                          "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
                    )}>
                      <ImpactIcon className="w-4 h-4" />
                      {isRisk && <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 bg-rose-500 rounded-full border border-white" />}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Title + Badges */}
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <h4 className="text-sm font-bold text-slate-700 group-hover:text-indigo-900 transition-colors line-clamp-1">
                          {signal.title}
                        </h4>
                        <Tag className="text-[9px] py-0 px-1.5 h-4 bg-white border-slate-200 opacity-0 group-hover:opacity-100 transition-opacity">
                          {typeConfig?.label}
                        </Tag>
                      </div>

                      {/* Summary - Only 1 Line */}
                      <p className="text-xs text-slate-500 line-clamp-1 leading-normal">
                        {signal.summary}
                      </p>
                    </div>

                    {/* Meta Info (Hidden on mobile, visible on group hover) */}
                    <div className="hidden sm:flex items-center gap-2 text-[10px] text-slate-300 group-hover:text-slate-400 transition-colors whitespace-nowrap opacity-0 group-hover:opacity-100">
                      <span>{new Date(signal.detectedAt).toLocaleDateString()}</span>
                      <ChevronRight className="w-3 h-3" />
                    </div>
                  </div>
                );
              })}

              {/* More Signals Indicator */}
              {signals.length > 3 && (
                <div className="px-3 py-1 text-center">
                  <span className="text-[10px] text-slate-400 font-medium">
                    + {signals.length - 3} more signals
                  </span>
                </div>
              )}
            </div>

            {/* 기업 상세 보기 링크 */}
            <div
              className="py-2.5 bg-slate-50 border-t border-slate-100 flex items-center justify-center gap-1.5 cursor-pointer hover:bg-slate-100 transition-colors text-[11px] font-semibold text-slate-500 hover:text-indigo-600"
              onClick={(e) => {
                e.stopPropagation();
                onCorporationClick(corporationId);
              }}
            >
              <span>View Full Analysis</span>
              <ExternalLink className="w-3 h-3" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
