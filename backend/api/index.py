"""Vercel serverless entrypoint exposing the Django WSGI app.

The Python runtime imports `app` from this module. Requests keep their original
path (for example `/api/health/` and `/api/plan/`); `config.urls` routes them.
"""

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402

# Vercel looks up `app`. Django's WSGI callable is `application`.
app = application
