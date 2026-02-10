import { useParams, useNavigate, useLocation } from "react-router-dom";
import { DynamicBackground, GlassCard, StatusBadge, Tag, Sparkline } from "@/components/premium";
import { MainLayout } from "@/components/layout/MainLayout";
// Mock data imports removed
import {
  formatDate,
  getBankTransactionTypeLabel,
} from "@/data/signals";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import {
  ArrowLeft,
  Building2,
  Landmark,
  Users,
  Loader2,
  FileDown,
  RefreshCw,
  Globe,
  Factory,
  TrendingUp,
  Package,
  Shield,
  ExternalLink,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronDown,
  ChevronUp,
  FileText,
  Target,
  Zap,
  Search,
  FileWarning,
  Command,
  Sparkles,
  Share2,
  Download,
  CornerDownRight,
  ChevronRight,
  Brain,
  CheckCircle2,
  BrainCircuit,
  Clock,
  TrendingDown,
  DollarSign,
  Activity,
  MapPin,
  CreditCard,
  ArrowUpRight,
  ShieldCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { useState, useEffect, useMemo, useCallback } from "react";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import { useCorporation, useSignals, useCorporationSnapshot, useCorpProfile, useCorpProfileDetail, useRefreshCorpProfile, useJobStatus, useLoanInsight, useBankingData, useBankingInsights, useDartFinancials } from "@/hooks/useApi";
import { BankingPulseDashboard } from "@/components/dashboard/BankingPulseDashboard";
import { toast } from "sonner";
import type { ProfileConfidence, CorpProfile } from "@/types/profile";
import { useQueryClient } from "@tanstack/react-query";
import { getCorporationReport } from "@/lib/api";
import { EvidenceBackedField } from "@/components/profile/EvidenceBackedField";
import { EvidenceMap } from "@/components/profile/EvidenceMap";
import { RiskIndicators } from "@/components/profile/RiskIndicators";
import { DrillDownSheet } from "@/components/dashboard/DrillDownSheet";
import { motion, AnimatePresence } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, LineChart, Line, BarChart, Bar, LabelList } from "recharts";

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

// Job 진행 단계 정의 (파이프라인 순서)
const JOB_STEPS = [
  { step: 'QUEUED', label: '대기 중', progress: 0 },
  { step: 'SNAPSHOT', label: '데이터 수집', progress: 10 },
  { step: 'DOC_INGEST', label: '문서 분석', progress: 20 },
  { step: 'PROFILING', label: '기업 프로파일링', progress: 35 },
  { step: 'EXTERNAL', label: '외부 정보 검색', progress: 50 },
  { step: 'CONTEXT', label: '컨텍스트 구성', progress: 60 },
  { step: 'SIGNAL', label: '시그널 추출', progress: 75 },
  { step: 'VALIDATION', label: '검증 중', progress: 85 },
  { step: 'INDEX', label: '인덱싱', progress: 90 },
  { step: 'INSIGHT', label: '인사이트 생성', progress: 95 },
  { step: 'DONE', label: '완료', progress: 100 },
];

function getJobProgress(currentStep: string | undefined): { progress: number; label: string } {
  if (!currentStep) return { progress: 5, label: '시작 중...' };
  const found = JOB_STEPS.find(s => s.step === currentStep);
  return found ? { progress: found.progress, label: found.label } : { progress: 5, label: currentStep };
}

// Confidence 배지 색상 헬퍼
function getConfidenceBadge(confidence: ProfileConfidence | undefined): { bg: string; text: string; label: string } {
  const map: Record<ProfileConfidence, { bg: string; text: string; label: string }> = {
    HIGH: { bg: 'bg-green-100', text: 'text-green-700', label: '신뢰도 높음' },
    MED: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '신뢰도 중간' },
    LOW: { bg: 'bg-orange-100', text: 'text-orange-700', label: '신뢰도 낮음' },
    NONE: { bg: 'bg-gray-100', text: 'text-gray-500', label: '데이터 없음' },
    CACHED: { bg: 'bg-blue-100', text: 'text-blue-700', label: '캐시 데이터' },
    STALE: { bg: 'bg-red-100', text: 'text-red-700', label: '만료됨' },
  };
  return map[confidence || 'NONE'] || map.NONE;
}

