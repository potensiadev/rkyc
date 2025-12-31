import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui-liquid/GlassCard";
import { Separator } from "@/components/ui/separator";
import { Signal, Evidence } from "@/types/signal";
import { Calendar, Building2, TrendingUp, TrendingDown, FileText, Database, Shield, Link as LinkIcon, ExternalLink } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface GlassSignalViewerProps {
    signal: any; // Using any for flexibility as extended signal type is local to page, ideally should be shared
}

export function GlassSignalViewer({ signal }: GlassSignalViewerProps) {
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 10 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <GlassCard className="h-full flex flex-col p-8 overflow-hidden bg-white/5 border-white/10 backdrop-blur-2xl">
            <ScrollArea className="h-full w-full pr-4">
                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                >
                    {/* Header */}
                    <motion.div variants={itemVariants} className="space-y-4">
                        <div className="flex items-center gap-2 text-indigo-400 text-sm font-mono tracking-wider uppercase">
                            <FileText className="w-4 h-4" />
                            <span>분석 리포트</span>
                        </div>

                        <h1 className="text-3xl font-bold text-white leading-tight">
                            {signal.title}
                        </h1>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
                            <div className="flex items-center gap-1.5">
                                <Building2 className="w-4 h-4" />
                                <span>{signal.corporationName}</span>
                            </div>
                            <div className="w-1 h-1 rounded-full bg-zinc-700" />
                            <div className="flex items-center gap-1.5">
                                <Calendar className="w-4 h-4" />
                                <span>{signal.detectedAt}</span>
                            </div>
                            <div className="w-1 h-1 rounded-full bg-zinc-700" />
                            <div className={`px-2 py-0.5 rounded textxs font-medium border ${signal.impact === 'risk' ? 'border-red-500/30 text-red-400 bg-red-500/10' :
                                    signal.impact === 'opportunity' ? 'border-green-500/30 text-green-400 bg-green-500/10' :
                                        'border-zinc-500/30 text-zinc-400'
                                }`}>
                                {signal.impact === 'risk' ? '위험' : signal.impact === 'opportunity' ? '기회' : '참고'}
                            </div>
                        </div>
                    </motion.div>

                    <Separator className="bg-white/10" />

                    {/* 1. Overview */}
                    <motion.div variants={itemVariants} className="space-y-3">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <span className="w-1 h-6 bg-indigo-500 rounded-full" />
                            요약 (Executive Summary)
                        </h2>
                        <p className="text-zinc-300 leading-relaxed text-base">
                            {signal.summary}
                        </p>
                    </motion.div>

                    {/* 2. Detailed Analysis */}
                    <motion.div variants={itemVariants} className="space-y-3">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <span className="w-1 h-6 bg-purple-500 rounded-full" />
                            상세 분석
                        </h2>
                        <GlassCard className="bg-white/5 border-0 p-4">
                            <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">
                                {signal.aiSummary || "상세 분석 내용이 AI 엔진에 의해 처리 중입니다."}
                            </p>
                        </GlassCard>
                    </motion.div>

                    {/* 3. Evidences */}
                    <motion.div variants={itemVariants} className="space-y-3">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <span className="w-1 h-6 bg-cyan-500 rounded-full" />
                            근거 자료
                        </h2>
                        <div className="grid gap-3">
                            {signal.evidences?.map((evidence: any, i: number) => (
                                <motion.a
                                    key={i}
                                    href={evidence.sourceUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    whileHover={{ scale: 1.01, backgroundColor: "rgba(255,255,255,0.08)" }}
                                    className="block p-4 rounded-xl bg-white/5 border border-white/5 transition-colors group"
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="space-y-1">
                                            <h4 className="text-zinc-200 font-medium group-hover:text-indigo-300 transition-colors">
                                                {evidence.title}
                                            </h4>
                                            <div className="flex items-center gap-2 text-xs text-zinc-500">
                                                <span>{evidence.sourceName}</span>
                                                <span>•</span>
                                                <span>{evidence.publishedAt || "최근"}</span>
                                            </div>
                                            <p className="text-sm text-zinc-400 mt-2 line-clamp-2">
                                                {evidence.snippet}
                                            </p>
                                        </div>
                                        <ExternalLink className="w-4 h-4 text-zinc-600 group-hover:text-white transition-colors shrink-0" />
                                    </div>
                                </motion.a>
                            ))}
                        </div>
                    </motion.div>

                    {/* 4. Risk Assessment */}
                    <motion.div variants={itemVariants} className="space-y-3">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <span className="w-1 h-6 bg-rose-500 rounded-full" />
                            영향도 평가
                        </h2>
                        <div className="grid grid-cols-2 gap-4">
                            <GlassCard className="p-4 bg-white/5 space-y-1">
                                <span className="text-xs text-zinc-500 uppercase tracking-widest">영향도 레벨</span>
                                <div className={`text-xl font-bold ${signal.impact === 'risk' ? 'text-red-400' : 'text-green-400'
                                    }`}>
                                    {signal.impactStrength?.toUpperCase() || "보통"}
                                </div>
                            </GlassCard>
                            <GlassCard className="p-4 bg-white/5 space-y-1">
                                <span className="text-xs text-zinc-500 uppercase tracking-widest">이벤트 분류</span>
                                <div className="text-xl font-bold text-white">
                                    {signal.eventClassification?.toUpperCase() || "일반"}
                                </div>
                            </GlassCard>
                        </div>
                    </motion.div>

                </motion.div>
            </ScrollArea>
        </GlassCard>
    );
}
