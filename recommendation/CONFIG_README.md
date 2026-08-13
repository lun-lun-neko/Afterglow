# Afterglow 추천 설정 가이드

이 문서는 [`config.py`](./config.py)에 정의된 규칙과 설정값을 개발자, 기획자, 의료정책 검토자가 함께 확인할 수 있도록 설명한다.

현재 설정은 규칙 기반 MVP 정책이다. 의료진의 진료나 개별 병원의 사후관리 지침을 대체하지 않으며, 운영 전 의료진 검수가 필요하다. 특정 병원의 안내가 공통 정책보다 엄격한 경우 병원별 정책으로 덮어쓰는 기능은 아직 구현되지 않았다.

## 1. 처리 흐름

추천 엔진은 다음 순서로 동작한다.

```text
사용자 요청과 Anchor
→ 반경 내 장소 조회
→ 장소 위험 신호 추출
→ 시술 및 경과일 규칙 적용
→ BLOCK 장소 제거
→ Place Score 계산
→ 장소 3개 조합
→ 최단 방문 순서와 거리 제한 확인
→ Course Score 계산
→ 서로 충분히 다른 Top 코스 반환
```

## 2. 장소 검색 및 반환 설정

| 설정 | 현재 값 | 의미 |
|---|---:|---|
| `MAX_SEARCH_RADIUS_KM` | 5.0km | Anchor에서 이 거리를 초과한 장소는 후보에서 제외한다. |
| `DEFAULT_RESULT_LIMIT` | 20 | `/recommend/places`의 기본 반환 개수다. |
| `MAX_RESULT_LIMIT` | 100 | 장소 추천 API에서 요청할 수 있는 최대 개수다. |
| `DEFAULT_PURPOSE_SCORE` | 50 | 목적과 카테고리 조합이 점수표에 없을 때 적용한다. |

거리 계산에는 Haversine 직선거리를 사용한다. 실제 도보 경로 또는 이동시간이 아니므로 강, 고속도로, 건물 출입구 같은 이동 제약은 아직 반영되지 않는다.

## 3. Place Score

장소 점수는 0~100 범위이며 다음 식으로 계산한다.

```text
Place Score
= 목적 적합도 × 0.35
+ 시술 적합도 × 0.30
+ 거리 적합도 × 0.20
+ 도보 적합도 × 0.15
```

`SCORE_WEIGHTS`:

| 요소 | 가중치 |
|---|---:|
| 목적 적합도 `purpose` | 35% |
| 시술 적합도 `treatment` | 30% |
| 거리 적합도 `distance` | 20% |
| 도보 적합도 `walk` | 15% |

가중치를 변경할 때 합계가 1.0인지 확인해야 한다.

### 시술 판정 점수

`TREATMENT_SCORE`:

| 상태 | 점수 | 처리 방식 |
|---|---:|---|
| `NORMAL` | 100 | 정상적으로 점수를 계산한다. |
| `PENALTY` | 50 | 후보에는 남지만 시술 적합도에서 감점한다. |
| `BLOCK` | 없음 | 점수 계산 전에 후보에서 완전히 제거한다. |

다른 조건이 모두 같다면 `PENALTY`는 `NORMAL`보다 최종 Place Score가 15점 낮다.

### 거리 점수

`DISTANCE_SCORE_BANDS`는 `(거리 상한 km, 점수)` 형식이며 순서대로 검사한다.

| Anchor와의 거리 | 점수 |
|---|---:|
| 0~0.5km | 100 |
| 0.5km 초과~1km | 90 |
| 1km 초과~2km | 75 |
| 2km 초과~3km | 55 |
| 3km 초과~5km | 30 |
| 5km 초과 | 후보 제외 |

상한값은 해당 구간에 포함된다. 예를 들어 정확히 0.5km는 100점이다.

### 도보 점수

사용자 도보 선호도와 장소의 `walkHard`는 모두 1~5 척도다.

```text
초과 단계 = max(0, walkHard - user_walk_preference)
```

`WALK_SCORE_BY_EXCESS`와 `WALK_SCORE_LARGE_EXCESS`:

| 초과 단계 | 점수 |
|---:|---:|
| 0 이하 | 100 |
| 1 | 75 |
| 2 | 40 |
| 3 이상 | 10 |

