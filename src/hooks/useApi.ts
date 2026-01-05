/**
 * API Hooks with TanStack Query
 * Backend API와 Mock 데이터를 통합 관리
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
import { Corporation, CORPORATIONS } from '@/data/corporations';
import { SIGNALS } from '@/data/signals';

// 환경변수로 Demo 모드 제어
const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

// API 응답 → Frontend 타입 변환 함수
function mapApiCorporationToFrontend(api: ApiCorporation): Corporation {
  // Mock 데이터에서 상세 정보 조회 (corp_id로 직접 매칭)
  const mockCorp = CORPORATIONS.find(c => c.id === api.corp_id);

  if (mockCorp) {
    return {
      ...mockCorp,
      id: api.corp_id,
      name: api.corp_name,
      ceo: api.ceo_name,
    };
  }

  // Mock 데이터가 없으면 기본값으로 반환
  return {
    id: api.corp_id,
    name: api.corp_name,
    businessNumber: api.biz_no,
    corpRegNo: api.corp_reg_no,
    industry: getIndustryName(api.industry_code),
    industryCode: api.industry_code,
    mainBusiness: '',
    ceo: api.ceo_name,
    executives: [],
    employeeCount: 0,
    foundedYear: 0,
    headquarters: '',
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

function getIndustryName(code: string): string {
  const industries: Record<string, string> = {
    C10: '식품제조업',
    C21: '의약품제조업',
    C26: '전자부품제조업',
    C29: '기계장비제조업',
    D35: '전기업',
    F41: '건설업',
  };
  return industries[code] || '기타';
}

// TanStack Query Hooks
export function useCorporations() {
  return useQuery({
    queryKey: ['corporations'],
    queryFn: async () => {
      if (isDemoMode) {
        return CORPORATIONS;
      }
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
      if (isDemoMode) {
        // Mock ID ("1", "2") 또는 API corp_id ("8001-3719240") 모두 지원
        const corp = CORPORATIONS.find(c => c.id === corpId);
        if (corp) return corp;
        // corp_id로 매칭 실패시 null 반환하지 않고 API 호출
      }
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
      if (isDemoMode) {
        let signals = SIGNALS;

        if (params?.corp_id) {
          signals = signals.filter(s => s.corporationId === params.corp_id);
        }
        if (params?.signal_type) {
          const category = params.signal_type.toLowerCase() as SignalCategory;
          signals = signals.filter(s => s.signalCategory === category);
        }
        if (params?.impact_direction) {
          const impact = params.impact_direction.toLowerCase() as SignalImpact;
          signals = signals.filter(s => s.impact === impact);
        }

        return signals;
      }
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
      if (isDemoMode) {
        return SIGNALS.find(s => s.id === signalId) || null;
      }
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
      if (isDemoMode) {
        return {
          total: SIGNALS.length,
          new: SIGNALS.filter(s => s.status === 'new').length,
          review: SIGNALS.filter(s => s.status === 'review').length,
          resolved: SIGNALS.filter(s => s.status === 'resolved').length,
          risk: SIGNALS.filter(s => s.impact === 'risk').length,
          opportunity: SIGNALS.filter(s => s.impact === 'opportunity').length,
          neutral: SIGNALS.filter(s => s.impact === 'neutral').length,
          direct: SIGNALS.filter(s => s.signalCategory === 'direct').length,
          industry: SIGNALS.filter(s => s.signalCategory === 'industry').length,
          environment: SIGNALS.filter(s => s.signalCategory === 'environment').length,
        };
      }

      const response = await getSignals({ limit: 1000 });
      const signals = response.items;

      return {
        total: signals.length,
        new: signals.length, // API에서는 status 없음
        review: 0,
        resolved: 0,
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
// Session 5: Signal Detail & Status Hooks
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
// Session 5-3: Corporation Snapshot Hook
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
