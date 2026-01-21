/**
 * rKYC API Client
 * Backend API와 통신하는 클라이언트
 */

import type {
  ApiCorpProfileResponse,
  ApiCorpProfileDetailResponse,
  ApiProfileRefreshResponse,
} from '@/types/profile';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://rkyc-production.up.railway.app';

// API 응답 타입 (Backend 스키마)
export interface ApiCorporation {
  corp_id: string;
  corp_name: string;
  corp_reg_no: string | null;
  biz_no: string | null;
  industry_code: string;
  ceo_name: string;
  // 사업자등록증 추가 정보 (migration_v9)
  address: string | null;
  hq_address: string | null;
  founded_date: string | null;  // YYYY-MM-DD
  biz_type: string | null;      // 업태
  biz_item: string | null;      // 종목 (상세 업종)
  is_corporation: boolean | null;
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

// ============================================================
// Session 14: Corp Profile API (PRD v1.2)
// ============================================================

// Corp Profile 조회 (기본)
export async function getCorpProfile(corpId: string): Promise<ApiCorpProfileResponse> {
  return fetchApi<ApiCorpProfileResponse>(`/api/v1/corporations/${corpId}/profile`);
}

// Corp Profile 상세 조회 (Audit Trail 포함)
export async function getCorpProfileDetail(corpId: string): Promise<ApiCorpProfileDetailResponse> {
  return fetchApi<ApiCorpProfileDetailResponse>(`/api/v1/corporations/${corpId}/profile/detail`);
}

// Corp Profile 갱신 트리거
export async function refreshCorpProfile(corpId: string): Promise<ApiProfileRefreshResponse> {
  const demoToken = import.meta.env.VITE_DEMO_TOKEN || 'demo';
  return fetchApi<ApiProfileRefreshResponse>(`/api/v1/corporations/${corpId}/profile/refresh`, {
    method: 'POST',
    headers: {
      'X-DEMO-TOKEN': demoToken,
    },
  });
}

// ============================================================
// 신규 법인 KYC API
// ============================================================

// 신규 KYC 분석 요청 타입
export interface NewKycAnalysisRequest {
  corpName?: string;
  memo?: string;
  files: { type: string; file: File }[];
}

// 신규 KYC 분석 응답
export interface NewKycAnalysisResponse {
  job_id: string;
  status: string;
  message: string;
}

// 신규 KYC Job 상태 응답
export interface NewKycJobStatusResponse {
  job_id: string;
  status: 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED';
  corp_name?: string;
  progress: {
    step: string | null;
    percent: number;
  };
  error?: {
    code: string | null;
    message: string | null;
  };
}

// 신규 KYC 리포트 - 시그널
export interface NewKycSignal {
  signal_id?: string;
  signal_type: string;
  event_type: string;
  impact_direction: 'RISK' | 'OPPORTUNITY' | 'NEUTRAL';
  impact_strength: 'HIGH' | 'MED' | 'LOW';
  confidence: 'HIGH' | 'MED' | 'LOW';
  title: string;
  summary: string;
  evidences?: {
    evidence_type: string;
    ref_type: string;
    ref_value: string;
    snippet?: string;
  }[];
}

// 신규 KYC 리포트 응답
export interface NewKycReportResponse {
  job_id: string;
  corp_info: {
    corp_name?: string;
    biz_no?: string;
    corp_reg_no?: string;
    ceo_name?: string;
    founded_date?: string;
    industry?: string;
    capital?: number;
    address?: string;
  };
  financial_summary?: {
    year: number;
    revenue?: number;
    operating_profit?: number;
    debt_ratio?: number;
  };
  shareholders?: {
    name: string;
    ownership_pct: number;
  }[];
  signals: NewKycSignal[];
  insight?: string;
  created_at: string;
}

// 신규 KYC 분석 시작
export async function startNewKycAnalysis(request: NewKycAnalysisRequest): Promise<NewKycAnalysisResponse> {
  const formData = new FormData();

  if (request.corpName) {
    formData.append('corp_name', request.corpName);
  }
  if (request.memo) {
    formData.append('memo', request.memo);
  }

  // 파일 추가
  request.files.forEach(({ type, file }) => {
    formData.append(`file_${type}`, file);
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/new-kyc/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API Error: ${response.statusText}`);
  }

  return response.json();
}

// 신규 KYC Job 상태 조회
export async function getNewKycJobStatus(jobId: string): Promise<NewKycJobStatusResponse> {
  return fetchApi<NewKycJobStatusResponse>(`/api/v1/new-kyc/jobs/${jobId}`);
}

// 신규 KYC 리포트 조회
export async function getNewKycReport(jobId: string): Promise<NewKycReportResponse> {
  return fetchApi<NewKycReportResponse>(`/api/v1/new-kyc/report/${jobId}`);
}

// ============================================================
// Session 16: Signal Enriched Detail API (풍부한 시그널 상세)
// ============================================================

// 유사 과거 케이스
export interface ApiSimilarCase {
  id: string;
  similarity_score: number;
  corp_id: string | null;
  corp_name: string | null;
  industry_code: string | null;
  signal_type: string | null;
  event_type: string | null;
  summary: string | null;
  outcome: string | null;
}

// 소스 검증 결과
export interface ApiVerification {
  id: string;
  verification_type: string;
  source_name: string | null;
  source_url: string | null;
  verification_status: 'VERIFIED' | 'PARTIAL' | 'UNVERIFIED' | 'CONFLICTING';
  confidence_contribution: number | null;
  details: Record<string, unknown> | null;
  verified_at: string;
}

// 영향도 분석
export interface ApiImpactAnalysis {
  id: string;
  analysis_type: 'FINANCIAL' | 'CREDIT' | 'OPERATIONAL' | 'REGULATORY';
  metric_name: string;
  current_value: number | null;
  projected_impact: number | null;
  impact_direction: 'INCREASE' | 'DECREASE' | 'STABLE' | null;
  impact_percentage: number | null;
  industry_avg: number | null;
  industry_percentile: number | null;
  reasoning: string | null;
  data_source: string | null;
}

// 관련 시그널
export interface ApiRelatedSignal {
  signal_id: string;
  relation_type: 'SAME_CORP' | 'SAME_INDUSTRY' | 'CAUSAL' | 'TEMPORAL';
  relation_strength: number | null;
  corp_id: string;
  corp_name: string;
  signal_type: string;
  event_type: string;
  impact_direction: string;
  impact_strength: string;
  title: string;
  summary_short: string | null;
  detected_at: string;
  description: string | null;
}

// 기업 컨텍스트
export interface ApiCorpContext {
  corp_id: string;
  corp_name: string;
  industry_code: string;
  industry_name: string | null;
  revenue_krw: number | null;
  employee_count: number | null;
  export_ratio_pct: number | null;
  country_exposure: string[] | null;
  key_materials: string[] | null;
  key_customers: string[] | null;
  supply_chain_risk: 'LOW' | 'MED' | 'HIGH' | null;
  internal_risk_grade: string | null;
  overdue_flag: boolean | null;
  total_exposure_krw: number | null;
  profile_confidence: string | null;
  profile_updated_at: string | null;
}

// 확장된 Evidence
export interface ApiEnrichedEvidence extends ApiEvidence {
  source_credibility: 'OFFICIAL' | 'MAJOR_MEDIA' | 'MINOR_MEDIA' | 'UNKNOWN' | null;
  verification_status: string | null;
  retrieved_at: string | null;
  source_domain: string | null;
  is_primary_source: boolean;
}

// 풍부한 시그널 상세 응답
export interface ApiSignalEnrichedDetail extends ApiSignal {
  summary: string;
  evidences: ApiEnrichedEvidence[];
  analysis_reasoning: string | null;
  llm_model: string | null;
  corp_context: ApiCorpContext | null;
  similar_cases: ApiSimilarCase[];
  verifications: ApiVerification[];
  impact_analysis: ApiImpactAnalysis[];
  related_signals: ApiRelatedSignal[];
  insight_excerpt: string | null;
}

// Signal Enriched Detail 조회
export interface GetSignalEnrichedParams {
  include_similar_cases?: boolean;
  include_verifications?: boolean;
  include_impact?: boolean;
  include_related?: boolean;
}

export async function getSignalEnrichedDetail(
  signalId: string,
  params?: GetSignalEnrichedParams
): Promise<ApiSignalEnrichedDetail> {
  const searchParams = new URLSearchParams();

  if (params?.include_similar_cases !== undefined) {
    searchParams.set('include_similar_cases', String(params.include_similar_cases));
  }
  if (params?.include_verifications !== undefined) {
    searchParams.set('include_verifications', String(params.include_verifications));
  }
  if (params?.include_impact !== undefined) {
    searchParams.set('include_impact', String(params.include_impact));
  }
  if (params?.include_related !== undefined) {
    searchParams.set('include_related', String(params.include_related));
  }

  const query = searchParams.toString();
  return fetchApi<ApiSignalEnrichedDetail>(
    `/api/v1/signals-enriched/${signalId}/enriched${query ? `?${query}` : ''}`
  );
}

// 유사 케이스만 조회
export async function getSignalSimilarCases(
  signalId: string,
  limit?: number,
  minSimilarity?: number
): Promise<ApiSimilarCase[]> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set('limit', String(limit));
  if (minSimilarity) searchParams.set('min_similarity', String(minSimilarity));

  const query = searchParams.toString();
  return fetchApi<ApiSimilarCase[]>(
    `/api/v1/signals-enriched/${signalId}/similar-cases${query ? `?${query}` : ''}`
  );
}

// 관련 시그널만 조회
export async function getSignalRelated(
  signalId: string,
  relationTypes?: string[],
  limit?: number
): Promise<ApiRelatedSignal[]> {
  const searchParams = new URLSearchParams();
  if (relationTypes) {
    relationTypes.forEach(t => searchParams.append('relation_types', t));
  }
  if (limit) searchParams.set('limit', String(limit));

  const query = searchParams.toString();
  return fetchApi<ApiRelatedSignal[]>(
    `/api/v1/signals-enriched/${signalId}/related${query ? `?${query}` : ''}`
  );
}

// ============================================================
// Session 16: Scheduler Control API (실시간 자동 탐지)
// ============================================================

export type SchedulerStatusType = 'STOPPED' | 'RUNNING' | 'PAUSED';

export interface SchedulerStatus {
  status: SchedulerStatusType;
  interval_minutes: number;
  last_run: string | null;
  next_run: string | null;
  total_runs: number;
  total_signals_detected: number;
  corporations_count: number;
  current_corp_index: number;
}

export interface SchedulerActionResponse {
  status: string;
  message: string;
  interval_minutes?: number;
  corporations_count?: number;
}

export interface SchedulerTriggerResponse {
  status: string;
  result?: {
    cycle: number;
    jobs_created: number;
    corporations_scanned: number;
    new_signals: number;
    timestamp: string;
  };
}

// 스케줄러 상태 조회
export async function getSchedulerStatus(): Promise<SchedulerStatus> {
  return fetchApi<SchedulerStatus>('/api/v1/scheduler/status');
}

// 스케줄러 시작
export async function startScheduler(intervalMinutes: number): Promise<SchedulerActionResponse> {
  return fetchApi<SchedulerActionResponse>('/api/v1/scheduler/start', {
    method: 'POST',
    body: JSON.stringify({ interval_minutes: intervalMinutes }),
  });
}

// 스케줄러 중지
export async function stopScheduler(): Promise<SchedulerActionResponse> {
  return fetchApi<SchedulerActionResponse>('/api/v1/scheduler/stop', {
    method: 'POST',
  });
}

// 스케줄러 주기 변경
export async function setSchedulerInterval(intervalMinutes: number): Promise<SchedulerActionResponse> {
  return fetchApi<SchedulerActionResponse>('/api/v1/scheduler/interval', {
    method: 'PATCH',
    body: JSON.stringify({ interval_minutes: intervalMinutes }),
  });
}

// 즉시 스캔 트리거
export async function triggerImmediateScan(): Promise<SchedulerTriggerResponse> {
  return fetchApi<SchedulerTriggerResponse>('/api/v1/scheduler/trigger', {
    method: 'POST',
  });
}
