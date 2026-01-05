"""
Corporate Registry Certificate Parser
법인 등기부등본 파서
"""

import logging
import re
from typing import Optional

from .base import BaseDocParser

logger = logging.getLogger(__name__)


class RegistryParser(BaseDocParser):
    """
    Parser for Korean Corporate Registry Certificate (법인 등기부등본).

    Extracts:
    - corp_name: 상호
    - corp_reg_no: 등록번호
    - address: 본점 소재지
    - purpose: 목적사항
    - capital: 자본금
    - issue_amount: 발행주식총수
    - ceo_name: 대표이사
    - directors: 이사/감사 목록
    - established_date: 설립일
    - last_change_date: 최종 변경일
    """

    DOC_TYPE = "REGISTRY"

    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for corporate registry fields.
        """
        return {
            # 상호
            "corp_name": r"상\s*호[:\s]*([^\n]+?)(?:\n|본점|등록)",

            # 등록번호
            "corp_reg_no": r"등록\s*번호[:\s]*(\d{6}[-\s]?\d{7})",

            # 본점 소재지
            "address": r"본\s*점[:\s]*([^\n]+?)(?:\n|목적|공고)",

            # 목적사항 (복수 라인 가능)
            "purpose": r"목\s*적[:\s]*(.+?)(?=자본금|발행|임원|$)",

            # 자본금
            "capital": r"자본(?:금|의\s*총액)[:\s]*(?:금\s*)?([\d,]+)\s*원",

            # 발행주식총수
            "issue_amount": r"발행(?:주식)?총수[:\s]*([\d,]+)\s*주",

            # 대표이사
            "ceo_name": r"대표\s*이사[:\s]*([^\n]+?)(?:\n|이사|감사|$)",

            # 설립일
            "established_date": r"(?:설립|등기)\s*연월일[:\s]*(\d{4}[.\-/년]?\s*\d{1,2}[.\-/월]?\s*\d{1,2}[일]?)",

            # 최종 변경일
            "last_change_date": r"(?:최종)?변경\s*(?:등기\s*)?일[:\s]*(\d{4}[.\-/년]?\s*\d{1,2}[.\-/월]?\s*\d{1,2}[일]?)",
        }

    def parse(self, pdf_path: str) -> dict:
        """
        Parse corporate registry certificate PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of extracted facts,
                "raw_text": first 500 chars
            }
        """
        logger.info(f"Parsing corporate registry: {pdf_path}")

        # Step 1: Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("Empty text extracted from PDF")
            return {"facts": [], "raw_text": ""}

        # Step 2: Apply regex patterns
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)

        # Step 3: Extract directors list separately
        directors = self._extract_directors(text)
        if directors:
            results["directors"] = directors

        # Step 4: Post-process extracted values
        results = self._post_process(results)

        # Step 5: LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                "법인 등기부등본"
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        # Step 6: Build facts
        facts = self.build_facts(results, failed_fields, text)

        logger.info(f"Extracted {len(facts)} facts from corporate registry")

        return {
            "facts": facts,
            "raw_text": text[:500],
        }

    def _extract_directors(self, text: str) -> list[dict]:
        """
        Extract list of directors and auditors.

        Returns:
            list[dict]: List of {name, position, appointed_date}
        """
        directors = []

        # Pattern for director entries
        # 이사 홍길동 2023.01.01 취임
        pattern = r"(이사|대표이사|사내이사|사외이사|감사|상무이사|전무이사)[:\s]+([가-힣]+)[:\s]+(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})"

        matches = re.findall(pattern, text)

        for match in matches:
            position, name, date = match
            directors.append({
                "position": position,
                "name": name,
                "appointed_date": date,
            })

        return directors

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

            if key == "corp_reg_no":
                # Normalize to XXXXXX-XXXXXXX format
                value = re.sub(r'[\s-]', '', value)
                if len(value) == 13:
                    value = f"{value[:6]}-{value[6:]}"

            elif key in ("established_date", "last_change_date"):
                # Normalize date format
                value = re.sub(r'[년월]', '-', value)
                value = re.sub(r'[일\s]', '', value)
                value = re.sub(r'\.', '-', value)
                value = re.sub(r'-+', '-', value)
                value = value.strip('-')

            elif key == "capital":
                # Keep only digits
                value = re.sub(r'[^\d]', '', value)
                if value:
                    value = int(value)

            elif key == "issue_amount":
                # Keep only digits
                value = re.sub(r'[^\d]', '', value)
                if value:
                    value = int(value)

            elif key == "purpose":
                # Clean up purpose text
                value = re.sub(r'\s+', ' ', value)
                value = value.strip()

            processed[key] = value

        return processed
