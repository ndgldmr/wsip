import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

export interface ContributionSegment {
  label: string;
  value: number;
  color: string;
}

interface ContributionBarProps {
  segments: ContributionSegment[];
  height?: number;
}

export function ContributionBar({ segments, height = 48 }: ContributionBarProps) {
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  if (total === 0) {
    return (
      <div
        className="rounded text-xs text-center py-3"
        style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
      >
        No contribution data
      </div>
    );
  }

  // Single row of stacked bars — one data point per segment
  const data = [Object.fromEntries(segments.map((s) => [s.label, s.value]))];

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" barSize={height - 8} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <XAxis type="number" hide domain={[0, total]} />
          <Tooltip
            contentStyle={{
              background: "#1f2937",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "6px",
              fontSize: "12px",
              color: "#f9fafb",
            }}
            formatter={(value, name) => {
              const numVal = typeof value === "number" ? value : 0;
              const pct = total > 0 ? ((numVal / total) * 100).toFixed(1) : "0";
              return [`${numVal.toFixed(0)} units (${pct}%)`, name];
            }}
          />
          {segments.map((seg) => (
            <Bar key={seg.label} dataKey={seg.label} stackId="a" radius={0}>
              <Cell fill={seg.color} />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
        {segments
          .filter((s) => s.value > 0)
          .map((s) => (
            <span key={s.label} className="flex items-center gap-1 text-xs font-mono">
              <span
                className="inline-block w-2 h-2 rounded-sm"
                style={{ background: s.color }}
              />
              <span style={{ color: "var(--text-muted)" }}>
                {s.label}
              </span>
              <span style={{ color: "var(--text-secondary)" }}>
                {total > 0 ? ((s.value / total) * 100).toFixed(0) : 0}%
              </span>
            </span>
          ))}
      </div>
    </div>
  );
}
