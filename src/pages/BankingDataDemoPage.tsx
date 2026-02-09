
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    ArrowLeft, Search, RefreshCw, Download,
    TrendingUp, TrendingDown, DollarSign, Activity, AlertTriangle,
    MapPin, Building2, CreditCard, Globe, PieChart as PieChartIcon,
    ArrowUpRight, ArrowDownRight, MoreHorizontal, ShieldCheck, ShieldAlert,
    BrainCircuit, Sparkles
} from "lucide-react";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell, PieChart, Pie, Sector, Legend, LineChart, Line
} from "recharts";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { DynamicBackground, GlassCard, StatusBadge, Tag } from "@/components/premium";
import { MainLayout } from "@/components/layout/MainLayout";
import { DrillDownSheet } from "@/components/dashboard/DrillDownSheet";
import { motion } from "framer-motion";

// --- Mock Data ---

const LOAN_TREND_DATA = [
    { year: "2023", secured: 420, unsecured: 150, fx: 80 },
    { year: "2024", secured: 480, unsecured: 180, fx: 120 },
    { year: "2025", secured: 550, unsecured: 220, fx: 150 },
    { year: "2026", secured: 700, unsecured: 300, fx: 200 },
];

const DEPOSIT_TREND_DATA = [
    { month: "Jul", balance: 250 },
    { month: "Aug", balance: 280 },
    { month: "Sep", balance: 260 },
    { month: "Oct", balance: 310 },
    { month: "Nov", balance: 290 },
    { month: "Dec", balance: 320 },
    { month: "Jan", balance: 350 },
];

const EXPORT_IMPORT_DATA = [
    { month: "Jul", export: 120, import: 80 },
    { month: "Aug", export: 135, import: 92 },
    { month: "Sep", export: 118, import: 85 },
    { month: "Oct", export: 142, import: 98 },
    { month: "Nov", export: 138, import: 91 },
    { month: "Dec", export: 155, import: 105 },
    { month: "Jan", export: 148, import: 99 },
];

const CARD_USAGE_DATA = [
    { name: "Travel", value: 35, color: "#6366f1" },
    { name: "Entertainment", value: 22, color: "#8b5cf6" },
    { name: "Supplies", value: 18, color: "#ec4899" },
    { name: "Fuel", value: 12, color: "#f43f5e" },
    { name: "Others", value: 13, color: "#94a3b8" },
];

// --- Components ---

const RiskBanner = () => (
    <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: "auto", opacity: 1 }}
        className="bg-red-500/10 border-l-4 border-red-500 p-4 mb-6 rounded-r-lg flex items-start gap-4"
    >
        <div className="p-2 bg-red-100/10 rounded-full">
            <AlertTriangle className="w-5 h-5 text-red-500" />
        </div>
        <div>
            <h4 className="text-sm font-bold text-red-500 mb-1">High Risk Alert Detected</h4>
            <p className="text-sm text-red-400/90">
                <span className="font-semibold">FX Hedge Ratio 35%</span> - Extremely vulnerable to recent volatility. Recommended immediate action: Forward Exchange Booking.
            </p>
        </div>
        <Button size="sm" variant="ghost" className="ml-auto text-red-400 hover:text-red-300 hover:bg-red-500/10">
            View Details <ArrowUpRight className="ml-1 w-4 h-4" />
        </Button>
    </motion.div>
);

const SectionHeader = ({ icon: Icon, title, subtitle }: { icon: any, title: string, subtitle?: string }) => (
    <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Icon className="w-4 h-4" />
        </div>
        <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">{title}</h2>
            {subtitle && <p className="text-xs text-slate-400 font-medium">{subtitle}</p>}
        </div>
    </div>
);

