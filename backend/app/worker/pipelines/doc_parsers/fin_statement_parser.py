"""
Financial Statement Parser
재무제표 파서
"""

import logging
import re
from typing import Optional

from .base import BaseDocParser

logger = logging.getLogger(__name__)


class FinStatementParser(BaseDocParser):
    """
    Parser for Korean Financial Statements (재무제표).

    Extracts:
    - fiscal_year: 사업연도
    - total_assets: 자산총계
    - total_liabilities: 부채총계
    - total_equity: 자본총계
    - revenue: 매출액
    - operating_income: 영업이익
    - net_income: 당기순이익
    - current_assets: 유동자산
    - current_liabilities: 유동부채
    - retained_earnings: 이익잉여금
    - debt_ratio: 부채비율 (계산값)
    - current_ratio: 유동비율 (계산값)
    """

    DOC_TYPE = "FIN_STATEMENT"

    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for financial statement fields.
        """
        return {
            # 사업연도
            "fiscal_year": r"(?:제\s*)?(\d+)\s*기|(\d{4})[년도\s]*(?:결산|재무)",

            # 자산총계
            "total_assets": r"자산\s*총계[:\s]*([\d,]+)",

            # 부채총계
            "total_liabilities": r"부채\s*총계[:\s]*([\d,]+)",

            # 자본총계
            "total_equity": r"자본\s*총계[:\s]*([\d,]+)",

            # 매출액
            "revenue": r"매출\s*(?:액|총액)[:\s]*([\d,]+)",

            # 영업이익
            "operating_income": r"영업\s*(?:이익|손익)[:\s]*([\d,\-\(\)]+)",

            # 당기순이익
            "net_income": r"(?:당기)?순\s*(?:이익|손익)[:\s]*([\d,\-\(\)]+)",

            # 유동자산
            "current_assets": r"유동\s*자산[:\s]*([\d,]+)",

            # 유동부채
            "current_liabilities": r"유동\s*부채[:\s]*([\d,]+)",

            # 이익잉여금
            "retained_earnings": r"(?:이익)?잉여금[:\s]*([\d,\-\(\)]+)",
        }

    def parse(self, pdf_path: str) -> dict:
        """
        Parse financial statement PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of extracted facts,
                "raw_text": first 500 chars
            }
        """
        logger.info(f"Parsing financial statement: {pdf_path}")

        # Step 1: Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("Empty text extracted from PDF")
            return {"facts": [], "raw_text": ""}

        # Step 2: Try to extract from tables first
        tables = self.extract_tables_from_pdf(pdf_path)
        table_results = self._parse_financial_tables(tables)

        # Step 3: Apply regex patterns
        patterns = self.get_regex_patterns()
        regex_results, failed_fields = self.extract_with_regex(text, patterns)

        # Merge results (table takes precedence)
        results = {**regex_results, **table_results}
        failed_fields = [f for f in failed_fields if f not in table_results]

        # Step 4: Post-process extracted values
        results = self._post_process(results)

        # Step 5: Calculate financial ratios
        ratios = self._calculate_ratios(results)
        results.update(ratios)

        # Step 6: LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                "재무제표"
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        # Step 7: Build facts
        facts = self.build_facts(results, failed_fields, text)

        logger.info(f"Extracted {len(facts)} facts from financial statement")

        return {
            "facts": facts,
            "raw_text": text[:500],
        }

    def _parse_financial_tables(self, tables: list) -> dict:
        """
        Parse financial data from extracted tables.

        Expected table formats:
        - Balance Sheet: 계정과목 | 당기 | 전기
        - Income Statement: 계정과목 | 금액

        Returns:
            dict: Extracted financial figures
        """
        results = {}

        # Map Korean account names to field keys
        account_map = {
            "자산총계": "total_assets",
            "자산합계": "total_assets",
            "부채총계": "total_liabilities",
            "부채합계": "total_liabilities",
            "자본총계": "total_equity",
            "자본합계": "total_equity",
            "매출액": "revenue",
            "매출": "revenue",
            "영업이익": "operating_income",
            "영업손익": "operating_income",
            "당기순이익": "net_income",
            "당기순손익": "net_income",
            "순이익": "net_income",
            "유동자산": "current_assets",
            "유동부채": "current_liabilities",
            "이익잉여금": "retained_earnings",
        }

        for table in tables:
            if not table or len(table) < 2:
                continue

            for row in table:
                if not row or len(row) < 2:
                    continue

                # First column is usually account name
                account = str(row[0]).strip() if row[0] else ""

                # Check if this is a known account
                for korean_name, field_key in account_map.items():
                    if korean_name in account:
                        # Find the numeric value (usually 2nd or 3rd column)
                        for cell in row[1:]:
                            if cell:
                                value_str = str(cell)
                                # Extract numeric value
                                value = re.sub(r'[^\d\-\(\)]', '', value_str)
                                if value:
                                    # Handle negative values in parentheses
                                    if '(' in value or ')' in value:
                                        value = value.replace('(', '-').replace(')', '')
                                    try:
                                        results[field_key] = int(value)
                                        break
                                    except ValueError:
                                        continue

        return results

    def _post_process(self, results: dict) -> dict:
        """
        Post-process extracted values for normalization.
        """
        processed = {}

        for key, value in results.items():
            if value is None:
                continue

            if isinstance(value, str):
                value = value.strip()

                # Handle numeric string values
                if key in (
                    "total_assets", "total_liabilities", "total_equity",
                    "revenue", "operating_income", "net_income",
                    "current_assets", "current_liabilities", "retained_earnings"
                ):
                    # Handle negative values in parentheses
                    if '(' in value or ')' in value:
                        value = value.replace('(', '-').replace(')', '')

                    # Keep only digits and minus sign
                    value = re.sub(r'[^\d\-]', '', value)
                    if value:
                        try:
                            value = int(value)
                        except ValueError:
                            continue

                elif key == "fiscal_year":
                    # Extract year number
                    year_match = re.search(r'(\d{4})', value)
                    if year_match:
                        value = int(year_match.group(1))

            processed[key] = value

        return processed

    def _calculate_ratios(self, results: dict) -> dict:
        """
        Calculate financial ratios from extracted figures.
        """
        ratios = {}

        # 부채비율 = 부채총계 / 자본총계 * 100
        if results.get("total_liabilities") and results.get("total_equity"):
            try:
                liabilities = results["total_liabilities"]
                equity = results["total_equity"]
                if equity != 0:
                    ratios["debt_ratio"] = round(liabilities / equity * 100, 2)
            except (TypeError, ZeroDivisionError):
                pass

        # 유동비율 = 유동자산 / 유동부채 * 100
        if results.get("current_assets") and results.get("current_liabilities"):
            try:
                current_assets = results["current_assets"]
                current_liabilities = results["current_liabilities"]
                if current_liabilities != 0:
                    ratios["current_ratio"] = round(
                        current_assets / current_liabilities * 100, 2
                    )
            except (TypeError, ZeroDivisionError):
                pass

        # 자기자본비율 = 자본총계 / 자산총계 * 100
        if results.get("total_equity") and results.get("total_assets"):
            try:
                equity = results["total_equity"]
                assets = results["total_assets"]
                if assets != 0:
                    ratios["equity_ratio"] = round(equity / assets * 100, 2)
            except (TypeError, ZeroDivisionError):
                pass

        # 영업이익률 = 영업이익 / 매출액 * 100
        if results.get("operating_income") and results.get("revenue"):
            try:
                operating_income = results["operating_income"]
                revenue = results["revenue"]
                if revenue != 0:
                    ratios["operating_margin"] = round(
                        operating_income / revenue * 100, 2
                    )
            except (TypeError, ZeroDivisionError):
                pass

        return ratios
