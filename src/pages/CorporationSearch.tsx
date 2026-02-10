import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Search, Building2, ChevronRight, AlertCircle, Loader2, BarChart3, TrendingUp, ArrowUpRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { useCorporations, useSignals } from "@/hooks/useApi";
import { getBankingData, ApiBankingDataResponse } from "@/lib/api";
import { buildSignalCountsByCorpId, getCorpSignalCountsFromMap } from "@/data/signals";
import { DynamicBackground, GlassCard, StatusBadge, Tag } from "@/components/premium";
import { motion } from "framer-motion";

// 금액 포맷팅 함수 (억원 단위)
function formatLoanBalance(amountKrw: number | undefined | null): string {
  if (!amountKrw) return "-";
  const amountInBillion = amountKrw / 100_000_000; // 억원 단위
  if (amountInBillion >= 1) {
    return `${amountInBillion.toFixed(1)}억원`;
  }
  const amountInMillion = amountKrw / 10_000; // 만원 단위
  return `${amountInMillion.toFixed(0)}만원`;
}

const signalTypeConfig = {
  direct: { label: "직접", className: "bg-indigo-50 text-indigo-600 border-indigo-100" },
  industry: { label: "산업", className: "bg-cyan-50 text-cyan-600 border-cyan-100" },
  environment: { label: "환경", className: "bg-slate-50 text-slate-500 border-slate-100" },
};

