/**
 * Corp Profile TypeScript Types
 * PRD v1.2: Corp Profiling Pipeline
 */

// ============================================================================
// Confidence Levels
// ============================================================================

export type ProfileConfidence = 'HIGH' | 'MED' | 'LOW' | 'NONE' | 'CACHED' | 'STALE';
export type ProfileStatus = 'ACTIVE' | 'INACTIVE' | 'UNKNOWN';

// ============================================================================
// Nested Types (JSONB fields)
// ============================================================================

export interface Executive {
  name: string;
  position: string;
  tenure_years?: number;
}

export interface FinancialSnapshot {
  year: number;
  revenue_krw?: number;
  operating_profit_krw?: number;
  net_profit_krw?: number;
  total_assets_krw?: number;
  total_liabilities_krw?: number;
  export_ratio_pct?: number;
}

export interface Competitor {
  name: string;
  market_share_pct?: number;
  relationship?: 'DIRECT' | 'INDIRECT';
}

export interface MacroFactor {
  factor: string;
  impact: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  description?: string;
}

export interface SupplyChain {
  key_suppliers: string[];
  supplier_countries: Record<string, number>;  // {"중국": 60, "일본": 30}
  single_source_risk: string[];
  material_import_ratio_pct: number | null;
}

export interface OverseasBusiness {
  subsidiaries: OverseasSubsidiary[];
  manufacturing_countries: string[];
}

export interface OverseasSubsidiary {
  name: string;
  country: string;
  business_type?: string;
  ownership_pct?: number;
}

export interface Shareholder {
  name: string;
  ownership_pct: number;
  is_largest?: boolean;
  relationship?: 'FOUNDER' | 'INSTITUTION' | 'FOREIGN' | 'OTHER';
}

// ============================================================================
// Consensus Metadata (PRD v1.2)
// ============================================================================

// Fallback Layer names from backend FallbackLayer enum
export type FallbackLayerType =
  | 'CACHE'
  | 'PERPLEXITY_GEMINI'
  | 'CLAUDE_SYNTHESIS'
  | 'RULE_BASED'
  | 'GRACEFUL_DEGRADATION'
  | number;  // Also accepts numeric values for backwards compatibility

export interface ConsensusMetadata {
  consensus_at: string | null;
  perplexity_success: boolean;
  gemini_success: boolean;
  claude_success: boolean;
  total_fields: number;
  matched_fields: number;
  discrepancy_fields: number;
  enriched_fields: number;
  overall_confidence: ProfileConfidence;
  fallback_layer: FallbackLayerType;  // Can be string enum or number
  retry_count: number;
  error_messages: string[];
}

// ============================================================================
// Field Provenance (Anti-Hallucination Audit Trail)
// ============================================================================

export interface FieldProvenance {
  source_url: string;
  excerpt: string;
  confidence: ProfileConfidence;
  extraction_date: string;
}

// ============================================================================
// Main Corp Profile Interface
// ============================================================================

export interface CorpProfile {
  profile_id: string;
  corp_id: string;

  // Basic Info
  business_summary: string | null;
  ceo_name: string | null;
  employee_count: number | null;
  founded_year: number | null;
  headquarters: string | null;
  executives: Executive[];

  // Business Overview
  industry_overview: string | null;
  business_model: string | null;

  // Financial
  revenue_krw: number | null;
  export_ratio_pct: number | null;
  financial_history: FinancialSnapshot[];

  // Exposure Information
  country_exposure: Record<string, number>;
  key_materials: string[];
  key_customers: string[];
  overseas_operations: string[];  // Legacy compatibility

  // Value Chain (PRD v1.2)
  competitors: Competitor[];
  macro_factors: MacroFactor[];

  // Supply Chain (PRD v1.2)
  supply_chain: SupplyChain;

  // Overseas Business (PRD v1.2)
  overseas_business: OverseasBusiness;

  // Shareholders
  shareholders: Shareholder[];

  // Consensus Metadata (PRD v1.2)
  consensus_metadata: ConsensusMetadata;

  // Confidence & Attribution
  profile_confidence: ProfileConfidence;
  field_confidences: Record<string, ProfileConfidence>;
  source_urls: string[];

  // Audit Trail
  raw_search_result?: unknown;
  field_provenance: Record<string, FieldProvenance>;
  extraction_model: string | null;
  extraction_prompt_version: string | null;

  // Fallback Flags
  is_fallback: boolean;
  search_failed: boolean;
  validation_warnings: string[];

  // Status & TTL
  status: ProfileStatus;
  fetched_at: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiCorpProfileResponse {
  profile_id: string;
  corp_id: string;

  // Basic Info
  business_summary: string | null;
  ceo_name: string | null;
  employee_count: number | null;
  founded_year: number | null;
  headquarters: string | null;
  executives: Executive[];

  // Business Overview
  industry_overview: string | null;
  business_model: string | null;

  // Financial
  revenue_krw: number | null;
  export_ratio_pct: number | null;
  financial_history: FinancialSnapshot[];

  // Exposure
  country_exposure: Record<string, number>;
  key_materials: string[];
  key_customers: string[];
  overseas_operations: string[];

  // Value Chain
  competitors: Competitor[];
  macro_factors: MacroFactor[];

  // Supply Chain
  supply_chain: SupplyChain;

  // Overseas Business
  overseas_business: OverseasBusiness;

  // Shareholders
  shareholders: Shareholder[];

  // Metadata
  consensus_metadata: ConsensusMetadata;
  profile_confidence: ProfileConfidence;
  field_confidences: Record<string, ProfileConfidence>;
  source_urls: string[];

  // Status
  is_fallback: boolean;
  status: ProfileStatus;
  fetched_at: string;
  expires_at: string;
}

// Detail response includes audit trail
export interface ApiCorpProfileDetailResponse extends ApiCorpProfileResponse {
  field_provenance: Record<string, FieldProvenance>;
  extraction_model: string | null;
  extraction_prompt_version: string | null;
  search_failed: boolean;
  validation_warnings: string[];
  raw_search_result?: unknown;
  created_at: string;
  updated_at: string;
}

// Refresh trigger response
export interface ApiProfileRefreshResponse {
  message: string;
  corp_id: string;
  job_id: string;
  status: 'QUEUED' | 'FAILED';
  note?: string;
  error?: string;
}
