import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { HeatmapData, PlanResponse, RouteOption } from "../types";
import { RISK_COLORS, RISK_SCORE_COLORS, ROUTE_COLORS } from "../riskColors";

interface Props {
  data: PlanResponse | null;
  selectedId: string | null;
  hourIndex: number;
  showHeatmap: boolean;
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

class HeatCanvasOverlay extends L.Layer {
  private canvas: HTMLCanvasElement | null = null;
  private points: HeatmapData["points"] = [];
  private scores: number[] = [];

  onAdd(map: L.Map): this {
    this.canvas = document.createElement("canvas");
    this.canvas.className = "heat-canvas leaflet-zoom-animated";
    this.canvas.style.pointerEvents = "none";
    const size = map.getSize();
    this.canvas.width = size.x;
    this.canvas.height = size.y;
    map.getPanes().overlayPane.appendChild(this.canvas);
    map.on("moveend viewreset", this.reset, this);
    this.reset();
    return this;
  }

  onRemove(map: L.Map): this {
    if (this.canvas?.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    map.off("moveend viewreset", this.reset, this);
    this.canvas = null;
    return this;
  }

  setData(points: HeatmapData["points"], scores: number[]) {
    this.points = points;
    this.scores = scores;
    this.reset();
  }

  private reset = () => {
    const map = this._map;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    const topLeft = map.containerPointToLayerPoint([0, 0]);
    L.DomUtil.setPosition(canvas, topLeft);
    const size = map.getSize();
    if (canvas.width !== size.x || canvas.height !== size.y) {
      canvas.width = size.x;
      canvas.height = size.y;
    }
    this.draw();
  };

  private draw() {
    const map = this._map;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const zoom = map.getZoom();
    const radius = Math.max(14, Math.min(36, (zoom - 4) * 6));

    for (let i = 0; i < this.points.length; i++) {
      const p = this.points[i];
      const score = this.scores[i] ?? 0;
      const pt = map.latLngToContainerPoint([p.lat, p.lon]);
      const color = RISK_SCORE_COLORS[Math.min(score, RISK_SCORE_COLORS.length - 1)];
      const grad = ctx.createRadialGradient(pt.x, pt.y, 0, pt.x, pt.y, radius);
      grad.addColorStop(0, hexToRgba(color, 0.55));
      grad.addColorStop(1, hexToRgba(color, 0));
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

export function RouteMap({ data, selectedId, hourIndex, showHeatmap }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routesLayerRef = useRef<L.LayerGroup | null>(null);
  const heatRef = useRef<HeatCanvasOverlay | null>(null);
  const fittedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    }).setView([39.5, -98.35], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    routesLayerRef.current = L.layerGroup().addTo(map);
    heatRef.current = new HeatCanvasOverlay();
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = routesLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    if (!data) return;

    const bounds = L.latLngBounds([]);
    data.routes.forEach((route: RouteOption, idx: number) => {
      const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];
      const isSelected = route.id === selectedId;
      const isBest = route.id === data.recommendation.best_route_id;
      const latlngs = route.coordinates.map((c) => L.latLng(c[0], c[1]));
      latlngs.forEach((ll) => bounds.extend(ll));

      L.polyline(latlngs, {
        color,
        weight: isSelected ? 6 : isBest ? 5 : 3,
        opacity: isSelected || isBest ? 0.95 : 0.55,
        lineJoin: "round",
      }).addTo(layer);

      route.checkpoints.forEach((cp) => {
        const marker = L.circleMarker([cp.lat, cp.lon], {
          radius: isSelected ? 6 : 4,
          color: "#1a1a1a",
          weight: 1,
          fillColor: RISK_COLORS[cp.risk],
          fillOpacity: 0.9,
        });
        marker.bindPopup(
          `<strong>${route.label}</strong><br/>` +
            `${cp.distance_miles.toFixed(0)} mi · <b>${cp.risk}</b><br/>` +
            `ETA ${new Date(cp.eta).toLocaleString()}<br/>` +
            `Wind ${cp.wind_mph} mph · Rain ${cp.rain_in_hr} in/hr · Snow ${cp.snow_in_hr} in/hr`,
        );
        marker.addTo(layer);
      });
    });

    L.circleMarker([data.origin.lat, data.origin.lon], {
      radius: 8,
      color: "#111",
      fillColor: "#fff",
      fillOpacity: 1,
      weight: 2,
    })
      .bindPopup(`Origin: ${data.origin.display_name}`)
      .addTo(layer);
    L.circleMarker([data.destination.lat, data.destination.lon], {
      radius: 8,
      color: "#111",
      fillColor: "#212529",
      fillOpacity: 1,
      weight: 2,
    })
      .bindPopup(`Destination: ${data.destination.display_name}`)
      .addTo(layer);

    const fitKey = `${data.origin.lat},${data.destination.lat},${data.routes.length}`;
    if (bounds.isValid() && fittedRef.current !== fitKey) {
      map.fitBounds(bounds.pad(0.12));
      fittedRef.current = fitKey;
    }
  }, [data, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    const heat = heatRef.current;
    if (!map || !heat) return;

    if (!data || !showHeatmap) {
      if (map.hasLayer(heat)) {
        map.removeLayer(heat);
      }
      return;
    }

    const scores = data.heatmap.scores_by_hour[hourIndex] || [];
    heat.setData(data.heatmap.points, scores);
    if (!map.hasLayer(heat)) {
      map.addLayer(heat);
    }
  }, [data, hourIndex, showHeatmap]);

  return <div ref={containerRef} className="route-map" role="img" aria-label="Route map" />;
}
