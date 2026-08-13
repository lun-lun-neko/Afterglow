const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const INPUT = path.join(
  ROOT,
  'data',
  'gangnam_seocho_places_drugstore_attraction_department_culture.csv'
);
const OUTPUT = path.join(
  ROOT,
  'data',
  'gangnam_seocho_places_drugstore_attraction_department_culture_popularity.csv'
);
const REPORT = path.join(
  ROOT,
  'data',
  'gangnam_seocho_places_drugstore_attraction_department_culture_popularity_report.json'
);

const NUMERIC_COLUMNS = new Set(['popularity', 'isIndoor', 'walkHard', 'isNa']);
const REQUEST_DELAY_MS = Number(process.env.KAKAO_PLACE_DELAY_MS || 180);
const MAX_RETRIES = Number(process.env.KAKAO_PLACE_MAX_RETRIES || 4);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else if (ch !== '\r') {
      cell += ch;
    }
  }

  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  return rows.filter((csvRow) => csvRow.some((value) => value !== ''));
}

function toObjects(csvRows) {
  const headers = csvRows[0];
  return {
    headers,
    rows: csvRows.slice(1).map((values) => {
      const object = {};
      headers.forEach((header, index) => {
        object[header] = values[index] ?? '';
      });
      return object;
    }),
  };
}

function quoteCsvValue(value, columnName) {
  const stringValue = String(value ?? '');

  if (NUMERIC_COLUMNS.has(columnName) && /^-?\d+(\.\d+)?$/.test(stringValue)) {
    return stringValue;
  }

  return `"${stringValue.replace(/"/g, '""')}"`;
}

function writeCsv(filePath, headers, rows) {
  const lines = [
    headers.map((header) => quoteCsvValue(header, '')).join(','),
    ...rows.map((row) =>
      headers.map((header) => quoteCsvValue(row[header], header)).join(',')
    ),
  ];
  fs.writeFileSync(filePath, `\ufeff${lines.join('\r\n')}\r\n`, 'utf8');
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function calculatePopularity({ averageScore, kakaoReviewCount, blogReviewCount }) {
  const ratingScore = kakaoReviewCount > 0 ? averageScore : null;
  const blogScore = clamp(Math.log10(blogReviewCount + 1) * 2.5, 0, 5);
  const raw = ratingScore == null ? blogScore : ratingScore * 0.7 + blogScore * 0.3;
  return clamp(Math.round(raw), 0, 5);
}

function getHeaders(placeId) {
  return {
    Accept: 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    Origin: 'https://place.map.kakao.com',
    Referer: `https://place.map.kakao.com/${placeId}`,
    'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    appVersion: '6.6.0',
    pf: 'PC',
  };
}

async function fetchJson(url, placeId) {
  let lastError;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt += 1) {
    try {
      const response = await fetch(url, { headers: getHeaders(placeId) });

      if (response.ok) {
        const text = await response.text();
        if (!text.trim()) return {};
        return JSON.parse(text);
      }

      lastError = new Error(`HTTP ${response.status}`);
      if (![408, 429, 500, 502, 503, 504].includes(response.status)) {
        break;
      }
    } catch (error) {
      lastError = error;
    }

    await sleep(REQUEST_DELAY_MS * attempt * 2);
  }

  throw lastError;
}

function normalizeCount(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : 0;
}

async function fetchPopularitySignals(placeId) {
  const kakaoReviewUrl =
    `https://place-api.map.kakao.com/places/tab/reviews/kakaomap/${placeId}` +
    '?order=RECOMMENDED&only_photo_review=false';
  const blogReviewUrl =
    `https://place-api.map.kakao.com/places/tab/reviews/blog/${placeId}?page=1`;

  const [kakaoReviewData, blogReviewData] = await Promise.all([
    fetchJson(kakaoReviewUrl, placeId),
    fetchJson(blogReviewUrl, placeId),
  ]);

  const scoreSet = kakaoReviewData?.score_set ?? {};
  const kakaoReviewCount = normalizeCount(scoreSet.review_count);
  const averageScore = normalizeCount(scoreSet.average_score);
  const blogReviewCount = normalizeCount(blogReviewData?.review_count);
  const popularity = calculatePopularity({
    averageScore,
    kakaoReviewCount,
    blogReviewCount,
  });

  return {
    popularity,
    averageScore,
    kakaoReviewCount,
    blogReviewCount,
  };
}

function getOutputHeaders(headers) {
  if (headers.includes('popularity')) return headers;

  const kakaoPlaceIdIndex = headers.indexOf('kakaoPlaceId');
  if (kakaoPlaceIdIndex === -1) return [...headers, 'popularity'];

  return [
    ...headers.slice(0, kakaoPlaceIdIndex + 1),
    'popularity',
    ...headers.slice(kakaoPlaceIdIndex + 1),
  ];
}

async function main() {
  if (!fs.existsSync(INPUT)) {
    throw new Error(`Input file not found: ${INPUT}`);
  }

  const csv = parseCsv(fs.readFileSync(INPUT, 'utf8'));
  const { headers, rows } = toObjects(csv);
  const outputHeaders = getOutputHeaders(headers);
  const reportRows = [];
  const failures = [];

  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const placeId = row.kakaoPlaceId;

    try {
      const signals = await fetchPopularitySignals(placeId);
      row.popularity = signals.popularity;
      reportRows.push({
        placeName: row.placeName,
        kakaoPlaceId: placeId,
        ...signals,
      });
    } catch (error) {
      row.popularity = 0;
      failures.push({
        placeName: row.placeName,
        kakaoPlaceId: placeId,
        error: error.message,
      });
      reportRows.push({
        placeName: row.placeName,
        kakaoPlaceId: placeId,
        popularity: 0,
        averageScore: 0,
        kakaoReviewCount: 0,
        blogReviewCount: 0,
        failed: true,
      });
    }

    if ((index + 1) % 20 === 0 || index + 1 === rows.length) {
      console.log(`Processed ${index + 1}/${rows.length}`);
    }

    await sleep(REQUEST_DELAY_MS);
  }

  writeCsv(OUTPUT, outputHeaders, rows);

  const distribution = rows.reduce((acc, row) => {
    const key = String(row.popularity);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const report = {
    input: path.relative(ROOT, INPUT),
    output: path.relative(ROOT, OUTPUT),
    generatedAt: new Date().toISOString(),
    rowCount: rows.length,
    failures,
    popularityFormula:
      'round(average_score * 0.7 + min(5, log10(blog_review_count + 1) * 2.5) * 0.3), or blog score only when Kakao review count is 0',
    popularityDistribution: distribution,
    rows: reportRows,
  };

  fs.writeFileSync(REPORT, JSON.stringify(report, null, 2), 'utf8');

  console.log(`Wrote ${OUTPUT}`);
  console.log(`Wrote ${REPORT}`);
  console.log(`Failures: ${failures.length}`);
  console.log(`Distribution: ${JSON.stringify(distribution)}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
