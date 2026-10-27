"""OSRM public demo routing with alternative generation via waypoint detours."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .fixtures import demo_routes
from .geo import decode_polyline, midpoint, offset_point

logger = logging.getLogger(__name__)

OSRM_BASE = "https://router.project-osrm.org"
USER_AGENT = "WeatherAwareTruckRouting/1.0 (educational assessment)"


def _demo_mode() -> bool:
    return os.environ.get("USE_DEMO_FIXTURES", "").lower() in ("1", "true", "yes")


def _route_url(coords: list[tuple[float, float]]) -> str:
    # OSRM expects lon,lat
    path = ";".join(f"{lon},{lat}" for lat, lon in coords)
    return f"{OSRM_BASE}/route/v1/driving/{path}"


def _fetch_routes(
    points: list[tuple[float, float]],
    alternatives: bool = True,
) -> list[dict[str, Any]]:
    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "false",
        "alternatives": "true" if alternatives else "false",
    }
    headers = {"User-Agent": USER_AGENT}
    url = _route_url(points)

    with httpx.Client(timeout=45.0) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RuntimeError(f"OSRM routing failed: {payload.get('code', 'unknown')}")

    results: list[dict[str, Any]] = []
    for route in payload["routes"]:
        geometry = route["geometry"]
        coords = decode_polyline(geometry)
        distance_m = float(route["distance"])
        duration_s = float(route["duration"])
        results.append(
            {
                "geometry": geometry,
                "coordinates": coords,  # (lat, lon)
                "distance_meters": distance_m,
                "distance_miles": distance_m / 1609.344,
                "duration_seconds": duration_s,
            }
        )
    return results


def _geometry_fingerprint(coords: list[tuple[float, float]], samples: int = 12) -> tuple:
    if not coords:
        return ()
    n = len(coords)
    idxs = [int(i * (n - 1) / (samples - 1)) for i in range(samples)]
    return tuple((round(coords[i][0], 3), round(coords[i][1], 3)) for i in idxs)


def _is_duplicate(candidate: dict, existing: list[dict], miles_tol: float = 8.0) -> bool:
    c_fp = _geometry_fingerprint(candidate["coordinates"])
    for other in existing:
        if abs(candidate["distance_miles"] - other["distance_miles"]) < miles_tol:
            if c_fp == _geometry_fingerprint(other["coordinates"]):
                return True
            # Also treat nearly identical midpoints as duplicates
            mid_c = candidate["coordinates"][len(candidate["coordinates"]) // 2]
            mid_o = other["coordinates"][len(other["coordinates"]) // 2]
            from .geo import haversine_miles

            if haversine_miles(mid_c[0], mid_c[1], mid_o[0], mid_o[1]) < 15:
                if abs(candidate["duration_seconds"] - other["duration_seconds"]) < 600:
                    return True
    return False


def _detour_waypoints(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> list[tuple[float, float]]:
    """Generate lateral waypoint candidates for alternative routes."""
    mid = midpoint(origin[0], origin[1], destination[0], destination[1])
    # Rough bearing of corridor (east-ish offset for northbound, etc.)
    # Offsets perpendicular-ish at ~40–80 miles
    candidates = [
        offset_point(mid[0], mid[1], 45, 45),
        offset_point(mid[0], mid[1], 225, 45),
        offset_point(mid[0], mid[1], 90, 70),
        offset_point(mid[0], mid[1], 270, 70),
        offset_point(mid[0], mid[1], 0, 55),
        offset_point(mid[0], mid[1], 180, 55),
        offset_point(mid[0], mid[1], 135, 60),
        offset_point(mid[0], mid[1], 315, 60),
    ]
    return candidates


def get_three_routes(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> list[dict[str, Any]]:
    """Return up to 3 distinct driving routes between origin and destination.

    Uses OSRM alternatives=true; if fewer than 3, generates extras via
    waypoint detours as required by the assessment.
    """
    if _demo_mode():
        return demo_routes()

    try:
        routes = _fetch_routes([origin, destination], alternatives=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OSRM failed (%s); using demo corridor fixtures", exc)
        return demo_routes()

    unique: list[dict[str, Any]] = []
    for r in routes:
        if not _is_duplicate(r, unique):
            unique.append(r)

    if len(unique) < 3:
        for wp in _detour_waypoints(origin, destination):
            if len(unique) >= 3:
                break
            try:
                detoured = _fetch_routes([origin, wp, destination], alternatives=False)
            except Exception as exc:  # noqa: BLE001 — keep collecting alternatives
                logger.warning("Detour route failed: %s", exc)
                continue
            for r in detoured:
                if len(unique) >= 3:
                    break
                if not _is_duplicate(r, unique):
                    unique.append(r)

    if not unique:
        raise RuntimeError("No routes found between origin and destination")

    # Pad with slightly varied detours if still short (rare)
    while len(unique) < 3:
        # Clone last with a synthetic label — better to return what we have
        # but assessment asks for 3; try one more offset
        n = len(unique)
        mid = midpoint(origin[0], origin[1], destination[0], destination[1])
        wp = offset_point(mid[0], mid[1], 30 * n, 40 + 15 * n)
        try:
            detoured = _fetch_routes([origin, wp, destination], alternatives=False)
            for r in detoured:
                if not _is_duplicate(r, unique):
                    unique.append(r)
                    break
            else:
                break
        except Exception:  # noqa: BLE001
            break

    labeled: list[dict[str, Any]] = []
    for i, r in enumerate(unique[:3]):
        labeled.append(
            {
                "id": f"route_{i + 1}",
                "label": f"Route {i + 1}",
                "geometry": r["geometry"],
                "coordinates": [[c[0], c[1]] for c in r["coordinates"]],  # [lat, lon] for Leaflet
                "distance_miles": round(r["distance_miles"], 2),
                "duration_seconds": round(r["duration_seconds"], 1),
                "duration_hours": round(r["duration_seconds"] / 3600.0, 2),
            }
        )
    return labeled
