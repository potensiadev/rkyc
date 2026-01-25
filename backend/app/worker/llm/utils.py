"""
LLM Utilities - Common functions for LLM operations

This module contains shared utilities used across LLM-related modules
to prevent circular import issues.
"""

import logging
import re

logger = logging.getLogger(__name__)


# P1-8 Fix: Prompt Injection 방어를 위한 금지 패턴
_PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:the\s+)?(?:above|previous)\s+instructions?",
    r"disregard\s+(?:the\s+)?(?:above|previous)",
    r"forget\s+(?:everything|all)",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?:",
    r"system\s*:",
    r"</?(?:system|user|assistant)>",
]


def sanitize_input_for_prompt(text: str, field_name: str = "input") -> str:
    """
    P1-8 Fix: LLM 프롬프트에 사용되는 사용자 입력을 안전하게 처리

    Args:
        text: 사용자 입력 (기업명, 업종명 등)
        field_name: 필드명 (로깅용)

    Returns:
        Sanitized text (위험 패턴 제거)

    Raises:
        ValueError: 입력이 너무 길거나 의심스러운 패턴 포함 시
    """
    if not text:
        return ""

    # 1. 길이 제한 (기업명/업종명은 100자면 충분)
    if len(text) > 100:
        logger.warning(f"[PromptSanitizer] {field_name} too long ({len(text)}), truncating")
        text = text[:100]

    # 2. 위험 패턴 탐지
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.error(f"[PromptSanitizer] Prompt injection detected in {field_name}: {text[:50]}...")
            raise ValueError(f"Suspicious input detected in {field_name}")

    # 3. 특수문자 정규화 (제어문자 제거, 줄바꿈 → 공백)
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)  # 제어문자 제거
    text = re.sub(r"\s+", " ", text).strip()  # 연속 공백 정리

    return text
