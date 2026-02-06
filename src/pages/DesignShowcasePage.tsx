import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    ArrowLeft,
    Search,
    Command,
    Sparkles,
    TrendingUp,
    ChevronRight,
    CornerDownRight,
    Globe,
    Share2,
    Download
} from "lucide-react";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer
} from "recharts";
import { Button } from "@/components/ui/button";



// --- Icons ---
const IconBuilding = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M2 22H22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path fillRule="evenodd" clipRule="evenodd" d="M17 2H7C5.89543 2 5 2.89543 5 4V22H19V4C19 2.89543 18.1046 2 17 2Z" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9 7H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M9 11H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M9 15H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
);
const IconZaps = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);
const IconLayer = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);
const IconTarget = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <circle cx="12" cy="12" r="6" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="2" />
        <circle cx="12" cy="12" r="2" fill="currentColor" />
    </svg>
);
const IconBank = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M3 21H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M5 21V7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M19 21V7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M5 7L12 3L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M10 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M14 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
);
const IconRisk = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" clipRule="evenodd" d="M12 2L2 22H22L12 2Z" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 8V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M12 18H12.01" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
);
const IconGrowth = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M22 6L13.5 14.5L8.5 9.5L2 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M16 6H22V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 20H22" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" strokeLinecap="round" />
    </svg>
);

// --- Components ---

import {
    DynamicBackground,
    GlassCard,
    StatusBadge,
    Tag,
    Sparkline,
    ContextualHighlight,
    HoverCard
} from "@/components/premium";

// --- Hooks ---
const useScrollSpy = (ids: string[], offset: number = 100) => {
    const [activeId, setActiveId] = useState("");

    useEffect(() => {
        const listener = () => {
            const scroll = window.scrollY;
            for (const id of ids) {
                const element = document.getElementById(id);
                if (element) {
                    const top = element.offsetTop - offset;
                    const bottom = top + element.offsetHeight;
                    if (scroll >= top && scroll < bottom) {
                        setActiveId(id);
                        break;
                    }
                }
            }
        };
        window.addEventListener("scroll", listener);
        return () => window.removeEventListener("scroll", listener);
    }, [ids, offset]);

    return activeId;
};

