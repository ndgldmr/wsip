import { SCORE_COLOR, SEVERITY_COLOR } from "@/lib/theme";

type Severity = "high" | "medium" | "low";

interface RiskBadgeProps {
  severity?: Severity;
  score?: number;
}

function severityFromScore(score: number): Severity {
  return score > 0.7 ? "high" : score > 0.4 ? "medium" : "low";
}

export function RiskBadge({ severity, score }: RiskBadgeProps) {
  const sev: Severity = severity ?? (score !== undefined ? severityFromScore(score) : "low");
  const color = SEVERITY_COLOR[sev] ?? SCORE_COLOR(score ?? 0);
  const label = sev.toUpperCase();
  const blinking = sev === "high";

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
      style={{
        background: `${color}12`,
        border: `1px solid ${color}35`,
        color,
        fontFamily: "var(--font-display)",
        fontSize: "9px",
        fontWeight: 600,
        letterSpacing: "0.12em",
      }}
    >
      <span
        className={blinking ? "blink-dot" : ""}
        style={{
          display: "inline-block",
          width: "4px",
          height: "4px",
          borderRadius: "50%",
          background: color,
          boxShadow: `0 0 5px ${color}`,
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  );
}
