# Kakao Place Collection

This project collects Kakao Local API place data inside Gangnam-gu.

## Required API key

Create or use a Kakao Developers app, enable Kakao Map API, and add its REST API
key to `.env`.

`.env`:

```dotenv
KAKAO_REST_API_KEY=your-rest-api-key
```

Run:

```powershell
node scripts/collect_kakao_gangnam_places.js
```

The script creates `data/gangnam_kakao_places.csv`.

Default searches:

- `AT4`: tourist attractions
- `CE7`: cafes
- `CT1`: cultural facilities, including galleries and exhibition facilities
- `MT1`: large marts
- `HP8`: hospitals
- Skin-treatment hospital keywords: dermatology, skin procedures, Botox, fillers,
  lifting, skin lasers, acne, hair removal, Thermage, and Ulthera
- Keyword `백화점`: department stores, because Kakao has no department-store category group code
- Beauty-store keywords: cosmetics stores and H&B brands such as Olive Young,
  Lalavla, Chicor, and Sephora

The Kakao Local API exposes at most 45 results for one search range. The script
recursively divides Gangnam-gu into smaller rectangles, deduplicates results by
Kakao place ID, and filters the final results to addresses in Gangnam-gu.

## Clean collected CSV

The PowerShell entry point finds Conda, creates or updates the project environment,
and runs the Python cleaner:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean_kakao_places.ps1
```

Outputs:

- `data/gangnam_kakao_places_cleaned.csv`: cleaned places with all hospitals removed
- `data/gangnam_skin_treatment_hospitals.csv`: all retained skin-treatment hospitals
- `data/gangnam_kakao_places_cleaning_report.json`
- `data/gangnam_skin_hospitals_review.csv`

Multiple Python interpreters are safe because the entry point always uses Python
from the named Conda environment `afterglow-data-clean`.

The cleaner keeps hospitals only when Kakao classifies them as dermatology or
when they appear in one of the skin-treatment keyword searches. Other hospitals
are removed.

Dermatology-category hospitals are marked `confirmed`. Hospitals found by two or
more skin-treatment keywords are marked `high`, and single-keyword matches are
marked `medium` and copied to the review CSV.
