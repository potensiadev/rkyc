import React, { useState } from "react";
import { motion } from "framer-motion";
import {
    ArrowLeft,
    MoreHorizontal,
    FileText,
    Download,
    Share2,
    Globe
} from "lucide-react";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    AreaChart,
    Area,
    Tooltip
} from "recharts";
import { Button } from "@/components/ui/button";

// --- Custom Premium Icons (Silicon Valley Style) ---
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

const IconSearch = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="8" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="2" />
        <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
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

const IconProfile = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" />
        <path d="M9 9H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M9 13H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M9 17H12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
);

const IconBrain = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M12 16V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M12 8H12.01" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <circle cx="12" cy="12" r="6" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" />
    </svg>
);

// --- Mock Data ---
const RISK_SCORE = 72; // 0-100

const MOCK_SUMMARY = {
    name: "엠케이전자",
    industry: "기타 반도체 소자 제조업",
    credit: "중립/안정적",
    description: "엠케이전자는 반도체 패키징용 소재 분야에서 글로벌 본딩와이어 시장 점유율 1위를 차지하고 있으며, 솔더볼 시장에서도 글로벌 Top 3에 속하는 경쟁력을 보유하고 있습니다. 현재 특이 시그널이 감지되지 않았습니다.",
};

const MOCK_CORP_DETAILS = {
    ceo: "현기진",
    bizNo: "135-81-06406",
    corpNo: "134511-0004412",
    founded: "1982년",
    address: "경기도 용인시 처인구 이동읍 백옥대로 765",
    type: "법인사업자",
    indCode: "C26 (제조업)"
};

const MOCK_INTELLIGENCE = {
    revenue: "8,806억원",
    export: "85%",
    employees: "393명",
    bizModel: "엠케이전자는 반도체 패키징 공정의 핵심 재료인 본딩와이어와 솔더볼을 제조하여 글로벌 반도체 후공정 업체에 공급하는 B2B 비즈니스 모델을 운영하고 있다.",
    suppliers: ["고려아연", "LS MnM"],
    customers: ["삼성전자", "SK하이닉스", "마이크론", "ASE", "Amkor", "JCET", "SPIL"],
    materials: ["금", "은", "구리", "주석"],
    singleSourceRisk: ["금"],
    supplyChainGeo: { "한국": 70, "기타": 30 },
    competitors: ["ASE", "Amkor", "JCET"],
    factors: {
        positive: ["전기차 수요 증가"],
        negative: ["금 가격 변동", "환율 변동"],
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
    globalExposure: "대만 30% 중국 40% 동남아시아 30%"
}

const MOCK_BANK_DATA = {
    loan: "12", // 억
    deposit: "-", // 억
    fx: "-",
    collateral: "부동산",
    kyc: "KYC 완료",
    updateDate: "2024-11-15"
};

const MOCK_SIGNALS = {
    direct: 0,
    industry: 0,
    environment: 2
};


// --- Premium UI Components (Advanced Interactions) ---

const DynamicBackground = () => (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-200/20 rounded-full blur-[120px] animate-pulse" style={{ animationDuration: '8s' }} />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-100/20 rounded-full blur-[120px] animate-pulse" style={{ animationDuration: '10s' }} />
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] bg-rose-100/10 rounded-full blur-[100px]" />
    </div>
);

const AnimatedCounter = ({ value, duration = 2 }: { value: number | string, duration?: number }) => {
    // A simplified counter effect for demo purposes. 
    // In a real app, use 'useSpring' or a library like 'react-countup'
    return <span className="tabular-nums font-feature-settings-tnum">{value}</span>;
};

