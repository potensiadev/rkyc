/* 
  rKYC Landing Page - Hackathon Version (Nano Gorilla)
*/

import { useRef } from "react";
import { motion, useScroll, useTransform, useInView } from "framer-motion";
import { Link } from "react-router-dom";
import {
    ArrowRight,
    CheckCircle2,
    AlertTriangle,
    Building2,
    Activity,
    Globe,
    FileText,
    Search,
    TrendingUp,
    Zap,
    AlertCircle,
    Landmark,
    Coins,
    Timer
} from "lucide-react";
import { Button } from "@/components/ui/button";

// --- DESIGN SYSTEM ---

const FadeUp = ({ children, delay = 0, className }: { children: React.ReactNode, delay?: number, className?: string }) => (
    <motion.div
        initial={{ opacity: 0, y: 40, filter: "blur(10px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, margin: "-10% 0px" }}
        transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
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

            <div className="relative z-10 text-center px-6 max-w-7xl">
                <FadeUp delay={0.1}>
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-blue-300 text-xs font-medium tracking-wider mb-8 shadow-[0_0_20px_rgba(59,130,246,0.2)] backdrop-blur-md">
                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        Nano Gorilla Team
                    </div>
                </FadeUp>

                <FadeUp delay={0.2}>
                    <h1 className="text-6xl md:text-8xl lg:text-9xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60 leading-[1.1] mb-8 word-keep-all">
                        진짜로 고객을 알자,<br />
                        <span className="text-blue-500">rKYC</span>
                    </h1>
                </FadeUp>

                <FadeUp delay={0.4}>
                    <p className="text-xl md:text-3xl text-white/70 max-w-4xl mx-auto leading-relaxed font-light tracking-tight word-keep-all">
                        지루한 오퍼레이션 업무가<br className="hidden md:block" />
                        <span className="text-white font-semibold">290억 가치의 비즈니스</span>로 전환되는 순간.<br />
                        나노고릴라가 그 변화를 시작합니다.
                    </p>
                </FadeUp>

                <FadeUp delay={0.6} className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-6">
                    <Button className="rounded-full h-14 px-8 text-lg bg-blue-600 hover:bg-blue-500 text-white transition-all hover:scale-105 shadow-[0_0_30px_rgba(37,99,235,0.4)]">
                        분석 엔진 가동하기
                        <ArrowRight className="ml-2 w-5 h-5" />
                    </Button>
                </FadeUp>
            </div>
        </section>
    );
};

const ProblemSection = () => {
    return (
        <section className="py-32 bg-black relative border-t border-white/5">
            <div className="container mx-auto px-6 max-w-5xl">
                <div className="grid md:grid-cols-2 gap-16 items-center">
                    <FadeUp>
                        <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 word-keep-all leading-tight">
                            <span className="text-white/40">질문 하나 드립니다.</span><br />
                            고객이 은행에 오면 가장 먼저 무엇을 합니까?
                        </h2>
                    </FadeUp>
                    <FadeUp delay={0.2} className="space-y-6">
                        <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                            <h3 className="text-xl font-bold text-red-400 mb-3 flex items-center gap-2">
                                <AlertTriangle className="w-5 h-5" />
                                바로 KYC (Know Your Customer)
                            </h3>
                            <p className="text-white/60 leading-relaxed word-keep-all">
                                이것 없이는 계좌 개설도, 여신도 불가능합니다.<br />
                                하지만 현장에서는 어떻습니까?
                            </p>
                        </div>
                        <div className="space-y-2">
                            <p className="text-2xl font-light text-white/80 word-keep-all">
                                "지루한 서류 작업, 버려지는 수많은 정보들..."
                            </p>
                            <p className="text-white/40 word-keep-all">
                                사업자등록증, 주주명부, 재무제표... 수많은 서류를 징구하지만<br />
                                영업점과 고객 모두에게 그저 <span className="text-red-400 font-medium">아까운 시간</span>일 뿐입니다.
                            </p>
                        </div>
                    </FadeUp>
                </div>
            </div>
        </section>
    );
};

const SolutionSection = () => {
    return (
        <section className="py-32 bg-gradient-to-b from-black to-neutral-900 relative">
            <div className="container mx-auto px-6 text-center">
                <FadeUp>
                    <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 word-keep-all">
                        하지만, <span className="text-blue-500">버려지는 정보</span> 속에 돈이 있습니다.
                    </h2>
                    <p className="text-xl text-white/60 max-w-3xl mx-auto mb-16 word-keep-all leading-relaxed">
                        기업의 여신 데이터, 거래 내역, KYC 정보...<br />
                        사실 어디서도 돈 주고 살 수 없는 귀한 **내부 정보**입니다.<br />
                        이 정보가 **AI**를 만나는 순간, **대체 불가능한 가치**가 만들어집니다.
                    </p>
                </FadeUp>

                <FadeUp delay={0.2} className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                    {[
                        { icon: Database, bg: "bg-blue-500/10", text: "귀중한 내부 데이터", color: "text-blue-400" },
                        { icon: Cpu, bg: "bg-purple-500/10", text: "AI 인텔리전스", color: "text-purple-400" },
                        { icon: Zap, bg: "bg-yellow-500/10", text: "폭발적 가치 창출", color: "text-yellow-400" }
                    ].map((item, i) => (
                        <div key={i} className={`p-8 rounded-2xl border border-white/5 ${item.bg} flex flex-col items-center gap-4`}>
                            <item.icon className={`w-10 h-10 ${item.color}`} />
                            <span className={`text-lg font-bold ${item.color}`}>{item.text}</span>
                        </div>
                    ))}
                </FadeUp>
            </div>
        </section>
    );
};

// --- PRODUCT SHOWCASE (REAL ENTERPRISE UI REPLICA) ---
const ProductShowcase = () => {
    return (
        <section className="py-40 bg-black relative overflow-hidden">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] h-[90vw] bg-indigo-600/10 blur-[150px] rounded-full pointer-events-none" />

            <div className="container mx-auto px-6 relative z-10">
                <div className="text-center mb-16">
                    <FadeUp>
                        <div className="inline-block px-4 py-1.5 rounded-full bg-blue-500/20 text-blue-300 text-sm font-bold mb-4 border border-blue-500/30">
                            Live Demo
                        </div>
                        <h2 className="text-4xl md:text-7xl font-bold text-white tracking-tighter mb-6 word-keep-all">
                            MK전자, 1분 만에 파악하기
                        </h2>
                        <p className="text-xl text-white/50 max-w-2xl mx-auto word-keep-all">
                            "이 기업은 어떻게 돈을 벌까? 취약점은 무엇일까?"<br />
                            사람이 하면 며칠 걸릴 분석, rKYC는 자동입니다.
                        </p>
                    </FadeUp>
                </div>

                <FadeUp delay={0.2} className="relative mx-auto max-w-6xl aspect-[16/10] group perspective-1000">

                    {/* THE INTERFACE CARD (MK Electronics Demo) */}
                    <div className="w-full h-full rounded-2xl overflow-hidden border border-white/10 bg-[#0A0A0A] shadow-[0_40px_100px_rgba(0,0,0,0.8)] relative flex flex-col transition-transform duration-700 hover:scale-[1.01]">

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
                                    <span>MK전자 (033160)</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className="text-xs font-mono text-green-400 flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                    실시간 분석 완료
                                </span>
                            </div>
                        </div>

                        {/* 2. Main Layout */}
                        <div className="flex-1 flex overflow-hidden">

                            {/* Sidebar */}
                            <div className="w-64 border-r border-white/10 bg-black/20 p-4 flex flex-col gap-6">
                                <div className="flex items-center gap-3 px-2">
                                    <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-lg">M</div>
                                    <div className="text-left">
                                        <div className="text-sm font-bold text-white">MK전자</div>
                                        <div className="text-[10px] text-white/40">반도체 소재 / 본딩와이어</div>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-500/10 text-blue-400 rounded-md text-sm font-medium border border-blue-500/20">
                                        <Activity className="w-4 h-4" /> 분석 개요
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-white/40 hover:bg-white/5 rounded-md text-sm transition-colors">
                                        <Building2 className="w-4 h-4" /> 지배구조
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-white/40 hover:bg-white/5 rounded-md text-sm transition-colors">
                                        <FileText className="w-4 h-4" /> 관련문서
                                    </div>
                                </div>

                                {/* AI Analysis Logic Badge */}
                                <div className="mt-auto p-3 rounded-lg bg-gradient-to-br from-indigo-900/50 to-purple-900/50 border border-white/10">
                                    <p className="text-[10px] text-indigo-300 font-bold mb-1">AI Logic</p>
                                    <p className="text-[10px] text-white/60 leading-tight">
                                        내부 거래 데이터와<br />외부 매크로 변수 결합중...
                                    </p>
                                </div>
                            </div>

                            {/* Content Area */}
                            <div className="flex-1 p-8 bg-gradient-to-br from-black to-neutral-900 overflow-y-auto custom-scrollbar">

                                {/* Top Stats Row */}
                                <div className="grid grid-cols-4 gap-4 mb-8">
                                    {[
                                        { label: "AI 리스크 점수", value: "72/100", sub: "주의 필요", color: "text-amber-400" },
                                        { label: "추정 매출", value: "4,620억", sub: "전년비 +5%", color: "text-white" },
                                        { label: "주요 수출국", value: "중국, 대만", sub: "환율 민감도 高", color: "text-white" },
                                        { label: "현금 흐름", value: "양호", sub: "단기 유동성 충분", color: "text-blue-400" },
                                    ].map((stat, i) => (
                                        <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                                            <div className="text-[10px] uppercase tracking-wider text-white/40 mb-1">{stat.label}</div>
                                            <div className={`text-1xl md:text-2xl font-bold ${stat.color} mb-1 truncate`}>{stat.value}</div>
                                            <div className="text-xs text-white/30">{stat.sub}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Main Grid */}
                                <div className="grid grid-cols-3 gap-6 h-[400px]">

                                    {/* Supply Chain / Market Map */}
                                    <div className="col-span-2 bg-black/40 border border-white/5 rounded-xl p-6 relative overflow-hidden flex flex-col">
                                        <div className="flex justify-between items-center mb-6">
                                            <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                                <Globe className="w-4 h-4 text-blue-500" /> 밸류체인 & 리스크 팩터
                                            </h3>
                                            <div className="px-2 py-0.5 rounded-full bg-white/10 text-[10px] text-white/60">Auto-Generated</div>
                                        </div>

                                        {/* Fake Graph Visual */}
                                        <div className="flex-1 relative border border-white/5 rounded-lg bg-grid-white/[0.02] flex items-center justify-center">
                                            {/* Logic Visual */}
                                            <div className="relative w-full h-full">
                                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-indigo-600 rounded-full border-4 border-black z-10 flex items-center justify-center text-white font-bold shadow-[0_0_30px_rgba(79,70,229,0.4)]">MK</div>

                                                {/* Connecting Nodes */}
                                                <div className="absolute top-[20%] left-[20%] p-2 rounded bg-red-900/40 border border-red-500/30 text-xs text-red-200">
                                                    환율 변동성 (Risk)
                                                </div>
                                                <div className="absolute top-[20%] left-[50%] w-[2px] h-[30%] bg-gradient-to-b from-red-500/50 to-transparent origin-top -rotate-45" />

                                                <div className="absolute bottom-[20%] right-[20%] p-2 rounded bg-green-900/40 border border-green-500/30 text-xs text-green-200">
                                                    용인 클러스터 (Opp)
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Alerts / Signals - THE CORE DEMO PART */}
                                    <div className="col-span-1 bg-black/40 border border-white/5 rounded-xl p-6 flex flex-col relative overflow-hidden">
                                        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent pointer-events-none" />
                                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                                            <AlertCircle className="w-4 h-4 text-yellow-400" /> 실시간 감지 시그널
                                        </h3>
                                        <div className="space-y-3 relative z-10">
                                            {/* SIGNAL 1: Opportunity */}
                                            <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20 flex flex-col gap-1">
                                                <div className="flex justify-between items-start">
                                                    <span className="text-[10px] font-bold text-green-400 bg-green-500/20 px-1.5 py-0.5 rounded">HOZ (기회)</span>
                                                    <span className="text-[10px] text-green-400/60">방금 전</span>
                                                </div>
                                                <div className="text-sm text-green-100 font-medium">담보 토지 인근 도로 개설 확정</div>
                                                <div className="text-[10px] text-green-400/70">→ 담보 가치 급등 예상 (여신 영업 기회)</div>
                                            </div>

                                            {/* SIGNAL 2: Risk */}
                                            <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20 flex flex-col gap-1">
                                                <div className="flex justify-between items-start">
                                                    <span className="text-[10px] font-bold text-red-400 bg-red-500/20 px-1.5 py-0.5 rounded">RISK (위험)</span>
                                                    <span className="text-[10px] text-red-400/60">10분 전</span>
                                                </div>
                                                <div className="text-sm text-red-100 font-medium">원/달러 환율 1,450원 돌파</div>
                                                <div className="text-[10px] text-red-400/70">→ 유산스 결제 대금 부담 증가 예상</div>
                                            </div>

                                            {/* SIGNAL 3: Info */}
                                            <div className="p-3 bg-white/5 rounded-lg border border-white/5 flex flex-col gap-1 opacity-60">
                                                <div className="flex justify-between items-start">
                                                    <span className="text-[10px] font-bold text-white/60 bg-white/10 px-1.5 py-0.5 rounded">INFO</span>
                                                    <span className="text-[10px] text-white/40">1시간 전</span>
                                                </div>
                                                <div className="text-sm text-white/80 font-medium">주요 원자재 가격 변동</div>
                                            </div>
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

const ImpactSection = () => {
    return (
        <section className="py-40 bg-black relative border-t border-white/5">
            <div className="container mx-auto px-6 max-w-7xl">
                <FadeUp>
                    <div className="text-center mb-20">
                        <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 word-keep-all">
                            비용이 아닌, <span className="text-blue-500">이익</span>으로의 전환
                        </h2>
                        <p className="text-white/40 text-lg">JB금융그룹 기준 시뮬레이션 결과</p>
                    </div>
                </FadeUp>

                <div className="grid md:grid-cols-3 gap-8 items-center">
                    {/* 1. Cost */}
                    <FadeUp delay={0.1} className="relative p-8 rounded-3xl bg-[#111] border border-white/5 flex flex-col items-center text-center">
                        <div className="text-sm text-white/40 font-mono mb-4 uppercase tracking-widest">Current Cost</div>
                        <div className="text-5xl font-bold text-white/40 mb-2">42억</div>
                        <div className="text-sm text-white/30">연간 KYC 운영 비용</div>
                    </FadeUp>

                    {/* Arrow */}
                    <div className="hidden md:flex justify-center text-white/20">
                        <ArrowRight className="w-8 h-8" />
                    </div>

                    {/* 3. Profit */}
                    <FadeUp delay={0.3} className="relative p-10 rounded-3xl bg-gradient-to-b from-blue-900/20 to-blue-900/10 border border-blue-500/30 flex flex-col items-center text-center shadow-[0_0_50px_rgba(37,99,235,0.15)] transform md:scale-110 z-10">
                        <div className="absolute -top-4 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg">경제적 이득</div>
                        <div className="text-sm text-blue-300 font-mono mb-4 uppercase tracking-widest">Total Benefit</div>
                        <div className="text-6xl md:text-7xl font-bold text-white mb-2 drop-shadow-[0_0_20px_rgba(37,99,235,0.5)]">290억</div>
                        <div className="text-sm text-blue-200/60">비즈니스 전환 가치</div>
                    </FadeUp>
                </div>

                <div className="mt-16 text-center">
                    <p className="text-white/40 text-sm">* 수동 분석 시 소요되는 기회비용(250억)과 운영 비용 절감액을 합산한 수치입니다.</p>
                </div>
            </div>
        </section>
    );
};

const UseCasesSection = () => {
    return (
        <section className="py-32 bg-neutral-900 relative overflow-hidden">
            <div className="container mx-auto px-6">
                <FadeUp>
                    <h2 className="text-3xl md:text-5xl font-bold text-white mb-16 text-center word-keep-all">
                        영업 기회와 리스크 관리의 시작
                    </h2>
                </FadeUp>

                <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
                    {/* Case 1: Opp */}
                    <FadeUp delay={0.1} className="group relative overflow-hidden rounded-3xl bg-black border border-white/10 hover:border-green-500/50 transition-colors duration-500">
                        <div className="absolute inset-0 bg-green-500/5 group-hover:bg-green-500/10 transition-colors" />
                        <div className="p-10 relative z-10">
                            <div className="mb-6 w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                                <Landmark className="w-6 h-6 text-green-400" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">선제적 여신 영업</h3>
                            <p className="text-white/60 mb-6">
                                "담보물 가치가 상승할 것이 확실하다면?"<br />
                                도로 개설 정보를 미리 파악하여 여신 한도 증액을 제안합니다.
                            </p>
                            <div className="p-4 rounded-xl bg-green-900/20 border border-green-500/20">
                                <div className="text-xs text-green-400 font-mono mb-1">Detected Signal</div>
                                <div className="text-sm text-white font-medium">MK전자 보유 나대지 인근 도로 포장 공사 발주</div>
                            </div>
                        </div>
                    </FadeUp>

                    {/* Case 2: Risk */}
                    <FadeUp delay={0.2} className="group relative overflow-hidden rounded-3xl bg-black border border-white/10 hover:border-red-500/50 transition-colors duration-500">
                        <div className="absolute inset-0 bg-red-500/5 group-hover:bg-red-500/10 transition-colors" />
                        <div className="p-10 relative z-10">
                            <div className="mb-6 w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
                                <TrendingUp className="w-6 h-6 text-red-400" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">환율 리스크 헷지</h3>
                            <p className="text-white/60 mb-6">
                                "결제일이 다가오는데 환율이 급등한다면?"<br />
                                환율 변동성을 미리 경고하고 선물환 상품을 제안합니다.
                            </p>
                            <div className="p-4 rounded-xl bg-red-900/20 border border-red-500/20">
                                <div className="text-xs text-red-400 font-mono mb-1">Detected Signal</div>
                                <div className="text-sm text-white font-medium">USD/KRW 환율 전일 대비 2.5% 급등 (1,452원)</div>
                            </div>
                        </div>
                    </FadeUp>
                </div>
            </div>
        </section>
    );
};

const Footer = () => (
    <footer className="py-32 bg-black border-t border-white/5 text-center px-6 relative overflow-hidden">
        {/* The Halo */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-blue-600/20 blur-[100px] rounded-full pointer-events-none animate-pulse-slow" />

        <FadeUp className="relative z-10">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-8 tracking-tight word-keep-all">
                이 모든 분석이,<br />단 1분 안에 이루어집니다.
            </h2>

            <div className="group relative inline-block">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-20 group-hover:opacity-75 transition duration-1000 group-hover:duration-200" />
                <Button className="relative h-16 px-12 text-lg rounded-full bg-white text-black hover:bg-neutral-100 hover:scale-105 transition-all duration-300 shadow-[0_0_40px_rgba(255,255,255,0.3)] border border-white/50 word-keep-all">
                    rKYC 엔진 초기화 (Initialize)
                </Button>
            </div>

            <div className="mt-16 text-white/20 text-sm">
                © 2024 Nano Gorilla Team. All rights reserved.
            </div>
        </FadeUp>
    </footer>
);

// --- MAIN PAGE COMPONENT ---

import { Database, Cpu } from "lucide-react"; // Import missing icons

export default function LandingPage() {
    return (
        <div className="bg-black text-white min-h-screen selection:bg-blue-500/50 selection:text-white font-sans">
            {/* GLOBAL NAV */}
            <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-6 flex justify-between items-center bg-gradient-to-b from-black/80 to-transparent backdrop-blur-[2px]">
                <Link to="/" className="text-2xl font-bold tracking-tighter text-white flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-mono text-sm">r</div>
                    rKYC
                </Link>
            </nav>

            <HeroSection />
            <ProblemSection />
            <SolutionSection />
            <ProductShowcase />
            <ImpactSection />
            <UseCasesSection />
            <Footer />
        </div>
    );
}
