import { motion } from "framer-motion";
import { Signal, SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import { AlertTriangle, TrendingUp, TrendingDown, FileText, Building2, Factory, Globe, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ApiLoanInsightSummary } from "@/hooks/useApi";

interface LevitatingCardProps {
    signal: Signal & { summary?: string, evidenceCount?: number };
    index: number;
    onClick: (id: string) => void;
    loanInsight?: ApiLoanInsightSummary;
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
const STANCE_CONFIG: Record<string, { bg: string; text: string; border: string }> = {
    CAUTION: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
    MONITORING: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
    STABLE: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
    POSITIVE: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
};

export function LevitatingCard({ signal, index, onClick, loanInsight }: LevitatingCardProps) {
    const TypeIcon = TypeIcons[signal.signalCategory] || Building2;
    const ImpactIcon = ImpactIcons[signal.impact] || FileText;

    const typeConfig = SIGNAL_TYPE_CONFIG?.[signal.signalCategory] || { label: "Unknown", colorClass: "text-gray-500", bgClass: "bg-gray-100" };
    const impactConfig = SIGNAL_IMPACT_CONFIG?.[signal.impact] || { label: "Unknown", colorClass: "text-gray-500", bgClass: "bg-gray-100" };

    const isHighRisk = signal.impact === "risk" && signal.impactStrength === "high";
    const stanceConfig = loanInsight ? STANCE_CONFIG[loanInsight.stance_level] : null;

    // Random delay for floating effect to avoid synchronized movement
    const randomDelay = Math.random() * 2;

    return (
        <motion.div
            layoutId={`card-${signal.id}`}
            className="relative group perspective-1000"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onClick(signal.id)}
        >
            <motion.div
                className={cn(
                    "relative h-full bg-card rounded-xl border p-5 cursor-pointer transition-colors duration-300",
                    isHighRisk
                        ? "border-destructive/30 bg-destructive/5 hover:border-destructive/50"
                        : "border-border hover:border-primary/50 hover:bg-muted/10",
                    "shadow-lg hover:shadow-xl"
                )}
                // Floating animation
                animate={{
                    y: [0, -8, 0],
                }}
                transition={{
                    y: {
                        duration: 4,
                        repeat: Infinity,
                        repeatType: "reverse",
                        ease: "easeInOut",
                        delay: randomDelay,
                    }
                }}
                // Hover 3D Logic can be complex, for now using simple scale/z-index
                whileHover={{
                    scale: 1.02,
                    zIndex: 20,
                }}
            >
                {/* Risk Pulse Overlay */}
                {isHighRisk && (
                    <motion.div
                        className="absolute inset-0 rounded-xl rounded-t-xl pointer-events-none"
                        animate={{ boxShadow: ["inset 0 0 0px rgba(220,38,38,0)", "inset 0 0 20px rgba(220,38,38,0.2)", "inset 0 0 0px rgba(220,38,38,0)"] }}
                        transition={{ duration: 2, repeat: Infinity }}
                    />
                )}

                {/* Card Header */}
                <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center bg-muted")}>
                            {/* Fallback avatar/logo */}
                            <span className="text-lg font-bold text-muted-foreground">
                                {signal.corporationName.charAt(0)}
                            </span>
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-semibold text-foreground leading-tight group-hover:text-primary transition-colors">
                                    {signal.corporationName}
                                </h3>
                                {/* Stance Badge - 핵심 가치 표시 */}
                                {loanInsight && stanceConfig && (
                                    <span className={cn(
                                        "text-[10px] px-1.5 py-0.5 rounded border font-medium whitespace-nowrap flex-shrink-0",
                                        stanceConfig.bg, stanceConfig.text, stanceConfig.border
                                    )}>
                                        {loanInsight.stance_label}
                                    </span>
                                )}
                            </div>
                            <p className="text-xs text-muted-foreground">{signal.corporationId}</p>
                        </div>
                    </div>

                    {isHighRisk && (
                        <div className="text-destructive animate-pulse">
                            <AlertTriangle className="w-5 h-5" />
                        </div>
                    )}
                </div>

                {/* Content Body */}
                <div className="space-y-3 mb-4">
                    <div className="flex flex-wrap gap-2 text-xs">
                        <span className={cn("px-2 py-1 rounded", typeConfig.bgClass, typeConfig.colorClass)}>
                            <TypeIcon className="w-3 h-3 inline mr-1" />
                            {typeConfig.label}
                        </span>
                        <span className={cn("px-2 py-1 rounded", impactConfig.bgClass, impactConfig.colorClass)}>
                            <ImpactIcon className="w-3 h-3 inline mr-1" />
                            {impactConfig.label}
                        </span>
                    </div>

                    <h4 className="text-sm font-medium line-clamp-2 min-h-[2.5rem]">
                        {signal.title}
                    </h4>

                    <p className="text-xs text-muted-foreground line-clamp-2">
                        {signal.summary}
                    </p>
                </div>

                {/* AI Insight Preview - 핵심 가치 표시 */}
                {loanInsight?.executive_summary && (
                    <div className="mb-3 p-2 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-100 dark:border-amber-900/50">
                        <div className="flex items-start gap-1.5">
                            <Lightbulb className="w-3 h-3 text-amber-600 mt-0.5 flex-shrink-0" />
                            <p className="text-[11px] text-amber-800 dark:text-amber-200 line-clamp-2 leading-relaxed">
                                {loanInsight.executive_summary}
                            </p>
                        </div>
                    </div>
                )}

                {/* Footer actions - Reveal on hover */}
                <div className="flex items-center justify-between pt-3 border-t border-border mt-auto">
                    <span className="text-xs text-muted-foreground">
                        {signal.evidenceCount} evidences
                        {loanInsight && (
                            <span className="ml-2">
                                · 위험 {loanInsight.risk_count} / 기회 {loanInsight.opportunity_count}
                            </span>
                        )}
                    </span>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        className="text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                        View Details &rarr;
                    </motion.button>
                </div>
            </motion.div>
        </motion.div>
    );
}
