
const DAY_MS = 24 * 60 * 60 * 1000;

const hospitals = {
  gangnam: {
    name: "강남 Glow Dermatology",
    address: "서울특별시 강남구 테헤란로 152",
    phone: "+82-2-555-0199",
    languages: "일본어, 영어 상담 가능",
    description: "피부관리, 레이저, 필링 상담을 제공하는 강남권 의료관광 샘플 시설입니다.",
  },
  seomyeon: {
    name: "Seomyeon Beauty Clinic",
    address: "부산광역시 부산진구 중앙대로 730",
    phone: "+82-51-555-0188",
    languages: "일본어 안내 가능",
    description: "서면 뷰티 쇼핑 동선과 연결하기 좋은 의료관광 샘플 시설입니다.",
  },
};

let externalHospitals = {};
let externalFacilities = {};
let selectedHospitalIds = {};

const places = {
  gangnam: [
    { name: "병원 인근 카페", type: "cafe", indoor: true, outdoor: false, distance: 0.2, tags: ["rest"], time: "12:00", x: 292, y: 204 },
    { name: "코엑스 실내몰", type: "shopping", indoor: true, outdoor: false, distance: 1.6, tags: ["beauty", "shopping"], time: "14:00", x: 414, y: 222 },
    { name: "현대백화점 뷰티관", type: "shopping", indoor: true, outdoor: false, distance: 1.9, tags: ["beauty", "shopping"], time: "16:00", x: 530, y: 158 },
    { name: "선릉 산책로", type: "park", indoor: false, outdoor: true, distance: 1.1, tags: ["walk"], time: "15:00", x: 502, y: 292 },
    { name: "강남 전시 라운지", type: "culture", indoor: true, outdoor: false, distance: 1.3, tags: ["culture"], time: "15:30", x: 360, y: 118 },
  ],
  seomyeon: [
    { name: "서면 휴식 카페", type: "cafe", indoor: true, outdoor: false, distance: 0.3, tags: ["rest"], time: "12:00", x: 292, y: 204 },
    { name: "서면 지하상가", type: "shopping", indoor: true, outdoor: false, distance: 0.8, tags: ["beauty", "shopping"], time: "14:00", x: 414, y: 222 },
    { name: "롯데백화점 부산본점", type: "shopping", indoor: true, outdoor: false, distance: 1.0, tags: ["beauty", "shopping"], time: "16:00", x: 530, y: 158 },
    { name: "전포 카페거리", type: "cafe", indoor: false, outdoor: true, distance: 1.4, tags: ["walk"], time: "15:00", x: 502, y: 292 },
  ],
};

const sampleForecasts = {
  gangnam: [
    { condition: "clear", uvIndex: 7, dustLevel: "normal", temperature: 24 },
    { condition: "rain", uvIndex: 2, dustLevel: "good", temperature: 20 },
    { condition: "clear", uvIndex: 8, dustLevel: "bad", temperature: 27 },
    { condition: "clear", uvIndex: 5, dustLevel: "normal", temperature: 23 },
  ],
  seomyeon: [
    { condition: "clear", uvIndex: 6, dustLevel: "normal", temperature: 23 },
    { condition: "rain", uvIndex: 2, dustLevel: "good", temperature: 19 },
    { condition: "clear", uvIndex: 7, dustLevel: "bad", temperature: 25 },
    { condition: "clear", uvIndex: 4, dustLevel: "normal", temperature: 22 },
  ],
};

