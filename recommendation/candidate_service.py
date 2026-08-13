from __future__ import annotations

from pathlib import Path

import pandas as pd

from recommendation.config import (
    ANCHOR_DATA_FILE,
    CANDIDATE_DATA_FILES,
    MAX_SEARCH_RADIUS_KM,
)
from recommendation.distance_service import haversine_km
from recommendation.models import Anchor, Place
from recommendation.place_score import calculate_place_score
from recommendation.treatment_filter import FilterStatus, treatment_filter


def _repair_legacy_text(value: object) -> str:
    text = str(value or "").strip()
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired if repaired else text


class CsvPlaceRepository:
    """CSV adapter; replace this class with a DB repository without changing scoring."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._anchors = self._load_anchors()
        self._places = self._load_places()

    @staticmethod
    def _read(path: Path) -> pd.DataFrame:
        if not path.is_file():
            raise RuntimeError(f"Required place data not found: {path}")
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    def _load_anchors(self) -> list[Anchor]:
        frame = self._read(self.data_dir / ANCHOR_DATA_FILE)
        return [
            Anchor(
                name=_repair_legacy_text(row.placeName),
                latitude=float(row.mapY),
                longitude=float(row.mapX),
                anchor_type=row.primaryType,
            )
            for row in frame.itertuples(index=False)
        ]

    def _load_places(self) -> list[Place]:
        by_id: dict[str, Place] = {}
        for filename in CANDIDATE_DATA_FILES:
            frame = self._read(self.data_dir / filename)
            for row in frame.to_dict("records"):
                if row.get("isNa", "0") == "1":
                    continue
                category = row["primaryType"]
                indoor = row.get("isIndoor", "")
                walk_hard = row.get("walkHard", "")
                if not indoor or not walk_hard:
                    continue
                try:
                    place = Place(
                        place_id=row["kakaoPlaceId"],
                        place_name=_repair_legacy_text(row["placeName"]),
                        place_category=category,
                        latitude=float(row["mapY"]),
                        longitude=float(row["mapX"]),
                        is_indoor=bool(int(indoor)),
                        walk_hard=int(walk_hard),
                        category_name=_repair_legacy_text(row.get("categoryName", "")),
                        place_url=row.get("placeUrl", ""),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                by_id.setdefault(place.place_id, place)
        return list(by_id.values())

    def find_anchor(self, name: str) -> Anchor | None:
        normalized = name.strip().casefold()
        return next((anchor for anchor in self._anchors if anchor.name.casefold() == normalized), None)

    def list_places(self) -> list[Place]:
        return self._places


class CandidateService:
    def __init__(self, repository: CsvPlaceRepository):
        self.repository = repository

    def recommend(
        self,
        *,
        anchor: Anchor,
        treatment: str,
        days_after: int,
        user_purpose: str,
        user_walk_preference: int,
        limit: int,
    ) -> list[dict]:
        candidates = []
        for place in self.repository.list_places():
            distance = haversine_km(
                anchor.latitude, anchor.longitude, place.latitude, place.longitude
            )
            if distance > MAX_SEARCH_RADIUS_KM:
                continue
            status, risk_signals = treatment_filter(treatment, place, days_after)
            if status is FilterStatus.BLOCK:
                continue
            scores = calculate_place_score(
                user_purpose, user_walk_preference, place, status, distance
            )
            candidates.append(
                {
                    "place_id": place.place_id,
                    "place_name": place.place_name,
                    "place_category": place.place_category,
                    "category_name": place.category_name,
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "is_indoor": place.is_indoor,
                    "walk_hard": place.walk_hard,
                    "distance_from_anchor_km": round(distance, 3),
                    "filter_status": status.value,
                    "risk_signals": risk_signals,
                    "purpose_score": scores.purpose_score,
                    "treatment_score": scores.treatment_score,
                    "distance_score": scores.distance_score,
                    "walk_score": scores.walk_score,
                    "place_score": scores.place_score,
                    "place_url": place.place_url,
                }
            )
        candidates.sort(
            key=lambda item: (-item["place_score"], item["distance_from_anchor_km"], item["place_id"])
        )
        return candidates[:limit]
