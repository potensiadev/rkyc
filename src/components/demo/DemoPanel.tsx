/**
 * Demo Mode Panel
 * 시연용 수동 분석 실행 기능 (PRD 5.4.2)
 */

import { useState } from 'react';
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
import { Progress } from '@/components/ui/progress';
import { AlertCircle, CheckCircle, Loader2, Play, RefreshCw } from 'lucide-react';

export function DemoPanel() {
  const [selectedCorpId, setSelectedCorpId] = useState<string>('');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const { data: corporations = [] } = useCorporations();
  const analyzeJob = useAnalyzeJob();
  const { data: jobStatus } = useJobStatus(currentJobId || '', {
    enabled: !!currentJobId,
  });

  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

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

  const getStatusIcon = () => {
    if (!jobStatus) return null;

    switch (jobStatus.status) {
      case 'QUEUED':
      case 'RUNNING':
        return <Loader2 className="w-4 h-4 animate-spin text-amber-600" />;
      case 'DONE':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'FAILED':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
    }
  };

  const getStatusText = () => {
    if (!jobStatus) return '';

    switch (jobStatus.status) {
      case 'QUEUED':
        return '대기 중...';
      case 'RUNNING':
        return `분석 중... (${jobStatus.progress.step || '준비'})`;
      case 'DONE':
        return '분석 완료!';
      case 'FAILED':
        return `실패: ${jobStatus.error?.message || '알 수 없는 오류'}`;
    }
  };

  const getProgressPercent = () => {
    if (!jobStatus) return 0;
    return jobStatus.progress.percent || 0;
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="bg-amber-500 text-white text-xs px-2 py-0.5 rounded font-medium">
          DEMO MODE
        </span>
        <span className="text-sm text-amber-700">시연용 수동 실행 기능</span>
      </div>

      <p className="text-xs text-amber-600 mb-4">
        접속/조회는 분석을 실행하지 않습니다. 아래 기능은 시연을 위한 수동 실행입니다.
      </p>

      <div className="flex items-center gap-3">
        <Select value={selectedCorpId} onValueChange={setSelectedCorpId}>
          <SelectTrigger className="w-[200px] bg-white">
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
          disabled={!selectedCorpId || analyzeJob.isPending || jobStatus?.status === 'RUNNING'}
          className="bg-amber-600 hover:bg-amber-700"
        >
          <Play className="w-4 h-4 mr-2" />
          분석 실행 (시연용)
        </Button>

        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="w-4 h-4 mr-2" />
          결과 새로고침
        </Button>
      </div>

      {/* 작업 상태 표시 */}
      {currentJobId && jobStatus && (
        <div className="mt-4 p-3 bg-white rounded-md border border-amber-100">
          <div className="flex items-center gap-2 mb-2">
            {getStatusIcon()}
            <span className="text-sm font-medium text-amber-800">{getStatusText()}</span>
          </div>

          {(jobStatus.status === 'QUEUED' || jobStatus.status === 'RUNNING') && (
            <Progress value={getProgressPercent()} className="h-2" />
          )}

          {jobStatus.status === 'DONE' && (
            <p className="text-xs text-green-600">
              분석이 완료되었습니다. "결과 새로고침" 버튼을 눌러 시그널을 확인하세요.
            </p>
          )}

          {jobStatus.status === 'FAILED' && (
            <p className="text-xs text-red-600">
              Worker가 아직 구현되지 않았습니다. LLM API 키 설정 후 사용 가능합니다.
            </p>
          )}
        </div>
      )}

      {/* Worker 미구현 안내 (job이 QUEUED 상태로 유지될 때) */}
      {currentJobId && jobStatus?.status === 'QUEUED' && (
        <div className="mt-2 text-xs text-amber-600">
          * 현재 Worker가 구현되지 않아 작업이 대기 상태로 유지됩니다.
        </div>
      )}
    </div>
  );
}
