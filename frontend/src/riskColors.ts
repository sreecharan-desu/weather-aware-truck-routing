import type { RiskLabel } from "./types";

export const RISK_COLORS: Record<RiskLabel, string> = {
  Low: "#2f9e44",
  Moderate: "#f59f00",
  High: "#f76707",
  Severe: "#e03131",
  "No Travel": "#862e9c",
};

export const RISK_SCORE_COLORS = ["#2f9e44", "#f59f00", "#f76707", "#e03131", "#862e9c"];

export const ROUTE_COLORS = ["#1c7ed6", "#0ca678", "#d9480f"];
