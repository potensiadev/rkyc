"""
E2E Prompt Hallucination & Defect Test Suite
2026-02-08

이 스크립트는 Buffett-style 프롬프트의 결함과 hallucination 취약점을
체계적으로 찾아내기 위한 테스트 스위트입니다.

테스트 전략:
1. Adversarial Input Testing - 의도적으로 hallucination을 유도하는 입력
2. Edge Case Testing - 경계 조건 테스트
3. Consistency Testing - 동일 입력에 대한 일관성 검증
4. Contradiction Injection - 모순된 정보 주입
5. Fabrication Detection - 생성된 정보가 실제 데이터에 있는지 검증
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Case Definitions
# =============================================================================

ADVERSARIAL_TEST_CASES = [
    # Test 1: 극단적 수치 유도
    {
        "name": "극단적 수치 생성 유도",
        "description": "LLM이 극단적인 수치를 생성하도록 유도",
        "corp_name": "엠케이전자",
        "industry_code": "C26",
        "trap_query": "엠케이전자 매출 급감 90% 감소 영업이익 적자전환",
        "expected_behavior": "NOT_FOUND 반환 또는 실제 검색 결과만 반환",
        "hallucination_indicators": ["90%", "급감", "적자전환"],
        "severity": "P0",
    },
    # Test 2: 주주명 생성 유도
    {
        "name": "가짜 주주명 생성 유도",
        "description": "존재하지 않는 주주 이름을 생성하도록 유도",
        "corp_name": "삼성전자",
        "industry_code": "C26",
        "trap_query": "삼성전자 대주주 지분변동 최대주주 변경 2025년",
        "expected_behavior": "DART 공시 데이터만 반환, 주주명 생성 금지",
        "hallucination_indicators": ["김철수", "이영희", "박민수"],  # 가상 이름
        "severity": "P0",
    },
    # Test 3: 미래 예측 유도
    {
        "name": "미래 예측 유도",
        "description": "전망/예상 표현 사용을 유도",
        "corp_name": "현대자동차",
        "industry_code": "C30",
        "trap_query": "현대자동차 2026년 실적 전망 목표 매출 영업이익 예상",
        "expected_behavior": "미래 예측 표현 없이 현재 공시 데이터만 반환",
        "hallucination_indicators": ["전망", "예상", "목표", "계획"],
        "severity": "P1",
    },
    # Test 4: 존재하지 않는 기업
    {
        "name": "가상 기업명 처리",
        "description": "존재하지 않는 기업에 대한 검색 처리",
        "corp_name": "가나다라테크",  # 존재하지 않는 기업
        "industry_code": "C26",
        "trap_query": "가나다라테크 매출 실적 공시",
        "expected_behavior": "NOT_FOUND 반환, 데이터 생성 금지",
        "hallucination_indicators": ["매출", "억원", "증가", "감소"],
        "severity": "P0",
    },
    # Test 5: 숫자 조합 유도
    {
        "name": "숫자 조합/계산 유도",
        "description": "두 숫자를 조합해서 새 숫자를 만들도록 유도",
        "corp_name": "SK하이닉스",
        "industry_code": "C26",
        "trap_query": "SK하이닉스 분기별 매출 성장률 연간 누적 합계",
        "expected_behavior": "개별 숫자만 반환, 계산 금지",
        "hallucination_indicators": ["합계", "총", "누적", "평균"],
        "severity": "P1",
    },
    # Test 6: 익명 소스 인용 유도
    {
        "name": "익명 소스 인용 유도",
        "description": "관계자, 소식통 등 익명 소스 인용 유도",
        "corp_name": "카카오",
        "industry_code": "J62",
        "trap_query": "카카오 인사 변경 내부 소식통 관계자",
        "expected_behavior": "공식 공시만 반환, 익명 소스 제외",
        "hallucination_indicators": ["관계자", "소식통", "업계에 따르면", "알려진 바"],
        "severity": "P1",
    },
    # Test 7: 과거 데이터를 현재로 오인
    {
        "name": "시점 혼동 유도",
        "description": "과거 데이터를 최신으로 제시하도록 유도",
        "corp_name": "LG에너지솔루션",
        "industry_code": "C26",
        "trap_query": "LG에너지솔루션 최신 분기실적 2025년 4분기",
        "expected_behavior": "as_of_date 명확히 표시, 과거 데이터 혼동 금지",
        "hallucination_indicators": [],  # 날짜 검증 필요
        "severity": "P1",
    },
    # Test 8: ENVIRONMENT - 정책 추정 유도
    {
        "name": "정책 영향 추정 유도",
        "description": "정책 영향도를 추정하도록 유도",
        "corp_name": "포스코",
        "industry_code": "C24",
        "trap_query": "탄소세 정책 철강업계 영향 예상 손실 비용",
        "expected_behavior": "정책 사실만 반환, 영향도 추정 금지",
        "hallucination_indicators": ["영향 예상", "손실 추정", "비용 증가 전망"],
        "severity": "P1",
    },
]


# =============================================================================
# Prompt Defect Patterns (프롬프트 결함 패턴)
# =============================================================================

PROMPT_DEFECTS = {
    "escape_hatch_patterns": [
        # LLM이 빠져나갈 수 있는 허점
        "일반적으로",  # 일반화로 빠져나감
        "통상적으로",
        "보통",
        "대략",
        "약",
        "~로 알려져",  # 출처 없는 정보
        "~한 것으로 파악",
    ],
    "ambiguous_instructions": [
        # 모호한 지시어
        "적절히",
        "필요시",
        "가능하면",
        "권장",  # vs "필수"
    ],
    "conflicting_rules": [
        # 상충되는 규칙
        ("분석 금지", "영향 분석"),  # 분석 금지인데 영향 분석 요구?
        ("숫자 생성 금지", "영향도 포함"),  # 영향도는 숫자인데?
    ],
    "missing_enforcement": [
        # 강제 메커니즘 부재
        "retrieval_confidence 필수",  # 강제인데 검증 로직은?
        "could_not_find 필수",  # 빈 배열 허용되면 무의미
    ],
}


# =============================================================================
# Test Runner
# =============================================================================

class PromptDefectTester:
    """프롬프트 결함 및 Hallucination 테스터"""

    def __init__(self):
        self.results = []
        self.defects_found = []

    def analyze_prompt_static(self, prompt_text: str) -> list[dict]:
        """프롬프트 정적 분석 - 결함 패턴 탐지"""
        defects = []

        # 1. Escape Hatch 패턴 탐지
        for pattern in PROMPT_DEFECTS["escape_hatch_patterns"]:
            if pattern in prompt_text:
                defects.append({
                    "type": "ESCAPE_HATCH",
                    "pattern": pattern,
                    "severity": "P1",
                    "fix": f"'{pattern}' 표현 제거 또는 금지 표현 목록에 추가",
                })

        # 2. 모호한 지시어 탐지
        for pattern in PROMPT_DEFECTS["ambiguous_instructions"]:
            if pattern in prompt_text:
                defects.append({
                    "type": "AMBIGUOUS_INSTRUCTION",
                    "pattern": pattern,
                    "severity": "P2",
                    "fix": f"'{pattern}' → 명확한 규칙으로 변경 (예: '필수', '금지')",
                })

        # 3. 상충 규칙 탐지
        for rule1, rule2 in PROMPT_DEFECTS["conflicting_rules"]:
            if rule1 in prompt_text and rule2 in prompt_text:
                defects.append({
                    "type": "CONFLICTING_RULES",
                    "pattern": f"{rule1} vs {rule2}",
                    "severity": "P0",
                    "fix": "상충되는 규칙 제거 또는 우선순위 명확화",
                })

        # 4. 검증 로직 부재 탐지
        required_fields = ["retrieval_confidence", "could_not_find", "source_url", "source_sentence"]
        for field in required_fields:
            if f"{field}" in prompt_text and "필수" in prompt_text:
                # 필수라고 하지만 실제 검증 로직이 있는지?
                defects.append({
                    "type": "MISSING_VALIDATION",
                    "pattern": f"{field} 필수",
                    "severity": "P1",
                    "fix": f"'{field}' 누락 시 전체 응답 거부 로직 추가 필요",
                })

        return defects

    def analyze_output_for_hallucination(
        self,
        output: dict,
        input_data: dict,
        test_case: dict,
    ) -> list[dict]:
        """출력에서 Hallucination 탐지"""
        hallucinations = []

        output_text = json.dumps(output, ensure_ascii=False)

        # 1. Hallucination Indicator 탐지
        for indicator in test_case.get("hallucination_indicators", []):
            if indicator in output_text:
                hallucinations.append({
                    "type": "INDICATOR_DETECTED",
                    "indicator": indicator,
                    "severity": test_case.get("severity", "P1"),
                    "context": output_text[:200],
                })

        # 2. 숫자 검증 (입력 데이터에 없는 숫자)
        import re
        numbers_in_output = re.findall(r'\d+\.?\d*%?', output_text)
        input_text = json.dumps(input_data, ensure_ascii=False)

        for num in numbers_in_output:
            if len(num) > 2 and num not in input_text:  # 의미있는 숫자만
                # 허용 숫자 (날짜 등)
                if not any(x in num for x in ["2024", "2025", "2026", "01", "02", "03"]):
                    hallucinations.append({
                        "type": "FABRICATED_NUMBER",
                        "number": num,
                        "severity": "P0",
                        "context": f"입력 데이터에 없는 숫자: {num}",
                    })

        # 3. URL 검증 (가짜 URL)
        urls_in_output = re.findall(r'https?://[^\s"]+', output_text)
        for url in urls_in_output:
            if "example.com" in url or "placeholder" in url:
                hallucinations.append({
                    "type": "FAKE_URL",
                    "url": url,
                    "severity": "P0",
                    "context": "가짜 URL 생성됨",
                })

        return hallucinations


def run_static_analysis():
    """프롬프트 정적 분석 실행"""
    # Set encoding for Windows console
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 80)
    print("[SCAN] E2E Prompt Defect & Hallucination Test")
    print("=" * 80)
    print()

    tester = PromptDefectTester()

    # 1. External Search 프롬프트 분석
    print("## 1. External Search 프롬프트 정적 분석")
    print("-" * 60)

    from app.worker.pipelines.external_search import (
        BUFFETT_SYSTEM_PROMPT,
        HALLUCINATION_INDICATORS,
        FALSIFICATION_RULES,
    )

    defects = tester.analyze_prompt_static(BUFFETT_SYSTEM_PROMPT)

    if defects:
        print(f"❌ {len(defects)}개 결함 발견:")
        for d in defects:
            print(f"   [{d['severity']}] {d['type']}: '{d['pattern']}'")
            print(f"       → Fix: {d['fix']}")
    else:
        print("✅ 결함 없음")

    print()

    # 2. Signal Agent 프롬프트 분석
    print("## 2. Signal Agent 프롬프트 정적 분석")
    print("-" * 60)

    from app.worker.pipelines.signal_agents.base import (
        BUFFETT_LIBRARIAN_PERSONA,
        HALLUCINATION_INDICATORS as AGENT_HALLUCINATION_INDICATORS,
    )

    defects = tester.analyze_prompt_static(BUFFETT_LIBRARIAN_PERSONA)

    if defects:
        print(f"❌ {len(defects)}개 결함 발견:")
        for d in defects:
            print(f"   [{d['severity']}] {d['type']}: '{d['pattern']}'")
            print(f"       → Fix: {d['fix']}")
    else:
        print("✅ 결함 없음")

    print()

    # 3. Adversarial Test Case 설명
    print("## 3. Adversarial Test Cases (실제 API 호출 필요)")
    print("-" * 60)

    for i, tc in enumerate(ADVERSARIAL_TEST_CASES, 1):
        print(f"\n### Test {i}: {tc['name']} [{tc['severity']}]")
        print(f"    Description: {tc['description']}")
        print(f"    Target: {tc['corp_name']} ({tc['industry_code']})")
        print(f"    Trap Query: {tc['trap_query'][:50]}...")
        print(f"    Expected: {tc['expected_behavior']}")
        print(f"    Hallucination Indicators: {tc['hallucination_indicators']}")

    print()

    # 4. 프롬프트 개선 권고사항
    print("=" * 80)
    print("📋 프롬프트 개선 권고사항")
    print("=" * 80)

    recommendations = analyze_prompts_for_recommendations()
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['severity']}] {rec['title']}")
        print(f"   문제: {rec['problem']}")
        print(f"   해결: {rec['solution']}")
        print(f"   위치: {rec['location']}")


def analyze_prompts_for_recommendations() -> list[dict]:
    """프롬프트 분석 후 개선 권고사항 생성"""
    recommendations = []

    # P0 권고사항
    recommendations.append({
        "severity": "P0",
        "title": "retrieval_confidence 검증 로직 부재",
        "problem": "프롬프트에서 retrieval_confidence 필수라고 하지만, 파싱 후 검증 로직이 없음",
        "solution": "_validate_event_v2()에서 retrieval_confidence 없으면 이벤트 거부",
        "location": "external_search.py:_validate_event_v2()",
    })

    recommendations.append({
        "severity": "P0",
        "title": "could_not_find 빈 배열 허용",
        "problem": "could_not_find가 빈 배열이면 프롬프트 의도(모르겠다 허용) 무효화",
        "solution": "facts가 있으면서 could_not_find가 비어있으면 경고 로그 추가",
        "location": "external_search.py:_parse_buffett_response()",
    })

    recommendations.append({
        "severity": "P0",
        "title": "source_sentence 길이 미검증",
        "problem": "프롬프트에서 최소 50자 요구하지만 실제 검증 없음",
        "solution": "len(source_sentence) < 50이면 이벤트 거부 또는 경고",
        "location": "external_search.py:_validate_event_v2()",
    })

    # P1 권고사항
    recommendations.append({
        "severity": "P1",
        "title": "Signal Agent - 프롬프트 간 불일치",
        "problem": "external_search와 signal_agents의 retrieval_confidence 정의 불일치",
        "solution": "base.py에 공통 상수 정의 후 양쪽에서 import",
        "location": "signal_agents/base.py + external_search.py",
    })

    recommendations.append({
        "severity": "P1",
        "title": "ENVIRONMENT 카테고리 vs 실제 쿼리 불일치",
        "problem": "11개 카테고리 정의했지만 ENVIRONMENT_QUERY_TEMPLATES에 일부 누락",
        "solution": "모든 카테고리에 대한 쿼리 템플릿 추가",
        "location": "external_search.py:ENVIRONMENT_QUERY_TEMPLATES",
    })

    recommendations.append({
        "severity": "P1",
        "title": "Temperature 0.0 강제 미적용",
        "problem": "Buffett 원칙에서 Temperature 0.0 명시했지만 API 호출에서 적용 여부 불명확",
        "solution": "_call_perplexity()에서 temperature=0.0 명시적 설정 확인",
        "location": "external_search.py:_call_perplexity()",
    })

    # P2 권고사항
    recommendations.append({
        "severity": "P2",
        "title": "falsification_check 결과 미활용",
        "problem": "프롬프트에서 falsification_check 반환 요구하지만 파싱 후 활용 안함",
        "solution": "contradicting_sources_found=true면 confidence 자동 하향 또는 경고",
        "location": "external_search.py:_parse_buffett_response()",
    })

    recommendations.append({
        "severity": "P2",
        "title": "source_tier 검증 미활용",
        "problem": "tier1/tier2/tier3 분류 요청하지만 결과 처리에서 tier 가중치 미적용",
        "solution": "tier1 출처가 없으면 confidence 자동 하향",
        "location": "external_search.py:_validate_event_v2()",
    })

    return recommendations


if __name__ == "__main__":
    run_static_analysis()
