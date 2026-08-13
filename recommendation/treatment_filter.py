from enum import StrEnum

from recommendation.config import (
    HEAT_CATEGORY_KEYWORDS,
    MASSAGE_CATEGORY_KEYWORDS,
    RISK_HEAT_EXPOSURE,
    RISK_HIGH_ACTIVITY,
    RISK_MASSAGE_PRESSURE,
    RISK_OUTDOOR_EXPOSURE,
    TREATMENT_RISK_RULES,
)
from recommendation.models import Place


class FilterStatus(StrEnum):
    NORMAL = "NORMAL"
    PENALTY = "PENALTY"
    BLOCK = "BLOCK"


STATUS_PRIORITY = {
    FilterStatus.NORMAL: 0,
    FilterStatus.PENALTY: 1,
    FilterStatus.BLOCK: 2,
}


def place_risk_signals(place: Place) -> set[str]:
    signals: set[str] = set()
    if place.walk_hard >= 4:
        signals.add(RISK_HIGH_ACTIVITY)
    if not place.is_indoor:
        signals.add(RISK_OUTDOOR_EXPOSURE)
    category_text = f"{place.place_category} {place.category_name}"
    if any(keyword in category_text for keyword in HEAT_CATEGORY_KEYWORDS):
        signals.add(RISK_HEAT_EXPOSURE)
    if any(keyword in category_text for keyword in MASSAGE_CATEGORY_KEYWORDS):
        signals.add(RISK_MASSAGE_PRESSURE)
    return signals


def _status_for_rule(treatment: str, signal: str, days_after: int) -> FilterStatus:
    periods = TREATMENT_RISK_RULES.get(treatment, {}).get(signal, ())
    for first_day, last_day, status in periods:
        if first_day <= days_after <= last_day:
            return FilterStatus(status)
    return FilterStatus.NORMAL


def treatment_filter(
    treatment: str, place: Place, days_after: int
) -> tuple[FilterStatus, list[str]]:
    signals = sorted(place_risk_signals(place))
    statuses = [_status_for_rule(treatment, signal, days_after) for signal in signals]
    final_status = max(statuses, key=STATUS_PRIORITY.get, default=FilterStatus.NORMAL)
    return final_status, signals
