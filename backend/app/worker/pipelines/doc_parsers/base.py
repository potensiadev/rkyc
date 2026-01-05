"""
Base Document Parser Class
PDF text parsing + regex extraction + LLM fallback
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


class BaseDocParser(ABC):
    """
    Base class for document parsers.

    Processing flow:
    1. Extract text from PDF using pdfplumber
    2. Apply regex patterns to extract structured data
    3. For failed fields, fall back to LLM extraction
    4. Return structured facts
    """

    DOC_TYPE: str = "UNKNOWN"

    def __init__(self, llm_service=None):
        """
        Initialize parser with optional LLM service for fallback.

        Args:
            llm_service: LLMService instance for fallback extraction
        """
        self.llm = llm_service

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract all text content from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text content
        """
        text_content = []
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

            full_text = "\n".join(text_content)
            logger.debug(f"Extracted {len(full_text)} characters from {pdf_path}")
            return full_text

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

    def extract_tables_from_pdf(self, pdf_path: str) -> list[list]:
        """
        Extract tables from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            list[list]: List of tables (each table is a list of rows)
        """
        tables = []
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)

            logger.debug(f"Extracted {len(tables)} tables from {pdf_path}")
            return tables

        except Exception as e:
            logger.error(f"Failed to extract tables from PDF: {e}")
            return []

    @abstractmethod
    def parse(self, pdf_path: str) -> dict:
        """
        Parse document and extract facts.

        Must be implemented by subclasses.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "facts": list of fact dicts,
                "raw_text": first 500 chars of text
            }
        """
        pass

    @abstractmethod
    def get_regex_patterns(self) -> dict:
        """
        Return regex patterns for field extraction.

        Must be implemented by subclasses.

        Returns:
            dict: {field_name: regex_pattern}
        """
        pass

    def extract_with_regex(self, text: str, patterns: dict) -> tuple[dict, list]:
        """
        Extract fields using regex patterns.

        Args:
            text: Full text content
            patterns: Dict of {field_name: regex_pattern}

        Returns:
            tuple: (results dict, list of failed fields)
        """
        results = {}
        failed_fields = []

        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
                if match:
                    # Get first capturing group
                    value = match.group(1).strip()
                    # Clean up whitespace
                    value = re.sub(r'\s+', ' ', value)
                    results[field_name] = value
                else:
                    failed_fields.append(field_name)
            except Exception as e:
                logger.warning(f"Regex error for field {field_name}: {e}")
                failed_fields.append(field_name)

        logger.info(
            f"Regex extraction: {len(results)} success, {len(failed_fields)} failed"
        )
        return results, failed_fields

    def fallback_to_llm(
        self,
        text: str,
        failed_fields: list,
        doc_type_name: str
    ) -> dict:
        """
        Use LLM to extract fields that regex failed to capture.

        Args:
            text: Full text content (will be truncated)
            failed_fields: List of field names to extract
            doc_type_name: Human-readable document type name

        Returns:
            dict: Extracted fields from LLM
        """
        if not failed_fields or not self.llm:
            return {}

        logger.info(f"LLM fallback for {len(failed_fields)} fields: {failed_fields}")

        # Truncate text for LLM context
        max_text_length = 3000
        truncated_text = text[:max_text_length]
        if len(text) > max_text_length:
            truncated_text += "\n... (truncated)"

        prompt = f"""다음 {doc_type_name} 문서에서 아래 필드를 추출해주세요.

추출할 필드: {', '.join(failed_fields)}

문서 내용:
{truncated_text}

JSON 형식으로 응답해주세요:
{{"field_name": "value", ...}}

찾을 수 없는 필드는 null로 표시하세요."""

        messages = [{"role": "user", "content": prompt}]

        try:
            result = self.llm.call_with_json_response(messages)
            logger.info(f"LLM fallback extracted {len(result)} fields")
            return result
        except Exception as e:
            logger.error(f"LLM fallback failed: {e}")
            return {}

    def build_facts(
        self,
        results: dict,
        failed_fields: list,
        text: str
    ) -> list[dict]:
        """
        Convert extracted results to fact format.

        Args:
            results: Dict of extracted {field_name: value}
            failed_fields: List of fields that needed LLM fallback
            text: Full text for snippet extraction

        Returns:
            list[dict]: List of fact dicts
        """
        facts = []

        for field_key, field_value in results.items():
            if field_value is None:
                continue

            # Determine confidence based on extraction method
            confidence = "HIGH" if field_key not in failed_fields else "MED"

            facts.append({
                "fact_type": self.DOC_TYPE,
                "field_key": field_key,
                "field_value": field_value,
                "confidence": confidence,
                "evidence_snippet": self._get_snippet(text, str(field_value)),
            })

        return facts

    def _get_snippet(
        self,
        text: str,
        value: str,
        context_chars: int = 50
    ) -> str:
        """
        Extract text snippet around a value for evidence.

        Args:
            text: Full text
            value: Value to find
            context_chars: Number of chars before/after

        Returns:
            str: Context snippet
        """
        if not value or value not in text:
            return ""

        idx = text.find(value)
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(value) + context_chars)

        snippet = text[start:end]
        # Clean up snippet
        snippet = re.sub(r'\s+', ' ', snippet)

        return snippet

    def parse_text(self, text: str) -> dict:
        """
        Parse already extracted text (alternative to PDF parsing).

        Useful for testing or when text is already available.

        Args:
            text: Document text content

        Returns:
            dict: Same format as parse()
        """
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)

        # LLM fallback for failed fields
        if failed_fields and self.llm:
            llm_results = self.fallback_to_llm(
                text,
                failed_fields,
                self.DOC_TYPE
            )
            for key, value in llm_results.items():
                if value is not None:
                    results[key] = value

        facts = self.build_facts(results, failed_fields, text)

        return {
            "facts": facts,
            "raw_text": text[:500],
        }
