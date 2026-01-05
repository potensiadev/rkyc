// 중앙화된 인사이트 메모리 데이터
// Supabase corp 테이블 기준 (seed_v2.sql)
// 과거 사례 참고용 데이터

export interface InsightMemoryEntry {
  corporationId: string;
  corporationName: string;
  similarCaseCount: number;
  impactClassification: "단기" | "중기" | "장기";
  description: string;
}

export const INSIGHT_MEMORY: InsightMemoryEntry[] = [
  {
    corporationId: "8001-3719240",
    corporationName: "엠케이전자",
    similarCaseCount: 3,
    impactClassification: "단기",
    description: "과거 반도체 업황 둔화 시그널은 단기적 매출 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "8000-7647330",
    corporationName: "동부건설",
    similarCaseCount: 5,
    impactClassification: "중기",
    description: "건설업 PF 위기 관련 시그널은 중기적 유동성 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "4028-1234567",
    corporationName: "전북식품",
    similarCaseCount: 2,
    impactClassification: "단기",
    description: "수출 관세 변동 시그널은 단기적 수출 매출에 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "6201-2345678",
    corporationName: "광주정밀기계",
    similarCaseCount: 4,
    impactClassification: "중기",
    description: "자동차 산업 전환 시그널은 중기적 수주 변동과 연관된 사례가 있습니다.",
  },
  {
    corporationId: "4301-3456789",
    corporationName: "익산바이오텍",
    similarCaseCount: 6,
    impactClassification: "장기",
    description: "바이오 규제 강화 시그널은 장기적 R&D 일정에 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "6701-4567890",
    corporationName: "나주태양에너지",
    similarCaseCount: 3,
    impactClassification: "중기",
    description: "신재생에너지 정책 변화 시그널은 중기적 수익성에 영향을 미친 사례가 있습니다.",
  },
];

export const getInsightMemoryByCorporationId = (corporationId: string): InsightMemoryEntry | undefined => {
  return INSIGHT_MEMORY.find(entry => entry.corporationId === corporationId);
};

export const getInsightMemoryByCorporationName = (name: string): InsightMemoryEntry | undefined => {
  return INSIGHT_MEMORY.find(entry => entry.corporationName === name);
};