const procedureRules = {
  botox: {
    label: "보톡스",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "마사지", "과격한 운동"],
    care: [
      "시술 후 붉은기, 부기, 멍이 들 수 있으나 보통 1-2주 후 완화됩니다.",
      "주름 시술 후 일시적으로 표정이 어색하거나 무거운 느낌이 있을 수 있습니다.",
      "시술 당일 가벼운 세안과 화장은 가능하지만 스킨보톡스는 당일 화장을 자제하는 편이 좋습니다.",
      "종아리 보톡스 후에는 하이힐을 피하는 것이 좋습니다.",
      "승모근 보톡스 후에는 무거운 짐을 들지 않는 것이 좋습니다.",
      "7일간 음주, 흡연, 사우나, 마사지, 과격한 운동은 피해주세요.",
    ],
  },
  filler: {
    label: "필러",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "마사지", "과격한 운동", "시술 부위 압박"],
    care: [
      "시술 후 붉은기, 부기, 멍이 들 수 있으나 보통 1-2주 후 완화됩니다.",
      "시술 부위가 일시적으로 울퉁불퉁해 보일 수 있으나 1-2주 내로 자연스러워집니다.",
      "시술 부위를 힘주어 누르거나 압력을 가하지 않는 것이 좋습니다.",
      "2-3시간 동안 세안과 화장을 피해주세요.",
      "코필러 후 약 7일 동안 선글라스와 안경 착용을 피해주세요.",
      "7일간 음주, 흡연, 사우나, 마사지, 과격한 운동은 피해주세요.",
    ],
  },
  skinBooster: {
    label: "스킨부스터",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "과격한 운동", "직사광선", "시술 부위 접촉"],
    care: [
      "시술 후 붉은기, 부기, 멍이 들 수 있으나 보통 1-2주 후 완화됩니다.",
      "시술 부위를 힘주어 누르거나 만지는 것은 피해주세요.",
      "세안이나 메이크업은 시술 다음날부터 가능합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "3-7일간 음주, 흡연, 사우나, 과격한 운동은 피해주세요.",
    ],
  },
  contourInjection: {
    label: "윤곽/체형주사",
    restLevel: "moderate",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "마사지", "과격한 운동", "장시간 이동"],
    care: [
      "피부 상태에 따라 열감, 부기, 멍 등이 나타날 수 있으나 1-3주 후 완화됩니다.",
      "일시적인 떨림, 두근거림, 어지러움이 생길 수 있으나 수일 내 완화됩니다.",
      "시술 후 생리의 양 및 주기 변화가 생길 수 있으나 자연스럽게 사라집니다.",
      "샤워는 윤곽주사 4시간 후, 체형주사는 다음날부터 권장합니다.",
      "윤곽주사 후 얼음찜질은 부기 완화에 도움이 될 수 있습니다.",
      "시술 후 수분섭취를 충분히 하는 것이 좋습니다.",
      "7일간 음주, 흡연, 사우나, 마사지, 과격한 운동은 피해주세요.",
    ],
  },
  peeling: {
    label: "필링",
    restLevel: "moderate",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "과격한 운동", "직사광선", "각질 제거"],
    care: [
      "시술 후 당김, 가려움, 따가움 등이 생길 수 있으나 약 7일 후 완화됩니다.",
      "딱지나 각질이 생기면 손대지 말고 자연 탈각되도록 해주세요.",
      "당일 세안은 가능하지만 최대한 자극 없이 가볍게 해주세요.",
      "각질제거 및 스크럽제 사용을 피해주세요.",
      "보습관리를 위해 수분섭취 및 재생크림 사용을 권장합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 과격한 운동은 피해주세요.",
    ],
  },
  laser: {
    label: "피부레이저",
    restLevel: "moderate",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "직사광선", "기능성 화장품"],
    care: [
      "시술 후 따끔거림, 붉은기, 부기, 가려움증이 나타날 수 있으나 1-2주 후 완화됩니다.",
      "딱지나 각질이 생기면 손대지 말고 자연 탈각되도록 해주세요.",
      "세안은 시술 다음날부터 가능합니다.",
      "화이트닝, 주름개선 등 기능성 화장품 사용은 자제해주세요.",
      "보습관리를 위해 수분섭취 및 재생크림 사용을 권장합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "3-7일간 음주, 흡연, 사우나, 찜질방은 피해주세요.",
    ],
  },
  liftingUltrasound: {
    label: "초음파리프팅",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "직사광선", "강한 피부 자극"],
    care: [
      "시술 후 붉은기, 열감, 욱신거림, 부기가 나타날 수 있으나 1-2주 후 완화됩니다.",
      "민감해진 피부에 강한 자극이나 필링은 삼가주세요.",
      "세안 및 화장 등 일상생활 복귀는 바로 가능합니다.",
      "2-3일간 미온수 세안을 하는 것이 좋습니다.",
      "보습관리를 위해 수분섭취 및 재생크림 사용을 권장합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 찜질방은 피해주세요.",
    ],
  },
  liftingRf: {
    label: "고주파리프팅",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "직사광선", "강한 피부 자극"],
    care: [
      "시술 후 붉은기, 열감, 통증, 부기가 나타날 수 있으나 1-2주 후 완화됩니다.",
      "민감해진 피부에 강한 자극이나 필링은 삼가주세요.",
      "세안 및 화장 등 일상생활 복귀는 바로 가능합니다.",
      "2-3일간 미온수 세안을 하는 것이 좋습니다.",
      "보습관리를 위해 수분섭취 및 재생크림 사용을 권장합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 찜질방은 피해주세요.",
    ],
  },
  threadLifting: {
    label: "실리프팅",
    restLevel: "moderate",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "마사지", "시술 부위 압박", "질긴 음식"],
    care: [
      "시술 후 일시적으로 멍, 부기, 뻐근함 등이 생길 수 있으나 약 4주 이내 완화됩니다.",
      "질기거나 단단한 음식은 피하고 입을 크게 벌리지 않도록 주의가 필요합니다.",
      "시술 부위를 강하게 문지르거나 누르는 것은 피해주세요.",
      "세안과 화장은 시술 다음날부터 가볍게 가능합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 찜질방, 마사지는 피해주세요.",
    ],
  },
  skinCare: {
    label: "피부관리",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "직사광선", "자극적인 세안"],
    care: [
      "시술에 따라 붉은기, 부기, 멍 등이 발생할 수 있으나 약 1주 후 완화됩니다.",
      "각질이 생기면 손대지 말고 자연 탈각되도록 해주세요.",
      "시술 당일 세안 및 화장이 가능하나 자극적인 세안은 삼가주세요.",
      "보습관리를 위해 수분섭취 및 재생크림 사용을 권장합니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 찜질방은 피해주세요.",
    ],
  },
  hairRemoval: {
    label: "제모",
    restLevel: "light",
    avoidDays: 7,
    avoid: ["음주", "흡연", "사우나", "찜질방", "직사광선", "왁싱", "선탠", "태닝"],
    care: [
      "시술 후 붉은기, 색소침착 등이 생길 수 있으나 약 1-2주 후 완화됩니다.",
      "남은 털은 시술 후 1-2일에 걸쳐 서서히 빠질 수 있습니다.",
      "시술 기간 동안 왁싱, 선탠, 태닝, 털을 뽑는 행위는 피해주세요.",
      "시술 직후 샤워, 세안, 화장이 가능합니다.",
      "시술 부위가 건조해지지 않도록 보습제를 발라주는 것이 좋습니다.",
      "시술 후 직사광선은 피하고 자외선 차단제를 꼭 사용해주세요.",
      "7일간 음주, 흡연, 사우나, 찜질방은 피해주세요.",
    ],
  },
  dietMedication: {
    label: "비만 약처방",
    restLevel: "moderate",
    avoidDays: 3,
    avoid: ["음주", "무리한 일정", "수분 부족", "늦은 시간 복용"],
    care: [
      "약으로 인해 가슴 두근거림, 손발 저림 등의 증상이 나타날 수 있으나 수일 내 완화됩니다.",
      "취침시간으로부터 약 8시간 이전에 복용하는 것을 권장합니다.",
      "입 마름, 변비 등이 생길 수 있으니 수분섭취를 충분히 해주세요.",
      "임신과 수유 계획이 있을 때는 약물 복용을 피해주세요.",
      "상담을 통해 처방전이 발급되며 처방 기간은 상담 후 결정됩니다.",
    ],
  },
};

