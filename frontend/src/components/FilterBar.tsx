import { useState } from "react";
import { today } from "@/lib/utils";

export interface RecommendationFilters {
  scope: string;
  priority_min: number;
}

interface FilterBarProps {
  onFiltersChange: (filters: RecommendationFilters) => void;
}

const SCOPE_OPTIONS = [
  { value: "",         label: "All scopes" },
  { value: "org",      label: "Org" },
  { value: "team",     label: "Team" },
  { value: "employee", label: "Employee" },
];

const selectStyle: React.CSSProperties = {
  background: "var(--bg-elevated)",
  border: "1px solid var(--border)",
  color: "var(--text-primary)",
  borderRadius: "4px",
  fontSize: "11px",
  padding: "3px 6px",
  fontFamily: "var(--font-mono)",
  outline: "none",
};

export function FilterBar({ onFiltersChange }: FilterBarProps) {
  const [scope, setScope] = useState("");
  const [priorityMin, setPriorityMin] = useState(0);

  function handleScopeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    setScope(val);
    onFiltersChange({ scope: val, priority_min: priorityMin });
  }

  function handlePriorityChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseFloat(e.target.value);
    setPriorityMin(val);
    onFiltersChange({ scope, priority_min: val });
  }

  return (
    <div
      className="flex flex-wrap items-center gap-5 px-4 py-2.5 rounded mb-4"
      style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
    >
      <span
        className="font-display text-[9px] tracking-widest uppercase"
        style={{ color: "var(--text-muted)" }}
      >
        Filters
      </span>

      <label className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-secondary)" }}>
        <span className="font-display text-[9px] tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
          Scope
        </span>
        <select value={scope} onChange={handleScopeChange} style={selectStyle}>
          {SCOPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-3 text-[11px]" style={{ color: "var(--text-secondary)" }}>
        <span className="font-display text-[9px] tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
          Min Priority
        </span>
        <span
          className="font-mono text-[11px] w-8 text-right"
          style={{ color: "var(--accent-cyan)" }}
        >
          {priorityMin.toFixed(1)}
        </span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={priorityMin}
          onChange={handlePriorityChange}
          className="w-20"
          style={{ accentColor: "var(--accent-cyan)" }}
        />
      </label>
    </div>
  );
}

export { today };
