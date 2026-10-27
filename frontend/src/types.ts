export type RiskLabel = "Low" | "Moderate" | "High" | "Severe" | "No Travel";

export interface Checkpoint {
  lat: number;
  lon: number;
  distance_miles: number;
  segment_miles: number;
  eta: string;
  wind_risk: RiskLabel;
  rain_risk: RiskLabel;
  snow_risk: RiskLabel;
  risk: RiskLabel;
  risk_score: number;
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface RouteSummary {
  severe_miles: number;
  high_miles: number;
  no_travel_miles: number;
  average_risk: number;
  duration_seconds: number;
  risk_counts: Record<string, number>;
  checkpoint_count: number;
}

export interface RouteOption {
  id: string;
  label: string;
  geometry: string;
  coordinates: [number, number][];
  distance_miles: number;
  duration_seconds: number;
  duration_hours: number;
  checkpoints: Checkpoint[];
  summary: RouteSummary;
}

export interface HeatmapData {
  points: { lat: number; lon: number }[];
  hours: number;
  times: string[];
  scores_by_hour: number[][];
}

export interface PlanResponse {
  origin: { query: string; display_name: string; lat: number; lon: number };
  destination: { query: string; display_name: string; lat: number; lon: number };
  departure: string;
  load_lb: number;
  sample_interval_miles: number;
  routes: RouteOption[];
  recommendation: {
    best_route_id: string | null;
    order: string[];
    rationale: string;
  };
  heatmap: HeatmapData;
}

export interface PlanRequest {
  origin: string;
  destination: string;
  departure: string;
  load_lb: number;
  sample_interval_miles: 10 | 25 | 50;
}
