// 중앙화된 기업 마스터 데이터
// 전북/광주 지역 대형 법인 고객 기반의 현실적인 데이터
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
  id: string;
  name: string;
  businessNumber: string;
  industry: string;
  industryCode: string;
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

export const CORPORATIONS: Corporation[] = [
  {
    id: "1",
    name: "전북식품",
    businessNumber: "402-81-12345",
    industry: "식품제조업",
    industryCode: "10790",
    mainBusiness: "김치, 젓갈 등 전통 발효식품 제조 및 수출",
    ceo: "김정호",
    executives: [
      { name: "김정호", position: "대표이사", isKeyMan: true },
      { name: "박민수", position: "생산총괄이사", isKeyMan: true },
      { name: "이영희", position: "재무이사" },
    ],
    employeeCount: 245,
    foundedYear: 1987,
    headquarters: "전북 전주시 덕진구",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "32억원",
      loanBalance: "85억원",
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
      { name: "김정호", ownership: "45%", type: "개인" },
      { name: "김영수(차남)", ownership: "25%", type: "개인" },
      { name: "전북창업투자", ownership: "15%", type: "기관" },
      { name: "기타", ownership: "15%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry"],
    lastReviewed: "2024-12-20",
  },
  {
    id: "2",
    name: "광주정밀기계",
    businessNumber: "410-81-23456",
    industry: "기계장비제조업",
    industryCode: "29199",
    mainBusiness: "자동차 부품용 정밀 금형 및 자동화 설비 제조",
    ceo: "이상훈",
    executives: [
      { name: "이상훈", position: "대표이사", isKeyMan: true },
      { name: "최기술", position: "기술연구소장", isKeyMan: true },
      { name: "정운영", position: "운영이사" },
    ],
    employeeCount: 178,
    foundedYear: 1995,
    headquarters: "광주 광산구 평동산단",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "18억원",
      loanBalance: "120억원",
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
      { name: "이상훈", ownership: "52%", type: "개인" },
      { name: "(주)광주기계홀딩스", ownership: "28%", type: "법인" },
      { name: "우리사주조합", ownership: "12%", type: "기관" },
      { name: "기타", ownership: "8%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-12-19",
  },
  {
    id: "3",
    name: "익산바이오텍",
    businessNumber: "403-81-34567",
    industry: "의약품제조업",
    industryCode: "21210",
    mainBusiness: "동물용 의약품 및 사료첨가제 연구개발·제조",
    ceo: "박성민",
    executives: [
      { name: "박성민", position: "대표이사", isKeyMan: true },
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
      loanBalance: "210억원",
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
      { name: "박성민", ownership: "38%", type: "개인" },
      { name: "전북벤처투자", ownership: "22%", type: "기관" },
      { name: "농협경제지주", ownership: "18%", type: "법인" },
      { name: "임직원", ownership: "12%", type: "개인" },
      { name: "기타", ownership: "10%", type: "개인" },
    ],
    recentSignalTypes: ["direct"],
    lastReviewed: "2024-12-18",
  },
  {
    id: "4",
    name: "나주태양에너지",
    businessNumber: "411-81-45678",
    industry: "전기장비제조업",
    industryCode: "28420",
    mainBusiness: "태양광 발전 모듈 및 ESS 시스템 제조·설치",
    ceo: "정태양",
    executives: [
      { name: "정태양", position: "대표이사", isKeyMan: true },
      { name: "김설치", position: "시공본부장" },
      { name: "이에너지", position: "사업개발이사", isKeyMan: true },
    ],
    employeeCount: 156,
    foundedYear: 2010,
    headquarters: "전남 나주시 빛가람동",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "12억원",
      loanBalance: "95억원",
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
      { name: "정태양", ownership: "55%", type: "개인" },
      { name: "에너지파트너스(주)", ownership: "25%", type: "법인" },
      { name: "기타", ownership: "20%", type: "개인" },
    ],
    recentSignalTypes: ["industry", "environment"],
    lastReviewed: "2024-12-22",
  },
  {
    id: "5",
    name: "군산조선기자재",
    businessNumber: "404-81-56789",
    industry: "선박부품제조업",
    industryCode: "31114",
    mainBusiness: "선박용 엔진 부품 및 의장품 제조",
    ceo: "최해양",
    executives: [
      { name: "최해양", position: "대표이사", isKeyMan: true },
      { name: "강품질", position: "품질관리이사", isKeyMan: true },
      { name: "윤생산", position: "생산이사" },
    ],
    employeeCount: 423,
    foundedYear: 1982,
    headquarters: "전북 군산시 소룡동",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "28억원",
      loanBalance: "180억원",
      fxTransactions: "연 420억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "1,245억원", operatingProfit: "85억원", netProfit: "62억원", totalAssets: "892억원", totalLiabilities: "578억원", equity: "314억원" },
      { year: 2022, revenue: "1,123억원", operatingProfit: "72억원", netProfit: "51억원", totalAssets: "845억원", totalLiabilities: "552억원", equity: "293억원" },
      { year: 2021, revenue: "978억원", operatingProfit: "58억원", netProfit: "38억원", totalAssets: "798억원", totalLiabilities: "528억원", equity: "270억원" },
    ],
    shareholders: [
      { name: "(주)한국조선해양", ownership: "35%", type: "법인" },
      { name: "최해양", ownership: "32%", type: "개인" },
      { name: "산업은행", ownership: "18%", type: "기관" },
      { name: "기타", ownership: "15%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry"],
    lastReviewed: "2024-12-21",
  },
  {
    id: "6",
    name: "무안물류",
    businessNumber: "412-81-67890",
    industry: "창고및운송업",
    industryCode: "52102",
    mainBusiness: "항만 물류 및 냉장·냉동 창고 운영",
    ceo: "홍물류",
    executives: [
      { name: "홍물류", position: "대표이사", isKeyMan: true },
      { name: "배운송", position: "운영본부장" },
      { name: "임창고", position: "시설관리이사" },
    ],
    employeeCount: 89,
    foundedYear: 1998,
    headquarters: "전남 무안군 삼향읍",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "8억원",
      loanBalance: "65억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: false,
    },
    financialSnapshots: [
      { year: 2023, revenue: "187억원", operatingProfit: "15억원", netProfit: "10억원", totalAssets: "156억원", totalLiabilities: "98억원", equity: "58억원" },
      { year: 2022, revenue: "172억원", operatingProfit: "13억원", netProfit: "8억원", totalAssets: "145억원", totalLiabilities: "92억원", equity: "53억원" },
      { year: 2021, revenue: "158억원", operatingProfit: "11억원", netProfit: "6억원", totalAssets: "138억원", totalLiabilities: "88억원", equity: "50억원" },
    ],
    shareholders: [
      { name: "홍물류", ownership: "68%", type: "개인" },
      { name: "홍물류(배우자)", ownership: "22%", type: "개인" },
      { name: "기타", ownership: "10%", type: "개인" },
    ],
    recentSignalTypes: ["environment"],
    lastReviewed: "2024-12-20",
  },
  {
    id: "7",
    name: "정읍농산",
    businessNumber: "405-81-78901",
    industry: "농업회사법인",
    industryCode: "01110",
    mainBusiness: "친환경 유기농 쌀·잡곡 생산 및 가공",
    ceo: "농대표",
    executives: [
      { name: "농대표", position: "대표이사", isKeyMan: true },
      { name: "김영농", position: "생산이사" },
    ],
    employeeCount: 45,
    foundedYear: 2008,
    headquarters: "전북 정읍시 신태인읍",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "5억원",
      loanBalance: "28억원",
      retirementPension: false,
      payrollService: true,
      corporateCard: false,
    },
    financialSnapshots: [
      { year: 2023, revenue: "78억원", operatingProfit: "6억원", netProfit: "4억원", totalAssets: "65억원", totalLiabilities: "38억원", equity: "27억원" },
      { year: 2022, revenue: "72억원", operatingProfit: "5억원", netProfit: "3억원", totalAssets: "58억원", totalLiabilities: "35억원", equity: "23억원" },
      { year: 2021, revenue: "65억원", operatingProfit: "4억원", netProfit: "2억원", totalAssets: "52억원", totalLiabilities: "32억원", equity: "20억원" },
    ],
    shareholders: [
      { name: "농대표", ownership: "60%", type: "개인" },
      { name: "정읍농협", ownership: "25%", type: "기관" },
      { name: "조합원", ownership: "15%", type: "개인" },
    ],
    recentSignalTypes: ["industry"],
    lastReviewed: "2024-12-22",
  },
  {
    id: "8",
    name: "광주모빌리티",
    businessNumber: "413-81-89012",
    industry: "자동차부품제조업",
    industryCode: "30320",
    mainBusiness: "전기차용 배터리 팩 및 BMS 제조",
    ceo: "차모빌",
    executives: [
      { name: "차모빌", position: "대표이사", isKeyMan: true },
      { name: "전기술", position: "CTO", isKeyMan: true },
      { name: "배터리", position: "생산본부장" },
      { name: "송영업", position: "영업이사" },
    ],
    employeeCount: 287,
    foundedYear: 2015,
    headquarters: "광주 광산구 첨단과기로",
    bankRelationship: {
      hasRelationship: true,
      depositBalance: "52억원",
      loanBalance: "280억원",
      fxTransactions: "연 180억원",
      retirementPension: true,
      payrollService: true,
      corporateCard: true,
    },
    financialSnapshots: [
      { year: 2023, revenue: "687억원", operatingProfit: "45억원", netProfit: "32억원", totalAssets: "512억원", totalLiabilities: "345억원", equity: "167억원" },
      { year: 2022, revenue: "523억원", operatingProfit: "28억원", netProfit: "18억원", totalAssets: "425억원", totalLiabilities: "298억원", equity: "127억원" },
      { year: 2021, revenue: "345억원", operatingProfit: "12억원", netProfit: "5억원", totalAssets: "356억원", totalLiabilities: "268억원", equity: "88억원" },
    ],
    shareholders: [
      { name: "차모빌", ownership: "42%", type: "개인" },
      { name: "현대차증권PEF", ownership: "28%", type: "기관" },
      { name: "광주테크노파크", ownership: "15%", type: "기관" },
      { name: "임직원", ownership: "10%", type: "개인" },
      { name: "기타", ownership: "5%", type: "개인" },
    ],
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-12-21",
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