const form = document.querySelector("#plannerForm");
const distanceInput = document.querySelector("#maxDistance");
const distanceValue = document.querySelector("#distanceValue");
const tripStartInput = document.querySelector("#tripStart");
const tripEndInput = document.querySelector("#tripEnd");
const procedureDateInput = document.querySelector("#procedureDate");
const dateHint = document.querySelector("#dateHint");
const dayTabs = document.querySelector("#dayTabs");
const hospitalSelect = document.querySelector("#hospitalSelect");
const facilityHint = document.querySelector("#facilityHint");
const bottomNavButtons = document.querySelectorAll(".bottom-nav button");

let currentItinerary = [];
let selectedDayIndex = 0;

setDefaultDates();
renderHospitalOptions(document.querySelector("#area").value);

distanceInput.addEventListener("input", () => {
  distanceValue.textContent = Number(distanceInput.value).toFixed(1);
  renderRecommendation(getOptions());
});

[tripStartInput, tripEndInput, procedureDateInput].forEach((input) => {
  input.addEventListener("change", () => {
    normalizeDates();
    selectedDayIndex = 0;
    renderRecommendation(getOptions());
  });
});

hospitalSelect.addEventListener("change", () => {
  selectedHospitalIds[getOptions().area] = hospitalSelect.value;
  selectedDayIndex = 0;
  renderRecommendation(getOptions());
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  renderRecommendation(getOptions());
  switchView("trips");
});