export default function BankingDataDemoPage() {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState("overview");
    const [drillDownConfig, setDrillDownConfig] = useState<{ isOpen: boolean; title: string; data: any } | null>(null);

    const handleChartClick = (data: any, titlePrefix: string, timeKey: string) => {
        if (data && data.activePayload && data.activePayload.length > 0) {
            const payload = data.activePayload[0].payload;
            setDrillDownConfig({
                isOpen: true,
                title: `${titlePrefix} (${payload[timeKey]})`,
                data: [payload]
            });
        }
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-32 selection:bg-indigo-100 selection:text-indigo-900">
            <DynamicBackground />

            {/* Navbar (Simplified) */}
            <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-white/20 px-6 py-3 shadow-sm flex justify-between items-center">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => navigate(-1)}><ArrowLeft className="w-4 h-4" /></Button>
                    <div className="flex items-center gap-2">
                        <h1 className="text-base font-bold text-slate-900">MK Electronics (Drafting)</h1>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-500">KOSDAQ: 033160</span>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm"><RefreshCw className="w-3.5 h-3.5 mr-2" /> Refresh Data</Button>
                    <Button variant="default" size="sm" className="bg-indigo-600 hover:bg-indigo-700"><Download className="w-3.5 h-3.5 mr-2" /> Export Report</Button>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">

                {/* 1. Risk Banner */}
                <RiskBanner />

                {/* 2. Top KPI Cards - High Density */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <GlassCard className="p-5">
                        <div className="flex justify-between items-start mb-3">
                            <div className="p-1.5 bg-blue-50 rounded-md text-blue-600"><DollarSign className="w-4 h-4" /></div>
                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">총 여신 잔액 (Exposure)</span>
                        </div>
                        <div className="text-2xl font-bold text-slate-900 mb-1 font-mono tracking-tight">120억 KRW</div>
                        <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 font-mono">
                            <TrendingUp className="w-3 h-3" /> +15% YoY
                        </div>
                    </GlassCard>
                    <GlassCard className="p-5">
                        <div className="flex justify-between items-start mb-3">
                            <div className="p-1.5 bg-purple-50 rounded-md text-purple-600"><Activity className="w-4 h-4" /></div>
                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">내부 신용 등급 (Grade)</span>
                        </div>
                        <div className="text-2xl font-bold text-slate-900 mb-1 font-mono tracking-tight">A2</div>
                        <div className="flex items-center gap-1 text-[11px] font-medium text-slate-500 border border-slate-200 rounded px-1.5 py-0.5 bg-slate-50">
                            Stable Outlook
                        </div>
                    </GlassCard>
                    <GlassCard className="p-5">
                        <div className="flex justify-between items-start mb-3">
                            <div className="p-1.5 bg-amber-50 rounded-md text-amber-600"><AlertTriangle className="w-4 h-4" /></div>
                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">위험 신호 (Risk Alerts)</span>
                        </div>
                        <div className="text-2xl font-bold text-slate-900 mb-1 font-mono tracking-tight">2 <span className="text-sm font-normal text-slate-400">건</span></div>
                        <div className="flex items-center gap-1 text-[11px] font-medium text-amber-600">
                            즉시 조치 필요
                        </div>
                    </GlassCard>
                    <GlassCard className="p-0 border-none shadow-lg bg-gradient-to-br from-indigo-600 to-violet-700 text-white relative overflow-hidden group hover:shadow-indigo-500/30 transition-shadow">
                        <div className="absolute top-0 right-0 p-3 opacity-20"><BrainCircuit className="w-16 h-16" /></div>
                        <div className="p-5 relative z-10 flex flex-col h-full justify-between">
                            <div className="flex items-center gap-2 mb-2 opacity-90">
                                <Sparkles className="w-4 h-4 text-indigo-200" />
                                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-100">AI Insight</span>
                            </div>
                            <div>
                                <div className="text-lg font-bold mb-1 leading-tight">담보 가치 상승 예상</div>
                                <p className="text-[11px] text-indigo-100 leading-snug opacity-90">
                                    인근 GTX 노선 확정으로 공장 부지 가치 +15% 상승 전망. 담보 여력 확대 가능.
                                </p>
                            </div>
                        </div>
                    </GlassCard>
                </div>

                {/* 3. Main Data Dashboard */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                    {/* Left Column (Main Charts) - 8/12 */}
                    <div className="lg:col-span-8 space-y-6">

                        {/* Loan & Deposit Chart */}
                        <GlassCard className="p-5">
                            <div className="flex items-center justify-between mb-5">
                                <SectionHeader icon={TrendingUp} title="여/수신 현황 (Banking Relationship)" subtitle="Credit Exposure & Deposit Trend" />
                                <div className="flex gap-2">
                                    <Button size="sm" variant={activeTab === 'overview' ? 'secondary' : 'ghost'} onClick={() => setActiveTab('overview')} className="h-8 text-[11px]">전체 개요</Button>
                                    <Button size="sm" variant={activeTab === 'loan' ? 'secondary' : 'ghost'} onClick={() => setActiveTab('loan')} className="h-8 text-[11px]">여신 상세</Button>
                                </div>
                            </div>

                            <div className="h-[280px] w-full relative">
                                {/* Credit Limit Line */}
                                <div className="absolute top-[18%] left-[45px] right-0 border-t border-dashed border-slate-300 z-0"></div>
                                <span className="absolute top-[15%] right-0 text-[10px] text-slate-400 font-mono bg-white/50 px-1 backdrop-blur-sm z-0">Total Limit: 2,000억</span>

                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart
                                        data={LOAN_TREND_DATA}
                                        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                                        onClick={(data) => handleChartClick(data, "여신 상세 내역", "year")}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <defs>
                                            <linearGradient id="colorSecured" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                            </linearGradient>
                                            <linearGradient id="colorUnsecured" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.15} />
                                                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} fontFamily="monospace" tickMargin={10} />
                                        <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}억`} fontFamily="monospace" />
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px -2px rgba(0, 0, 0, 0.08)', fontSize: '12px', fontFamily: 'monospace' }}
                                            labelStyle={{ color: '#64748b', fontSize: '11px', marginBottom: '4px' }}
                                            cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '4 4' }}
                                        />
                                        <Area type="monotone" dataKey="secured" stackId="1" stroke="#6366f1" fill="url(#colorSecured)" strokeWidth={2} name="담보대출" activeDot={{ r: 4, strokeWidth: 0 }} />
                                        <Area type="monotone" dataKey="unsecured" stackId="1" stroke="#8b5cf6" fill="url(#colorUnsecured)" strokeWidth={2} name="신용대출" />
                                        <Area type="monotone" dataKey="fx" stackId="1" stroke="#ec4899" fill="#fbcfe8" strokeWidth={2} name="외화대출" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </GlassCard>

                        {/* Trade Finance & FX */}
                        <GlassCard className="p-5">
                            <SectionHeader icon={Globe} title="글로벌 무역금융 (Global Trade)" subtitle="수출입 실적 및 환리스크 관리 현황" />
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-2">
                                <div className="h-[220px]">
                                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center justify-between">
                                        수출입 실적 추이 (USD)
                                        <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-normal normal-case">전년 대비 실선 표시</span>
                                    </h4>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart
                                            data={EXPORT_IMPORT_DATA}
                                            onClick={(data) => handleChartClick(data, "수출입 상세 내역", "month")}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                            <XAxis dataKey="month" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} fontFamily="monospace" />
                                            <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} fontFamily="monospace" />
                                            <Tooltip
                                                contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontFamily: 'monospace', fontSize: '12px' }}
                                                cursor={{ stroke: '#94a3b8', strokeWidth: 1 }}
                                            />
                                            <Legend iconType="circle" fontSize={10} wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                                            {/* Benchmark Line (YoY) - Mock */}
                                            <Line type="monotone" dataKey={() => 100} stroke="#e2e8f0" strokeWidth={2} dot={false} strokeDasharray="4 4" name="전년 평균" />
                                            <Line type="monotone" dataKey="export" stroke="#2563eb" strokeWidth={2} dot={false} activeDot={{ r: 4 }} name="수출 (Export)" />
                                            <Line type="monotone" dataKey="import" stroke="#f43f5e" strokeWidth={2} dot={false} name="수입 (Import)" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="space-y-6">
                                    <div>
                                        <div className="flex justify-between text-[11px] mb-2 font-mono">
                                            <span className="font-bold text-slate-500 font-sans">유산스 한도 소진율 (Usance)</span>
                                            <span className="font-bold text-red-600">90% <span className="text-slate-400 font-normal">/ 100%</span></span>
                                        </div>
                                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden relative">
                                            <div className="h-full bg-red-500 w-[90%] rounded-full absolute top-0 left-0" />
                                            {/* Limit Marker */}
                                            <div className="absolute top-0 bottom-0 w-0.5 bg-slate-900/20 right-[10%] z-10"></div>
                                        </div>
                                        <p className="text-[10px] text-red-500 mt-1.5 font-medium flex items-center gap-1">
                                            <AlertTriangle className="w-3 h-3" /> 한도 초과 임박 (Limit Warning)
                                        </p>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-[11px] mb-2 font-mono">
                                            <span className="font-bold text-slate-500 font-sans">환헤지 비율 (Hedge Ratio)</span>
                                            <span className="font-bold text-amber-600">35%</span>
                                        </div>
                                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden relative">
                                            <div className="h-full bg-amber-400 w-[35%] rounded-full absolute top-0 left-0" />
                                            {/* Target Marker */}
                                            <div className="absolute top-0 bottom-0 w-0.5 bg-indigo-500/50 left-[50%] z-10"></div>
                                        </div>
                                        <div className="flex justify-between mt-1">
                                            <p className="text-[10px] text-amber-500 font-medium">권고치 미달 (Target 50%)</p>
                                            <span className="text-[9px] text-indigo-400 font-mono">Target: 50%</span>
                                        </div>
                                    </div>

                                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                                        <div className="text-[11px] font-bold text-slate-500 mb-2 uppercase tracking-wider">국가별 익스포저 (Country Exposure)</div>
                                        <div className="flex gap-2">
                                            <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-700 font-mono shadow-sm">🇨🇳 CN 35%</span>
                                            <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-700 font-mono shadow-sm">🇺🇸 US 28%</span>
                                            <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-700 font-mono shadow-sm">🇯🇵 JP 15%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </GlassCard>

                    </div>

                    {/* Right Column (Side Data) - 4/12 */}
                    <div className="lg:col-span-4 space-y-6">

                        {/* Collateral Card */}
                        <GlassCard className="p-5 flex flex-col h-auto">
                            <SectionHeader icon={Building2} title="담보 관리 (Collateral)" />
                            <div className="space-y-3 flex-1">
                                <div className="p-3 bg-white border border-indigo-100 rounded-xl shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-all cursor-pointer ring-1 ring-transparent hover:ring-indigo-100">
                                    <div className="absolute top-0 right-0 p-1.5 bg-indigo-500 rounded-bl-lg shadow-sm">
                                        <ArrowUpRight className="w-3 h-3 text-white" />
                                    </div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center text-slate-500 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors border border-slate-100">
                                            <MapPin className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-slate-900">울산 제2공장 (Ulsan Factory)</div>
                                            <div className="text-[10px] text-slate-400 font-mono">감정가: 85억 KRW</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 mt-3">
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                                            <Sparkles className="w-3 h-3" /> 개발 호재 지역
                                        </span>
                                        <span className="text-[10px] text-slate-400 font-mono ml-auto">LTV: 60%</span>
                                    </div>
                                </div>

                                <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm opacity-60 hover:opacity-100 transition-opacity cursor-pointer text-slate-400 grayscale hover:grayscale-0">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400 border border-slate-100">
                                            <MapPin className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-slate-700">동해 물류센터</div>
                                            <div className="text-[10px] text-slate-400 font-mono">감정가: 32억 KRW</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className="text-[10px] text-slate-400 font-mono ml-auto">LTV: 60%</span>
                                    </div>
                                </div>
                            </div>
                        </GlassCard>

                        {/* Card Usage */}
                        <GlassCard className="p-5">
                            <SectionHeader icon={CreditCard} title="법인카드 지출 (Expense)" />
                            <div className="h-[180px] relative mt-2">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={CARD_USAGE_DATA}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={50}
                                            outerRadius={70}
                                            paddingAngle={4}
                                            dataKey="value"
                                        >
                                            {CARD_USAGE_DATA.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontFamily: 'monospace', fontSize: '11px' }}
                                            itemStyle={{ color: '#334155' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="absolute inset-0 flex items-center justify-center pointer-events-none flex-col">
                                    <div className="text-center">
                                        <div className="text-xl font-bold text-slate-900 font-mono">55M</div>
                                        <div className="text-[10px] text-slate-400">월 평균 (Avg)</div>
                                    </div>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-x-4 gap-y-2 justify-center mt-2 px-4">
                                {CARD_USAGE_DATA.slice(0, 3).map((item, i) => (
                                    <div key={i} className="flex items-center gap-1.5 text-[11px]">
                                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                                        <span className="text-slate-600 font-medium">{item.name} <span className="font-mono text-slate-400">{item.value}%</span></span>
                                    </div>
                                ))}
                            </div>
                        </GlassCard>

                    </div>
                </div>

            </main>

            {/* Drill Down Sheet */}
            {drillDownConfig && (
                <DrillDownSheet
                    isOpen={drillDownConfig.isOpen}
                    onClose={() => setDrillDownConfig(null)}
                    title={drillDownConfig.title}
                    data={drillDownConfig.data}
                />
            )}
        </div>
    );
}

