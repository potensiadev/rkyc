"""
Articles of Incorporation Parser
정관 파서
"""

import logging
import re
from typing import Optional

from .base import BaseDocParser

logger = logging.getLogger(__name__)


class AoiParser(BaseDocParser):
    """
    Parser for Korean Articles of Incorporation (정관).

    Extracts:
    - corp_name: 상호
    - purpose: 목적
    - head_office_location: 본점 소재지
    - total_shares_authorized: 발행할 주식 총수
    - par_value: 1주의 금액
    - share_types: 주식의 종류
    - fiscal_year_end: 사업연도 종료일
    - dividend_policy: 배당 정책
    - board_composition: 이사회 구성
    - last_amended_date: 최종 개정일
    """

    DOC_TYPE = "AOI"

    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for articles of incorporation fields.
        """
        return {
            # 상호
            "corp_name": r"(?:제\s*\d+\s*조[^상]*)?상\s*호[:\s]*[^\n]*?(?:본\s*회사[는의]?\s*)?(주식회사[^\n]+|[^\n]*주식회사)",

            # 목적
            "purpose": r"(?:제\s*\d+\s*조[^목]*)?목\s*적[:\s]*(.+?)(?=제\s*\d+\s*조|본\s*점)",

            # 본점 소재지
            "head_office_location": r"본\s*점[^소]*소재지[:\s]*([^\n]+?)(?:\n|제|$)",

            # 발행할 주식 총수
            "total_shares_authorized": r"발행할\s*주식[의\s]*(?:총수)?[:\s]*([\d,]+)\s*주",

            # 1주의 금액
            "par_value": r"(?:1주[의\s]*금액|액면가)[:\s]*(?:금\s*)?([\d,]+)\s*원",

            # 사업연도
            "fiscal_year_end": r"사업\s*연도[:\s]*([^\n]+?)(?:\n|제|$)",

            # 최종 개정일
            "last_amended_date": r"(?:최종\s*)?개정[:\s]*(\d{4}[.\-/년]?\s*\d{1,2}[.\-/월]?\s*\d{1,2}[일]?)",
        }

    def parse(self, pdf_path: str) -> dict:
        """
        Parse articles of incorporation PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of extracted facts,
                "raw_text": first 500 chars
            }
        """
        logger.info(f"Parsing articles of incorporation: {pdf_path}")

        # Step 1: Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("Empty text extracted from PDF")
            return {"facts": [], "raw_text": ""}

        # Step 2: Apply regex patterns
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)

        # Step 3: Extract additional structured data
        share_types = self._extract_share_types(text)
        if share_types:
            results["share_types"] = share_types

        board_info = self._extract_board_info(text)
        if board_info:
            results["board_composition"] = board_info

        # Step 4: Post-process extracted values
        results = self._post_process(results)

        # Step 5: LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                "정관"
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        # Step 6: Build facts
        facts = self.build_facts(results, failed_fields, text)

        logger.info(f"Extracted {len(facts)} facts from articles of incorporation")

        return {
            "facts": facts,
            "raw_text": text[:500],
        }

    def _extract_share_types(self, text: str) -> list[str]:
        """
        Extract types of shares mentioned in the document.
        """
        share_types = []

        # Common share type patterns
        patterns = [
            r"보통주",
            r"우선주",
            r"상환주식",
            r"전환주식",
            r"무의결권주",
        ]

        for pattern in patterns:
            if re.search(pattern, text):
                share_types.append(pattern)

        return share_types

    def _extract_board_info(self, text: str) -> dict:
        """
        Extract board of directors composition information.
        """
        board_info = {}

        # 이사 수
        director_match = re.search(
            r"이사[는의\s]*(\d+)\s*인\s*(?:이상\s*)?(?:(\d+)\s*인\s*이하)?",
            text
        )
        if director_match:
            board_info["min_directors"] = int(director_match.group(1))
            if director_match.group(2):
                board_info["max_directors"] = int(director_match.group(2))

        # 감사 수
        auditor_match = re.search(
            r"감사[는의\s]*(\d+)\s*인",
            text
        )
        if auditor_match:
            board_info["auditors"] = int(auditor_match.group(1))

        return board_info if board_info else None

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

            if key == "total_shares_authorized":
                # Keep only digits
                value = re.sub(r'[^\d]', '', str(value))
                if value:
                    value = int(value)

            elif key == "par_value":
                # Keep only digits
                value = re.sub(r'[^\d]', '', str(value))
                if value:
                    value = int(value)

            elif key == "last_amended_date":
                # Normalize date format
                value = re.sub(r'[년월]', '-', value)
                value = re.sub(r'[일\s]', '', value)
                value = re.sub(r'\.', '-', value)
                value = re.sub(r'-+', '-', value)
                value = value.strip('-')

            elif key == "purpose":
                # Clean up purpose text
                value = re.sub(r'\s+', ' ', value)
                value = value.strip()
                # Truncate if too long
                if len(value) > 1000:
                    value = value[:1000] + "..."

            elif key == "fiscal_year_end":
                # Extract month/day info
                month_match = re.search(r'(\d{1,2})\s*월', value)
                day_match = re.search(r'(\d{1,2})\s*일', value)
                if month_match and day_match:
                    value = f"{month_match.group(1)}월 {day_match.group(1)}일"

            processed[key] = value

        return processed
