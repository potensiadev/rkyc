// 중앙화된 기업 마스터 데이터
// Supabase corp 테이블 기준
// 모든 화면에서 동일한 기업 정보를 사용합니다.

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

// Supabase corp 테이블 기준 6개 기업
export const CORPORATIONS: Corporation[] = [
  {
    id: "8001-3719240",
    name: "엠케이전자",
    businessNumber: "135-81-06406",
    corpRegNo: "134511-0004412",
    industry: "전자부품 제조업",
    industryCode: "C26",
    mainBusiness: "반도체 부품 및 전자부품 제조",
    ceo: "현기진",
    executives: [
      { name: "현기진", position: "대표이사", isKeyMan: true },
      { name: "이기술", position: "기술연구소장", isKeyMan: true },
      { name: "박영업", position: "영업본부장" },
    ],
    employeeCount: 156,
    foundedYear: 2005,
    headquarters: "경기 화성시 동탄",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "15억원",
      loanBalance: "12억원",
      fxTransactions: "연 50억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "320억원", operatingProfit: "25억원", netProfit: "18억원", totalAssets: "245억원", totalLiabilities: "120억원", equity: "125억원" },
      { year: 2022, revenue: "298억원", operatingProfit: "22억원", netProfit: "15억원", totalAssets: "225억원", totalLiabilities: "112억원", equity: "113억원" },
      { year: 2021, revenue: "275억원", operatingProfit: "19억원", netProfit: "12억원", totalAssets: "205억원", totalLiabilities: "105억원", equity: "100억원" },
    ],
    shareholders: [
      { name: "현기진", ownership: "45%", type: "개인" },
      { name: "현기진(배우자)", ownership: "20%", type: "개인" },
      { name: "벤처캐피탈", ownership: "20%", type: "기관" },
      { name: "기타", ownership: "15%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-11-15",
  },
  {
    id: "8000-7647330",
    name: "동부건설",
    businessNumber: "824-87-03495",
    corpRegNo: "110111-0012345",
    industry: "종합건설업",
    industryCode: "F41",
    mainBusiness: "주택 및 상업시설 건설",
    ceo: "윤진오",
    executives: [
      { name: "윤진오", position: "대표이사", isKeyMan: true },
      { name: "김건설", position: "현장총괄이사", isKeyMan: true },
      { name: "이재무", position: "CFO" },
    ],
    employeeCount: 328,
    foundedYear: 1992,
    headquarters: "서울 강남구 역삼동",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "28억원",
      loanBalance: "58억원",
      fxTransactions: "연 30억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "1,250억원", operatingProfit: "45억원", netProfit: "28억원", totalAssets: "892억원", totalLiabilities: "580억원", equity: "312억원" },
      { year: 2022, revenue: "1,180억원", operatingProfit: "52억원", netProfit: "35억원", totalAssets: "845억원", totalLiabilities: "542억원", equity: "303억원" },
      { year: 2021, revenue: "1,050억원", operatingProfit: "48억원", netProfit: "32억원", totalAssets: "798억원", totalLiabilities: "510억원", equity: "288억원" },
    ],
    shareholders: [
      { name: "윤진오", ownership: "52%", type: "개인" },
      { name: "(주)동부홀딩스", ownership: "28%", type: "법인" },
      { name: "기타", ownership: "20%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-10-20",
  },
  {
    id: "4028-1234567",
    name: "전북식품",
    businessNumber: "418-01-55362",
    corpRegNo: "180111-0123456",
    industry: "식품 제조업",
    industryCode: "C10",
    mainBusiness: "김치, 젓갈 등 전통 발효식품 제조 및 수출",
    ceo: "강동구",
    executives: [
      { name: "강동구", position: "대표이사", isKeyMan: true },
      { name: "박민수", position: "생산총괄이사", isKeyMan: true },
      { name: "김영희", position: "재무이사" },
    ],
    employeeCount: 245,
    foundedYear: 1987,
    headquarters: "전북 전주시 덕진구",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "32억원",
      loanBalance: "8억원",
      fxTransactions: "연 120억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "456억원", operatingProfit: "28억원", netProfit: "21억원", totalAssets: "312억원", totalLiabilities: "185억원", equity: "127억원" },
      { year: 2022, revenue: "412억원", operatingProfit: "24억원", netProfit: "18억원", totalAssets: "289억원", totalLiabilities: "172억원", equity: "117억원" },
      { year: 2021, revenue: "378억원", operatingProfit: "21억원", netProfit: "15억원", totalAssets: "265억원", totalLiabilities: "160억원", equity: "105억원" },
    ],
    shareholders: [
      { name: "강동구", ownership: "45%", type: "개인" },
      { name: "강동구(차남)", ownership: "25%", type: "개인" },
      { name: "전북창업투자", ownership: "15%", type: "기관" },
      { name: "기타", ownership: "15%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry"],
    lastReviewed: "2024-09-10",
  },
  {
    id: "6201-2345678",
    name: "광주정밀기계",
    businessNumber: "415-02-96323",
    corpRegNo: "200111-0234567",
    industry: "기계장비 제조업",
    industryCode: "C29",
    mainBusiness: "자동차 부품용 정밀 금형 및 자동화 설비 제조",
    ceo: "강성우",
    executives: [
      { name: "강성우", position: "대표이사", isKeyMan: true },
      { name: "김기술", position: "기술연구소장", isKeyMan: true },
      { name: "정운영", position: "운영이사" },
    ],
    employeeCount: 178,
    foundedYear: 1995,
    headquarters: "광주 광산구 평동산단",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "18억원",
      loanBalance: "5억원",
      fxTransactions: "연 85억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: false,
    },
    financialSnapshots: [
      { year: 2023, revenue: "523억원", operatingProfit: "35억원", netProfit: "26억원", totalAssets: "412억원", totalLiabilities: "268억원", equity: "144억원" },
      { year: 2022, revenue: "489억원", operatingProfit: "31억원", netProfit: "23억원", totalAssets: "385억원", totalLiabilities: "252억원", equity: "133억원" },
      { year: 2021, revenue: "445억원", operatingProfit: "27억원", netProfit: "19억원", totalAssets: "356억원", totalLiabilities: "238억원", equity: "118억원" },
    ],
    shareholders: [
      { name: "강성우", ownership: "52%", type: "개인" },
      { name: "(주)광주기계홀딩스", ownership: "28%", type: "법인" },
      { name: "우리사주조합", ownership: "12%", type: "기관" },
      { name: "기타", ownership: "8%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-08-05",
  },
  {
    id: "4301-3456789",
    name: "삼성전자",
    businessNumber: "124-81-00998",
    corpRegNo: "180211-0345678",
    industry: "의약품 제조업",
    industryCode: "C21",
    mainBusiness: "동물용 의약품 및 사료첨가제 연구개발/제조",
    ceo: "전영현",
    executives: [
      { name: "전영현", position: "대표이사", isKeyMan: true },
      { name: "김연구", position: "R&D센터장", isKeyMan: true },
      { name: "한영업", position: "영업본부장" },
      { name: "조재무", position: "CFO" },
    ],
    employeeCount: 312,
    foundedYear: 2003,
    headquarters: "전북 익산시 왕궁면",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "45억원",
      loanBalance: "25억원",
      fxTransactions: "연 280억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "892억원", operatingProfit: "78억원", netProfit: "58억원", totalAssets: "645억원", totalLiabilities: "385억원", equity: "260억원" },
      { year: 2022, revenue: "765억원", operatingProfit: "62억원", netProfit: "45억원", totalAssets: "578억원", totalLiabilities: "352억원", equity: "226억원" },
      { year: 2021, revenue: "698억원", operatingProfit: "54억원", netProfit: "38억원", totalAssets: "512억원", totalLiabilities: "318억원", equity: "194억원" },
    ],
    shareholders: [
      { name: "전영현", ownership: "38%", type: "개인" },
      { name: "전북벤처투자", ownership: "22%", type: "기관" },
      { name: "농협경제지주", ownership: "18%", type: "법인" },
      { name: "임직원", ownership: "12%", type: "개인" },
      { name: "기타", ownership: "10%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-11-01",
  },
  {
    id: "6701-4567890",
    name: "휴림로봇",
    businessNumber: "109-81-60401",
    corpRegNo: "200311-0456789",
    industry: "전기/가스 공급업",
    industryCode: "D35",
    mainBusiness: "태양광 발전 모듈 및 ESS 시스템 제조/설치",
    ceo: "김봉관",
    executives: [
      { name: "김봉관", position: "대표이사", isKeyMan: true },
      { name: "김설치", position: "시공본부장" },
      { name: "이에너지", position: "사업개발이사", isKeyMan: true },
    ],
    employeeCount: 156,
    foundedYear: 2010,
    headquarters: "전남 나주시 빛가람동",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "12억원",
      loanBalance: "15억원",
      retirementPension: true,
      payrollService: false,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "312억원", operatingProfit: "18억원", netProfit: "12억원", totalAssets: "278억원", totalLiabilities: "195억원", equity: "83억원" },
      { year: 2022, revenue: "345억원", operatingProfit: "22억원", netProfit: "15억원", totalAssets: "256억원", totalLiabilities: "178억원", equity: "78억원" },
      { year: 2021, revenue: "298억원", operatingProfit: "15억원", netProfit: "9억원", totalAssets: "234억원", totalLiabilities: "165억원", equity: "69억원" },
    ],
    shareholders: [
      { name: "김봉관", ownership: "55%", type: "개인" },
      { name: "에너지파트너스(주)", ownership: "25%", type: "법인" },
      { name: "기타", ownership: "20%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-07-20",
  },
];

export const getCorporationById = (id: string): Corporation | undefined => {
  return CORPORATIONS.find(corp => corp.id === id);
};

export const getCorporationByName = (name: string): Corporation | undefined => {
  return CORPORATIONS.find(corp => corp.name === name);
};

export const getCorporationByBusinessNumber = (businessNumber: string): Corporation | undefined => {
  return CORPORATIONS.find(corp => corp.businessNumber === businessNumber);
};

export const getAllCorporations = (): Corporation[] => {
  return CORPORATIONS;
};

// corp_id 형식에서 숫자 ID 추출 (하위 호환성)
export const getNumericId = (corpId: string): string => {
  const parts = corpId.split('-');
  return parts[parts.length - 1] || corpId;
};
