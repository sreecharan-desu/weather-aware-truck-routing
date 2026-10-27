import { useState, type FormEvent } from "react";
import type { PlanRequest } from "../types";

interface Props {
  loading: boolean;
  onSubmit: (req: PlanRequest) => void;
}

function defaultDepartureLocal(): string {
  const d = new Date();
  d.setMinutes(0, 0, 0);
  d.setHours(d.getHours() + 1);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function PlanForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState("Dallas, TX");
  const [destination, setDestination] = useState("Denver, CO");
  const [departure, setDeparture] = useState(defaultDepartureLocal);
  const [loadLb, setLoadLb] = useState(35000);
  const [interval, setInterval] = useState<10 | 25 | 50>(25);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // Treat datetime-local as local wall time → ISO with offset
    const local = new Date(departure);
    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      departure: local.toISOString(),
      load_lb: Number(loadLb),
      sample_interval_miles: interval,
    });
  }

  return (
    <form className="plan-form" onSubmit={handleSubmit}>
      <label>
        Origin
        <input value={origin} onChange={(e) => setOrigin(e.target.value)} required placeholder="City, State" />
      </label>
      <label>
        Destination
        <input
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          required
          placeholder="City, State"
        />
      </label>
      <label>
        Departure
        <input
          type="datetime-local"
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
          required
        />
      </label>
      <label>
        Load weight (lb)
        <input
          type="number"
          min={0}
          step={100}
          value={loadLb}
          onChange={(e) => setLoadLb(Number(e.target.value))}
          required
        />
      </label>
      <fieldset>
        <legend>Weather sample interval</legend>
        <div className="segmented">
          {([10, 25, 50] as const).map((v) => (
            <button
              key={v}
              type="button"
              className={interval === v ? "active" : ""}
              onClick={() => setInterval(v)}
            >
              {v} mi
            </button>
          ))}
        </div>
      </fieldset>
      <button type="submit" className="primary" disabled={loading}>
        {loading ? "Planning routes…" : "Plan safest route"}
      </button>
    </form>
  );
}