사용자의 도보 선호도가 높다고 해서 쉬운 장소를 감점하지 않는다. 예를 들어 선호도 5, 장소 난이도 1이면 100점이다.

## 4. 목적별 장소 점수

현재 유효한 목적은 `PURPOSE_CATEGORY_SCORE`의 최상위 키에서 자동 생성한다.

```text
문화관광
뷰티쇼핑
휴식
```

현재 후보 데이터의 네 카테고리에 적용되는 점수는 다음과 같다.

| 목적 | 문화시설 | 관광명소 | 백화점 | 드럭스토어 |
|---|---:|---:|---:|---:|
| 문화관광 | 100 | 95 | 60 | 40 |
| 뷰티쇼핑 | 45 | 35 | 90 | 95 |
| 휴식 | 75 | 55 | 65 | 60 |

내부 카테고리 이름:

| 한글 의미 | 내부 값 |
|---|---|
| 문화시설 | `cultural_facility` |
| 관광명소 | `tourist_attraction` |
| 백화점 | `department_store` |
| 드럭스토어 | `drugstore` |

새 목적을 `PURPOSE_CATEGORY_SCORE`에 추가하면 `VALID_PURPOSES`에도 자동 반영된다.

## 5. 의료 위험 신호

장소는 하나 이상의 위험 신호를 가질 수 있다.

| 설정 | 위험 신호 | 판정 기준 |
|---|---|---|
| `RISK_HIGH_ACTIVITY` | `HIGH_ACTIVITY` | `walkHard >= 4` |
| `RISK_OUTDOOR_EXPOSURE` | `OUTDOOR_EXPOSURE` | `isIndoor = 0` |
| `RISK_HEAT_EXPOSURE` | `HEAT_EXPOSURE` | 카테고리명에 열 노출 키워드 포함 |
| `RISK_MASSAGE_PRESSURE` | `MASSAGE_PRESSURE` | 카테고리명에 마사지·압박 키워드 포함 |

열 노출 키워드 `HEAT_CATEGORY_KEYWORDS`:

```text
사우나, 찜질방, 온천
```

마사지·압박 키워드 `MASSAGE_CATEGORY_KEYWORDS`:

```text
마사지, 경락, 안마, 스파
```

여러 위험 신호가 동시에 적용되면 가장 강한 판정을 사용한다.

```text
BLOCK > PENALTY > NORMAL
```

현재 후보 CSV에는 사우나와 마사지 시설이 없으므로 `HEAT_EXPOSURE`와 `MASSAGE_PRESSURE`는 실제 데이터에서 아직 발생하지 않는다. 관련 카테고리 장소가 추가되면 기존 키워드 규칙으로 자동 판정된다.

## 6. 경과일 해석

`days_after`는 0 이상의 정수이며 0은 시술 당일이다.

규칙 튜플은 다음 형식이다.

```python
(시작일, 종료일, "상태")
```

시작일과 종료일을 모두 포함한다.

```text
(0, 3, "BLOCK") → 0, 1, 2, 3일에 BLOCK
(4, 7, "PENALTY") → 4, 5, 6, 7일에 PENALTY
```

해당 날짜에 일치하는 규칙이 없으면 `NORMAL`이다. 현재 정책에서는 대부분 8일 이후 `NORMAL`로 돌아간다.

## 7. 시술별 위험 정책

아래 표는 `TREATMENT_RISK_RULES`의 전체 내용을 나타낸다.

| 시술 | 고강도 활동 | 장시간 야외·직사광선 | 사우나·찜질방 | 마사지·압박 |
|---|---|---|---|---|
| 리프팅 | 0~2일 `PENALTY` | 0~7일 `PENALTY` | 0~7일 `BLOCK` | 0~7일 `PENALTY` |
| 보톡스 | 0일 `BLOCK`, 1~7일 `PENALTY` | `NORMAL` | 0~7일 `BLOCK` | 0~7일 `BLOCK` |
| 필러 | 0~1일 `BLOCK` | 0~3일 `PENALTY` | 0~7일 `BLOCK` | 0~3일 `BLOCK` |
| 스킨부스터 | 0~7일 `BLOCK` | 0~7일 `PENALTY` | 0~7일 `BLOCK` | 0~2일 `BLOCK` |
| 윤곽/체형주사 | 0~7일 `BLOCK` | `NORMAL` | 0~7일 `BLOCK` | 0~7일 `BLOCK` |
| 필링 | 0~7일 `BLOCK` | 0~7일 `BLOCK` | 0~7일 `BLOCK` | 0~7일 `PENALTY` |
| 피부레이저 | 0~3일 `PENALTY` | 0~3일 `BLOCK`, 4~7일 `PENALTY` | 0~7일 `BLOCK` | 0~3일 `PENALTY` |
| 피부관리 | `NORMAL` | 0~7일 `PENALTY` | 0~7일 `BLOCK` | 0~2일 `PENALTY` |
| 제모 | `NORMAL` | 0~7일 `PENALTY` | 0~7일 `BLOCK` | `NORMAL` |
| 비만(약처방) | `NORMAL` | `NORMAL` | `NORMAL` | `NORMAL` |

