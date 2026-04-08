import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { MetricCard, MetricCardSkeleton } from "@/components/MetricCard";
import { TimeseriesChart } from "@/components/TimeseriesChart";
import { RiskBadge } from "@/components/RiskBadge";
import { ContributionBar, type ContributionSegment } from "@/components/ContributionBar";
import { useTeamHealth, useTeamMembers, useTeamTrends } from "@/api/teams";
import { dateToWeekKey, weekRange, today } from "@/lib/utils";

function makeContributionSegments(members: { role_family: string }[]): ContributionSegment[] {
  // Approximate distribution based on role family — no separate breakdown endpoint
  const counts: Record<string, number> = {
    Engineering: 0,
    Research: 0,
    Design: 0,
    Operations: 0,
    Management: 0,
  };
  members.forEach((m) => {
    const key = m.role_family in counts ? m.role_family : "Operations";
    counts[key]++;
  });
  const map: ContributionSegment[] = [
    { label: "Engineering", value: counts.Engineering * 40, color: "#00d4ff" },
    { label: "Research", value: counts.Research * 30, color: "#f59e0b" },
    { label: "Design", value: counts.Design * 25, color: "#10b981" },
    { label: "Ops", value: counts.Operations * 20, color: "#8b5cf6" },
    { label: "Mgmt", value: counts.Management * 15, color: "#6b7280" },
  ];
  return map.filter((s) => s.value > 0);
}

export function TeamView() {
  const { id: teamId = "" } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const asOf = searchParams.get("as_of") ?? today();
  const weekKey = dateToWeekKey(asOf);
  const { fromWeek, toWeek } = weekRange(asOf, 12);

  const health = useTeamHealth(teamId, weekKey);
  const members = useTeamMembers(teamId, asOf);
  const trends = useTeamTrends(teamId, fromWeek, toWeek);

  function handleDateChange(date: string) {
    setSearchParams((prev) => { prev.set("as_of", date); return prev; });
  }

  const trendLines = [
    { key: "underutilization_rate", color: "#f59e0b", label: "Underutil" },
    { key: "overload_rate", color: "#ef4444", label: "Overload" },
    { key: "silent_disengagement_rate", color: "#8b5cf6", label: "Disengagement" },
    { key: "burnout_risk_rate", color: "#f97316", label: "Burnout Risk" },
  ];

  // Convert week_key int to readable label for x-axis
  const trendData = (trends.data ?? []).map((pt) => ({
    ...pt,
    week: String(pt.week_key).replace(/(\d{4})(\d{2})/, "W$2 '$1"),
  }));

  const segments = makeContributionSegments(members.data ?? []);

  return (
    <Shell
      orgName={health.data?.team_name ?? "—"}
      asOf={asOf}
      onDateChange={handleDateChange}
    >
      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        {health.isLoading
          ? Array.from({ length: 5 }).map((_, i) => <MetricCardSkeleton key={i} />)
          : health.data
          ? (
            <>
              <MetricCard label="Underutil" value={Number(health.data.underutilization_rate)} format="percent" />
              <MetricCard label="Overload" value={Number(health.data.overload_rate)} format="percent" />
              <MetricCard label="Disengagement" value={Number(health.data.silent_disengagement_rate)} format="percent" />
              <MetricCard label="Cross-Team Collab" value={Number(health.data.cross_team_collaboration_rate)} format="percent" />
              <MetricCard label="Burnout Risk" value={Number(health.data.burnout_risk_rate)} format="percent" />
            </>
          )
          : <div className="col-span-5 text-sm" style={{ color: "var(--text-muted)" }}>No health data for this week.</div>
        }
      </div>

      {/* Trends chart */}
      <div
        className="rounded-lg p-4 mb-6"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
      >
        <div className="text-xs uppercase tracking-widest mb-3" style={{ color: "var(--text-muted)" }}>
          12-Week Trends
        </div>
        {trends.isLoading ? (
          <div className="h-52 animate-pulse rounded" style={{ background: "var(--bg-elevated)" }} />
        ) : trendData.length > 0 ? (
          <TimeseriesChart data={trendData} lines={trendLines} xKey="week" height={220} />
        ) : (
          <div className="h-52 flex items-center justify-center text-sm" style={{ color: "var(--text-muted)" }}>
            No trend data available.
          </div>
        )}
      </div>

      {/* Members + ContributionBar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Member table */}
        <div
          className="lg:col-span-2 rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
        >
          <div
            className="px-4 py-3 text-xs uppercase tracking-widest"
            style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
          >
            Members · {members.data?.length ?? "—"}
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Name", "Role", "Level", "Risk"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs" style={{ color: "var(--text-muted)" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {members.isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      {[140, 80, 48, 40].map((w, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-3 rounded animate-pulse" style={{ background: "var(--bg-elevated)", width: w }} />
                        </td>
                      ))}
                    </tr>
                  ))
                : (members.data ?? []).length === 0
                ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                      No members on this team.
                    </td>
                  </tr>
                )
                : (members.data ?? []).map((emp) => (
                    <tr
                      key={emp.employee_id}
                      className="cursor-pointer transition-colors"
                      style={{ borderTop: "1px solid var(--border)" }}
                      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--bg-elevated)")}
                      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "")}
                      onClick={() => navigate(`/employees/${emp.employee_id}?as_of=${asOf}`)}
                    >
                      <td className="px-4 py-3 font-medium" style={{ color: "var(--text-primary)" }}>
                        {emp.full_name}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>
                        {emp.role_family}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                        {emp.job_level}
                      </td>
                      <td className="px-4 py-3">
                        <RiskBadge score={0.3} />
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {/* Contribution mix */}
        <div
          className="rounded-lg p-4"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
        >
          <div className="text-xs uppercase tracking-widest mb-3" style={{ color: "var(--text-muted)" }}>
            Team Composition Mix
          </div>
          <ContributionBar segments={segments} height={56} />
        </div>
      </div>
    </Shell>
  );
}
