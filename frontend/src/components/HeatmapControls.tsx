import { useEffect, useRef, useState } from "react";
import type { HeatmapData } from "../types";
import { RISK_SCORE_COLORS } from "../riskColors";

interface Props {
  heatmap: HeatmapData | null;
  hourIndex: number;
  onHourChange: (h: number) => void;
  showHeatmap: boolean;
  onToggle: (v: boolean) => void;
}

export function HeatmapControls({ heatmap, hourIndex, onHourChange, showHeatmap, onToggle }: Props) {
  const [localHour, setLocalHour] = useState(hourIndex);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    setLocalHour(hourIndex);
  }, [hourIndex]);

  function handleSlide(value: number) {
    setLocalHour(value);
    if (timer.current) window.clearTimeout(timer.current);
    // Debounce parent update so canvas redraw stays smooth while dragging
    timer.current = window.setTimeout(() => onHourChange(value), 40);
  }

  const max = Math.max((heatmap?.hours ?? 48) - 1, 0);
  const timeLabel = heatmap?.times?.[localHour]
    ? new Date(heatmap.times[localHour] + "Z").toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
      })
    : `+${localHour}h`;

  return (
    <div className="heatmap-controls">
      <div className="heatmap-head">
        <label className="toggle">
          <input type="checkbox" checked={showHeatmap} onChange={(e) => onToggle(e.target.checked)} />
          Weather corridor heatmap
        </label>
        <span className="time-label">{showHeatmap ? timeLabel : "Hidden"}</span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={localHour}
        disabled={!showHeatmap || !heatmap}
        onChange={(e) => handleSlide(Number(e.target.value))}
        aria-label="Forecast hour 0 to 48"
      />
      <div className="slider-ends">
        <span>0h</span>
        <span>48h forecast</span>
      </div>
      <div className="legend">
        {["Low", "Moderate", "High", "Severe", "No Travel"].map((label, i) => (
          <span key={label}>
            <i style={{ background: RISK_SCORE_COLORS[i] }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