const TOC = ({ items, activeId }: { items: { id: string, label: string }[], activeId: string }) => (
    <div className="space-y-1">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest px-3 mb-4">Contents</p>
        <div className="relative border-l border-slate-200 ml-3 space-y-4 py-2">
            {items.map(item => (
                <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`block pl-4 text-xs font-medium transition-colors border-l-2 -ml-[1px] py-1 ${activeId === item.id ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
                >
                    {item.label}
                </a>
            ))}
        </div>
    </div>
);

const StickyCommandBar = () => (
    <div className="fixed bottom-6 right-6 z-40 bg-white/90 backdrop-blur-md border border-slate-200 shadow-2xl shadow-indigo-500/10 rounded-full px-4 py-2 flex items-center gap-3 transition-transform hover:-translate-y-1 cursor-pointer group">
        <div className="flex items-center justify-center w-6 h-6 bg-slate-100 rounded text-slate-500 group-hover:text-indigo-600 group-hover:bg-indigo-50 transition-colors">
            <Command className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-semibold text-slate-700">Actions</span>
        <div className="w-px h-3 bg-slate-200" />
        <span className="text-[10px] text-slate-400 font-mono">Cmd + K</span>
    </div>
);


const SectionHeader = ({ icon: Icon, title, subtitle }: { icon: any, title: string, subtitle?: string }) => (
    <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-50 text-slate-700 border border-slate-100">
            <Icon className="w-4 h-4" />
        </div>
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">{title}</h2>
        {subtitle && (
            <div className="flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-slate-300" />
                <span className="text-xs text-slate-400 font-medium">{subtitle}</span>
            </div>
        )}
    </div>
);

const DataField = ({ label, value, isHighlighted = false }: { label: string, value: string | React.ReactNode, isHighlighted?: boolean }) => (
    <div className="flex flex-col gap-1.5">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</span>
        <span className={`text-[13px] ${isHighlighted ? 'text-slate-900 font-bold' : 'text-slate-700 font-medium'} font-mono leading-tight truncate`}>
            {value}
        </span>
    </div>
);

// --- FULL MOCK DATA (Restored & Enhanced) ---
const RISK_SCORE = 72;
const MOCK_SUMMARY = {
    name: "엠케이전자",
    marketState: "KOSDAQ: 033160",
    description: "엠케이전자는 반도체 패키징용 소재 분야에서 글로벌 본딩와이어 시장 점유율 1위를 차지하고 있으며, 솔더볼 시장에서도 글로벌 Top 3에 속합니다. 현재 특이 시그널이 감지되지 않았으나, 매크로 변동성에 대한 주의가 필요합니다.",
    riskSentence: "최근 금 가격 변동성이 확대됨에 따라 원자재 비용 부담이 증가할 수 있는 리스크가 감지됩니다.",
    signals: { direct: 0, industry: 0, environment: 2 }
};

const MOCK_CORP_DETAILS = {
    ceo: "현기진",
    bizNo: "135-81-06406",
    corpNo: "134511-0004412",
    founded: "1982년",
    address: "경기도 용인시 처인구 이동읍 백옥대로 765",
    type: "법인사업자",
    indCode: "C26 (제조업 - 반도체 소재)"
};

const MOCK_BANK_DATA = {
    loan: "12",
    loanTrend: [10, 11, 12, 11, 12, 12],
    deposit: "34",
    depositTrend: [30, 32, 33, 34, 34, 34],
    fx: "-",
    collateral: "부동산",
    kyc: "Completed",
    updateDate: "2024-11-15"
};

const MOCK_INTELLIGENCE = {
    revenue: "8,806억원",
    export: "85%",
    employees: "393명",
    bizModel: "반도체 패키징 공정의 핵심 재료인 본딩와이어와 솔더볼을 제조하여 글로벌 반도체 후공정(OSAT) 및 IDM 업체에 공급하는 B2B 비즈니스 모델. 고순도 금속 정련 기술을 바탕으로 2차전지 소재 등 신사업으로 확장 중.",
    suppliers: ["고려아연", "LS MnM"],
    customers: ["삼성전자", "SK하이닉스", "마이크론", "ASE", "Amkor", "JCET"],
    materials: ["금(Au)", "은(Ag)", "구리(Cu)", "주석(Sn)"],
    singleSourceRisk: ["금(Au)"],
    supplyChainGeo: { "한국": 70, "기타": 30 },
    competitors: [
        { name: "ASE Technology", marketShare: "Global #1", desc: "Taiwan based OSAT leader" },
        { name: "Amkor Tech", marketShare: "Global #2", desc: "US based packaging giant" },
        { name: "JCET Group", marketShare: "Global #3", desc: "China based competitor" }
    ],
    factors: {
        positive: ["전기차 수요 증가", "AI 반도체 패키징 고도화"],
        negative: ["금 가격 변동", "환율 변동성 확대"],
    },
    shareholders: [
        { name: "오션홀딩스", share: "25.14%" },
        { name: "신성건설", share: "5.75%" },
        { name: "차정훈", share: "5.07%" },
        { name: "자사주", share: "2.92%" },
    ],
    globalSites: [
        { name: "MK Electron (Kunshan)", type: "중국 법인" },
        { name: "대만 사무소", type: "해외 지사" },
        { name: "홍콩 판매 법인", type: "판매 법인" }
    ],
    globalExposure: "대만 30% 중국 40% 동남아 30%"
};

// --- Demo Guide Overlay (Cinematic Walkthrough) ---

const DEMO_STEPS = [
    {
        targetId: "summary-card",
        title: "Executive Summary",
        desc: "AI가 분석한 기업의 핵심 요약과 리스크 전망을 가장 먼저 확인하세요. 긍정/부정 요인이 한눈에 파악됩니다.",
        position: "bottom-right"
    },
    {
        targetId: "risk-score-card",
        title: "AI Risk Score",
        desc: "실시간 데이터 기반으로 산출된 통합 리스크 점수입니다. 70점 이상은 '주의' 단계로 심층 모니터링이 필요합니다.",
        position: "bottom-left"
    },
    {
        targetId: "financial-sparklines",
        title: "Financial Flow",
        desc: "여신 및 수신 잔액의 지난 6개월 변동 추이(Sparkline)를 통해 단순 잔액뿐만 아니라 자금의 흐름을 파악합니다.",
        position: "top-right"
    },
    {
        targetId: "value-chain-map",
        title: "Interactive Value Chain",
        desc: "공급사부터 고객사까지 이어지는 밸류체인 맵입니다. 각 노드에 마우스를 올리면(Hover) 의존도와 리스크 상세 정보를 볼 수 있습니다.",
        position: "top-center"
    },
    {
        targetId: "ai-assistant-widget",
        title: "AI Analysis Assistant",
        desc: "궁금한 점은 언제든 AI에게 물어보세요. 기업 데이터와 시장 상황을 종합하여 실시간으로 답변해 줍니다.",
        position: "left"
    }
];

const DemoOverlay = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
    const [currentStep, setCurrentStep] = useState(0);

    useEffect(() => {
        if (!isOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                if (currentStep < DEMO_STEPS.length - 1) {
                    setCurrentStep(c => c + 1);
                } else {
                    onClose();
                }
            } else if (e.key === 'ArrowLeft') {
                if (currentStep > 0) setCurrentStep(c => c - 1);
            } else if (e.key === 'Escape') {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, currentStep, onClose]);

    // Calculate spotlight position (Simplified for this static layout demo)
    // In a real app, use getBoundingClientRect() here.
    // For this showcase, we will use a centralized 'focus' UI approach 
    // where we Dim everything and show the tooltip and a visual highlight.

    // Position mappings for the 'Spotlight' visuals based on the target IDs
    // These are approximations for the demo effect to work smoothly without complex rect logic code overhead
    const getStepStyles = (index: number) => {
        switch (index) {
            case 0: return { top: '18%', left: '33%', width: '500px', height: '240px' }; // Summary
            case 1: return { top: '18%', left: '72%', width: '300px', height: '240px' }; // Risk Score
            case 2: return { top: '55%', left: '25%', width: '600px', height: '200px' }; // Financials
            case 3: return { top: '80%', left: '40%', width: '700px', height: '300px' }; // Value Chain
            case 4: return { top: '30%', left: '85%', width: '300px', height: '300px' }; // AI Widget
            default: return { top: '50%', left: '50%', width: '0px', height: '0px' };
        }
    };

    const spotlightStyle = getStepStyles(currentStep);

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-auto"
                >
                    {/* Backdrop with Blur */}
                    <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-all duration-500" />

                    {/* Spotlight Cutout Simulation (Moving Glow) */}
                    <motion.div
                        layoutId="spotlight"
                        className="absolute bg-transparent border-2 border-indigo-400/50 shadow-[0_0_0_9999px_rgba(15,23,42,0.6)] rounded-3xl z-10 box-content transition-all duration-500 ease-in-out"
                        style={{
                            top: spotlightStyle.top,
                            left: spotlightStyle.left,
                            width: spotlightStyle.width,
                            height: spotlightStyle.height,
                            transform: 'translate(-50%, -50%)',
                            boxShadow: '0 0 0 9999px rgba(15,23,42,0.6), 0 0 40px rgba(99,102,241,0.3)'
                        }}
                    />

                    {/* Glass Tooltip */}
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -20, scale: 0.95 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="absolute z-20 max-w-sm"
                        style={{
                            top: `calc(${spotlightStyle.top} + ${parseInt(spotlightStyle.height) / 2 + 20}px)`,
                            left: spotlightStyle.left,
                            transform: 'translateX(-50%)'
                        }}
                    >
                        <div className="bg-white/10 backdrop-blur-xl border border-white/20 p-6 rounded-2xl shadow-2xl text-white">
                            <div className="flex items-center gap-2 mb-3">
                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-500 text-[10px] font-bold">
                                    {currentStep + 1}
                                </span>
                                <h3 className="font-bold text-lg">{DEMO_STEPS[currentStep].title}</h3>
                            </div>
                            <p className="text-sm text-slate-200 leading-relaxed mb-6">
                                {DEMO_STEPS[currentStep].desc}
                            </p>
                            <div className="flex justify-between items-center text-xs text-slate-400 font-mono">
                                <span>Press <b className="text-white">Space</b> to continue</span>
                                <div>
                                    <span className="text-white">{currentStep + 1}</span> / {DEMO_STEPS.length}
                                </div>
                            </div>
                        </div>
                        {/* Glow effect behind tooltip */}
                        <div className="absolute inset-0 -z-10 bg-indigo-500/20 blur-2xl rounded-full" />
                    </motion.div>

                    {/* Skip Button */}
                    <button
                        onClick={onClose}
                        className="absolute top-8 right-8 text-white/50 hover:text-white text-sm font-medium z-20 flex items-center gap-2 transition-colors"
                    >
                        Skip Tour <span className="px-1.5 py-0.5 rounded border border-white/20 text-[10px]">ESC</span>
                    </button>

                </motion.div>
            )}
        </AnimatePresence>
    );
};

const TOC_ITEMS = [
    { id: "summary", label: "Executive Summary" },
    { id: "profile", label: "Corporate Profile" },
    { id: "financials", label: "Bank Relationship" },
    { id: "intelligence", label: "Intelligence & Flow" },
];

export default function DesignShowcasePage() {
    const activeSection = useScrollSpy(TOC_ITEMS.map(i => i.id));
    const [isTourOpen, setIsTourOpen] = useState(false);

    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-32 relative selection:bg-indigo-100 selection:text-indigo-900 group/page">
            <DynamicBackground />
            <DemoOverlay isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
            <StickyCommandBar />

            {/* Navbar */}
            <motion.div
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-white/20 px-6 py-3 shadow-sm"
            >
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-slate-100 rounded-full text-slate-500">
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <div className="flex items-center gap-2">
                            <h1 className="text-base font-bold text-slate-900">{MOCK_SUMMARY.name}</h1>
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-500">{MOCK_SUMMARY.marketState}</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="hidden md:flex relative group">
                            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input type="text" placeholder="Search..." className="h-8 pl-9 pr-4 rounded-full bg-slate-50 border border-transparent text-xs focus:bg-white focus:border-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-100/50 transition-all w-48" />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-300 font-mono group-hover:text-slate-400">/</span>
                        </div>
                        <div className="h-4 w-px bg-slate-200 mx-2" />

                        {/* Tour Trigger Button */}
                        <Button
                            variant="outline" size="sm"
                            onClick={() => setIsTourOpen(true)}
                            className="h-8 text-xs border-indigo-200 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 mr-2"
                        >
                            <Sparkles className="w-3.5 h-3.5 mr-1.5 fill-indigo-600/20" />
                            Start Demo
                        </Button>

                        <Button variant="outline" size="sm" className="h-8 w-8 p-0 rounded-full border-slate-200 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50"><Share2 className="w-3.5 h-3.5" /></Button>
                        <Button variant="outline" size="sm" className="h-8 w-8 p-0 rounded-full border-slate-200 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50"><Download className="w-3.5 h-3.5" /></Button>
                        <Button size="sm" className="h-8 text-xs bg-slate-900 hover:bg-slate-800 text-white shadow-lg shadow-slate-200 rounded-full px-4 ml-2">
                            Review
                        </Button>
                    </div>
                </div>
            </motion.div>

            <main className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">

                    {/* Left: Main Content */}
                    <div className="lg:col-span-9 space-y-8">

                        {/* 1. Summary & Gauge */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6" id="summary">
                            <GlassCard className="md:col-span-2 p-8" id="summary-card">
                                <div className="flex justify-between items-start mb-6">
                                    <h3 className="text-lg font-bold text-slate-900">Executive Summary</h3>
                                    <StatusBadge variant="success">Positive Outlook</StatusBadge>
                                </div>
                                <p className="text-[14px] leading-relaxed text-slate-600 mb-6 bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                                    {MOCK_SUMMARY.description} <ContextualHighlight text={MOCK_SUMMARY.riskSentence} reason="금 가격 변동성은 2주 전 대비 15% 증가하여 단기 마진 압박 요인으로 작용할 수 있습니다." />
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    <Tag className="gap-2">
                                        <IconZaps className="w-3 h-3 text-slate-400" />
                                        Signals: Direct {MOCK_SUMMARY.signals.direct} / Ind {MOCK_SUMMARY.signals.industry} / Env {MOCK_SUMMARY.signals.environment}
                                    </Tag>
                                    <Tag className="gap-2">
                                        <Globe className="w-3 h-3 text-slate-400" />
                                        Global Exposure: Extensive
                                    </Tag>
                                </div>
                            </GlassCard>

                            <GlassCard className="p-6 flex flex-col items-center justify-center relative overflow-hidden text-center" id="risk-score-card">
                                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-400 opacity-20" />
                                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">AI Risk Score</h3>
                                <div className="relative mb-2">
                                    <ResponsiveContainer width={160} height={80}>
                                        <PieChart>
                                            <Pie data={[{ value: 1 }]} cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={60} outerRadius={80} dataKey="value" stroke="none" isAnimationActive={false}>
                                                <Cell fill="#f1f5f9" />
                                            </Pie>
                                            <Pie data={[{ value: RISK_SCORE }, { value: 100 - RISK_SCORE }]} cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={60} outerRadius={80} dataKey="value" cornerRadius={12} stroke="none">
                                                <Cell fill="#F43F5E" />
                                                <Cell fill="transparent" />
                                            </Pie>
                                        </PieChart>
                                    </ResponsiveContainer>
                                    <div className="absolute inset-0 flex items-end justify-center transform translate-y-1">
                                        <span className="text-5xl font-mono font-bold text-slate-900 tracking-tighter">{RISK_SCORE}</span>
                                    </div>
                                </div>
                                <StatusBadge variant="danger" className="mt-2 text-[10px] uppercase">Warning Level</StatusBadge>
                            </GlassCard>
                        </div>

                        {/* 2. Corporate Profile Grid */}
                        <div id="profile">
                            <GlassCard className="p-8">
                                <SectionHeader icon={IconBuilding} title="Corporate Profile" />
                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                                    <DataField label="CEO" value={MOCK_CORP_DETAILS.ceo} isHighlighted />
                                    <DataField label="Established" value={MOCK_CORP_DETAILS.founded} />
                                    <DataField label="Biz Type" value={MOCK_CORP_DETAILS.type} />
                                    <DataField label="Industry" value={MOCK_CORP_DETAILS.indCode} />
                                    <div className="lg:col-span-2">
                                        <DataField label="Headquarters" value={MOCK_CORP_DETAILS.address} />
                                    </div>
                                    <DataField label="Tax Code" value={MOCK_CORP_DETAILS.bizNo} />
                                    <DataField label="Corp Code" value={MOCK_CORP_DETAILS.corpNo} />
                                </div>
                            </GlassCard>
                        </div>

                        {/* 3. Financial Relationship */}
                        <div id="financials">
                            <GlassCard className="p-8" id="financial-sparklines">
                                <SectionHeader icon={IconBank} title="Bank Relationship" />
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
                                    {/* Loan */}
                                    <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 hover:bg-white hover:shadow-md transition-all group relative overflow-hidden">
                                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                            <TrendingUp className="w-12 h-12 text-indigo-600" />
                                        </div>
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Total Loan</p>
                                                <div className="flex items-baseline gap-1">
                                                    <span className="text-3xl font-mono font-bold text-slate-900">{MOCK_BANK_DATA.loan}</span>
                                                    <span className="text-sm font-medium text-slate-500">억원</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="h-12 w-full">
                                            <Sparkline data={MOCK_BANK_DATA.loanTrend} color="#6366f1" />
                                        </div>
                                    </div>

                                    {/* Deposit */}
                                    <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 hover:bg-white hover:shadow-md transition-all group relative overflow-hidden">
                                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                            <TrendingUp className="w-12 h-12 text-emerald-600" />
                                        </div>
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Total Deposit</p>
                                                <div className="flex items-baseline gap-1">
                                                    <span className="text-3xl font-mono font-bold text-slate-900">{MOCK_BANK_DATA.deposit}</span>
                                                    <span className="text-sm font-medium text-slate-500">억원</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="h-12 w-full">
                                            <Sparkline data={MOCK_BANK_DATA.depositTrend} color="#10b981" />
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-4 pt-6 border-t border-slate-100">
                                    <DataField label="Collateral" value={MOCK_BANK_DATA.collateral} />
                                    <DataField label="FX Service" value={MOCK_BANK_DATA.fx} />
                                    <div className="flex flex-col gap-1.5">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">KYC Status</span>
                                        <StatusBadge variant="success">{MOCK_BANK_DATA.kyc}</StatusBadge>
                                    </div>
                                </div>
                            </GlassCard>
                        </div>

                        {/* 4. Intelligence & Flow (FULL DATA RESTORED) */}
                        <div id="intelligence">
                            <GlassCard className="p-8 space-y-8" id="value-chain-map">
                                <div className="flex items-center justify-between">
                                    <SectionHeader icon={IconLayer} title="Deep Intelligence" subtitle="Full Analysis" />
                                    <Button variant="outline" size="sm" className="h-7 text-[10px] uppercase font-bold text-slate-500 border-slate-200">Export Report</Button>
                                </div>

                                {/* Business Overview */}
                                <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                                    <h4 className="text-xs font-bold text-slate-800 mb-3 flex items-center gap-2">
                                        <span className="w-1 h-4 bg-indigo-500 rounded-full" /> Business Overview
                                    </h4>
                                    <p className="text-[13px] leading-relaxed text-slate-600 text-justify mb-6">
                                        {MOCK_INTELLIGENCE.bizModel}
                                    </p>
                                    <div className="flex gap-8">
                                        <DataField label="Revenue" value={MOCK_INTELLIGENCE.revenue} />
                                        <DataField label="Export" value={MOCK_INTELLIGENCE.export} />
                                        <DataField label="Employees" value={MOCK_INTELLIGENCE.employees} />
                                    </div>
                                </div>

                                {/* Value Chain Flow */}
                                <div className="relative flex items-center justify-between gap-4 px-4 py-8 bg-white/50 rounded-3xl border border-dotted border-slate-200 overflow-x-auto">
                                    <div className="absolute top-1/2 left-10 right-10 h-0.5 bg-slate-200 -z-10" />

                                    {/* Suppliers Section (Interactive) */}
                                    <div className="flex flex-col gap-3 min-w-[120px]">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase text-center mb-1">Suppliers</span>
                                        {MOCK_INTELLIGENCE.suppliers.map(s => (
                                            <HoverCard key={s} trigger={
                                                <div className="bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm text-xs font-medium text-slate-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors cursor-pointer w-full text-center">
                                                    {s}
                                                </div>
                                            } content={
                                                <div>
                                                    <span className="font-bold text-slate-800 block mb-1">{s}</span>
                                                    <StatusBadge variant="neutral">Major Supplier</StatusBadge>
                                                </div>
                                            } />
                                        ))}
                                    </div>

                                    <div className="flex items-center text-slate-300"><ChevronRight className="w-5 h-5 animate-pulse" /><ChevronRight className="w-5 h-5 animate-pulse delay-75" /></div>

                                    {/* Center Core */}
                                    <div className="relative px-4">
                                        <div className="absolute -inset-4 bg-indigo-100/50 rounded-full blur-xl animate-pulse" />
                                        <div className="relative bg-white p-6 rounded-2xl border-2 border-indigo-100 shadow-xl flex flex-col items-center gap-2 w-48">
                                            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                                                <IconTarget className="w-5 h-5" />
                                            </div>
                                            <span className="text-sm font-bold text-slate-900">{MOCK_SUMMARY.name}</span>

                                            {/* Materials & Risks */}
                                            <div className="flex flex-wrap justify-center gap-1 mt-2">
                                                {MOCK_INTELLIGENCE.materials.map(m => (
                                                    <span key={m} className={`text-[9px] px-1.5 py-0.5 rounded border ${MOCK_INTELLIGENCE.singleSourceRisk.includes(m) ? 'bg-rose-50 text-rose-600 border-rose-100 font-bold' : 'bg-slate-50 text-slate-500 border-slate-100'}`}>{m}</span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center text-slate-300"><ChevronRight className="w-5 h-5 animate-pulse" /><ChevronRight className="w-5 h-5 animate-pulse delay-75" /></div>

                                    {/* Customers */}
                                    <div className="grid grid-cols-2 gap-2 min-w-[200px]">
                                        {MOCK_INTELLIGENCE.customers.map(c => (
                                            <div key={c} className="bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm text-xs font-medium text-slate-600 text-center flex items-center justify-center h-full">
                                                {c}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Deep Analysis Grid (Macro, Competitors, Shareholders) */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                                    {/* Competitors & Macro */}
                                    <div className="space-y-6">
                                        <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                                            <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Competitors</h5>
                                            <div className="space-y-3">
                                                {MOCK_INTELLIGENCE.competitors.map(c => (
                                                    <div key={c.name} className="flex justify-between items-center bg-white p-3 rounded-xl border border-slate-100 shadow-sm">
                                                        <div>
                                                            <div className="text-xs font-bold text-slate-800">{c.name}</div>
                                                            <div className="text-[10px] text-slate-400">{c.desc}</div>
                                                        </div>
                                                        <Tag>{c.marketShare}</Tag>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                                            <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Macro Factors</h5>
                                            <div className="flex flex-wrap gap-2">
                                                {MOCK_INTELLIGENCE.factors.positive.map(f => (
                                                    <StatusBadge key={f} variant="success" className="bg-white border-emerald-100">{f}</StatusBadge>
                                                ))}
                                                {MOCK_INTELLIGENCE.factors.negative.map(f => (
                                                    <StatusBadge key={f} variant="danger" className="bg-white border-rose-100">{f}</StatusBadge>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Shareholders & Global Sites */}
                                    <div className="space-y-6">
                                        <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 h-full">
                                            <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Shareholders</h5>
                                            <table className="w-full text-xs text-left">
                                                <tbody>
                                                    {MOCK_INTELLIGENCE.shareholders.map((s, i) => (
                                                        <tr key={s.name} className="border-b border-slate-100 last:border-0 hover:bg-white/50 transition-colors">
                                                            <td className="py-2 text-slate-600 font-medium pl-2">{s.name}</td>
                                                            <td className="py-2 text-slate-800 font-mono text-right pr-2">{s.share}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>

                                            <div className="mt-8 pt-6 border-t border-slate-200">
                                                <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Global Sites</h5>
                                                <div className="flex flex-wrap gap-2">
                                                    {MOCK_INTELLIGENCE.globalSites.map(s => (
                                                        <div key={s.name} className="flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 rounded-md shadow-sm">
                                                            <Globe className="w-3 h-3 text-indigo-400" />
                                                            <span className="text-[10px] font-medium text-slate-700">{s.name}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                </div>
                            </GlassCard>
                        </div>

                    </div>

                    {/* Right: Sticky Sidebar (TOC) */}
                    <div className="hidden lg:block lg:col-span-3">
                        <div className="sticky top-24 space-y-8">
                            <TOC items={TOC_ITEMS} activeId={activeSection} />

                            {/* Ask AI Mini Widget */}
                            <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl p-6 text-white shadow-xl shadow-indigo-200">
                                <div className="flex items-center gap-2 mb-3">
                                    <Sparkles className="w-4 h-4 text-indigo-200" />
                                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-100">AI Assistant</span>
                                </div>
                                <p className="text-sm font-medium leading-snug mb-4 text-indigo-50">
                                    Ask about the correlation between gold prices and MK Electron's margin.
                                </p>
                                <div className="relative">
                                    <input type="text" placeholder="Ask a question..." className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-xs text-white placeholder:text-indigo-200/70 focus:outline-none focus:bg-white/20 transition-all" />
                                    <CornerDownRight className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-indigo-200" />
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}
