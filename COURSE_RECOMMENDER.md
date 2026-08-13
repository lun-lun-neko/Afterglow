# LightGBM course rating model

The first recommendation model predicts the rating of a complete candidate
course. The application can generate several valid candidate courses, predict a
rating for each one, and return them in descending score order.

The source data does not contain multiple candidate courses for the same full
user context. For that reason, an `LGBMRanker` cannot learn a within-context
ranking from this dataset. This version uses `LGBMRegressor`; it can be replaced
with a ranker after real impressions and choices provide candidate groups.

`Course_Rating` is an LLM-generated synthetic label. Offline metrics therefore
measure how well the model reproduces that label, not real user satisfaction.

## Setup

```powershell
conda env create -f environment.yml
conda activate afterglow-data-clean
```

If the environment already exists:

```powershell
conda env update -f environment.yml --prune
```

## Train

From the repository root:

```powershell
python scripts/train_course_lightgbm.py
```

Outputs:

- `models/course_rating_lightgbm.joblib`
- `models/course_rating_lightgbm_metrics.json`

The train/test split is grouped by `User_ID`, preventing the same synthetic user
from appearing in both partitions.

## Candidate input

Each candidate course must be summarized into the same fields used during
training:

- context: hospital, treatment, weather, purpose, walking preference, days after
  treatment
- course: stop count, indoor ratio, walking difficulty statistics, distance
  statistics, category diversity, and the ratio of stops in each category

Do not pass arbitrary or medically unsafe courses to the model. Safety,
operating-hours, travel-radius, and post-treatment restrictions should be
applied before scoring.

## Serve with FastAPI

Install/update the environment, then start the model API from the repository
root:

```powershell
conda env update -f environment.yml --prune
conda activate afterglow-data-clean
uvicorn model_server:app --host 127.0.0.1 --port 8001
```

Interactive API documentation is available at `http://127.0.0.1:8001/docs`.
The server exposes:

- `GET /health`: verify that the model artifact loaded
- `POST /predict`: predict ratings for one or more candidate courses
- `POST /rank`: predict and sort candidates by descending rating

Set `MODEL_PATH` to use a different artifact:

```powershell
$env:MODEL_PATH='models/course_rating_lightgbm.joblib'
uvicorn model_server:app --port 8001
```

### Model input fields

`POST /predict` and `POST /rank` accept a `candidates` array. Each item describes
one complete candidate course.

| Field | Type / range | Description |
| --- | --- | --- |
| `Hospital_Name` | non-empty string | 시술을 받은 병원명 |
| `Treatment` | non-empty string | 받은 시술의 종류 또는 분류 |
| `Weather` | non-empty string | 코스 이용 시점의 날씨 또는 대기 상태 |
| `User_Purpose` | non-empty string | 코스를 이용하는 주된 목적 |
| `User_Walk_Preference` | number | 사용자의 걷기 선호도. 학습 데이터와 같은 척도를 사용 |
| `Days_After` | integer, 0 이상 | 시술일로부터 지난 일수. 시술 당일은 `0` |
| `stop_count` | integer, 1 이상 | 후보 코스에 포함된 방문 장소 수 |
| `indoor_ratio` | 0~1 | 전체 장소 중 실내 장소의 비율 |
| `walk_hard_mean` | number, 0 이상 | 장소별 보행 난이도의 평균 |
| `walk_hard_max` | number, 0 이상 | 장소별 보행 난이도 중 최댓값 |
| `distance_mean_km` | number, 0 이상 | 장소별 이동 거리의 평균(km) |
| `distance_max_km` | number, 0 이상 | 장소별 이동 거리 중 최댓값(km) |
| `distance_sum_km` | number, 0 이상 | 코스의 장소별 이동 거리 합계(km) |
| `category_count` | integer, 1 이상 | 코스에 포함된 서로 다른 장소 카테고리 수 |
| `sports_ratio` | 0~1 | 전체 장소 중 스포츠 카테고리의 비율 |
| `outdoor_attraction_ratio` | 0~1 | 전체 장소 중 야외 명소 카테고리의 비율 |
| `culture_ratio` | 0~1 | 전체 장소 중 문화시설 카테고리의 비율 |
| `shopping_ratio` | 0~1 | 전체 장소 중 쇼핑 카테고리의 비율 |
| `food_cafe_ratio` | 0~1 | 전체 장소 중 음식점·카페 카테고리의 비율 |

`walk_hard_max`는 `walk_hard_mean` 이상이어야 하고,
`distance_max_km`는 `distance_mean_km` 이상이어야 합니다. 다섯 개의
카테고리 비율 합은 `1`이어야 합니다(부동소수점 반올림 오차 `0.001`
허용). 예를 들어 모든 비율에 `1`을 넣으면 합이 `5`이므로 요청이
거부됩니다.

Example:

```json
{
  "candidates": [
    {
      "Hospital_Name": "나나성형외과의원",
      "Treatment": "윤곽/체형주사",
      "Weather": "미세먼지 나쁨",
      "User_Purpose": "뷰티쇼핑",
      "User_Walk_Preference": 1,
      "Days_After": 1,
      "stop_count": 3,
      "indoor_ratio": 1.0,
      "walk_hard_mean": 2.0,
      "walk_hard_max": 2.0,
      "distance_mean_km": 1.5,
      "distance_max_km": 2.9,
      "distance_sum_km": 4.5,
      "category_count": 2,
      "sports_ratio": 0.0,
      "outdoor_attraction_ratio": 0.0,
      "culture_ratio": 0.0,
      "shopping_ratio": 0.67,
      "food_cafe_ratio": 0.33
    }
  ]
}
```
