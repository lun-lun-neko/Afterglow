# Data Files

이 폴더는 카카오 로컬 API와 의료관광 API에서 수집한 CSV/리포트 파일을 관리합니다.

## 주의

`gangnam_places_attraction_department_culture.csv`는 수작업 입력 원본입니다. 정제 스크립트는 이 파일을 덮어쓰지 않습니다. `isNa=1`을 제거한 결과는 별도 파일 `gangnam_places_attraction_department_culture_active.csv`로 생성합니다.

## 현재 수집 기준

- 강남구: 관광명소, 문화시설, 백화점, 병원, 드럭스토어
- 서초구: 관광명소, 문화시설, 백화점, 병원, 드럭스토어
- 더 이상 신규 수집하지 않는 항목: 카페, 뷰티매장, 대형마트

## 강남구

- `gangnam_kakao_places.csv`: 강남구 카카오 원본 데이터
- `gangnam_skin_treatment_hospitals.csv`: 강남구 피부과 및 피부 시술 병원
- `gangnam_places_attraction_department_culture.csv`: 강남구 관광명소/백화점/문화시설 수작업 원본, 덮어쓰기 금지
- `gangnam_places_attraction_department_culture_active.csv`: 위 파일에서 `isNa=1`을 제거한 사용 대상
- `gangnam_drugstores.csv`: 강남구 드럭스토어, `isIndoor=1`, `walkHard=2`, `isNa=0`
- `gangnam_places_beauty_cafe_mart.csv`: 기존 카페/뷰티매장/대형마트 데이터, 신규 수집 안 함, 추후 제거 예정

## 서초구

- `seocho_kakao_places.csv`: 서초구 카카오 원본 데이터
- `seocho_skin_treatment_hospitals.csv`: 서초구 피부과 및 피부 시술 병원
- `seocho_places_attraction_department_culture.csv`: 서초구 관광명소/백화점/문화시설, 기본값 `isIndoor=0`, `walkHard=0`, `isNa=0`
- `seocho_places_attraction_department_culture_active.csv`: 서초구 수작업 대상 사용 파일
- `seocho_drugstores.csv`: 서초구 드럭스토어, `isIndoor=1`, `walkHard=2`, `isNa=0`
- `seocho_places_drugstore_attraction_department_culture.csv`: 서초구 드럭스토어와 관광명소/백화점/문화시설 통합 파일

## 기타

- `gangnam_dermatology_skin_aesthetic_hospitals.csv`: 한국관광공사 의료관광 API 기반 강남구 피부과·피부미용 의료기관
- `kakao_places_cleaning_report.json`: 구별 정제 실행 리포트

## 실행

카카오 원본 수집:

```powershell
node scripts/collect_kakao_gangnam_places.js --all
```

정제 및 파일 분리:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean_kakao_places.ps1
```
