"""
Environment Query Selector Service

Selects ENVIRONMENT queries based on corp profile conditions.
This module is designed to be lightweight and usable from both API and Worker.
"""

from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryCondition:
    """Condition for query selection."""
    field: str
    op: str  # >=, ==, in, contains_key, is_not_empty
    value: Any


class EnvironmentQuerySelector:
    """Select ENVIRONMENT queries based on profile conditions."""

    # Query definitions with conditions
    QUERY_CONDITIONS: dict[str, list[QueryCondition]] = {
        "FX_RISK": [
            QueryCondition(field="export_ratio_pct", op=">=", value=30),
        ],
        "TRADE_BLOC": [
            QueryCondition(field="export_ratio_pct", op=">=", value=30),
        ],
        "GEOPOLITICAL": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="country_exposure", op="contains_key", value="미국"),
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "SUPPLY_CHAIN": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="key_materials", op="is_not_empty", value=None),
        ],
        "REGULATION": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="country_exposure", op="contains_key", value="미국"),
        ],
        "COMMODITY": [
            QueryCondition(field="key_materials", op="is_not_empty", value=None),
        ],
        "PANDEMIC_HEALTH": [
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "POLITICAL_INSTABILITY": [
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "CYBER_TECH": [
            QueryCondition(field="industry_code", op="in", value=["C26", "C21"]),
        ],
        "ENERGY_SECURITY": [
            QueryCondition(field="industry_code", op="==", value="D35"),
        ],
        "FOOD_SECURITY": [
            QueryCondition(field="industry_code", op="==", value="C10"),
        ],
    }

    def select_queries(
        self,
        profile: dict,
        industry_code: str,
    ) -> tuple[list[str], list[dict]]:
        """
        Select applicable query categories based on profile.

        Returns:
            Tuple of (selected category names, details with conditions met)
        """
        selected = []
        details = []

        for category, conditions in self.QUERY_CONDITIONS.items():
            met_conditions = []
            is_applicable = False

            for cond in conditions:
                if self._evaluate_condition(profile, industry_code, cond):
                    is_applicable = True
                    met_conditions.append({
                        "field": cond.field,
                        "operator": cond.op,
                        "value": cond.value,
                        "is_met": True,
                    })

            if is_applicable:
                selected.append(category)
                details.append({
                    "category": category,
                    "conditions_met": met_conditions,
                })

        logger.info(f"Selected {len(selected)} query categories: {selected}")
        return selected, details

    def _evaluate_condition(
        self,
        profile: dict,
        industry_code: str,
        cond: QueryCondition,
    ) -> bool:
        """Evaluate a single condition."""
        # Get field value
        if cond.field == "industry_code":
            field_value = industry_code
        else:
            field_value = profile.get(cond.field)

        if field_value is None:
            return False

        # Evaluate based on operator
        if cond.op == ">=":
            return isinstance(field_value, (int, float)) and field_value >= cond.value
        elif cond.op == "==":
            return field_value == cond.value
        elif cond.op == "in":
            return field_value in cond.value
        elif cond.op == "contains_key":
            return isinstance(field_value, dict) and cond.value in field_value
        elif cond.op == "is_not_empty":
            if isinstance(field_value, (list, dict)):
                return len(field_value) > 0
            return bool(field_value)

        return False
