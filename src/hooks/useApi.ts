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

export function useJobStatus(jobId: string, options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId),
    enabled: options?.enabled ?? !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as JobStatusResponse | undefined;
      // QUEUED 또는 RUNNING 상태일 때만 폴링
      if (data?.status === 'QUEUED' || data?.status === 'RUNNING') {
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

// API 타입 re-export (페이지에서 직접 사용)
export type { ApiSignalDetail, ApiEvidence, ApiDashboardSummary, ApiSnapshot, SnapshotJson, SignalStatusType };
