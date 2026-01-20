/**
 * 신규 법인 KYC 분석 - 분석 진행 상태 페이지
 */

import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { useNewKycJobStatus } from "@/hooks/useApi";
import { Loader2, Check, Clock, AlertCircle, FileText, Search, Brain, FileCheck } from "lucide-react";

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
        <div className="max-w-2xl mx-auto text-center py-16">
          <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-950/30 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-foreground mb-2">분석 실패</h1>
          <p className="text-muted-foreground mb-6">
            {jobStatus?.error?.message || "분석 중 오류가 발생했습니다."}
          </p>
          <button
            onClick={() => navigate('/new-kyc')}
            className="text-primary hover:underline"
          >
            다시 시도하기
          </button>
        </div>
      </MainLayout>
    );
  }

  // 로딩 상태
  if (isLoading && !jobStatus) {
    return (
      <MainLayout>
        <div className="max-w-2xl mx-auto text-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">분석 상태를 불러오는 중...</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            {jobStatus?.status === 'DONE' ? (
              <Check className="w-8 h-8 text-green-500" />
            ) : (
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            {jobStatus?.status === 'DONE' ? 'AI 분석 완료' : 'AI 분석 진행 중'}
          </h1>
          {jobStatus?.corp_name && (
            <p className="text-lg text-foreground">{jobStatus.corp_name}</p>
          )}
        </div>

        {/* 진행률 바 */}
        <div className="bg-card rounded-lg border p-6 mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-muted-foreground">분석 단계</span>
            <span className="text-sm font-medium">{Math.round(progressPercent)}%</span>
          </div>
          <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* 단계별 상태 */}
        <div className="bg-card rounded-lg border p-6">
          <div className="space-y-4">
            {ANALYSIS_STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex || jobStatus?.status === 'DONE';
              const isCurrent = index === currentStepIndex && jobStatus?.status !== 'DONE';
              const isPending = index > currentStepIndex && jobStatus?.status !== 'DONE';

              return (
                <div
                  key={step.key}
                  className={`
                    flex items-center gap-4 p-3 rounded-lg transition-colors
                    ${isCurrent ? 'bg-primary/5' : ''}
                  `}
                >
                  {/* 아이콘 */}
                  <div className={`
                    w-10 h-10 rounded-full flex items-center justify-center shrink-0
                    ${isCompleted
                      ? 'bg-green-500 text-white'
                      : isCurrent
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                    }
                  `}>
                    {isCompleted ? (
                      <Check className="w-5 h-5" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Clock className="w-5 h-5" />
                    )}
                  </div>

                  {/* 텍스트 */}
                  <div className="flex-1 min-w-0">
                    <div className={`
                      font-medium
                      ${isCompleted
                        ? 'text-green-600 dark:text-green-400'
                        : isCurrent
                          ? 'text-foreground'
                          : 'text-muted-foreground'
                      }
                    `}>
                      {isCompleted ? `${step.label} 완료` : isCurrent ? `${step.label} 중...` : step.label}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {step.description}
                    </div>
                  </div>

                  {/* 상태 표시 */}
                  {isCompleted && (
                    <span className="text-xs text-green-600 dark:text-green-400">완료</span>
                  )}
                  {isCurrent && (
                    <span className="text-xs text-primary">진행중</span>
                  )}
                  {isPending && (
                    <span className="text-xs text-muted-foreground">대기</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* 안내 메시지 */}
        <div className="text-center mt-6">
          {jobStatus?.status === 'DONE' ? (
            <p className="text-sm text-green-600 dark:text-green-400">
              분석이 완료되었습니다. 리포트 페이지로 이동합니다...
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              분석이 완료되면 자동으로 리포트 페이지로 이동합니다.
            </p>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
