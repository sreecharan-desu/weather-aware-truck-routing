"""Vercel serverless entrypoint exposing the Django WSGI app."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()

_django_app = app


def app(environ, start_response):  # noqa: F811
    """Log the incoming path for diagnostics, then hand off to Django."""
    print("PATH_INFO", environ.get("PATH_INFO"), "RAW", environ.get("RAW_URI"), "HDR", environ.get("HTTP_X_MATCHED_PATH"), flush=True)
    return _django_app(environ, start_response)
