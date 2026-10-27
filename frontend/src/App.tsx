import { useCallback, useState } from "react";
import { planTrip } from "./api";
import { HeatmapControls } from "./components/HeatmapControls";
import { PlanForm } from "./components/PlanForm";
import { RouteMap } from "./components/RouteMap";
import { RoutePanel } from "./components/RoutePanel";
import type { PlanRequest, PlanResponse } from "./types";
import "./App.css";

export default function App() {
  const [data, setData] = useState<PlanResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hourIndex, setHourIndex] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);

  const onSubmit = useCallback(async (req: PlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await planTrip(req);
      setData(result);
      setSelectedId(result.recommendation.best_route_id ?? result.routes[0]?.id ?? null);
      setHourIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Planning failed");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <p className="brand">Corridor</p>
          <h1>Weather-Aware Truck Routing</h1>
          <p className="tagline">Choose the safest path for the load, the weather, and the clock.</p>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <PlanForm loading={loading} onSubmit={onSubmit} />
          {error && <div className="error">{error}</div>}
          {loading && (
            <div className="loading-note">
              Geocoding, fetching OSRM alternatives, and batching Open-Meteo forecasts…
            </div>
          )}
          {data && (
            <RoutePanel data={data} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </aside>

        <main className="map-stage">
          <RouteMap
            data={data}
            selectedId={selectedId}
            hourIndex={hourIndex}
            showHeatmap={showHeatmap}
          />
          <HeatmapControls
            heatmap={data?.heatmap ?? null}
            hourIndex={hourIndex}
            onHourChange={setHourIndex}
            showHeatmap={showHeatmap}
            onToggle={setShowHeatmap}
          />
          {!data && !loading && (
            <div className="map-empty">
              Plan a trip to see three weather-scored routes. Try Dallas, TX → Denver, CO.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
