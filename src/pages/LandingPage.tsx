/* 
  rKYC Landing Page - Korean Version (High-Fidelity Materiality)
*/

import { useRef, useState, useEffect } from "react";
import { motion, useScroll, useTransform, useInView, useSpring } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronRight, Play, CheckCircle2, AlertTriangle, ShieldCheck, Building2, Users, Wallet, TrendingUp, Activity, Globe, FileText, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

// --- DESIGN SYSTEM ---

const FadeUp = ({ children, delay = 0, className }: { children: React.ReactNode, delay?: number, className?: string }) => (
    <motion.div
        initial={{ opacity: 0, y: 40, filter: "blur(10px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, margin: "-10% 0px" }}
        transition={{ duration: 1.0, delay, ease: [0.16, 1, 0.3, 1] }}
        className={className}
    >
        {children}
    </motion.div>
);

const AuroraBackground = () => (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none bg-black">
        {/* Deep Space Gradient */}
        <div className="absolute top-[-50%] left-[-20%] w-[150%] h-[150%] bg-[radial-gradient(circle_farthest-corner,rgba(29,78,216,0.15),transparent_55%)] animate-pulse-slower opacity-60" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[120%] h-[120%] bg-[radial-gradient(circle_farthest-corner,rgba(79,70,229,0.1),transparent_50%)] animate-pulse-slow opacity-60" />
        {/* Grid Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_100%)]" />
    </div>
);

// --- SECTIONS ---

const HeroSection = () => {
    return (
        <section className="relative h-screen flex flex-col items-center justify-center overflow-hidden">
            <AuroraBackground />

            <div className="relative z-10 text-center px-6 max-w-6xl">
                <FadeUp delay={0.1}>
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-blue-300 text-xs font-medium tracking-wider mb-8 shadow-[0_0_20px_rgba(59,130,246,0.2)] backdrop-blur-md">
                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        RKYC 인텔리전스 엔진 v2.0
                    </div>
                </FadeUp>

                <FadeUp delay={0.2}>
                    <h1 className="text-7xl md:text-9xl lg:text-[9rem] font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40 leading-[0.9] mb-8 lang-ko word-keep-all">
                        데이터,<br />
                        깨어나다.
                    </h1>
                </FadeUp>

                <FadeUp delay={0.4}>
                    <p className="text-xl md:text-3xl text-white/70 max-w-4xl mx-auto leading-normal font-light tracking-tight word-keep-all">
                        은행의 정적인 데이터는 리스크를 놓칩니다. <br className="hidden md:block" />
                        rKYC의 <span className="text-white font-medium">실시간 인지형 AI</span>는 멈춰있는 데이터를 동적인 인텔리전스로 전환하여, <br className="hidden md:block" />
                        남들이 보지 못하는 <span className="text-blue-400">숨겨진 기회</span>와 <span className="text-red-400">위험</span>을 포착합니다.
                    </p>
                </FadeUp>

                <FadeUp delay={0.6} className="mt-16 flex flex-col sm:flex-row items-center justify-center gap-8">
                    <Button className="rounded-full h-16 pl-10 pr-2 text-xl bg-white text-black hover:bg-white/90 transition-all hover:scale-105 active:scale-95 shadow-[0_0_50px_rgba(255,255,255,0.3)] group word-keep-all">
                        분석 시작하기
                        <div className="ml-6 w-12 h-12 bg-black rounded-full flex items-center justify-center group-hover:rotate-45 transition-transform">
                            <ArrowRight className="w-5 h-5 text-white" />
                        </div>
                    </Button>
                </FadeUp>
            </div>
        </section>
    );
};

// --- PRODUCT SHOWCASE (REAL ENTERPRISE UI REPLICA) ---
const ProductShowcase = () => {
    return (
        <section className="py-40 bg-black relative overflow-hidden">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] h-[90vw] bg-blue-600/10 blur-[150px] rounded-full pointer-events-none" />

            <div className="container mx-auto px-6 text-center relative z-10">
                <FadeUp>
                    <h2 className="text-5xl md:text-8xl font-bold text-white tracking-tighter mb-8 word-keep-all">
                        완벽한 가시성.
                    </h2>
                    <p className="text-xl text-white/50 max-w-2xl mx-auto mb-20 word-keep-all">
                        단 한 번의 클릭으로 포괄적인 기업 인텔리전스에 접근하세요.
                    </p>
                </FadeUp>

                <FadeUp delay={0.2} className="relative mx-auto max-w-6xl aspect-[16/10] group perspective-1000">

                    {/* THE INTERFACE CARD (Enterprise Dashboard Replica) */}
                    <div className="w-full h-full rounded-2xl overflow-hidden border border-white/10 bg-[#0A0A0A] shadow-[0_40px_100px_rgba(0,0,0,0.8)] relative flex flex-col transition-transform duration-700 group-hover:scale-[1.01]">

                        {/* 1. App Header */}
                        <div className="h-14 border-b border-white/10 flex items-center justify-between px-6 bg-white/5 backdrop-blur-md">
                            <div className="flex items-center gap-4">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                                </div>
                                <div className="h-4 w-px bg-white/10 mx-2" />
                                <div className="flex items-center gap-2 text-xs text-white/60 bg-black/50 px-3 py-1 rounded-md border border-white/5">
                                    <Search className="w-3 h-3" />
                                    <span>테라 홀딩스</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className="text-xs font-mono text-green-400 flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                    실시간 연결됨
                                </span>
                            </div>
                        </div>

                        {/* 2. Main Layout */}
                        <div className="flex-1 flex overflow-hidden">

                            {/* Sidebar */}
                            <div className="w-64 border-r border-white/10 bg-black/20 p-4 flex flex-col gap-6">
                                <div className="flex items-center gap-3 px-2">
                                    <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold">T</div>
                                    <div className="text-left">
                                        <div className="text-sm font-bold text-white">테라 홀딩스</div>
                                        <div className="text-[10px] text-white/40">법인등록번호: 110111-xxxxxxx</div>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-500/10 text-blue-400 rounded-md text-sm font-medium border border-blue-500/20">
                                        <Activity className="w-4 h-4" /> 개요
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-white/40 hover:bg-white/5 rounded-md text-sm transition-colors">
                                        <Building2 className="w-4 h-4" /> 지배구조
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-white/40 hover:bg-white/5 rounded-md text-sm transition-colors">
                                        <Users className="w-4 h-4" /> 주주현황
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-white/40 hover:bg-white/5 rounded-md text-sm transition-colors">
                                        <FileText className="w-4 h-4" /> 관련문서
                                    </div>
                                </div>
                            </div>

                            {/* Content Area */}
                            <div className="flex-1 p-8 bg-gradient-to-br from-black to-neutral-900 overflow-y-auto custom-scrollbar">

                                {/* Top Stats Row */}
                                <div className="grid grid-cols-4 gap-4 mb-8">
                                    {[
                                        { label: "리스크 점수", value: "98/100", sub: "매우 안전", color: "text-green-400" },
                                        { label: "추정 매출", value: "425억원", sub: "전년비 +12%", color: "text-white" },
                                        { label: "임직원 수", value: "1,240명", sub: "글로벌", color: "text-white" },
                                        { label: "법적 상태", value: "정상", sub: "오늘 검증됨", color: "text-blue-400" },
                                    ].map((stat, i) => (
                                        <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                                            <div className="text-[10px] uppercase tracking-wider text-white/40 mb-1">{stat.label}</div>
                                            <div className={`text-2xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
                                            <div className="text-xs text-white/30">{stat.sub}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Main Grid */}
                                <div className="grid grid-cols-3 gap-6 h-[400px]">

                                    {/* Network Graph Replica */}
                                    <div className="col-span-2 bg-black/40 border border-white/5 rounded-xl p-6 relative overflow-hidden flex flex-col">
                                        <div className="flex justify-between items-center mb-6">
                                            <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                                <Globe className="w-4 h-4 text-blue-500" /> 주주 네트워크 시각화
                                            </h3>
                                            <div className="flex gap-2">
                                                <span className="w-2 h-2 rounded-full bg-blue-500" />
                                                <span className="w-2 h-2 rounded-full bg-white/20" />
                                            </div>
                                        </div>

                                        {/* Fake Graph Visual */}
                                        <div className="flex-1 relative border border-white/5 rounded-lg bg-grid-white/[0.02]">
                                            {/* Central Node */}
                                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-blue-600 rounded-full border-4 border-black z-10 flex items-center justify-center text-white font-bold shadow-[0_0_30px_rgba(37,99,235,0.4)]">TH</div>
                                            {/* Satellite Nodes */}
                                            {[0, 60, 120, 180, 240, 300].map((deg, i) => (
                                                <div key={i} className="absolute top-1/2 left-1/2 w-2 h-2 bg-white/40 rounded-full"
                                                    style={{
                                                        transform: `translate(-50%, -50%) rotate(${deg}deg) translate(120px) rotate(-${deg}deg)`,
                                                    }}>
                                                    <div className="absolute top-1/2 left-1/2 w-[120px] h-px bg-white/10 origin-left -translate-y-1/2 -ml-[120px] rotate-180" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Alerts / Signals */}
                                    <div className="col-span-1 bg-black/40 border border-white/5 rounded-xl p-6 flex flex-col">
                                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                                            <AlertTriangle className="w-4 h-4 text-yellow-500" /> 최근 감지된 시그널
                                        </h3>
                                        <div className="space-y-3">
                                            {[
                                                { text: "싱가포르 자회사 설립", time: "2시간 전", type: "info" },
                                                { text: "신규 이사 선임 (김철수)", time: "5시간 전", type: "success" },
                                                { text: "유상증자 결정 (50억)", time: "1일 전", type: "info" },
                                                { text: "체납 세금 완납 확인", time: "2일 전", type: "success" },
                                            ].map((sig, i) => (
                                                <div key={i} className="p-3 bg-white/5 rounded-lg border border-white/5 flex justify-between items-start">
                                                    <div className="text-left">
                                                        <div className="text-xs text-white font-medium">{sig.text}</div>
                                                        <div className="text-[10px] text-white/30">{sig.time}</div>
                                                    </div>
                                                    <div className={`w-1.5 h-1.5 rounded-full ${sig.type === 'info' ? 'bg-blue-500' : 'bg-green-500'}`} />
                                                </div>
                                            ))}
                                        </div>
                                        <div className="mt-auto pt-4 text-center">
                                            <Button variant="ghost" size="sm" className="text-xs text-blue-400 hover:text-blue-300 w-full">모든 시그널 보기</Button>
                                        </div>
                                    </div>

                                </div>

                            </div>

                        </div>
                    </div>

                </FadeUp>
            </div>
        </section>
    );
};

// 3. COMPARISON: Typography Driven
const ImpactSection = () => {
    return (
        <section className="py-40 bg-black relative">
            <div className="container mx-auto px-6 max-w-4xl">
                <FadeUp>
                    <div className="flex flex-col md:flex-row items-end justify-between border-b border-white/10 pb-8 mb-8">
                        <span className="text-6xl md:text-8xl font-bold text-white/20">기존</span>
                        <div className="text-right">
                            <div className="text-4xl text-white/40 font-light strikethrough decoration-red-500/50 line-through">3주</div>
                            <div className="text-sm text-white/20 mt-2">수동 검토 소요 시간</div>
                        </div>
                    </div>
                </FadeUp>

                <FadeUp delay={0.2}>
                    <div className="flex flex-col md:flex-row items-start justify-between">
                        <span className="text-6xl md:text-8xl font-bold text-white">변화</span>
                        <div className="text-right">
                            <div className="text-7xl md:text-9xl font-bold text-blue-500 drop-shadow-[0_0_30px_rgba(59,130,246,0.4)]">30초</div>
                            <div className="text-sm text-blue-400/60 mt-2 tracking-widest uppercase">rKYC 엔진 처리 속도</div>
                        </div>
                    </div>
                </FadeUp>
            </div>
        </section>
    )
}

const Footer = () => (
    <footer className="py-32 bg-black border-t border-white/5 text-center px-6 relative overflow-hidden">
        {/* The Halo (Portal Light) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-blue-600/20 blur-[100px] rounded-full pointer-events-none animate-pulse-slow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[200px] bg-indigo-500/20 blur-[80px] rounded-full pointer-events-none mix-blend-screen" />

        <FadeUp className="relative z-10">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-12 tracking-tight word-keep-all">
                모든 것을 알 준비가 되셨나요?
            </h2>

            <div className="group relative inline-block">
                {/* Button Glow on Hover */}
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-20 group-hover:opacity-75 transition duration-1000 group-hover:duration-200" />

                <Button className="relative h-16 px-12 text-lg rounded-full bg-white text-black hover:bg-neutral-100 hover:scale-105 transition-all duration-300 shadow-[0_0_40px_rgba(255,255,255,0.3)] border border-white/50 word-keep-all">
                    엔진 가동 (Initialize)
                </Button>
            </div>

            {/* Footer links removed */}
        </FadeUp>
    </footer>
);

export default function LandingPage() {
    return (
        <div className="bg-black text-white min-h-screen selection:bg-blue-500/50 selection:text-white font-sans">

            {/* GLOBAL NAV - Minimal */}
            <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-6 flex justify-between items-center bg-gradient-to-b from-black/80 to-transparent backdrop-blur-[2px]">
                <Link to="/" className="text-2xl font-bold tracking-tighter text-white">rKYC</Link>
                {/* Login button removed */}
            </nav>

            <HeroSection />
            {/* Removed TrustGrid */}
            <ProductShowcase />
            <ImpactSection />
            <Footer />
        </div>
    );
}
