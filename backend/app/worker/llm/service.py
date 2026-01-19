"""
LLM Service with Fallback Chain
Multi-provider LLM integration using litellm
"""

import json
import logging
import time
from typing import Optional, Any

import litellm
from litellm import completion

from app.core.config import settings
from app.worker.llm.exceptions import (
    LLMError,
    AllProvidersFailedError,
    ContentPolicyError,
    RateLimitError,
    InvalidResponseError,
)

logger = logging.getLogger(__name__)

# Configure litellm
litellm.set_verbose = False  # Set to True for debugging


class LLMService:
    """
    LLM Service with automatic fallback chain.

    Primary: Claude Opus 4.5 (claude-opus-4-5-20251101)
    Fallback 1: GPT-5
    Fallback 2: Gemini 3 Pro Preview

    Features:
    - Automatic fallback on failure
    - Exponential backoff retry
    - JSON response parsing
    - Error classification
    """

    # Model configuration - 3-stage fallback chain
    MODELS = [
        {
            "model": "claude-opus-4-5-20251101",
            "provider": "anthropic",
            "max_tokens": 4096,
        },
        {
            "model": "gpt-5",
            "provider": "openai",
            "max_tokens": 4096,
        },
        {
            "model": "gemini/gemini-3-pro-preview",
            "provider": "google",
            "max_tokens": 4096,
        },
    ]

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0  # seconds
    MAX_DELAY = 60.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    # Non-retryable error patterns
    NON_RETRYABLE_ERRORS = [
        "content_policy_violation",
        "invalid_api_key",
        "authentication_error",
    ]

    def __init__(self):
        """Initialize LLM service with API keys"""
        self._configure_api_keys()

    def _configure_api_keys(self):
        """Set API keys for litellm"""
        if settings.ANTHROPIC_API_KEY:
            litellm.anthropic_key = settings.ANTHROPIC_API_KEY
        if settings.OPENAI_API_KEY:
            litellm.openai_key = settings.OPENAI_API_KEY
        if settings.GOOGLE_API_KEY:
            # For Gemini via litellm
            import os
            os.environ["GEMINI_API_KEY"] = settings.GOOGLE_API_KEY

    def _get_api_key(self, provider: str) -> str:
        """Get API key for specific provider"""
        if provider == "anthropic":
            return settings.ANTHROPIC_API_KEY
        elif provider == "openai":
            return settings.OPENAI_API_KEY
        elif provider == "google":
            return settings.GOOGLE_API_KEY
        return ""

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable"""
        error_str = str(error).lower()
        for pattern in self.NON_RETRYABLE_ERRORS:
            if pattern in error_str:
                return False
        return True

    def _classify_error(self, error: Exception, provider: str) -> LLMError:
        """Classify exception into specific LLM error type"""
        error_str = str(error).lower()

        if "content_policy" in error_str or "safety" in error_str:
            return ContentPolicyError(str(error), provider)
        elif "rate_limit" in error_str or "429" in error_str:
            return RateLimitError(str(error), provider)
        else:
            return LLMError(str(error), provider)

    def call_with_fallback(
        self,
        messages: list[dict],
        response_format: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call LLM with automatic fallback chain.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional response format (e.g., {"type": "json_object"})
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            str: LLM response content

        Raises:
            AllProvidersFailedError: When all providers fail
        """
        errors = []

        for model_config in self.MODELS:
            model = model_config["model"]
            provider = model_config["provider"]

            # Check if API key is available
            api_key = self._get_api_key(provider)
            if not api_key:
                logger.warning(f"Skipping {provider}: No API key configured")
                continue

            # Try this model with retries
            for attempt in range(self.MAX_RETRIES):
                try:
                    logger.info(
                        f"Calling {model} (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )

                    # Build request kwargs
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }

                    # Add response format if specified (for JSON mode)
                    # Note: Anthropic models don't support response_format directly
                    if response_format and provider != "anthropic":
                        kwargs["response_format"] = response_format

                    # Make the call
                    response = completion(**kwargs)

                    content = response.choices[0].message.content

                    # Check for empty response
                    if not content or not content.strip():
                        raise ValueError("Empty response from LLM")

                    logger.info(f"Successfully got response from {model}")

                    return content

                except Exception as e:
                    classified_error = self._classify_error(e, provider)
                    errors.append({"model": model, "error": str(e)})

                    logger.warning(f"{model} failed (attempt {attempt + 1}): {e}")

                    # Check if retryable
                    if not self._is_retryable_error(e):
                        logger.error(f"Non-retryable error from {model}: {e}")
                        break  # Move to next model

                    # If this is the last retry, move to next model
                    if attempt >= self.MAX_RETRIES - 1:
                        break

                    # Calculate backoff delay
                    delay = min(
                        self.INITIAL_DELAY * (self.BACKOFF_MULTIPLIER ** attempt),
                        self.MAX_DELAY,
                    )
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        # All models exhausted
        raise AllProvidersFailedError(
            message=f"All LLM providers failed after {len(errors)} attempts",
            errors=errors,
        )

    def call_with_json_response(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Call LLM and parse JSON response.

        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            dict: Parsed JSON response

        Raises:
            InvalidResponseError: When response is not valid JSON
            AllProvidersFailedError: When all providers fail
        """
        response = self.call_with_fallback(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Strip markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith("```"):
            # Remove opening backticks and optional language identifier
            first_newline = clean_response.find("\n")
            if first_newline != -1:
                clean_response = clean_response[first_newline+1:]
            
            # Remove closing backticks
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
        
        clean_response = clean_response.strip()

        try:
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            raise InvalidResponseError(
                message=f"Failed to parse JSON response: {e}",
                raw_response=response[:500],
            )

    def extract_signals(self, context: dict, system_prompt: str, user_prompt: str) -> list[dict]:
        """
        Extract risk signals from context using LLM.

        Args:
            context: Unified context data
            system_prompt: System prompt for signal extraction
            user_prompt: User prompt with context data

        Returns:
            list[dict]: Extracted signals
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self.call_with_json_response(messages)

        signals = result.get("signals", [])
        logger.info(f"Extracted {len(signals)} signals from LLM")

        return signals

    def generate_insight(self, signals: list[dict], context: dict, prompt: str) -> str:
        """
        Generate executive insight summary.

        Args:
            signals: List of validated signals
            context: Unified context data
            prompt: Insight generation prompt

        Returns:
            str: Generated insight text
        """
        messages = [{"role": "user", "content": prompt}]

        return self.call_with_fallback(
            messages=messages,
            temperature=0.3,  # Slightly higher for more natural text
            max_tokens=2048,
        )

    def extract_document_facts(
        self,
        image_base64: str,
        doc_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        Extract structured facts from document image using Vision LLM.

        Args:
            image_base64: Base64 encoded image data
            doc_type: Document type (BIZ_REG, REGISTRY, etc.)
            system_prompt: System prompt for extraction
            user_prompt: Document-type specific extraction prompt

        Returns:
            dict: Extracted facts in structured format
        """
        # Build vision message with image
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high",  # Use high detail for document OCR
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            },
        ]

        result = self._call_vision_with_fallback(messages)

        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise InvalidResponseError(
                message=f"Failed to parse document extraction JSON: {e}",
                raw_response=result[:500],
            )

    def _call_vision_with_fallback(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call Vision LLM with automatic fallback chain.

        Vision-capable models:
        - Claude Sonnet 4 (primary)
        - GPT-4o (fallback)

        Args:
            messages: List of message dicts with vision content
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            str: LLM response content
        """
        errors = []

        # Vision-capable models only (3-stage fallback)
        vision_models = [
            {
                "model": "claude-opus-4-5-20251101",
                "provider": "anthropic",
                "max_tokens": 4096,
            },
            {
                "model": "gpt-5",
                "provider": "openai",
                "max_tokens": 4096,
            },
            {
                "model": "gemini/gemini-3-pro-preview",
                "provider": "google",
                "max_tokens": 4096,
            },
        ]

        for model_config in vision_models:
            model = model_config["model"]
            provider = model_config["provider"]

            # Check if API key is available
            api_key = self._get_api_key(provider)
            if not api_key:
                logger.warning(f"Skipping {provider}: No API key configured")
                continue

            # Try this model with retries
            for attempt in range(self.MAX_RETRIES):
                try:
                    logger.info(
                        f"Calling Vision {model} (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )

                    # Build request kwargs
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }

                    # Make the call
                    response = completion(**kwargs)

                    content = response.choices[0].message.content
                    logger.info(f"Successfully got vision response from {model}")

                    return content

                except Exception as e:
                    errors.append({"model": model, "error": str(e)})
                    logger.warning(f"Vision {model} failed (attempt {attempt + 1}): {e}")

                    # Check if retryable
                    if not self._is_retryable_error(e):
                        logger.error(f"Non-retryable error from {model}: {e}")
                        break

                    # If this is the last retry, move to next model
                    if attempt >= self.MAX_RETRIES - 1:
                        break

                    # Calculate backoff delay
                    delay = min(
                        self.INITIAL_DELAY * (self.BACKOFF_MULTIPLIER ** attempt),
                        self.MAX_DELAY,
                    )
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        # All models exhausted
        raise AllProvidersFailedError(
            message=f"All Vision LLM providers failed after {len(errors)} attempts",
            errors=errors,
        )
