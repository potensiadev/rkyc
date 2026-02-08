"""
DART에서 소규모 기업 검색

코스닥/코넥스 소형주 중 DART API로 조회 가능한 기업 찾기
"""
import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.dart_api import (
    load_corp_codes,
    get_corp_code,
    get_company_info,
    get_financial_statements,
)


# 테스트할 소규모 기업 후보 (코스닥/코넥스)
SMALL_CORP_CANDIDATES = [
    # 코스닥 소형주 (다양한 업종)
    "케이씨피드",          # 사료
    "세원이앤씨",          # 건설
    "한국제지",            # 제지
    "아세아시멘트",        # 시멘트
    "한진피앤씨",          # 물류
    "대한과학",            # 과학기기
    "팬엔터테인먼트",      # 엔터
    "삼화콘덴서",          # 전자부품
    "화승알앤에이",        # 자동차부품
    "세종공업",            # 자동차부품
    # 코넥스 기업
    "바이오노트",          # 바이오
    "크라우드웍스",        # IT
    "파이오링크",          # IT 보안
    "미래반도체",          # 반도체
    "이엘피",              # 전자
    "대덕전자",            # PCB
    "서울반도체",          # LED
    "텔레칩스",            # 반도체
    "에스에프에이",        # 장비
    "원익IPS",             # 장비
    # 추가 후보
    "평화산업",            # 자동차부품
    "삼아알미늄",          # 알루미늄
    "에스앤에스텍",        # 소재
    "이오테크닉스",        # 레이저
    "인터플렉스",          # 전자부품
]


async def check_corp(name: str) -> dict:
    """기업 DART 조회"""
    result = {
        "name": name,
        "found": False,
        "corp_code": None,
        "corp_cls": None,
        "revenue": None,
        "industry": None,
    }

    try:
        corp_code = await get_corp_code(corp_name=name)
        if not corp_code:
            return result

        result["found"] = True
        result["corp_code"] = corp_code

        # 기업개황
        info = await get_company_info(corp_code)
        if info:
            result["corp_cls"] = info.corp_cls  # Y:유가, K:코스닥, N:코넥스, E:기타
            result["industry"] = info.induty_code
            result["ceo"] = info.ceo_name

        # 재무제표
        financials = await get_financial_statements(corp_code)
        if financials:
            latest = financials[0]
            if latest.revenue:
                result["revenue"] = latest.revenue
                result["revenue_display"] = f"{latest.revenue/100000000:.0f}억"

    except Exception as e:
        result["error"] = str(e)

    return result


async def main():
    print("=" * 70)
    print("DART 조회 가능한 소규모 기업 검색")
    print("=" * 70)

    # DART 코드 로드
    print("\n[1] DART 기업 목록 로드 중...")
    await load_corp_codes()
    print("완료")

    # 각 후보 기업 조회
    print(f"\n[2] {len(SMALL_CORP_CANDIDATES)}개 후보 기업 조회 중...\n")

    results = []
    for name in SMALL_CORP_CANDIDATES:
        result = await check_corp(name)
        results.append(result)

        status = "O" if result["found"] else "X"
        if result["found"]:
            cls_name = {"Y": "유가증권", "K": "코스닥", "N": "코넥스", "E": "기타"}.get(result["corp_cls"], "?")
            revenue = result.get("revenue_display", "N/A")
            print(f"  [{status}] {name}: {cls_name}, 매출 {revenue}")
        else:
            print(f"  [{status}] {name}: 미등록")

    # 소규모 기업 필터링 (매출 1000억 이하)
    print("\n" + "=" * 70)
    print("추천 소규모 기업 (매출 1000억 이하, DART 조회 가능)")
    print("=" * 70)

    small_corps = []
    for r in results:
        if r["found"] and r.get("revenue"):
            if r["revenue"] <= 100000000000:  # 1000억 이하
                small_corps.append(r)

    # 매출 기준 정렬
    small_corps.sort(key=lambda x: x.get("revenue", 0))

    for i, corp in enumerate(small_corps[:10], 1):
        cls_name = {"Y": "유가증권", "K": "코스닥", "N": "코넥스", "E": "기타"}.get(corp["corp_cls"], "?")
        print(f"  {i}. {corp['name']} ({cls_name})")
        print(f"     - DART 코드: {corp['corp_code']}")
        print(f"     - 매출: {corp.get('revenue_display', 'N/A')}")
        print(f"     - 대표: {corp.get('ceo', 'N/A')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
