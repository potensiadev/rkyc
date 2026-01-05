"""
Business Registration Certificate Parser
사업자등록증 파서
"""

import logging
import re
from typing import Optional

from .base import BaseDocParser

logger = logging.getLogger(__name__)


class BizRegParser(BaseDocParser):
    """
    Parser for Korean Business Registration Certificate (사업자등록증).

    Extracts:
    - biz_no: 사업자등록번호 (XXX-XX-XXXXX)
    - corp_name: 상호/법인명
    - ceo_name: 대표자명
    - address: 사업장 소재지
    - biz_type: 업태
    - biz_item: 종목
    - open_date: 개업연월일
    - corp_reg_no: 법인등록번호 (법인인 경우)
    """

    DOC_TYPE = "BIZ_REG"

    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for business registration fields.

        Korean business registration certificates have standardized format.
        """
        return {
            # 사업자등록번호: XXX-XX-XXXXX format
            "biz_no": r"사업자\s*등록\s*번호[:\s]*(\d{3}[-\s]?\d{2}[-\s]?\d{5})",

            # 상호/법인명
            "corp_name": r"(?:상\s*호|법\s*인\s*명)[:\s]*([^\n]+?)(?:\n|법인|대표|사업)",

            # 대표자
            "ceo_name": r"대\s*표\s*자[:\s]*([^\n]+?)(?:\n|주민|생년|사업)",

            # 사업장 소재지
            "address": r"사업장\s*소재지[:\s]*([^\n]+?)(?:\n|업\s*태|종\s*목|$)",

            # 업태
            "biz_type": r"업\s*태[:\s]*([^\n]+?)(?:\n|종\s*목|사업|$)",

            # 종목
            "biz_item": r"종\s*목[:\s]*([^\n]+?)(?:\n|개업|사업|$)",

            # 개업연월일
            "open_date": r"개업\s*연\s*월\s*일[:\s]*(\d{4}[.\-/년]?\s*\d{1,2}[.\-/월]?\s*\d{1,2}[일]?)",

            # 법인등록번호 (법인인 경우)
            "corp_reg_no": r"법인\s*등록\s*번호[:\s]*(\d{6}[-\s]?\d{7})",
        }

    def parse(self, pdf_path: str) -> dict:
        """
        Parse business registration certificate PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of extracted facts,
                "raw_text": first 500 chars
            }
        """
        logger.info(f"Parsing business registration: {pdf_path}")

        # Step 1: Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("Empty text extracted from PDF")
            return {"facts": [], "raw_text": ""}

        # Step 2: Apply regex patterns
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)

        # Step 3: Post-process extracted values
        results = self._post_process(results)

        # Step 4: LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                "사업자등록증"
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        # Step 5: Build facts
        facts = self.build_facts(results, failed_fields, text)

        logger.info(f"Extracted {len(facts)} facts from business registration")

        return {
            "facts": facts,
            "raw_text": text[:500],
        }

    def _post_process(self, results: dict) -> dict:
        """
        Post-process extracted values for normalization.
        """
        processed = {}

        for key, value in results.items():
            if value is None:
                continue

            value = value.strip()

            if key == "biz_no":
                # Normalize to XXX-XX-XXXXX format
                value = re.sub(r'[\s-]', '', value)
                if len(value) == 10:
                    value = f"{value[:3]}-{value[3:5]}-{value[5:]}"

            elif key == "corp_reg_no":
                # Normalize to XXXXXX-XXXXXXX format
                value = re.sub(r'[\s-]', '', value)
                if len(value) == 13:
                    value = f"{value[:6]}-{value[6:]}"

            elif key == "open_date":
                # Normalize date format to YYYY-MM-DD
                value = re.sub(r'[년월]', '-', value)
                value = re.sub(r'[일\s]', '', value)
                value = re.sub(r'\.', '-', value)
                # Clean up multiple dashes
                value = re.sub(r'-+', '-', value)
                value = value.strip('-')

            elif key in ("biz_type", "biz_item"):
                # Remove trailing punctuation
                value = re.sub(r'[,\.\s]+$', '', value)

            processed[key] = value

        return processed

    def validate_biz_no(self, biz_no: str) -> bool:
        """
        Validate Korean business registration number using checksum.

        The last digit is a check digit calculated from the first 9 digits.

        Args:
            biz_no: Business registration number (XXX-XX-XXXXX format)

        Returns:
            bool: True if valid
        """
        # Remove dashes
        digits = re.sub(r'[^0-9]', '', biz_no)

        if len(digits) != 10:
            return False

        # Checksum weights
        weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]

        try:
            total = sum(int(digits[i]) * weights[i] for i in range(9))
            # Add last weighted value divided by 10
            total += (int(digits[8]) * 5) // 10
            check_digit = (10 - (total % 10)) % 10

            return int(digits[9]) == check_digit
        except (ValueError, IndexError):
            return False
