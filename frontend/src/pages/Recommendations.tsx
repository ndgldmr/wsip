import { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronRight } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { FilterBar, type RecommendationFilters } from "@/components/FilterBar";
import { useRecommendations, useAcceptRecommendation, type RecommendationOut } from "@/api/recommendations";

function priorityColor(p: number): string {
  return p > 0.7 ? "#ef4444" : p > 0.4 ? "#f59e0b" : "#10b981";
}

function RecommendationRow({ rec, onAccept }: { rec: RecommendationOut; onAccept: () => void }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="cursor-pointer transition-colors"
        style={{
          borderTop: "1px solid var(--border)",
          opacity: rec.accepted_flag ? 0.5 : 1,
        }}
        onClick={() => setExpanded((e) => !e)}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--bg-elevated)")}
        onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "")}
      >
        <td className="px-4 py-3 w-6">
          {expanded ? (
            <ChevronDown size={14} style={{ color: "var(--text-muted)" }} />
          ) : (
            <ChevronRight size={14} style={{ color: "var(--text-muted)" }} />
          )}
        </td>
        <td className="px-4 py-3 text-xs font-mono" style={{ color: "var(--text-secondary)" }}>
          {rec.target_scope ?? "—"}
        </td>
        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-primary)" }}>
          {rec.action_type.replace(/_/g, " ")}
        </td>
        <td className="px-4 py-3 font-mono text-xs" style={{ color: priorityColor(rec.priority) }}>
          {rec.priority.toFixed(2)}
        </td>
        <td className="px-4 py-3">
          {rec.accepted_flag ? (
            <CheckCircle2 size={16} style={{ color: "#10b981" }} />
          ) : null}
        </td>
      </tr>

      {expanded && (
        <tr style={{ borderTop: "1px solid var(--border)", background: "var(--bg-elevated)" }}>
          <td colSpan={5} className="px-6 py-4">
            <p className="text-xs mb-3" style={{ color: "var(--text-secondary)" }}>
              Insight ID: <span className="font-mono">{rec.insight_id}</span>
            </p>
            <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
              Target scope: <span style={{ color: "var(--text-secondary)" }}>{rec.target_scope}</span>
            </p>
            {!rec.accepted_flag && (
              <button
                onClick={(e) => { e.stopPropagation(); onAccept(); }}
                className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
                style={{
                  background: "rgba(0,212,255,0.12)",
                  color: "var(--accent-cyan)",
                  border: "1px solid rgba(0,212,255,0.3)",
                }}
              >
                Accept recommendation
              </button>
            )}
            {rec.accepted_flag && rec.accepted_at && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Accepted {new Date(rec.accepted_at).toLocaleDateString()}
                {rec.accepted_by ? ` by ${rec.accepted_by}` : ""}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export function Recommendations() {
  const [filters, setFilters] = useState<RecommendationFilters>({ scope: "", priority_min: 0 });
  const { data, isLoading } = useRecommendations({
    scope: filters.scope || undefined,
    priority_min: filters.priority_min,
    limit: 100,
  });
  const acceptMutation = useAcceptRecommendation();

  const sorted = [...(data ?? [])].sort((a, b) => b.priority - a.priority);

  return (
    <Shell orgName="Recommendations">
      <FilterBar onFiltersChange={setFilters} />

      <div
        className="rounded-lg overflow-hidden"
        style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
      >
        <div
          className="px-4 py-3 text-xs uppercase tracking-widest flex items-center justify-between"
          style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
        >
          <span>Recommendations · {data?.length ?? "—"} total</span>
          {data && (
            <span style={{ color: "#10b981" }}>
              {data.filter((r) => r.accepted_flag).length} accepted
            </span>
          )}
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <th className="w-6" />
              {["Scope", "Action", "Priority", "Status"].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-xs" style={{ color: "var(--text-muted)" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {[20, 80, 140, 48, 32].map((w, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 rounded animate-pulse" style={{ background: "var(--bg-elevated)", width: w }} />
                      </td>
                    ))}
                  </tr>
                ))
              : sorted.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                    No active recommendations.
                  </td>
                </tr>
              )
              : sorted.map((rec) => (
                  <RecommendationRow
                    key={rec.id}
                    rec={rec}
                    onAccept={() => acceptMutation.mutate(rec.id)}
                  />
                ))
            }
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
