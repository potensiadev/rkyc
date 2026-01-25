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

// Stance badge config
const STANCE_CONFIG: Record<string, { bg: string; text: string; border: string; label: string }> = {
  CAUTION: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", label: "주의" },
  MONITORING: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200", label: "관찰" },
  STABLE: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200", label: "안정" },
  POSITIVE: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", label: "긍정" },
};

export function GroupedSignalCard({
  corporationId,
  corporationName,
  signals,
  loanInsight,
  onSignalClick,
  onCorporationClick,
}: GroupedSignalCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const stanceConfig = loanInsight ? STANCE_CONFIG[loanInsight.stance_level] : null;

  // 시그널 통계
  const riskCount = signals.filter((s) => s.impact === "risk").length;
  const oppCount = signals.filter((s) => s.impact === "opportunity").length;
  const hasHighRisk = signals.some((s) => s.impact === "risk" && s.impactStrength === "high");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "bg-card rounded-xl border overflow-hidden",
        hasHighRisk ? "border-red-200 dark:border-red-800" : "border-border"
      )}
    >
      {/* ============================================================ */}
      {/* Group Header - 기업 정보 (1회만 표시) */}
      {/* ============================================================ */}
      <div
        className={cn(
          "p-4 cursor-pointer transition-colors",
          hasHighRisk ? "bg-red-50/50 dark:bg-red-950/20" : "bg-muted/30 hover:bg-muted/50"
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          {/* Left: 기업 정보 */}
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div
              className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg",
                hasHighRisk
                  ? "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300"
                  : "bg-primary/10 text-primary"
              )}
            >
              {corporationName.charAt(0)}
            </div>

            {/* Name + ID */}
            <div>
              <div className="flex items-center gap-2">
                <h3
                  className="font-semibold text-foreground hover:text-primary cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCorporationClick(corporationId);
                  }}
                >
                  {corporationName}
                </h3>
                {stanceConfig && (
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded border font-medium",
                      stanceConfig.bg,
                      stanceConfig.text,
                      stanceConfig.border
                    )}
                  >
                    {loanInsight?.stance_label || stanceConfig.label}
                  </span>
                )}
                {hasHighRisk && (
                  <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">{corporationId}</p>
            </div>
          </div>

          {/* Right: 시그널 카운트 + 확장 아이콘 */}
          <div className="flex items-center gap-4">
            {/* 시그널 통계 */}
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-muted-foreground">
                시그널 <span className="font-semibold text-foreground">{signals.length}</span>건
              </span>
              {riskCount > 0 && (
                <span className="flex items-center gap-1 text-red-600">
                  <TrendingDown className="w-3 h-3" />
                  {riskCount}
                </span>
              )}
              {oppCount > 0 && (
                <span className="flex items-center gap-1 text-green-600">
                  <TrendingUp className="w-3 h-3" />
                  {oppCount}
                </span>
              )}
            </div>

            {/* 확장/축소 */}
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
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
          >
            <div className="divide-y divide-border">
              {signals.map((signal) => {
                const TypeIcon = TypeIcons[signal.signalCategory] || Building2;
                const ImpactIcon = ImpactIcons[signal.impact] || FileText;
                const typeConfig = SIGNAL_TYPE_CONFIG?.[signal.signalCategory];
                const impactConfig = SIGNAL_IMPACT_CONFIG?.[signal.impact];
                const isRisk = signal.impact === "risk";
                const isOpp = signal.impact === "opportunity";

                return (
                  <div
                    key={signal.id}
                    className={cn(
                      "px-4 py-3 cursor-pointer transition-colors hover:bg-muted/50 flex items-start gap-3",
                      // 좌측 보더로 위험/기회 구분
                      "border-l-4",
                      isRisk
                        ? "border-l-red-400"
                        : isOpp
                        ? "border-l-green-400"
                        : "border-l-gray-200"
                    )}
                    onClick={() => onSignalClick(signal.id)}
                  >
                    {/* Impact Icon */}
                    <div
                      className={cn(
                        "w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5",
                        impactConfig?.bgClass || "bg-gray-100"
                      )}
                    >
                      <ImpactIcon
                        className={cn("w-4 h-4", impactConfig?.colorClass || "text-gray-500")}
                      />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Title + Badges */}
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <h4 className="text-sm font-medium text-foreground line-clamp-1">
                          {signal.title}
                        </h4>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span
                            className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded",
                              typeConfig?.bgClass,
                              typeConfig?.colorClass
                            )}
                          >
                            {typeConfig?.label}
                          </span>
                          <span
                            className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded",
                              impactConfig?.bgClass,
                              impactConfig?.colorClass
                            )}
                          >
                            {impactConfig?.label}
                          </span>
                        </div>
                      </div>

                      {/* Summary */}
                      <p className="text-xs text-muted-foreground line-clamp-1 mb-1.5">
                        {signal.summary}
                      </p>

                      {/* Meta */}
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                        <span>근거 {signal.evidenceCount || 0}건</span>
                        <span>{signal.detectedAt}</span>
                      </div>
                    </div>

                    {/* Arrow */}
                    <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                );
              })}
            </div>

            {/* 기업 상세 보기 링크 */}
            <div
              className="px-4 py-2.5 bg-muted/30 border-t border-border flex items-center justify-center gap-2 cursor-pointer hover:bg-muted/50 transition-colors text-xs text-muted-foreground hover:text-primary"
              onClick={(e) => {
                e.stopPropagation();
                onCorporationClick(corporationId);
              }}
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>{corporationName} 상세 보고서 보기</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
