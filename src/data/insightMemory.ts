// 중앙화된 인사이트 메모리 데이터
// 과거 사례 참고용 데이터

export interface InsightMemoryEntry {
  corporationId: string;
  similarCaseCount: number;
  impactClassification: "단기" | "중기" | "장기";
  description: string;
}

export const INSIGHT_MEMORY: InsightMemoryEntry[] = [
  {
    corporationId: "1", // 삼성전자
    similarCaseCount: 3,
    impactClassification: "단기",
    description: "과거 유사한 인력 재배치 시그널은 단기적 시장 반응을 보인 사례가 있습니다.",
  },
  {
    corporationId: "2", // 현대자동차
    similarCaseCount: 5,
    impactClassification: "중기",
    description: "자동차 업종의 실적 변동 시그널은 중기적 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "3", // 카카오
    similarCaseCount: 2,
    impactClassification: "중기",
    description: "플랫폼 기업 규제 관련 시그널은 중기적 사업 환경 변화와 연관된 사례가 있습니다.",
  },
  {
    corporationId: "4", // LG에너지솔루션
    similarCaseCount: 4,
    impactClassification: "중기",
    description: "배터리 산업 수요 변화 시그널은 중기적 실적에 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "5", // 네이버
    similarCaseCount: 6,
    impactClassification: "장기",
    description: "AI 관련 인수합병 시그널은 장기적 사업 확장과 연관된 사례가 있습니다.",
  },
  {
    corporationId: "6", // 포스코홀딩스
    similarCaseCount: 3,
    impactClassification: "단기",
    description: "무역 관세 관련 시그널은 단기적 수출 영향을 미친 사례가 있습니다.",
  },
  {
    corporationId: "7", // SK하이닉스
    similarCaseCount: 4,
    impactClassification: "중기",
    description: "반도체 수요 증가 시그널은 중기적 실적 개선과 연관된 사례가 있습니다.",
  },
  {
    corporationId: "8", // 한국전력공사
    similarCaseCount: 2,
    impactClassification: "장기",
    description: "전기요금 정책 변화 시그널은 장기적 수익 구조에 영향을 미친 사례가 있습니다.",
  },
];

export const getInsightMemoryByCorporationId = (corporationId: string): InsightMemoryEntry | undefined => {
  return INSIGHT_MEMORY.find(entry => entry.corporationId === corporationId);
};