document.querySelector("#area").addEventListener("change", async () => {
  selectedDayIndex = 0;
  renderRecommendation(getOptions());
  await loadMedicalFacilities(getOptions().area);
});

document.querySelector("#shareButton").addEventListener("click", async () => {
  const title = document.querySelector("#resultTitle").textContent;
  const text = `${title} - ${document.querySelector("#hospitalName").textContent}`;
  if (navigator.share) {
    await navigator.share({ title: "Afterglow", text });
    return;
  }
  await navigator.clipboard.writeText(text);
  document.querySelector("#shareButton").textContent = "복사됨";
  setTimeout(() => {
    document.querySelector("#shareButton").textContent = "공유";
  }, 1400);
});

bottomNavButtons.forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
  });
});

function setDefaultDates() {
  const today = new Date();
  const start = toDateInputValue(today);
  const procedure = toDateInputValue(addDays(today, 1));
  const end = toDateInputValue(addDays(today, 4));

  tripStartInput.value = start;
  procedureDateInput.value = procedure;
  tripEndInput.value = end;
}

function normalizeDates() {
  if (!tripStartInput.value) tripStartInput.value = toDateInputValue(new Date());
  if (!tripEndInput.value || dateDiff(tripStartInput.value, tripEndInput.value) < 0) {
    tripEndInput.value = tripStartInput.value;
  }

  if (!procedureDateInput.value) procedureDateInput.value = tripStartInput.value;
  if (dateDiff(tripStartInput.value, procedureDateInput.value) < 0) {
    procedureDateInput.value = tripStartInput.value;
  }
  if (dateDiff(procedureDateInput.value, tripEndInput.value) < 0) {
    procedureDateInput.value = tripEndInput.value;
  }
}

function getOptions() {
  return {
    area: document.querySelector("#area").value,
    purpose: document.querySelector("#purpose").value,
    procedureType: document.querySelector("#procedureType").value,
    tripStart: tripStartInput.value,
    tripEnd: tripEndInput.value,
    procedureDate: procedureDateInput.value,
    procedureDayIndex: dateDiff(tripStartInput.value, procedureDateInput.value) + 1,
    maxDistance: Number(distanceInput.value),
  };
}

