import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { useNewKycJobStatus } from "@/hooks/useApi";
import { Loader2, Check, Clock, AlertCircle, FileText, Search, Brain, FileCheck } from "lucide-react";
import {
  DynamicBackground,
  GlassCard,
  StatusBadge
} from "@/components/premium";
import { motion } from "framer-motion";

// 분석 단계 정의
const ANALYSIS_STEPS = [
  { key: 'DOC_INGEST', label: '서류 파싱', icon: FileText, description: '제출 서류 분석 중' },
  { key: 'PROFILING', label: '외부 정보 수집', icon: Search, description: '뉴스, 공시, 업종 동향 검색 중' },
  { key: 'SIGNAL', label: '리스크/기회 분석', icon: Brain, description: 'AI가 시그널 추출 중' },
  { key: 'INSIGHT', label: '리포트 생성', icon: FileCheck, description: '종합 분석 리포트 작성 중' },
];

export default function NewKycAnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // Job 상태 폴링
  const { data: jobStatus, isLoading, error } = useNewKycJobStatus(jobId || '');

  // 완료 시 리포트 페이지로 이동
  useEffect(() => {
    if (jobStatus?.status === 'DONE') {
      // 약간의 딜레이 후 이동 (사용자가 완료 상태를 볼 수 있도록)
      const timer = setTimeout(() => {
        navigate(`/new-kyc/report/${jobId}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [jobStatus?.status, jobId, navigate]);

  // 현재 단계 인덱스 계산
  const getCurrentStepIndex = () => {
    if (!jobStatus?.progress?.step) return 0;
    const idx = ANALYSIS_STEPS.findIndex(s => s.key === jobStatus.progress.step);
    return idx >= 0 ? idx : 0;
  };

  const currentStepIndex = getCurrentStepIndex();
  const progressPercent = jobStatus?.progress?.percent || ((currentStepIndex + 1) / ANALYSIS_STEPS.length) * 100;

  // 에러 상태
  if (error || jobStatus?.status === 'FAILED') {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="h-[calc(100vh-100px)] flex items-center justify-center relative z-10">
          <GlassCard className="max-w-md w-full p-8 text-center flex flex-col items-center">
            <div className="w-16 h-16 rounded-full bg-rose-50 flex items-center justify-center mb-4 ring-8 ring-rose-50/50">
              <AlertCircle className="w-8 h-8 text-rose-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-800 mb-2">Analysis Failed</h1>
            <p className="text-slate-500 mb-6 leading-relaxed">
              {jobStatus?.error?.message || "An error occurred during the analysis process."}
            </p>
            <button
              onClick={() => navigate('/new-kyc')}
              className="text-indigo-600 hover:text-indigo-700 font-medium hover:underline transition-all"
            >
              Try Again
            </button>
          </GlassCard>
        </div>
      </MainLayout>
    );
  }

  // 로딩 상태 (초기)
  if (isLoading && !jobStatus) {
    return (
      <MainLayout>
        <DynamicBackground />
        <div className="h-[calc(100vh-100px)] flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
            <p className="text-slate-500 font-medium animate-pulse">Initializing Analysis...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="max-w-2xl mx-auto py-12 relative z-10 px-6">
        {/* 헤더 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="w-20 h-20 rounded-full bg-white/50 backdrop-blur-sm shadow-sm flex items-center justify-center mx-auto mb-6 ring-4 ring-white/30">
            {jobStatus?.status === 'DONE' ? (
              <Check className="w-10 h-10 text-emerald-500" />
            ) : (
              <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
            )}
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2 tracking-tight">
            {jobStatus?.status === 'DONE' ? 'Analysis Complete' : 'AI Analysis In Progress'}
          </h1>
          <p className="text-lg text-slate-600 font-medium">
            {jobStatus?.corp_name && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(jobStatus.corp_name)
              ? jobStatus.corp_name
              : "Target Corporation"}
          </p>
        </motion.div>

        {/* 진행률 바 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <GlassCard className="p-6">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Progress</span>
              <span className="text-lg font-bold text-indigo-600">{Math.round(progressPercent)}%</span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden shadow-inner">
              <motion.div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </GlassCard>
        </motion.div>

        {/* 단계별 상태 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <GlassCard className="p-2">
            <div className="space-y-1">
              {ANALYSIS_STEPS.map((step, index) => {
                const isCompleted = index < currentStepIndex || jobStatus?.status === 'DONE';
                const isCurrent = index === currentStepIndex && jobStatus?.status !== 'DONE';
                const isPending = index > currentStepIndex && jobStatus?.status !== 'DONE';

                return (
                  <motion.div
                    key={step.key}
                    initial={false}
                    animate={{
                      backgroundColor: isCurrent ? "rgba(79, 70, 229, 0.05)" : "rgba(255, 255, 255, 0)",
                    }}
                    className={`
                      flex items-center gap-4 p-4 rounded-xl transition-all
                      ${isCurrent ? 'border border-indigo-100 shadow-sm' : 'border border-transparent'}
                    `}
                  >
                    {/* 아이콘 */}
                    <div className={`
                      w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors duration-300
                      ${isCompleted
                        ? 'bg-emerald-500 text-white shadow-md shadow-emerald-200'
                        : isCurrent
                          ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200'
                          : 'bg-slate-100 text-slate-400'
                      }
                    `}>
                      {isCompleted ? (
                        <Check className="w-5 h-5" />
                      ) : isCurrent ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <step.icon className="w-5 h-5" />
                      )}
                    </div>

                    {/* 텍스트 */}
                    <div className="flex-1 min-w-0">
                      <div className={`
                        font-semibold text-sm mb-0.5
                        ${isCompleted
                          ? 'text-foreground'
                          : isCurrent
                            ? 'text-indigo-900'
                            : 'text-slate-400'
                        }
                      `}>
                        {step.label}
                      </div>
                      <div className="text-xs text-slate-500">
                        {step.description}
                      </div>
                    </div>

                    {/* 상태 표시 */}
                    {isCompleted && (
                      <StatusBadge variant="success" className="h-6 text-xs">Completed</StatusBadge>
                    )}
                    {isCurrent && (
                      <StatusBadge variant="brand" className="h-6 text-xs animate-pulse">Processing</StatusBadge>
                    )}
                    {isPending && (
                      <span className="text-xs text-slate-300 font-medium px-2">Pending</span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>
        </motion.div>

        {/* 안내 메시지 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center mt-8"
        >
          {jobStatus?.status === 'DONE' ? (
            <p className="text-sm font-medium text-emerald-600 flex items-center justify-center gap-2">
              <Check className="w-4 h-4" />
              Analysis complete. Redirecting to report...
            </p>
          ) : (
            <p className="text-sm text-slate-400">
              You will be automatically redirected once the analysis is complete.
            </p>
          )}
        </motion.div>
      </div>
    </MainLayout>
  );
}
