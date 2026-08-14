from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
from catboost import CatBoostRegressor
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from recommendation.candidate_service import CandidateService, CsvPlaceRepository
from recommendation.course_service import CourseService
from recommendation.config import (
    DEFAULT_RESULT_LIMIT,
    DEFAULT_TOP_COURSES,
    MAX_RESULT_LIMIT,
    MAX_TOP_COURSES,
    VALID_PURPOSES,
    VALID_TREATMENTS,
)
from recommendation.models import Anchor, TreatmentContext


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "course_rating_catboost_v4.cbm"
DEFAULT_METRICS_PATH = BASE_DIR / "models" / "course_rating_catboost_v4_metrics.json"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH))).resolve()
METRICS_PATH = Path(os.getenv("METRICS_PATH", str(DEFAULT_METRICS_PATH))).resolve()

RatingLevel = Annotated[float, Field(ge=1.0, le=5.0)]
Distance = Annotated[float, Field(ge=0.0)]

CATEGORICAL_COLUMNS = [
    "Hospital_Name", "Treatment", "User_Purpose",
    "Category_1", "Category_2", "Category_3",
    "Place_1", "Place_2", "Place_3",
]
NUMERIC_COLUMNS = [
    "User_Walk_Preference", "Days_After",
    "Is_Indoor_1", "Is_Indoor_2", "Is_Indoor_3",
    "Walk_Hard_1", "Walk_Hard_2", "Walk_Hard_3",
    "Dist_1", "Dist_2", "Dist_3",
    "Mean_Walk_Hard", "Indoor_Count", "Preference_Hard_Diff",
]
FEATURE_COLUMNS = CATEGORICAL_COLUMNS + NUMERIC_COLUMNS


class CourseCandidate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "Hospital_Name": "닥터스프링의원",
                "Treatment": "피부레이저",
                "User_Purpose": "휴식",
                "Category_1": "문화시설",
                "Category_2": "쇼핑",
                "Category_3": "문화시설",
                "Place_1": "PS로이",
                "Place_2": "올리브영 압구정로데오점",
                "Place_3": "송은",
                "User_Walk_Preference": 2,
                "Days_After": 0,
                "Is_Indoor_1": 1,
                "Is_Indoor_2": 1,
                "Is_Indoor_3": 1,
                "Walk_Hard_1": 1,
                "Walk_Hard_2": 2,
                "Walk_Hard_3": 2,
                "Dist_1": 0.4,
                "Dist_2": 0.5,
                "Dist_3": 0.6,
            }
        },
    )

    Hospital_Name: str = Field(min_length=1)
    Treatment: str = Field(min_length=1)
    User_Purpose: str = Field(min_length=1)
    Category_1: str = Field(min_length=1)
    Category_2: str = Field(min_length=1)
    Category_3: str = Field(min_length=1)
    Place_1: str = Field(min_length=1)
    Place_2: str = Field(min_length=1)
    Place_3: str = Field(min_length=1)
    User_Walk_Preference: RatingLevel
    Days_After: int = Field(ge=0)
    Is_Indoor_1: int = Field(ge=0, le=1)
    Is_Indoor_2: int = Field(ge=0, le=1)
    Is_Indoor_3: int = Field(ge=0, le=1)
    Walk_Hard_1: RatingLevel
    Walk_Hard_2: RatingLevel
    Walk_Hard_3: RatingLevel
    Dist_1: Distance
    Dist_2: Distance
    Dist_3: Distance


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[CourseCandidate] = Field(min_length=1, max_length=1000)


class Prediction(BaseModel):
    index: int
    predicted_rating: float


class PredictResponse(BaseModel):
    predictions: list[Prediction]


class RankedPrediction(Prediction):
    rank: int


class RankResponse(BaseModel):
    rankings: list[RankedPrediction]


class TreatmentEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    treatment: str
    days_after: int | None = Field(default=None, ge=0)
    scheduled_at: datetime | None = None
    hospital_name: str | None = None
    package_id: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> "TreatmentEventInput":
        if (self.days_after is None) == (self.scheduled_at is None):
            raise ValueError("Provide exactly one of days_after or scheduled_at")
        if self.scheduled_at is not None and self.scheduled_at.utcoffset() is None:
            raise ValueError("scheduled_at must include a timezone offset")
        return self


class PlaceRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jwt: str | None = None
    title: str = Field(min_length=1)
    treatment: str | None = None
    days_after: int | None = Field(default=None, ge=0)
    treatments: list[TreatmentEventInput] | None = Field(default=None, min_length=1, max_length=20)
    recommendation_at: datetime | None = None
    user_purpose: str
    user_walk_preference: int = Field(ge=1, le=5)
    anchor_type: str | None = None
    anchor_latitude: float | None = Field(default=None, ge=-90, le=90)
    anchor_longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_treatments(self) -> "PlaceRecommendationRequest":
        has_legacy = self.treatment is not None or self.days_after is not None
        if has_legacy and self.treatments is not None:
            raise ValueError("Use either treatment/days_after or treatments, not both")
        if has_legacy:
            if self.treatment is None or self.days_after is None:
                raise ValueError("Both treatment and days_after are required")
        elif not self.treatments:
            raise ValueError("At least one treatment is required")
        scheduled_events = [
            event for event in self.treatments or [] if event.scheduled_at is not None
        ]
        if scheduled_events and self.recommendation_at is None:
            raise ValueError("recommendation_at is required with scheduled_at")
        if self.recommendation_at is not None and self.recommendation_at.utcoffset() is None:
            raise ValueError("recommendation_at must include a timezone offset")
        return self


class AnchorResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    anchor_type: str | None = None


class CandidatePlaceResponse(BaseModel):
    place_id: str
    place_name: str
    place_category: str
    category_name: str
    latitude: float
    longitude: float
    is_indoor: bool
    walk_hard: int
    distance_from_anchor_km: float
    filter_status: str
    risk_signals: list[str]
    treatment_evaluations: list["TreatmentEvaluationResponse"]
    purpose_score: float
    treatment_score: float
    distance_score: float
    walk_score: float
    place_score: float
    place_url: str


class TreatmentEvaluationResponse(BaseModel):
    treatment: str
    days_after: int
    status: str
    matched_risk_signals: list[str]
    hospital_name: str | None = None
    package_id: str | None = None


class ActiveTreatmentResponse(BaseModel):
    treatment: str
    days_after: int
    hospital_name: str | None = None
    package_id: str | None = None


class PlaceRecommendationData(BaseModel):
    anchor: AnchorResponse
    active_treatments: list[ActiveTreatmentResponse]
    medical_compatibility_checked: bool = False
    candidate_places: list[CandidatePlaceResponse]


class PlaceRecommendationResponse(BaseModel):
    status: str = "success"
    data: PlaceRecommendationData


class CoursePlaceResponse(CandidatePlaceResponse):
    order: int
    distance_from_previous_km: float


class CourseResponse(BaseModel):
    rank: int
    course_score: float
    average_place_score: float
    route_score: float
    diversity_score: float
    purpose_composition_score: float
    total_distance_km: float
    places: list[CoursePlaceResponse]


class CourseRecommendationData(BaseModel):
    anchor: AnchorResponse
    active_treatments: list[ActiveTreatmentResponse]
    medical_compatibility_checked: bool = False
    courses: list[CourseResponse]


class CourseRecommendationResponse(BaseModel):
    status: str = "success"
    data: CourseRecommendationData


def load_model(path: Path) -> CatBoostRegressor:
    if not path.is_file():
        raise RuntimeError(
            f"Model not found: {path}. Run scripts/train_course_catboost.py first."
        )
    model = CatBoostRegressor()
    model.load_model(path)
    if model.feature_names_ != FEATURE_COLUMNS:
        raise RuntimeError("The model feature schema does not match the inference API.")
    return model


