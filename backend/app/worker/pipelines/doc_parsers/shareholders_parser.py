"""
Shareholder Registry Parser
주주명부 파서
"""

import logging
import re
from typing import Optional

from .base import BaseDocParser

logger = logging.getLogger(__name__)


class ShareholdersParser(BaseDocParser):
    """
    Parser for Korean Shareholder Registry (주주명부).

    Extracts:
    - total_shares: 발행주식총수
    - shareholders: 주주 목록 [{name, shares, ratio}]
    - largest_shareholder: 최대주주
    - largest_shareholder_ratio: 최대주주 지분율
    - record_date: 기준일
    """

    DOC_TYPE = "SHAREHOLDERS"

    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for shareholder registry fields.
        """
        return {
            # 발행주식총수
            "total_shares": r"(?:발행)?주식\s*(?:총수|합계)[:\s]*([\d,]+)\s*주?",

            # 최대주주 (단일 매칭)
            "largest_shareholder": r"(?:최대|제1)\s*주주[:\s]*([가-힣a-zA-Z\s]+?)(?:\n|\d|지분)",

            # 최대주주 지분율
            "largest_shareholder_ratio": r"(?:최대|제1)\s*주주[^\d]*(\d+[.\d]*)\s*%",

            # 기준일
            "record_date": r"기준\s*일[:\s]*(\d{4}[.\-/년]?\s*\d{1,2}[.\-/월]?\s*\d{1,2}[일]?)",
        }

    def parse(self, pdf_path: str) -> dict:
        """
        Parse shareholder registry PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of extracted facts,
                "raw_text": first 500 chars
            }
        """
        logger.info(f"Parsing shareholder registry: {pdf_path}")

        # Step 1: Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("Empty text extracted from PDF")
            return {"facts": [], "raw_text": ""}

        # Step 2: Try to extract table data
        tables = self.extract_tables_from_pdf(pdf_path)
        shareholders = self._parse_shareholder_table(tables)

        # Step 3: Apply regex patterns
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)

        # Add shareholders list if extracted
        if shareholders:
            results["shareholders"] = shareholders

        # Step 4: Post-process extracted values
        results = self._post_process(results)

        # Step 5: LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                "주주명부"
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        # Step 6: Build facts
        facts = self.build_facts(results, failed_fields, text)

        logger.info(f"Extracted {len(facts)} facts from shareholder registry")

        return {
            "facts": facts,
            "raw_text": text[:500],
        }

    def _parse_shareholder_table(self, tables: list) -> list[dict]:
        """
        Parse shareholder information from extracted tables.

        Expected table format:
        | 주주명 | 주식수 | 지분율 |

        Returns:
            list[dict]: List of {name, shares, ratio}
        """
        shareholders = []

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Try to find header row
            header_idx = -1
            for i, row in enumerate(table):
                if row and any(
                    cell and ("주주" in str(cell) or "성명" in str(cell))
                    for cell in row
                ):
                    header_idx = i
                    break

            if header_idx < 0:
                continue

            # Find column indices
            header = table[header_idx]
            name_col = shares_col = ratio_col = -1

            for j, cell in enumerate(header):
                if cell:
                    cell_str = str(cell)
                    if "주주" in cell_str or "성명" in cell_str:
                        name_col = j
                    elif "주식" in cell_str or "수량" in cell_str:
                        shares_col = j
                    elif "지분" in cell_str or "비율" in cell_str:
                        ratio_col = j

            if name_col < 0:
                continue

            # Extract shareholder data
            for row in table[header_idx + 1:]:
                if not row or len(row) <= name_col:
                    continue

                name = row[name_col]
                if not name or name == "합계" or name == "총계":
                    continue

                shareholder = {"name": str(name).strip()}

                if shares_col >= 0 and len(row) > shares_col:
                    shares = row[shares_col]
                    if shares:
                        shares_num = re.sub(r'[^\d]', '', str(shares))
                        if shares_num:
                            shareholder["shares"] = int(shares_num)

                if ratio_col >= 0 and len(row) > ratio_col:
                    ratio = row[ratio_col]
                    if ratio:
                        ratio_match = re.search(r'(\d+[.\d]*)', str(ratio))
                        if ratio_match:
                            shareholder["ratio"] = float(ratio_match.group(1))

                shareholders.append(shareholder)

        return shareholders

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

            if key == "total_shares":
                # Keep only digits
                value = re.sub(r'[^\d]', '', str(value))
                if value:
                    value = int(value)

            elif key == "largest_shareholder_ratio":
                # Parse as float
                try:
                    value = float(value)
                except ValueError:
                    pass

            elif key == "record_date":
                # Normalize date format
                value = re.sub(r'[년월]', '-', value)
                value = re.sub(r'[일\s]', '', value)
                value = re.sub(r'\.', '-', value)
                value = re.sub(r'-+', '-', value)
                value = value.strip('-')

            processed[key] = value

        return processed