function renderRecommendation(options) {
  const hospital = getHospital(options.area);
  currentItinerary = buildItinerary(options, hospital);
  selectedDayIndex = Math.min(selectedDayIndex, currentItinerary.length - 1);
  const selectedDay = currentItinerary[selectedDayIndex];

  document.querySelector("#resultTitle").textContent = `${areaLabel(options.area)} 전체 여행 코스`;
  document.querySelector("#hospitalName").textContent = hospital.name;
  document.querySelector("#tripSummary").textContent = `${formatDate(options.tripStart)}-${formatDate(options.tripEnd)} / 시술 ${options.procedureDayIndex}일차`;
  document.querySelector("#itinerarySummary").textContent = `${currentItinerary.length}일 코스`;
  document.querySelector("#selectedDaySummary").textContent = `Day ${selectedDay.dayIndex} · ${recoveryLabel(selectedDay.recoveryDay)}`;
  document.querySelector("#selectedDaySummaryTrip").textContent = `Day ${selectedDay.dayIndex} · ${recoveryLabel(selectedDay.recoveryDay)}`;
  document.querySelector("#safetyScore").textContent = `${safetyScore(selectedDay.options, selectedDay.places)}점`;
  document.querySelector("#routeMeta").textContent = routeMeta(selectedDay.options, selectedDay.places);
  dateHint.textContent = `${tripLength(options)}일 여행 전체를 생성했습니다. Day 탭을 선택하면 날짜별 동선과 회복 단계를 볼 수 있습니다.`;

  renderDayTabs(currentItinerary);
  renderTimeline(selectedDay.route, selectedDay.options);
  renderPins(selectedDay.route);
  renderReasons(selectedDay.options, selectedDay.places);
  renderMedicalFacilityInfo(options.area, hospital);
  renderCareGuide(selectedDay.options);
}

function switchView(viewName) {
  document.querySelectorAll(".app-view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${viewName}`);
  });
  bottomNavButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
}

function buildItinerary(baseOptions, hospital) {
  const totalDays = tripLength(baseOptions);
  return Array.from({ length: totalDays }, (_, index) => {
    const targetDate = toDateInputValue(addDays(parseDate(baseOptions.tripStart), index));
    const dayOptions = {
      ...baseOptions,
      targetDate,
      targetDayIndex: index + 1,
      recoveryDay: dateDiff(baseOptions.procedureDate, targetDate),
      forecast: getForecast(baseOptions.area, targetDate),
    };
    const scoredPlaces = places[baseOptions.area]
      .filter((place) => isAllowed(place, dayOptions))
      .map((place) => ({ ...place, score: scorePlace(place, dayOptions) }))
      .filter((place) => place.distance <= baseOptions.maxDistance)
      .sort((a, b) => b.score - a.score || a.distance - b.distance)
      .slice(0, 3)
      .sort((a, b) => a.distance - b.distance);
    return {
      dayIndex: index + 1,
      date: targetDate,
      recoveryDay: dayOptions.recoveryDay,
      options: dayOptions,
      places: scoredPlaces,
      route: [
        { name: hospital.name, type: "clinic", distance: 0, time: index + 1 === baseOptions.procedureDayIndex ? "10:00" : "11:00", x: 158, y: 246 },
        ...scoredPlaces,
      ],
    };
  });
}

function renderDayTabs(itinerary) {
  dayTabs.innerHTML = "";
  itinerary.forEach((day, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `day-tab${index === selectedDayIndex ? " active" : ""}`;
    button.innerHTML = `<strong>Day ${day.dayIndex}</strong><span>${formatDate(day.date)} · ${recoveryLabel(day.recoveryDay)}</span>`;
    button.addEventListener("click", () => {
      selectedDayIndex = index;
      renderRecommendation(getOptions());
    });
    dayTabs.appendChild(button);
  });
}

async function loadMedicalFacilities(area) {
  try {
    facilityHint.textContent = "의료관광정보 API에서 시설을 조회하는 중입니다.";
    const response = await fetch(`/api/medical?area=${encodeURIComponent(area)}&lang=JPN`);
    const payload = await response.json();
    if (!payload.ok || !payload.items.length) return;

    const first = payload.items[0];
    externalFacilities[area] = payload.items;
    selectedHospitalIds[area] = selectedHospitalIds[area] || first.contentId || first.title;
    renderHospitalOptions(area);
    facilityHint.textContent = `${payload.items.length}개 시설을 조회했습니다. 시술 예정 병원을 선택해주세요.`;
    renderRecommendation(getOptions());
  } catch (error) {
    renderHospitalOptions(area);
    facilityHint.textContent = "API 조회에 실패해 샘플 병원으로 진행합니다.";
    console.warn("Medical tourism API fallback:", error);
  }
}

