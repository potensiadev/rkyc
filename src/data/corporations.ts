// 중앙화된 기업 마스터 데이터 타입 정의
// API 응답 데이터와 호환되는 타입 정의만 유지
// 실제 데이터는 Supabase API에서 가져옵니다.

export interface Executive {
  name: string;
  position: string;
  isKeyMan?: boolean;
}

export interface BankRelationship {
  hasRelationship: boolean;
  depositBalance?: string;
  loanBalance?: string;
  fxTransactions?: string;
  retirementPension?: boolean;
  payrollService?: boolean;
  corporateCard?: boolean;
}

export interface FinancialSnapshot {
  year: number;
  revenue: string;
  operatingProfit: string;
  netProfit: string;
  totalAssets: string;
  totalLiabilities: string;
  equity: string;
}

export interface Shareholder {
  name: string;
  ownership: string;
  type: "개인" | "법인" | "기관";
}

export interface Corporation {
  id: string;  // corp_id from Supabase
  name: string;
  businessNumber: string | null;  // biz_no
  corpRegNo?: string | null;  // corp_reg_no (optional, 개인사업자는 null)
  industry: string;           // industry_master.industry_name
  industryCode: string;       // C26, F41 형식
  mainBusiness: string;       // biz_item (종목)
  ceo: string;
  executives: Executive[];
  employeeCount: number;
  foundedYear: number;
  headquarters: string;       // hq_address or address
  address: string;            // 사업장 소재지
  bizType: string;            // 업태
  isCorporation: boolean;     // 법인/개인 구분
  bankRelationship: BankRelationship;
  financialSnapshots: FinancialSnapshot[];
  shareholders: Shareholder[];
  recentSignalTypes: ("direct" | "industry" | "environment")[];
  lastReviewed: string;
}

// 업종 코드 → 업종명 변환 (industry_master 테이블과 동기화)
export const getIndustryName = (code: string): string => {
  const industries: Record<string, string> = {
    C10: '식품 제조업',
    C21: '의약품 제조업',
    C26: '전자부품 제조업',
    C29: '기계장비 제조업',
    D35: '전기/가스 공급업',
    F41: '종합건설업',
    G47: '소매업',
  };
  return industries[code] || '기타';
};

// ============================================================================
// Corporation Index for O(1) Lookups
// ============================================================================

/** Map type for corporation ID -> Corporation lookup */
export type CorporationIndex = Map<string, Corporation>;

/**
 * Builds an index for O(1) corporation lookups by ID.
 * Single O(n) pass creates the index.
 *
 * @param corporations - Array of Corporation objects to index
 * @returns Map where keys are corporation IDs
 *
 * Complexity: O(n) build time, O(1) lookup time
 */
export const buildCorporationIndex = (
  corporations: Corporation[]
): CorporationIndex => {
  const index = new Map<string, Corporation>();
  for (const corp of corporations) {
    index.set(corp.id, corp);
  }
  return index;
};

/**
 * Retrieves a corporation by ID from precomputed index.
 *
 * @param index - Precomputed CorporationIndex
 * @param corpId - Corporation ID to look up
 * @returns Corporation if found, undefined otherwise
 *
 * Complexity: O(1)
 * Previous (array find): O(n)
 */
export const getCorporationById = (
  index: CorporationIndex,
  corpId: string
): Corporation | undefined => {
  return index.get(corpId);
};
