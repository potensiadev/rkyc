/**
 * Demo Mode Panel
 * 시연용 수동 분석 실행 기능 (PRD 5.4.2)
 * 8단계 파이프라인 시각화 포함
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import { useAnalyzeJob, useJobStatus, useCorporations } from '@/hooks/useApi';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  Play,
  RefreshCw,
  Clock,
  Database,
  FileText,
  Building2,
  Globe,
  Layers,
  Zap,
  Shield,
  Brain,
  ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

// 8단계 파이프라인 정의
const PIPELINE_STEPS = [
  { id: 'SNAPSHOT', label: '데이터 수집', icon: Database, description: '내부 스냅샷 로드' },
  { id: 'DOC_INGEST', label: '문서 분석', icon: FileText, description: 'KYC 문서 파싱' },
  { id: 'PROFILING', label: '기업 프로파일링', icon: Building2, description: '외부 정보 수집' },
  { id: 'EXTERNAL', label: '외부 검색', icon: Globe, description: '뉴스/공시 수집' },
  { id: 'CONTEXT', label: '컨텍스트 구성', icon: Layers, description: '통합 컨텍스트 생성' },
  { id: 'SIGNAL', label: '시그널 추출', icon: Zap, description: 'rKYC Agent 병렬 분석' },
  { id: 'VALIDATION', label: '검증', icon: Shield, description: 'Cross-Validation' },
  { id: 'INSIGHT', label: '인사이트 생성', icon: Brain, description: 'AI 분석 리포트' },
];

type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

interface PipelineStepProps {
  step: typeof PIPELINE_STEPS[number];
  status: StepStatus;
  isLast: boolean;
}

function PipelineStep({ step, status, isLast }: PipelineStepProps) {
  const Icon = step.icon;

  return (
    <div className={cn("flex items-center", !isLast && "flex-1")}>
      <div className="flex flex-col items-center">
        {/* Step Circle */}
        <div
          className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 relative",
            status === 'completed' && "bg-green-500 text-white shadow-lg shadow-green-200",
            status === 'running' && "bg-amber-500 text-white shadow-lg shadow-amber-200 animate-pulse",
            status === 'pending' && "bg-slate-100 text-slate-400 border-2 border-slate-200",
            status === 'failed' && "bg-red-500 text-white shadow-lg shadow-red-200"
          )}
        >
          {status === 'running' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : status === 'completed' ? (
            <CheckCircle className="w-5 h-5" />
          ) : status === 'failed' ? (
            <AlertCircle className="w-5 h-5" />
          ) : (
            <Icon className="w-5 h-5" />
          )}

          {/* Pulse ring for running state */}
          {status === 'running' && (
            <span className="absolute inset-0 rounded-full bg-amber-400 animate-ping opacity-30" />
          )}
        </div>

        {/* Step Label */}
        <div className="mt-2 text-center w-20">
          <p className={cn(
            "text-xs font-semibold truncate",
            status === 'completed' && "text-green-700",
            status === 'running' && "text-amber-700",
            status === 'pending' && "text-slate-400",
            status === 'failed' && "text-red-700"
          )}>
            {step.label}
          </p>
          <p className={cn(
            "text-[10px] truncate mt-0.5",
            status === 'running' ? "text-amber-600" : "text-slate-400"
          )}>
            {step.description}
          </p>
        </div>
      </div>

      {/* Connector Line */}
      {!isLast && (
        <div className="flex items-center mx-1 -mt-6 flex-1">
          <div
            className={cn(
              "w-full h-0.5 transition-all duration-500",
              status === 'completed' ? "bg-green-400" : "bg-slate-200"
            )}
          />
          <ChevronRight
            className={cn(
              "w-3 h-3 -ml-1",
              status === 'completed' ? "text-green-400" : "text-slate-300"
            )}
          />
        </div>
      )}
    </div>
  );
}

