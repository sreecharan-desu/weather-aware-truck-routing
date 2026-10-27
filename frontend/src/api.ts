import type { PlanRequest, PlanResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export async function planTrip(body: PlanRequest): Promise<PlanResponse> {
  const res = await fetch(`${API_BASE}/api/plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data as PlanResponse;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health/`);
    return res.ok;
  } catch {
    return false;
  }
}

export { API_BASE };
