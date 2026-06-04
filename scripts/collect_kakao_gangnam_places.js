const fs = require("fs");
const path = require("path");

loadEnv(path.resolve(process.cwd(), ".env"));

const API_KEY = process.env.KAKAO_REST_API_KEY;
const OUTPUT_PATH = path.resolve(
  process.cwd(),
  process.env.KAKAO_OUTPUT || "data/gangnam_kakao_places.csv",
);

// Covers Gangnam-gu. Results are filtered by their returned Gangnam-gu address.
const GANGNAM_BOUNDS = {
  west: 127.008,
  south: 37.456,
  east: 127.125,
  north: 37.536,
};

const SEARCHES = [
  { type: "category", value: "AT4", label: "tourist_attraction" },
  { type: "category", value: "CE7", label: "cafe" },
  { type: "category", value: "CT1", label: "cultural_facility" },
  { type: "category", value: "MT1", label: "large_mart" },
  { type: "category", value: "HP8", label: "hospital" },
  ...[
    "피부과",
    "피부시술",
    "피부클리닉",
    "보톡스",
    "필러",
    "리프팅",
    "피부레이저",
    "여드름",
    "제모",
    "써마지",
    "울쎄라",
  ].map((keyword) => ({
    type: "keyword",
    value: keyword,
    label: "skin_treatment_hospital",
    signal: keyword,
    matches: isSkinTreatmentHospital,
  })),
  {
    type: "keyword",
    value: "백화점",
    label: "department_store",
    matches: (place) => place.category_name.includes("백화점"),
  },
  {
    type: "keyword",
    value: "화장품",
    label: "beauty_store",
    matches: isBeautyStore,
  },
  {
    type: "keyword",
    value: "올리브영",
    label: "beauty_store",
    matches: isBeautyStore,
  },
  {
    type: "keyword",
    value: "랄라블라",
    label: "beauty_store",
    matches: isBeautyStore,
  },
  {
    type: "keyword",
    value: "시코르",
    label: "beauty_store",
    matches: isBeautyStore,
  },
  {
    type: "keyword",
    value: "세포라",
    label: "beauty_store",
    matches: isBeautyStore,
  },
];

const MAX_DEPTH = 9;
const PAGE_SIZE = 15;
const REQUEST_DELAY_MS = 80;
const RETRY_COUNT = 5;
const places = new Map();
let requestCount = 0;

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separator = trimmed.indexOf("=");
    if (separator < 1) {
      continue;
    }

    const name = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (process.env[name] === undefined) {
      process.env[name] = value;
    }
  }
}

