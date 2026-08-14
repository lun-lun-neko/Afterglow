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
from recommendation.models import Place, TreatmentContext


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


def evaluate_treatments(
    treatments: list[TreatmentContext], place: Place
) -> tuple[FilterStatus, list[str], list[dict]]:
    evaluations = []
    all_signals: set[str] = set()
    statuses = []
    for context in treatments:
        status, signals = treatment_filter(context.treatment, place, context.days_after)
        matched_signals = [
            signal
            for signal in signals
            if status is not FilterStatus.NORMAL
            and _status_for_rule(context.treatment, signal, context.days_after) is status
        ]
        statuses.append(status)
        all_signals.update(signals)
        evaluations.append(
            {
                "treatment": context.treatment,
                "days_after": context.days_after,
                "status": status.value,
                "matched_risk_signals": matched_signals,
                "hospital_name": context.hospital_name,
                "package_id": context.package_id,
            }
        )
    final_status = max(statuses, key=STATUS_PRIORITY.get, default=FilterStatus.NORMAL)
    return final_status, sorted(all_signals), evaluations
