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
  businessNumber: string;  // biz_no
  corpRegNo?: string;  // corp_reg_no (optional)
  industry: string;
  industryCode: string;  // C26, F41 형식
  mainBusiness: string;
  ceo: string;
  executives: Executive[];
  employeeCount: number;
  foundedYear: number;
  headquarters: string;
  bankRelationship: BankRelationship;
  financialSnapshots: FinancialSnapshot[];
  shareholders: Shareholder[];
  recentSignalTypes: ("direct" | "industry" | "environment")[];
  lastReviewed: string;
}

// 업종 코드 → 업종명 변환
export const getIndustryName = (code: string): string => {
  const industries: Record<string, string> = {
    C10: '식품 제조업',
    C21: '의약품 제조업',
    C26: '전자부품 제조업',
    C29: '기계장비 제조업',
    D35: '전기/가스 공급업',
    F41: '종합건설업',
  };
  return industries[code] || '기타';
};
