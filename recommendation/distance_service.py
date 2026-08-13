from math import asin, cos, radians, sin, sqrt

from recommendation.config import DISTANCE_SCORE_BANDS


EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, (lat1, lon1, lat2, lon2))
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    value = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(value))


def distance_score(distance_km: float) -> float:
    for upper_bound, score in DISTANCE_SCORE_BANDS:
        if distance_km <= upper_bound:
            return score
    return 0.0