def load_metrics(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model(MODEL_PATH)
    app.state.metrics = load_metrics(METRICS_PATH)
    repository = CsvPlaceRepository(BASE_DIR / "data")
    app.state.place_repository = repository
    app.state.candidate_service = CandidateService(repository)
    app.state.course_service = CourseService(app.state.candidate_service)
    yield
    app.state.model = None
    app.state.place_repository = None
    app.state.candidate_service = None
    app.state.course_service = None


app = FastAPI(
    title="Afterglow CatBoost Course Rating API",
    version="4.0.0",
    lifespan=lifespan,
)


def candidates_to_frame(candidates: list[CourseCandidate]) -> pd.DataFrame:
    frame = pd.DataFrame([candidate.model_dump() for candidate in candidates])
    walk_columns = ["Walk_Hard_1", "Walk_Hard_2", "Walk_Hard_3"]
    indoor_columns = ["Is_Indoor_1", "Is_Indoor_2", "Is_Indoor_3"]
    frame["Mean_Walk_Hard"] = frame[walk_columns].mean(axis=1)
    frame["Indoor_Count"] = frame[indoor_columns].sum(axis=1)
    frame["Preference_Hard_Diff"] = (
        frame["User_Walk_Preference"] - frame["Mean_Walk_Hard"]
    ).abs()
    return frame[FEATURE_COLUMNS]


def infer(request: Request, candidates: list[CourseCandidate]) -> list[float]:
    try:
        values = request.app.state.model.predict(candidates_to_frame(candidates))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Model inference failed") from exc
    return [float(value) for value in values]


@app.get("/health")
def health(request: Request) -> dict:
    model = request.app.state.model
    metrics = request.app.state.metrics
    return {
        "status": "ok",
        "model": "CatBoostRegressor",
        "version": app.version,
        "tree_count": model.tree_count_,
        "feature_count": len(model.feature_names_),
        "test_rmse": metrics.get("rmse"),
    }


@app.post("/predict", response_model=PredictResponse)
def predict_courses(payload: PredictRequest, request: Request) -> PredictResponse:
    values = infer(request, payload.candidates)
    return PredictResponse(
        predictions=[
            Prediction(index=index, predicted_rating=value)
            for index, value in enumerate(values)
        ]
    )


@app.post("/rank", response_model=RankResponse)
def rank_courses(payload: PredictRequest, request: Request) -> RankResponse:
    values = infer(request, payload.candidates)
    sorted_values = sorted(enumerate(values), key=lambda item: item[1], reverse=True)
    return RankResponse(
        rankings=[
            RankedPrediction(index=index, predicted_rating=value, rank=rank)
            for rank, (index, value) in enumerate(sorted_values, start=1)
        ]
    )


@app.post("/recommend/places", response_model=PlaceRecommendationResponse)
def recommend_places(
    payload: PlaceRecommendationRequest,
    request: Request,
    limit: int = Query(default=DEFAULT_RESULT_LIMIT, ge=1, le=MAX_RESULT_LIMIT),
) -> PlaceRecommendationResponse:
    anchor = resolve_anchor(payload, request)
    treatments = resolve_treatments(payload)
    candidates = request.app.state.candidate_service.recommend(
        anchor=anchor,
        treatments=treatments,
        user_purpose=payload.user_purpose,
        user_walk_preference=payload.user_walk_preference,
        limit=limit,
    )
    return PlaceRecommendationResponse(
        data=PlaceRecommendationData(
            anchor=AnchorResponse(
                name=anchor.name,
                latitude=anchor.latitude,
                longitude=anchor.longitude,
                anchor_type=anchor.anchor_type,
            ),
            active_treatments=[ActiveTreatmentResponse(**vars(item)) for item in treatments],
            candidate_places=[CandidatePlaceResponse(**item) for item in candidates],
        )
    )


def resolve_anchor(payload: PlaceRecommendationRequest, request: Request) -> Anchor:
    if payload.user_purpose not in VALID_PURPOSES:
        raise HTTPException(status_code=422, detail="Unsupported user_purpose")
    coordinates = (payload.anchor_latitude, payload.anchor_longitude)
    if (coordinates[0] is None) != (coordinates[1] is None):
        raise HTTPException(status_code=422, detail="Both anchor coordinates are required")
    if coordinates[0] is None:
        anchor = request.app.state.place_repository.find_anchor(payload.title)
        if anchor is None:
            raise HTTPException(status_code=404, detail="Anchor not found")
        return anchor
    return Anchor(
        name=payload.title,
        latitude=coordinates[0],
        longitude=coordinates[1],
        anchor_type=payload.anchor_type,
    )


def resolve_treatments(payload: PlaceRecommendationRequest) -> list[TreatmentContext]:
    if payload.treatments is None:
        events = [
            TreatmentEventInput(
                treatment=payload.treatment,
                days_after=payload.days_after,
            )
        ]
    else:
        events = payload.treatments

    contexts = []
    for event in events:
        if event.treatment not in VALID_TREATMENTS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported treatment: {event.treatment}",
            )
        if event.days_after is not None:
            days_after = event.days_after
        else:
            recommendation_at = payload.recommendation_at
            scheduled_at = event.scheduled_at
            recommendation_in_treatment_tz = recommendation_at.astimezone(
                scheduled_at.tzinfo
            )
            if recommendation_in_treatment_tz < scheduled_at:
                continue
            days_after = (
                recommendation_in_treatment_tz.date() - scheduled_at.date()
            ).days
        contexts.append(
            TreatmentContext(
                treatment=event.treatment,
                days_after=days_after,
                hospital_name=event.hospital_name,
                package_id=event.package_id,
            )
        )
    return contexts


@app.post("/recommend/courses", response_model=CourseRecommendationResponse)
def recommend_courses(
    payload: PlaceRecommendationRequest,
    request: Request,
    top_n: int = Query(default=DEFAULT_TOP_COURSES, ge=1, le=MAX_TOP_COURSES),
) -> CourseRecommendationResponse:
    anchor = resolve_anchor(payload, request)
    treatments = resolve_treatments(payload)
    courses = request.app.state.course_service.recommend(
        anchor=anchor,
        treatments=treatments,
        user_purpose=payload.user_purpose,
        user_walk_preference=payload.user_walk_preference,
        top_n=top_n,
    )
    return CourseRecommendationResponse(
        data=CourseRecommendationData(
            anchor=AnchorResponse(
                name=anchor.name,
                latitude=anchor.latitude,
                longitude=anchor.longitude,
                anchor_type=anchor.anchor_type,
            ),
            active_treatments=[ActiveTreatmentResponse(**vars(item)) for item in treatments],
            courses=[CourseResponse(**course) for course in courses],
        )
    )
