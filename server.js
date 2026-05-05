const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = Number(process.env.PORT || 8000);
const medicalApiBase = "https://apis.data.go.kr/B551011/MdclTursmService";
const medicalApiKey = "6ebdab7e4a7fc5d7abcaa400bc5c2d3ca458a6053f15374e1a6491af1203a527";

const areaCodes = {
  gangnam: { lDongRegnCd: "11", lDongSignguCd: "680" },
  seomyeon: { lDongRegnCd: "26", lDongSignguCd: "230" },
};

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
};

const server = http.createServer(async (request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host}`);
  const requestedPath = decodeURIComponent(requestUrl.pathname);

  if (requestedPath === "/api/medical") {
    await handleMedicalApi(requestUrl, response);
    return;
  }

  const relativePath = requestedPath === "/" ? "index.html" : requestedPath.replace(/^[/\\]+/, "");
  const filePath = path.resolve(root, relativePath);

  if (!filePath.startsWith(root)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": types[path.extname(filePath)] || "application/octet-stream" });
    response.end(content);
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Afterglow MVP running at http://127.0.0.1:${port}`);
});

async function handleMedicalApi(requestUrl, response) {
  const area = requestUrl.searchParams.get("area") || "gangnam";
  const lang = requestUrl.searchParams.get("lang") || "JPN";
  const codes = areaCodes[area] || areaCodes.gangnam;
  const apiUrl = new URL(`${medicalApiBase}/areaBasedList`);

  apiUrl.searchParams.set("serviceKey", medicalApiKey);
  apiUrl.searchParams.set("MobileOS", "ETC");
  apiUrl.searchParams.set("MobileApp", "afterglow");
  apiUrl.searchParams.set("_type", "json");
  apiUrl.searchParams.set("numOfRows", "10");
  apiUrl.searchParams.set("pageNo", "1");
  apiUrl.searchParams.set("langDivCd", lang);
  apiUrl.searchParams.set("lDongRegnCd", codes.lDongRegnCd);
  apiUrl.searchParams.set("lDongSignguCd", codes.lDongSignguCd);

  try {
    const apiResponse = await fetch(apiUrl);
    const text = await apiResponse.text();
    if (!apiResponse.ok) {
      sendJson(response, 502, {
        ok: false,
        status: apiResponse.status,
        message: "Medical tourism API request failed.",
        upstream: text.slice(0, 500),
      });
      return;
    }

    const payload = JSON.parse(text);
    const items = normalizeItems(payload);
    sendJson(response, 200, {
      ok: true,
      source: "KTO MdclTursmService areaBasedList",
      items,
    });
  } catch (error) {
    sendJson(response, 502, {
      ok: false,
      message: "Medical tourism API request failed.",
      error: error.message,
    });
  }
}

function normalizeItems(payload) {
  const rawItems = payload?.response?.body?.items?.item || [];
  const items = Array.isArray(rawItems) ? rawItems : [rawItems];
  return items.map((item) => ({
    title: item.title || "의료관광 시설",
    address: [item.baseAddr, item.detailAddr].filter(Boolean).join(" "),
    baseAddr: item.baseAddr || "",
    detailAddr: item.detailAddr || "",
    zipCode: item.zipCd || "",
    phone: item.tel || "",
    mapX: Number(item.mapX || 0),
    mapY: Number(item.mapY || 0),
    mapLevel: item.mlevel || "",
    contentId: item.contentId || "",
    orgImage: item.orgImage || "",
    thumbImage: item.thumbImage || "",
    langDivCd: item.langDivCd || "",
    lDongRegnCd: item.lDongRegnCd || "",
    lDongSignguCd: item.lDongSignguCd || "",
    registeredAt: item.regDt || "",
    modifiedAt: item.mdfcnDt || "",
  }));
}

function sendJson(response, statusCode, body) {
  response.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}
