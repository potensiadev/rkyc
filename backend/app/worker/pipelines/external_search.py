"""
External Search Pipeline Stage
Stage 3: Search external news/events using Perplexity API
"""

import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExternalSearchPipeline:
    """
    Stage 3: EXTERNAL - Search external information using Perplexity API

    Uses Perplexity sonar-pro model for real-time web search.
    Falls back to empty results if API key not configured.
    """

    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"
    TIMEOUT = 30.0

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("Perplexity API key not configured - external search disabled")

    def execute(self, corp_name: str, industry_name: str, corp_id: str) -> dict:
        """
        Execute external search stage.

        Args:
            corp_name: Corporation name for search
            industry_name: Industry name for context
            corp_id: Corporation ID for logging

        Returns:
            dict with structure:
                - events: List of external event dicts
                - source: "perplexity" or "disabled"
        """
        logger.info(f"EXTERNAL stage starting for corp_id={corp_id}, corp_name={corp_name}")

        if not self.enabled:
            logger.info("External search disabled (no API key)")
            return {"events": [], "source": "disabled"}

        try:
            events = self._search_external_events(corp_name, industry_name)
            logger.info(f"EXTERNAL stage completed: found {len(events)} events")
            return {"events": events, "source": "perplexity"}

        except Exception as e:
            logger.error(f"External search failed: {e}")
            return {"events": [], "source": "error"}

    def _search_external_events(self, corp_name: str, industry_name: str) -> list[dict]:
        """
        Search for external events using Perplexity API.

        Returns list of event dicts with structure:
            - title: Event title
            - summary: Event summary
            - source_url: Source URL
            - published_at: Publication date (if available)
            - relevance: HIGH/MED/LOW
        """
        prompt = self._build_search_prompt(corp_name, industry_name)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst researching corporate risk signals. "
                        "Search for recent news and events that could indicate risks or opportunities. "
                        "Focus on: regulatory changes, industry shocks, financial issues, "
                        "leadership changes, legal matters, and market developments. "
                        "Return results in JSON format."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        with httpx.Client(timeout=self.TIMEOUT) as client:
            response = client.post(
                self.PERPLEXITY_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse events from response
        events = self._parse_events(content)
        return events

    def _build_search_prompt(self, corp_name: str, industry_name: str) -> str:
        """Build search prompt for Perplexity."""
        today = datetime.now().strftime("%Y-%m-%d")

        return f"""Search for recent news and events (last 30 days) related to:

Company: {corp_name}
Industry: {industry_name}

Find information about:
1. Any regulatory or legal issues affecting this company
2. Industry-wide events or shocks affecting {industry_name}
3. Financial news (earnings, debt, restructuring)
4. Leadership or ownership changes
5. Policy or regulation changes affecting the industry

Today's date: {today}

Return results as a JSON array with this structure:
[
  {{
    "title": "Event title",
    "summary": "Brief summary of the event and its potential impact",
    "source_url": "URL of the source",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW based on impact potential"
  }}
]

If no relevant events found, return an empty array: []
Only include factual, verifiable information from reliable sources."""

    def _parse_events(self, content: str) -> list[dict]:
        """Parse events from Perplexity response."""
        import json

        # Try to extract JSON from response
        try:
            # Find JSON array in response
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON array found in Perplexity response")
                return []

            json_str = content[start_idx:end_idx]
            events = json.loads(json_str)

            # Validate and clean events
            valid_events = []
            for event in events:
                if self._validate_event(event):
                    valid_events.append(event)

            return valid_events

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Perplexity response as JSON: {e}")
            return []

    def _validate_event(self, event: dict) -> bool:
        """Validate a single event dict."""
        required_fields = ["title", "summary"]

        for field in required_fields:
            if not event.get(field):
                return False

        # Validate relevance if present
        if event.get("relevance") and event["relevance"] not in {"HIGH", "MED", "LOW"}:
            event["relevance"] = "MED"  # Default to MED

        return True
