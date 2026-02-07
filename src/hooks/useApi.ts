/**
 * API Hooks with TanStack Query
 * Backend API 데이터 관리 (Mock 데이터 제거됨)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCorporations,
  getSignals,
  getCorporation,
  getSignal,
  getSignalDetail,
  updateSignalStatus,
  dismissSignal,
  getDashboardSummary,
  getCorporationSnapshot,
  triggerAnalyzeJob,
  getJobStatus,
  getCorpProfile,
  getCorpProfileDetail,
  refreshCorpProfile,
  ApiCorporation,
  ApiSignal,
  ApiSignalDetail,
  ApiEvidence,
  ApiDashboardSummary,
  ApiSnapshot,
  SnapshotJson,
  GetSignalsParams,
  JobStatusResponse,
  SignalStatusType,
} from '@/lib/api';
import type {
  ApiCorpProfileResponse,
  ApiCorpProfileDetailResponse,
} from '@/types/profile';
import { Signal, SignalCategory, SignalStatus, SignalImpact, SignalStrength } from '@/types/signal';
import { Corporation, getIndustryName } from '@/data/corporations';

// API 응답 → Frontend 타입 변환 함수
function mapApiCorporationToFrontend(api: ApiCorporation): Corporation {
  // founded_date에서 연도 추출
  const foundedYear = api.founded_date ? parseInt(api.founded_date.split('-')[0]) : 0;

  return {
    id: api.corp_id,
    name: api.corp_name,
    businessNumber: api.biz_no,
    corpRegNo: api.corp_reg_no,
    // biz_item(종목)이 있으면 더 정확한 정보, 없으면 industry_master에서 조회
    industry: api.biz_item || getIndustryName(api.industry_code),
    industryCode: api.industry_code,
    mainBusiness: api.biz_item || '',
    ceo: api.ceo_name,
    executives: [],
    employeeCount: 0,
    foundedYear,
    // hq_address가 있으면 사용, 없으면 address
    headquarters: api.hq_address || api.address || '',
    address: api.address || '',
    bizType: api.biz_type || '',
    isCorporation: api.is_corporation ?? true,
    bankRelationship: { hasRelationship: false },
    financialSnapshots: [],
    shareholders: [],
    recentSignalTypes: [],
    lastReviewed: api.updated_at.split('T')[0],
  };
}

function mapSignalStatus(status: SignalStatusType | null): SignalStatus {
  if (!status || status === 'NEW') return 'new';
  if (status === 'REVIEWED') return 'review';
  if (status === 'DISMISSED') return 'resolved';
  return 'new';
}

function mapApiSignalToFrontend(api: ApiSignal): Signal {
  const signalCategory = api.signal_type.toLowerCase() as SignalCategory;
  const impact = api.impact_direction.toLowerCase() as SignalImpact;
  const impactStrength = mapStrength(api.impact_strength);

  return {
    id: api.signal_id,
    corporationName: api.corp_name,
    corporationId: api.corp_id,
    signalCategory,
    signalSubType: getSubTypeFromEventType(api.event_type),
    status: mapSignalStatus(api.signal_status),
    title: api.title,
    summary: api.summary_short,
    source: 'rKYC System',
    detectedAt: api.detected_at,
    detailCategory: api.event_type.replace(/_/g, ' '),
    impact,
    impactStrength,
    evidenceCount: api.evidence_count,
    confidenceLevel: mapStrength(api.confidence),
    sourceType: 'external',
    eventClassification: 'market_shift',
  };
}

function mapStrength(strength: 'HIGH' | 'MED' | 'LOW'): SignalStrength {
  const map: Record<string, SignalStrength> = {
    HIGH: 'high',
    MED: 'medium',
    LOW: 'low',
  };
  return map[strength] || 'medium';
}

function getSubTypeFromEventType(eventType: string): 'news' | 'financial' | 'regulatory' | 'governance' | 'market' | 'macro' {
  const mapping: Record<string, 'news' | 'financial' | 'regulatory' | 'governance' | 'market' | 'macro'> = {
    KYC_REFRESH: 'regulatory',
    INTERNAL_RISK_GRADE_CHANGE: 'financial',
    OVERDUE_FLAG_ON: 'financial',
    LOAN_EXPOSURE_CHANGE: 'financial',
    COLLATERAL_CHANGE: 'financial',
    OWNERSHIP_CHANGE: 'governance',
    GOVERNANCE_CHANGE: 'governance',
    FINANCIAL_STATEMENT_UPDATE: 'financial',
    INDUSTRY_SHOCK: 'market',
    POLICY_REGULATION_CHANGE: 'macro',
  };
  return mapping[eventType] || 'news';
}

// TanStack Query Hooks
export function useCorporations() {
  return useQuery({
    queryKey: ['corporations'],
    queryFn: async () => {
      const response = await getCorporations();
      return response.items.map(mapApiCorporationToFrontend);
    },
    staleTime: 5 * 60 * 1000, // 5분
  });
}

export function useCorporation(corpId: string) {
  return useQuery({
    queryKey: ['corporation', corpId],
    queryFn: async () => {
      const response = await getCorporation(corpId);
      return mapApiCorporationToFrontend(response);
    },
    enabled: !!corpId,
  });
}

export function useSignals(params?: GetSignalsParams) {
  return useQuery({
    queryKey: ['signals', params],
    queryFn: async () => {
      const response = await getSignals(params);
      return response.items.map(mapApiSignalToFrontend);
    },
    staleTime: 1 * 60 * 1000, // 1분
  });
}

export function useSignal(signalId: string) {
  return useQuery({
    queryKey: ['signal', signalId],
    queryFn: async () => {
      const response = await getSignal(signalId);
      return mapApiSignalToFrontend(response);
    },
    enabled: !!signalId,
  });
}

// 시그널 통계
export function useSignalStats() {
  return useQuery({
    queryKey: ['signalStats'],
    queryFn: async () => {
      const response = await getSignals({ limit: 1000 });
      const signals = response.items;

      return {
        total: signals.length,
        new: signals.filter(s => !s.signal_status || s.signal_status === 'NEW').length,
        review: signals.filter(s => s.signal_status === 'REVIEWED').length,
        resolved: signals.filter(s => s.signal_status === 'DISMISSED').length,
        risk: signals.filter(s => s.impact_direction === 'RISK').length,
        opportunity: signals.filter(s => s.impact_direction === 'OPPORTUNITY').length,
        neutral: signals.filter(s => s.impact_direction === 'NEUTRAL').length,
        direct: signals.filter(s => s.signal_type === 'DIRECT').length,
        industry: signals.filter(s => s.signal_type === 'INDUSTRY').length,
        environment: signals.filter(s => s.signal_type === 'ENVIRONMENT').length,
      };
    },
  });
}

// Job 관련 훅
export function useAnalyzeJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (corpId: string) => triggerAnalyzeJob(corpId),
    onSuccess: () => {
      // 시그널 목록 새로고침
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['signalStats'] });
    },
  });
}

const JOB_TIMEOUT_MS = 2 * 60 * 1000; // 2분 타임아웃

export function useJobStatus(jobId: string, options?: { enabled?: boolean; refetchInterval?: number; onTimeout?: () => void }) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId),
    enabled: options?.enabled ?? !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as JobStatusResponse | undefined;
      // QUEUED 또는 RUNNING 상태일 때만 폴링
      if (data?.status === 'QUEUED' || data?.status === 'RUNNING') {
        // 타임아웃 체크: created_at 기준 2분 경과 시 폴링 중단
        if (data.queued_at) {
          const createdTime = new Date(data.queued_at).getTime();
          const elapsed = Date.now() - createdTime;
          if (elapsed > JOB_TIMEOUT_MS) {
            options?.onTimeout?.();
            return false; // 폴링 중단
          }
        }
        return options?.refetchInterval ?? 2000;
      }
      return false;
    },
  });
}

// ============================================================
// Signal Detail & Status Hooks
// ============================================================

// Signal 상세 조회 훅 (Evidence 포함)
export function useSignalDetail(signalId: string) {
  return useQuery({
    queryKey: ['signal', signalId, 'detail'],
    queryFn: () => getSignalDetail(signalId),
    enabled: !!signalId,
  });
}

// Signal 상태 변경 훅
export function useUpdateSignalStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ signalId, status }: { signalId: string; status: SignalStatusType }) =>
      updateSignalStatus(signalId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['signal', variables.signalId] });
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['signalStats'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Signal 기각 훅
export function useDismissSignal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ signalId, reason }: { signalId: string; reason: string }) =>
      dismissSignal(signalId, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['signal', variables.signalId] });
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['signalStats'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Dashboard 요약 통계 훅
export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: getDashboardSummary,
    staleTime: 1 * 60 * 1000, // 1분
  });
}

// ============================================================
// Corporation Snapshot Hook
// ============================================================

// Corporation Snapshot 조회 훅
export function useCorporationSnapshot(corpId: string) {
  return useQuery({
    queryKey: ['corporation', corpId, 'snapshot'],
    queryFn: () => getCorporationSnapshot(corpId),
    enabled: !!corpId,
    staleTime: 5 * 60 * 1000, // 5분
  });
}

// ============================================================
// Session 14: Corp Profile Hooks (PRD v1.2)
// ============================================================

// Corp Profile 조회 훅
export function useCorpProfile(corpId: string) {
  return useQuery({
    queryKey: ['corporation', corpId, 'profile'],
    queryFn: () => getCorpProfile(corpId),
    enabled: !!corpId,
    staleTime: 5 * 60 * 1000, // 5분 (TTL 7일이지만 화면 새로고침 시 최신 데이터 확인)
  });
}

// Corp Profile 상세 조회 훅 (Audit Trail 포함)
export function useCorpProfileDetail(corpId: string) {
  return useQuery({
    queryKey: ['corporation', corpId, 'profile', 'detail'],
    queryFn: () => getCorpProfileDetail(corpId),
    enabled: !!corpId,
    staleTime: 5 * 60 * 1000,
    retry: false,  // P1-2 Fix: 404는 재시도 불필요
  });
}

// Corp Profile 갱신 트리거 훅
export function useRefreshCorpProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (corpId: string) => refreshCorpProfile(corpId),
    onSuccess: (_, corpId) => {
      // Profile 관련 쿼리 무효화
      queryClient.invalidateQueries({ queryKey: ['corporation', corpId, 'profile'] });
    },
  });
}

// ============================================================
// 신규 법인 KYC Hooks - 비활성화
// ============================================================

import {
  getNewKycJobStatus,
  getNewKycReport,
  NewKycJobStatusResponse,
  NewKycReportResponse,
} from '@/lib/api';

// 신규 KYC Job 상태 폴링 훅
export function useNewKycJobStatus(jobId: string) {
  return useQuery({
    queryKey: ['new-kyc', 'job', jobId],
    queryFn: () => getNewKycJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as NewKycJobStatusResponse | undefined;
      // QUEUED 또는 RUNNING 상태일 때만 폴링
      if (data?.status === 'QUEUED' || data?.status === 'RUNNING') {
        return 2000; // 2초 간격
      }
      return false;
    },
  });
}

// 신규 KYC 리포트 조회 훅
export function useNewKycReport(jobId: string) {
  return useQuery({
    queryKey: ['new-kyc', 'report', jobId],
    queryFn: () => getNewKycReport(jobId),
    enabled: !!jobId,
    staleTime: 5 * 60 * 1000, // 5분
  });
}

// ============================================================
// Session 16: Signal Enriched Detail Hooks (풍부한 시그널 상세)
// ============================================================

import {
  getSignalEnrichedDetail,
  getSignalSimilarCases,
  getSignalRelated,
  GetSignalEnrichedParams,
  ApiSignalEnrichedDetail,
  ApiSimilarCase,
  ApiRelatedSignal,
  ApiCorpContext,
  ApiEnrichedEvidence,
  ApiVerification,
  ApiImpactAnalysis,
} from '@/lib/api';

// Signal Enriched Detail 조회 훅 (풍부한 상세 정보)
export function useSignalEnrichedDetail(signalId: string, params?: GetSignalEnrichedParams) {
  return useQuery({
    queryKey: ['signal', signalId, 'enriched', params],
    queryFn: () => getSignalEnrichedDetail(signalId, params),
    enabled: !!signalId,
    staleTime: 2 * 60 * 1000, // 2분
  });
}

// 유사 과거 케이스 조회 훅
export function useSignalSimilarCases(signalId: string, limit?: number, minSimilarity?: number) {
  return useQuery({
    queryKey: ['signal', signalId, 'similar-cases', { limit, minSimilarity }],
    queryFn: () => getSignalSimilarCases(signalId, limit, minSimilarity),
    enabled: !!signalId,
    staleTime: 5 * 60 * 1000, // 5분
  });
}

// 관련 시그널 조회 훅
export function useSignalRelated(signalId: string, relationTypes?: string[], limit?: number) {
  return useQuery({
    queryKey: ['signal', signalId, 'related', { relationTypes, limit }],
    queryFn: () => getSignalRelated(signalId, relationTypes, limit),
    enabled: !!signalId,
    staleTime: 2 * 60 * 1000, // 2분
  });
}

// ============================================================
// Session 16: Scheduler Control Hooks (실시간 자동 탐지 제어)
// ============================================================

import {
  getSchedulerStatus,
  startScheduler,
  stopScheduler,
  setSchedulerInterval,
  triggerImmediateScan,
  SchedulerStatus,
  SchedulerActionResponse,
  SchedulerTriggerResponse,
} from '@/lib/api';

// 스케줄러 상태 조회 훅
export function useSchedulerStatus() {
  return useQuery({
    queryKey: ['scheduler', 'status'],
    queryFn: getSchedulerStatus,
    refetchInterval: 5000, // 5초마다 상태 갱신
  });
}

// 스케줄러 시작 훅
export function useStartScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (intervalMinutes: number) => startScheduler(intervalMinutes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] });
    },
  });
}

// 스케줄러 중지 훅
export function useStopScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: stopScheduler,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] });
    },
  });
}

// 스케줄러 주기 변경 훅
export function useSetSchedulerInterval() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (intervalMinutes: number) => setSchedulerInterval(intervalMinutes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] });
    },
  });
}

// 즉시 스캔 트리거 훅
export function useTriggerImmediateScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerImmediateScan,
    onSuccess: () => {
      // 스캔 후 시그널 목록 갱신
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] });
    },
  });
}

// ============================================================
// Report Hook
// ============================================================

import {
  getCorporationReport,
  getLoanInsight,
  checkLoanInsightExists,
  getAllLoanInsightSummaries,
  ApiReportResponse,
  ApiLoanInsightResponse,
  ApiLoanInsightExistsResponse,
  ApiLoanInsightSummary,
  ApiLoanInsightSummariesResponse,
} from '@/lib/api';

export function useCorporationReport(corpId: string) {
  return useQuery({
    queryKey: ['report', corpId],
    queryFn: () => getCorporationReport(corpId),
    enabled: !!corpId,
    // 캐싱 전략 개선: 더 긴 캐시 유지
    staleTime: 10 * 60 * 1000,      // 10분 동안 fresh 상태
    gcTime: 30 * 60 * 1000,          // 30분 동안 캐시 유지 (구 cacheTime)
    refetchOnWindowFocus: false,     // 포커스 시 재요청 방지
    refetchOnMount: false,           // 마운트 시 재요청 방지 (캐시 있으면)
  });
}

// ============================================================
// Loan Insight Hook
// ============================================================

export function useLoanInsight(corpId: string) {
  return useQuery({
    queryKey: ['loan-insight', corpId],
    queryFn: () => getLoanInsight(corpId),
    enabled: !!corpId,
    staleTime: 5 * 60 * 1000,
    retry: false, // 404면 재시도 안함
  });
}

export function useLoanInsightExists(corpId: string) {
  return useQuery({
    queryKey: ['loan-insight-exists', corpId],
    queryFn: () => checkLoanInsightExists(corpId),
    enabled: !!corpId,
    staleTime: 60 * 1000, // 1분 캐시
  });
}

// Signal Inbox용 - 전체 기업 스탠스 배치 조회
export function useLoanInsightSummaries() {
  return useQuery({
    queryKey: ['loan-insight-summaries'],
    queryFn: () => getAllLoanInsightSummaries(),
    staleTime: 2 * 60 * 1000, // 2분 캐시
  });
}

// API 타입 re-export (페이지에서 직접 사용)
export type {
  ApiSignalDetail,
  ApiEvidence,
  ApiDashboardSummary,
  ApiSnapshot,
  SnapshotJson,
  SignalStatusType,
  ApiCorpProfileResponse,
  ApiCorpProfileDetailResponse,
  NewKycJobStatusResponse,
  NewKycReportResponse,
  // Session 16: Enriched types
  ApiSignalEnrichedDetail,
  ApiSimilarCase,
  ApiRelatedSignal,
  ApiCorpContext,
  ApiEnrichedEvidence,
  ApiVerification,
  ApiImpactAnalysis,
  // Scheduler types
  SchedulerStatus,
  SchedulerActionResponse,
  SchedulerTriggerResponse,
  // Report types
  ApiReportResponse,
  // Loan Insight types
  ApiLoanInsightResponse,
  ApiLoanInsightExistsResponse,
  ApiLoanInsightSummary,
  ApiLoanInsightSummariesResponse,
};