### 정책 해석 시 주의사항

- 리프팅은 실리프팅과 초음파·고주파 리프팅을 현재 입력값에서 구분하지 않는다. 마사지·압박 규칙은 보수적인 공통값이다.
- 보톡스의 일반 공통 정책은 당일 고강도 활동을 `BLOCK`, 1~7일을 `PENALTY`로 처리한다. 병원이 7일 운동 금지를 명시한 경우 해당 병원만 `BLOCK`하도록 덮어쓰는 기능은 아직 없다.
- 제모는 고강도 활동을 일괄 차단하지 않는다. 0~7일 야외 노출만 `PENALTY`이며 `BLOCK`하지 않는다.
- 이 표는 서비스 MVP 정책이며 개별 사용자의 상태나 의료진 지시를 대신하지 않는다.

## 8. 유효 입력값

`VALID_TREATMENTS`는 `TREATMENT_RISK_RULES`에서 자동 생성된다.

```text
리프팅
보톡스
필러
스킨부스터
윤곽/체형주사
필링
피부레이저
피부관리
제모
비만(약처방)
```

시술을 추가할 때는 `TREATMENT_RISK_RULES`에 항목을 추가하면 API 허용 목록에도 자동 반영된다. `NORMAL`만 필요한 시술도 빈 딕셔너리로 등록해야 한다.

```python
"새 시술": {}
```

## 9. 코스 구성 정책

`CourseService`는 Place Score가 계산된 장소를 사용해 코스를 만든다.

| 설정 | 현재 값 | 의미 |
|---|---:|---|
| `COURSE_PLACE_COUNT` | 3 | 코스당 장소 수 |
| `DEFAULT_TOP_COURSES` | 3 | 기본 반환 코스 수 |
| `MAX_TOP_COURSES` | 10 | API에서 요청 가능한 최대 코스 수 |
| `COURSE_CANDIDATES_PER_CATEGORY` | 12 | 각 카테고리에서 코스 조합에 사용할 상위 장소 수 |
| `MAX_SAME_CATEGORY_PER_COURSE` | 2 | 한 코스에 같은 카테고리를 넣을 수 있는 최대 횟수 |
| `MIN_DISTINCT_CATEGORIES` | 2 | 한 코스가 포함해야 하는 최소 카테고리 종류 수 |
| `MAX_LEG_DISTANCE_KM` | 2.0km | Anchor→첫 장소 및 장소 간 각 구간의 최대 거리 |
| `MAX_COURSE_DISTANCE_KM` | 5.0km | Anchor→장소1→장소2→장소3의 거리 합계 상한 |
| `MAX_SHARED_PLACES_BETWEEN_TOP_COURSES` | 1 | Top 코스 두 개가 공통으로 가질 수 있는 장소 수 |

Anchor로 돌아오는 거리는 현재 계산하지 않는다.

장소 3개의 가능한 순서 6개를 모두 계산하고, 거리 제한을 만족하는 순서 중 총 이동 거리가 가장 짧은 순서를 사용한다.

후보 장소를 전체 점수순으로만 자르면 특정 카테고리가 후보를 독점할 수 있다. 이를 방지하기 위해 카테고리별 상위 12개를 조합 후보로 사용한다.

## 10. 목적별 코스 필수 조건

`PURPOSE_REQUIRED_CATEGORIES`와 `REST_MIN_INDOOR_PLACES`가 담당한다.

