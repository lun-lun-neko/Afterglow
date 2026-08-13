const fs = require("fs");
const path = require("path");

loadEnv(path.resolve(process.cwd(), ".env"));

const API_KEY = process.env.KAKAO_REST_API_KEY;
const DATA_DIR = path.resolve(process.cwd(), "data");
const ENDPOINT = "https://dapi.kakao.com/v2/local/search/category.json";
const CATEGORY_CODE = "AD5";
const PAGE_SIZE = 15;
const MAX_DEPTH = 10;
const REQUEST_DELAY_MS = Number(process.env.KAKAO_PLACE_DELAY_MS || 100);
const RETRY_COUNT = 5;

const DISTRICTS = {
  gangnam: {
    name: "강남구",
    addressPrefix: "서울 강남구",
    bounds: { west: 127.008, south: 37.456, east: 127.125, north: 37.536 },
    output: "gangnam_accommodations.csv",
  },
  seocho: {
    name: "서초구",
    addressPrefix: "서울 서초구",
    bounds: { west: 126.975, south: 37.425, east: 127.095, north: 37.525 },
    output: "seocho_accommodations.csv",
  },
};

const COLUMNS = [
  "placeName", "kakaoPlaceId", "primaryType", "primaryTypeName",
  "collectionTypes", "skinTreatmentConfidence", "skinTreatmentSignals",
  "categoryName", "categoryGroupCode", "categoryGroupName", "phone",
  "addressName", "roadAddressName", "mapX", "mapY", "placeUrl",
];

if (!API_KEY) {
  console.error("KAKAO_REST_API_KEY is required in .env or the environment.");
  process.exit(1);
}

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const text = line.trim();
    if (!text || text.startsWith("#")) continue;
    const separator = text.indexOf("=");
    if (separator < 1) continue;
    const key = text.slice(0, separator).trim();
    let value = text.slice(separator + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1);
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const rect = (b) => [b.west, b.south, b.east, b.north].join(",");

function splitBounds(b) {
  const midX = (b.west + b.east) / 2;
  const midY = (b.south + b.north) / 2;
  return [
    { west: b.west, south: b.south, east: midX, north: midY },
    { west: midX, south: b.south, east: b.east, north: midY },
    { west: b.west, south: midY, east: midX, north: b.north },
    { west: midX, south: midY, east: b.east, north: b.north },
  ];
}

async function request(bounds, page) {
  const url = new URL(ENDPOINT);
  url.searchParams.set("category_group_code", CATEGORY_CODE);
  url.searchParams.set("rect", rect(bounds));
  url.searchParams.set("page", String(page));
  url.searchParams.set("size", String(PAGE_SIZE));
  for (let attempt = 1; attempt <= RETRY_COUNT; attempt += 1) {
    await sleep(REQUEST_DELAY_MS);
    const response = await fetch(url, { headers: { Authorization: `KakaoAK ${API_KEY}` } });
    if (response.ok) return response.json();
    const body = await response.text();
    if (response.status !== 429 && response.status < 500) {
      throw new Error(`Kakao API ${response.status}: ${body}`);
    }
    await sleep(500 * attempt);
  }
  throw new Error("Kakao API request failed after retries");
}

function addPlaces(target, district, documents) {
  for (const place of documents) {
    if (!(place.address_name.startsWith(district.addressPrefix) ||
          place.road_address_name.startsWith(district.addressPrefix))) continue;
    target.set(place.id, place);
  }
}

async function collectBounds(target, district, bounds, stats, depth = 0) {
  const first = await request(bounds, 1);
  stats.requests += 1;
  if (first.meta.pageable_count >= 45 && depth < MAX_DEPTH) {
    for (const child of splitBounds(bounds)) {
      await collectBounds(target, district, child, stats, depth + 1);
    }
    return;
  }
  addPlaces(target, district, first.documents);
  const pages = Math.ceil(first.meta.pageable_count / PAGE_SIZE);
  for (let page = 2; page <= pages; page += 1) {
    const result = await request(bounds, page);
    stats.requests += 1;
    addPlaces(target, district, result.documents);
  }
  if (first.meta.pageable_count >= 45) stats.saturatedCells += 1;
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function writeCsv(filePath, places) {
  const rows = [...places.values()]
    .sort((a, b) => a.place_name.localeCompare(b.place_name, "ko"))
    .map((place) => ({
      placeName: place.place_name,
      kakaoPlaceId: place.id,
      primaryType: "accommodation",
      primaryTypeName: "숙박시설",
      collectionTypes: "accommodation",
      skinTreatmentConfidence: "",
      skinTreatmentSignals: "",
      categoryName: place.category_name,
      categoryGroupCode: place.category_group_code,
      categoryGroupName: place.category_group_name,
      phone: place.phone,
      addressName: place.address_name,
      roadAddressName: place.road_address_name,
      mapX: place.x,
      mapY: place.y,
      placeUrl: place.place_url,
    }));
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const csv = [COLUMNS, ...rows.map((row) => COLUMNS.map((key) => row[key]))]
    .map((row) => row.map(csvCell).join(","))
    .join("\r\n");
  fs.writeFileSync(filePath, `\uFEFF${csv}\r\n`, "utf8");
  return rows;
}

async function main() {
  const report = {};
  for (const [key, district] of Object.entries(DISTRICTS)) {
    const places = new Map();
    const stats = { requests: 0, saturatedCells: 0 };
    console.log(`Collecting ${district.name} accommodations...`);
    await collectBounds(places, district, district.bounds, stats);
    const outputPath = path.join(DATA_DIR, district.output);
    const rows = writeCsv(outputPath, places);
    report[key] = { output: outputPath, rows: rows.length, ...stats };
    console.log(`${district.name}: ${rows.length} unique places, ${stats.requests} requests`);
  }
  fs.writeFileSync(
    path.join(DATA_DIR, "kakao_accommodations_report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );
  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
