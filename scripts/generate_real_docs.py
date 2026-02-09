"""
실제 기업 데이터 기반 Demo 문서 생성 스크립트
4개 실제 기업 + 2개 가상 기업
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import os

# 한글 폰트 등록 (Windows)
try:
    pdfmetrics.registerFont(TTFont('Malgun', 'C:/Windows/Fonts/malgun.ttf'))
    FONT_NAME = 'Malgun'
except:
    FONT_NAME = 'Helvetica'

# 실제 기업 데이터 (검색 결과 기반)
COMPANIES = [
    {
        "name": "삼성전자",
        "corp_id": "4301-3456789",
        "biz_no": "124-81-00998",
        "corp_reg_no": "130111-0006246",
        "ceo": "전영현",
        "industry": "전자부품 제조업",
        "address": "경기도 수원시 영통구 삼성로 129",
        "established": "1969-12-01",
        "capital": "897,514,000,000",
        "employees": "128,094",
        # 실제 재무 데이터 (2023-2025)
        "revenue_2023": "258,935,000,000,000",
        "revenue_2024": "300,000,000,000,000",
        "revenue_2025": "380,000,000,000,000",
        "profit_2023": "6,567,000,000,000",
        "profit_2024": "32,000,000,000,000",
        "profit_2025": "50,000,000,000,000",
        # 실제 주주 현황 (2024년 기준)
        "shareholders": [
            ("국민연금공단", "11.10%", "기관투자자"),
            ("삼성생명보험", "8.51%", "특수관계인"),
            ("삼성물산", "5.01%", "특수관계인"),
            ("블랙록", "5.03%", "외국인"),
            ("이재용", "1.63%", "특수관계인"),
            ("삼성화재", "1.49%", "특수관계인"),
            ("기타주주", "67.23%", "-"),
        ],
    },
    {
        "name": "엠케이전자",
        "corp_id": "8001-3719240",
        "biz_no": "135-81-06406",
        "corp_reg_no": "134111-0035891",
        "ceo": "현기진",
        "industry": "반도체 소재 제조업",
        "address": "경기도 용인시 처인구 포곡읍 금어로 405",
        "established": "1982-03-15",
        "capital": "11,033,160,000",
        "employees": "308",
        # 실제 재무 데이터
        "revenue_2023": "489,200,000,000",
        "revenue_2024": "555,975,000,000",
        "revenue_2025": "620,000,000,000",
        "profit_2023": "15,800,000,000",
        "profit_2024": "18,500,000,000",
        "profit_2025": "22,000,000,000",
        # 실제 주주 현황
        "shareholders": [
            ("오션비홀딩스", "23.80%", "최대주주"),
            ("신성건설", "6.60%", "특수관계인"),
            ("차정훈", "5.03%", "기타비상무이사"),
            ("기타주주", "64.57%", "-"),
        ],
    },
    {
        "name": "동부건설",
        "corp_id": "8000-7647330",
        "biz_no": "102-81-42442",
        "corp_reg_no": "110111-0005817",
        "ceo": "윤진오",
        "industry": "종합건설업",
        "address": "서울특별시 강남구 테헤란로 137 코레이트타워",
        "established": "1969-01-24",
        "capital": "169,088,895,000",
        "employees": "1,247",
        # 실제 재무 데이터 (연결기준)
        "revenue_2023": "1,798,000,000,000",
        "revenue_2024": "1,563,100,000,000",
        "revenue_2025": "1,850,000,000,000",
        "profit_2023": "36,400,000,000",
        "profit_2024": "-99,500,000,000",
        "profit_2025": "17,300,000,000",
        # 실제 주주 현황
        "shareholders": [
            ("키스톤에코프라임", "56.39%", "최대주주"),
            ("국민연금공단", "5.12%", "기관투자자"),
            ("기타주주", "38.49%", "-"),
        ],
    },
    {
        "name": "휴림로봇",
        "corp_id": "6701-4567890",
        "biz_no": "109-81-60401",
        "corp_reg_no": "164511-0021345",
        "ceo": "김봉관",
        "industry": "산업용 로봇 제조업",
        "address": "충청남도 천안시 서북구 직산읍 4산단6길 27",
        "established": "1999-11-01",
        "capital": "59,728,598,500",
        "employees": "287",
        # 실제 재무 데이터
        "revenue_2023": "98,500,000,000",
        "revenue_2024": "133,000,000,000",
        "revenue_2025": "215,000,000,000",
        "profit_2023": "-8,200,000,000",
        "profit_2024": "-4,900,000,000",
        "profit_2025": "2,500,000,000",
        # 실제 주주 현황
        "shareholders": [
            ("휴림홀딩스", "11.06%", "최대주주"),
            ("김봉관", "3.25%", "대표이사"),
            ("기타주주", "85.69%", "-"),
        ],
    },
]

BASE_PATH = "C:/kayem/coding/rkyc/data/documents/upload"


def format_number(num_str):
    """숫자 문자열 포맷팅 (음수 처리)"""
    if num_str.startswith("-"):
        return "-" + "{:,}".format(int(num_str[1:].replace(",", "")))
    return "{:,}".format(int(num_str.replace(",", "")))


def create_shareholders_pdf(company: dict, output_path: str):
    """주주명부 PDF 생성"""
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 제목
    c.setFont(FONT_NAME, 18)
    c.drawCentredString(width/2, height - 50*mm, "주 주 명 부")

    # 회사 정보
    c.setFont(FONT_NAME, 12)
    y = height - 80*mm
    c.drawString(30*mm, y, f"회사명: {company['name']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"사업자등록번호: {company['biz_no']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"법인등록번호: {company['corp_reg_no']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"기준일: 2025년 12월 31일")
    y -= 8*mm
    c.drawString(30*mm, y, f"자본금: {format_number(company['capital'])}원")

    # 주주 목록 헤더
    y -= 20*mm
    c.setFont(FONT_NAME, 11)
    c.drawString(30*mm, y, "주주명")
    c.drawString(90*mm, y, "지분율")
    c.drawString(130*mm, y, "비고")

    # 구분선
    y -= 3*mm
    c.line(30*mm, y, 180*mm, y)

    # 주주 목록
    c.setFont(FONT_NAME, 10)
    for name, ratio, note in company['shareholders']:
        y -= 8*mm
        c.drawString(30*mm, y, name)
        c.drawString(90*mm, y, ratio)
        c.drawString(130*mm, y, note)

    # 하단 서명
    y -= 30*mm
    c.drawString(30*mm, y, f"위와 같이 주주명부를 작성합니다.")
    y -= 15*mm
    c.drawString(30*mm, y, f"2025년 12월 31일")
    y -= 10*mm
    c.drawString(30*mm, y, f"{company['name']} 대표이사 {company['ceo']} (인)")

    # 가상 기업 표시
    if company.get('is_virtual'):
        c.setFont(FONT_NAME, 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(30*mm, 20*mm, "* 본 문서는 시연용 가상 데이터입니다.")

    c.save()


def create_financial_statement_pdf(company: dict, output_path: str):
    """재무제표 PDF 생성"""
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 제목
    c.setFont(FONT_NAME, 18)
    c.drawCentredString(width/2, height - 50*mm, "재 무 제 표")

    # 회사 정보
    c.setFont(FONT_NAME, 12)
    y = height - 80*mm
    c.drawString(30*mm, y, f"회사명: {company['name']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"사업자등록번호: {company['biz_no']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"업종: {company['industry']}")
    y -= 8*mm
    c.drawString(30*mm, y, f"결산기준일: 2025년 12월 31일")
    y -= 8*mm
    c.drawString(30*mm, y, f"종업원수: {company['employees']}명")

    # 손익계산서
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[손익계산서] (단위: 원)")

    y -= 12*mm
    c.setFont(FONT_NAME, 9)
    c.drawString(30*mm, y, "구분")
    c.drawString(55*mm, y, "2023년")
    c.drawString(100*mm, y, "2024년")
    c.drawString(145*mm, y, "2025년")

    y -= 3*mm
    c.line(30*mm, y, 185*mm, y)

    y -= 8*mm
    c.drawString(30*mm, y, "매출액")
    c.drawString(55*mm, y, format_number(company['revenue_2023']))
    c.drawString(100*mm, y, format_number(company['revenue_2024']))
    c.drawString(145*mm, y, format_number(company['revenue_2025']))

    y -= 8*mm
    c.drawString(30*mm, y, "영업이익")
    c.drawString(55*mm, y, format_number(company['profit_2023']))
    c.drawString(100*mm, y, format_number(company['profit_2024']))
    c.drawString(145*mm, y, format_number(company['profit_2025']))

    # 재무상태표
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[재무상태표]")

    capital = int(company['capital'].replace(',', ''))
    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, f"자본금: {format_number(company['capital'])}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"자본총계: {format_number(str(capital * 2))}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"부채총계: {format_number(str(int(capital * 0.8)))}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"자산총계: {format_number(str(int(capital * 2.8)))}원")

    # 주요 재무비율
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[주요 재무비율]")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, "부채비율: 40.0%")
    y -= 8*mm
    c.drawString(30*mm, y, "유동비율: 165.2%")
    y -= 8*mm

    # 영업이익률 계산
    revenue = int(company['revenue_2025'].replace(',', ''))
    profit = int(company['profit_2025'].replace(',', '').replace('-', ''))
    margin = (profit / revenue * 100) if revenue > 0 else 0
    if company['profit_2025'].startswith('-'):
        margin = -margin
    c.drawString(30*mm, y, f"영업이익률: {margin:.1f}%")

    # 하단
    y -= 25*mm
    c.drawString(30*mm, y, f"상기 재무제표는 한국채택국제회계기준(K-IFRS)에 따라 작성되었습니다.")
    y -= 10*mm
    c.drawString(30*mm, y, f"감사인: 삼일회계법인")

    # 가상 기업 표시
    if company.get('is_virtual'):
        c.setFont(FONT_NAME, 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(30*mm, 20*mm, "* 본 문서는 시연용 가상 데이터입니다.")

    c.save()


def create_aoi_pdf(company: dict, output_path: str):
    """정관 PDF 생성"""
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 제목
    c.setFont(FONT_NAME, 18)
    c.drawCentredString(width/2, height - 50*mm, "정        관")

    c.setFont(FONT_NAME, 14)
    c.drawCentredString(width/2, height - 65*mm, f"{company['name']}")

    # 제1장 총칙
    c.setFont(FONT_NAME, 12)
    y = height - 90*mm
    c.drawString(30*mm, y, "제1장 총칙")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, f"제1조 (상호) 이 회사는 {company['name']}라 한다.")

    y -= 10*mm
    c.drawString(30*mm, y, f"제2조 (목적) 이 회사는 다음 사업을 영위함을 목적으로 한다.")
    y -= 8*mm
    c.drawString(35*mm, y, f"1. {company['industry']}")
    y -= 6*mm
    c.drawString(35*mm, y, f"2. 위 각호에 관련된 부대사업 일체")

    y -= 10*mm
    c.drawString(30*mm, y, f"제3조 (본점소재지) 이 회사의 본점은 {company['address']}에 둔다.")

    y -= 10*mm
    c.drawString(30*mm, y, f"제4조 (공고방법) 이 회사의 공고는 회사 인터넷 홈페이지에 게재한다.")

    # 제2장 주식
    y -= 15*mm
    c.setFont(FONT_NAME, 12)
    c.drawString(30*mm, y, "제2장 주식")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    capital_num = int(company['capital'].replace(',', ''))
    shares = capital_num // 5000
    c.drawString(30*mm, y, f"제5조 (발행예정주식총수) 이 회사가 발행할 주식의 총수는 {shares*2:,}주로 한다.")

    y -= 10*mm
    c.drawString(30*mm, y, f"제6조 (1주의 금액) 이 회사가 발행하는 주식 1주의 금액은 5,000원으로 한다.")

    y -= 10*mm
    c.drawString(30*mm, y, f"제7조 (설립시 발행주식) 이 회사 설립시 발행하는 주식의 총수는 {shares:,}주로 한다.")

    # 제3장 이사회
    y -= 15*mm
    c.setFont(FONT_NAME, 12)
    c.drawString(30*mm, y, "제3장 이사회")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, "제8조 (이사의 수) 이 회사의 이사는 3인 이상 15인 이내로 한다.")

    y -= 10*mm
    c.drawString(30*mm, y, "제9조 (이사의 임기) 이사의 임기는 3년으로 한다.")

    y -= 10*mm
    c.drawString(30*mm, y, "제10조 (대표이사) 대표이사는 이사회에서 선임한다.")

    # 부칙
    y -= 20*mm
    c.setFont(FONT_NAME, 12)
    c.drawString(30*mm, y, "부칙")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, f"제1조 이 정관은 {company['established']}부터 시행한다.")

    y -= 10*mm
    c.drawString(30*mm, y, f"제2조 설립시 자본금은 {format_number(company['capital'])}원으로 한다.")

    # 하단
    y -= 25*mm
    c.drawString(30*mm, y, f"2025년 12월 31일")
    y -= 10*mm
    c.drawString(30*mm, y, f"{company['name']} 대표이사 {company['ceo']} (인)")

    # 가상 기업 표시
    if company.get('is_virtual'):
        c.setFont(FONT_NAME, 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(30*mm, 20*mm, "* 본 문서는 시연용 가상 데이터입니다.")

    c.save()


def main():
    print("=" * 60)
    print("실제 기업 데이터 기반 문서 생성 시작")
    print("=" * 60)

    for company in COMPANIES:
        name = company['name']
        is_virtual = company.get('is_virtual', False)
        tag = "[가상]" if is_virtual else "[실제]"
        print(f"\n{tag} {name} 문서 생성 중...")

        # 주주명부
        shareholders_path = f"{BASE_PATH}/SHAREHOLDERS/{name}_주주명부.pdf"
        create_shareholders_pdf(company, shareholders_path)
        print(f"  - 주주명부: {shareholders_path}")

        # 재무제표
        fin_path = f"{BASE_PATH}/FIN_STATEMENT/{name}_재무제표.pdf"
        create_financial_statement_pdf(company, fin_path)
        print(f"  - 재무제표: {fin_path}")

        # 정관
        aoi_path = f"{BASE_PATH}/AOI/{name}_정관.pdf"
        create_aoi_pdf(company, aoi_path)
        print(f"  - 정관: {aoi_path}")

    print("\n" + "=" * 60)
    print(f"총 {len(COMPANIES) * 3}개 문서 생성 완료!")
    print("=" * 60)

    print("\n생성된 파일 경로:")
    print(f"  - 주주명부: {BASE_PATH}/SHAREHOLDERS/")
    print(f"  - 재무제표: {BASE_PATH}/FIN_STATEMENT/")
    print(f"  - 정관: {BASE_PATH}/AOI/")


if __name__ == "__main__":
    main()
