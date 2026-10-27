import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.geocoding import geocode
from .services.planner import plan_trip

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health(_request):
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode_view(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = geocode(q)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Geocode failed")
        return Response({"detail": f"Geocoding error: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(result)


@api_view(["POST"])
def plan_view(request):
    data = request.data or {}
    origin = str(data.get("origin", "")).strip()
    destination = str(data.get("destination", "")).strip()
    departure = str(data.get("departure", "")).strip()
    load_lb = data.get("load_lb", data.get("load_weight"))
    interval = data.get("sample_interval_miles", 25)

    missing = [name for name, val in [
        ("origin", origin),
        ("destination", destination),
        ("departure", departure),
        ("load_lb", load_lb),
    ] if val in ("", None)]
    if missing:
        return Response(
            {"detail": f"Missing required fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        load_val = float(load_lb)
        interval_val = int(interval)
    except (TypeError, ValueError):
        return Response(
            {"detail": "load_lb must be a number and sample_interval_miles must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = plan_trip(
            origin_query=origin,
            destination_query=destination,
            departure_iso=departure,
            load_lb=load_val,
            sample_interval_miles=interval_val,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Plan failed")
        return Response({"detail": f"Planning error: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(result)
