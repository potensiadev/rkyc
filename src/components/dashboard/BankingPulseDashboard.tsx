import React from 'react';
import { Column, Pie } from '@ant-design/charts';
import {
    ArrowUpRight,
    Building2,
    AlertTriangle,
    Sparkles,
    Briefcase,
    Globe
} from 'lucide-react';
import { GlassCard } from "@/components/premium";

// --- Types ---
interface BankingPulseDashboardProps {
    bankingData?: any;
    className?: string;
}

// --- Utils ---
const formatKRW = (value: number) => {
    return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(value);
};

const formatAssetType = (type: string) => {
    if (!type) return '';
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
};

// --- Config Helpers ---
const commonChartConfig = {
    padding: 'auto',
    appendPadding: 10,
};

// --- Main Component ---
export function BankingPulseDashboard({ bankingData, className }: BankingPulseDashboardProps) {

    // 1. Loan Exposure Data (Mocked for visual + mapped real logic if available)
    const loanExposureData = [
        { year: '2024', type: '담보대출', value: 500 },
        { year: '2024', type: '신용대출', value: 200 },
        { year: '2024', type: '외화대출', value: 100 },
        { year: '2025', type: '담보대출', value: 600 },
        { year: '2025', type: '신용대출', value: 250 },
        { year: '2025', type: '외화대출', value: 150 },
        { year: '2026', type: '담보대출', value: 700 }, // Projected
        { year: '2026', type: '신용대출', value: 300 },
        { year: '2026', type: '외화대출', value: 200 },
    ];

    const loanConfig = {
        data: loanExposureData,
        isStack: true,
        xField: 'year',
        yField: 'value',
        seriesField: 'type',
        // Matches the card colors: Indigo (Secured), Purple (Unsecured), Rose (Foreign)
        color: ['#6366f1', '#a855f7', '#db2777'],
        columnStyle: {
            radius: [4, 4, 0, 0],
        },
        legend: {
            position: 'top-left' as const,
            itemName: {
                style: {
                    fill: '#94a3b8',
                    fontSize: 12,
                    fontWeight: 500
                }
            },
            marker: { symbol: 'circle' }
        },
        xAxis: {
            label: {
                style: {
                    fill: '#94a3b8',
                    fontSize: 12,
                    fontWeight: 600,
                },
            },
            line: {
                style: { stroke: '#e2e8f0' }
            }
        },
        yAxis: {
            label: {
                formatter: (v: string) => `${v}`,
                style: {
                    fill: '#cbd5e1',
                    fontSize: 11,
                }
            },
            grid: {
                line: {
                    style: {
                        stroke: '#f1f5f9',
                        lineDash: [4, 4],
                    },
                },
            },
        },
        tooltip: {
            domStyles: {
                'g2-tooltip': {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(8px)',
                    boxShadow: '0 10px 30px -10px rgba(0,0,0,0.1)',
                    borderRadius: '12px',
                    border: '1px solid #f1f5f9',
                    padding: '12px',
                    color: '#334155',
                    fontSize: '12px'
                },
            },
        },
        height: 280,
        autoFit: true,
    };

    // 2. Expense Data (Donut)
    const expenseData = [
        { type: '출장비', value: 35 },
        { type: '접대비', value: 25 },
        { type: '기타', value: 40 },
    ];

    const expenseConfig = {
        appendPadding: 10,
        data: expenseData,
        angleField: 'value',
        colorField: 'type',
        radius: 1,
        innerRadius: 0.65,
        color: ['#6366f1', '#a855f7', '#cbd5e1'], // Matches theme
        label: false, // Clean look, hide labels on segments
        statistic: {
            title: false,
            content: {
                style: {
                    whiteSpace: 'pre-wrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    fontSize: '28px',
                    fontWeight: '800',
                    color: '#1e293b',
                    fontFamily: 'monospace' // Premium numeric feel
                },
                content: '55M',
            },
        },
        legend: {
            position: 'right' as const,
            itemHeight: 14,
            itemName: {
                style: { fill: '#64748b', fontSize: 12, fontWeight: 500 },
            },
            marker: { symbol: 'square', style: { r: 3 } }
        },
        interactions: [{ type: 'element-active' }],
        height: 180,
        autoFit: true,
    };

    return (
        <div className={`grid grid-cols-1 lg:grid-cols-12 gap-6 ${className}`}>

            {/* LEFT COLUMN (8 cols) */}
            <div className="lg:col-span-8 flex flex-col gap-6">

                {/* 1. Loan Exposure Trend Chart */}
                <GlassCard className="p-8 pb-4 relative overflow-hidden">
                    <div className="flex justify-between items-start mb-4 relative z-10">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <h3 className="text-base font-bold text-slate-600 uppercase tracking-wide">여신 잔액 추이 (Loan Exposure Trend)</h3>
                                <span className="bg-indigo-50 text-indigo-600 text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-100">등급: A2</span>
                            </div>
                            <div className="flex items-baseline gap-3">
                                <span className="text-4xl font-bold text-slate-900 tracking-tight">120억원</span>
                                <span className="flex items-center text-emerald-500 font-bold text-sm bg-emerald-50 px-2 py-0.5 rounded-full">
                                    <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                                    +20.0% YoY
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Chart Area */}
                    <div className="h-[280px] w-full relative z-10">
                        {/* @ts-ignore */}
                        <Column {...loanConfig} />
                    </div>
                </GlassCard>

                {/* 2. Current Composition Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Card 1 */}
                    <GlassCard className="p-5 flex flex-col justify-between h-[140px] hover:border-indigo-300 transition-colors cursor-default group shadow-[0_4px_20px_-4px_rgba(99,102,241,0.1)]">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-[#6366f1]" />
                            <span className="text-xs font-bold text-slate-500">담보대출</span>
                        </div>
                        <div>
                            <div className="text-2xl font-bold text-indigo-600 mb-1 group-hover:scale-105 transition-transform origin-left">70억원</div>
                            <div className="text-xs text-slate-400 font-medium">비중: <span className="text-slate-600 font-bold">58.3%</span></div>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 mt-3 rounded-full overflow-hidden">
                            <div className="h-full bg-[#6366f1] w-[58.3%] rounded-full" />
                        </div>
                    </GlassCard>

                    {/* Card 2 */}
                    <GlassCard className="p-5 flex flex-col justify-between h-[140px] hover:border-purple-300 transition-colors cursor-default group shadow-[0_4px_20px_-4px_rgba(168,85,247,0.1)]">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-[#a855f7]" />
                            <span className="text-xs font-bold text-slate-500">신용대출</span>
                        </div>
                        <div>
                            <div className="text-2xl font-bold text-purple-600 mb-1 group-hover:scale-105 transition-transform origin-left">30억원</div>
                            <div className="text-xs text-slate-400 font-medium">비중: <span className="text-slate-600 font-bold">25.0%</span></div>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 mt-3 rounded-full overflow-hidden">
                            <div className="h-full bg-[#a855f7] w-[25.0%] rounded-full" />
                        </div>
                    </GlassCard>

                    {/* Card 3 */}
                    <GlassCard className="p-5 flex flex-col justify-between h-[140px] hover:border-pink-300 transition-colors cursor-default group shadow-[0_4px_20px_-4px_rgba(236,72,153,0.1)]">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-[#db2777]" />
                            <span className="text-xs font-bold text-slate-500">외화대출</span>
                        </div>
                        <div>
                            <div className="text-2xl font-bold text-pink-600 mb-1 group-hover:scale-105 transition-transform origin-left">20억원</div>
                            <div className="text-xs text-slate-400 font-medium">비중: <span className="text-slate-600 font-bold">16.7%</span></div>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 mt-3 rounded-full overflow-hidden">
                            <div className="h-full bg-[#db2777] w-[16.7%] rounded-full" />
                        </div>
                    </GlassCard>
                </div>

                {/* 3. Trade Finance & Hedge (Bottom Row) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Trade Finance */}
                    <GlassCard className="p-6">
                        <div className="flex items-center gap-2 mb-6">
                            <Globe className="w-4 h-4 text-slate-400" />
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide">무역금융 (Trade Finance)</h3>
                        </div>

                        <div className="flex justify-between items-end mb-4">
                            <div className="text-left">
                                <div className="text-[10px] text-slate-400 mb-1 font-medium">수출 채권 (Export)</div>
                                <div className="text-2xl font-bold text-indigo-600 font-mono tracking-tight">$3.1M</div>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] text-slate-400 mb-1 font-medium">수입 채무 (Import)</div>
                                <div className="text-2xl font-bold text-rose-500 font-mono tracking-tight">$1.4M</div>
                            </div>
                        </div>

                        {/* Pixel-Perfect Custom Stacked Bar using HTML/CSS */}
                        <div className="w-full">
                            <div className="flex h-3 rounded-full overflow-hidden bg-slate-100">
                                <div className="h-full bg-indigo-500 transition-all duration-1000 w-[69%]" />
                                <div className="h-full bg-rose-500 transition-all duration-1000 w-[31%]" />
                            </div>
                            <div className="flex justify-between mt-2 text-[10px] font-bold text-slate-400 font-mono">
                                <span>69%</span>
                                <span>31%</span>
                            </div>
                        </div>
                    </GlassCard>

                    {/* Hedge Ratio */}
                    <GlassCard className="p-6">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide">환헤지 비율 (Hedge Ratio)</h3>
                            <span className="bg-amber-50 text-amber-600 border border-amber-200 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                주의 필요
                            </span>
                        </div>

                        <div className="flex items-end gap-2 mb-6">
                            <span className="text-4xl font-bold text-slate-900 leading-none font-mono tracking-tight">35%</span>
                            <span className="text-xs font-medium text-slate-500 mb-1">권고치 (50%) 미달</span>
                        </div>

                        {/* Pixel-Perfect Custom Bullet/Progress using HTML/CSS */}
                        <div className="w-full pt-1 relative">
                            {/* Background Track */}
                            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                {/* Actual Value Bar */}
                                <div className="h-full bg-slate-700 w-[35%] rounded-full" />
                            </div>

                            {/* Target Marker */}
                            <div className="absolute top-[-4px] left-[50%] flex flex-col items-center group cursor-help">
                                <div className="h-5 w-0.5 bg-amber-400 z-10" />
                                <span className="absolute -top-5 text-[9px] font-bold text-amber-500 bg-amber-50 px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Target 50%</span>
                            </div>
                        </div>
                        <div className="flex justify-between mt-2 text-[9px] text-slate-400 font-mono">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </GlassCard>
                </div>

            </div>

            {/* RIGHT COLUMN (4 cols) */}
            <div className="lg:col-span-4 flex flex-col gap-6">

                {/* 4. Collateral Info */}
                <GlassCard className="p-0 overflow-hidden">
                    <div className="p-6 pb-4">
                        <div className="flex justify-between items-center mb-6">
                            <div className="space-y-1">
                                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide">주요 담보 (Collateral)</h3>
                            </div>
                            <div className="text-right bg-white border border-slate-100 rounded-lg px-3 py-2 shadow-sm">
                                <div className="text-[10px] font-bold text-slate-400 mb-0.5">Avg LTV</div>
                                <div className="text-sm font-bold text-slate-900">46.7%</div>
                            </div>
                        </div>

                        {/* AI Note */}
                        <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-4 mb-4">
                            <div className="flex gap-2">
                                <Sparkles className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
                                <p className="text-xs text-indigo-800 leading-relaxed font-medium">
                                    <span className="font-bold">AI Note:</span> 울산 공장 인근 인프라 개발 호재로 감정가 상승 예상 (+15%)
                                </p>
                            </div>
                        </div>

                        {/* Collateral Item */}
                        <div className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm hover:border-slate-300 transition-colors cursor-pointer group">
                            <div className="flex items-start gap-3 mb-3">
                                <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                                    <Building2 className="w-4 h-4" />
                                </div>
                                <div>
                                    <div className="text-sm font-bold text-slate-800">울산 남구 무거동 반도체 공장</div>
                                    <div className="text-[10px] text-slate-400 font-mono uppercase mt-0.5">{formatAssetType('REAL_ESTATE')}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 text-xs">
                                <span className="text-slate-400 font-bold w-6">LTV</span>
                                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 w-[46.7%]" />
                                </div>
                                <span className="font-mono font-bold text-emerald-600">46.7%</span>
                            </div>
                        </div>
                    </div>
                </GlassCard>

                {/* 5. Expense Breakdown (Donut) */}
                <GlassCard className="p-6 h-[275px]">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">법인카드 지출 (Expense)</h3>

                    <div className="flex items-center h-[200px]">
                        <div className="flex-1 h-full w-full">
                            {/* @ts-ignore */}
                            <Pie {...expenseConfig} />
                        </div>
                    </div>
                </GlassCard>

            </div>
        </div>
    );
}
