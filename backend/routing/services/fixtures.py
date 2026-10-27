"""Offline Dallas→Denver fixtures for local demo when external APIs are unreachable.

Enabled with USE_DEMO_FIXTURES=true. Production/default uses live free APIs.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _line(a: tuple[float, float], b: tuple[float, float], n: int = 40) -> list[list[float]]:
    return [[_lerp(a[0], b[0], i / (n - 1)), _lerp(a[1], b[1], i / (n - 1))] for i in range(n)]


def _concat(*segments: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for seg in segments:
        if out and seg and out[-1] == seg[0]:
            out.extend(seg[1:])
        else:
            out.extend(seg)
    return out


def _path_miles(coords: list[list[float]]) -> float:
    from .geo import haversine_miles

    total = 0.0
    for i in range(1, len(coords)):
        total += haversine_miles(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
    return total


DALLAS = {"query": "Dallas, TX", "display_name": "Dallas, Texas, United States", "lat": 32.7767, "lon": -96.7970}
DENVER = {"query": "Denver, CO", "display_name": "Denver, Colorado, United States", "lat": 39.7392, "lon": -104.9903}


def geocode_fixture(query: str) -> dict[str, Any] | None:
    q = query.strip().lower()
    if "dallas" in q:
        return {**DALLAS, "query": query}
    if "denver" in q:
        return {**DENVER, "query": query}
    return None


def demo_routes() -> list[dict[str, Any]]:
    """Three corridor variants Dallas → Denver (I-35/I-70-ish, western, eastern)."""
    origin = (DALLAS["lat"], DALLAS["lon"])
    dest = (DENVER["lat"], DENVER["lon"])

    # Route 1: relatively direct
    r1 = _line(origin, dest, 50)

    # Route 2: western bulge (via Amarillo-ish)
    west = (35.2, -101.8)
    r2 = _concat(_line(origin, west, 30), _line(west, dest, 30))

    # Route 3: eastern/northern bulge (via OKC / Wichita-ish)
    east = (37.7, -97.3)
    r3 = _concat(_line(origin, east, 30), _line(east, dest, 30))

    routes = []
    for i, coords in enumerate([r1, r2, r3], start=1):
        miles = _path_miles(coords)
        # Assume ~55 mph average truck speed
        duration = miles / 55.0 * 3600.0
        routes.append(
            {
                "id": f"route_{i}",
                "label": f"Route {i}",
                "geometry": "",
                "coordinates": coords,
                "distance_miles": round(miles, 2),
                "duration_seconds": round(duration, 1),
                "duration_hours": round(duration / 3600.0, 2),
            }
        )
    return routes


def demo_weather_series(
    lat: float,
    lon: float,
    forecast_hours: int = 48,
) -> dict[str, Any]:
    """Synthetic hourly weather that varies by longitude (western routes windier/snowier).

    Tuned so a Dallas→Denver western bulge hits High/Severe wind under a 35k lb load,
    while the more direct / eastern options stay milder — recommendation is weather-led.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = [(now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00") for h in range(forecast_hours)]

    # lon -96 (Dallas) → 0; lon -102 (Amarillo-ish) → 1; lon -105 (Denver) → 1.5
    westness = min(max((-lon - 96.0) / 6.0, 0.0), 1.8)
    northness = min(max((lat - 32.0) / 8.0, 0.0), 1.2)

    wind = []
    rain = []
    snow = []
    for h in range(forecast_hours):
        diurnal = 0.55 + 0.45 * math.sin((h / 24.0) * math.pi * 2)
        w = 14 + westness * 22 * diurnal + northness * 4
        # Sustained High/Severe band on the western plains across most of the forecast
        if westness >= 0.7:
            w += 18 + westness * 10
        if westness >= 1.1 and 4 <= (h % 24) <= 18:
            w += 8  # push toward Severe / No-Travel with heavy loads
        # Eastern bulge: moderate rain band
        r = 0.02
        if westness < 0.35 and 10 <= h <= 30:
            r = 0.18 + 0.12 * northness
        s = 0.0
        if westness > 0.8 and northness > 0.5:
            s = 0.4 + westness * 0.5 * diurnal
        wind.append(round(w, 2))
        rain.append(round(r, 4))
        snow.append(round(s, 3))

    return {"times": times, "wind_mph": wind, "rain_in_hr": rain, "snow_in_hr": snow}
