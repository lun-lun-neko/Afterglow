from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, permutations

from recommendation.candidate_service import CandidateService
from recommendation.config import (
    COURSE_CANDIDATES_PER_CATEGORY,
    COURSE_DISTANCE_SCORE_BANDS,
    COURSE_PLACE_COUNT,
    COURSE_SCORE_WEIGHTS,
    MAX_COURSE_DISTANCE_KM,
    MAX_LEG_DISTANCE_KM,
    MAX_SAME_CATEGORY_PER_COURSE,
    MAX_SHARED_PLACES_BETWEEN_TOP_COURSES,
    MIN_DISTINCT_CATEGORIES,
    PURPOSE_REQUIRED_CATEGORIES,
    REST_MIN_INDOOR_PLACES,
)
from recommendation.distance_service import haversine_km
from recommendation.models import Anchor


def _route_distance_score(total_distance_km: float) -> float:
    for upper_bound, score in COURSE_DISTANCE_SCORE_BANDS:
        if total_distance_km <= upper_bound:
            return score
    return 0.0


def _purpose_composition_score(user_purpose: str, places: tuple[dict, ...]) -> float | None:
    if user_purpose == "휴식":
        indoor_count = sum(place["is_indoor"] for place in places)
        if indoor_count < REST_MIN_INDOOR_PLACES:
            return None
        return 100.0 if indoor_count == COURSE_PLACE_COUNT else 80.0

    required = PURPOSE_REQUIRED_CATEGORIES.get(user_purpose, set())
    matching_count = sum(place["place_category"] in required for place in places)
    if required and matching_count == 0:
        return None
    return 100.0 if matching_count >= 2 else 75.0


def _best_route(anchor: Anchor, places: tuple[dict, ...]) -> tuple[tuple[dict, ...], list[float], float] | None:
    best = None
    for ordered in permutations(places):
        points = [(anchor.latitude, anchor.longitude)] + [
            (place["latitude"], place["longitude"]) for place in ordered
        ]
        legs = [
            haversine_km(start[0], start[1], end[0], end[1])
            for start, end in zip(points, points[1:])
        ]
        total = sum(legs)
        if any(distance > MAX_LEG_DISTANCE_KM for distance in legs):
            continue
        if total > MAX_COURSE_DISTANCE_KM:
            continue
        if best is None or total < best[2]:
            best = ordered, legs, total
    return best


class CourseService:
    def __init__(self, candidate_service: CandidateService):
        self.candidate_service = candidate_service

    def recommend(
        self,
        *,
        anchor: Anchor,
        treatment: str,
        days_after: int,
        user_purpose: str,
        user_walk_preference: int,
        top_n: int,
    ) -> list[dict]:
        all_candidates = self.candidate_service.recommend(
            anchor=anchor,
            treatment=treatment,
            days_after=days_after,
            user_purpose=user_purpose,
            user_walk_preference=user_walk_preference,
            limit=10_000,
        )
        by_category: dict[str, list[dict]] = defaultdict(list)
        for candidate in all_candidates:
            category_candidates = by_category[candidate["place_category"]]
            if len(category_candidates) < COURSE_CANDIDATES_PER_CATEGORY:
                category_candidates.append(candidate)
        candidate_places = [
            candidate
            for category_candidates in by_category.values()
            for candidate in category_candidates
        ]
        scored_courses = []
        for place_group in combinations(candidate_places, COURSE_PLACE_COUNT):
            category_counts = Counter(place["place_category"] for place in place_group)
            if max(category_counts.values()) > MAX_SAME_CATEGORY_PER_COURSE:
                continue
            if len(category_counts) < MIN_DISTINCT_CATEGORIES:
                continue
            purpose_composition = _purpose_composition_score(user_purpose, place_group)
            if purpose_composition is None:
                continue
            route = _best_route(anchor, place_group)
            if route is None:
                continue
            ordered_places, leg_distances, total_distance = route
            average_place_score = sum(p["place_score"] for p in ordered_places) / COURSE_PLACE_COUNT
            route_score = _route_distance_score(total_distance)
            diversity_score = 100.0 if len(category_counts) == 3 else 70.0
            course_score = (
                average_place_score * COURSE_SCORE_WEIGHTS["places"]
                + route_score * COURSE_SCORE_WEIGHTS["route"]
                + diversity_score * COURSE_SCORE_WEIGHTS["diversity"]
                + purpose_composition * COURSE_SCORE_WEIGHTS["purpose_composition"]
            )
            route_places = []
            for order, (place, leg_distance) in enumerate(
                zip(ordered_places, leg_distances), start=1
            ):
                route_places.append({**place, "order": order, "distance_from_previous_km": round(leg_distance, 3)})
            scored_courses.append(
                {
                    "course_score": round(course_score, 2),
                    "average_place_score": round(average_place_score, 2),
                    "route_score": route_score,
                    "diversity_score": diversity_score,
                    "purpose_composition_score": purpose_composition,
                    "total_distance_km": round(total_distance, 3),
                    "places": route_places,
                }
            )

        scored_courses.sort(
            key=lambda course: (-course["course_score"], course["total_distance_km"])
        )
        selected = []
        for course in scored_courses:
            place_ids = {place["place_id"] for place in course["places"]}
            if any(
                len(place_ids & {place["place_id"] for place in chosen["places"]})
                > MAX_SHARED_PLACES_BETWEEN_TOP_COURSES
                for chosen in selected
            ):
                continue
            selected.append({**course, "rank": len(selected) + 1})
            if len(selected) == top_n:
                break
        return selected
