import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


REQUIRED_COLUMNS = {
    "placeName",
    "kakaoPlaceId",
    "collectionTypes",
    "categoryName",
    "addressName",
    "roadAddressName",
    "mapX",
    "mapY",
}

TYPE_ORDER = [
    "skin_treatment_hospital",
    "tourist_attraction",
    "cafe",
    "cultural_facility",
    "large_mart",
    "hospital",
    "department_store",
    "beauty_store",
]

TYPE_NAMES = {
    "skin_treatment_hospital": "피부시술병원",
    "tourist_attraction": "관광명소",
    "cafe": "카페",
    "cultural_facility": "문화시설",
    "large_mart": "대형마트",
    "hospital": "병원",
    "department_store": "백화점",
    "beauty_store": "뷰티매장",
}

PLACE_GROUPS = {
    "bulk": {"beauty_store", "cafe", "large_mart"},
    "manual": {"tourist_attraction", "department_store", "cultural_facility"},
}

OUTPUT_COLUMNS = [
    "placeName",
    "kakaoPlaceId",
    "primaryType",
    "primaryTypeName",
    "collectionTypes",
    "skinTreatmentConfidence",
    "skinTreatmentSignals",
    "categoryName",
    "categoryGroupCode",
    "categoryGroupName",
    "phone",
    "addressName",
    "roadAddressName",
    "mapX",
    "mapY",
    "placeUrl",
]

MANUAL_OUTPUT_COLUMNS = [
    "placeName",
    "kakaoPlaceId",
    "isIndoor",
    "walkHard",
    "isNa",
    *OUTPUT_COLUMNS[2:],
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean Kakao place CSV data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/gangnam_kakao_places.csv"),
        help="Source CSV path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/gangnam_kakao_places_cleaned.csv"),
        help="Cleaned CSV path",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/gangnam_kakao_places_cleaning_report.json"),
        help="Cleaning report JSON path",
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=Path("data/gangnam_skin_hospitals_review.csv"),
        help="CSV path for medium-confidence skin-treatment hospitals",
    )
    parser.add_argument(
        "--hospitals",
        type=Path,
        default=Path("data/gangnam_skin_treatment_hospitals.csv"),
        help="CSV path for all retained skin-treatment hospitals",
    )
    parser.add_argument(
        "--bulk-places",
        type=Path,
        default=Path("data/gangnam_places_beauty_cafe_mart.csv"),
        help="CSV path for beauty stores, cafes, and large marts",
    )
    parser.add_argument(
        "--manual-places",
        type=Path,
        default=Path("data/gangnam_places_attraction_department_culture.csv"),
        help="CSV path for attractions, department stores, and cultural facilities",
    )
    return parser.parse_args()


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_types(value: str | None) -> list[str]:
    types = {item.strip() for item in (value or "").split("|") if item.strip()}
    return sorted(types, key=lambda item: (TYPE_ORDER.index(item) if item in TYPE_ORDER else 999, item))


def coordinate(value: str | None, minimum: float, maximum: float) -> str | None:
    try:
        number = float(value or "")
    except ValueError:
        return None
    if not minimum <= number <= maximum:
        return None
    return f"{number:.10f}".rstrip("0").rstrip(".")


def clean_row(row: dict[str, str]) -> tuple[dict[str, str] | None, str | None]:
    cleaned = {key: normalize_text(value) for key, value in row.items()}
    if not cleaned["kakaoPlaceId"] or not cleaned["placeName"]:
        return None, "missing_identity"

    if not (
        cleaned["addressName"].startswith("서울 강남구 ")
        or cleaned["roadAddressName"].startswith("서울 강남구 ")
    ):
        return None, "outside_gangnam"

    map_x = coordinate(cleaned["mapX"], 124.0, 132.0)
    map_y = coordinate(cleaned["mapY"], 33.0, 39.0)
    if map_x is None or map_y is None:
        return None, "invalid_coordinates"

    types = normalize_types(cleaned["collectionTypes"])
    if not types:
        return None, "missing_type"

    if "hospital" in types:
        signals = normalize_types(cleaned.get("searchSignals", ""))
        if "피부과" in cleaned["categoryName"]:
            types = normalize_types("|".join([*types, "skin_treatment_hospital"]))
            signals = ["kakao_category:피부과", *signals]
        if "skin_treatment_hospital" not in types:
            return None, "non_skin_treatment_hospital"
        cleaned["skinTreatmentSignals"] = "|".join(signals)
        cleaned["skinTreatmentConfidence"] = (
            "confirmed"
            if "피부과" in cleaned["categoryName"]
            else "high"
            if len(signals) >= 2
            else "medium"
        )

    primary_type = types[0]
    cleaned.update(
        {
            "primaryType": primary_type,
            "primaryTypeName": TYPE_NAMES.get(primary_type, primary_type),
            "collectionTypes": "|".join(types),
            "mapX": map_x,
            "mapY": map_y,
        }
    )
    return {column: cleaned.get(column, "") for column in OUTPUT_COLUMNS}, None


def main() -> None:
    args = parse_args()
    removals: Counter[str] = Counter()
    by_id: dict[str, dict[str, str]] = {}
    input_rows = 0

    with args.input.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        for row in reader:
            input_rows += 1
            cleaned, reason = clean_row(row)
            if reason:
                removals[reason] += 1
                continue
            if cleaned["kakaoPlaceId"] in by_id:
                removals["duplicate_kakao_place_id"] += 1
                continue
            by_id[cleaned["kakaoPlaceId"]] = cleaned

    rows = sorted(by_id.values(), key=lambda row: (row["primaryType"], row["placeName"]))
    hospital_rows = [
        row for row in rows if row["primaryType"] == "skin_treatment_hospital"
    ]
    place_rows = [
        row for row in rows if row["primaryType"] != "skin_treatment_hospital"
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.hospitals.parent.mkdir(parents=True, exist_ok=True)
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.bulk_places.parent.mkdir(parents=True, exist_ok=True)
    args.manual_places.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(place_rows)

    with args.hospitals.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(hospital_rows)

    bulk_place_rows = [
        row for row in place_rows if row["primaryType"] in PLACE_GROUPS["bulk"]
    ]
    manual_place_rows = [
        row for row in place_rows if row["primaryType"] in PLACE_GROUPS["manual"]
    ]
    for output_path, grouped_rows in (
        (args.bulk_places, bulk_place_rows),
        (
            args.manual_places,
            [
                {**row, "isIndoor": "0", "walkHard": "0", "isNa": "0"}
                for row in manual_place_rows
            ],
        ),
    ):
        with output_path.open("w", encoding="utf-8-sig", newline="") as destination:
            fieldnames = (
                MANUAL_OUTPUT_COLUMNS
                if output_path == args.manual_places
                else OUTPUT_COLUMNS
            )
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(grouped_rows)

    review_rows = [
        row
        for row in hospital_rows
        if row["skinTreatmentConfidence"] == "medium"
    ]
    with args.review.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(review_rows)

    type_counts = Counter(row["primaryType"] for row in rows)
    report = {
        "input": str(args.input),
        "output": str(args.output),
        "hospitalOutput": str(args.hospitals),
        "inputRows": input_rows,
        "outputRows": len(place_rows),
        "hospitalRows": len(hospital_rows),
        "bulkPlaceRows": len(bulk_place_rows),
        "manualPlaceRows": len(manual_place_rows),
        "reviewRows": len(review_rows),
        "removedRows": sum(removals.values()),
        "removalsByReason": dict(sorted(removals.items())),
        "rowsByPrimaryTypeBeforeSplit": dict(sorted(type_counts.items())),
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
