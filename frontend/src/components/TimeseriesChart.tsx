import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface LineConfig {
  key: string;
  color: string;
  label: string;
}

interface TimeseriesChartProps {
  data: Record<string, unknown>[];
  lines: LineConfig[];
  xKey: string;
  height?: number;
}

export function TimeseriesChart({ data, lines, xKey, height = 220 }: TimeseriesChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <defs>
          {lines.map(({ key, color }) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor={color} stopOpacity={0.22} />
              <stop offset="90%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        <CartesianGrid
          strokeDasharray="2 4"
          stroke="rgba(0,216,255,0.05)"
          vertical={false}
        />

        <XAxis
          dataKey={xKey}
          tick={{ fill: "#27384f", fontSize: 10, fontFamily: "'Share Tech Mono', monospace" }}
          axisLine={false}
          tickLine={false}
          tickMargin={6}
        />
        <YAxis
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          tick={{ fill: "#27384f", fontSize: 10, fontFamily: "'Share Tech Mono', monospace" }}
          axisLine={false}
          tickLine={false}
          domain={[0, "auto"]}
        />

        <Tooltip
          contentStyle={{
            background: "#0b1120",
            border: "1px solid rgba(0,216,255,0.18)",
            borderRadius: "4px",
            fontSize: "11px",
            color: "#d8e8f8",
            boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
            fontFamily: "'Share Tech Mono', monospace",
          }}
          labelStyle={{ color: "#6e8fb0", marginBottom: "4px", fontSize: "10px" }}
          itemStyle={{ color: "#d8e8f8" }}
          formatter={(value, name) => {
            const numVal = typeof value === "number" ? value : 0;
            const strName = String(name);
            const line = lines.find((l) => l.key === strName);
            return [`${(numVal * 100).toFixed(1)}%`, line?.label ?? strName];
          }}
          cursor={{ stroke: "rgba(0,216,255,0.15)", strokeWidth: 1 }}
        />

        {lines.map(({ key, color }) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad-${key})`}
            dot={false}
            activeDot={{ r: 3, fill: color, strokeWidth: 0 }}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
