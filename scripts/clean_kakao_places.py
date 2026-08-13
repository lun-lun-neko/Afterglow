import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


DISTRICTS = {
    "gangnam": {"nameKo": "강남구", "addressPrefix": "서울 강남구 "},
    "seocho": {"nameKo": "서초구", "addressPrefix": "서울 서초구 "},
}

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
    "drugstore",
    "tourist_attraction",
    "department_store",
    "cultural_facility",
    "hospital",
]

TYPE_NAMES = {
    "skin_treatment_hospital": "피부시술병원",
    "drugstore": "드럭스토어",
    "tourist_attraction": "관광명소",
    "department_store": "백화점",
    "cultural_facility": "문화시설",
    "hospital": "병원",
}

MANUAL_TYPES = {"tourist_attraction", "department_store", "cultural_facility"}
DRUGSTORE_TYPES = {"drugstore"}

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

ANNOTATED_OUTPUT_COLUMNS = [
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
        "--district",
        choices=[*DISTRICTS.keys(), "all"],
        default="all",
        help="District to clean",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
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


def district_paths(data_dir: Path, district_key: str) -> dict[str, Path]:
    return {
        "input": data_dir / f"{district_key}_kakao_places.csv",
        "cleaned": data_dir / f"{district_key}_kakao_places_cleaned.csv",
        "hospitals": data_dir / f"{district_key}_skin_treatment_hospitals.csv",
        "review": data_dir / f"{district_key}_skin_hospitals_review.csv",
        "manual": data_dir / f"{district_key}_places_attraction_department_culture.csv",
        "manual_active": data_dir / f"{district_key}_places_attraction_department_culture_active.csv",
        "drugstores": data_dir / f"{district_key}_drugstores.csv",
        "seocho_combined": data_dir / "seocho_places_drugstore_attraction_department_culture.csv",
    }


def load_annotations(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"kakaoPlaceId", "isIndoor", "walkHard", "isNa"}
        if not required.issubset(reader.fieldnames or []):
            return {}
        return {
            row["kakaoPlaceId"]: {
                "isIndoor": normalize_text(row.get("isIndoor")),
                "walkHard": normalize_text(row.get("walkHard")),
                "isNa": normalize_text(row.get("isNa")),
            }
            for row in reader
            if row.get("kakaoPlaceId")
        }


def annotate_row(row: dict[str, str], annotations: dict[str, dict[str, str]]) -> dict[str, str]:
    saved = annotations.get(row["kakaoPlaceId"])
    if saved:
        is_indoor = saved.get("isIndoor") or "0"
        walk_hard = saved.get("walkHard") or "0"
        is_na = saved.get("isNa") or "0"
    elif row["primaryType"] == "drugstore":
        is_indoor = "1"
        walk_hard = "2"
        is_na = "0"
    else:
        is_indoor = "0"
        walk_hard = "0"
        is_na = "0"

    return {**row, "isIndoor": is_indoor, "walkHard": walk_hard, "isNa": is_na}


def clean_row(
    row: dict[str, str],
    district: dict[str, str],
) -> tuple[dict[str, str] | None, str | None]:
    cleaned = {key: normalize_text(value) for key, value in row.items()}
    if not cleaned["kakaoPlaceId"] or not cleaned["placeName"]:
        return None, "missing_identity"

    if not (
        cleaned["addressName"].startswith(district["addressPrefix"])
        or cleaned["roadAddressName"].startswith(district["addressPrefix"])
    ):
        return None, "outside_district"

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


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def process_district(data_dir: Path, district_key: str) -> dict[str, object]:
    district = DISTRICTS[district_key]
    paths = district_paths(data_dir, district_key)
    if not paths["input"].exists():
        return {
            "district": district_key,
            "skipped": True,
            "reason": f"missing input: {paths['input']}",
        }

    removals: Counter[str] = Counter()
    by_id: dict[str, dict[str, str]] = {}
    input_rows = 0

    with paths["input"].open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{paths['input']} missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            input_rows += 1
            cleaned, reason = clean_row(row, district)
            if reason:
                removals[reason] += 1
                continue
            if cleaned["kakaoPlaceId"] in by_id:
                removals["duplicate_kakao_place_id"] += 1
                continue
            by_id[cleaned["kakaoPlaceId"]] = cleaned

    rows = sorted(by_id.values(), key=lambda row: (row["primaryType"], row["placeName"]))
    annotations = load_annotations(paths["manual"])

    hospital_rows = [row for row in rows if row["primaryType"] == "skin_treatment_hospital"]
    review_rows = [row for row in hospital_rows if row["skinTreatmentConfidence"] == "medium"]
    drugstore_rows = [
        annotate_row(row, {}) for row in rows if row["primaryType"] in DRUGSTORE_TYPES
    ]
    manual_rows_all = [
        annotate_row(row, annotations) for row in rows if row["primaryType"] in MANUAL_TYPES
    ]
    manual_rows_active = [row for row in manual_rows_all if row["isNa"] != "1"]
    removed_manual_na = len(manual_rows_all) - len(manual_rows_active)
    if removed_manual_na:
        removals["manual_is_na"] += removed_manual_na

    place_rows = [
        row
        for row in rows
        if row["primaryType"] not in {"skin_treatment_hospital", "hospital"}
        and row["kakaoPlaceId"] not in {item["kakaoPlaceId"] for item in manual_rows_all if item["isNa"] == "1"}
    ]

    write_csv(paths["cleaned"], OUTPUT_COLUMNS, place_rows)
    write_csv(paths["hospitals"], OUTPUT_COLUMNS, hospital_rows)
    write_csv(paths["review"], OUTPUT_COLUMNS, review_rows)
    write_csv(paths["drugstores"], ANNOTATED_OUTPUT_COLUMNS, drugstore_rows)
    write_csv(paths["manual_active"], ANNOTATED_OUTPUT_COLUMNS, manual_rows_active)

    # Never overwrite an existing manual annotation file. It may contain hand-entered work.
    if district_key != "gangnam" and not paths["manual"].exists():
        write_csv(paths["manual"], ANNOTATED_OUTPUT_COLUMNS, manual_rows_all)

    if district_key == "seocho":
        combined = sorted(
            [*manual_rows_active, *drugstore_rows],
            key=lambda row: (row["primaryType"], row["placeName"]),
        )
        write_csv(paths["seocho_combined"], ANNOTATED_OUTPUT_COLUMNS, combined)

    type_counts = Counter(row["primaryType"] for row in rows)
    return {
        "district": district_key,
        "input": str(paths["input"]),
        "inputRows": input_rows,
        "cleanedOutput": str(paths["cleaned"]),
        "cleanedRows": len(place_rows),
        "hospitalOutput": str(paths["hospitals"]),
        "hospitalRows": len(hospital_rows),
        "drugstoreOutput": str(paths["drugstores"]),
        "drugstoreRows": len(drugstore_rows),
        "manualSource": str(paths["manual"]),
        "manualActiveOutput": str(paths["manual_active"]),
        "manualActiveRows": len(manual_rows_active),
        "reviewRows": len(review_rows),
        "removedRows": sum(removals.values()),
        "removalsByReason": dict(sorted(removals.items())),
        "rowsByPrimaryType": dict(sorted(type_counts.items())),
    }


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir
    districts = DISTRICTS.keys() if args.district == "all" else [args.district]
    reports = [process_district(data_dir, district) for district in districts]

    report_path = data_dir / "kakao_places_cleaning_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"districts": reports}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"districts": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
