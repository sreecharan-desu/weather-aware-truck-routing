"""Unit tests for risk classification and route recommendation."""

from routing.services.risk import (
    RiskLevel,
    apply_load_rules,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
    recommend_routes,
    summarize_route_risk,
)


class TestWindClassification:
    def test_low(self):
        assert classify_wind(0) == RiskLevel.LOW
        assert classify_wind(24.9) == RiskLevel.LOW

    def test_moderate(self):
        assert classify_wind(25) == RiskLevel.MODERATE
        assert classify_wind(34) == RiskLevel.MODERATE

    def test_high(self):
        assert classify_wind(35) == RiskLevel.HIGH
        assert classify_wind(44) == RiskLevel.HIGH

    def test_severe(self):
        assert classify_wind(45) == RiskLevel.SEVERE
        assert classify_wind(54) == RiskLevel.SEVERE

    def test_no_travel(self):
        assert classify_wind(55) == RiskLevel.NO_TRAVEL
        assert classify_wind(80) == RiskLevel.NO_TRAVEL


class TestRainClassification:
    def test_boundaries(self):
        assert classify_rain(0.0) == RiskLevel.LOW
        assert classify_rain(0.09) == RiskLevel.LOW
        assert classify_rain(0.10) == RiskLevel.MODERATE
        assert classify_rain(0.25) == RiskLevel.MODERATE
        assert classify_rain(0.26) == RiskLevel.HIGH
        assert classify_rain(0.50) == RiskLevel.HIGH
        assert classify_rain(0.51) == RiskLevel.SEVERE
        assert classify_rain(1.00) == RiskLevel.SEVERE
        assert classify_rain(1.01) == RiskLevel.NO_TRAVEL


class TestSnowClassification:
    def test_boundaries(self):
        assert classify_snow(0.0) == RiskLevel.LOW
        assert classify_snow(0.49) == RiskLevel.LOW
        assert classify_snow(0.5) == RiskLevel.MODERATE
        assert classify_snow(1.0) == RiskLevel.MODERATE
        assert classify_snow(1.01) == RiskLevel.HIGH
        assert classify_snow(2.0) == RiskLevel.HIGH
        assert classify_snow(2.01) == RiskLevel.SEVERE
        assert classify_snow(3.0) == RiskLevel.SEVERE
        assert classify_snow(3.01) == RiskLevel.NO_TRAVEL


class TestLoadRules:
    def test_any_load_no_travel_at_55(self):
        assert apply_load_rules(55, 0, RiskLevel.LOW) == RiskLevel.NO_TRAVEL
        assert apply_load_rules(60, 10_000, RiskLevel.MODERATE) == RiskLevel.NO_TRAVEL

    def test_heavy_load_severe_wind_becomes_no_travel(self):
        # 45–54 mph + >30,000 lb → No Travel
        assert apply_load_rules(50, 30_001, RiskLevel.SEVERE) == RiskLevel.NO_TRAVEL
        assert apply_load_rules(50, 30_000, RiskLevel.SEVERE) == RiskLevel.SEVERE

    def test_very_heavy_load_high_wind_becomes_severe(self):
        # 35–44 mph + >40,000 lb → Severe
        assert apply_load_rules(40, 40_001, RiskLevel.HIGH) == RiskLevel.SEVERE
        assert apply_load_rules(40, 40_000, RiskLevel.HIGH) == RiskLevel.HIGH

    def test_does_not_downgrade(self):
        # Load rules only raise risk
        assert apply_load_rules(10, 50_000, RiskLevel.SEVERE) == RiskLevel.SEVERE


class TestClassifyCheckpoint:
    def test_max_of_conditions(self):
        result = classify_checkpoint(
            wind_mph=10,
            rain_in_hr=0.6,  # Severe
            snow_in_hr=0.0,
            load_lb=20_000,
        )
        assert result["risk"] == "Severe"
        assert result["risk_score"] == int(RiskLevel.SEVERE)

    def test_load_upgrade(self):
        result = classify_checkpoint(
            wind_mph=50,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_lb=35_000,
        )
        assert result["risk"] == "No Travel"


class TestRecommendation:
    def _cp(self, risk_score: int, miles: float = 25.0) -> dict:
        return {"risk_score": risk_score, "segment_miles": miles}

    def test_prefers_fewer_severe_miles(self):
        a = summarize_route_risk("a", [self._cp(3), self._cp(3)], 3600, 25)
        b = summarize_route_risk("b", [self._cp(3), self._cp(0)], 4000, 25)
        assert recommend_routes([a, b])[0] == "b"

    def test_then_fewer_high_miles(self):
        a = summarize_route_risk("a", [self._cp(2), self._cp(2)], 3600, 25)
        b = summarize_route_risk("b", [self._cp(2), self._cp(0)], 4000, 25)
        assert recommend_routes([a, b])[0] == "b"

    def test_then_lower_average_risk(self):
        a = summarize_route_risk("a", [self._cp(1), self._cp(1)], 3600, 25)
        b = summarize_route_risk("b", [self._cp(0), self._cp(0)], 3600, 25)
        assert recommend_routes([a, b])[0] == "b"

    def test_then_shortest_time(self):
        a = summarize_route_risk("a", [self._cp(0)], 5000, 25)
        b = summarize_route_risk("b", [self._cp(0)], 3000, 25)
        assert recommend_routes([a, b])[0] == "b"

    def test_no_travel_sorted_before_severe(self):
        a = summarize_route_risk("a", [self._cp(4)], 2000, 25)
        b = summarize_route_risk("b", [self._cp(3), self._cp(3)], 5000, 25)
        assert recommend_routes([a, b])[0] == "b"
