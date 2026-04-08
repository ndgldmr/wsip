import { useState, useMemo, useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { useOrgOverview, type TeamSummary } from "@/api/orgs";
import { isAccessDenied } from "@/api/errors";
import { MetricCard, MetricCardSkeleton } from "@/components/MetricCard";
import { RiskBadge } from "@/components/RiskBadge";
import { Shell } from "@/components/layout/Shell";
import { SCORE_COLOR } from "@/lib/theme";
import { today } from "@/lib/utils";
import { ShieldOff, ChevronUp, ChevronDown } from "lucide-react";

type SortKey = "team_name" | "active_employee_count" | "underutilization_rate" | "overload_rate";
type SortDir = "asc" | "desc";

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ChevronUp size={12} style={{ color: "var(--text-muted)" }} />;
  return dir === "asc" ? (
    <ChevronUp size={12} style={{ color: "var(--accent-cyan)" }} />
  ) : (
    <ChevronDown size={12} style={{ color: "var(--accent-cyan)" }} />
  );
}

export function OrgOverview() {
  const { id: orgId = "" } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const asOf = searchParams.get("as_of") ?? today();

  const [sortKey, setSortKey] = useState<SortKey>("team_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const { data, isLoading, error } = useOrgOverview(orgId, asOf);

  // Persist org context for Simulation page
  useEffect(() => {
    if (orgId) localStorage.setItem("wsip_org_id", orgId);
  }, [orgId]);

  function handleDateChange(date: string) {
    setSearchParams((prev) => {
      prev.set("as_of", date);
      return prev;
    });
  }

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "team_name" ? "asc" : "desc");
    }
  }

  const sortedTeams = useMemo<TeamSummary[]>(() => {
    if (!data?.teams) return [];
    return [...data.teams].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data?.teams, sortKey, sortDir]);

  // Access denied state
  if (isAccessDenied(error)) {
    return (
      <Shell orgName="—" asOf={asOf} onDateChange={handleDateChange}>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <ShieldOff size={40} style={{ color: "var(--accent-red)" }} />
          <div className="text-center">
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
              Access Denied
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              Your token does not have permission to view this resource.
            </p>
          </div>
        </div>
      </Shell>
    );
  }

  const COLS: { key: SortKey; label: string }[] = [
    { key: "team_name", label: "Team" },
    { key: "active_employee_count", label: "Members" },
    { key: "underutilization_rate", label: "Underutil %" },
    { key: "overload_rate", label: "Overload %" },
  ];

  return (
    <Shell orgName={data?.org_name ?? "—"} asOf={asOf} onDateChange={handleDateChange}>
      {/* Metric cards row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : data ? (
          <>
            <MetricCard
              label="Underutilization"
              value={Number(data.underutilization_rate)}
              format="percent"
            />
            <MetricCard
              label="Overload"
              value={Number(data.overload_rate)}
              format="percent"
            />
            <MetricCard
              label="Disengagement Risk"
              value={Number(data.disengagement_risk_rate)}
              format="percent"
            />
            <MetricCard
              label="Contribution Units"
              value={Number(data.total_contribution_units)}
              format="count"
            />
          </>
        ) : null}
      </div>

      {/* Team table */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
      >
        <div
          className="px-4 py-3 text-xs uppercase tracking-widest"
          style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
        >
          Teams · {data?.teams.length ?? "—"} total
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {COLS.map(({ key, label }) => (
                <th
                  key={key}
                  className="px-4 py-2 text-left cursor-pointer select-none"
                  style={{ color: "var(--text-muted)" }}
                  onClick={() => handleSort(key)}
                >
                  <span className="flex items-center gap-1">
                    {label}
                    <SortIcon active={sortKey === key} dir={sortDir} />
                  </span>
                </th>
              ))}
              <th className="px-4 py-2 text-left" style={{ color: "var(--text-muted)" }}>
                Risk
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div
                          className="h-3 rounded animate-pulse"
                          style={{ background: "var(--bg-elevated)", width: j === 0 ? "120px" : "48px" }}
                        />
                      </td>
                    ))}
                  </tr>
                ))
              : sortedTeams.map((team) => {
                  const maxRisk = Math.max(team.underutilization_rate, team.overload_rate);
                  return (
                    <tr
                      key={team.team_id}
                      className="cursor-pointer transition-colors"
                      style={{ borderTop: "1px solid var(--border)" }}
                      onClick={() => navigate(`/teams/${team.team_id}?as_of=${asOf}`)}
                      onMouseEnter={(e) =>
                        ((e.currentTarget as HTMLElement).style.background = "var(--bg-elevated)")
                      }
                      onMouseLeave={(e) =>
                        ((e.currentTarget as HTMLElement).style.background = "")
                      }
                    >
                      <td className="px-4 py-3 font-medium" style={{ color: "var(--text-primary)" }}>
                        {team.team_name}
                      </td>
                      <td className="px-4 py-3 font-mono" style={{ color: "var(--text-secondary)" }}>
                        {team.active_employee_count}
                      </td>
                      <td className="px-4 py-3 font-mono" style={{ color: SCORE_COLOR(team.underutilization_rate) }}>
                        {(team.underutilization_rate * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 font-mono" style={{ color: SCORE_COLOR(team.overload_rate) }}>
                        {(team.overload_rate * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-3">
                        <RiskBadge score={maxRisk} />
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
