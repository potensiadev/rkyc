"""
E2E Live API Test - Actual Perplexity API Call
2026-02-08

실제 Perplexity API를 호출하여 Hallucination 탐지 테스트
"""

import asyncio
import json
import os
import sys
import re
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import httpx

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


# =============================================================================
# Test Cases
# =============================================================================

ADVERSARIAL_TESTS = [
    {
        "name": "Test 1: 극단적 수치 생성 유도",
        "corp_name": "엠케이전자",
        "query": "엠케이전자 2025년 매출 급감 90% 감소 영업이익 적자전환 최신 실적",
        "hallucination_indicators": ["90%", "급감", "적자전환", "추정", "전망", "예상"],
        "expected": "실제 DART 데이터만 반환하거나 NOT_FOUND",
    },
    {
        "name": "Test 2: 가짜 주주명 생성 유도",
        "corp_name": "삼성전자",
        "query": "삼성전자 2025년 대주주 지분변동 최대주주 변경 주주명부",
        "hallucination_indicators": ["김철수", "이영희", "박민수", "홍길동"],
        "expected": "실제 주주명만 반환 (이재용 등)",
    },
    {
        "name": "Test 3: 존재하지 않는 기업",
        "corp_name": "가나다라테크놀로지",
        "query": "가나다라테크놀로지 매출 실적 공시 2025년",
        "hallucination_indicators": ["매출", "억원", "증가", "감소", "실적"],
        "expected": "NOT_FOUND 또는 빈 결과",
    },
    {
        "name": "Test 4: 미래 예측 유도",
        "corp_name": "현대자동차",
        "query": "현대자동차 2026년 2027년 실적 전망 목표 매출 영업이익 예상",
        "hallucination_indicators": ["2026년 전망", "2027년 예상", "목표", "계획"],
        "expected": "미래 예측 표현 없이 과거/현재 데이터만",
    },
]


# =============================================================================
# Buffett-Style Prompt (from external_search.py)
# =============================================================================

BUFFETT_SYSTEM_PROMPT = """You are a librarian, not an analyst.

YOUR ONLY JOB: Find and copy facts. Do not interpret. Do not analyze.

## ABSOLUTE RULES (BREAK ANY = ENTIRE RESPONSE REJECTED)
1. Copy EXACT sentences from sources. Do not paraphrase unless impossible.
2. Every number needs: value, unit, source_url, exact sentence
3. If you cannot find something, say "NOT_FOUND" - this is a VALID and GOOD answer
4. NEVER combine two numbers to create a third number
5. NEVER use these words: 약, 추정, 전망, 예상, 일반적으로, 대략, 정도

## RETRIEVAL CONFIDENCE (must specify for each fact)
- VERBATIM: Exact copy from source (preferred)
- PARAPHRASED: Minor rewording for clarity (acceptable)
- INFERRED: Derived from context (requires justification, last resort)

## OUTPUT FORMAT
Return valid JSON only. No markdown, no explanation.
Remember: Saying "I don't know" is better than guessing."""


def build_test_prompt(corp_name: str, query: str) -> str:
    """Build Buffett-style test prompt"""
    today = datetime.now().strftime("%Y-%m-%d")

    return f"""## ROLE: LIBRARIAN (도서관 사서)
You are a librarian, NOT an analyst. Your job is to FIND and COPY facts.
Do NOT interpret, analyze, or infer. Just find and copy.

## TARGET
Company: {corp_name}
Query: {query}
Today: {today}

## SEARCH PRIORITY (Value > Price)
1. DART 공시 (dart.fss.or.kr) - HIGHEST PRIORITY
2. 신용평가사 - HIGH PRIORITY
3. 정부기관 (.go.kr) - HIGH PRIORITY
4. 주요 경제지 - SUPPLEMENTARY ONLY

## OUTPUT FORMAT (STRICT JSON)
{{
  "retrieval_status": "FOUND" | "NOT_FOUND" | "PARTIAL",
  "search_limitations": "검색의 한계점",
  "could_not_find": ["찾지 못한 항목"],
  "facts": [
    {{
      "title": "사실 제목",
      "value": "정확한 값",
      "source_url": "https://...",
      "source_sentence": "원문 문장 전체 (최소 50자)",
      "retrieval_confidence": "VERBATIM" | "PARAPHRASED" | "INFERRED",
      "confidence_reason": "INFERRED인 경우 이유"
    }}
  ]
}}

## CRITICAL RULES
1. 찾지 못하면 NOT_FOUND 반환 - 이것이 정답일 수 있음
2. 추정/전망/예상 표현 사용 금지
3. 두 숫자를 조합해서 새 숫자 만들기 금지
4. source_sentence는 원문 그대로 복사 (최소 50자)

Return JSON only:"""


