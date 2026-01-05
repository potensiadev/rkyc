// 기업별 가치사슬망 데이터
// 각 기업의 업종 특성에 맞는 공급망, 경쟁사, 수요처 정보

export interface Supplier {
  name: string;
  type: string;  // 원재료, 부품, 서비스 등
  share?: string;  // 조달 비중
  location?: string;
}

export interface Competitor {
  name: string;
  marketShare?: string;
  revenue?: string;
  note?: string;
}

export interface Customer {
  name: string;
  type: string;  // B2B, B2C, 수출 등
  share?: string;  // 매출 비중
}

export interface MacroFactor {
  category: string;  // 정책, 규제, 환경 등
  description: string;
  impact: "positive" | "negative" | "neutral";
}

export interface ValueChain {
  corpId: string;
  industryOverview: string;  // 산업 비즈니스 구조 설명
  businessModel: string;  // B2B/B2C/수출 등 비즈니스 모델
  suppliers: Supplier[];
  competitors: Competitor[];
  customers: Customer[];
  macroFactors: MacroFactor[];
}

export const VALUE_CHAINS: ValueChain[] = [
  // 엠케이전자 (C26 - 전자부품 제조업)
  {
    corpId: "8001-3719240",
    industryOverview: `전자부품 제조업은 반도체, 디스플레이, 2차전지 등 첨단 산업의 핵심 공급망을 구성합니다.
국내 전자부품 시장은 대기업 중심의 수직계열화와 중소 전문업체의 니치마켓 전략이 공존하는 구조입니다.
글로벌 공급망 재편으로 국내 소부장(소재·부품·장비) 업체들의 기술 내재화가 가속화되고 있으며,
특히 반도체 후공정 및 패키징 분야에서 국내 업체들의 경쟁력이 강화되고 있습니다.`,
    businessModel: "B2B 중심 / 대기업 납품 + 해외 수출(40%)",
    suppliers: [
      { name: "삼성SDI", type: "소재(실리콘웨이퍼)", share: "25%", location: "국내" },
      { name: "SKC", type: "화학소재(PI필름)", share: "20%", location: "국내" },
      { name: "신에츠화학", type: "실리콘계 소재", share: "15%", location: "일본" },
      { name: "듀폰코리아", type: "절연소재", share: "12%", location: "미국계" },
      { name: "국내 중소협력사", type: "금속부품/PCB", share: "28%", location: "국내" },
    ],
    competitors: [
      { name: "삼성전기", marketShare: "32%", revenue: "8.2조원", note: "업계 1위, 대기업" },
      { name: "LG이노텍", marketShare: "24%", revenue: "6.8조원", note: "업계 2위, 대기업" },
      { name: "대덕전자", marketShare: "8%", revenue: "1.2조원", note: "PCB 전문" },
      { name: "심텍", marketShare: "5%", revenue: "8,500억원", note: "반도체 기판" },
      { name: "엠케이전자", marketShare: "0.2%", revenue: "320억원", note: "당사" },
    ],
    customers: [
      { name: "삼성전자", type: "B2B(대기업)", share: "35%" },
      { name: "SK하이닉스", type: "B2B(대기업)", share: "25%" },
      { name: "해외 EMS업체", type: "수출(중국/동남아)", share: "25%" },
      { name: "국내 중소 전자업체", type: "B2B(중소기업)", share: "15%" },
    ],
    macroFactors: [
      { category: "정책", description: "소부장 특별법 시행으로 R&D 세액공제 확대 및 금융지원 강화", impact: "positive" },
      { category: "규제", description: "EU RoHS 규제 강화로 친환경 소재 전환 필요", impact: "negative" },
      { category: "환경", description: "글로벌 반도체 공급망 재편(미-중 갈등)으로 국내 수요 증가 기대", impact: "positive" },
      { category: "기술", description: "AI 반도체 수요 급증으로 고부가 패키징 기술 수요 확대", impact: "positive" },
    ],
  },

  // 동부건설 (F41 - 종합건설업)
  {
    corpId: "8000-7647330",
    industryOverview: `건설업은 주거용, 상업용, 산업용 시설물의 건축과 토목 인프라 구축을 담당하는 기간산업입니다.
국내 건설시장은 대형 종합건설사와 전문건설사의 계층적 구조로 운영되며,
PF(프로젝트 파이낸싱) 사업과 공공발주 사업이 주요 수주 채널입니다.
최근 고금리와 부동산 경기 침체로 PF 부실 리스크가 산업 전반의 불확실성을 높이고 있습니다.`,
    businessModel: "B2B + B2C / PF사업(55%) + 공공입찰(30%) + 재개발(15%)",
    suppliers: [
      { name: "포스코건재", type: "철강재(H빔/철근)", share: "22%", location: "국내" },
      { name: "동양시멘트", type: "레미콘/시멘트", share: "18%", location: "국내" },
      { name: "한샘", type: "마감재/인테리어", share: "12%", location: "국내" },
      { name: "두산밥캣", type: "중장비 임대", share: "8%", location: "국내" },
      { name: "협력 전문건설사", type: "하도급(설비/전기)", share: "40%", location: "국내" },
    ],
    competitors: [
      { name: "삼성물산 건설", marketShare: "8.5%", revenue: "15조원", note: "업계 1위, 대기업" },
      { name: "현대건설", marketShare: "7.8%", revenue: "13조원", note: "업계 2위" },
      { name: "GS건설", marketShare: "5.2%", revenue: "9조원", note: "업계 5위" },
      { name: "호반건설", marketShare: "2.1%", revenue: "3.5조원", note: "중견 아파트 특화" },
      { name: "동부건설", marketShare: "0.7%", revenue: "1,250억원", note: "당사" },
    ],
    customers: [
      { name: "시행사(PF사업)", type: "B2B(시행사)", share: "55%" },
      { name: "공공기관(LH/SH)", type: "B2B(공공)", share: "25%" },
      { name: "개인 수분양자", type: "B2C(분양)", share: "15%" },
      { name: "기업체(상업시설)", type: "B2B(민간)", share: "5%" },
    ],
    macroFactors: [
      { category: "금융", description: "고금리 지속으로 PF 사업성 악화 및 자금조달 비용 상승", impact: "negative" },
      { category: "정책", description: "1기 신도시 재건축 규제 완화로 수도권 재개발 사업 기회", impact: "positive" },
      { category: "규제", description: "건설안전특별법 시행으로 안전관리비용 증가", impact: "negative" },
      { category: "환경", description: "탄소중립 정책에 따른 친환경 건축 수요 증가(그린리모델링)", impact: "positive" },
    ],
  },

  // 전북식품 (C10 - 식품 제조업)
  {
    corpId: "4028-1234567",
    industryOverview: `발효식품 산업은 김치, 젓갈, 장류 등 전통 가공식품을 제조하는 산업으로,
원료 조달부터 발효·숙성, 포장, 냉장 유통까지 연결된 네트워크형 가치사슬이 구성되어 있습니다.
산업의 특성상 '발효'라는 요소에서 비롯됩니다. 발효식품은 시간이 지남에 따라 품질이 계속 변화하기 때문에,
수율을 유지하면서도 원가 표준화를 유지하며서도 품질과 원가통제는 표준화에 따라 품위 리스크와 수익성이 크게 달라집니다.`,
    businessModel: "B2B(60%) + B2C(15%) + 수출(25%) / 대형마트 납품 + 해외 수출",
    suppliers: [
      { name: "전북 농협", type: "배추/고춧가루", share: "35%", location: "전북" },
      { name: "충남 수산협동조합", type: "젓갈 원료", share: "20%", location: "충남" },
      { name: "영광농협", type: "소금/천일염", share: "10%", location: "전남" },
      { name: "CJ프레시웨이", type: "포장재/자재", share: "15%", location: "국내" },
      { name: "영동농협", type: "마늘/파", share: "20%", location: "경북" },
    ],
    competitors: [
      { name: "CJ제일제당", marketShare: "28%", revenue: "2.5조원(식품사업)", note: "업계 1위, 대기업" },
      { name: "대상(청정원)", marketShare: "22%", revenue: "1.8조원", note: "업계 2위" },
      { name: "풀무원", marketShare: "12%", revenue: "8,500억원", note: "김치 특화" },
      { name: "한울(종가집)", marketShare: "8%", revenue: "3,200억원", note: "김치 특화" },
      { name: "전북식품", marketShare: "0.5%", revenue: "456억원", note: "당사" },
    ],
    customers: [
      { name: "이마트/롯데마트", type: "B2B(대형유통)", share: "35%" },
      { name: "CJ올리브영/쿠팡", type: "B2C(온라인)", share: "15%" },
      { name: "미국/일본 수입업체", type: "수출", share: "25%" },
      { name: "급식업체/식자재마트", type: "B2B(외식)", share: "25%" },
    ],
    macroFactors: [
      { category: "환경", description: "이상기후로 배추 작황 불안정, 원재료 가격 변동성 확대", impact: "negative" },
      { category: "정책", description: "K-푸드 해외 홍보 지원으로 수출 확대 기회", impact: "positive" },
      { category: "소비", description: "1인 가구 증가로 소포장 간편식 수요 증가", impact: "positive" },
      { category: "규제", description: "식품표시법 강화로 라벨링 비용 증가", impact: "negative" },
    ],
  },

  // 광주정밀기계 (C29 - 기계장비 제조업)
  {
    corpId: "6201-2345678",
    industryOverview: `기계장비 제조업은 자동차, 전자, 조선 등 제조업의 핵심 생산설비를 공급하는 산업입니다.
특히 자동차 부품용 정밀 금형 분야는 높은 기술력과 품질 관리 역량이 필요한 고부가가치 산업으로,
국내 주요 완성차 업체와의 장기 공급 계약을 통해 안정적인 매출 기반을 확보하는 것이 중요합니다.
최근 전기차 전환으로 기존 내연기관 부품 수요는 감소하나, 배터리 케이스 등 신규 수요가 발생하고 있습니다.`,
    businessModel: "B2B 전문 / 완성차 OEM(70%) + Tier1 부품사(20%) + 수출(10%)",
    suppliers: [
      { name: "포스코", type: "특수강/금형강", share: "30%", location: "국내" },
      { name: "두산공작기계", type: "CNC 설비", share: "15%", location: "국내" },
      { name: "미쓰비시소재", type: "초경합금공구", share: "12%", location: "일본" },
      { name: "화낙코리아", type: "로봇/제어장치", share: "18%", location: "일본계" },
      { name: "국내 가공협력사", type: "2차 가공", share: "25%", location: "국내" },
    ],
    competitors: [
      { name: "현대위아", marketShare: "15%", revenue: "8.5조원", note: "업계 1위, 대기업" },
      { name: "두산공작기계", marketShare: "12%", revenue: "1.2조원", note: "공작기계 특화" },
      { name: "태성정밀", marketShare: "3%", revenue: "2,800억원", note: "금형 특화 중견" },
      { name: "신영정밀", marketShare: "2%", revenue: "1,500억원", note: "자동차금형" },
      { name: "광주정밀기계", marketShare: "0.3%", revenue: "523억원", note: "당사" },
    ],
    customers: [
      { name: "현대자동차그룹", type: "B2B(OEM)", share: "45%" },
      { name: "기아자동차", type: "B2B(OEM)", share: "25%" },
      { name: "현대모비스/만도", type: "B2B(Tier1)", share: "20%" },
      { name: "중국/베트남 수출", type: "수출", share: "10%" },
    ],
    macroFactors: [
      { category: "기술", description: "전기차 전환 가속화로 내연기관 금형 수요 감소, 배터리 케이스 금형 수요 증가", impact: "neutral" },
      { category: "정책", description: "뿌리산업 육성정책으로 설비투자 세액공제 확대", impact: "positive" },
      { category: "환경", description: "탄소중립 정책에 따른 친환경 설비 전환 압박", impact: "negative" },
      { category: "글로벌", description: "글로벌 공급망 재편으로 국내 생산 회귀 수요 기대", impact: "positive" },
    ],
  },

  // 익산바이오텍 (C21 - 의약품 제조업) - 데이터상 '삼성전자'로 되어있지만 실제는 바이오텍
  {
    corpId: "4301-3456789",
    industryOverview: `동물용 의약품 산업은 축산업 및 반려동물 시장의 성장과 함께 꾸준한 성장세를 보이고 있습니다.
특히 사료첨가제 시장은 항생제 사용 규제 강화로 인해 천연 대체재 및 프로바이오틱스 수요가 급증하고 있습니다.
R&D 투자가 중요한 산업 특성상 기술력을 갖춘 중견기업들이 니치마켓에서 경쟁력을 확보하고 있으며,
해외 수출을 통한 성장 전략이 핵심입니다.`,
    businessModel: "B2B 중심 / 축산농가(40%) + 사료회사(35%) + 수출(25%)",
    suppliers: [
      { name: "바스프코리아", type: "원료의약품(API)", share: "25%", location: "독일계" },
      { name: "대한약품공업", type: "첨가제/부형제", share: "15%", location: "국내" },
      { name: "녹십자수의약품", type: "원료", share: "12%", location: "국내" },
      { name: "DSM뉴트리션", type: "비타민/영양제 원료", share: "20%", location: "네덜란드계" },
      { name: "국내 화학원료사", type: "기초화학원료", share: "28%", location: "국내" },
    ],
    competitors: [
      { name: "녹십자수의약품", marketShare: "25%", revenue: "4,500억원", note: "업계 1위" },
      { name: "동방", marketShare: "18%", revenue: "3,200억원", note: "업계 2위" },
      { name: "우진비앤지", marketShare: "12%", revenue: "2,100억원", note: "사료첨가제 특화" },
      { name: "고려비엔피", marketShare: "8%", revenue: "1,400억원", note: "동물백신" },
      { name: "익산바이오텍", marketShare: "5%", revenue: "892억원", note: "당사" },
    ],
    customers: [
      { name: "대형 축산농가", type: "B2B(축산)", share: "40%" },
      { name: "팜스코/CJ사료", type: "B2B(사료회사)", share: "35%" },
      { name: "동남아/중동 수출", type: "수출", share: "20%" },
      { name: "동물병원", type: "B2B(의료)", share: "5%" },
    ],
    macroFactors: [
      { category: "규제", description: "항생제 사용 금지 정책 강화로 대체재 수요 급증", impact: "positive" },
      { category: "시장", description: "반려동물 시장 성장(펫코노미)으로 프리미엄 제품 수요 증가", impact: "positive" },
      { category: "환경", description: "AI(조류독감) 발생 시 가축 살처분으로 일시적 매출 감소 리스크", impact: "negative" },
      { category: "글로벌", description: "K-바이오 성장으로 해외 수출 확대 기회", impact: "positive" },
    ],
  },

  // 나주태양에너지 (D35 - 전기/가스 공급업) - 데이터상 '휴림로봇'
  {
    corpId: "6701-4567890",
    industryOverview: `태양광 발전 산업은 정부의 재생에너지 정책과 ESG 투자 확대로 급성장하고 있는 분야입니다.
태양광 모듈 제조부터 ESS(에너지저장장치) 시스템, 발전소 EPC(설계·조달·시공)까지
수직계열화된 기업들이 경쟁력을 확보하고 있습니다.
최근 중국산 저가 모듈의 공세와 보조금 정책 변화가 산업의 주요 리스크 요인입니다.`,
    businessModel: "B2B + B2G / EPC사업(50%) + 모듈판매(30%) + O&M(20%)",
    suppliers: [
      { name: "OCI", type: "폴리실리콘", share: "25%", location: "국내" },
      { name: "한화솔루션", type: "태양전지셀", share: "30%", location: "국내" },
      { name: "삼성SDI", type: "ESS 배터리", share: "20%", location: "국내" },
      { name: "중국 LONGi", type: "모듈(저가)", share: "15%", location: "중국" },
      { name: "국내 부품사", type: "인버터/구조물", share: "10%", location: "국내" },
    ],
    competitors: [
      { name: "한화솔루션", marketShare: "35%", revenue: "8.5조원(신재생)", note: "업계 1위, 대기업" },
      { name: "OCI", marketShare: "15%", revenue: "2.8조원", note: "폴리실리콘 특화" },
      { name: "신성이엔지", marketShare: "8%", revenue: "6,500억원", note: "EPC 특화" },
      { name: "에스에너지", marketShare: "5%", revenue: "3,200억원", note: "모듈 제조" },
      { name: "나주태양에너지", marketShare: "0.4%", revenue: "312억원", note: "당사" },
    ],
    customers: [
      { name: "한국전력/발전공기업", type: "B2G(공공)", share: "35%" },
      { name: "기업 자가발전", type: "B2B(RE100)", share: "30%" },
      { name: "농어촌 태양광사업자", type: "B2B(농촌)", share: "25%" },
      { name: "해외 EPC프로젝트", type: "수출", share: "10%" },
    ],
    macroFactors: [
      { category: "정책", description: "RE100 의무화 확대로 기업 자가발전 수요 급증", impact: "positive" },
      { category: "경쟁", description: "중국산 저가 모듈 덤핑으로 가격 경쟁 심화", impact: "negative" },
      { category: "금융", description: "고금리로 인한 태양광 PF 사업성 악화", impact: "negative" },
      { category: "기술", description: "ESS 화재 안전규제 강화로 프리미엄 제품 경쟁력 확보 기회", impact: "positive" },
    ],
  },
];

// 기업 ID로 가치사슬망 조회
export const getValueChainByCorpId = (corpId: string): ValueChain | undefined => {
  return VALUE_CHAINS.find(vc => vc.corpId === corpId);
};

// 모든 가치사슬망 조회
export const getAllValueChains = (): ValueChain[] => {
  return VALUE_CHAINS;
};
