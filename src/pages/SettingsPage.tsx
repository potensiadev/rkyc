import { MainLayout } from "@/components/layout/MainLayout";
import { DemoPanel } from "@/components/demo/DemoPanel";
import { SchedulerPanel } from "@/components/demo/SchedulerPanel";
import { Badge } from "@/components/ui/badge";
import { Activity, Settings as SettingsIcon, Database, Network, Zap, Workflow, Cpu, Bot, Search, Globe, GitMerge, Building2, Factory, Landmark, FileText, ShieldCheck, Ban, Calculator, Link as LinkIcon, Fingerprint, Sparkles, Layers, ArrowRight, Laptop, Server, Lock, Clock } from "lucide-react";
import {
    DynamicBackground,
    GlassCard,
    StatusBadge
} from "@/components/premium";
import { motion } from "framer-motion";

export default function SettingsPage() {
    const enableScheduler = import.meta.env.VITE_ENABLE_SCHEDULER === 'true' || import.meta.env.DEV;
    const demoMode = import.meta.env.VITE_DEMO_MODE === 'true' || import.meta.env.DEV;
    const apiUrl = import.meta.env.VITE_API_URL;

    return (
        <MainLayout>
            <DynamicBackground />
            <div className="max-w-4xl mx-auto space-y-8 pb-20 relative z-10 px-6">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-4 pt-6 mb-2"
                >
                    <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center border border-slate-200">
                        <SettingsIcon className="w-6 h-6 text-slate-700" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">System Settings</h1>
                        <p className="text-slate-500 font-medium mt-1">Configure system behavior and manage demo environments.</p>
                    </div>
                </motion.div>

                {/* System Features */}
                <section className="space-y-6">

                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Activity className="w-5 h-5 text-indigo-500" />
                        <h2 className="text-lg font-bold text-slate-800">Feature Control</h2>
                    </motion.div>

                    <div className="grid gap-8">
                        {/* Scheduler Panel (Env Controlled) */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Automated Scheduler</h3>
                                <StatusBadge variant={enableScheduler ? "success" : "neutral"}>
                                    {enableScheduler ? "Active" : "Disabled (Env)"}
                                </StatusBadge>
                            </div>

                            {enableScheduler ? (
                                <div className="bg-white/50 backdrop-blur-sm rounded-xl border border-slate-200 shadow-sm p-1">
                                    <SchedulerPanel />
                                </div>
                            ) : (
                                <GlassCard className="bg-slate-50/50 border-dashed border-slate-300 p-8 text-center flex flex-col items-center justify-center gap-2">
                                    <h4 className="text-slate-900 font-semibold">Scheduler Disabled</h4>
                                    <p className="text-slate-500 text-sm max-w-md">The scheduler feature is disabled by the environment variable (VITE_ENABLE_SCHEDULER). Please check your configuration.</p>
                                </GlassCard>
                            )}
                        </motion.div>

                        {/* Demo Mode Panel */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Demo Environment</h3>
                                <StatusBadge variant={demoMode ? "brand" : "neutral"}>
                                    {demoMode ? "Demo Mode Active" : "Production Mode"}
                                </StatusBadge>
                            </div>

                            {demoMode ? (
                                <div className="bg-gradient-to-br from-indigo-50/50 to-purple-50/50 backdrop-blur-sm rounded-xl border border-indigo-100 shadow-sm p-1">
                                    <DemoPanel />
                                </div>
                            ) : (
                                <GlassCard className="bg-slate-50/50 border-dashed border-slate-300 p-8 text-center flex flex-col items-center justify-center gap-2">
                                    <h4 className="text-slate-900 font-semibold">Production Mode</h4>
                                    <p className="text-slate-500 text-sm max-w-md">Demo controls are hidden in production mode.</p>
                                </GlassCard>
                            )}
                        </motion.div>
                    </div>
                </section>

                {/* Orchestrator Architecture */}
                <section className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.35 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Cpu className="w-5 h-5 text-indigo-500" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">Core Orchestrators</h2>
                            <p className="text-xs text-slate-500 font-medium">3개의 Orchestrator (팀장 역할)</p>
                        </div>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* MultiAgent Orchestrator */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 }}
                        >
                            <GlassCard className="h-full p-5 flex flex-col gap-3 hover:border-indigo-200 transition-colors group">
                                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                                    <Network className="w-5 h-5 text-indigo-600" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800 text-sm">MultiAgent Orchestrator</h3>
                                    <p className="text-xs text-indigo-600 font-medium mt-1">기업 프로파일링 담당</p>
                                </div>
                                <div className="space-y-2 mt-1">
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            기업 외부 정보 수집 <span className="text-slate-700 font-medium"></span> 총괄
                                        </p>
                                    </div>
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            Perplexity 검색 - Gemini 교차 검증 <span className="text-slate-700 font-medium"></span>
                                        </p>
                                    </div>
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            4단계 Fallback 조율<span className="text-slate-700 font-medium"></span>
                                        </p>
                                    </div>
                                </div>
                            </GlassCard>
                        </motion.div>

                        {/* SignalAgent Orchestrator */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 }}
                        >
                            <GlassCard className="h-full p-5 flex flex-col gap-3 hover:border-amber-200 transition-colors group">
                                <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center group-hover:bg-amber-100 transition-colors">
                                    <Zap className="w-5 h-5 text-amber-600" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800 text-sm">SignalAgent Orchestrator</h3>
                                    <p className="text-xs text-amber-600 font-medium mt-1">3개 Agent 병렬 실행</p>
                                </div>
                                <div className="space-y-2 mt-1">
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            3개의 Signal Agent를 <span className="text-slate-700 font-medium">동시에 병렬 실행</span>
                                        </p>
                                    </div>
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            Direct, Industry, Environment 리스크를 <span className="text-slate-700 font-medium">한꺼번에 추출</span>
                                        </p>
                                    </div>
                                </div>
                            </GlassCard>
                        </motion.div>

                        {/* NewKyc Orchestrator */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6 }}
                        >
                            <GlassCard className="h-full p-5 flex flex-col gap-3 hover:border-emerald-200 transition-colors group">
                                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
                                    <Workflow className="w-5 h-5 text-emerald-600" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800 text-sm">NewKyc Orchestrator</h3>
                                    <p className="text-xs text-emerald-600 font-medium mt-1">전체 분석 흐름 총괄</p>
                                </div>
                                <div className="space-y-2 mt-1">
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            신규 기업 분석의 <span className="text-slate-700 font-medium">전체 흐름 총괄</span>
                                        </p>
                                    </div>
                                    <div className="flex items-start gap-2">
                                        <div className="w-1 h-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                                        <p className="text-xs text-slate-500 leading-relaxed">
                                            프로파일링 → 시그널 → 검증까지, <span className="text-slate-700 font-medium">Phase별 병렬 처리</span>
                                        </p>
                                    </div>
                                </div>
                            </GlassCard>
                        </motion.div>
                    </div>
                </section>

                {/* Sub-Agents Architecture */}
                <section className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.55 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Bot className="w-5 h-5 text-purple-500" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">Sub-Agents</h2>
                            <p className="text-xs text-slate-500 font-medium">7개의 Sub-Agent (실무자 역할)</p>
                        </div>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {/* PerplexityProvider */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-sky-50 flex items-center justify-center">
                                    <Search className="w-4 h-4 text-sky-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">PerplexityProvider</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                실시간 웹 검색 담당
                            </p>
                        </div>

                        {/* GeminiGroundingProvider */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                                    <Globe className="w-4 h-4 text-blue-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">GeminiGrounding</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                Google Search 기반 검색
                            </p>
                        </div>

                        {/* GeminiAdapter */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
                                    <GitMerge className="w-4 h-4 text-purple-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">GeminiAdapter</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                Perplexity와 Gemini 결과 교차 검증
                            </p>
                        </div>

                        {/* DirectSignalAgent */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center">
                                    <Building2 className="w-4 h-4 text-orange-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">DirectSignalAgent</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                <span className="font-semibold text-slate-700">기업 내부 변화 분석</span><br />
                                <span className="text-slate-400">8종류의 이벤트 탐지</span>
                            </p>
                        </div>

                        {/* IndustrySignalAgent */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                                    <Factory className="w-4 h-4 text-slate-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">IndustrySignalAgent</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                해당 기업이 속한 <span className="font-semibold text-slate-700">산업 전체의 리스크 분석</span>
                            </p>
                        </div>

                        {/* EnvironmentSignalAgent */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                                    <Landmark className="w-4 h-4 text-emerald-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">EnvSignalAgent</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                정책, 규제 등 <span className="font-semibold text-slate-700">외부 환경 리스크 분석</span>
                            </p>
                        </div>

                        {/* DocumentAgent */}
                        <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-slate-200 p-4 hover:bg-white/80 transition-colors md:col-span-2 lg:col-span-1 xl:col-span-2">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center">
                                    <FileText className="w-4 h-4 text-rose-600" />
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm">DocumentAgent</h3>
                            </div>
                            <p className="text-xs text-slate-500 leading-relaxed pl-11">
                                재무제표, 사업자등록증 등 5종 문서를 <span className="font-semibold text-slate-700">OCR로 파싱</span>
                            </p>
                        </div>
                    </div>
                </section>

                {/* Anti-Hallucination Layers */}
                <section className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.7 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <ShieldCheck className="w-5 h-5 text-rose-500" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">Anti-Hallucination</h2>
                            <p className="text-xs text-slate-500 font-medium">5단계 검증 (Safety Layers)</p>
                        </div>
                    </motion.div>

                    <div className="grid gap-3">
                        {/* Layer 1 */}
                        <GlassCard className="flex items-center gap-4 p-4 hover:border-rose-200 transition-colors">
                            <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                                <span className="font-bold text-rose-600 text-sm">L1</span>
                            </div>
                            <div className="flex-1 grid md:grid-cols-2 gap-2 items-center">
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                                        <Ban className="w-4 h-4 text-rose-400" />
                                        Soft Guardrails
                                    </h4>
                                </div>
                                <p className="text-xs text-slate-500">
                                    "~로 추정됨" 등 <span className="text-slate-700 font-medium">단정 표현 강제 차단</span>
                                </p>
                            </div>
                        </GlassCard>

                        {/* Layer 2 */}
                        <GlassCard className="flex items-center gap-4 p-4 hover:border-rose-200 transition-colors">
                            <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                                <span className="font-bold text-rose-600 text-sm">L2</span>
                            </div>
                            <div className="flex-1 grid md:grid-cols-2 gap-2 items-center">
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                                        <Calculator className="w-4 h-4 text-rose-400" />
                                        Number Validation
                                    </h4>
                                </div>
                                <p className="text-xs text-slate-500">
                                    "88% 감소" 등 수치 <span className="text-slate-700 font-medium">입력 데이터 미존재 시 거부</span>
                                </p>
                            </div>
                        </GlassCard>

                        {/* Layer 3 */}
                        <GlassCard className="flex items-center gap-4 p-4 hover:border-rose-200 transition-colors">
                            <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                                <span className="font-bold text-rose-600 text-sm">L3</span>
                            </div>
                            <div className="flex-1 grid md:grid-cols-2 gap-2 items-center">
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                                        <LinkIcon className="w-4 h-4 text-rose-400" />
                                        Evidence Validation
                                    </h4>
                                </div>
                                <p className="text-xs text-slate-500">
                                    출처 URL이 <span className="text-slate-700 font-medium">실제 존재하는지 실시간 확인</span>
                                </p>
                            </div>
                        </GlassCard>

                        {/* Layer 4 */}
                        <GlassCard className="flex items-center gap-4 p-4 hover:border-rose-200 transition-colors">
                            <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                                <span className="font-bold text-rose-600 text-sm">L4</span>
                            </div>
                            <div className="flex-1 grid md:grid-cols-2 gap-2 items-center">
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                                        <Fingerprint className="w-4 h-4 text-rose-400" />
                                        Entity Confusion Prevention
                                    </h4>
                                </div>
                                <p className="text-xs text-slate-500">
                                    "엠케이전자" 분석에 "삼성전자" 정보 <span className="text-slate-700 font-medium">혼입 방지</span>
                                </p>
                            </div>
                        </GlassCard>

                        {/* Layer 5 */}
                        <GlassCard className="flex items-center gap-4 p-4 hover:border-emerald-200 transition-colors border-emerald-100 bg-emerald-50/30">
                            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
                                <span className="font-bold text-emerald-600 text-sm">L5</span>
                            </div>
                            <div className="flex-1 grid md:grid-cols-2 gap-2 items-center">
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-emerald-500" />
                                        Gemini Fact-Check
                                    </h4>
                                </div>
                                <p className="text-xs text-slate-500">
                                    Google Search로 <span className="text-slate-700 font-medium">최종 팩트체크</span> (FALSE → 폐기)
                                </p>
                            </div>
                        </GlassCard>
                    </div>
                </section>

                {/* 4-Layer Fallback */}
                <section className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Layers className="w-5 h-5 text-amber-500" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">4-Layer Fallback</h2>
                            <p className="text-xs text-slate-500 font-medium">시스템 장애 대응 (System Resilience)</p>
                        </div>
                    </motion.div>

                    <GlassCard className="p-0 overflow-hidden border-amber-100">
                        <div className="divide-y divide-slate-100">
                            {/* Layer 1 */}
                            <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-amber-50/30 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500">1</div>
                                    <span className="text-sm text-slate-600 font-medium">Perplexity가 죽으면?</span>
                                </div>
                                <div className="flex items-center gap-2 pl-11 sm:pl-0">
                                    <ArrowRight className="w-4 h-4 text-amber-400" />
                                    <span className="text-sm font-bold text-slate-800">Gemini가 대신합니다</span>
                                </div>
                            </div>

                            {/* Layer 2 */}
                            <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-amber-50/30 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500">2</div>
                                    <span className="text-sm text-slate-600 font-medium">Gemini도 죽으면?</span>
                                </div>
                                <div className="flex items-center gap-2 pl-11 sm:pl-0">
                                    <ArrowRight className="w-4 h-4 text-amber-400" />
                                    <span className="text-sm font-bold text-slate-800">Claude가 합성합니다</span>
                                </div>
                            </div>

                            {/* Layer 3 */}
                            <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-amber-50/30 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500">3</div>
                                    <span className="text-sm text-slate-600 font-medium">Claude도 죽으면?</span>
                                </div>
                                <div className="flex items-center gap-2 pl-11 sm:pl-0">
                                    <ArrowRight className="w-4 h-4 text-amber-400" />
                                    <span className="text-sm font-bold text-slate-800">Rule-Based 병합</span>
                                </div>
                            </div>

                            {/* Layer 4 */}
                            <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-red-50/10 hover:bg-red-50/20 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-xs font-bold text-red-600">4</div>
                                    <span className="text-sm text-slate-600 font-medium">그래도 안 되면?</span>
                                </div>
                                <div className="flex items-center gap-2 pl-11 sm:pl-0">
                                    <ArrowRight className="w-4 h-4 text-red-300" />
                                    <span className="text-sm font-bold text-red-600">최소 프로필 + 경고 플래그</span>
                                </div>
                            </div>
                        </div>
                    </GlassCard>
                </section>

                {/* Security First Tech Stack */}
                <section className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.9 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Lock className="w-5 h-5 text-slate-700" />
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">Security First Tech Stack</h2>
                            <p className="text-xs text-slate-500 font-medium">보안 중심 아키텍처 (Zero Trust)</p>
                        </div>
                    </motion.div>

                    <GlassCard className="p-0 overflow-hidden border-slate-200">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-slate-50 border-b border-slate-100">
                                    <tr>
                                        <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">서비스</th>
                                        <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">기술</th>
                                        <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">핵심 포인트</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-slate-800 flex items-center gap-2 whitespace-nowrap">
                                            <Laptop className="w-4 h-4 text-slate-400" /> Frontend
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 whitespace-nowrap">React 18 + Vercel</td>
                                        <td className="px-6 py-4 text-slate-600">글로벌 CDN 서빙</td>
                                    </tr>
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-slate-800 flex items-center gap-2 whitespace-nowrap">
                                            <Server className="w-4 h-4 text-slate-400" /> Backend
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 whitespace-nowrap">FastAPI + Railway</td>
                                        <td className="px-6 py-4 text-slate-600">
                                            순수 CRUD, <span className="font-bold text-slate-900">LLM 키 없음</span>
                                        </td>
                                    </tr>
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-slate-800 flex items-center gap-2 whitespace-nowrap">
                                            <Database className="w-4 h-4 text-slate-400" /> Database
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 whitespace-nowrap">Supabase + pgvector</td>
                                        <td className="px-6 py-4 text-slate-600">
                                            도쿄 리전, 벡터 유사 케이스 검색
                                        </td>
                                    </tr>
                                    <tr className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-slate-800 flex items-center gap-2 whitespace-nowrap">
                                            <Cpu className="w-4 h-4 text-slate-400" /> Worker
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 whitespace-nowrap">Celery + Redis + litellm</td>
                                        <td className="px-6 py-4 text-slate-600">
                                            AI 분석 전담, <span className="underline decoration-slate-300 underline-offset-4">5개 LLM 라우팅</span>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </GlassCard>
                </section>





                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.1 }}
                    className="pt-10 border-t border-slate-200 mt-10"
                >
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <Database className="w-3 h-3" />
                        <span>API Endpoint: {apiUrl}</span>
                    </div>
                </motion.div>
            </div>
        </MainLayout >
    );
}
