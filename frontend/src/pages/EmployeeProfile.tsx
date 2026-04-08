import { useParams, useSearchParams } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { MetricCard } from "@/components/MetricCard";
import { TimeseriesChart } from "@/components/TimeseriesChart";
import { RiskBadge } from "@/components/RiskBadge";
import { AuditGate } from "@/components/AuditGate";
import { useEmployeeTimeline, useEmployeeInsights, type EmployeeProfileOut } from "@/api/employees";
import { today } from "@/lib/utils";

interface ProfileContentProps {
  profile: EmployeeProfileOut;
  asOf: string;
}

function deltaCell(value: number | null) {
  if (value === null) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const color = value < 0 ? "#ef4444" : "#10b981";
  const arrow = value < 0 ? "▼" : "▲";
  return (
    <span className="font-mono text-xs" style={{ color }}>
      {arrow} {Math.abs(value).toFixed(2)}
    </span>
  );
}

function ProfileContent({ profile, asOf }: ProfileContentProps) {
  const fromDate = (() => {
    const d = new Date(asOf + "T00:00:00");
    d.setDate(d.getDate() - 89);
    return d.toISOString().slice(0, 10);
  })();

  const timeline = useEmployeeTimeline(profile.employee_id, fromDate, asOf);
  const insights = useEmployeeInsights(profile.employee_id, asOf);

  const timelineData = (timeline.data ?? []).map((d) => ({
    ...d,
    date: d.date_key.slice(5), // MM-DD
  }));

  const timelineLines = [
    { key: "contribution_units", color: "#00d4ff", label: "Contribution Units" },
    { key: "meeting_count", color: "#f59e0b", label: "Meetings" },
  ];

  const baselineRows = [
    { label: "Commits (30d)", value: profile.commits_30d, selfDelta: profile.commits_30d_vs_self_baseline, roleDelta: profile.commits_30d_vs_role_baseline },
    { label: "PRs merged (30d)", value: profile.prs_merged_30d, selfDelta: null, roleDelta: null },
    { label: "Meeting load (hrs)", value: profile.meeting_load_hours_30d, selfDelta: null, roleDelta: null },
    { label: "Collab breadth", value: profile.collaboration_breadth_30d, selfDelta: null, roleDelta: null },
    { label: "Experiments (30d)", value: profile.experiment_runs_30d, selfDelta: null, roleDelta: null },
  ];

  return (
    <div>
      {/* Personal header */}
      <div className="flex items-start gap-4 mb-6">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
          style={{ background: "var(--bg-elevated)", color: "var(--accent-cyan)" }}
        >
          {profile.full_name.charAt(0)}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
              {profile.full_name}
            </h1>
            {profile.archetype_label && (
              <span
                className="text-xs px-2 py-0.5 rounded font-mono"
                style={{ background: "rgba(0,212,255,0.12)", color: "var(--accent-cyan)", border: "1px solid rgba(0,212,255,0.3)" }}
              >
                {profile.archetype_label}
              </span>
            )}
          </div>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
            {profile.role_title} · {profile.role_family} · {profile.job_level}
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            {profile.team_name} · as of {profile.snapshot_date}
          </p>
        </div>
      </div>

      {/* 5 core metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <MetricCard label="Underutil" value={Number(profile.underutilization_score)} format="score" />
        <MetricCard label="Overload" value={Number(profile.overload_score)} format="score" />
        <MetricCard label="Disengagement" value={Number(profile.disengagement_risk_score)} format="score" />
        <MetricCard label="Skill Util" value={Number(profile.skill_utilization_score)} format="score" />
        <MetricCard label="Glue Person" value={Number(profile.glue_person_score)} format="score" />
      </div>

      {/* Timeline chart */}
      <div
        className="rounded-lg p-4 mb-6"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
      >
        <div className="text-xs uppercase tracking-widest mb-3" style={{ color: "var(--text-muted)" }}>
          90-Day Activity
        </div>
        {timeline.isLoading ? (
          <div className="h-52 animate-pulse rounded" style={{ background: "var(--bg-elevated)" }} />
        ) : timelineData.length > 0 ? (
          <TimeseriesChart data={timelineData} lines={timelineLines} xKey="date" height={200} />
        ) : (
          <div className="h-52 flex items-center justify-center text-sm" style={{ color: "var(--text-muted)" }}>
            No activity data available.
          </div>
        )}
      </div>

      {/* Baseline comparison + Insights side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Baseline table */}
        <div
          className="rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
        >
          <div
            className="px-4 py-3 text-xs uppercase tracking-widest"
            style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
          >
            Activity vs Baselines
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Metric", "Value", "vs Self", "vs Role"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs" style={{ color: "var(--text-muted)" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {baselineRows.map((row) => (
                <tr key={row.label} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="px-4 py-2.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                    {row.label}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "var(--text-primary)" }}>
                    {typeof row.value === "number" ? row.value.toFixed(1) : row.value}
                  </td>
                  <td className="px-4 py-2.5">{deltaCell(row.selfDelta)}</td>
                  <td className="px-4 py-2.5">{deltaCell(row.roleDelta)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Insights */}
        <div
          className="rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
        >
          <div
            className="px-4 py-3 text-xs uppercase tracking-widest"
            style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
          >
            Insights
          </div>
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {insights.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-4 py-3 animate-pulse flex gap-3">
                  <div className="h-4 w-12 rounded" style={{ background: "var(--bg-elevated)" }} />
                  <div className="h-4 flex-1 rounded" style={{ background: "var(--bg-elevated)" }} />
                </div>
              ))
            ) : (insights.data ?? []).length === 0 ? (
              <div className="px-4 py-6 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                No insights for this employee.
              </div>
            ) : (
              (insights.data ?? []).map((ins) => (
                <div key={ins.id} className="px-4 py-3 flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <RiskBadge severity={ins.severity} />
                    <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                      {ins.title}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {ins.insight_description}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function EmployeeProfile() {
  const { id: employeeId = "" } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const asOf = searchParams.get("as_of") ?? today();

  function handleDateChange(date: string) {
    setSearchParams((prev) => { prev.set("as_of", date); return prev; });
  }

  return (
    <Shell asOf={asOf} onDateChange={handleDateChange}>
      <AuditGate employeeId={employeeId} asOf={asOf}>
        {(profile) => <ProfileContent profile={profile} asOf={asOf} />}
      </AuditGate>
    </Shell>
  );
}
