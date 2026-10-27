"""Nominatim geocoding with polite User-Agent and light caching."""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Any

import httpx

from .fixtures import geocode_fixture

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "WeatherAwareTruckRouting/1.0 (educational assessment; contact: github.com/sreecharan-desu/weather-aware-truck-routing)"

# Nominatim usage policy: max ~1 req/sec
_LAST_REQUEST_AT = 0.0
_MIN_INTERVAL = 1.05


def _demo_mode() -> bool:
    return os.environ.get("USE_DEMO_FIXTURES", "").lower() in ("1", "true", "yes")


def _throttle() -> None:
    global _LAST_REQUEST_AT
    elapsed = time.monotonic() - _LAST_REQUEST_AT
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_REQUEST_AT = time.monotonic()


@lru_cache(maxsize=256)
def geocode(query: str) -> dict[str, Any]:
    """Resolve a free-text place name to lat/lon.

    Raises ValueError if no results.
    """
    q = query.strip()
    if not q:
        raise ValueError("Empty geocoding query")

    if _demo_mode():
        hit = geocode_fixture(q)
        if hit:
            return hit
        raise ValueError(f"Demo fixtures only cover Dallas/Denver; could not geocode: {query}")

    _throttle()
    params = {
        "q": q,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nominatim failed (%s); trying demo fixture fallback", exc)
        hit = geocode_fixture(q)
        if hit:
            return hit
        raise

    if not data:
        raise ValueError(f"Could not geocode: {query}")

    hit = data[0]
    return {
        "query": query,
        "display_name": hit.get("display_name", query),
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
    }


def clear_geocode_cache() -> None:
    geocode.cache_clear()