function getHospital(area) {
  const facilities = externalFacilities[area] || [];
  const selectedId = selectedHospitalIds[area];
  const selectedFacility = facilities.find((facility) => facilityKey(facility) === selectedId);
  if (selectedFacility) return facilityToHospital(selectedFacility);
  return externalHospitals[area] || hospitals[area];
}

function renderHospitalOptions(area) {
  const facilities = externalFacilities[area] || [];
  hospitalSelect.innerHTML = "";

  if (!facilities.length) {
    const fallback = hospitals[area];
    hospitalSelect.appendChild(new Option(fallback.name, "sample"));
    selectedHospitalIds[area] = "sample";
    return;
  }

  facilities.forEach((facility) => {
    hospitalSelect.appendChild(new Option(facility.title, facilityKey(facility)));
  });
  hospitalSelect.value = selectedHospitalIds[area] || facilityKey(facilities[0]);
}

function facilityToHospital(facility) {
  return {
    name: facility.title,
    address: facility.address || "주소 정보 없음",
    phone: facility.phone || "전화번호 정보 없음",
    languages: `공공데이터 의료관광정보 API · ${facility.langDivCd || "JPN"}`,
    description: `contentId ${facility.contentId || "-"} · 좌표 ${formatCoordinate(facility.mapY)}, ${formatCoordinate(facility.mapX)}`,
    facility,
  };
}

function facilityKey(facility) {
  return facility.contentId || facility.title;
}

function isAllowed(place, options) {
  const rule = getProcedureRule(options.procedureType);
  const afterProcedure = options.recoveryDay >= 0;
  const needsStrictRecovery = afterProcedure && (options.recoveryDay <= 1 || isInAvoidWindow(options, rule));
  if (needsStrictRecovery && place.outdoor && (isUvHigh(options.forecast) || options.forecast.condition !== "clear")) {
    return false;
  }
  if (isDustBad(options.forecast) && place.outdoor) {
    return false;
  }
  return true;
}

function scorePlace(place, options) {
  let score = 100 - place.distance * 12;
  const rule = getProcedureRule(options.procedureType);
  if (place.indoor) score += 18;
  if (options.purpose === "shopping" && place.tags.includes("shopping")) score += 28;
  if (options.purpose === "medical" && place.tags.includes("rest")) score += 18;
  if (options.purpose === "lightTour" && place.tags.includes("culture")) score += 18;
  if (rule.restLevel === "light" && place.tags.includes("rest")) score += 26;
  if (rule.restLevel === "moderate" && place.tags.includes("rest")) score += 34;
  if (options.forecast.condition === "rain" && place.indoor) score += 24;
  if (isDustBad(options.forecast) && place.indoor) score += 20;
  if (isUvHigh(options.forecast) && place.indoor) score += 18;
  if (place.outdoor) score -= options.recoveryDay >= 0 && options.recoveryDay <= 3 ? 35 : 8;
  if (isInAvoidWindow(options, rule) && place.distance > 1.5) score -= rule.restLevel === "moderate" ? 28 : 18;
  return score;
}

function renderTimeline(route, options) {
  const timeline = document.querySelector("#timeline");
  timeline.innerHTML = "";
  route.forEach((item, index) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="time">${item.time}</span>
      <div>
        <p class="place-name">${item.name}</p>
        <p class="place-meta">${timelineText(item, index, options)}</p>
      </div>
    `;
    timeline.appendChild(li);
  });
}

function renderPins(route) {
  const pinLayer = document.querySelector("#mapPins");
  const routeLine = document.querySelector("#routeLine");
  pinLayer.innerHTML = "";
  routeLine.setAttribute("d", route.map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`).join(" "));

  route.forEach((point, index) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.innerHTML = `
      <circle cx="${point.x}" cy="${point.y}" r="15" fill="${index === 0 ? "#1d7f86" : "#d66f5d"}"></circle>
      <text x="${point.x}" y="${point.y + 5}" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">${index + 1}</text>
      <text class="pin-label" x="${point.x + 20}" y="${point.y - 18}">${shortName(point.name)}</text>
    `;
    pinLayer.appendChild(group);
  });
}