export function DemoPanel() {
  const [selectedCorpId, setSelectedCorpId] = useState<string>('');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const { data: corporations = [] } = useCorporations();
  const analyzeJob = useAnalyzeJob();

  const { data: jobStatus } = useJobStatus(currentJobId || '', {
    enabled: !!currentJobId,
  });

  const isDemoMode = import.meta.env.VITE_DEMO_MODE?.toLowerCase() === 'true' || import.meta.env.DEV;

  // 이전 상태 추적 (중복 새로고침 방지)
  const prevStatusRef = useRef<string | null>(null);

  // 분석 완료 시 자동 새로고침
  useEffect(() => {
    const currentStatus = jobStatus?.status;
    const prevStatus = prevStatusRef.current;

    // DONE으로 변경된 경우에만 자동 새로고침
    if (currentStatus === 'DONE' && prevStatus !== 'DONE' && prevStatus !== null) {
      // 분석 완료된 기업 ID를 sessionStorage에 저장 (시그널 목록에서 우선 표시용)
      if (selectedCorpId) {
        sessionStorage.setItem('lastAnalyzedCorpId', selectedCorpId);
      }
      // 시그널 목록 자동 새로고침
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['signalStats'] });
      // P0: 프로필 캐시도 무효화 (PROFILING 단계 결과 반영)
      queryClient.invalidateQueries({ queryKey: ['corporation', selectedCorpId, 'profile'] });
      queryClient.invalidateQueries({ queryKey: ['corporation', selectedCorpId, 'profile', 'detail'] });
      // Loan Insight도 갱신
      queryClient.invalidateQueries({ queryKey: ['loan-insight', selectedCorpId] });
      toast.success('분석 완료! 시그널 목록이 업데이트되었습니다.');
    }

    prevStatusRef.current = currentStatus || null;
  }, [jobStatus?.status, queryClient]);

  // 각 단계의 상태 계산
  const stepStatuses = useMemo(() => {
    const currentStep = jobStatus?.progress?.step;
    const jobState = jobStatus?.status;

    if (!currentJobId || !jobStatus) {
      return PIPELINE_STEPS.map(() => 'pending' as StepStatus);
    }

    if (jobState === 'DONE') {
      return PIPELINE_STEPS.map(() => 'completed' as StepStatus);
    }

    if (jobState === 'FAILED') {
      const currentIndex = PIPELINE_STEPS.findIndex(s => s.id === currentStep);
      return PIPELINE_STEPS.map((_, i) => {
        if (i < currentIndex) return 'completed' as StepStatus;
        if (i === currentIndex) return 'failed' as StepStatus;
        return 'pending' as StepStatus;
      });
    }

    if (jobState === 'QUEUED') {
      return PIPELINE_STEPS.map(() => 'pending' as StepStatus);
    }

    // RUNNING state
    const currentIndex = PIPELINE_STEPS.findIndex(s => s.id === currentStep);
    return PIPELINE_STEPS.map((_, i) => {
      if (i < currentIndex) return 'completed' as StepStatus;
      if (i === currentIndex) return 'running' as StepStatus;
      return 'pending' as StepStatus;
    });
  }, [jobStatus, currentJobId]);

  // Demo 모드가 아니면 렌더링하지 않음
  if (!isDemoMode) return null;

  const handleRunAnalysis = async () => {
    if (!selectedCorpId) return;

    try {
      const result = await analyzeJob.mutateAsync(selectedCorpId);
      setCurrentJobId(result.job_id);
    } catch (error) {
      console.error('Job trigger failed:', error);
    }
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['signals'] });
    queryClient.invalidateQueries({ queryKey: ['signalStats'] });
    setCurrentJobId(null);
  };

  const getStatusBadge = () => {
    if (!jobStatus) return null;

    switch (jobStatus.status) {
      case 'QUEUED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
            <Clock className="w-3 h-3" />
            대기 중
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
            <Loader2 className="w-3 h-3 animate-spin" />
            분석 중
          </span>
        );
      case 'DONE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <CheckCircle className="w-3 h-3" />
            완료
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
            <AlertCircle className="w-3 h-3" />
            실패
          </span>
        );
    }
  };

  const selectedCorpName = corporations.find(c => c.id === selectedCorpId)?.name;

  return (
    <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-5 mb-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs px-3 py-1 rounded-full font-semibold shadow-sm">
            DEMO MODE
          </span>
          <span className="text-sm font-medium text-amber-800">AI 리스크 분석 파이프라인</span>
        </div>
        {getStatusBadge()}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-5">
        <Select value={selectedCorpId} onValueChange={setSelectedCorpId}>
          <SelectTrigger className="w-[200px] bg-white border-amber-200 focus:ring-amber-500">
            <SelectValue placeholder="기업 선택" />
          </SelectTrigger>
          <SelectContent>
            {corporations.map((corp) => (
              <SelectItem key={corp.id} value={corp.id}>
                {corp.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          onClick={handleRunAnalysis}
          disabled={!selectedCorpId || analyzeJob.isPending || jobStatus?.status === 'RUNNING' || jobStatus?.status === 'QUEUED'}
          className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-md"
        >
          <Play className="w-4 h-4 mr-2" />
          분석 실행
        </Button>

        <Button
          variant="outline"
          onClick={handleRefresh}
          className="border-amber-300 text-amber-700 hover:bg-amber-100"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          새로고침
        </Button>
      </div>

      {/* Pipeline Visualization */}
      {currentJobId && (
        <div className="bg-white rounded-lg border border-amber-100 p-5 shadow-inner">
          {/* Target Corporation */}
          {selectedCorpName && (
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Building2 className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-600">분석 대상:</span>
              <span className="text-sm font-semibold text-slate-800">{selectedCorpName}</span>
            </div>
          )}

          {/* 8-Stage Pipeline */}
          <div className="flex items-start justify-between w-full">
            {PIPELINE_STEPS.map((step, index) => (
              <PipelineStep
                key={step.id}
                step={step}
                status={stepStatuses[index]}
                isLast={index === PIPELINE_STEPS.length - 1}
              />
            ))}
          </div>

          {/* Status Messages */}
          <div className="mt-4 pt-3 border-t border-slate-100">
            {jobStatus?.status === 'DONE' && (
              <div className="flex items-center gap-2 text-green-700 bg-green-50 px-3 py-2 rounded-lg">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm font-medium">
                  분석 완료! 시그널 목록이 자동으로 업데이트되었습니다.
                </span>
              </div>
            )}

            {jobStatus?.status === 'FAILED' && (
              <div className="flex items-center gap-2 text-red-700 bg-red-50 px-3 py-2 rounded-lg">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">
                  분석 실패: {jobStatus.error?.message || '알 수 없는 오류가 발생했습니다.'}
                </span>
              </div>
            )}

            {jobStatus?.status === 'RUNNING' && (
              <div className="flex items-center gap-2 text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm font-medium">
                  {PIPELINE_STEPS.find(s => s.id === jobStatus.progress?.step)?.label || '처리 중'}...
                </span>
                <span className="text-xs text-amber-600 ml-auto">
                  {jobStatus.progress?.percent || 0}%
                </span>
              </div>
            )}

            {jobStatus?.status === 'QUEUED' && (
              <div className="flex items-center gap-2 text-slate-600 bg-slate-50 px-3 py-2 rounded-lg">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">
                  Worker 대기 중... 잠시 후 분석이 시작됩니다.
                </span>
              </div>
            )}
          </div>
        </div>
      )}



      {/* Info Text */}
      <p className="text-[11px] text-amber-600/80 mt-3 text-center">
        * 접속/조회는 분석을 실행하지 않습니다. 위 기능은 시연을 위한 수동 실행입니다.
      </p>
    </div>
  );
}
