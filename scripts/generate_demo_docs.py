"""
Demo 문서 생성 스크립트
6개 기업 x 3종 문서 (주주명부, 재무제표, 정관) = 18개 PDF
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

# 기업 데이터
COMPANIES = [
    {
        "name": "엠케이전자",
        "corp_id": "8001-3719240",
        "biz_no": "135-81-06406",
        "ceo": "현기진",
        "industry": "반도체 제조업",
        "address": "경기도 화성시 동탄산업단지 123",
        "established": "2015-03-15",
        "capital": "50,000,000,000",
        "revenue_2023": "120,000,000,000",
        "revenue_2024": "145,000,000,000",
        "revenue_2025": "180,000,000,000",
        "profit_2023": "8,000,000,000",
        "profit_2024": "12,000,000,000",
        "profit_2025": "18,000,000,000",
        "shareholders": [
            ("현기진", "35.0%", "대표이사"),
            ("MK홀딩스(주)", "25.0%", "법인"),
            ("국민연금공단", "8.5%", "기관투자자"),
            ("기타소액주주", "31.5%", "-"),
        ],
    },
    {
        "name": "동부건설",
        "corp_id": "8000-7647330",
        "biz_no": "824-87-03495",
        "ceo": "윤진오",
        "industry": "종합 건설업",
        "address": "서울특별시 강남구 테헤란로 456",
        "established": "1998-07-20",
        "capital": "80,000,000,000",
        "revenue_2023": "350,000,000,000",
        "revenue_2024": "420,000,000,000",
        "revenue_2025": "480,000,000,000",
        "profit_2023": "15,000,000,000",
        "profit_2024": "22,000,000,000",
        "profit_2025": "28,000,000,000",
        "shareholders": [
            ("윤진오", "28.0%", "대표이사"),
            ("동부그룹(주)", "32.0%", "법인"),
            ("한국투자증권", "12.0%", "기관투자자"),
            ("기타소액주주", "28.0%", "-"),
        ],
    },
    {
        "name": "삼성전자",
        "corp_id": "4301-3456789",
        "biz_no": "124-81-00998",
        "ceo": "전영현",
        "industry": "전자부품 제조업",
        "address": "경기도 수원시 영통구 삼성로 129",
        "established": "1969-01-13",
        "capital": "897,514,000,000",
        "revenue_2023": "258,935,000,000,000",
        "revenue_2024": "279,000,000,000,000",
        "revenue_2025": "302,000,000,000,000",
        "profit_2023": "15,487,000,000,000",
        "profit_2024": "22,100,000,000,000",
        "profit_2025": "28,500,000,000,000",
        "shareholders": [
            ("삼성생명", "8.51%", "법인"),
            ("국민연금공단", "7.23%", "기관투자자"),
            ("삼성물산", "5.01%", "법인"),
            ("기타주주", "79.25%", "-"),
        ],
    },
    {
        "name": "휴림로봇",
        "corp_id": "6701-4567890",
        "biz_no": "109-81-60401",
        "ceo": "김봉관",
        "industry": "산업용 로봇 제조업",
        "address": "대전광역시 유성구 테크노로 55",
        "established": "2018-06-22",
        "capital": "10,000,000,000",
        "revenue_2023": "32,000,000,000",
        "revenue_2024": "48,000,000,000",
        "revenue_2025": "72,000,000,000",
        "profit_2023": "1,800,000,000",
        "profit_2024": "3,500,000,000",
        "profit_2025": "6,200,000,000",
        "shareholders": [
            ("김봉관", "38.0%", "대표이사"),
            ("한국로봇산업협회", "15.0%", "법인"),
            ("벤처캐피탈(주)", "22.0%", "투자사"),
            ("기타소액주주", "25.0%", "-"),
        ],
    },
]

BASE_PATH = "C:/kayem/coding/rkyc/data/documents/upload"


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
    c.drawString(30*mm, y, f"기준일: 2025년 12월 31일")
    y -= 8*mm
    c.drawString(30*mm, y, f"자본금: {company['capital']}원")

    # 주주 목록 헤더
    y -= 20*mm
    c.setFont(FONT_NAME, 11)
    c.drawString(30*mm, y, "주주명")
    c.drawString(80*mm, y, "지분율")
    c.drawString(120*mm, y, "비고")

    # 구분선
    y -= 3*mm
    c.line(30*mm, y, 180*mm, y)

    # 주주 목록
    c.setFont(FONT_NAME, 10)
    for name, ratio, note in company['shareholders']:
        y -= 8*mm
        c.drawString(30*mm, y, name)
        c.drawString(80*mm, y, ratio)
        c.drawString(120*mm, y, note)

    # 하단 서명
    y -= 30*mm
    c.drawString(30*mm, y, f"위와 같이 주주명부를 작성합니다.")
    y -= 15*mm
    c.drawString(30*mm, y, f"2025년 12월 31일")
    y -= 10*mm
    c.drawString(30*mm, y, f"{company['name']} 대표이사 {company['ceo']} (인)")

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

    # 손익계산서
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[손익계산서]")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, "구분")
    c.drawString(70*mm, y, "2023년")
    c.drawString(110*mm, y, "2024년")
    c.drawString(150*mm, y, "2025년")

    y -= 3*mm
    c.line(30*mm, y, 180*mm, y)

    y -= 8*mm
    c.drawString(30*mm, y, "매출액")
    c.drawString(70*mm, y, company['revenue_2023'])
    c.drawString(110*mm, y, company['revenue_2024'])
    c.drawString(150*mm, y, company['revenue_2025'])

    y -= 8*mm
    c.drawString(30*mm, y, "영업이익")
    c.drawString(70*mm, y, company['profit_2023'])
    c.drawString(110*mm, y, company['profit_2024'])
    c.drawString(150*mm, y, company['profit_2025'])

    # 재무상태표
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[재무상태표]")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, f"자본금: {company['capital']}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"자본총계: {int(company['capital'].replace(',','')) * 2:,}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"부채총계: {int(company['capital'].replace(',','')) * 1:,}원")
    y -= 8*mm
    c.drawString(30*mm, y, f"자산총계: {int(company['capital'].replace(',','')) * 3:,}원")

    # 주요 재무비율
    y -= 20*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(30*mm, y, "[주요 재무비율]")

    y -= 12*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(30*mm, y, "부채비율: 50.0%")
    y -= 8*mm
    c.drawString(30*mm, y, "유동비율: 180.5%")
    y -= 8*mm
    c.drawString(30*mm, y, "영업이익률: 8.5%")

    # 하단
    y -= 25*mm
    c.drawString(30*mm, y, f"상기 재무제표는 한국채택국제회계기준(K-IFRS)에 따라 작성되었습니다.")
    y -= 10*mm
    c.drawString(30*mm, y, f"감사인: 삼일회계법인")

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
    c.drawString(30*mm, y, "제8조 (이사의 수) 이 회사의 이사는 3인 이상 7인 이내로 한다.")

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
    c.drawString(30*mm, y, f"제2조 설립시 자본금은 {company['capital']}원으로 한다.")

    # 하단
    y -= 25*mm
    c.drawString(30*mm, y, f"2025년 12월 31일")
    y -= 10*mm
    c.drawString(30*mm, y, f"{company['name']} 대표이사 {company['ceo']} (인)")

    c.save()


def main():
    print("Demo 문서 생성 시작...")

    for company in COMPANIES:
        name = company['name']
        print(f"\n[{name}] 문서 생성 중...")

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

    print("\n" + "="*50)
    print(f"총 {len(COMPANIES) * 3}개 문서 생성 완료!")
    print("="*50)


if __name__ == "__main__":
    main()