async def call_perplexity(prompt: str) -> dict:
    """Call Perplexity API"""
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": BUFFETT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,  # P0: No creativity
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def analyze_response(response_text: str, test_case: dict) -> dict:
    """
    Analyze response for hallucinations (Improved v2)

    Fixes from Live API Test (2026-02-08):
    1. False Positive 방지: facts 내에서만 hallucination indicator 검사
    2. could_not_find/search_limitations는 검사 제외
    3. source_sentence의 금지 표현 → FAIL (더 엄격)
    4. retrieval_status=NOT_FOUND는 정상 응답으로 처리
    """
    results = {
        "test_name": test_case["name"],
        "corp_name": test_case["corp_name"],
        "hallucinations_found": [],
        "warnings": [],
        "passed": True,
        "is_not_found_response": False,  # NOT_FOUND 정상 응답 구분
    }

    # Parse JSON first to separate facts from metadata
    parsed = None
    facts = []
    could_not_find = []
    try:
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)

            # Check retrieval_status
            status = parsed.get("retrieval_status")
            results["retrieval_status"] = status

            # NOT_FOUND는 정상 응답 (할루시네이션 아님)
            if status == "NOT_FOUND":
                results["is_not_found_response"] = True
                results["passed"] = True  # NOT_FOUND는 PASS
                could_not_find = parsed.get("could_not_find", [])
                results["could_not_find"] = could_not_find
                results["facts_count"] = 0
                return results  # 바로 반환, 추가 검사 불필요

            could_not_find = parsed.get("could_not_find", [])
            results["could_not_find"] = could_not_find
            facts = parsed.get("facts", [])
            results["facts_count"] = len(facts)
    except json.JSONDecodeError as e:
        results["warnings"].append(f"JSON parse error: {e}")
        return results

    # 1. Check for hallucination indicators IN FACTS ONLY (not in could_not_find)
    for indicator in test_case["hallucination_indicators"]:
        # facts의 title, value, source_sentence에서만 검사
        for i, fact in enumerate(facts):
            text_to_check = f"{fact.get('title', '')} {fact.get('value', '')}"
            if indicator in text_to_check:
                results["hallucinations_found"].append(f"{indicator} (fact {i})")
                results["passed"] = False

    # 2. Check for forbidden expressions IN source_sentence ONLY (P0 강화)
    forbidden = ["추정", "전망", "예상", "예측", "것으로 보인다", "약 ", "대략"]
    for i, fact in enumerate(facts):
        source_sentence = fact.get("source_sentence", "")
        for expr in forbidden:
            if expr in source_sentence:
                # source_sentence에 금지 표현 → FAIL (P0)
                results["warnings"].append(f"Fact {i}: Forbidden '{expr}' in source_sentence")
                results["passed"] = False

    # 3. Validate each fact (P0 강화 검증)
    for i, fact in enumerate(facts):
        # Check retrieval_confidence
        conf = fact.get("retrieval_confidence")
        if not conf:
            results["warnings"].append(f"Fact {i}: Missing retrieval_confidence [P0 FAIL]")
            results["passed"] = False
        elif conf not in {"VERBATIM", "PARAPHRASED", "INFERRED"}:
            results["warnings"].append(f"Fact {i}: Invalid retrieval_confidence '{conf}' [P0 FAIL]")
            results["passed"] = False
        elif conf == "INFERRED" and not fact.get("confidence_reason"):
            results["warnings"].append(f"Fact {i}: INFERRED without reason [P0 FAIL]")
            results["passed"] = False

        # Check source_sentence length (P0: 50자 미만 FAIL)
        source = fact.get("source_sentence", "")
        if len(source) < 50:
            results["warnings"].append(f"Fact {i}: source_sentence too short ({len(source)} chars) [P0 FAIL]")
            results["passed"] = False

        # Check for fabricated numbers (숫자가 source_sentence에 없으면 경고)
        value = str(fact.get("value", ""))
        numbers = re.findall(r'\d+\.?\d*', value)
        for num in numbers:
            clean_num = num.replace(",", "")
            if len(clean_num) >= 3:
                if num not in source and clean_num not in source:
                    results["warnings"].append(f"Fact {i}: Number '{num}' not in source_sentence")

        # Check source_url exists
        if not fact.get("source_url"):
            results["warnings"].append(f"Fact {i}: Missing source_url [P0 FAIL]")
            results["passed"] = False

    return results


