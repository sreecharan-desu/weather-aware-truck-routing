"""Open-Meteo hourly weather with batching and in-memory cache."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Sequence

import httpx

from .fixtures import demo_weather_series

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "WeatherAwareTruckRouting/1.0 (educational assessment)"

# Cache entries: key -> (expires_at, payload)
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes
_MAX_COORDS_PER_REQUEST = 40


def _demo_mode() -> bool:
    return os.environ.get("USE_DEMO_FIXTURES", "").lower() in ("1", "true", "yes")


def _cache_get(key: str) -> Any | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time.monotonic() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.monotonic() + _CACHE_TTL_SECONDS, value)


def clear_weather_cache() -> None:
    _CACHE.clear()


def _ms_to_mph(ms: float) -> float:
    return ms * 2.23693629


def _mm_to_inches(mm: float) -> float:
    return mm / 25.4


def _round_coord(lat: float, lon: float, decimals: int = 2) -> tuple[float, float]:
    return (round(lat, decimals), round(lon, decimals))


def _chunk(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def fetch_hourly_weather(
    coordinates: Sequence[tuple[float, float]],
    forecast_hours: int = 48,
) -> dict[tuple[float, float], dict[str, Any]]:
    """Fetch hourly wind/precip/snowfall for many coordinates.

    Returns map of rounded (lat, lon) -> {
        "times": [iso...],
        "wind_mph": [...],
        "rain_in_hr": [...],
        "snow_in_hr": [...],
    }
    """
    if not coordinates:
        return {}

    rounded = [_round_coord(lat, lon) for lat, lon in coordinates]
    # Deduplicate while preserving order
    unique: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for c in rounded:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    cache_key = hashlib.sha256(
        f"{unique}|{forecast_hours}|demo={_demo_mode()}".encode()
    ).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if _demo_mode():
        result = {c: demo_weather_series(c[0], c[1], forecast_hours) for c in unique}
        _cache_set(cache_key, result)
        return result

    result: dict[tuple[float, float], dict[str, Any]] = {}
    headers = {"User-Agent": USER_AGENT}

    try:
        for batch in _chunk(unique, _MAX_COORDS_PER_REQUEST):
            lats = ",".join(str(c[0]) for c in batch)
            lons = ",".join(str(c[1]) for c in batch)
            params = {
                "latitude": lats,
                "longitude": lons,
                "hourly": "wind_speed_10m,precipitation,snowfall",
                "wind_speed_unit": "ms",
                "forecast_hours": str(min(max(forecast_hours, 1), 48)),
                "timezone": "UTC",
            }
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(OPEN_METEO_URL, params=params, headers=headers)
                resp.raise_for_status()
                payload = resp.json()

            # Open-Meteo returns a list when multiple locations, else a single object
            entries = payload if isinstance(payload, list) else [payload]
            for coord, entry in zip(batch, entries):
                hourly = entry.get("hourly") or {}
                times = hourly.get("time") or []
                wind_ms = hourly.get("wind_speed_10m") or []
                precip_mm = hourly.get("precipitation") or []
                snow_cm = hourly.get("snowfall") or []

                n = min(len(times), forecast_hours)
                wind_mph = [_ms_to_mph(float(wind_ms[i] or 0)) for i in range(n)]
                rain_in = [_mm_to_inches(float(precip_mm[i] or 0)) for i in range(n)]
                snow_in = [(float(snow_cm[i] or 0) / 2.54) for i in range(n)]

                result[coord] = {
                    "times": times[:n],
                    "wind_mph": wind_mph,
                    "rain_in_hr": rain_in,
                    "snow_in_hr": snow_in,
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo failed (%s); using demo weather fixtures", exc)
        result = {c: demo_weather_series(c[0], c[1], forecast_hours) for c in unique}

    _cache_set(cache_key, result)
    return result


def weather_at_eta(
    series: dict[str, Any],
    eta: datetime,
) -> dict[str, float]:
    """Pick the hourly sample closest to ``eta`` (UTC-aware preferred)."""
    times: list[str] = series.get("times") or []
    if not times:
        return {"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}

    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=timezone.utc)
    else:
        eta = eta.astimezone(timezone.utc)

    best_i = 0
    best_delta = float("inf")
    for i, t in enumerate(times):
        # Open-Meteo times are "YYYY-MM-DDTHH:MM" without Z
        try:
            ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        delta = abs((ts - eta).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_i = i

    return {
        "wind_mph": float(series["wind_mph"][best_i]),
        "rain_in_hr": float(series["rain_in_hr"][best_i]),
        "snow_in_hr": float(series["snow_in_hr"][best_i]),
    }


def weather_at_hour_index(series: dict[str, Any], hour_index: int) -> dict[str, float]:
    n = len(series.get("times") or [])
    if n == 0:
        return {"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}
    i = min(max(int(hour_index), 0), n - 1)
    return {
        "wind_mph": float(series["wind_mph"][i]),
        "rain_in_hr": float(series["rain_in_hr"][i]),
        "snow_in_hr": float(series["snow_in_hr"][i]),
    }


def risk_score_from_weather(wind: float, rain: float, snow: float, load_lb: float) -> int:
    from .risk import classify_checkpoint

    return int(classify_checkpoint(wind, rain, snow, load_lb)["risk_score"])


def build_corridor_heatmap(
    coordinates: Sequence[tuple[float, float]],
    load_lb: float,
    forecast_hours: int = 48,
) -> dict[str, Any]:
    """Precompute risk scores per hour for corridor points (slider-ready)."""
    # Downsample dense polylines for heatmap performance
    coords = list(coordinates)
    if len(coords) > 80:
        step = math.ceil(len(coords) / 80)
        coords = coords[::step]

    weather = fetch_hourly_weather(coords, forecast_hours=forecast_hours)
    points: list[dict[str, Any]] = []
    hour_scores: list[list[int]] = [[] for _ in range(forecast_hours)]

    for lat, lon in coords:
        key = _round_coord(lat, lon)
        series = weather.get(key)
        if not series:
            scores = [0] * forecast_hours
        else:
            n = min(forecast_hours, len(series["times"]))
            scores = []
            for h in range(forecast_hours):
                if h < n:
                    w = weather_at_hour_index(series, h)
                    scores.append(risk_score_from_weather(w["wind_mph"], w["rain_in_hr"], w["snow_in_hr"], load_lb))
                else:
                    scores.append(scores[-1] if scores else 0)
        points.append({"lat": lat, "lon": lon})
        for h, s in enumerate(scores[:forecast_hours]):
            hour_scores[h].append(s)

    # Align times from first available series
    times: list[str] = []
    for series in weather.values():
        times = (series.get("times") or [])[:forecast_hours]
        if times:
            break

    return {
        "points": points,
        "hours": forecast_hours,
        "times": times,
        "scores_by_hour": hour_scores,  # [hour][point_index] -> risk_score 0-4
    }
