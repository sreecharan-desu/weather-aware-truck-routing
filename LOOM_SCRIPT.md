# Loom walkthrough script (5–8 minutes)

Record yourself sharing the screen. Speak naturally; use this as a checklist, not a teleprompter. Target **5–8 minutes** (assessment allows up to ~10).

---

## 0:00–0:40 — Intro

- Name the project: **Weather-Aware Truck Routing**.
- One sentence: “A React + Django app that compares three truck routes using live weather at the driver’s ETA, load weight, and travel time.”
- Mention stack briefly: React/Leaflet frontend, Django API, free services only (OSRM, Nominatim, Open-Meteo, OSM tiles).

## 0:40–1:30 — Architecture overview

- Show the GitHub repo layout: `frontend/`, `backend/routing/services/`.
- Point at `risk.py` (thresholds + load rules + recommendation), `planner.py` (orchestration), and the map UI.
- Note: no paid API keys; deploy configs for Vercel + Render.

## 1:30–2:30 — Local or hosted demo start

- Open the running app (local or deployed).
- Fill the form:
  - Origin: **Dallas, TX**
  - Destination: **Denver, CO**
  - Departure: a time in the next few hours
  - Load: **35,000 lb**
  - Sample interval: **25 miles**
- Click **Plan safest route**. While it loads, say: geocode → OSRM alternatives → Open-Meteo batch → risk scoring.

## 2:30–4:00 — Map, routes, checkpoints

- Show **three routes** on the map with different colors.
- Click the recommended route in the sidebar; highlight Severe / High mile summaries.
- Open a checkpoint popup: risk label, ETA, wind / rain / snow values.
- Briefly explain recommendation order: No-Travel → Severe → High → average risk → shortest time.
- Mention load rules: e.g. 45–54 mph wind with &gt;30k lb becomes No Travel.

## 4:00–5:30 — Heatmap slider

- Toggle the **weather corridor heatmap**.
- Drag the **0–48h** slider; show colors changing along the corridor.
- Call out performance: scores are **precomputed per hour** on the backend; the UI only swaps arrays and redraws on a **canvas** with a **debounced** slider.

## 5:30–6:30 — Interval + tests (optional depth)

- Re-run with **10 mi** sampling (or mention it) to show denser checkpoints.
- Flash `pytest` results or open `test_risk.py` — unit tests for thresholds, load rules, and ranking.

## 6:30–7:30 — Deploy + limits + close

- Point at `vercel.json`, `render.yaml`, and README deploy steps.
- Honest limits: shared free APIs, Render cold starts, hourly weather resolution.
- Close: “Correctness of risk and recommendation first; map and heatmap kept lean for clarity.”

---

## Recording tips

- Use 1080p; zoom IDE text if needed.
- Avoid personal email, phone, or private IDs on screen.
- If an API is slow, narrate the wait once and continue when data arrives.
- Keep extras out — no feature tour beyond the assessment requirements.
