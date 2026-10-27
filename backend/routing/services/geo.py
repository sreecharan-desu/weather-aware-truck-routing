"""Geodesic helpers and polyline sampling."""

from __future__ import annotations

import math
from typing import Sequence

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Decode Google/OSRM polyline into (lat, lon) pairs."""
    coordinates: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lon = 0
    factor = 10**precision

    while index < len(encoded):
        for coord_i in range(2):
            result = 0
            shift = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if coord_i == 0:
                lat += delta
            else:
                lon += delta
        coordinates.append((lat / factor, lon / factor))
    return coordinates


def path_length_miles(coords: Sequence[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(coords)):
        total += haversine_miles(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
    return total


def sample_along_route(
    coords: Sequence[tuple[float, float]],
    interval_miles: float,
) -> list[dict]:
    """Sample checkpoints every ``interval_miles`` along a polyline.

    Returns list of dicts with lat, lon, distance_miles, fraction (0–1).
    Always includes the start point; end is included if it falls on a sample.
    """
    if not coords:
        return []
    if len(coords) == 1:
        return [
            {
                "lat": coords[0][0],
                "lon": coords[0][1],
                "distance_miles": 0.0,
                "fraction": 0.0,
                "segment_miles": 0.0,
            }
        ]

    samples: list[dict] = []
    next_at = 0.0
    traveled = 0.0
    total = path_length_miles(coords) or 1.0

    # Always sample origin
    samples.append(
        {
            "lat": coords[0][0],
            "lon": coords[0][1],
            "distance_miles": 0.0,
            "fraction": 0.0,
            "segment_miles": interval_miles,
        }
    )
    next_at = interval_miles

    for i in range(1, len(coords)):
        a = coords[i - 1]
        b = coords[i]
        seg = haversine_miles(a[0], a[1], b[0], b[1])
        if seg == 0:
            continue
        seg_start = traveled
        while next_at <= traveled + seg + 1e-9:
            t = (next_at - seg_start) / seg
            t = min(max(t, 0.0), 1.0)
            lat = a[0] + (b[0] - a[0]) * t
            lon = a[1] + (b[1] - a[1]) * t
            samples.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "distance_miles": round(next_at, 3),
                    "fraction": round(next_at / total, 6),
                    "segment_miles": interval_miles,
                }
            )
            next_at += interval_miles
        traveled += seg

    # Fix last segment miles to remaining distance if short
    if samples:
        remaining = max(total - samples[-1]["distance_miles"], 0.0)
        if remaining < interval_miles:
            samples[-1]["segment_miles"] = round(remaining, 3) if remaining > 0 else interval_miles

    return samples


def offset_point(lat: float, lon: float, bearing_deg: float, distance_miles: float) -> tuple[float, float]:
    """Move a point by distance along a bearing (degrees)."""
    br = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    ang = distance_miles / EARTH_RADIUS_MILES
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(br)
    )
    lon2 = lon1 + math.atan2(
        math.sin(br) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    return (lat1 + lat2) / 2.0, (lon1 + lon2) / 2.0
