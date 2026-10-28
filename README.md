# Weather-Aware Truck Routing

React + Django web app that helps a truck driver pick the safest route based on weather, load weight, and travel time.

## Live demo

- Web app: https://wx-truck-routing.vercel.app
- API: https://wx-truck-routing-api.vercel.app

`GET /api/health/` returns `{"status":"ok"}`. `POST /api/plan/` plans a trip. The frontend is built with `VITE_API_URL=https://wx-truck-routing-api.vercel.app`, and the API allows the web origin `https://wx-truck-routing.vercel.app` (plus `https://truck-routing-web.vercel.app` when that host is used).

Same deployments also answer on https://truck-routing-web-murex.vercel.app and https://truck-routing-api-xi.vercel.app. The unsuffixed names `truck-routing-web.vercel.app` and `truck-routing-api.vercel.app` are already assigned on another Vercel team, so they are not this app.

## Features

- Origin, destination, departure date/time, and load weight inputs
- Three driving route options (OSRM public demo; waypoint detours if fewer than three alternatives)
- Weather sampled every **10 / 25 / 50** miles at the truck’s ETA for each checkpoint
- Risk classification from wind / rain / snow thresholds plus load rules
- Recommendation order: fewest No-Travel miles, fewest Severe miles, fewest High miles, lowest average risk, shortest time
- Leaflet map with all routes, checkpoints, risk colors, ETAs, and summaries
- Corridor weather heatmap with a **0–48 hour** forecast slider (precomputed per hour, canvas draw, debounced updates)

## Architecture

```
frontend/          Vite + React + TypeScript + Leaflet
backend/           Django + Django REST Framework
  routing/
    services/
      risk.py      Thresholds, load rules, recommendation
      geo.py       Polyline decode & mile sampling
      geocoding.py Nominatim (User-Agent + 1 req/s)
      osrm.py      OSRM routes + detour alternatives
      weather.py   Open-Meteo batch + cache
      planner.py   Orchestrates a full plan
```

`POST /api/plan/` geocodes endpoints, fetches routes, batches weather, scores checkpoints, ranks routes, and returns a precomputed heatmap payload for the slider.

## API choices (free only)

| Need | Service | Notes |
|------|---------|--------|
| Geocoding | [Nominatim](https://nominatim.openstreetmap.org/) | Custom User-Agent; throttled to ~1 req/s; in-process LRU cache |
| Routing | [OSRM](https://router.project-osrm.org/) public demo | `alternatives=true`; detours via mid-corridor waypoints when &lt; 3 routes |
| Weather | [Open-Meteo](https://open-meteo.com/) | Hourly wind / precipitation / snowfall; batched coordinates; 30‑min cache |
| Map tiles | OpenStreetMap via Leaflet | No API key |

No paid API keys are required.

## Risk logic

### Condition thresholds

| | Low | Moderate | High | Severe | No Travel |
|---|-----|----------|------|--------|-----------|
| Wind | &lt;25 mph | 25–34 | 35–44 | 45–54 | ≥55 mph |
| Rain | &lt;0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | &gt;1.00 |
| Snow | &lt;0.5 in/hr | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | &gt;3.0 |

Checkpoint overall risk = max(wind, rain, snow), then load rules may raise it:

- ≥55 mph → **No Travel** for any load
- 45–54 mph + load &gt; 30,000 lb → **No Travel**
- 35–44 mph + load &gt; 40,000 lb → **Severe**

### Recommendation

Routes are ordered by:

1. Fewest No-Travel miles  
2. Fewest Severe miles  
3. Fewest High miles  
4. Lowest average risk score  
5. Shortest travel time  

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Health check: `GET http://127.0.0.1:8000/api/health/`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://127.0.0.1:8000
npm run dev
```

Open the Vite URL (default `http://127.0.0.1:5173`).

### Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Covers wind/rain/snow thresholds, load rules, and recommendation ordering.

### Demo

1. Origin: `Dallas, TX`  
2. Destination: `Denver, CO`  
3. Departure: near-term datetime  
4. Load: e.g. `35000` lb  
5. Interval: `25` mi  

Expect three scored routes, a recommended route, checkpoint ETAs/risks on the map, and a working heatmap slider.

## Deploy (free tiers)

### Backend — Vercel

- Project root: `backend/`
- `backend/api/index.py` exposes the Django WSGI app; `backend/vercel.json` rewrites every path to that function and allows up to 60s for a plan.
- `DJANGO_ALLOWED_HOSTS` should include `.vercel.app`.
- `CORS_ALLOWED_ORIGINS` should include the web origin (`https://wx-truck-routing.vercel.app`).

### Backend — Render

- `render.yaml` at the repo root defines a free Python web service (`rootDir: backend`, gunicorn).
- Set **`CORS_ALLOWED_ORIGINS`** to your frontend origin (e.g. `https://wx-truck-routing.vercel.app`).
- Optional: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=.onrender.com`.

Manual alternative: create a Render Web Service pointing at `backend/`, build `pip install -r requirements.txt`, start with the `Procfile` / gunicorn command.

### Frontend — Vercel

- Project root: `frontend/`
- Build: `npm run build` · Output: `dist`
- Env: `VITE_API_URL=https://wx-truck-routing-api.vercel.app`
- `vercel.json` provides SPA rewrites

After both are live, confirm CORS allows the Vercel origin and that a Dallas → Denver plan succeeds.

## Demo fixtures (offline)

Set `USE_DEMO_FIXTURES=true` to force the Dallas/Denver offline corridor (no external HTTPS).  
If live Nominatim / OSRM / Open-Meteo are unreachable, the API also falls back to those fixtures automatically so local demos keep working. Live APIs are the default when the network allows them.

## Known limits

- OSRM public demo and Nominatim are shared resources — rate limits or downtime can slow or fail plans.
- Open-Meteo free forecast is hourly; sub-hour weather is interpolated by nearest hour.
- Detour-generated alternatives may share long corridor segments; they are still distinct OSRM paths.
- Render free tier spins down after idle; the first API request may be slow.
- Heatmap samples a downsampled corridor (not a full regional grid) to stay responsive.
- SQLite is used for Django’s defaults only; planning state is computed per request (no trip DB).
- Offline fixtures are for Dallas → Denver demos only; other city pairs need live geocoding/routing.

## Loom walkthrough

See [`LOOM_SCRIPT.md`](./LOOM_SCRIPT.md) for a 5–8 minute recording script.

## License

MIT — see [`LICENSE`](./LICENSE).
