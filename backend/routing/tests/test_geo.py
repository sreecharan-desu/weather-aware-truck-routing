"""Unit tests for geometry helpers."""

from routing.services.geo import decode_polyline, haversine_miles, sample_along_route


def test_haversine_dallas_denver_ballpark():
    # Dallas ~32.78,-96.80 ; Denver ~39.74,-104.99 — roughly 660–700 mi
    miles = haversine_miles(32.78, -96.80, 39.74, -104.99)
    assert 620 < miles < 760


def test_sample_interval():
    # Straight-ish short path ~100 miles north
    start = (32.0, -97.0)
    end = (33.45, -97.0)  # ~100 miles
    # Build dense line
    coords = []
    for i in range(21):
        t = i / 20
        coords.append((start[0] + (end[0] - start[0]) * t, start[1]))
    samples = sample_along_route(coords, 25)
    assert samples[0]["distance_miles"] == 0.0
    distances = [s["distance_miles"] for s in samples]
    # Samples at 0, 25, 50, 75, 100 (approx)
    assert distances[0] == 0.0
    assert any(abs(d - 25) < 1 for d in distances)
    assert any(abs(d - 50) < 1 for d in distances)


def test_decode_polyline_roundtrip_shape():
    # Known short polyline encoding for a couple points (OSRM style)
    # Empty / trivial: just ensure function returns list
    encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    coords = decode_polyline(encoded)
    assert len(coords) >= 2
    assert all(len(c) == 2 for c in coords)
