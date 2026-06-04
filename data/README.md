# Data Files

이 폴더는 프로젝트에서 수집하고 정제한 장소 데이터를 관리합니다.

## 파일 설명

### `gangnam_kakao_places.csv`

카카오 로컬 API에서 수집한 강남구 장소 원본 데이터입니다.

- 관광명소, 카페, 문화시설, 대형마트, 병원, 백화점, 뷰티 매장 포함
- 카카오 장소 ID 기준 중복 제거
- 피부 시술 병원 판별에 사용한 검색 키워드는 `searchSignals`에 기록
- 수집 명령:

```powershell
node scripts/collect_kakao_gangnam_places.js
```

### `gangnam_kakao_places_cleaned.csv`

정제된 일반 장소 데이터입니다.

- 병원 데이터는 모두 제거됨
- 강남구 주소, 유효 좌표, 필수값 검증 완료
- 카페, 관광명소, 문화시설, 대형마트, 백화점, 뷰티 매장 포함
- 3716 행 부터 기타시설. 이전까지는 카페, 음식점, 뷰티 매장 등 <- 이것들은 나중에 묶어서 처리

### `gangnam_places_beauty_cafe_mart.csv`

추후 묶어서 처리할 일반 장소 데이터입니다.

- 뷰티 매장
- 카페
- 대형마트

### `gangnam_places_attraction_department_culture.csv`

수작업 검토 및 처리를 위한 장소 데이터입니다.

- 관광명소
- 백화점
- 문화시설
- 수작업용 `isIndoor`, `walkHard`, `isNa` 컬럼 포함

### `gangnam_skin_treatment_hospitals.csv`

피부과 및 피부 시술을 제공하는 것으로 판별된 병원 전용 데이터입니다.

- `confirmed`: 카카오 세부 카테고리가 피부과
- `high`: 피부 시술 관련 검색 키워드 2개 이상에 노출
- `medium`: 피부 시술 관련 검색 키워드 1개에 노출
- 세 등급 모두 최종 병원 데이터에 포함

### `gangnam_skin_hospitals_review.csv`

`medium` 신뢰도로 판별된 피부 시술 병원만 모은 검토용 데이터입니다.
검사용 데이터 지금은 별 필요x

### `gangnam_dermatology_skin_aesthetic_hospitals.csv`

한국관광공사 의료관광 API에서 수집한 피부과·피부미용 의료기관 데이터입니다.

- 카카오 장소 데이터와 별도 데이터 소스
- 병원이름, `contentId`, 주소, 좌표 포함

### `gangnam_kakao_places_cleaning_report.json`

정제 실행 결과 리포트입니다.

- 입력 및 출력 행 수
- 제거된 행 수와 사유
- 분리된 피부 시술 병원 수
- 장소 분류별 행 수

## 정제 실행

Conda 전용 환경에서 수집 원본을 정제하고 일반 장소와 피부 시술 병원 CSV로 분리합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean_kakao_places.ps1
```