// Spotlight Effect Card
const SpotlightCard = ({ children, className = "", delay = 0 }: { children: React.ReactNode, className?: string, delay?: number }) => {
    const divRef = React.useRef<HTMLDivElement>(null);
    const [isFocused, setIsFocused] = React.useState(false);
    const [position, setPosition] = React.useState({ x: 0, y: 0 });
    const [opacity, setOpacity] = React.useState(0);

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!divRef.current) return;
        const rect = divRef.current.getBoundingClientRect();
        setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };

    const handleFocus = () => {
        setIsFocused(true);
        setOpacity(1);
    };

    const handleBlur = () => {
        setIsFocused(false);
        setOpacity(0);
    };

    const handleMouseEnter = () => {
        setOpacity(1);
    };

    const handleMouseLeave = () => {
        setOpacity(0);
    };

    return (
        <motion.div
            ref={divRef}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay, ease: "easeOut" }}
            onMouseMove={handleMouseMove}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            className={`
                relative overflow-hidden rounded-2xl border border-white/40 bg-white/60 
                backdrop-blur-xl shadow-sm transition-shadow duration-300 hover:shadow-lg hover:border-indigo-200/50
                group ${className}
            `}
        >
            <div
                className="pointer-events-none absolute -inset-px opacity-0 transition duration-300 group-hover:opacity-100"
                style={{
                    opacity,
                    background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, rgba(99,102,241,0.06), transparent 40%)`,
                }}
            />
            {children}
        </motion.div>
    );
};
// Re-export as GlassCard for compatibility with existing usage
const GlassCard = SpotlightCard;

const SectionHeader = ({ icon: Icon, title, subtitle }: { icon: any, title: string, subtitle?: string }) => (
    <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 text-slate-700 border border-slate-200 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
            <Icon className="w-4 h-4" />
        </div>
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">{title}</h2>
        {subtitle && <span className="text-xs text-slate-400 font-medium px-2 py-0.5 rounded-full bg-slate-50 border border-slate-100">{subtitle}</span>}
    </div>
);

// --- Premium Micro-Components ---

// 1. StatusBadge: Used for statuses (Active, Warning, Stable)
// Design: "Glowing Dot" style - minimalist, clean, breathable.
const StatusBadge = ({ children, variant = "neutral", className = "" }: { children: React.ReactNode, variant?: "success" | "warning" | "danger" | "neutral" | "brand", className?: string }) => {
    const styles = {
        success: { dot: "bg-emerald-500", shadow: "shadow-[0_0_8px_2px_rgba(16,185,129,0.15)]", text: "text-slate-700", border: "border-emerald-200/60", bg: "bg-emerald-50/40" },
        warning: { dot: "bg-amber-500", shadow: "shadow-[0_0_8px_2px_rgba(245,158,11,0.15)]", text: "text-slate-700", border: "border-amber-200/60", bg: "bg-amber-50/40" },
        danger: { dot: "bg-rose-500", shadow: "shadow-[0_0_8px_2px_rgba(244,63,94,0.15)]", text: "text-slate-700", border: "border-rose-200/60", bg: "bg-rose-50/40" },
        neutral: { dot: "bg-slate-400", shadow: "shadow-none", text: "text-slate-600", border: "border-slate-200", bg: "bg-slate-50/50" },
        brand: { dot: "bg-indigo-500", shadow: "shadow-[0_0_8px_2px_rgba(99,102,241,0.2)]", text: "text-slate-700", border: "border-indigo-200/60", bg: "bg-indigo-50/40" },
    };

    const style = styles[variant] || styles.neutral;

    return (
        <span className={`
            inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium tracking-tight
            border ${style.border} ${style.bg} ${style.text} backdrop-blur-sm
            ${className}
        `}>
            <span className={`w-1.5 h-1.5 rounded-full ${style.dot} ${style.shadow} animate-pulse`} style={{ animationDuration: '3s' }} />
            {children}
        </span>
    );
};

// 2. Tag: Used for categories, lists (Suppliers, Competitors)
// Design: Apple-style "lozenge" - subtle gray background, high legibility.
const Tag = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
    <span className={`
        inline-flex items-center px-2 py-1 rounded-[6px] text-[11px] font-medium text-slate-600 
        bg-slate-100/80 border border-slate-200/60 hover:bg-slate-200/60 hover:text-slate-900 transition-colors cursor-default
        ${className}
    `}>
        {children}
    </span>
);

// Backward compatibility or specialized unified wrapper if needed
const Badge = ({ children, variant }: { children: React.ReactNode, variant?: any }) => {
    // Map old variants to new components just in case, or direct usage
    if (variant === 'outline') return <Tag>{children}</Tag>;
    return <StatusBadge variant={variant}>{children}</StatusBadge>;
};

const DataField = ({ label, value, isHighlighted = false }: { label: string, value: string, isHighlighted?: boolean }) => (
    <div className="flex flex-col gap-1.5 min-w-[120px]">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{label}</span>
        <span className={`text-[13px] ${isHighlighted ? 'text-slate-900 font-bold' : 'text-slate-700 font-medium'} truncate`}>
            {value}
        </span>
    </div>
);

export default function DesignShowcasePage() {
    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-20 overflow-hidden relative">
            <DynamicBackground />

            {/* Header */}
            <motion.div
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="sticky top-0 z-50 border-b border-indigo-100/50 bg-white/80 backdrop-filter backdrop-blur-lg px-6 py-3"
            >
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-slate-100 rounded-full text-slate-500">
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                                {MOCK_SUMMARY.name}
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500 border border-slate-200">KOSDAQ</span>
                            </h1>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="h-8 text-xs border-slate-200 text-slate-600 hover:bg-slate-50">
                            <Share2 className="w-3.5 h-3.5 mr-1.5" />
                            Share
                        </Button>
                        <Button variant="outline" size="sm" className="h-8 text-xs border-slate-200 text-slate-600 hover:bg-slate-50">
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            PDF
                        </Button>
                        <Button size="sm" className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-100">
                            심사 승인 요청
                        </Button>
                    </div>
                </div>
            </motion.div>

            <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">

                {/* 1. Executive Summary & KPIs */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Summary Text */}
                    <GlassCard className="lg:col-span-2 p-6" delay={0.1}>
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-base font-bold text-slate-900">요약 (Executive Summary)</h3>
                            <Badge variant="success">중립/안정적</Badge>
                        </div>
                        <p className="text-[13px] leading-relaxed text-slate-600 bg-slate-50 rounded-lg p-4 border border-slate-100">
                            {MOCK_SUMMARY.description}
                        </p>
                        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500 bg-white border border-slate-100 rounded-md px-3 py-2 w-fit">
                            <span className="font-semibold text-slate-700">탐지된 시그널:</span>
                            <span>직접 {MOCK_SIGNALS.direct}건</span>
                            <span className="w-px h-3 bg-slate-200" />
                            <span>산업 {MOCK_SIGNALS.industry}건</span>
                            <span className="w-px h-3 bg-slate-200" />
                            <span>환경 {MOCK_SIGNALS.environment}건</span>
                        </div>
                    </GlassCard>

                    {/* Risk Gauge */}
                    <GlassCard className="p-6 flex flex-col items-center justify-center bg-white" delay={0.2}>
                        <div className="text-center mb-4">
                            <h3 className="text-sm font-bold text-slate-900">AI Risk Score</h3>
                            <p className="text-[11px] text-slate-400 mt-1">실시간 종합 위험도</p>
                        </div>

                        <div className="w-40 h-20 relative mb-4">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie data={[{ value: 1 }]} cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={55} outerRadius={75} dataKey="value" stroke="none" isAnimationActive={false}>
                                        <Cell fill="#F1F5F9" />
                                    </Pie>
                                    <Pie data={[{ value: RISK_SCORE }, { value: 100 - RISK_SCORE }]} cx="50%" cy="100%" startAngle={180} endAngle={0} innerRadius={55} outerRadius={75} dataKey="value" cornerRadius={6} stroke="none">
                                        <Cell fill="#EF4444" />
                                        <Cell fill="transparent" />
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="absolute inset-0 flex items-end justify-center transform translate-y-1">
                                <span className="text-4xl font-black text-slate-900 tracking-tighter">{RISK_SCORE}</span>
                                <span className="text-sm text-slate-400 font-bold ml-1 mb-1">/100</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#FFF1F2] border border-[#FECDD3]">
                            <StatusBadge variant="danger" className="border-0 bg-transparent px-0 py-0">Warning Level</StatusBadge>
                        </div>
                    </GlassCard>
                </div>

                {/* 2. Corporate Profile & Bank Relationship */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Corporate Profile */}
                    <GlassCard className="p-6" delay={0.3}>
                        <SectionHeader icon={IconBuilding} title="기업 개요" />
                        <div className="grid grid-cols-2 gap-y-6 gap-x-8">
                            <DataField label="기업명" value={MOCK_SUMMARY.name} isHighlighted />
                            <DataField label="대표이사" value={MOCK_CORP_DETAILS.ceo} />
                            <DataField label="사업자등록번호" value={MOCK_CORP_DETAILS.bizNo} />
                            <DataField label="법인등록번호" value={MOCK_CORP_DETAILS.corpNo} />
                            <DataField label="업종" value={MOCK_SUMMARY.industry} />
                            <DataField label="설립년도" value={MOCK_CORP_DETAILS.founded} />
                            <DataField label="업종코드" value={MOCK_CORP_DETAILS.indCode} />
                            <DataField label="사업자 유형" value={MOCK_CORP_DETAILS.type} />
                            <div className="col-span-2 border-t border-slate-50 pt-4 mt-2">
                                <DataField label="본사 소재지" value={MOCK_CORP_DETAILS.address} />
                            </div>
                        </div>
                    </GlassCard>

                    {/* Bank Relationship */}
                    <GlassCard className="p-6" delay={0.4}>
                        <SectionHeader icon={IconBank} title="당행 거래 현황" />

                        {/* Status Bar */}
                        <div className="flex items-center bg-slate-50 rounded-lg p-3 border border-slate-100 mb-6 font-mono text-sm">
                            <div className="flex-1 flex flex-col items-center border-r border-slate-200">
                                <span className="text-[10px] text-slate-400 font-bold uppercase mb-1">수신 (Deposit)</span>
                                <span className="font-bold text-slate-400">-</span>
                            </div>
                            <div className="flex-1 flex flex-col items-center border-r border-slate-200">
                                <span className="text-[10px] text-indigo-500 font-bold uppercase mb-1">여신 (Loan)</span>
                                <span className="font-bold text-indigo-700">{MOCK_BANK_DATA.loan}억원</span>
                            </div>
                            <div className="flex-1 flex flex-col items-center">
                                <span className="text-[10px] text-slate-400 font-bold uppercase mb-1">외환 (FX)</span>
                                <span className="font-bold text-slate-400">-</span>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center bg-white p-3 rounded-lg border border-slate-100 shadow-sm">
                                <span className="text-xs font-semibold text-slate-600">KYC 상태</span>
                                <div className="flex gap-2">
                                    <Badge variant="success">KYC 완료</Badge>
                                    <Badge variant="warning">중위험</Badge>
                                </div>
                            </div>
                            <div className="flex justify-between items-center bg-white p-3 rounded-lg border border-slate-100 shadow-sm">
                                <span className="text-xs font-semibold text-slate-600">담보 종류</span>
                                <Badge variant="neutral">부동산</Badge>
                            </div>
                            <div className="text-right">
                                <span className="text-[10px] text-slate-400">갱신일: {MOCK_BANK_DATA.updateDate}</span>
                            </div>

                        </div>
                    </GlassCard>
                </div>

                {/* 3. Corporate Intelligence (FULL DATA) */}
                <GlassCard className="p-6" delay={0.5}>
                    <SectionHeader icon={IconBrain} title="기업 인텔리전스" subtitle="Advanced Analytics" />

                    {/* Business Overview Text */}
                    <div className="mb-8">
                        <h4 className="text-[12px] font-bold text-slate-800 mb-3 px-1 border-l-2 border-slate-800">사업 개요</h4>
                        <p className="text-[13px] leading-7 text-slate-600 text-justify">
                            {MOCK_INTELLIGENCE.bizModel}
                        </p>
                        <div className="flex gap-6 mt-4 pt-4 border-t border-slate-100">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-slate-400 font-bold uppercase">연간 매출</span>
                                <span className="text-sm font-bold text-slate-900">{MOCK_INTELLIGENCE.revenue}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] text-slate-400 font-bold uppercase">수출 비중</span>
                                <span className="text-sm font-bold text-slate-900">{MOCK_INTELLIGENCE.export}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] text-slate-400 font-bold uppercase">임직원 수</span>
                                <span className="text-sm font-bold text-slate-900">{MOCK_INTELLIGENCE.employees}</span>
                            </div>
                        </div>
                    </div>

                    {/* Intelligence Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 border-t border-slate-100 pt-8">

                        {/* Left Column: Value Chain */}
                        <div className="space-y-8">
                            <div>
                                <h4 className="flex items-center gap-2 text-[12px] font-bold text-slate-800 mb-4">
                                    <IconLayer className="w-4 h-4 text-slate-500" /> 밸류체인 (Value Chain)
                                </h4>

                                <div className="space-y-4">
                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">공급사 (Suppliers)</p>
                                        <div className="flex flex-wrap gap-2">
                                            {MOCK_INTELLIGENCE.suppliers.map(v => (
                                                <Tag key={v}>{v}</Tag>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">고객사 (Customers)</p>
                                        <div className="flex flex-wrap gap-2">
                                            {MOCK_INTELLIGENCE.customers.map(v => (
                                                <Tag key={v}>{v}</Tag>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                            <p className="text-[11px] font-bold text-slate-500 mb-2">주요 원자재</p>
                                            <div className="flex flex-wrap gap-2">
                                                {MOCK_INTELLIGENCE.materials.map(v => (
                                                    <span key={v} className="text-xs font-medium text-slate-700 bg-white px-2 py-1 rounded border border-slate-200">{v}</span>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                                            <p className="text-[11px] font-bold text-red-500 mb-2">⚠️ 단일 조달치 위험</p>
                                            <div className="flex flex-wrap gap-2">
                                                {MOCK_INTELLIGENCE.singleSourceRisk.map(v => (
                                                    <span key={v} className="text-xs font-bold text-red-700 bg-white px-2 py-1 rounded border border-red-200">{v}</span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">공급 국가 비중</p>
                                        <div className="flex gap-4 text-xs font-medium text-slate-700">
                                            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-400"></span>기타 30%</div>
                                            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-400"></span>한국 70%</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right Column: Market Position */}
                        <div className="space-y-8">
                            <div>
                                <h4 className="flex items-center gap-2 text-[12px] font-bold text-slate-800 mb-4">
                                    <IconTarget className="w-4 h-4 text-slate-500" /> 시장 포지션 (Market Position)
                                </h4>

                                <div className="space-y-4">
                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">경쟁사 (Competitors)</p>
                                        <div className="flex flex-wrap gap-2">
                                            {MOCK_INTELLIGENCE.competitors.map(v => (
                                                <Tag key={v}>{v}</Tag>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">거시 요인 (Macro Factors)</p>
                                        <div className="flex flex-wrap gap-2 mb-2">
                                            {MOCK_INTELLIGENCE.factors.positive.map(v => (
                                                <span key={v} className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
                                                    <IconGrowth className="w-3 h-3" /> {v}
                                                </span>
                                            ))}
                                            {MOCK_INTELLIGENCE.factors.negative.map(v => (
                                                <span key={v} className="flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 px-2 py-1 rounded border border-rose-200">
                                                    <IconRisk className="w-3 h-3" /> {v}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                        <p className="text-[11px] font-bold text-slate-500 mb-2">주요 주주 현황</p>
                                        <div className="space-y-2">
                                            {MOCK_INTELLIGENCE.shareholders.map(s => (
                                                <div key={s.name} className="flex justify-between items-center text-xs border-b border-slate-200/50 last:border-0 pb-1.5 last:pb-0">
                                                    <span className="text-slate-700 font-medium">{s.name}</span>
                                                    <span className="font-mono text-slate-500">{s.share}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-white rounded-xl p-3 border border-slate-200 flex items-start gap-3">
                                        <Globe className="w-4 h-4 text-indigo-500 mt-0.5" />
                                        <div>
                                            <p className="text-[11px] font-bold text-slate-700 mb-1">글로벌 노출</p>
                                            <p className="text-xs text-slate-600">{MOCK_INTELLIGENCE.globalExposure}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>

                    {/* Global Sites Footer */}
                    <div className="mt-6 flex flex-wrap gap-2 bg-indigo-50/50 p-4 rounded-xl border border-indigo-100">
                        <span className="text-xs font-bold text-indigo-800 mr-2 flex items-center"><Globe className="w-3 h-3 mr-1" />해외 사업장:</span>
                        {MOCK_INTELLIGENCE.globalSites.map(s => (
                            <span key={s.name} className="text-xs text-indigo-700 bg-white px-2 py-1 rounded shadow-sm border border-indigo-100">
                                {s.name} <span className="text-indigo-400 opacity-70">({s.type})</span>
                            </span>
                        ))}
                    </div>
                </GlassCard>
            </main>
        </div>
    );
}