function renderReasons(options, selected) {
  const reasons = [
    `총 여행 ${tripLength(options)}일 중 ${options.procedureDayIndex}일차에 시술하고, 현재 Day ${options.targetDayIndex} 일정을 보고 있습니다.`,
    `${procedureLabel(options.procedureType)}와 ${recoveryLabel(options.recoveryDay)} 조건을 우선 반영했습니다.`,
    procedureReason(options),
    `추천 날짜의 자동 기상 데이터는 ${forecastSummary(options.forecast)}입니다.`,
    weatherReason(options),
    `최대 이동거리 ${options.maxDistance.toFixed(1)}km 안에서 ${selected.length}개 장소를 선택했습니다.`,
  ];
  const list = document.querySelector("#reasonList");
  list.innerHTML = "";
  reasons.forEach((reason) => {
    const li = document.createElement("li");
    li.textContent = reason;
    list.appendChild(li);
  });
}

function renderCareGuide(options) {
  const rule = getProcedureRule(options.procedureType);
  document.querySelector("#careMeta").textContent = `${rule.label} · 회피 ${rule.avoidDays}일`;
  const careList = document.querySelector("#careList");
  careList.innerHTML = "";
  rule.care.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    careList.appendChild(li);
  });
}

function renderMedicalFacilityInfo(area, hospital) {
  const facilities = externalFacilities[area];
  if (!facilities?.length) {
    document.querySelector("#hospitalDetails").innerHTML = `
      <div class="detail-row"><strong>주소</strong>${hospital.address}</div>
      <div class="detail-row"><strong>전화</strong>${hospital.phone}</div>
      <div class="detail-row"><strong>다국어</strong>${hospital.languages}</div>
      <div class="detail-row"><strong>소개</strong>${hospital.description}</div>
    `;
    return;
  }

  const selectedKey = hospital.facility ? facilityKey(hospital.facility) : selectedHospitalIds[area];
  const orderedFacilities = [
    ...facilities.filter((facility) => facilityKey(facility) === selectedKey),
    ...facilities.filter((facility) => facilityKey(facility) !== selectedKey),
  ];

  document.querySelector("#hospitalDetails").innerHTML = orderedFacilities.slice(0, 3).map((facility, index) => `
    <article class="facility-row">
      <div class="facility-title">
        <span>${index + 1}</span>
        <strong>${facility.title}${facilityKey(facility) === selectedKey ? " · 선택됨" : ""}</strong>
      </div>
      <dl>
        <div><dt>주소</dt><dd>${facility.address || "주소 정보 없음"}</dd></div>
        <div><dt>우편번호</dt><dd>${facility.zipCode || "-"}</dd></div>
        <div><dt>전화</dt><dd>${facility.phone || "미제공"}</dd></div>
        <div><dt>좌표</dt><dd>${formatCoordinate(facility.mapY)}, ${formatCoordinate(facility.mapX)}</dd></div>
        <div><dt>콘텐츠 ID</dt><dd>${facility.contentId || "-"}</dd></div>
        <div><dt>언어</dt><dd>${facility.langDivCd || "-"}</dd></div>
        <div><dt>수정일</dt><dd>${formatApiDate(facility.modifiedAt)}</dd></div>
      </dl>
    </article>
  `).join("");
}

function timelineText(item, index, options) {
  if (index === 0) {
    return options.targetDate === options.procedureDate
      ? "의료관광 시설 방문 및 시술/상담 일정입니다."
      : "시술 예정 병원 기준으로 동선을 계산한 출발 지점입니다.";
  }
  const indoorText = item.indoor ? "실내 중심" : "야외 활동 포함";
  return `${indoorText}, 병원 기준 약 ${item.distance.toFixed(1)}km. ${weatherShort(options)} 조건을 반영했습니다.`;
}

function areaLabel(area) {
  return area === "gangnam" ? "서울 강남" : "부산 서면";
}

function procedureLabel(procedureType) {
  return getProcedureRule(procedureType).label;
}

