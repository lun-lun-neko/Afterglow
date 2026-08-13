from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DEFAULT_DATA = Path("data/afterglow_real_hospitals_dataset.csv")
DEFAULT_MODEL = Path("models/course_rating_lightgbm.joblib")
DEFAULT_METRICS = Path("models/course_rating_lightgbm_metrics.json")

CATEGORICAL_COLUMNS = [
    "Hospital_Name",
    "Treatment",
    "Weather",
    "User_Purpose",
]

NUMERIC_COLUMNS = [
    "User_Walk_Preference",
    "Days_After",
    "stop_count",
    "indoor_ratio",
    "walk_hard_mean",
    "walk_hard_max",
    "distance_mean_km",
    "distance_max_km",
    "distance_sum_km",
    "category_count",
    "sports_ratio",
    "outdoor_attraction_ratio",
    "culture_ratio",
    "shopping_ratio",
    "food_cafe_ratio",
]

CATEGORY_RATIO_COLUMNS = {
    "레포츠": "sports_ratio",
    "명소(야외)": "outdoor_attraction_ratio",
    "문화시설": "culture_ratio",
    "쇼핑": "shopping_ratio",
    "음식점/카페": "food_cafe_ratio",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a LightGBM model that predicts a course rating."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def load_course_features(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig")

    required = {
        "Course_ID",
        "User_ID",
        "User_Walk_Preference",
        "Hospital_Name",
        "Treatment",
        "Days_After",
        "Weather",
        "User_Purpose",
        "Place_Category",
        "Is_Indoor",
        "Walk_Hard",
        "Distance_KM",
        "Course_Rating",
    }
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    numeric_raw = [
        "User_Walk_Preference",
        "Days_After",
        "Is_Indoor",
        "Walk_Hard",
        "Distance_KM",
        "Course_Rating",
    ]
    for column in numeric_raw:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    if raw[numeric_raw].isna().any().any():
        bad = raw[numeric_raw].isna().sum()
        bad = bad[bad > 0].to_dict()
        raise ValueError(f"Invalid numeric values found: {bad}")

    fixed_columns = [
        "User_ID",
        "User_Walk_Preference",
        "Hospital_Name",
        "Treatment",
        "Days_After",
        "Weather",
        "User_Purpose",
        "Course_Rating",
    ]
    inconsistent: dict[str, int] = {}
    grouped = raw.groupby("Course_ID", sort=False)
    for column in fixed_columns:
        count = grouped[column].nunique(dropna=False)
        if (count > 1).any():
            inconsistent[column] = int((count > 1).sum())
    if inconsistent:
        raise ValueError(f"Course-level columns vary within a course: {inconsistent}")

    first = grouped[fixed_columns].first()
    aggregate = grouped.agg(
        stop_count=("Place_Name", "size"),
        indoor_ratio=("Is_Indoor", "mean"),
        walk_hard_mean=("Walk_Hard", "mean"),
        walk_hard_max=("Walk_Hard", "max"),
        distance_mean_km=("Distance_KM", "mean"),
        distance_max_km=("Distance_KM", "max"),
        distance_sum_km=("Distance_KM", "sum"),
        category_count=("Place_Category", "nunique"),
    )
    category_ratios = (
        pd.crosstab(raw["Course_ID"], raw["Place_Category"], normalize="index")
        .reindex(columns=CATEGORY_RATIO_COLUMNS, fill_value=0.0)
        .rename(columns=CATEGORY_RATIO_COLUMNS)
    )
    courses = first.join(aggregate).join(category_ratios).reset_index()

    duplicate_context = courses.duplicated(
        subset=[
            "User_ID",
            "User_Walk_Preference",
            "Hospital_Name",
            "Treatment",
            "Days_After",
            "Weather",
            "User_Purpose",
        ],
        keep=False,
    )
    courses.attrs["ranking_contexts_with_multiple_candidates"] = int(
        duplicate_context.sum()
    )
    return courses


def build_pipeline(random_state: int) -> Pipeline:
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", min_frequency=2),
                CATEGORICAL_COLUMNS,
            ),
            ("numeric", "passthrough", NUMERIC_COLUMNS),
        ]
    )
    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=700,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=30,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=0.2,
        random_state=random_state,
        n_jobs=-1,
        verbosity=-1,
    )
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def main() -> None:
    args = parse_args()
    courses = load_course_features(args.data)

    features = CATEGORICAL_COLUMNS + NUMERIC_COLUMNS
    target = "Course_Rating"
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    train_idx, test_idx = next(
        splitter.split(courses[features], courses[target], groups=courses["User_ID"])
    )
    train = courses.iloc[train_idx]
    test = courses.iloc[test_idx]

    pipeline = build_pipeline(args.random_state)
    pipeline.fit(train[features], train[target])
    prediction = pipeline.predict(test[features])

    metrics = {
        "data_path": str(args.data),
        "model_type": "LGBMRegressor",
        "target": target,
        "split": "grouped_by_User_ID",
        "synthetic_target_warning": (
            "Course_Rating is synthetic; metrics measure reproduction of the "
            "synthetic rating rule, not real user satisfaction."
        ),
        "ranking_note": (
            "The source has no repeated candidate courses for the same complete "
            "user context, so a ranker is not identifiable. Rank generated "
            "candidate courses by this regressor's predicted rating."
        ),
        "course_count": int(len(courses)),
        "train_course_count": int(len(train)),
        "test_course_count": int(len(test)),
        "train_user_count": int(train["User_ID"].nunique()),
        "test_user_count": int(test["User_ID"].nunique()),
        "ranking_contexts_with_multiple_candidates": int(
            courses.attrs["ranking_contexts_with_multiple_candidates"]
        ),
        "rmse": float(np.sqrt(mean_squared_error(test[target], prediction))),
        "mae": float(mean_absolute_error(test[target], prediction)),
        "r2": float(r2_score(test[target], prediction)),
        "rating_mean": float(test[target].mean()),
        "rating_std": float(test[target].std()),
        "features": features,
    }

    artifact = {
        "pipeline": pipeline,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "numeric_columns": NUMERIC_COLUMNS,
        "feature_columns": features,
        "target": target,
        "metrics": metrics,
    }
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.model_out)
    args.metrics_out.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"Saved model: {args.model_out}")
    print(f"Saved metrics: {args.metrics_out}")


if __name__ == "__main__":
    main()
