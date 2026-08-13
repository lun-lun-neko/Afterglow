from dataclasses import dataclass

from recommendation.config import (
    DEFAULT_PURPOSE_SCORE,
    PURPOSE_CATEGORY_SCORE,
    SCORE_WEIGHTS,
    TREATMENT_SCORE,
    WALK_SCORE_BY_EXCESS,
    WALK_SCORE_LARGE_EXCESS,
)
from recommendation.distance_service import distance_score
from recommendation.models import Place
from recommendation.treatment_filter import FilterStatus


@dataclass(frozen=True)
class ScoreBreakdown:
    purpose_score: float
    treatment_score: float
    distance_score: float
    walk_score: float
    place_score: float


def purpose_score(user_purpose: str, place_category: str) -> float:
    return PURPOSE_CATEGORY_SCORE.get(user_purpose, {}).get(
        place_category, DEFAULT_PURPOSE_SCORE
    )


def walk_score(user_walk_preference: int, walk_hard: int) -> float:
    excess = max(0, walk_hard - user_walk_preference)
    return WALK_SCORE_BY_EXCESS.get(excess, WALK_SCORE_LARGE_EXCESS)


def calculate_place_score(
    user_purpose: str,
    user_walk_preference: int,
    place: Place,
    filter_status: FilterStatus,
    distance_km: float,
) -> ScoreBreakdown:
    purpose = purpose_score(user_purpose, place.place_category)
    treatment = TREATMENT_SCORE[filter_status.value]
    distance = distance_score(distance_km)
    walk = walk_score(user_walk_preference, place.walk_hard)
    total = (
        purpose * SCORE_WEIGHTS["purpose"]
        + treatment * SCORE_WEIGHTS["treatment"]
        + distance * SCORE_WEIGHTS["distance"]
        + walk * SCORE_WEIGHTS["walk"]
    )
    return ScoreBreakdown(purpose, treatment, distance, walk, round(total, 2))