// 금액 포맷팅 헬퍼
function formatKRW(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조원`;
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(0)}억원`;
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(0)}만원`;
  return `${value.toLocaleString()}원`;
}

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

const TOC_ITEMS = [
  { id: "summary", label: "Executive Summary" },
  { id: "profile", label: "Corporate Profile" },
  { id: "dart-financials", label: "DART 재무제표" },
  { id: "banking", label: "Banking Data" },
  { id: "financials", label: "Bank Relationship" },
  { id: "intelligence", label: "Intelligence & Flow" },
];

export default function CorporateDetailPage() {
  const { corpId } = useParams();
  const navigate = useNavigate();
  // Navigation state로부터 이름 전달받기 (목록 페이지 등에서 넘겨줌)
  const location = useLocation();
  const stateCorpName = location.state?.corpName;
  const searchParams = new URLSearchParams(location.search);
  const paramCorpName = searchParams.get("name");

  // 로딩 중 표시할 이름 (없으면 ID)
  const displayCorpName = stateCorpName || paramCorpName || corpId;

  const queryClient = useQueryClient();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [refreshStatus, setRefreshStatus] = useState<'idle' | 'running' | 'done' | 'failed' | 'timeout'>('idle');

  // API 훅 사용
  const { data: corporation, isLoading: isLoadingCorp } = useCorporation(corpId || "");
  const { data: apiSignals, isLoading: isLoadingSignals } = useSignals({ corp_id: corpId });
  const { data: snapshot, isLoading: isLoadingSnapshot } = useCorporationSnapshot(corpId || "");
  const { data: profile, isLoading: isLoadingProfile, error: profileError, refetch: refetchProfile } = useCorpProfile(corpId || "");
  // 상세 프로필 (field_provenance 포함) - 기본 뷰 / 상세 뷰 토글용
  // P1-3 Fix: Add error handling for profileDetail
  const { data: profileDetail, error: profileDetailError, refetch: refetchProfileDetail } = useCorpProfileDetail(corpId || "");
  // Loan Insight (사전 생성된 AI 분석)
  const { data: loanInsightData, isLoading: isLoadingLoanInsight, error: loanInsightError } = useLoanInsight(corpId || "");
  const loanInsight = loanInsightData?.insight || null;
  // Banking Data (PRD v1.1)
  const { data: bankingData, isLoading: isLoadingBankingData } = useBankingData(corpId || "");
  // Banking Insights (Rule-based 교차 분석)
  const { data: bankingInsights, isLoading: isLoadingBankingInsights } = useBankingInsights(corpId || "");
  // DART 재무제표 (100% Fact)
  const { data: dartFinancials, isLoading: isLoadingDartFinancials } = useDartFinancials(corporation?.name || "");
  // Banking Data Drill Down State
  const [drillDownConfig, setDrillDownConfig] = useState<{ isOpen: boolean; title: string; data: any } | null>(null);

  const handleDrillDown = (title: string, data: any) => {
    setDrillDownConfig({
      isOpen: true,
      title,
      data
    });
  };
  const refreshProfile = useRefreshCorpProfile();
  const [showDetailedView, setShowDetailedView] = useState(false);
  const [autoRefreshTriggered, setAutoRefreshTriggered] = useState(false);

  const activeSection = useScrollSpy(TOC_ITEMS.map(i => i.id));

  // =========================================================================
  // P0 Auto Pre-warming: 비활성화됨
  // - 시연 시 Demo Panel에서 수동으로 분석 실행
  // - Corporate Detail Page 진입 시 자동 분석 하지 않음
  // =========================================================================
  // useEffect(() => {
  //   // 이미 갱신 트리거됨 또는 로딩 중이면 스킵
  //   if (autoRefreshTriggered || isLoadingProfile || !corpId) return;

  //   // 현재 갱신 중이면 스킵
  //   if (refreshStatus === 'running') return;

  //   // 프로필 갱신 필요 조건 체크
  //   const needsRefresh = () => {
  //     // 1. 프로필이 없으면 갱신 필요
  //     if (!profile) return true;

  //     // 2. expires_at이 과거이면 갱신 필요
  //     if (profile.expiresAt) {
  //       const expiresAt = new Date(profile.expiresAt);
  //       if (expiresAt < new Date()) return true;
  //     }

  //     // 3. confidence가 STALE이면 갱신 필요
  //     if (profile.profileConfidence === 'STALE') return true;

  //     // 4. is_fallback이 true이면 갱신 권장 (더 나은 데이터 시도)
  //     if (profile.isFallback) return true;

  //     return false;
  //   };

  //   if (needsRefresh()) {
  //     setAutoRefreshTriggered(true);

  //     // 백그라운드 갱신 시작
  //     refreshProfile.mutate(corpId, {
  //       onSuccess: (job) => {
  //         if (job?.job_id) {
  //           setRefreshJobId(job.job_id);
  //           setRefreshStatus('running');
  //           toast.info("프로필 자동 갱신 중", {
  //             description: "최신 정보를 가져오고 있습니다...",
  //             duration: 3000,
  //           });
  //         }
  //       },
  //       onError: () => {
  //         // 자동 갱신 실패는 조용히 처리 (사용자 경험 방해 X)
  //         console.warn("[Auto Pre-warming] Profile refresh failed");
  //       },
  //     });
  //   }
  // }, [corpId, profile, isLoadingProfile, refreshStatus, autoRefreshTriggered, refreshProfile]);

  // 보고서 데이터 프리페칭 (hover 시 미리 로드)
  const prefetchReport = () => {
    if (corpId) {
      queryClient.prefetchQuery({
        queryKey: ['report', corpId],
        queryFn: () => getCorporationReport(corpId),
        staleTime: 10 * 60 * 1000, // 10분
      });
    }
  };

  // Job 타임아웃 핸들러
  const handleJobTimeout = useCallback(() => {
    setRefreshStatus('timeout');
    setRefreshJobId(null);
    toast.error("작업 시간 초과", {
      description: "분석 작업이 2분을 초과했습니다. 잠시 후 다시 시도해주세요.",
    });
  }, []);

  // Job 상태 폴링
  const { data: jobStatus } = useJobStatus(refreshJobId || '', {
    enabled: !!refreshJobId && refreshStatus === 'running',
    onTimeout: handleJobTimeout,
  });

  // Job 완료 시 프로필 + Loan Insight 다시 로드
  useEffect(() => {
    if (jobStatus?.status === 'DONE') {
      setRefreshStatus('done');
      setRefreshJobId(null);
      // 프로필 쿼리 무효화하여 다시 로드 (기본 + 상세)
      queryClient.invalidateQueries({ queryKey: ['corporation', corpId, 'profile'] });
      queryClient.invalidateQueries({ queryKey: ['corporation', corpId, 'profile', 'detail'] });
      // Loan Insight도 갱신
      queryClient.invalidateQueries({ queryKey: ['loan-insight', corpId] });
      toast.success("분석 완료", {
        description: "기업 정보가 성공적으로 갱신되었습니다.",
      });
    } else if (jobStatus?.status === 'FAILED') {
      setRefreshStatus('failed');
      setRefreshJobId(null);
      toast.error("분석 실패", {
        description: "기업 정보 갱신 중 오류가 발생했습니다.",
      });
    }
  }, [jobStatus?.status, queryClient, corpId]);

  // 정보 갱신 버튼 핸들러
  const handleRefreshProfile = async () => {
    if (!corpId) return;
    setRefreshStatus('running');
    toast.info("분석 시작", {
      description: "기업 정보 갱신을 시작합니다...",
    });

    try {
      const result = await refreshProfile.mutateAsync(corpId);
      if (result.status === 'QUEUED' && result.job_id) {
        setRefreshJobId(result.job_id);
      } else if (result.status === 'FAILED') {
        setRefreshStatus('failed');
        toast.error("분석 실패", {
          description: "기업 정보 갱신에 실패했습니다. 잠시 후 다시 시도해주세요.",
        });
      }
    } catch (error) {
      console.error('Profile refresh failed:', error);
      setRefreshStatus('failed');
      toast.error("분석 실패", {
        description: error instanceof Error ? error.message : "네트워크 오류가 발생했습니다.",
      });
    }
  };

  // 통합 로딩 상태 계산
  const loadingState = useMemo(() => {
    const states = [
      { name: '기업 정보', loading: isLoadingCorp, done: !!corporation },
      { name: '시그널', loading: isLoadingSignals, done: !!apiSignals },
      { name: '스냅샷', loading: isLoadingSnapshot, done: !!snapshot },
      { name: 'AI 분석', loading: isLoadingLoanInsight, done: !!loanInsight },
    ];
    const loadingItems = states.filter(s => s.loading);
    const doneCount = states.filter(s => s.done).length;
    const progress = Math.round((doneCount / states.length) * 100);
    return {
      isInitialLoading: isLoadingCorp,
      loadingItems,
      progress,
      currentItem: loadingItems[0]?.name || '완료',
    };
  }, [isLoadingCorp, isLoadingSignals, isLoadingSnapshot, isLoadingLoanInsight, corporation, apiSignals, snapshot, loanInsight]);

  // 초기 로딩 상태 (기업 정보)
  if (loadingState.isInitialLoading) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="h-[calc(100vh-100px)] flex items-center justify-center relative z-10 px-4">
          <GlassCard className="p-12 w-full max-w-[520px] flex flex-col items-center gap-10 border-t-4 border-t-indigo-500 shadow-2xl backdrop-blur-2xl">

            {/* Icon & Title */}
            <div className="flex flex-col items-center gap-6 text-center">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-500/30 blur-2xl rounded-full scale-150" />
                <div className="relative bg-white/80 backdrop-blur-sm p-5 rounded-2xl shadow-xl border border-white/50 ring-1 ring-indigo-50">
                  <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                </div>
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">rKYC 엔진 분석중</h2>
                <p className="text-slate-500 text-lg font-medium">
                  <span className="font-semibold text-indigo-600">{displayCorpName}</span>의 데이터를 심층 분석하고 있습니다.
                </p>
              </div>
            </div>

            {/* Progress Section */}
            <div className="w-full space-y-4">
              <div className="flex justify-between items-end px-1">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                  <span className="text-sm font-semibold text-slate-700">
                    {loadingState.currentItem}
                  </span>
                </div>
                <span className="text-sm font-bold text-indigo-600 font-mono tracking-wider">
                  {loadingState.progress}%
                </span>
              </div>

              <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden shadow-inner ring-1 ring-slate-200/50">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-indigo-400 rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                  style={{ width: `${loadingState.progress}%` }}
                >
                  <div className="absolute inset-0 w-full h-full bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.5)_50%,transparent_100%)] animate-[shimmer_1.5s_infinite]" />
                </div>
              </div>

              <p className="text-xs text-center text-slate-400 mt-4 leading-relaxed">
                글로벌 뉴스, 재무 데이터, 공급망 리스크 등<br />수천 개의 데이터 포인트를 실시간으로 교차 검증 중입니다.
              </p>
            </div>
          </GlassCard>
        </div>
      </MainLayout>
    );
  }

  if (!corporation) {
    return (
      <MainLayout>
        <div className="text-center py-16">
          <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">기업 정보를 찾을 수 없습니다.</p>
          <Button variant="outline" onClick={() => navigate(-1)} className="mt-4">
            돌아가기
          </Button>
        </div>
      </MainLayout>
    );
  }

  // API 시그널 카운트
  const signalCounts = apiSignals ? {
    direct: apiSignals.filter(s => s.signalCategory === 'direct').length,
    industry: apiSignals.filter(s => s.signalCategory === 'industry').length,
    environment: apiSignals.filter(s => s.signalCategory === 'environment').length,
  } : { direct: 0, industry: 0, environment: 0 };

  // Calculate Internal Risk Score for display (Example: 72 if High, 50 if Med, 20 if Low)
  const riskScore = snapshot?.snapshot_json?.corp?.kyc_status?.internal_risk_grade === 'HIGH' ? 85 :
    snapshot?.snapshot_json?.corp?.kyc_status?.internal_risk_grade === 'MED' ? 55 : 25;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-32 relative selection:bg-indigo-100 selection:text-indigo-900 group/page">
      <DynamicBackground />
      <StickyCommandBar />
      {/* Navbar */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-white/20 px-6 py-3 shadow-sm"
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-slate-100 rounded-full text-slate-500" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900">{corporation.name}</h1>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-500">{corporation.industryCode}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden md:flex relative group">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input type="text" placeholder="Search..." className="h-8 pl-9 pr-4 rounded-full bg-slate-50 border border-transparent text-xs focus:bg-white focus:border-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-100/50 transition-all w-48" />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-300 font-mono group-hover:text-slate-400">/</span>
            </div>
            <div className="h-4 w-px bg-slate-200 mx-2" />

            <Button variant="outline" size="sm"
              className="h-8 w-8 p-0 rounded-full border-slate-200 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50"
              onClick={handleRefreshProfile}
              disabled={refreshProfile.isPending || isLoadingProfile || refreshStatus === 'running'}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${(refreshProfile.isPending || refreshStatus === 'running') ? 'animate-spin' : ''}`} />
            </Button>


            <Button variant="outline" size="sm"
              className="h-8 w-8 p-0 rounded-full border-slate-200 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50"
              onClick={() => setShowPreviewModal(true)}
              onMouseEnter={prefetchReport}
              onFocus={prefetchReport}
            >
              <Download className="w-3.5 h-3.5" />
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
              <GlassCard className="md:col-span-3 p-8" id="summary-card">
                <div className="flex justify-between items-start mb-6">
                  <h3 className="text-lg font-bold text-slate-900">Executive Summary</h3>

                </div>
                <div className="text-[14px] leading-relaxed text-slate-600 mb-6 bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                  {loanInsight?.executive_summary ? (
                    <ul className="space-y-2">
                      {loanInsight.executive_summary
                        .split(/\n|•/)
                        .map(line => line.trim())
                        .filter(line => line.length > 0 && !line.startsWith('['))
                        .map((line, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                            <span>{line}</span>
                          </li>
                        ))}
                    </ul>
                  ) : (
                    <ul className="space-y-2">
                      <li className="flex items-start gap-2">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                        <span><strong className="text-slate-900 font-semibold">{corporation.name}</strong>은(는) {corporation.industry} 분야에서 사업을 영위하는 기업</span>
                      </li>
                      {corporation.headquarters && (
                        <li className="flex items-start gap-2">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                          <span>본사: {corporation.headquarters}</span>
                        </li>
                      )}
                      {bankingData && (
                        <li className="flex items-start gap-2">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                          <span>당행 거래: 여신 {((bankingData.loan_exposure as any)?.total_exposure_krw / 100000000).toFixed(0)}억, 수신 {((bankingData.deposit_trend as any)?.current_balance / 100000000).toFixed(0)}억</span>
                        </li>
                      )}
                    </ul>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Tag className="gap-2">
                    <IconZaps className="w-3 h-3 text-slate-400" />
                    Signals: Direct {signalCounts.direct} / Ind {signalCounts.industry} / Env {signalCounts.environment}
                  </Tag>
                  {profile?.country_exposure && Object.keys(profile.country_exposure).length > 0 && (
                    <Tag className="gap-2">
                      <Globe className="w-3 h-3 text-slate-400" />
                      Global Exposure: Extensive
                    </Tag>
                  )}
                </div>
              </GlassCard>


            </div>

            {/* 2. Corporate Profile Grid */}
            <div id="profile">
              <GlassCard className="p-8">
                <SectionHeader icon={IconBuilding} title="Corporate Profile" />
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                  <DataField label="CEO" value={corporation.ceo} isHighlighted />
                  <DataField label="Established" value={corporation.foundedYear > 0 ? `${corporation.foundedYear}년` : (corporation.establishedDate ? `${corporation.establishedDate.substring(0, 4)}년` : '-')} />
                  <DataField label="Biz Type" value={corporation.bizType || '-'} />
                  <DataField label="Industry" value={corporation.industryCode} />
                  <div className="lg:col-span-2">
                    <DataField label="Headquarters" value={corporation.headquarters || corporation.address} />
                  </div>
                  <DataField label="Tax Code" value={corporation.businessNumber || '-'} />
                  <DataField label="Corp Code" value={corporation.corpRegNo || corporation.jurirNo || '-'} />
                </div>

                {/* DART 공시 기반 정보 */}
                {(corporation.dartCorpCode || corporation.corpNameEng || corporation.accMt || corporation.homepageUrl) && (
                  <div className="mt-6 pt-6 border-t border-slate-100">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">DART 공시 정보</span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-green-100 text-green-700">100% Fact</span>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-sm">
                      {corporation.dartCorpCode && (
                        <DataField label="DART Code" value={corporation.dartCorpCode} />
                      )}
                      {corporation.corpNameEng && (
                        <div className="lg:col-span-2">
                          <DataField label="English Name" value={corporation.corpNameEng} />
                        </div>
                      )}
                      {corporation.accMt && (
                        <DataField label="Fiscal Month" value={`${corporation.accMt}월 결산`} />
                      )}
                      {corporation.homepageUrl && (
                        <div className="lg:col-span-2">
                          <div className="flex flex-col gap-1.5">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Homepage</span>
                            <a href={corporation.homepageUrl} target="_blank" rel="noopener noreferrer" className="text-[13px] text-indigo-600 hover:underline truncate flex items-center gap-1">
                              {corporation.homepageUrl.replace(/^https?:\/\//, '')}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Detail Grid: Competitors, Macro, Shareholders, Global Sites */}
                <div className="mt-6 pt-6 border-t border-slate-100">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                    {/* Left: Competitors & Macro */}
                    <div className="space-y-6">
                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Competitors</h5>
                        <div className="space-y-3">
                          {profile?.competitors?.slice(0, 3).map(c => (
                            <div key={c.name} className="flex justify-between items-center bg-white p-3 rounded-xl border border-slate-100 shadow-sm">
                              <div>
                                <div className="text-xs font-bold text-slate-800">{c.name}</div>
                              </div>
                            </div>
                          ))}
                          {(!profile?.competitors || profile.competitors.length === 0) && (
                            <div className="text-xs text-slate-400 italic">No Data</div>
                          )}
                        </div>
                      </div>

                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Macro Factors</h5>
                        <div className="flex flex-wrap gap-2">
                          {profile?.macro_factors?.map(f => (
                            <StatusBadge
                              key={f.factor}
                              variant={f.impact === 'POSITIVE' ? 'success' : f.impact === 'NEGATIVE' ? 'danger' : 'neutral'}
                              className="bg-white border-opacity-50"
                            >
                              {f.factor}
                            </StatusBadge>
                          ))}
                          {(!profile?.macro_factors || profile.macro_factors.length === 0) && (
                            <div className="text-xs text-slate-400 italic">No Data</div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right: Shareholders & Global Sites */}
                    <div className="space-y-6">
                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 h-full">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Shareholders</h5>
                        <table className="w-full text-xs text-left">
                          <tbody>
                            {profile?.shareholders?.slice(0, 5).map((s) => (
                              <tr key={s.name} className="border-b border-slate-100 last:border-0 hover:bg-white/50 transition-colors">
                                <td className="py-2 text-slate-600 font-medium pl-2">{s.name}</td>
                                <td className="py-2 text-slate-800 font-mono text-right pr-2">{s.ownership_pct || s.ratio_pct}%</td>
                              </tr>
                            ))}
                            {(!profile?.shareholders || profile.shareholders.length === 0) && (
                              <tr><td colSpan={2} className="text-xs text-slate-400 italic py-2 text-center">No Data</td></tr>
                            )}
                          </tbody>
                        </table>

                        <div className="mt-8 pt-6 border-t border-slate-200">
                          <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Global Sites</h5>
                          <div className="flex flex-wrap gap-2">
                            {profile?.overseas_business?.subsidiaries?.slice(0, 3).map(s => (
                              <div key={s.name} className="flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 rounded-md shadow-sm">
                                <Globe className="w-3 h-3 text-indigo-400" />
                                <span className="text-[10px] font-medium text-slate-700">{s.name} ({s.country})</span>
                              </div>
                            ))}
                            {(!profile?.overseas_business?.subsidiaries || profile.overseas_business.subsidiaries.length === 0) && (
                              <div className="text-xs text-slate-400 italic">No Data</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              </GlassCard>
            </div>
            

            {/* 2.5 DART Financial Statements (100% Fact) */}
            <div id="dart-financials">
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <SectionHeader icon={FileText} title="DART 재무제표" subtitle="100% Fact - DART 전자공시" />
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-1 rounded text-[10px] font-mono bg-green-100 text-green-700 border border-green-200">
                      <ShieldCheck className="w-3 h-3 inline mr-1" />
                      DART 공시
                    </span>
                  </div>
                </div>

                {isLoadingDartFinancials ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                    <span className="ml-2 text-slate-500">DART 재무제표를 불러오는 중...</span>
                  </div>
                ) : dartFinancials?.found && dartFinancials.financial_statements.length > 0 ? (
                  <div className="space-y-6">
                    {/* Financial Summary Cards */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      {(() => {
                        const latest = dartFinancials.financial_statements[0];
                        const prev = dartFinancials.financial_statements[1];

                        const calcChange = (curr: number | null, prev: number | null) => {
                          if (!curr || !prev || prev === 0) return null;
                          return ((curr - prev) / Math.abs(prev) * 100);
                        };

                        const revenueChange = calcChange(latest?.revenue, prev?.revenue);
                        const opChange = calcChange(latest?.operating_profit, prev?.operating_profit);
                        const netChange = calcChange(latest?.net_income, prev?.net_income);
                        const assetChange = calcChange(latest?.total_assets, prev?.total_assets);

                        return (
                          <>
                            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100">
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">매출액</p>
                              <p className="text-xl font-bold text-slate-900 font-mono">{formatKRW(latest?.revenue)}</p>
                              {revenueChange !== null && (
                                <p className={`text-[11px] font-medium font-mono flex items-center gap-0.5 mt-1 ${revenueChange >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                  {revenueChange >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {revenueChange >= 0 ? '+' : ''}{revenueChange.toFixed(1)}% YoY
                                </p>
                              )}
                            </div>
                            <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-xl p-4 border border-emerald-100">
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">영업이익</p>
                              <p className={`text-xl font-bold font-mono ${(latest?.operating_profit ?? 0) >= 0 ? 'text-slate-900' : 'text-rose-600'}`}>
                                {formatKRW(latest?.operating_profit)}
                              </p>
                              {opChange !== null && (
                                <p className={`text-[11px] font-medium font-mono flex items-center gap-0.5 mt-1 ${opChange >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                  {opChange >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {opChange >= 0 ? '+' : ''}{opChange.toFixed(1)}% YoY
                                </p>
                              )}
                            </div>
                            <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-4 border border-violet-100">
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">당기순이익</p>
                              <p className={`text-xl font-bold font-mono ${(latest?.net_income ?? 0) >= 0 ? 'text-slate-900' : 'text-rose-600'}`}>
                                {formatKRW(latest?.net_income)}
                              </p>
                              {netChange !== null && (
                                <p className={`text-[11px] font-medium font-mono flex items-center gap-0.5 mt-1 ${netChange >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                  {netChange >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {netChange >= 0 ? '+' : ''}{netChange.toFixed(1)}% YoY
                                </p>
                              )}
                            </div>
                            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-100">
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">자산총계</p>
                              <p className="text-xl font-bold text-slate-900 font-mono">{formatKRW(latest?.total_assets)}</p>
                              {assetChange !== null && (
                                <p className={`text-[11px] font-medium font-mono flex items-center gap-0.5 mt-1 ${assetChange >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                  {assetChange >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {assetChange >= 0 ? '+' : ''}{assetChange.toFixed(1)}% YoY
                                </p>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>

                    {/* Yearly Trend Chart */}
                    <div className="bg-slate-50/50 rounded-xl p-5 border border-slate-200">
                      <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-4">연도별 손익 추이</p>
                      <div className="h-[200px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={[...dartFinancials.financial_statements].reverse().map(stmt => ({
                              year: stmt.bsns_year,
                              revenue: stmt.revenue ? stmt.revenue / 100000000 : 0,
                              operating_profit: stmt.operating_profit ? stmt.operating_profit / 100000000 : 0,
                              net_income: stmt.net_income ? stmt.net_income / 100000000 : 0,
                            }))}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                            <XAxis dataKey="year" tick={{ fontSize: 12, fontWeight: 600 }} tickLine={false} axisLine={{ stroke: '#cbd5e1' }} />
                            <YAxis tick={{ fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} tickFormatter={(val) => `${val}억`} width={50} />
                            <Tooltip
                              contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 25px rgba(0,0,0,0.1)', fontSize: '12px', fontFamily: 'monospace' }}
                              formatter={(value: number, name: string) => {
                                const labels: Record<string, string> = { revenue: '매출액', operating_profit: '영업이익', net_income: '당기순이익' };
                                return [`${value.toFixed(1)}억원`, labels[name] || name];
                              }}
                              labelFormatter={(label) => `${label}년`}
                            />
                            <Legend formatter={(value) => {
                              const labels: Record<string, string> = { revenue: '매출액', operating_profit: '영업이익', net_income: '당기순이익' };
                              return labels[value] || value;
                            }} />
                            <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="operating_profit" fill="#10b981" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="net_income" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Balance Sheet Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* 재무상태표 */}
                      <div className="bg-slate-50/50 rounded-xl p-5 border border-slate-200">
                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-4">재무상태표 (최신연도)</p>
                        {(() => {
                          const latest = dartFinancials.financial_statements[0];
                          return (
                            <div className="space-y-3">
                              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                <span className="text-sm text-slate-600">자산총계</span>
                                <span className="text-sm font-bold font-mono text-slate-900">{formatKRW(latest?.total_assets)}</span>
                              </div>
                              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                <span className="text-sm text-slate-600">부채총계</span>
                                <span className="text-sm font-bold font-mono text-rose-600">{formatKRW(latest?.total_liabilities)}</span>
                              </div>
                              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                <span className="text-sm text-slate-600">자본총계</span>
                                <span className="text-sm font-bold font-mono text-emerald-600">{formatKRW(latest?.total_equity)}</span>
                              </div>
                              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                <span className="text-sm text-slate-600">이익잉여금</span>
                                <span className={`text-sm font-bold font-mono ${(latest?.retained_earnings ?? 0) >= 0 ? 'text-indigo-600' : 'text-rose-600'}`}>
                                  {formatKRW(latest?.retained_earnings)}
                                </span>
                              </div>
                              <div className="flex justify-between items-center py-2 bg-slate-100 rounded-lg px-3 -mx-1">
                                <span className="text-sm font-semibold text-slate-700">부채비율</span>
                                <span className={`text-sm font-bold font-mono ${(latest?.debt_ratio ?? 0) > 200 ? 'text-rose-600' : (latest?.debt_ratio ?? 0) > 100 ? 'text-amber-600' : 'text-emerald-600'}`}>
                                  {latest?.debt_ratio?.toFixed(1) || '-'}%
                                </span>
                              </div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* 연도별 상세 테이블 */}
                      <div className="bg-slate-50/50 rounded-xl p-5 border border-slate-200">
                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-4">연도별 상세 (단위: 억원)</p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-200">
                                <th className="py-2 text-left text-slate-500 font-semibold">연도</th>
                                {dartFinancials.financial_statements.map(stmt => (
                                  <th key={stmt.bsns_year} className="py-2 text-right text-slate-700 font-bold font-mono">{stmt.bsns_year}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-slate-100">
                                <td className="py-2 text-slate-600">매출액</td>
                                {dartFinancials.financial_statements.map(stmt => (
                                  <td key={stmt.bsns_year} className="py-2 text-right font-mono text-slate-800">
                                    {stmt.revenue ? (stmt.revenue / 100000000).toFixed(0) : '-'}
                                  </td>
                                ))}
                              </tr>
                              <tr className="border-b border-slate-100">
                                <td className="py-2 text-slate-600">영업이익</td>
                                {dartFinancials.financial_statements.map(stmt => (
                                  <td key={stmt.bsns_year} className={`py-2 text-right font-mono ${(stmt.operating_profit ?? 0) < 0 ? 'text-rose-600' : 'text-slate-800'}`}>
                                    {stmt.operating_profit ? (stmt.operating_profit / 100000000).toFixed(0) : '-'}
                                  </td>
                                ))}
                              </tr>
                              <tr className="border-b border-slate-100">
                                <td className="py-2 text-slate-600">순이익</td>
                                {dartFinancials.financial_statements.map(stmt => (
                                  <td key={stmt.bsns_year} className={`py-2 text-right font-mono ${(stmt.net_income ?? 0) < 0 ? 'text-rose-600' : 'text-slate-800'}`}>
                                    {stmt.net_income ? (stmt.net_income / 100000000).toFixed(0) : '-'}
                                  </td>
                                ))}
                              </tr>
                              <tr className="border-b border-slate-100">
                                <td className="py-2 text-slate-600">부채비율</td>
                                {dartFinancials.financial_statements.map(stmt => (
                                  <td key={stmt.bsns_year} className={`py-2 text-right font-mono ${(stmt.debt_ratio ?? 0) > 200 ? 'text-rose-600' : 'text-slate-800'}`}>
                                    {stmt.debt_ratio?.toFixed(0) || '-'}%
                                  </td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>

                    {/* Source Attribution */}
                    <div className="flex items-center justify-end gap-2 text-[10px] text-slate-400 pt-2">
                      <ShieldCheck className="w-3 h-3 text-green-500" />
                      <span>출처: DART 전자공시시스템 (금융감독원)</span>
                      <span className="text-slate-300">|</span>
                      <span>신뢰도: HIGH (100% Fact)</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p className="font-medium">DART 재무제표를 찾을 수 없습니다.</p>
                    <p className="text-xs mt-2">{dartFinancials?.message || "비상장 기업이거나 DART에 등록되지 않은 기업입니다."}</p>
                  </div>
                )}
              </GlassCard>
            </div>

            {/* 2.6 Banking Data Section (PRD v1.1) - Visual Update */}
            <div id="banking">
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <SectionHeader icon={IconBank} title="은행 내부 데이터 (Banking Data)" subtitle="여신, 수신, 담보 및 무역금융 종합 분석" />
                  <div className="flex gap-2">
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" /> 기준일: {bankingData?.data_date || new Date().toISOString().split('T')[0]}
                    </span>
                  </div>
                </div>

                {isLoadingBankingData ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                    <span className="ml-2 text-slate-500">은행 데이터를 불러오는 중...</span>
                  </div>
                ) : bankingData ? (
                  <div className="space-y-6">

                    {/* Banking Insights - Rule-based 교차 분석 */}
                    {bankingInsights && (bankingInsights.total_risk_count > 0 || bankingInsights.total_opportunity_count > 0) && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Risk Insights */}
                        {bankingInsights.risk_insights.length > 0 && (
                          <div className="bg-gradient-to-br from-rose-50 to-orange-50 rounded-xl p-5 border border-rose-200">
                            <h4 className="text-sm font-bold text-rose-800 mb-3 flex items-center gap-2">
                              <AlertTriangle className="w-4 h-4" />
                              리스크 관리 필요 ({bankingInsights.total_risk_count})
                            </h4>
                            <div className="space-y-3">
                              {bankingInsights.risk_insights.slice(0, 3).map((insight, idx) => (
                                <div key={idx} className="bg-white/70 rounded-lg p-3 border border-rose-100">
                                  <div className="flex items-start gap-2">
                                    <span className={`shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold ${insight.priority === 'HIGH' ? 'bg-rose-600 text-white' :
                                      insight.priority === 'MED' ? 'bg-orange-500 text-white' :
                                        'bg-amber-400 text-amber-900'
                                      }`}>
                                      {insight.priority}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-semibold text-slate-800">{insight.title}</p>
                                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">{insight.description}</p>
                                      {insight.related_signal_titles.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-1">
                                          {insight.related_signal_titles.slice(0, 2).map((title, i) => (
                                            <span key={i} className="text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-700 rounded">
                                              {title.length > 30 ? title.slice(0, 30) + '...' : title}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Opportunity Insights */}
                        {bankingInsights.opportunity_insights.length > 0 && (
                          <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-5 border border-emerald-200">
                            <h4 className="text-sm font-bold text-emerald-800 mb-3 flex items-center gap-2">
                              <TrendingUp className="w-4 h-4" />
                              영업 기회 포착 ({bankingInsights.total_opportunity_count})
                            </h4>
                            <div className="space-y-3">
                              {bankingInsights.opportunity_insights.slice(0, 3).map((insight, idx) => (
                                <div key={idx} className="bg-white/70 rounded-lg p-3 border border-emerald-100">
                                  <div className="flex items-start gap-2">
                                    <span className={`shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold ${insight.priority === 'HIGH' ? 'bg-emerald-600 text-white' :
                                      insight.priority === 'MED' ? 'bg-teal-500 text-white' :
                                        'bg-cyan-400 text-cyan-900'
                                      }`}>
                                      {insight.priority}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-semibold text-slate-800">{insight.title}</p>
                                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">{insight.description}</p>
                                      {insight.related_signal_titles.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-1">
                                          {insight.related_signal_titles.slice(0, 2).map((title, i) => (
                                            <span key={i} className="text-[10px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded">
                                              {title.length > 30 ? title.slice(0, 30) + '...' : title}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Main Dashboard Grid - High Density */}
                    <BankingPulseDashboard bankingData={bankingData} className="w-full" />

                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <IconBank className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p>은행 데이터가 없습니다.</p>
                  </div>
                )}
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
                          <span className="text-3xl font-mono font-bold text-slate-900">
                            {(bankingData?.loan_exposure as any)?.total_exposure_krw
                              ? `${((bankingData.loan_exposure as any).total_exposure_krw / 100000000).toFixed(0)}`
                              : snapshot?.snapshot_json?.credit?.loan_summary?.total_exposure_krw
                                ? `${(snapshot.snapshot_json.credit.loan_summary.total_exposure_krw / 100000000).toFixed(0)}`
                                : "0"}
                          </span>
                          <span className="text-sm font-medium text-slate-500">억원</span>
                        </div>
                      </div>
                    </div>
                    <div className="h-12 w-full">
                      {/* Placeholder sparkline data */}
                      <Sparkline data={[10, 11, 10, 12, 12, 12]} color="#6366f1" />
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
                          <span className="text-3xl font-mono font-bold text-slate-900">
                            {(bankingData?.deposit_trend as any)?.current_balance
                              ? `${((bankingData.deposit_trend as any).current_balance / 100000000).toFixed(0)}`
                              : "0"}
                          </span>
                          <span className="text-sm font-medium text-slate-500">억원</span>
                        </div>
                      </div>
                    </div>
                    <div className="h-12 w-full">
                      <Sparkline
                        data={((bankingData?.deposit_trend as any)?.monthly_balance || []).slice(-6).map((m: any) => m.balance / 100000000)}
                        color="#10b981"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 pt-6 border-t border-slate-100">
                  <DataField label="Collateral" value={
                    snapshot?.snapshot_json?.collateral?.has_collateral
                      ? snapshot.snapshot_json.collateral.collateral_types?.join(", ") || "Yes"
                      : "None"
                  } />
                  <DataField label="FX Service" value={corporation.bankRelationship.fxTransactions || "-"} />
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">KYC Status</span>
                    <StatusBadge variant={snapshot?.snapshot_json?.corp?.kyc_status?.is_kyc_completed ? "success" : "neutral"}>
                      {snapshot?.snapshot_json?.corp?.kyc_status?.is_kyc_completed ? "Completed" : "Pending"}
                    </StatusBadge>
                  </div>
                </div>
              </GlassCard>
            </div>

            {/* 4. Intelligence & Flow */}
            <div id="intelligence">
              <GlassCard className="p-8 space-y-8" id="value-chain-map">
                <div className="flex items-center justify-between">
                  <SectionHeader icon={IconLayer} title="Deep Intelligence" subtitle="Full Analysis" />
                  <Button variant="outline" size="sm" className="h-7 text-[10px] uppercase font-bold text-slate-500 border-slate-200">Export Report</Button>
                </div>

                {/* Business Overview - Enhanced */}
                <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 space-y-6">
                  <h4 className="text-xs font-bold text-slate-800 mb-3 flex items-center gap-2">
                    <span className="w-1 h-4 bg-indigo-500 rounded-full" /> Business Overview
                  </h4>

                  {/* 1. 사업 요약 */}
                  <div>
                    <p className="text-[13px] leading-relaxed text-slate-600 text-justify">
                      {profile?.business_summary || profile?.business_model || "No business overview available."}
                    </p>
                  </div>

                  {/* 2. 산업 현황 & 비즈니스 모델 Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* 산업 현황 */}
                    {profile?.industry_overview && (
                      <div className="bg-white rounded-xl p-4 border border-slate-100">
                        <div className="flex items-center gap-2 mb-2">
                          <Factory className="w-4 h-4 text-indigo-500" />
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Industry Position</span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {profile.industry_overview}
                        </p>
                      </div>
                    )}

                    {/* 비즈니스 모델 */}
                    {profile?.business_model && (
                      <div className="bg-white rounded-xl p-4 border border-slate-100">
                        <div className="flex items-center gap-2 mb-2">
                          <Target className="w-4 h-4 text-emerald-500" />
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Business Model</span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {profile.business_model}
                        </p>
                        {/* B2B/B2C 추론 태그 */}
                        <div className="mt-2 flex gap-1">
                          {profile.key_customers && profile.key_customers.length > 0 && (
                            <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-blue-50 text-blue-600 border border-blue-100">
                              B2B
                            </span>
                          )}
                          {profile.export_ratio_pct && profile.export_ratio_pct > 30 && (
                            <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-purple-50 text-purple-600 border border-purple-100">
                              수출 {profile.export_ratio_pct}%
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 3. 경쟁 구도 */}
                  {profile?.competitors && profile.competitors.length > 0 && (
                    <div className="bg-white rounded-xl p-4 border border-slate-100">
                      <div className="flex items-center gap-2 mb-3">
                        <Users className="w-4 h-4 text-amber-500" />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Competitive Landscape</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {profile.competitors.slice(0, 5).map((c, idx) => (
                          <div
                            key={c.name}
                            className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-2 ${
                              idx === 0 ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-slate-50 border-slate-200 text-slate-600'
                            }`}
                          >
                            {idx === 0 && <span className="text-[9px]">🥇</span>}
                            {idx === 1 && <span className="text-[9px]">🥈</span>}
                            {idx === 2 && <span className="text-[9px]">🥉</span>}
                            {c.name}
                            {c.market_share_pct && (
                              <span className="text-[9px] text-slate-400">({c.market_share_pct}%)</span>
                            )}
                          </div>
                        ))}
                      </div>
                      <p className="mt-2 text-[10px] text-slate-400">
                        * 시장 내 주요 경쟁사 (순서는 시장점유율 순이 아닐 수 있음)
                      </p>
                    </div>
                  )}

                  {/* 4. 핵심 강점 추론 (기존 데이터 기반) */}
                  <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap className="w-4 h-4 text-indigo-500" />
                      <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">Inferred Strengths</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {/* 수출 비중 기반 */}
                      {profile?.export_ratio_pct && profile.export_ratio_pct >= 50 && (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white border border-indigo-200 text-indigo-700">
                          🌏 글로벌 경쟁력 (수출 {profile.export_ratio_pct}%)
                        </span>
                      )}
                      {/* 고객사 기반 */}
                      {profile?.key_customers && profile.key_customers.some(c =>
                        c.toLowerCase().includes('삼성') || c.toLowerCase().includes('samsung') ||
                        c.toLowerCase().includes('sk') || c.toLowerCase().includes('lg')
                      ) && (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white border border-emerald-200 text-emerald-700">
                          🏢 대기업 공급망 진입
                        </span>
                      )}
                      {/* 공급사 다변화 기반 */}
                      {profile?.supply_chain?.supplier_countries && Object.keys(profile.supply_chain.supplier_countries).length >= 3 && (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white border border-blue-200 text-blue-700">
                          ⛓️ 공급망 다변화
                        </span>
                      )}
                      {/* 해외 법인 기반 */}
                      {profile?.overseas_business?.subsidiaries && profile.overseas_business.subsidiaries.length > 0 && (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white border border-purple-200 text-purple-700">
                          🏭 해외 생산기지 보유
                        </span>
                      )}
                      {/* 업력 기반 */}
                      {profile?.founded_year && (new Date().getFullYear() - profile.founded_year) >= 20 && (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-white border border-amber-200 text-amber-700">
                          ⏳ {new Date().getFullYear() - profile.founded_year}년 업력
                        </span>
                      )}
                      {/* 데이터 없을 때 */}
                      {!profile?.export_ratio_pct && !profile?.key_customers?.length && !profile?.supply_chain?.supplier_countries && (
                        <span className="text-xs text-slate-400 italic">추론할 데이터가 부족합니다</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Value Chain Flow */}
                <div className="relative flex items-center justify-between gap-4 px-4 py-8 bg-white/50 rounded-3xl border border-dotted border-slate-200 overflow-x-auto">
                  <div className="absolute top-1/2 left-10 right-10 h-0.5 bg-slate-200 -z-10" />

                  {/* Suppliers Section */}
                  <div className="flex flex-col gap-3 min-w-[120px]">
                    <span className="text-[10px] font-bold text-slate-400 uppercase text-center mb-1">Suppliers</span>
                    {profile?.supply_chain?.key_suppliers?.slice(0, 3).map(s => (
                      <div key={s} className="bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm text-xs font-medium text-slate-600 text-center">
                        {s}
                      </div>
                    ))}
                    {(!profile?.supply_chain?.key_suppliers || profile.supply_chain.key_suppliers.length === 0) && (
                      <div className="text-xs text-slate-400 text-center italic">No Data</div>
                    )}
                  </div>

                  <div className="flex items-center text-slate-300"><ChevronRight className="w-5 h-5" /><ChevronRight className="w-5 h-5" /></div>

                  {/* Center Core */}
                  <div className="relative px-4">
                    <div className="absolute -inset-4 bg-indigo-100/50 rounded-full blur-xl animate-pulse" />
                    <div className="relative bg-white p-6 rounded-2xl border-2 border-indigo-100 shadow-xl flex flex-col items-center gap-2 w-48">
                      <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                        <IconTarget className="w-5 h-5" />
                      </div>
                      <span className="text-sm font-bold text-slate-900 text-center leading-tight">{corporation.name}</span>
                      {/* Materials */}
                      <div className="flex flex-wrap justify-center gap-1 mt-2">
                        {profile?.key_materials?.slice(0, 3).map(m => (
                          <span key={m} className="text-[9px] px-1.5 py-0.5 rounded border bg-slate-50 text-slate-500 border-slate-100">{m}</span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center text-slate-300"><ChevronRight className="w-5 h-5" /><ChevronRight className="w-5 h-5" /></div>

                  {/* Customers */}
                  <div className="grid grid-cols-1 gap-2 min-w-[120px]">
                    <span className="text-[10px] font-bold text-slate-400 uppercase text-center mb-1">Customers</span>
                    {profile?.key_customers?.slice(0, 3).map(c => (
                      <div key={c} className="bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm text-xs font-medium text-slate-600 text-center flex items-center justify-center h-full">
                        {c}
                      </div>
                    ))}
                    {(!profile?.key_customers || profile.key_customers.length === 0) && (
                      <div className="text-xs text-slate-400 text-center italic">No Data</div>
                    )}
                  </div>
                </div>

                <div className="space-y-8 mt-6">
                  {/* AI Risk Opinion (Loan Insight) - Full Width */}
                  {/* 시그널이 있을 때만 Loan Insight 표시 */}
                  {apiSignals && apiSignals.length > 0 && (
                  <GlassCard id="loan-insight" className="overflow-hidden border-indigo-100 shadow-xl shadow-indigo-50/40">
                    {/* Header Section */}
                    <div className="px-8 py-6 border-b border-slate-100 bg-white/60 backdrop-blur-sm flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-50 text-slate-700 border border-slate-100">
                          <Brain className="w-4 h-4" />
                        </div>
                        <h2 className="text-lg font-bold text-slate-900 tracking-tight">AI Analysis</h2>
                        <div className="flex items-center gap-2">
                          <span className="w-1 h-1 rounded-full bg-slate-300" />
                          <span className="text-xs text-slate-400 font-medium">Risk/Opportunity</span>
                        </div>
                      </div>
                      {loanInsight && (
                        <div className={`px-4 py-2 rounded-xl border flex flex-col items-center justify-center min-w-[100px] ${loanInsight.stance.level === 'CAUTION' ? 'bg-rose-50 border-rose-100' :
                          loanInsight.stance.level === 'MONITORING' ? 'bg-amber-50 border-amber-100' :
                            loanInsight.stance.level === 'POSITIVE' ? 'bg-emerald-50 border-emerald-100' :
                              'bg-slate-50 border-slate-100'
                          }`}>
                          <span className={`text-[10px] uppercase font-bold tracking-wider mb-0.5 ${loanInsight.stance.level === 'CAUTION' ? 'text-rose-400' :
                            loanInsight.stance.level === 'MONITORING' ? 'text-amber-400' :
                              loanInsight.stance.level === 'POSITIVE' ? 'text-emerald-400' :
                                'text-slate-400'
                            }`}>Outlook</span>
                          <span className={`text-sm font-bold ${loanInsight.stance.level === 'CAUTION' ? 'text-rose-700' :
                            loanInsight.stance.level === 'MONITORING' ? 'text-amber-700' :
                              loanInsight.stance.level === 'POSITIVE' ? 'text-emerald-700' :
                                'text-slate-700'
                            }`}>{loanInsight.stance.label}</span>
                        </div>
                      )}
                    </div>

                    <div className="p-8 space-y-8 bg-white/40">

                      {/* Main Analysis Container */}
                      <div className="bg-slate-50 rounded-2xl border border-slate-200 p-6 space-y-8">
                        {/* Risk & Opportunity Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative">
                          {/* Vertical Divider for Desktop */}
                          <div className="hidden md:block absolute top-0 bottom-0 left-1/2 w-px bg-slate-200 -ml-px"></div>

                          {/* Risks - PRD v1.0 */}
                          <div className="bg-rose-50/0 rounded-xl relative">
                            <h4 className="flex items-center gap-2.5 text-base font-bold text-rose-700 mb-5">
                              <div className="p-1.5 bg-rose-100 rounded-lg">
                                <AlertTriangle className="w-4 h-4 text-rose-600" />
                              </div>
                              외부 리스크 요소
                            </h4>
                            <ul className="space-y-4">
                              {loanInsight?.key_risks?.map((risk, i: number) => {
                                // PRD v1.0: 구조화된 객체 또는 기존 string 호환
                                const isStructured = typeof risk === 'object' && risk !== null;
                                const text = isStructured ? (risk as any).text : String(risk);
                                const priority = isStructured ? (risk as any).priority : i + 1;
                                const sourceSignalId = isStructured ? (risk as any).source_signal_id : null;

                                return (
                                  <li key={i} className="flex gap-3 text-[14px] text-slate-700 leading-relaxed group">
                                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-rose-100 text-rose-600 text-[10px] font-bold shrink-0 mt-0.5">
                                      {priority}
                                    </span>
                                    <div className="flex-1">
                                      <span className="group-hover:text-slate-900 transition-colors">{text}</span>
                                      {sourceSignalId && (
                                        <button
                                          onClick={() => navigate(`/signals/${sourceSignalId}`)}
                                          className="ml-2 text-xs text-rose-500 hover:text-rose-700 hover:underline inline-flex items-center gap-1"
                                        >
                                          시그널 보기 →
                                        </button>
                                      )}
                                    </div>
                                  </li>
                                );
                              }) || <li className="text-sm text-slate-400 italic pl-4">식별된 주요 리스크가 없습니다.</li>}
                            </ul>
                          </div>

                          {/* Opportunities - PRD v1.0 */}
                          <div className="bg-emerald-50/0 rounded-xl">
                            <h4 className="flex items-center gap-2.5 text-base font-bold text-emerald-700 mb-5">
                              <div className="p-1.5 bg-emerald-100 rounded-lg">
                                <TrendingUp className="w-4 h-4 text-emerald-600" />
                              </div>
                              외부 기회 요소
                            </h4>
                            <ul className="space-y-4">
                              {loanInsight?.key_opportunities?.map((opp, i: number) => {
                                // PRD v1.0: 구조화된 객체 또는 기존 string 호환
                                const isStructured = typeof opp === 'object' && opp !== null;
                                const text = isStructured ? (opp as any).text : String(opp);
                                const priority = isStructured ? (opp as any).priority : i + 1;
                                const sourceSignalId = isStructured ? (opp as any).source_signal_id : null;

                                return (
                                  <li key={i} className="flex gap-3 text-[14px] text-slate-700 leading-relaxed group">
                                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 text-[10px] font-bold shrink-0 mt-0.5">
                                      {priority}
                                    </span>
                                    <div className="flex-1">
                                      <span className="group-hover:text-slate-900 transition-colors">{text}</span>
                                      {sourceSignalId && (
                                        <button
                                          onClick={() => navigate(`/signals/${sourceSignalId}`)}
                                          className="ml-2 text-xs text-emerald-500 hover:text-emerald-700 hover:underline inline-flex items-center gap-1"
                                        >
                                          시그널 보기 →
                                        </button>
                                      )}
                                    </div>
                                  </li>
                                );
                              }) || <li className="text-sm text-slate-400 italic pl-4">식별된 주요 기회 요인이 없습니다.</li>}
                            </ul>
                          </div>
                        </div>

                        {/* Mitigating Factors (if any) */}
                        {loanInsight?.mitigating_factors && loanInsight.mitigating_factors.length > 0 && (
                          <div>
                            <div className="h-px bg-slate-200 w-full mb-6"></div>
                            <h4 className="flex items-center gap-2.5 text-sm font-bold text-blue-700 mb-4">
                              <div className="p-1 bg-blue-100 rounded-md">
                                <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                              </div>
                              리스크 상쇄 요인
                            </h4>
                            <ul className="grid grid-cols-1 gap-3">
                              {loanInsight.mitigating_factors.map((factor: string, i: number) => (
                                <li key={i} className="flex items-start gap-3 text-[14px] text-slate-600 bg-white border border-slate-200/60 rounded-lg p-3 shadow-sm">
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                                  {factor}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Detected Signals by Type */}
                        {apiSignals && apiSignals.length > 0 && (
                          <div>
                            <div className="h-px bg-slate-200 w-full mb-6"></div>
                            <h4 className="flex items-center gap-2.5 text-sm font-bold text-slate-700 mb-4">
                              <div className="p-1 bg-slate-100 rounded-md">
                                <Activity className="w-3.5 h-3.5 text-slate-600" />
                              </div>
                              탐지된 시그널 ({apiSignals.length}건)
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              {/* DIRECT Signals */}
                              <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 rounded-xl p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <div className="w-2 h-2 rounded-full bg-indigo-500" />
                                  <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider">DIRECT</span>
                                  <span className="ml-auto text-[10px] font-mono text-indigo-500 bg-indigo-100 px-1.5 py-0.5 rounded">
                                    {apiSignals.filter(s => s.signalCategory === 'direct').length}
                                  </span>
                                </div>
                                <ul className="space-y-2">
                                  {apiSignals.filter(s => s.signalCategory === 'direct').slice(0, 3).map((signal, i) => (
                                    <li key={i} className="text-[12px] text-slate-600 flex items-start gap-2">
                                      <span className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${signal.impact === 'risk' ? 'bg-rose-400' : signal.impact === 'opportunity' ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                                      <span className="line-clamp-2">{signal.title || signal.summary?.slice(0, 50)}</span>
                                    </li>
                                  ))}
                                  {apiSignals.filter(s => s.signalCategory === 'direct').length === 0 && (
                                    <li className="text-[11px] text-slate-400 italic">탐지된 시그널 없음</li>
                                  )}
                                </ul>
                              </div>

                              {/* INDUSTRY Signals */}
                              <div className="bg-gradient-to-br from-violet-50 to-white border border-violet-100 rounded-xl p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <div className="w-2 h-2 rounded-full bg-violet-500" />
                                  <span className="text-xs font-bold text-violet-700 uppercase tracking-wider">INDUSTRY</span>
                                  <span className="ml-auto text-[10px] font-mono text-violet-500 bg-violet-100 px-1.5 py-0.5 rounded">
                                    {apiSignals.filter(s => s.signalCategory === 'industry').length}
                                  </span>
                                </div>
                                <ul className="space-y-2">
                                  {apiSignals.filter(s => s.signalCategory === 'industry').slice(0, 3).map((signal, i) => (
                                    <li key={i} className="text-[12px] text-slate-600 flex items-start gap-2">
                                      <span className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${signal.impact === 'risk' ? 'bg-rose-400' : signal.impact === 'opportunity' ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                                      <span className="line-clamp-2">{signal.title || signal.summary?.slice(0, 50)}</span>
                                    </li>
                                  ))}
                                  {apiSignals.filter(s => s.signalCategory === 'industry').length === 0 && (
                                    <li className="text-[11px] text-slate-400 italic">탐지된 시그널 없음</li>
                                  )}
                                </ul>
                              </div>

                              {/* ENVIRONMENT Signals */}
                              <div className="bg-gradient-to-br from-teal-50 to-white border border-teal-100 rounded-xl p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <div className="w-2 h-2 rounded-full bg-teal-500" />
                                  <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">ENVIRONMENT</span>
                                  <span className="ml-auto text-[10px] font-mono text-teal-500 bg-teal-100 px-1.5 py-0.5 rounded">
                                    {apiSignals.filter(s => s.signalCategory === 'environment').length}
                                  </span>
                                </div>
                                <ul className="space-y-2">
                                  {apiSignals.filter(s => s.signalCategory === 'environment').slice(0, 3).map((signal, i) => (
                                    <li key={i} className="text-[12px] text-slate-600 flex items-start gap-2">
                                      <span className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${signal.impact === 'risk' ? 'bg-rose-400' : signal.impact === 'opportunity' ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                                      <span className="line-clamp-2">{signal.title || signal.summary?.slice(0, 50)}</span>
                                    </li>
                                  ))}
                                  {apiSignals.filter(s => s.signalCategory === 'environment').length === 0 && (
                                    <li className="text-[11px] text-slate-400 italic">탐지된 시그널 없음</li>
                                  )}
                                </ul>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Metadata Footer */}
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-6 text-[11px] text-slate-400 font-medium border-t border-slate-100">
                        <div className="flex flex-wrap gap-x-4 gap-y-1">
                          <span className="flex items-center gap-1.5">
                            <BrainCircuit className="w-3 h-3 text-slate-300" />
                            Model: <span className="text-slate-600 font-mono">{loanInsight?.generation_model || 'RKYC-Standard-v2'}</span>
                          </span>
                          <span>Generated: {loanInsight?.generated_at ? new Date(loanInsight.generated_at).toLocaleDateString() : '-'}</span>
                        </div>
                        <div className="text-right">
                          * 본 분석은 AI 모델이 생성한 참고 자료이며, 은행의 공식 심사 의견을 대체하지 않습니다.
                        </div>
                      </div>

                    </div>
                  </GlassCard>
                  )}

                  {/* Detail Grid: Competitors, Macro, Shareholders */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                    {/* Left: Competitors & Macro */}
                    <div className="space-y-6">
                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Competitors</h5>
                        <div className="space-y-3">
                          {profile?.competitors?.slice(0, 3).map(c => (
                            <div key={c.name} className="flex justify-between items-center bg-white p-3 rounded-xl border border-slate-100 shadow-sm">
                              <div>
                                <div className="text-xs font-bold text-slate-800">{c.name}</div>
                              </div>
                            </div>
                          ))}
                          {(!profile?.competitors || profile.competitors.length === 0) && (
                            <div className="text-xs text-slate-400 italic">No Data</div>
                          )}
                        </div>
                      </div>

                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Macro Factors</h5>
                        <div className="flex flex-wrap gap-2">
                          {profile?.macro_factors?.map(f => (
                            <StatusBadge
                              key={f.factor}
                              variant={f.impact === 'POSITIVE' ? 'success' : f.impact === 'NEGATIVE' ? 'danger' : 'neutral'}
                              className="bg-white border-opacity-50"
                            >
                              {f.factor}
                            </StatusBadge>
                          ))}
                          {(!profile?.macro_factors || profile.macro_factors.length === 0) && (
                            <div className="text-xs text-slate-400 italic">No Data</div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right: Shareholders & Global Sites */}
                    <div className="space-y-6">
                      <div className="bg-slate-50/50 rounded-2xl p-6 border border-slate-100 h-full">
                        <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Shareholders</h5>
                        <table className="w-full text-xs text-left">
                          <tbody>
                            {profile?.shareholders?.slice(0, 5).map((s, i) => (
                              <tr key={s.name} className="border-b border-slate-100 last:border-0 hover:bg-white/50 transition-colors">
                                <td className="py-2 text-slate-600 font-medium pl-2">{s.name}</td>
                                <td className="py-2 text-slate-800 font-mono text-right pr-2">{s.ownership_pct}%</td>
                              </tr>
                            ))}
                            {(!profile?.shareholders || profile.shareholders.length === 0) && (
                              <tr><td colSpan={2} className="text-xs text-slate-400 italic py-2 text-center">No Data</td></tr>
                            )}
                          </tbody>
                        </table>

                        <div className="mt-8 pt-6 border-t border-slate-200">
                          <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Global Sites</h5>
                          <div className="flex flex-wrap gap-2">
                            {profile?.overseas_business?.subsidiaries?.slice(0, 3).map(s => (
                              <div key={s.name} className="flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 rounded-md shadow-sm">
                                <Globe className="w-3 h-3 text-indigo-400" />
                                <span className="text-[10px] font-medium text-slate-700">{s.name} ({s.country})</span>
                              </div>
                            ))}
                            {(!profile?.overseas_business?.subsidiaries || profile.overseas_business.subsidiaries.length === 0) && (
                              <div className="text-xs text-slate-400 italic">No Data</div>
                            )}
                          </div>
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
            </div>
          </div>

        </div>
      </main>

      <ReportPreviewModal
        open={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        corporationId={corporation.id}
      />
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
