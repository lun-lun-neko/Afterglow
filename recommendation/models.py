from dataclasses import dataclass


@dataclass(frozen=True)
class Anchor:
    name: str
    latitude: float
    longitude: float
    anchor_type: str | None = None


@dataclass(frozen=True)
class Place:
    place_id: str
    place_name: str
    place_category: str
    latitude: float
    longitude: float
    is_indoor: bool
    walk_hard: int
    category_name: str = ""
    place_url: str = ""


@dataclass(frozen=True)
class TreatmentContext:
    treatment: str
    days_after: int
    hospital_name: str | None = None
    package_id: str | None = None