| 목적 | 필수 조건 |
|---|---|
| 문화관광 | 문화시설 또는 관광명소가 최소 1개 필요 |
| 뷰티쇼핑 | 드럭스토어 또는 백화점이 최소 1개 필요 |
| 휴식 | 실내 장소가 최소 2개 필요 |

조건을 만족하지 않는 장소 조합은 Course Score를 계산하지 않고 제외한다.

## 11. Course Score

```text
Course Score
= 장소 평균 Place Score × 0.60
+ 이동 거리 점수 × 0.20
+ 카테고리 다양성 점수 × 0.10
+ 목적 구성 점수 × 0.10
```

`COURSE_SCORE_WEIGHTS`:

| 요소 | 가중치 |
|---|---:|
| 장소 평균 점수 `places` | 60% |
| 이동 거리 `route` | 20% |
| 카테고리 다양성 `diversity` | 10% |
| 목적 구성 `purpose_composition` | 10% |

가중치 합계는 1.0이어야 한다.

### 코스 거리 점수

`COURSE_DISTANCE_SCORE_BANDS`:

| 코스 총 거리 | 점수 |
|---|---:|
| 0~1.5km | 100 |
| 1.5km 초과~3km | 80 |
| 3km 초과~4km | 60 |
| 4km 초과~5km | 40 |
| 5km 초과 | 코스 제외 |

### 카테고리 다양성 점수

```text
3개 장소가 모두 다른 카테고리 → 100점
2개 카테고리로 구성 → 70점
1개 카테고리로 구성 → 코스 제외
```

### 목적 구성 점수

- 문화관광·뷰티쇼핑: 선호 카테고리가 2개 이상이면 100점, 1개이면 75점이다.
- 휴식: 실내 장소 3개이면 100점, 2개이면 80점이다. 1개 이하는 코스에서 제외한다.

## 12. Top 코스 다양성

Course Score가 높은 순서대로 선택하되 이미 선택된 코스와 공통 장소가 설정값을 초과하면 건너뛴다.

현재 값은 다음과 같다.

```text
두 코스가 공유할 수 있는 장소: 최대 1개
```

따라서 장소 2개 이상이 같은 유사 코스가 Top 결과를 차지하지 못한다.

## 13. 데이터 파일

Anchor 파일 `ANCHOR_DATA_FILE`:

```text
gangnam_seocho_skin_hospitals_accommodations.csv
```

병원과 숙소 이름 및 좌표를 조회한다.

후보 장소 파일 `CANDIDATE_DATA_FILES`:

```text
gangnam_seocho_places_drugstore_attraction_department_culture.csv
```

현재 이 파일 하나만 사용한다. `isNa=1`인 행은 로딩 시 제외한다. `isIndoor` 또는 `walkHard`가 비어 있거나 올바른 숫자가 아닌 장소도 제외한다.

## 14. 설정 변경 시 점검사항

1. Place Score 및 Course Score 가중치 합계가 각각 1.0인지 확인한다.
2. 거리 점수 구간은 상한이 작은 순서대로 배치한다.
3. 날짜 구간의 시작일과 종료일이 겹치거나 역전되지 않았는지 확인한다.
4. 상태 문자열은 `NORMAL`, `PENALTY`, `BLOCK` 중 하나만 사용한다.
5. 새로운 목적을 추가하면 모든 현재 장소 카테고리에 대한 점수를 검토한다.
6. 새로운 후보 카테고리를 추가하면 목적 점수와 위험 신호 추출 기준을 함께 검토한다.
7. `COURSE_PLACE_COUNT`를 3에서 변경하면 방문 순서 계산 비용과 테스트를 다시 검토한다.
8. 설정 변경 후 아래 테스트를 실행한다.

```powershell
python -m unittest discover -s tests -v
```

## 15. 관련 코드

- 설정값: [`config.py`](./config.py)
- 의료 위험 신호 및 기간 판정: [`treatment_filter.py`](./treatment_filter.py)
- Haversine 및 장소 거리 점수: [`distance_service.py`](./distance_service.py)
- Place Score: [`place_score.py`](./place_score.py)
- 후보 조회 및 필터 적용: [`candidate_service.py`](./candidate_service.py)
- 코스 조합·순서·Course Score: [`course_service.py`](./course_service.py)
- FastAPI 엔드포인트: [`../model_server.py`](../model_server.py)
- 테스트: [`../tests/test_recommendation.py`](../tests/test_recommendation.py)