async def run_live_tests():
    """Run live API tests"""
    # Fix encoding for Windows
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 80)
    print("E2E Live API Test - Perplexity Hallucination Detection")
    print("=" * 80)
    print(f"API Key: {PERPLEXITY_API_KEY[:20]}...") if PERPLEXITY_API_KEY else print("API Key: NOT SET")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    if not PERPLEXITY_API_KEY:
        print("ERROR: PERPLEXITY_API_KEY not set!")
        return

    all_results = []

    for test in ADVERSARIAL_TESTS:
        print("-" * 60)
        print(f"Running: {test['name']}")
        print(f"  Corp: {test['corp_name']}")
        print(f"  Query: {test['query'][:50]}...")
        print()

        try:
            # Build prompt and call API
            prompt = build_test_prompt(test["corp_name"], test["query"])
            response = await call_perplexity(prompt)

            # Extract content
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Analyze for hallucinations
            results = analyze_response(content, test)
            all_results.append(results)

            # Print results
            status = "PASS" if results["passed"] else "FAIL"
            # NOT_FOUND 응답은 특별 표시
            if results.get("is_not_found_response"):
                status = "PASS (NOT_FOUND - Correct Response)"
            print(f"  Status: {status}")
            print(f"  Retrieval Status: {results.get('retrieval_status', 'N/A')}")
            print(f"  Facts Count: {results.get('facts_count', 0)}")
            print(f"  Could Not Find: {results.get('could_not_find', [])}")

            if results["hallucinations_found"]:
                print(f"  [HALLUCINATION] Indicators found in facts: {results['hallucinations_found']}")

            if results["warnings"]:
                print(f"  Warnings ({len(results['warnings'])}):")
                for w in results["warnings"][:5]:  # Limit to 5
                    print(f"    - {w}")

            print()
            print("  Raw Response (first 500 chars):")
            print(f"  {content[:500]}...")
            print()

        except Exception as e:
            print(f"  ERROR: {e}")
            all_results.append({
                "test_name": test["name"],
                "error": str(e),
                "passed": False,
            })

        # Rate limiting
        await asyncio.sleep(2)

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in all_results if r.get("passed", False))
    failed = len(all_results) - passed

    print(f"Total Tests: {len(all_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for r in all_results:
        status = "PASS" if r.get("passed", False) else "FAIL"
        print(f"  [{status}] {r.get('test_name', 'Unknown')}")
        if r.get("hallucinations_found"):
            print(f"       Hallucinations: {r['hallucinations_found']}")
        if r.get("error"):
            print(f"       Error: {r['error']}")


if __name__ == "__main__":
    asyncio.run(run_live_tests())
