#!/usr/bin/env python3
"""
Gemini Grounding Provider 테스트 스크립트

사용법:
    cd backend
    python scripts/test_gemini_grounding.py

테스트 내용:
1. Gemini Grounding 검색 (Citation 추출 확인)
2. Perplexity 검색 (비교용)
3. Provider 우선순위 확인
"""

import asyncio
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_gemini_grounding():
    """Gemini Grounding 검색 테스트"""
    from app.worker.llm.search_providers import (
        GeminiGroundingProvider,
        get_circuit_breaker_manager,
        get_search_config,
    )

    print("=" * 60)
    print("1. Gemini Grounding 검색 테스트")
    print("=" * 60)

    # 현재 설정 확인
    config = get_search_config()
    print(f"\n현재 설정:")
    print(f"  - gemini_primary: {config['gemini_primary']}")
    print(f"  - grounding_enabled: {config['grounding_enabled']}")

    circuit_breaker = get_circuit_breaker_manager()
    provider = GeminiGroundingProvider(circuit_breaker)

    if not provider.is_available():
        print("\n❌ Gemini API 키가 설정되지 않았습니다.")
        print("   GOOGLE_API_KEY 환경변수를 설정하세요.")
        return None

    print("\n✅ Gemini API 키 확인됨")

    # 테스트 쿼리
    query = """엠케이전자 기업 정보를 검색해주세요.

다음 정보를 찾아주세요:
- 사업 개요
- 대표이사
- 최근 매출액
- 주요 고객사
- 경쟁사

정확한 수치와 출처를 포함해주세요."""

    print(f"\n검색 쿼리: {query[:100]}...")
    print("\n검색 중...")

    try:
        result = await provider.search(query)

        print(f"\n✅ 검색 성공!")
        print(f"  - Provider: {result.provider.value}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print(f"  - Latency: {result.latency_ms}ms")
        print(f"  - Grounding Used: {result.raw_response.get('grounding_used', False)}")
        print(f"  - Citations 수: {len(result.citations)}")

        if result.citations:
            print("\n📚 Citations (출처):")
            for i, url in enumerate(result.citations[:5], 1):
                print(f"  {i}. {url}")
        else:
            print("\n⚠️ Citation 없음 - Grounding이 활성화되지 않았을 수 있습니다.")

        print(f"\n📝 응답 내용 (처음 500자):")
        print("-" * 40)
        print(result.content[:500] if result.content else "(빈 응답)")
        print("-" * 40)

        return result

    except Exception as e:
        print(f"\n❌ 검색 실패: {e}")
        return None


async def test_perplexity():
    """Perplexity 검색 테스트 (비교용)"""
    from app.worker.llm.search_providers import (
        PerplexityProvider,
        get_circuit_breaker_manager,
    )

    print("\n" + "=" * 60)
    print("2. Perplexity 검색 테스트 (비교용)")
    print("=" * 60)

    circuit_breaker = get_circuit_breaker_manager()
    provider = PerplexityProvider(circuit_breaker)

    if not provider.is_available():
        print("\n⚠️ Perplexity API 키가 설정되지 않았습니다.")
        print("   PERPLEXITY_API_KEY 환경변수를 설정하세요.")
        print("   (Gemini Primary 모드에서는 선택 사항)")
        return None

    print("\n✅ Perplexity API 키 확인됨")

    query = "엠케이전자 기업 정보 매출 대표이사 주요 고객"

    print(f"\n검색 쿼리: {query}")
    print("\n검색 중...")

    try:
        result = await provider.search(query)

        print(f"\n✅ 검색 성공!")
        print(f"  - Provider: {result.provider.value}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print(f"  - Latency: {result.latency_ms}ms")
        print(f"  - Citations 수: {len(result.citations)}")

        if result.citations:
            print("\n📚 Citations (출처):")
            for i, url in enumerate(result.citations[:5], 1):
                print(f"  {i}. {url}")

        return result

    except Exception as e:
        print(f"\n❌ 검색 실패: {e}")
        return None


async def test_multi_search_manager():
    """MultiSearchManager 테스트 (Provider 우선순위)"""
    from app.worker.llm.search_providers import (
        MultiSearchManager,
        get_search_config,
    )

    print("\n" + "=" * 60)
    print("3. MultiSearchManager 테스트 (Provider 우선순위)")
    print("=" * 60)

    config = get_search_config()
    manager = MultiSearchManager(gemini_primary=config["gemini_primary"])

    print(f"\n현재 Provider 우선순위: {manager.get_provider_order()}")

    available = manager.get_available_providers()
    print(f"사용 가능한 Provider: {[p.provider_type.value for p in available]}")

    if not available:
        print("\n❌ 사용 가능한 Provider가 없습니다.")
        return

    query = "삼성전자 2025년 3분기 실적"
    print(f"\n검색 쿼리: {query}")
    print("\n검색 중 (Primary Provider 사용)...")

    try:
        result = await manager.search(query)

        print(f"\n✅ 검색 성공!")
        print(f"  - 사용된 Provider: {result.provider.value}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print(f"  - Latency: {result.latency_ms}ms")
        print(f"  - Citations 수: {len(result.citations)}")

    except Exception as e:
        print(f"\n❌ 검색 실패: {e}")


async def test_rollback():
    """롤백 테스트"""
    from app.worker.llm.search_providers import (
        get_search_config,
        set_gemini_primary,
        set_grounding_enabled,
    )

    print("\n" + "=" * 60)
    print("4. 롤백 테스트")
    print("=" * 60)

    original_config = get_search_config()
    print(f"\n원래 설정: {original_config}")

    # 롤백 테스트
    print("\n롤백 수행: gemini_primary=False, grounding_enabled=False")
    set_gemini_primary(False)
    set_grounding_enabled(False)

    rolled_back = get_search_config()
    print(f"롤백 후 설정: {rolled_back}")

    # 원래대로 복원
    print("\n원래 설정으로 복원")
    set_gemini_primary(original_config["gemini_primary"])
    set_grounding_enabled(original_config["grounding_enabled"])

    restored = get_search_config()
    print(f"복원된 설정: {restored}")

    print("\n✅ 롤백 테스트 완료")


async def main():
    print("\n" + "=" * 60)
    print("Gemini Grounding Provider 테스트")
    print("=" * 60)

    # 1. Gemini Grounding 테스트
    gemini_result = await test_gemini_grounding()

    # 2. Perplexity 테스트 (비교용)
    perplexity_result = await test_perplexity()

    # 3. MultiSearchManager 테스트
    await test_multi_search_manager()

    # 4. 롤백 테스트
    await test_rollback()

    # 결과 비교
    print("\n" + "=" * 60)
    print("결과 비교")
    print("=" * 60)

    print("\n| 항목 | Gemini Grounding | Perplexity |")
    print("|------|------------------|------------|")

    if gemini_result:
        gemini_citations = len(gemini_result.citations)
        gemini_latency = gemini_result.latency_ms
        gemini_confidence = gemini_result.confidence
    else:
        gemini_citations = "N/A"
        gemini_latency = "N/A"
        gemini_confidence = "N/A"

    if perplexity_result:
        perplexity_citations = len(perplexity_result.citations)
        perplexity_latency = perplexity_result.latency_ms
        perplexity_confidence = perplexity_result.confidence
    else:
        perplexity_citations = "N/A"
        perplexity_latency = "N/A"
        perplexity_confidence = "N/A"

    print(f"| Citations | {gemini_citations} | {perplexity_citations} |")
    print(f"| Latency (ms) | {gemini_latency} | {perplexity_latency} |")
    print(f"| Confidence | {gemini_confidence} | {perplexity_confidence} |")
    print(f"| 비용 | $0 | ~$0.005/req |")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
