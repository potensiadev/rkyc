import { useState, useMemo } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Search, Building2, ChevronRight, AlertCircle, Loader2, BarChart3, TrendingUp } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { useCorporations, useSignals } from "@/hooks/useApi";
import { getCorporationSnapshot, ApiSnapshot } from "@/lib/api";
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

  // 모든 기업의 스냅샷을 병렬로 가져오기
  const snapshotQueries = useQueries({
    queries: corporations.map((corp) => ({
      queryKey: ["snapshot", corp.id],
      queryFn: () => getCorporationSnapshot(corp.id),
      enabled: corporations.length > 0,
      staleTime: 5 * 60 * 1000,
      retry: false,
    })),
  });

  // 스냅샷에서 여신 잔액 맵 생성
  const loanBalanceMap = useMemo(() => {
    const map = new Map<string, number>();
    snapshotQueries.forEach((query, index) => {
      if (query.data) {
        const snapshot = query.data as ApiSnapshot;
        const loanAmount = snapshot.snapshot_json?.credit?.loan_summary?.total_exposure_krw;
        if (loanAmount) {
          map.set(corporations[index]?.id, loanAmount);
        }
      }
    });
    return map;
  }, [snapshotQueries, corporations]);

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
                transition={{ delay: 0.1 + (idx * 0.05) }}
                onClick={() => handleCorporationClick(corp.id, corp.name)}
              >
                <GlassCard className="h-full cursor-pointer hover:bg-white transition-all duration-300 hover:shadow-xl hover:shadow-indigo-500/10 group border-l-4 border-l-transparent hover:border-l-indigo-500">
                  <div className="p-5 flex flex-col h-full">
                    {/* Header */}
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 flex items-center justify-center shadow-inner group-hover:from-indigo-50 group-hover:to-white group-hover:border-indigo-100 transition-colors">
                          <Building2 className="w-6 h-6 text-slate-400 group-hover:text-indigo-500 transition-colors" />
                        </div>
                        <div>
                          <h3 className="font-bold text-slate-800 text-lg leading-tight group-hover:text-indigo-700 transition-colors">{corp.name}</h3>
                          <p className="text-xs text-slate-400 mt-0.5">{corp.industry}</p>
                        </div>
                      </div>
                    </div>

                    {/* Loan Info */}
                    <div className="mb-4 p-3 bg-slate-50 rounded-xl border border-slate-100 group-hover:bg-indigo-50/30 group-hover:border-indigo-100/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">총 여신 잔액</span>
                        <span className="font-mono font-bold text-slate-700">{formatLoanBalance(loanBalance)}</span>
                      </div>
                    </div>

                    {/* Footer (Signals) */}
                    <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between">
                      <div className="flex gap-1.5 flex-wrap">
                        {signalCounts.total === 0 ? (
                          <span className="text-xs text-slate-400 italic">활성 시그널 없음</span>
                        ) : (
                          <>
                            {signalCounts.direct > 0 && (
                              <Tag className="text-[10px] py-0.5 h-5 bg-indigo-50 text-indigo-600 border-indigo-100">
                                직접 {signalCounts.direct}
                              </Tag>
                            )}
                            {signalCounts.industry > 0 && (
                              <Tag className="text-[10px] py-0.5 h-5 bg-cyan-50 text-cyan-600 border-cyan-100">
                                산업 {signalCounts.industry}
                              </Tag>
                            )}
                          </>
                        )}
                      </div>
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-slate-300 group-hover:text-indigo-500 group-hover:bg-indigo-50 transition-all">
                        <ChevronRight className="w-5 h-5" />
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
