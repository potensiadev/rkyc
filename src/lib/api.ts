/**
 * rKYC API Client
 * Backend API와 통신하는 클라이언트
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://rkyc-production.up.railway.app';

// API 응답 타입 (Backend 스키마)
export interface ApiCorporation {
  corp_id: string;
  corp_name: string;
  corp_reg_no: string;
  biz_no: string;
  industry_code: string;
  ceo_name: string;
  created_at: string;
  updated_at: string;
}

export type SignalStatusType = 'NEW' | 'REVIEWED' | 'DISMISSED';

export interface ApiSignal {
  index_id: string;
  signal_id: string;
  corp_id: string;
  corp_name: string;
  industry_code: string;
  signal_type: 'DIRECT' | 'INDUSTRY' | 'ENVIRONMENT';
  event_type: string;
  impact_direction: 'RISK' | 'OPPORTUNITY' | 'NEUTRAL';
  impact_strength: 'HIGH' | 'MED' | 'LOW';
  confidence: 'HIGH' | 'MED' | 'LOW';
  title: string;
  summary_short: string;
  evidence_count: number;
  detected_at: string;
  // Session 5: Status fields
  signal_status: SignalStatusType | null;
  reviewed_at: string | null;
  dismissed_at: string | null;
  dismiss_reason: string | null;
}

// Evidence 응답 타입
export interface ApiEvidence {
  evidence_id: string;
  signal_id: string;
  evidence_type: 'INTERNAL_FIELD' | 'DOC' | 'EXTERNAL';
  ref_type: 'SNAPSHOT_KEYPATH' | 'DOC_PAGE' | 'URL';
  ref_value: string;
  snippet: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

// Signal 상세 응답 (Evidence 포함)
export interface ApiSignalDetail extends ApiSignal {
  summary: string; // 전체 요약
  evidences: ApiEvidence[];
}

// Dashboard 요약 통계
export interface ApiDashboardSummary {
  total_signals: number;
  new_signals: number;
  risk_signals: number;
  opportunity_signals: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  generated_at: string;
}

export interface ApiListResponse<T> {
  total: number;
  items: T[];
}

// API 에러 클래스
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// 기본 fetch 래퍼
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API Error: ${response.statusText}`);
  }

  return response.json();
}

// Corporation API
export async function getCorporations(): Promise<ApiListResponse<ApiCorporation>> {
  return fetchApi<ApiListResponse<ApiCorporation>>('/api/v1/corporations');
}

export async function getCorporation(corpId: string): Promise<ApiCorporation> {
  return fetchApi<ApiCorporation>(`/api/v1/corporations/${corpId}`);
}

// Signal API
export interface GetSignalsParams {
  corp_id?: string;
  signal_type?: 'DIRECT' | 'INDUSTRY' | 'ENVIRONMENT';
  impact_direction?: 'RISK' | 'OPPORTUNITY' | 'NEUTRAL';
  signal_status?: SignalStatusType;
  skip?: number;
  limit?: number;
}

export async function getSignals(params?: GetSignalsParams): Promise<ApiListResponse<ApiSignal>> {
  const searchParams = new URLSearchParams();

  if (params?.corp_id) searchParams.set('corp_id', params.corp_id);
  if (params?.signal_type) searchParams.set('signal_type', params.signal_type);
  if (params?.impact_direction) searchParams.set('impact_direction', params.impact_direction);
  if (params?.signal_status) searchParams.set('signal_status', params.signal_status);
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi<ApiListResponse<ApiSignal>>(`/api/v1/signals${query ? `?${query}` : ''}`);
}

export async function getSignal(signalId: string): Promise<ApiSignal> {
  return fetchApi<ApiSignal>(`/api/v1/signals/${signalId}`);
}

// Health check
export async function healthCheck(): Promise<{ status: string }> {
  return fetchApi<{ status: string }>('/health');
}

// Job API Types
export interface JobTriggerResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobProgress {
  step: string | null;
  percent: number;
}

export interface JobError {
  code: string | null;
  message: string | null;
}

export interface JobStatusResponse {
  job_id: string;
  job_type: string;
  corp_id: string | null;
  status: 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED';
  progress: JobProgress;
  error: JobError | null;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
}

// Job API Functions
export async function triggerAnalyzeJob(corpId: string): Promise<JobTriggerResponse> {
  const demoToken = import.meta.env.VITE_DEMO_TOKEN || 'demo';
  return fetchApi<JobTriggerResponse>('/api/v1/jobs/analyze/run', {
    method: 'POST',
    headers: {
      'X-DEMO-TOKEN': demoToken,
    },
    body: JSON.stringify({ corp_id: corpId }),
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return fetchApi<JobStatusResponse>(`/api/v1/jobs/${jobId}`);
}

// ============================================================
// Session 5: Signal Detail & Status APIs
// ============================================================

// Signal 상세 조회 (Evidence 포함)
export async function getSignalDetail(signalId: string): Promise<ApiSignalDetail> {
  return fetchApi<ApiSignalDetail>(`/api/v1/signals/${signalId}/detail`);
}

// Signal 상태 변경
export async function updateSignalStatus(
  signalId: string,
  status: SignalStatusType
): Promise<{ message: string; status: string }> {
  return fetchApi(`/api/v1/signals/${signalId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// Signal 기각
export async function dismissSignal(
  signalId: string,
  reason: string
): Promise<{ message: string; reason: string }> {
  return fetchApi(`/api/v1/signals/${signalId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// Dashboard 요약 통계
export async function getDashboardSummary(): Promise<ApiDashboardSummary> {
  return fetchApi<ApiDashboardSummary>('/api/v1/dashboard/summary');
}

// ============================================================
// Session 5-3: Corporation Snapshot API
// ============================================================

// Snapshot 응답 타입 (PRD 7장 스키마)
export interface ApiSnapshot {
  snapshot_id: string;
  corp_id: string;
  snapshot_version: number;
  snapshot_json: SnapshotJson;
  snapshot_hash: string;
  created_at: string;
}

// PRD 7장 Internal Snapshot JSON 스키마
export interface SnapshotJson {
  schema_version?: string;
  corp: {
    corp_id: string;
    corp_name: string;
    corp_reg_no?: string;
    biz_no?: string;
    industry_code?: string;
    ceo_name?: string;
    kyc_status?: {
      is_kyc_completed: boolean;
      last_kyc_updated: string;
      internal_risk_grade: 'HIGH' | 'MED' | 'LOW';
    };
  };
  credit?: {
    has_loan: boolean;
    loan_summary?: {
      total_exposure_krw: number;
      overdue_flag: boolean;
      risk_grade_internal: string;
    };
  };
  collateral?: {
    has_collateral: boolean;
    collateral_types?: string[];
    total_collateral_value_krw?: number;
  };
  derived_hints?: {
    potential_signals?: string[];
    risk_factors?: string[];
    opportunity_factors?: string[];
  };
}

// Corporation Snapshot 조회
export async function getCorporationSnapshot(corpId: string): Promise<ApiSnapshot> {
  return fetchApi<ApiSnapshot>(`/api/v1/corporations/${corpId}/snapshot`);
}
