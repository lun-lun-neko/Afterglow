from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


DEFAULT_DATA = Path("data/data2.csv")
DEFAULT_MODEL = Path("models/course_rating_catboost_v4.cbm")
DEFAULT_METRICS = Path("models/course_rating_catboost_v4_metrics.json")
DEFAULT_IMPORTANCE = Path("models/course_rating_catboost_v4_feature_importance.csv")
TARGET = "Course_Rating"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the v4 CatBoost course-rating model.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--importance-out", type=Path, default=DEFAULT_IMPORTANCE)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def add_engineered_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    walk_columns = ["Walk_Hard_1", "Walk_Hard_2", "Walk_Hard_3"]
    indoor_columns = ["Is_Indoor_1", "Is_Indoor_2", "Is_Indoor_3"]
    result["Mean_Walk_Hard"] = result[walk_columns].mean(axis=1)
    result["Indoor_Count"] = result[indoor_columns].sum(axis=1)
    result["Preference_Hard_Diff"] = (
        result["User_Walk_Preference"] - result["Mean_Walk_Hard"]
    ).abs()
    return result


def main() -> None:
    args = parse_args()
    data = add_engineered_features(pd.read_csv(args.data, encoding="utf-8-sig"))
    feature_columns = CATEGORICAL_COLUMNS + NUMERIC_COLUMNS
    missing = sorted(set(feature_columns + [TARGET]) - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    x = data[feature_columns]
    y = data[TARGET]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=args.test_size, random_state=args.random_state
    )
    train_pool = Pool(x_train, y_train, cat_features=CATEGORICAL_COLUMNS)
    test_pool = Pool(x_test, y_test, cat_features=CATEGORICAL_COLUMNS)

    model = CatBoostRegressor(
        iterations=5000,
        learning_rate=0.01,
        depth=6,
        l2_leaf_reg=1.0,
        random_strength=1.0,
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=args.random_state,
        allow_writing_files=False,
    )
    model.fit(
        train_pool,
        eval_set=test_pool,
        early_stopping_rounds=50,
        verbose=50,
        use_best_model=True,
    )

    predictions = model.predict(test_pool)
    metrics = {
        "model": "CatBoostRegressor",
        "data": str(args.data),
        "rows": int(len(data)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "test_size": args.test_size,
        "random_state": args.random_state,
        "best_iteration": int(model.get_best_iteration()),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
        "categorical_features": CATEGORICAL_COLUMNS,
        "numeric_features": NUMERIC_COLUMNS,
        "parameters": model.get_params(),
    }

    for output in (args.model_out, args.metrics_out, args.importance_out):
        output.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(args.model_out)
    args.metrics_out.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame({
        "feature": feature_columns,
        "importance": model.get_feature_importance(train_pool),
    }).sort_values("importance", ascending=False).to_csv(
        args.importance_out, index=False, encoding="utf-8-sig"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
