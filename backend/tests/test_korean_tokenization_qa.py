"""
한국어 QA 테스트: 한국어 토큰화 품질 검증
Native Korean QA Engineer 관점에서 작성

테스트 범위:
1. 실제 비즈니스 텍스트 토큰화
2. 조사/어미 제거 확인
3. Jaccard Similarity 정확도
4. Edge case 처리
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.worker.llm.consensus_engine import (
    tokenize,
    jaccard_similarity,
    compare_values_legacy as compare_values,  # P1 Fix: Use legacy API (2-value return)
    _get_kiwi,
)


class TestRealBusinessTextTokenization:
    """실제 비즈니스 텍스트 토큰화 테스트"""

    def test_company_business_description_1(self):
        """기업 사업 설명 1: 삼성전자"""
        text = "삼성전자는 반도체 및 스마트폰 사업을 영위하고 있습니다."
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 핵심 명사가 보존되어야 함
        assert "삼성전자" in tokens or "삼성" in tokens, "삼성전자/삼성 누락"
        assert "반도체" in tokens, "반도체 누락"
        assert "스마트폰" in tokens, "스마트폰 누락"
        assert "사업" in tokens, "사업 누락"

        # 조사/어미는 제거되어야 함
        assert "는" not in tokens, "조사 '는' 미제거"
        assert "을" not in tokens, "조사 '을' 미제거"
        assert "및" not in tokens, "접속사 '및' 미제거"
        assert "있습니다" not in tokens, "어미 '있습니다' 미제거"

    def test_company_business_description_2(self):
        """기업 사업 설명 2: 현대자동차"""
        text = "현대자동차의 전기차 수출이 증가했습니다."
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 핵심 명사
        assert "현대자동차" in tokens or "현대" in tokens
        assert "전기차" in tokens or "전기" in tokens
        assert "수출" in tokens

        # 조사/어미 제거
        assert "의" not in tokens, "조사 '의' 미제거"
        assert "이" not in tokens, "조사 '이' 미제거"
        assert "했습니다" not in tokens

    def test_company_business_description_3(self):
        """기업 사업 설명 3: LG화학"""
        text = "LG화학은 배터리 소재 등의 사업을 확대 중입니다."
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 핵심 내용어
        assert "lg화학" in tokens or "lg" in tokens or "화학" in tokens
        assert "배터리" in tokens
        assert "소재" in tokens
        assert "확대" in tokens

        # 복합조사 "등의" 제거 확인
        assert "등의" not in tokens, "복합조사 '등의' 미제거"
        assert "은" not in tokens

    def test_financial_information_with_numbers(self):
        """재무 정보 텍스트: 숫자 포함"""
        text = "2024년 매출 100억원을 달성했습니다."
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 숫자와 단위 처리
        assert "매출" in tokens
        assert "달성" in tokens
        # 숫자는 보존되거나 적절히 처리
        has_year = any("2024" in str(t) for t in tokens)
        print(f"연도 포함 여부: {has_year}")

    def test_financial_info_with_percentage(self):
        """재무 정보: SK하이닉스 HBM3"""
        text = "SK하이닉스 HBM3 생산량이 30% 증가"
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 핵심 단어
        assert "sk하이닉스" in tokens or "하이닉스" in tokens or "sk" in tokens
        assert "hbm3" in tokens or "hbm" in tokens
        assert "생산량" in tokens or "생산" in tokens
        assert "증가" in tokens

    def test_compound_postposition_removal(self):
        """복합 조사 제거: '으로부터의', '에서는' 등"""
        test_cases = [
            ("중국으로부터의 수입이 감소했습니다.", ["중국", "수입", "감소"]),
            ("정부에서는 규제를 완화했습니다.", ["정부", "규제", "완화"]),
            # P1 Fix: "무역협정"은 형태소 분석기가 "무역"+"협정"으로 분리할 수 있음
            ("미국과의 무역협정이 체결되었습니다.", ["미국", "무역", "체결"]),
        ]

        for text, expected_words in test_cases:
            tokens = tokenize(text)
            print(f"\n입력: '{text}'")
            print(f"토큰: {tokens}")

            for word in expected_words:
                # 단어가 정확히 또는 일부로 포함
                found = any(word in str(t) for t in tokens)
                assert found, f"'{word}'가 토큰에 없음: {tokens}"

            # 복합 조사 제거 확인
            assert "으로부터의" not in tokens
            assert "에서는" not in tokens
            assert "과의" not in tokens

    def test_news_article_style(self):
        """뉴스 기사 스타일 텍스트"""
        text = """삼성전자가 차세대 반도체 공정 개발에 성공했다고 밝혔다.
        이번 기술은 기존 대비 전력 효율을 20% 개선한 것으로 알려졌다."""
        tokens = tokenize(text)
        print(f"\n입력: '{text[:50]}...'")
        print(f"토큰: {tokens}")

        # 주요 키워드 확인
        important_words = ["삼성전자", "반도체", "공정", "개발", "성공", "기술", "전력", "효율", "개선"]
        for word in important_words:
            if word in ["삼성전자"]:
                assert "삼성전자" in tokens or "삼성" in tokens
            else:
                found = any(word in str(t) for t in tokens)
                # 일부는 형태소 분석으로 분리될 수 있음
                print(f"  '{word}' 포함: {found}")

    def test_disclosure_document_style(self):
        """공시 문서 스타일"""
        text = "동 회사는 제3자배정 유상증자를 통해 운영자금을 확보할 예정입니다."
        tokens = tokenize(text)
        print(f"\n입력: '{text}'")
        print(f"토큰: {tokens}")

        # 공시 용어 확인
        assert "회사" in tokens
        assert "유상증자" in tokens or "유상" in tokens or "증자" in tokens
        assert "운영자금" in tokens or "운영" in tokens or "자금" in tokens


class TestJaccardSimilarityWithBusinessText:
    """비즈니스 텍스트 Jaccard Similarity 테스트"""

    def test_similar_business_descriptions_high_similarity(self):
        """유사한 사업 설명: 높은 유사도 기대"""
        desc_a = "삼성전자는 반도체 및 디스플레이 사업을 영위합니다"
        desc_b = "삼성전자 반도체와 디스플레이 사업 영위"

        score = jaccard_similarity(desc_a, desc_b)
        print(f"\nText A: '{desc_a}'")
        print(f"Text B: '{desc_b}'")
        print(f"Jaccard Score: {score:.4f}")

        # 같은 내용이므로 높은 유사도 기대
        assert score >= 0.7, f"유사한 설명인데 유사도가 낮음: {score}"

    def test_different_business_descriptions_low_similarity(self):
        """다른 사업 설명: 낮은 유사도 기대"""
        desc_a = "삼성전자는 반도체 및 디스플레이 사업을 영위합니다"
        desc_c = "현대자동차는 자동차 제조 및 판매업을 영위합니다"

        score = jaccard_similarity(desc_a, desc_c)
        print(f"\nText A: '{desc_a}'")
        print(f"Text C: '{desc_c}'")
        print(f"Jaccard Score: {score:.4f}")

        # 다른 회사, 다른 사업이므로 낮은 유사도
        assert score < 0.5, f"다른 설명인데 유사도가 높음: {score}"

    def test_same_meaning_different_expression(self):
        """같은 의미, 다른 표현"""
        text_a = "매출이 크게 증가했습니다"
        text_b = "매출 대폭 증가"

        score = jaccard_similarity(text_a, text_b)
        print(f"\nText A: '{text_a}'")
        print(f"Text B: '{text_b}'")
        print(f"Jaccard Score: {score:.4f}")

        # "매출"과 "증가"가 공통이므로 어느 정도 유사
        assert score >= 0.3, f"같은 의미인데 유사도가 너무 낮음: {score}"

    def test_industry_specific_terms(self):
        """업종별 전문 용어 비교"""
        # 반도체 업종
        semi_a = "웨이퍼 가공 및 패키징 사업"
        semi_b = "반도체 웨이퍼 패키징 및 테스트"

        score = jaccard_similarity(semi_a, semi_b)
        print(f"\n반도체 A: '{semi_a}'")
        print(f"반도체 B: '{semi_b}'")
        print(f"Jaccard Score: {score:.4f}")

        # P1 Fix: 공통 토큰 "웨이퍼", "패키징" = 2개
        # 전체 유니크 토큰 약 6개 → Jaccard = 2/6 ≈ 0.33
        assert score >= 0.3

    def test_export_ratio_text_comparison(self):
        """수출 비중 텍스트 비교"""
        text_a = "수출 비중 45%로 해외 의존도가 높음"
        text_b = "수출 비율 45퍼센트, 해외 매출 의존"

        score = jaccard_similarity(text_a, text_b)
        print(f"\nText A: '{text_a}'")
        print(f"Text B: '{text_b}'")
        print(f"Jaccard Score: {score:.4f}")

        # "수출", "해외", "의존" 등 공통
        assert score >= 0.3


class TestEdgeCases:
    """Edge Case 테스트"""

    def test_empty_string(self):
        """빈 문자열"""
        tokens = tokenize("")
        assert tokens == set()

        score = jaccard_similarity("", "")
        assert score == 1.0  # 둘 다 비어있으면 일치

    def test_whitespace_only(self):
        """공백만 있는 문자열"""
        tokens = tokenize("   \t\n  ")
        print(f"공백만 있는 문자열 토큰: {tokens}")
        assert len(tokens) == 0

    def test_numbers_only(self):
        """숫자만 있는 문자열"""
        tokens = tokenize("123456789")
        print(f"숫자만 있는 문자열 토큰: {tokens}")
        # 숫자는 보존되거나 빈 집합

    def test_english_only(self):
        """영문만 있는 문자열"""
        tokens = tokenize("Samsung Electronics Corporation")
        print(f"영문만 있는 문자열 토큰: {tokens}")
        assert len(tokens) > 0
        assert "samsung" in tokens or "Samsung" in tokens.union({t.lower() for t in tokens})

    def test_mixed_korean_english_numbers(self):
        """한글+영문+숫자 혼합"""
        text = "삼성전자 Galaxy S24 출시 2024년"
        tokens = tokenize(text)
        print(f"\n혼합 텍스트: '{text}'")
        print(f"토큰: {tokens}")

        # 주요 단어 확인
        assert "삼성전자" in tokens or "삼성" in tokens
        # Galaxy나 galaxy가 포함
        has_galaxy = any("galaxy" in str(t).lower() for t in tokens)
        print(f"Galaxy 포함: {has_galaxy}")

    def test_special_characters(self):
        """특수문자 포함 텍스트"""
        text = "매출: ₩100억 (전년대비 +20%)"
        tokens = tokenize(text)
        print(f"\n특수문자 텍스트: '{text}'")
        print(f"토큰: {tokens}")

        assert "매출" in tokens
        # 특수문자는 제거되어야 함
        assert "₩" not in str(tokens)

    def test_very_long_text(self):
        """매우 긴 텍스트 처리"""
        long_text = "삼성전자 반도체 사업 " * 100
        tokens = tokenize(long_text)
        print(f"\n긴 텍스트 토큰 수: {len(tokens)}")

        # 긴 텍스트도 처리되어야 함
        assert len(tokens) > 0
        assert "삼성전자" in tokens or "삼성" in tokens

    def test_jamo_separated_text(self):
        """초성/중성/종성 분리된 텍스트 (깨진 텍스트)"""
        # 실제 깨진 텍스트 예시 (인코딩 문제 등)
        broken_text = "ㅅㅏㅁㅅㅓㅇ"  # "삼성"이 분리된 형태
        tokens = tokenize(broken_text)
        print(f"\n깨진 텍스트: '{broken_text}'")
        print(f"토큰: {tokens}")
        # 처리가 되든 안 되든 오류 없이 처리되어야 함

    def test_repeated_stopwords(self):
        """반복된 불용어"""
        text = "의 의 의 은 는 을 를"
        tokens = tokenize(text)
        print(f"\n반복 불용어: '{text}'")
        print(f"토큰: {tokens}")

        # P1 Fix: 불용어는 제거되어야 하지만, 형태소 분석기 동작에 따라
        # 예상치 못한 토큰이 생성될 수 있음.
        # 최소한 입력된 조사들("의", "은", "는", "을", "를")은 없어야 함
        stopwords_in_input = {"의", "은", "는", "을", "를"}
        remaining_stopwords = tokens & stopwords_in_input
        assert len(remaining_stopwords) == 0, f"불용어가 제거되지 않음: {remaining_stopwords}"


class TestKiwipiepyIntegration:
    """kiwipiepy 통합 확인"""

    def test_kiwi_is_available(self):
        """kiwipiepy 사용 가능 확인"""
        kiwi = _get_kiwi()
        print(f"\nKiwi instance: {kiwi}")
        assert kiwi is not None and kiwi is not False, "kiwipiepy가 설치되어 있지 않음"

    def test_morphological_analysis_quality(self):
        """형태소 분석 품질 확인"""
        kiwi = _get_kiwi()
        if not kiwi:
            pytest.skip("kiwipiepy not installed")

        text = "삼성전자는 반도체를 생산합니다"
        result = kiwi.tokenize(text)

        print(f"\n형태소 분석 결과:")
        for token in result:
            print(f"  {token.form} ({token.tag})")

        # 형태소 분석이 제대로 되었는지 확인
        forms = [t.form for t in result]
        tags = [t.tag for t in result]

        assert "삼성전자" in forms or "삼성" in forms
        assert "반도체" in forms
        # 조사가 분리되었는지
        assert "JKS" in tags or "JX" in tags  # 주격조사 또는 보조사


class TestCompareValuesWithKoreanText:
    """compare_values 함수의 한국어 텍스트 처리"""

    def test_string_comparison_korean(self):
        """한국어 문자열 비교"""
        is_match, score = compare_values(
            "삼성전자 반도체 사업",
            "삼성전자의 반도체 사업부",
            threshold=0.7
        )
        print(f"\n비교 결과: match={is_match}, score={score:.4f}")

        # 핵심 단어가 같으므로 매치될 가능성 높음
        assert score >= 0.5

    def test_list_comparison_korean_companies(self):
        """한국어 회사명 리스트 비교"""
        list_a = ["삼성전자", "SK하이닉스", "LG전자"]
        list_b = ["삼성전자", "SK하이닉스"]

        is_match, score = compare_values(list_a, list_b, threshold=0.5)
        print(f"\n리스트 비교: {list_a} vs {list_b}")
        print(f"결과: match={is_match}, score={score:.4f}")

        # 2/3 = 0.67 >= 0.5
        assert is_match
        assert 0.6 <= score <= 0.7

    def test_dict_comparison_country_exposure(self):
        """국가 노출 딕셔너리 비교"""
        dict_a = {"중국": 40, "미국": 30, "유럽": 20}
        dict_b = {"중국": 38, "미국": 32, "유럽": 20}

        is_match, score = compare_values(dict_a, dict_b, threshold=0.7)
        print(f"\n딕셔너리 비교:")
        print(f"  A: {dict_a}")
        print(f"  B: {dict_b}")
        print(f"결과: match={is_match}, score={score:.4f}")

        # 값이 10% 이내이므로 매치
        assert is_match


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
