"""End-to-end route planning: geocode → route → weather → risk → recommend."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .geocoding import geocode
from .geo import sample_along_route
from .osrm import get_three_routes
from .risk import classify_checkpoint, recommend_routes, summarize_route_risk
from .weather import build_corridor_heatmap, fetch_hourly_weather, weather_at_eta


def _demo_mode() -> bool:
    return os.environ.get("USE_DEMO_FIXTURES", "").lower() in ("1", "true", "yes")


def _parse_departure(value: str) -> datetime:
    """Parse ISO datetime; assume UTC if naive."""
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def plan_trip(
    origin_query: str,
    destination_query: str,
    departure_iso: str,
    load_lb: float,
    sample_interval_miles: int = 25,
) -> dict[str, Any]:
    if sample_interval_miles not in (10, 25, 50):
        raise ValueError("sample_interval_miles must be 10, 25, or 50")
    if load_lb < 0:
        raise ValueError("load_lb must be non-negative")

    departure = _parse_departure(departure_iso)
    origin = geocode(origin_query)
    destination = geocode(destination_query)

    routes = get_three_routes(
        (origin["lat"], origin["lon"]),
        (destination["lat"], destination["lon"]),
    )

    # Collect all checkpoint coords for a single batched weather fetch
    route_samples: dict[str, list[dict]] = {}
    all_coords: list[tuple[float, float]] = []

    for route in routes:
        coords = [(c[0], c[1]) for c in route["coordinates"]]
        samples = sample_along_route(coords, float(sample_interval_miles))
        route_samples[route["id"]] = samples
        all_coords.extend((s["lat"], s["lon"]) for s in samples)

    weather_map = fetch_hourly_weather(all_coords, forecast_hours=48)

    enriched_routes: list[dict[str, Any]] = []
    summaries = []

    for route in routes:
        samples = route_samples[route["id"]]
        duration = float(route["duration_seconds"])
        checkpoints: list[dict[str, Any]] = []

        for sample in samples:
            eta = departure + timedelta(seconds=duration * float(sample["fraction"]))
            key = (round(sample["lat"], 2), round(sample["lon"], 2))
            series = weather_map.get(key) or {}
            wx = weather_at_eta(series, eta)
            classified = classify_checkpoint(
                wx["wind_mph"],
                wx["rain_in_hr"],
                wx["snow_in_hr"],
                load_lb,
            )
            checkpoints.append(
                {
                    "lat": round(sample["lat"], 5),
                    "lon": round(sample["lon"], 5),
                    "distance_miles": sample["distance_miles"],
                    "segment_miles": sample["segment_miles"],
                    "eta": eta.isoformat().replace("+00:00", "Z"),
                    **classified,
                }
            )

        summary = summarize_route_risk(
            route["id"],
            checkpoints,
            duration,
            float(sample_interval_miles),
        )
        summaries.append(summary)

        # Risk color counts for UI summary
        counts = {"Low": 0, "Moderate": 0, "High": 0, "Severe": 0, "No Travel": 0}
        for cp in checkpoints:
            counts[cp["risk"]] = counts.get(cp["risk"], 0) + 1

        enriched_routes.append(
            {
                **route,
                "checkpoints": checkpoints,
                "summary": {
                    "severe_miles": summary.severe_miles,
                    "high_miles": summary.high_miles,
                    "no_travel_miles": summary.no_travel_miles,
                    "average_risk": summary.average_risk,
                    "duration_seconds": summary.duration_seconds,
                    "risk_counts": counts,
                    "checkpoint_count": summary.checkpoint_count,
                },
            }
        )

    order = recommend_routes(summaries)
    recommended_id = order[0] if order else None

    # Corridor heatmap: merge all route polylines (downsampled in builder)
    corridor_coords: list[tuple[float, float]] = []
    for route in routes:
        coords = [(c[0], c[1]) for c in route["coordinates"]]
        step = max(1, len(coords) // 40)
        corridor_coords.extend(coords[::step])

    heatmap = build_corridor_heatmap(corridor_coords, load_lb=load_lb, forecast_hours=48)

    return {
        "origin": origin,
        "destination": destination,
        "departure": departure.isoformat().replace("+00:00", "Z"),
        "load_lb": load_lb,
        "sample_interval_miles": sample_interval_miles,
        "routes": enriched_routes,
        "recommendation": {
            "best_route_id": recommended_id,
            "order": order,
            "rationale": (
                "Ordered by fewest No-Travel miles, then fewest Severe miles, "
                "then fewest High miles, then lowest average risk, then shortest time."
            ),
        },
        "heatmap": heatmap,
        "meta": {
            "demo_fixtures": _demo_mode(),
            "note": (
                "Using offline Dallas/Denver fixtures (USE_DEMO_FIXTURES)."
                if _demo_mode()
                else "Live Nominatim + OSRM + Open-Meteo (auto-falls back to fixtures if unreachable)."
            ),
        },
    }
