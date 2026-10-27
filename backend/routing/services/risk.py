"""Weather risk classification and route recommendation.

Thresholds and load rules follow the assessment specification exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Sequence


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }[self]


# Wind speed in mph
def classify_wind(mph: float) -> RiskLevel:
    if mph < 25:
        return RiskLevel.LOW
    if mph < 35:
        return RiskLevel.MODERATE
    if mph < 45:
        return RiskLevel.HIGH
    if mph < 55:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


# Rain intensity in inches per hour
def classify_rain(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour < 0.10:
        return RiskLevel.LOW
    if inches_per_hour <= 0.25:
        return RiskLevel.MODERATE
    if inches_per_hour <= 0.50:
        return RiskLevel.HIGH
    if inches_per_hour <= 1.00:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


# Snow intensity in inches per hour
def classify_snow(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour < 0.5:
        return RiskLevel.LOW
    if inches_per_hour <= 1.0:
        return RiskLevel.MODERATE
    if inches_per_hour <= 2.0:
        return RiskLevel.HIGH
    if inches_per_hour <= 3.0:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def apply_load_rules(wind_mph: float, load_lb: float, base_risk: RiskLevel) -> RiskLevel:
    """Apply load-dependent wind upgrades on top of the base (max) risk.

    Rules:
    - ≥55 mph → No Travel for any load
    - 45–54 mph + >30,000 lb → No Travel
    - 35–44 mph + >40,000 lb → Severe
    """
    risk = base_risk

    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL

    if 45 <= wind_mph < 55 and load_lb > 30_000:
        risk = max(risk, RiskLevel.NO_TRAVEL)

    if 35 <= wind_mph < 45 and load_lb > 40_000:
        risk = max(risk, RiskLevel.SEVERE)

    return risk


def classify_checkpoint(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lb: float,
) -> dict:
    """Classify a single checkpoint. Overall risk is the max of wind/rain/snow,
    then load rules may raise it further.
    """
    wind_risk = classify_wind(wind_mph)
    rain_risk = classify_rain(rain_in_hr)
    snow_risk = classify_snow(snow_in_hr)
    base = max(wind_risk, rain_risk, snow_risk)
    overall = apply_load_rules(wind_mph, load_lb, base)

    return {
        "wind_risk": wind_risk.label,
        "rain_risk": rain_risk.label,
        "snow_risk": snow_risk.label,
        "risk": overall.label,
        "risk_score": int(overall),
        "wind_mph": round(wind_mph, 2),
        "rain_in_hr": round(rain_in_hr, 4),
        "snow_in_hr": round(snow_in_hr, 3),
    }


@dataclass(frozen=True)
class RouteRiskSummary:
    route_id: str
    severe_miles: float
    high_miles: float
    no_travel_miles: float
    average_risk: float
    duration_seconds: float
    checkpoint_count: int


def summarize_route_risk(
    route_id: str,
    checkpoints: Sequence[dict],
    duration_seconds: float,
    sample_interval_miles: float,
) -> RouteRiskSummary:
    """Aggregate checkpoint risks into mile-weighted summary stats.

    Each checkpoint represents up to ``sample_interval_miles`` of the route
    (the last segment may be shorter; we still attribute the interval for
    comparison fairness across equally sampled routes).
    """
    if not checkpoints:
        return RouteRiskSummary(
            route_id=route_id,
            severe_miles=0.0,
            high_miles=0.0,
            no_travel_miles=0.0,
            average_risk=0.0,
            duration_seconds=duration_seconds,
            checkpoint_count=0,
        )

    severe = 0.0
    high = 0.0
    no_travel = 0.0
    score_sum = 0.0

    for cp in checkpoints:
        score = int(cp.get("risk_score", RiskLevel.LOW))
        miles = float(cp.get("segment_miles", sample_interval_miles))
        score_sum += score
        if score >= RiskLevel.NO_TRAVEL:
            no_travel += miles
        elif score >= RiskLevel.SEVERE:
            severe += miles
        elif score >= RiskLevel.HIGH:
            high += miles

    return RouteRiskSummary(
        route_id=route_id,
        severe_miles=round(severe, 2),
        high_miles=round(high, 2),
        no_travel_miles=round(no_travel, 2),
        average_risk=round(score_sum / len(checkpoints), 4),
        duration_seconds=duration_seconds,
        checkpoint_count=len(checkpoints),
    )


def recommend_routes(summaries: Iterable[RouteRiskSummary]) -> list[str]:
    """Order routes by the assessment preference:

    1. Fewest Severe miles (No Travel counted as worse — sorted first)
    2. Fewest High miles
    3. Lowest average risk
    4. Shortest travel time

    Returns ordered route_id list (best first).
    """
    ordered = sorted(
        summaries,
        key=lambda s: (
            s.no_travel_miles,
            s.severe_miles,
            s.high_miles,
            s.average_risk,
            s.duration_seconds,
        ),
    )
    return [s.route_id for s in ordered]
