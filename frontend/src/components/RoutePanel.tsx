import type { PlanResponse, RouteOption } from "../types";
import { RISK_COLORS, ROUTE_COLORS } from "../riskColors";

interface Props {
  data: PlanResponse;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatEta(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function RoutePanel({ data, selectedId, onSelect }: Props) {
  const best = data.recommendation.best_route_id;
  const byId = Object.fromEntries(data.routes.map((r) => [r.id, r])) as Record<string, RouteOption>;
  const ordered = data.recommendation.order.map((id) => byId[id]).filter(Boolean);

  return (
    <div className="route-panel">
      <div className="recommend-banner">
        <span className="eyebrow">Recommended</span>
        <strong>{byId[best ?? ""]?.label ?? "—"}</strong>
        <p>{data.recommendation.rationale}</p>
      </div>

      <ul className="route-list">
        {ordered.map((route, idx) => {
          const color = ROUTE_COLORS[data.routes.findIndex((r) => r.id === route.id) % ROUTE_COLORS.length];
          const isBest = route.id === best;
          const isSelected = route.id === selectedId;
          const lastCp = route.checkpoints[route.checkpoints.length - 1];
          return (
            <li key={route.id}>
              <button
                type="button"
                className={`route-card ${isSelected ? "selected" : ""} ${isBest ? "best" : ""}`}
                onClick={() => onSelect(route.id)}
                style={{ borderLeftColor: color }}
              >
                <div className="route-card-head">
                  <span className="swatch" style={{ background: color }} />
                  <span>
                    {route.label}
                    {isBest ? " · best" : ""}
                  </span>
                  <span className="rank">#{idx + 1}</span>
                </div>
                <div className="route-metrics">
                  <span>{route.distance_miles.toFixed(0)} mi</span>
                  <span>{formatDuration(route.duration_seconds)}</span>
                  <span>avg risk {route.summary.average_risk.toFixed(2)}</span>
                </div>
                <div className="risk-pills">
                  <span style={{ color: RISK_COLORS.Severe }}>
                    Severe {route.summary.severe_miles.toFixed(0)} mi
                  </span>
                  <span style={{ color: RISK_COLORS.High }}>
                    High {route.summary.high_miles.toFixed(0)} mi
                  </span>
                  {route.summary.no_travel_miles > 0 && (
                    <span style={{ color: RISK_COLORS["No Travel"] }}>
                      No Travel {route.summary.no_travel_miles.toFixed(0)} mi
                    </span>
                  )}
                </div>
                {lastCp && <div className="eta">Arrival ~ {formatEta(lastCp.eta)}</div>}
              </button>
            </li>
          );
        })}
      </ul>

      {selectedId && byId[selectedId] && (
        <div className="checkpoint-summary">
          <h3>Checkpoints · {byId[selectedId].label}</h3>
          <div className="cp-scroll">
            {byId[selectedId].checkpoints.map((cp, i) => (
              <div key={`${cp.distance_miles}-${i}`} className="cp-row">
                <span className="dot" style={{ background: RISK_COLORS[cp.risk] }} />
                <span>{cp.distance_miles.toFixed(0)} mi</span>
                <span className="risk-label" style={{ color: RISK_COLORS[cp.risk] }}>
                  {cp.risk}
                </span>
                <span>{formatEta(cp.eta)}</span>
                <span className="wx">
                  {cp.wind_mph.toFixed(0)} mph · rain {cp.rain_in_hr.toFixed(2)} · snow{" "}
                  {cp.snow_in_hr.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
