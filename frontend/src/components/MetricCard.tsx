import { SCORE_COLOR, SEVERITY_COLOR, type Severity } from "@/lib/theme";

interface MetricCardProps {
  label: string;
  value: number;
  delta?: number;
  format?: "score" | "percent" | "count";
  severity?: Severity;
}

function formatValue(value: number, format: MetricCardProps["format"]): string {
  switch (format) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "count":
      return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
    case "score":
    default:
      return value.toFixed(2);
  }
}

export function MetricCard({ label, value, delta, format = "score", severity }: MetricCardProps) {
  const color = severity ? SEVERITY_COLOR[severity] : SCORE_COLOR(value);

  const deltaColor = delta === undefined ? undefined : delta > 0 ? "#ff3355" : "#00e090";
  const deltaArrow = delta === undefined ? null : delta > 0 ? "▲" : "▼";

  return (
    <div
      className="hud-card rounded flex flex-col overflow-hidden"
      style={{
        background: `linear-gradient(145deg, ${color}09 0%, var(--bg-surface) 55%)`,
        border: "1px solid var(--border)",
        boxShadow: `0 0 0 1px ${color}18, inset 0 1px 0 ${color}10`,
      }}
    >
      {/* Color bar — top edge indicator */}
      <div
        style={{
          height: "2px",
          background: `linear-gradient(90deg, ${color}, ${color}44)`,
          boxShadow: `0 0 10px ${color}60`,
        }}
      />

      <div className="flex flex-col gap-1.5 p-4">
        {/* Label */}
        <span
          className="font-display text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: "var(--text-muted)" }}
        >
          {label}
        </span>

        {/* Value */}
        <span
          className="font-mono leading-none"
          data-metric
          style={{
            color: "var(--text-primary)",
            fontSize: "2rem",
            fontWeight: 400,
            textShadow: `0 0 20px ${color}30`,
            letterSpacing: "-0.01em",
          }}
        >
          {formatValue(value, format)}
        </span>

        {/* Delta */}
        {delta !== undefined && (
          <span
            className="font-mono text-[11px]"
            style={{ color: deltaColor }}
          >
            {deltaArrow} {Math.abs(delta * 100).toFixed(1)}pp
          </span>
        )}

        {/* Mini severity bar */}
        <div
          className="expand-x"
          style={{
            height: "1px",
            background: `linear-gradient(90deg, ${color}80, transparent)`,
            marginTop: "4px",
          }}
        />
      </div>
    </div>
  );
}

export function MetricCardSkeleton() {
  return (
    <div
      className="rounded overflow-hidden animate-pulse"
      style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
    >
      <div style={{ height: "2px", background: "var(--bg-elevated)" }} />
      <div className="p-4 flex flex-col gap-2">
        <div className="h-2.5 w-24 rounded" style={{ background: "var(--bg-elevated)" }} />
        <div className="h-8 w-20 rounded mt-1" style={{ background: "var(--bg-elevated)" }} />
      </div>
    </div>
  );
}