export default function CorporationSearch() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  // API에서 데이터 로드
  const { data: corporations = [], isLoading, error } = useCorporations();
  const { data: signals = [] } = useSignals();

  // 모든 기업의 Banking Data를 병렬로 가져오기
  const bankingDataQueries = useQueries({
    queries: corporations.map((corp) => ({
      queryKey: ["banking-data", corp.id],
      queryFn: () => getBankingData(corp.id),
      enabled: corporations.length > 0,
      staleTime: 5 * 60 * 1000,
      retry: false,
    })),
  });

  // Banking Data에서 여신 잔액 맵 생성
  const loanBalanceMap = useMemo(() => {
    const map = new Map<string, number>();
    bankingDataQueries.forEach((query, index) => {
      if (query.data) {
        const bankingData = query.data as ApiBankingDataResponse;
        // loan_exposure는 Record<string, unknown> 타입이므로 타입 단언 필요
        const loanExposure = bankingData.loan_exposure as { total_exposure_krw?: number } | null;
        const loanAmount = loanExposure?.total_exposure_krw;
        if (loanAmount) {
          map.set(corporations[index]?.id, loanAmount);
        }
      }
    });
    return map;
  }, [bankingDataQueries, corporations]);

  // Precompute signal counts map once when signals change
  const signalCountsMap = useMemo(
    () => buildSignalCountsByCorpId(signals),
    [signals]
  );

  // 검색 필터링
  const filteredCorporations = useMemo(() => {
    if (!searchQuery.trim()) return corporations;
    const query = searchQuery.toLowerCase();
    return corporations.filter(
      c => c.name.toLowerCase().includes(query) ||
        c.businessNumber.includes(query)
    );
  }, [corporations, searchQuery]);

  // Click company -> go directly to report
  const handleCorporationClick = (corporateId: string, corporateName: string) => {
    navigate(`/corporations/${corporateId}`, { state: { corpName: corporateName } });
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-100px)]">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
          <p className="text-slate-500 font-medium animate-pulse">기업 레지스트리 스캔 중...</p>
        </div>
      </MainLayout>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto pt-20">
          <GlassCard className="p-8 text-center border-rose-200 bg-rose-50/50">
            <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-rose-700">데이터 로드 실패</h3>
            <p className="text-rose-500">잠시 후 다시 시도해주세요.</p>
          </GlassCard>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-6xl mx-auto pb-20 relative z-10 space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center pt-8 pb-4"
        >
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-3">기업 인텔리전스</h1>
          {/* <p className="text-slate-500 text-lg max-w-2xl mx-auto word-keep-all">
            기업의 상세 프로필, 실시간 리스크 시그널, 그리고 여신 한도 분석에 접근하세요.
          </p> */}
        </motion.div>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="sticky top-4 z-20"
        >
          <GlassCard className="p-2 flex gap-2 shadow-2xl shadow-indigo-500/10 ring-1 ring-indigo-500/20 backdrop-blur-xl bg-white/80">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-indigo-400" />
              <Input
                type="text"
                placeholder="기업명 또는 법인등록번호로 검색..."
                className="pl-12 h-12 text-base border-0 bg-transparent focus-visible:ring-0 placeholder:text-slate-400"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button className="h-12 px-8 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/30 rounded-xl transition-all hover:scale-105 active:scale-95">
              검색
            </Button>
          </GlassCard>
        </motion.div>

        {/* Grid List */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
        >
          {filteredCorporations.map((corp, idx) => {
            const signalCounts = getCorpSignalCountsFromMap(signalCountsMap, corp.id);
            const loanBalance = loanBalanceMap.get(corp.id);

            return (
              <motion.div
                key={corp.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, scale: 1.005 }}
                transition={{ delay: 0.1 + (idx * 0.05) }}
                onClick={() => handleCorporationClick(corp.id, corp.name)}
                className="group relative h-full"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <GlassCard className="h-full relative overflow-hidden border-slate-200/60 group-hover:border-indigo-500/30 transition-colors bg-white/80 backdrop-blur-xl">

                  <div className="p-6 flex flex-col h-full relative z-10">
                    {/* Top Row: Identification & Risk */}
                    <div className="flex justify-between items-start mb-6">
                      <div className="space-y-3">
                        {/* Industry Tag - Minimalist */}
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-500 border border-slate-200/50">
                            {corp.industry}
                          </span>
                          <span className="text-[10px] font-mono text-slate-300">
                            {corp.businessNumber.substring(0, 3)}-**
                          </span>
                        </div>
                        {/* Company Name - Clean & Bold */}
                        <h3 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight group-hover:text-indigo-900 transition-colors leading-none">
                          {corp.name}
                        </h3>
                      </div>

                      {/* Risk Indicator Pulse */}
                      {signalCounts.total > 0 && (
                        <div className="relative flex items-center justify-center w-8 h-8 rounded-full bg-slate-50 border border-slate-100 shadow-sm ml-4">
                          <div className={`absolute w-full h-full rounded-full animate-ping opacity-20 ${signalCounts.direct > 0 ? 'bg-rose-500' : 'bg-amber-400'}`} />
                          <div className={`relative w-2.5 h-2.5 rounded-full ${signalCounts.direct > 0 ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]' : 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]'}`} />
                        </div>
                      )}
                    </div>

                    {/* Middle: Financial Impact Hero */}
                    <div className="mb-8">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1.5 opacity-80">
                        <BarChart3 className="w-3 h-3" />
                        Total Exposure
                      </p>
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-4xl font-bold text-slate-800 tracking-tighter tabular-nums group-hover:text-indigo-600 transition-colors leading-none">
                          {formatLoanBalance(loanBalance).replace(/[^\d.]/g, '')}
                        </span>
                        <span className="text-sm font-semibold text-slate-400 mb-1">
                          {formatLoanBalance(loanBalance).replace(/[\d.]/g, '')}
                        </span>
                      </div>
                    </div>

                    {/* Bottom: Signal Visualization Grid */}
                    <div className="mt-auto pt-4 border-t border-slate-100/50 flex items-center justify-between group-hover:border-indigo-100/50 transition-colors">
                      <div className="flex flex-col gap-1.5">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide opacity-80">Signal Profile</span>
                        <div className="flex items-center gap-1 h-4">
                          {signalCounts.total === 0 ? (
                            <span className="text-[10px] text-slate-300 font-medium tracking-tight">Active Signals Cleared</span>
                          ) : (
                            <>
                              {/* Visual Dots for Signals - Direct */}
                              {Array.from({ length: Math.min(signalCounts.direct, 5) }).map((_, i) => (
                                <div key={`d-${i}`} className="w-1 h-3 rounded-full bg-rose-500 group-hover:shadow-[0_0_6px_rgba(244,63,94,0.4)] transition-all" title="Direct Risk" />
                              ))}
                              {/* Visual Dots for Signals - Industry */}
                              {Array.from({ length: Math.min(signalCounts.industry, 5) }).map((_, i) => (
                                <div key={`i-${i}`} className="w-1 h-2 rounded-full bg-indigo-300 group-hover:bg-indigo-400 transition-colors" title="Industry Risk" />
                              ))}
                            </>
                          )}
                        </div>
                      </div>

                      {/* Action Arrow */}
                      <div className="w-8 h-8 rounded-full border border-slate-100 bg-white flex items-center justify-center text-slate-300 shadow-sm group-hover:border-indigo-100 group-hover:text-indigo-600 group-hover:bg-indigo-50 group-hover:scale-110 transition-all duration-300">
                        <ArrowUpRight className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            );
          })}
        </motion.div>

        {filteredCorporations.length === 0 && (
          <div className="text-center py-20">
            <p className="text-slate-400 text-lg">"{searchQuery}"에 해당하는 기업이 없습니다.</p>
          </div>
        )}

      </div>
    </MainLayout>
  );
}