if (!API_KEY) {
  console.error(
    "KAKAO_REST_API_KEY is required. Add it to .env or set the environment variable.",
  );
  process.exit(1);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toRect(bounds) {
  return [bounds.west, bounds.south, bounds.east, bounds.north].join(",");
}

function splitBounds(bounds) {
  const midX = (bounds.west + bounds.east) / 2;
  const midY = (bounds.south + bounds.north) / 2;
  return [
    { west: bounds.west, south: bounds.south, east: midX, north: midY },
    { west: midX, south: bounds.south, east: bounds.east, north: midY },
    { west: bounds.west, south: midY, east: midX, north: bounds.north },
    { west: midX, south: midY, east: bounds.east, north: bounds.north },
  ];
}

function isBeautyStore(place) {
  const category = place.category_name;
  const name = place.place_name;
  return (
    /화장품|향수|미용재료|네일아트용품/.test(category) ||
    /올리브영|랄라블라|시코르|세포라/.test(name)
  );
}

function isSkinTreatmentHospital(place) {
  const allowedCategories = [
    "피부과",
    "성형외과",
    "일반의원",
    "가정의학과",
  ];
  return (
    place.category_name.startsWith("의료,건강 > 병원") &&
    allowedCategories.some((category) => place.category_name.includes(category))
  );
}

async function requestPlaces(search, bounds, page = 1) {
  const endpoint =
    search.type === "category"
      ? "https://dapi.kakao.com/v2/local/search/category.json"
      : "https://dapi.kakao.com/v2/local/search/keyword.json";
  const url = new URL(endpoint);

  if (search.type === "category") {
    url.searchParams.set("category_group_code", search.value);
  } else {
    url.searchParams.set("query", search.value);
  }
  url.searchParams.set("rect", toRect(bounds));
  url.searchParams.set("page", String(page));
  url.searchParams.set("size", String(PAGE_SIZE));

  for (let attempt = 1; attempt <= RETRY_COUNT; attempt += 1) {
    await sleep(REQUEST_DELAY_MS);
    requestCount += 1;
    const response = await fetch(url, {
      headers: { Authorization: `KakaoAK ${API_KEY}` },
    });

    if (response.ok) {
      return response.json();
    }

    const body = await response.text();
    if (response.status !== 429 && response.status < 500) {
      throw new Error(`Kakao API ${response.status}: ${body}`);
    }
    await sleep(500 * attempt);
  }

  throw new Error(`Kakao API request failed after ${RETRY_COUNT} attempts`);
}

function isGangnam(place) {
  return (
    place.address_name.startsWith("서울 강남구 ") ||
    place.road_address_name.startsWith("서울 강남구 ")
  );
}

function addPlace(place, search) {
  if (!isGangnam(place) || (search.matches && !search.matches(place))) {
    return;
  }

  const existing = places.get(place.id);
  if (existing) {
    existing.collection_types.add(search.label);
    if (search.signal) {
      existing.search_signals.add(search.signal);
    }
    return;
  }

  places.set(place.id, {
    ...place,
    collection_types: new Set([search.label]),
    search_signals: new Set(search.signal ? [search.signal] : []),
  });
}

async function collectBounds(search, bounds, depth = 0) {
  const firstPage = await requestPlaces(search, bounds, 1);

  // Kakao exposes at most 45 places per search. Split dense areas to avoid loss.
  if (firstPage.meta.pageable_count >= 45 && depth < MAX_DEPTH) {
    for (const child of splitBounds(bounds)) {
      await collectBounds(search, child, depth + 1);
    }
    return;
  }

  firstPage.documents.forEach((place) => addPlace(place, search));
  const pageCount = Math.ceil(firstPage.meta.pageable_count / PAGE_SIZE);
  for (let page = 2; page <= pageCount; page += 1) {
    const result = await requestPlaces(search, bounds, page);
    result.documents.forEach((place) => addPlace(place, search));
  }

  if (firstPage.meta.pageable_count >= 45) {
    console.warn(
      `Warning: reached the 45-result limit at max depth for ${search.label}: ${toRect(bounds)}`,
    );
  }
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function writeCsv() {
  const columns = [
    "placeName",
    "kakaoPlaceId",
    "collectionTypes",
    "searchSignals",
    "categoryName",
    "categoryGroupCode",
    "categoryGroupName",
    "phone",
    "addressName",
    "roadAddressName",
    "mapX",
    "mapY",
    "placeUrl",
  ];
  const rows = [...places.values()]
    .sort((a, b) => a.place_name.localeCompare(b.place_name, "ko"))
    .map((place) => [
      place.place_name,
      place.id,
      [...place.collection_types].sort().join("|"),
      [...place.search_signals].sort().join("|"),
      place.category_name,
      place.category_group_code,
      place.category_group_name,
      place.phone,
      place.address_name,
      place.road_address_name,
      place.x,
      place.y,
      place.place_url,
    ]);
  const csv = [columns, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
  fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
  fs.writeFileSync(OUTPUT_PATH, `\uFEFF${csv}`, "utf8");
}

async function main() {
  for (const search of SEARCHES) {
    const before = places.size;
    console.log(`Collecting ${search.label}...`);
    await collectBounds(search, GANGNAM_BOUNDS);
    console.log(`  added ${places.size - before}, total unique ${places.size}`);
  }

  writeCsv();
  console.log(`Created ${OUTPUT_PATH}`);
  console.log(`Places: ${places.size}, API requests: ${requestCount}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