function recoveryLabel(day) {
  if (day < 0) return `시술 ${Math.abs(day)}일 전`;
  if (day === 0) return "시술 당일";
  if (day === 1) return "시술 1일차";
  if (day <= 3) return "시술 2-3일차";
  return "회복 이후";
}

function weatherShort(options) {
  if (options.forecast.condition === "rain") return "비";
  if (isDustBad(options.forecast)) return "미세먼지";
  if (isUvHigh(options.forecast)) return "높은 자외선";
  return "맑은 날씨";
}

function weatherReason(options) {
  if (options.forecast.condition === "rain") return "비 예보가 있어 지하철 접근성과 실내 활동을 우선했습니다.";
  if (isDustBad(options.forecast)) return "미세먼지 조건으로 야외 체류가 긴 장소를 제외했습니다.";
  if (isUvHigh(options.forecast)) return "자외선 지수가 높아 실내 쇼핑몰과 휴식 장소에 가중치를 부여했습니다.";
  return "날씨가 양호해 짧은 이동 동선을 중심으로 점수화했습니다.";
}

function routeMeta(options, selected) {
  const indoorCount = selected.filter((place) => place.indoor).length;
  if (indoorCount === selected.length) return "실내 중심, 짧은 이동";
  return "회복 단계에 맞춘 혼합 동선";
}

function safetyScore(options, selected) {
  const base = 86;
  const indoorBonus = selected.filter((place) => place.indoor).length * 3;
  const rule = getProcedureRule(options.procedureType);
  const recoveryBonus = options.recoveryDay >= 0 && options.recoveryDay <= 1 ? 4 : 1;
  const avoidBonus = isInAvoidWindow(options, rule) ? 2 : 0;
  return Math.min(98, base + indoorBonus + recoveryBonus + avoidBonus);
}

function getProcedureRule(procedureType) {
  return procedureRules[procedureType] || procedureRules.botox;
}

function isInAvoidWindow(options, rule) {
  return options.recoveryDay >= 0 && options.recoveryDay < rule.avoidDays;
}

function procedureReason(options) {
  const rule = getProcedureRule(options.procedureType);
  if (options.recoveryDay < 0) {
    return `${rule.label} 시술 전 일정이므로 무리한 제한은 적용하지 않고 병원 접근성을 중심으로 계산했습니다.`;
  }
  if (isInAvoidWindow(options, rule)) {
    return `${rule.label} 후 ${rule.avoidDays}일간 ${rule.avoid.join(", ")}을 피해야 하므로 짧은 이동과 휴식 장소에 가중치를 두었습니다.`;
  }
  return `${rule.label}의 주요 회피 기간이 지난 일정이므로 일반 관광 비중을 조금 높일 수 있습니다.`;
}

function tripLength(options) {
  return dateDiff(options.tripStart, options.tripEnd) + 1;
}

function dateDiff(startValue, endValue) {
  return Math.round((parseDate(endValue) - parseDate(startValue)) / DAY_MS);
}

function getForecast(area, dateValue) {
  const forecasts = sampleForecasts[area];
  const index = Math.abs(dateDiff("2026-01-01", dateValue)) % forecasts.length;
  return forecasts[index];
}

function isUvHigh(forecast) {
  return forecast.uvIndex >= 6;
}

function isDustBad(forecast) {
  return forecast.dustLevel === "bad";
}

function forecastSummary(forecast) {
  const conditionLabel = {
    clear: "맑음",
    rain: "비",
  }[forecast.condition] || forecast.condition;
  const dustLabel = {
    good: "좋음",
    normal: "보통",
    bad: "나쁨",
  }[forecast.dustLevel];
  return `${conditionLabel}, UV ${forecast.uvIndex}, 미세먼지 ${dustLabel}`;
}

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDate(value) {
  const date = parseDate(value);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function formatApiDate(value) {
  if (!value || value.length < 8) return "-";
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

function formatCoordinate(value) {
  return Number(value || 0).toFixed(6);
}

function shortName(name) {
  return name.replace("강남 ", "").replace("부산본점", "").slice(0, 8);
}

renderRecommendation(getOptions());
loadMedicalFacilities(getOptions().area);
