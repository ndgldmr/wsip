import { useState } from "react";
import { Plus, Zap } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import {
  useCreateSimulation,
  useAddMove,
  useComputeSimulation,
  useSimulationOutcomes,
  type SimulationRunOut,
  type SimulationMoveOut,
} from "@/api/simulations";
import { useOrgTeams } from "@/api/orgs";
import { useTeamMembers } from "@/api/teams";
import { today } from "@/lib/utils";

function deltaColor(delta: number): string {
  return delta < 0 ? "#10b981" : delta > 0 ? "#ef4444" : "#9ca3af";
}

function DeltaCell({ delta }: { delta: number }) {
  const color = deltaColor(delta);
  const sign = delta > 0 ? "+" : "";
  return (
    <span className="font-mono text-xs" style={{ color }}>
      {sign}{delta.toFixed(3)}
    </span>
  );
}

interface MoveBuilderProps {
  sim: SimulationRunOut;
  localMoves: SimulationMoveOut[];
  onMoveAdded: (move: SimulationMoveOut) => void;
  onCompute: () => void;
  computing: boolean;
}

function MoveBuilder({ sim, localMoves, onMoveAdded, onCompute, computing }: MoveBuilderProps) {
  const orgId = localStorage.getItem("wsip_org_id") ?? "";
  const snapshotDate = sim.snapshot_date;

  const [fromTeamId, setFromTeamId] = useState("");
  const [toTeamId, setToTeamId] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [allocation, setAllocation] = useState(0);
  const [notes, setNotes] = useState("");

  const teams = useOrgTeams(orgId, snapshotDate);
  const fromMembers = useTeamMembers(fromTeamId, snapshotDate);
  const addMove = useAddMove(sim.id);

  async function handleAddMove() {
    if (!fromTeamId || !toTeamId || !employeeId) return;
    const move = await addMove.mutateAsync({
      employee_id: employeeId,
      from_team_id: fromTeamId,
      to_team_id: toTeamId,
      allocation_pct_change: allocation,
      notes: notes || undefined,
    });
    onMoveAdded(move);
    setEmployeeId("");
    setNotes("");
  }

  const inputStyle = {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
    color: "var(--text-primary)",
    borderRadius: "6px",
    fontSize: "13px",
    padding: "6px 10px",
    width: "100%",
  } as const;

  const labelStyle = {
    display: "flex",
    flexDirection: "column" as const,
    gap: "4px",
    fontSize: "11px",
    color: "var(--text-muted)",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  };

  return (
    <div className="flex flex-col gap-4">
      <div style={labelStyle}>
        From team
        <select value={fromTeamId} onChange={(e) => { setFromTeamId(e.target.value); setEmployeeId(""); }} style={inputStyle}>
          <option value="">Select team…</option>
          {(teams.data ?? []).map((t) => (
            <option key={t.team_id} value={t.team_id}>{t.team_name}</option>
          ))}
        </select>
      </div>

      <div style={labelStyle}>
        Employee
        <select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} style={inputStyle} disabled={!fromTeamId}>
          <option value="">Select employee…</option>
          {(fromMembers.data ?? []).map((m) => (
            <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>
          ))}
        </select>
      </div>

      <div style={labelStyle}>
        To team
        <select value={toTeamId} onChange={(e) => setToTeamId(e.target.value)} style={inputStyle}>
          <option value="">Select team…</option>
          {(teams.data ?? []).filter((t) => t.team_id !== fromTeamId).map((t) => (
            <option key={t.team_id} value={t.team_id}>{t.team_name}</option>
          ))}
        </select>
      </div>

      <div style={labelStyle}>
        Allocation % change
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={-100}
            max={100}
            step={5}
            value={allocation}
            onChange={(e) => setAllocation(Number(e.target.value))}
            className="flex-1"
            style={{ accentColor: "var(--accent-cyan)" }}
          />
          <span className="font-mono text-xs w-12 text-right" style={{ color: "var(--accent-cyan)" }}>
            {allocation > 0 ? "+" : ""}{allocation}%
          </span>
        </div>
      </div>

      <div style={labelStyle}>
        Notes (optional)
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          style={{ ...inputStyle, resize: "none" }}
          placeholder="Rationale…"
        />
      </div>

      <button
        onClick={handleAddMove}
        disabled={!fromTeamId || !toTeamId || !employeeId || addMove.isPending}
        className="flex items-center justify-center gap-2 px-3 py-2 rounded text-sm font-medium transition-opacity disabled:opacity-40"
        style={{ background: "rgba(0,212,255,0.12)", color: "var(--accent-cyan)", border: "1px solid rgba(0,212,255,0.3)" }}
      >
        <Plus size={14} />
        {addMove.isPending ? "Adding…" : "Add Move"}
      </button>

      {/* Added moves list */}
      {localMoves.length > 0 && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            Moves ({localMoves.length})
          </div>
          {localMoves.map((m, i) => (
            <div
              key={m.id}
              className="flex items-center gap-2 px-3 py-2 rounded text-xs"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
            >
              <span className="font-mono" style={{ color: "var(--text-muted)" }}>#{i + 1}</span>
              <span className="flex-1 truncate">{m.employee_id.slice(0, 8)}…</span>
              <span className="font-mono" style={{ color: m.allocation_pct_change >= 0 ? "#10b981" : "#ef4444" }}>
                {m.allocation_pct_change > 0 ? "+" : ""}{m.allocation_pct_change}%
              </span>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={onCompute}
        disabled={localMoves.length === 0 || computing}
        className="flex items-center justify-center gap-2 px-3 py-2 rounded text-sm font-medium mt-2 transition-opacity disabled:opacity-40"
        style={{ background: "var(--accent-cyan)", color: "var(--bg-default)" }}
      >
        <Zap size={14} />
        {computing ? "Computing…" : "Compute"}
      </button>
    </div>
  );
}

export function Simulation() {
  const [sim, setSim] = useState<SimulationRunOut | null>(null);
  const [localMoves, setLocalMoves] = useState<SimulationMoveOut[]>([]);
  const [name, setName] = useState("");
  const [snapshotDate, setSnapshotDate] = useState(today());

  const createSim = useCreateSimulation();
  const computeSim = useComputeSimulation();
  const outcomes = useSimulationOutcomes(sim?.status === "computed" ? sim.id : null);

  async function handleCreate() {
    if (!name.trim()) return;
    const result = await createSim.mutateAsync({ name: name.trim(), snapshot_date: snapshotDate });
    setSim(result);
  }

  async function handleCompute() {
    if (!sim) return;
    const result = await computeSim.mutateAsync(sim.id);
    setSim(result);
  }

  const inputStyle = {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
    color: "var(--text-primary)",
    borderRadius: "6px",
    fontSize: "13px",
    padding: "6px 10px",
  } as const;

  return (
    <Shell orgName="Simulation Sandbox">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        {/* Left: Builder */}
        <div
          className="rounded-lg p-5 flex flex-col gap-5"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
        >
          <div className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            {sim ? `Sim: ${sim.name}` : "New Simulation"}
          </div>

          {!sim ? (
            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-1.5 text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                Name
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q3 reorg"
                  style={{ ...inputStyle, width: "100%" }}
                />
              </label>
              <label className="flex flex-col gap-1.5 text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                Snapshot date
                <input
                  type="date"
                  value={snapshotDate}
                  onChange={(e) => setSnapshotDate(e.target.value)}
                  style={{ ...inputStyle, width: "100%", colorScheme: "dark" }}
                />
              </label>
              <button
                onClick={handleCreate}
                disabled={!name.trim() || createSim.isPending}
                className="px-4 py-2 rounded text-sm font-medium disabled:opacity-40 transition-opacity"
                style={{ background: "var(--accent-cyan)", color: "var(--bg-default)" }}
              >
                {createSim.isPending ? "Creating…" : "Create Simulation"}
              </button>
            </div>
          ) : sim.status === "draft" ? (
            <MoveBuilder
              sim={sim}
              localMoves={localMoves}
              onMoveAdded={(m) => setLocalMoves((prev) => [...prev, m])}
              onCompute={handleCompute}
              computing={computeSim.isPending}
            />
          ) : (
            <div className="text-sm" style={{ color: "var(--text-muted)" }}>
              <p>Status: <span style={{ color: "#10b981" }}>computed</span></p>
              <p className="mt-1">Snapshot: <span className="font-mono">{sim.snapshot_date}</span></p>
              <p className="mt-1">{localMoves.length} move(s) applied.</p>
            </div>
          )}
        </div>

        {/* Right: Outcomes */}
        <div
          className="lg:col-span-2 rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
        >
          <div
            className="px-4 py-3 text-xs uppercase tracking-widest"
            style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}
          >
            Outcomes
          </div>

          {!sim ? (
            <div className="flex items-center justify-center h-48 text-sm" style={{ color: "var(--text-muted)" }}>
              Create a simulation to see outcomes.
            </div>
          ) : sim.status !== "computed" ? (
            <div className="flex items-center justify-center h-48 text-sm" style={{ color: "var(--text-muted)" }}>
              Add moves and click Compute.
            </div>
          ) : outcomes.isLoading ? (
            <div className="p-6 animate-pulse flex flex-col gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-4 rounded" style={{ background: "var(--bg-elevated)" }} />
              ))}
            </div>
          ) : (outcomes.data ?? []).length === 0 ? (
            <div className="flex items-center justify-center h-48 text-sm" style={{ color: "var(--text-muted)" }}>
              No outcome data returned.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Metric", "Baseline", "Simulated", "Delta"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs" style={{ color: "var(--text-muted)" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {outcomes.data!.map((o) => (
                  <tr key={o.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                      {o.metric_name.replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                      {o.baseline_value !== null ? o.baseline_value.toFixed(3) : "—"}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "var(--text-primary)" }}>
                      {o.simulated_value.toFixed(3)}
                    </td>
                    <td className="px-4 py-2.5">
                      <DeltaCell delta={o.delta} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Shell>
  );
}
