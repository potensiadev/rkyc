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
  skip?: number;
  limit?: number;
}

export async function getSignals(params?: GetSignalsParams): Promise<ApiListResponse<ApiSignal>> {
  const searchParams = new URLSearchParams();

  if (params?.corp_id) searchParams.set('corp_id', params.corp_id);
  if (params?.signal_type) searchParams.set('signal_type', params.signal_type);
  if (params?.impact_direction) searchParams.set('impact_direction', params.impact_direction);
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
