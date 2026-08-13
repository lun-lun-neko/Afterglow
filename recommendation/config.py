MAX_SEARCH_RADIUS_KM = 5.0
DEFAULT_RESULT_LIMIT = 20
MAX_RESULT_LIMIT = 100
DEFAULT_PURPOSE_SCORE = 50.0

SCORE_WEIGHTS = {
    "purpose": 0.35,
    "treatment": 0.30,
    "distance": 0.20,
    "walk": 0.15,
}
TREATMENT_SCORE = {"NORMAL": 100.0, "PENALTY": 50.0}

DISTANCE_SCORE_BANDS = (
    (0.5, 100.0), (1.0, 90.0), (2.0, 75.0),
    (3.0, 55.0), (5.0, 30.0),
)
WALK_SCORE_BY_EXCESS = {0: 100.0, 1: 75.0, 2: 40.0}
WALK_SCORE_LARGE_EXCESS = 10.0

PURPOSE_CATEGORY_SCORE = {
    "문화관광": {
        "cultural_facility": 100.0,
        "tourist_attraction": 95.0,
        "department_store": 60.0,
        "drugstore": 40.0,
    },
    "뷰티쇼핑": {
        "drugstore": 95.0,
        "department_store": 90.0,
        "cultural_facility": 45.0,
        "tourist_attraction": 35.0,
    },
    "휴식": {
        "cultural_facility": 75.0,
        "department_store": 65.0,
        "drugstore": 60.0,
        "tourist_attraction": 55.0,
    },
}

RISK_HIGH_ACTIVITY = "HIGH_ACTIVITY"
RISK_OUTDOOR_EXPOSURE = "OUTDOOR_EXPOSURE"
RISK_HEAT_EXPOSURE = "HEAT_EXPOSURE"
RISK_MASSAGE_PRESSURE = "MASSAGE_PRESSURE"

# (first day, last day, status), with inclusive day bounds.
TREATMENT_RISK_RULES = {
    "리프팅": {
        RISK_HIGH_ACTIVITY: ((0, 2, "PENALTY"),),
        RISK_OUTDOOR_EXPOSURE: ((0, 7, "PENALTY"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 7, "PENALTY"),),
    },
    "보톡스": {
        RISK_HIGH_ACTIVITY: ((0, 0, "BLOCK"), (1, 7, "PENALTY")),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 7, "BLOCK"),),
    },
    "필러": {
        RISK_HIGH_ACTIVITY: ((0, 1, "BLOCK"),),
        RISK_OUTDOOR_EXPOSURE: ((0, 3, "PENALTY"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 3, "BLOCK"),),
    },
    "스킨부스터": {
        RISK_HIGH_ACTIVITY: ((0, 7, "BLOCK"),),
        RISK_OUTDOOR_EXPOSURE: ((0, 7, "PENALTY"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 2, "BLOCK"),),
    },
    "윤곽/체형주사": {
        RISK_HIGH_ACTIVITY: ((0, 7, "BLOCK"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 7, "BLOCK"),),
    },
    "필링": {
        RISK_HIGH_ACTIVITY: ((0, 7, "BLOCK"),),
        RISK_OUTDOOR_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 7, "PENALTY"),),
    },
    "피부레이저": {
        RISK_HIGH_ACTIVITY: ((0, 3, "PENALTY"),),
        RISK_OUTDOOR_EXPOSURE: ((0, 3, "BLOCK"), (4, 7, "PENALTY")),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 3, "PENALTY"),),
    },
    "피부관리": {
        RISK_OUTDOOR_EXPOSURE: ((0, 7, "PENALTY"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
        RISK_MASSAGE_PRESSURE: ((0, 2, "PENALTY"),),
    },
    "제모": {
        RISK_OUTDOOR_EXPOSURE: ((0, 7, "PENALTY"),),
        RISK_HEAT_EXPOSURE: ((0, 7, "BLOCK"),),
    },
    "비만(약처방)": {},
}

HEAT_CATEGORY_KEYWORDS = ("사우나", "찜질방", "온천")
MASSAGE_CATEGORY_KEYWORDS = ("마사지", "경락", "안마", "스파")

VALID_TREATMENTS = set(TREATMENT_RISK_RULES)
VALID_PURPOSES = set(PURPOSE_CATEGORY_SCORE)

# Course MVP policy.
COURSE_PLACE_COUNT = 3
DEFAULT_TOP_COURSES = 3
MAX_TOP_COURSES = 10
COURSE_CANDIDATES_PER_CATEGORY = 12
MAX_SAME_CATEGORY_PER_COURSE = 2
MIN_DISTINCT_CATEGORIES = 2
MAX_LEG_DISTANCE_KM = 2.0
MAX_COURSE_DISTANCE_KM = 5.0
MAX_SHARED_PLACES_BETWEEN_TOP_COURSES = 1

COURSE_SCORE_WEIGHTS = {
    "places": 0.60,
    "route": 0.20,
    "diversity": 0.10,
    "purpose_composition": 0.10,
}
COURSE_DISTANCE_SCORE_BANDS = (
    (1.5, 100.0), (3.0, 80.0), (4.0, 60.0), (5.0, 40.0),
)
PURPOSE_REQUIRED_CATEGORIES = {
    "문화관광": {"cultural_facility", "tourist_attraction"},
    "뷰티쇼핑": {"drugstore", "department_store"},
}
REST_MIN_INDOOR_PLACES = 2

ANCHOR_DATA_FILE = "gangnam_seocho_skin_hospitals_accommodations.csv"
CANDIDATE_DATA_FILES = (
    "gangnam_seocho_places_drugstore_attraction_department_culture.csv",
)
