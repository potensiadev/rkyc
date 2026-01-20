/**
 * Scheduler Control Panel
 * 실시간 자동 시그널 탐지 제어 UI
 */

import { useState } from 'react';
import {
  useSchedulerStatus,
  useStartScheduler,
  useStopScheduler,
  useSetSchedulerInterval,
  useTriggerImmediateScan,
} from '@/hooks/useApi';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, Square, RefreshCw, Clock, Zap, Activity, AlertCircle } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const INTERVAL_OPTIONS = [
  { value: 1, label: '1분' },
  { value: 3, label: '3분' },
  { value: 5, label: '5분' },
  { value: 10, label: '10분' },
];

export function SchedulerPanel() {
  const [selectedInterval, setSelectedInterval] = useState<number>(5);

  const { data: status, isLoading: statusLoading, error: statusError } = useSchedulerStatus();
  const startScheduler = useStartScheduler();
  const stopScheduler = useStopScheduler();
  const setInterval = useSetSchedulerInterval();
  const triggerScan = useTriggerImmediateScan();

  const isRunning = status?.status === 'RUNNING';

  const handleStart = () => {
    startScheduler.mutate(selectedInterval);
  };

  const handleStop = () => {
    stopScheduler.mutate();
  };

  const handleIntervalChange = (value: string) => {
    const newInterval = parseInt(value);
    setSelectedInterval(newInterval);

    // 실행 중이면 즉시 주기 변경
    if (isRunning) {
      setInterval.mutate(newInterval);
    }
  };

  const handleTriggerNow = () => {
    triggerScan.mutate();
  };

  // 시간 포맷팅
  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // 다음 실행까지 남은 시간 계산
  const getTimeUntilNext = () => {
    if (!status?.next_run || !isRunning) return null;
    const next = new Date(status.next_run);
    const now = new Date();
    const diffMs = next.getTime() - now.getTime();
    if (diffMs < 0) return '곧 시작';
    const diffSec = Math.floor(diffMs / 1000);
    const min = Math.floor(diffSec / 60);
    const sec = diffSec % 60;
    return `${min}분 ${sec}초`;
  };

  if (statusError) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-red-700">
            <AlertCircle className="h-4 w-4" />
            스케줄러 연결 오류
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-600">
            스케줄러 상태를 확인할 수 없습니다. Worker가 실행 중인지 확인하세요.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={isRunning ? 'border-green-300 bg-green-50/50' : 'border-gray-200'}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className={`h-4 w-4 ${isRunning ? 'text-green-600 animate-pulse' : 'text-gray-400'}`} />
              실시간 자동 탐지
            </CardTitle>
            <CardDescription className="mt-1">
              전체 기업의 리스크/기회 시그널을 자동으로 탐지합니다
            </CardDescription>
          </div>
          <Badge
            variant={isRunning ? 'default' : 'secondary'}
            className={isRunning ? 'bg-green-600' : ''}
          >
            {statusLoading ? '확인 중...' : isRunning ? '실행 중' : '중지됨'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 제어 버튼 */}
        <div className="flex items-center gap-3">
          {/* 주기 선택 */}
          <Select
            value={selectedInterval.toString()}
            onValueChange={handleIntervalChange}
            disabled={startScheduler.isPending || setInterval.isPending}
          >
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="주기 선택" />
            </SelectTrigger>
            <SelectContent>
              {INTERVAL_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value.toString()}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 시작/중지 버튼 */}
          {isRunning ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleStop}
              disabled={stopScheduler.isPending}
            >
              {stopScheduler.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Square className="h-4 w-4 mr-1" />
              )}
              중지
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={handleStart}
              disabled={startScheduler.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {startScheduler.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Play className="h-4 w-4 mr-1" />
              )}
              시작
            </Button>
          )}

          {/* 즉시 실행 버튼 */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleTriggerNow}
            disabled={!isRunning || triggerScan.isPending}
          >
            {triggerScan.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Zap className="h-4 w-4 mr-1" />
            )}
            즉시 실행
          </Button>
        </div>

        {/* 상태 정보 */}
        {status && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="bg-white rounded-lg p-2 border">
              <div className="text-gray-500 text-xs">현재 주기</div>
              <div className="font-medium flex items-center gap-1">
                <Clock className="h-3 w-3 text-gray-400" />
                {status.interval_minutes}분
              </div>
            </div>

            <div className="bg-white rounded-lg p-2 border">
              <div className="text-gray-500 text-xs">마지막 실행</div>
              <div className="font-medium">
                {formatTime(status.last_run)}
              </div>
            </div>

            <div className="bg-white rounded-lg p-2 border">
              <div className="text-gray-500 text-xs">다음 실행</div>
              <div className="font-medium text-green-600">
                {isRunning ? getTimeUntilNext() || formatTime(status.next_run) : '-'}
              </div>
            </div>

            <div className="bg-white rounded-lg p-2 border">
              <div className="text-gray-500 text-xs">총 실행 횟수</div>
              <div className="font-medium">{status.total_runs}회</div>
            </div>
          </div>
        )}

        {/* 통계 정보 */}
        {status && (
          <div className="flex items-center gap-4 text-sm text-gray-600 pt-2 border-t">
            <span>
              <span className="font-medium">{status.corporations_count}</span>개 기업 모니터링
            </span>
            <span>
              <span className="font-medium text-blue-600">{status.total_signals_detected}</span>개 시그널 탐지
            </span>
          </div>
        )}

        {/* 안내 문구 */}
        <p className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
          스케줄러가 실행되면 설정된 주기마다 모든 기업의 외부 정보를 검색하고 리스크/기회 시그널을 자동으로 탐지합니다.
        </p>
      </CardContent>
    </Card>
  );
}
