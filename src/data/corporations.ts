// 중앙화된 기업 마스터 데이터
// 모든 화면에서 동일한 기업 정보를 사용합니다.

export interface Corporation {
  id: string;
  name: string;
  businessNumber: string;
  industry: string;
  mainBusiness: string;
  hasLoanRelationship: boolean;
  recentSignalTypes: ("direct" | "industry" | "environment")[];
  lastReviewed: string;
}

export const CORPORATIONS: Corporation[] = [
  {
    id: "1",
    name: "삼성전자",
    businessNumber: "124-81-00998",
    industry: "전자/반도체",
    mainBusiness: "반도체, 스마트폰, 디스플레이 제조 및 판매",
    hasLoanRelationship: true,
    recentSignalTypes: ["direct", "industry"],
    lastReviewed: "2024-12-20",
  },
  {
    id: "2",
    name: "현대자동차",
    businessNumber: "101-81-15555",
    industry: "자동차",
    mainBusiness: "자동차 및 부품 제조, 판매",
    hasLoanRelationship: false,
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-12-19",
  },
  {
    id: "3",
    name: "카카오",
    businessNumber: "120-81-47521",
    industry: "IT/플랫폼",
    mainBusiness: "인터넷 플랫폼 및 디지털 콘텐츠 서비스",
    hasLoanRelationship: false,
    recentSignalTypes: ["direct"],
    lastReviewed: "2024-12-18",
  },
  {
    id: "4",
    name: "LG에너지솔루션",
    businessNumber: "110-81-12345",
    industry: "2차전지",
    mainBusiness: "전기차용 배터리 및 에너지저장장치 제조",
    hasLoanRelationship: true,
    recentSignalTypes: ["industry"],
    lastReviewed: "2024-12-22",
  },
  {
    id: "5",
    name: "네이버",
    businessNumber: "220-81-62517",
    industry: "IT/플랫폼",
    mainBusiness: "인터넷 포털 및 검색 서비스, AI 기술 개발",
    hasLoanRelationship: false,
    recentSignalTypes: ["direct"],
    lastReviewed: "2024-12-21",
  },
  {
    id: "6",
    name: "포스코홀딩스",
    businessNumber: "102-81-45678",
    industry: "철강/소재",
    mainBusiness: "철강 및 2차전지 소재 제조",
    hasLoanRelationship: true,
    recentSignalTypes: ["environment"],
    lastReviewed: "2024-12-20",
  },
  {
    id: "7",
    name: "SK하이닉스",
    businessNumber: "105-81-11111",
    industry: "전자/반도체",
    mainBusiness: "메모리 반도체 제조 및 판매",
    hasLoanRelationship: true,
    recentSignalTypes: ["industry"],
    lastReviewed: "2024-12-22",
  },
  {
    id: "8",
    name: "한국전력공사",
    businessNumber: "120-81-99999",
    industry: "에너지/전력",
    mainBusiness: "전력 생산, 송전, 배전 및 판매",
    hasLoanRelationship: true,
    recentSignalTypes: ["environment"],
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
