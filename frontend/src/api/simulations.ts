import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export interface SimulationRunOut {
  id: string;
  name: string;
  description: string | null;
  status: "draft" | "computed";
  snapshot_date: string;
  created_by: string;
  created_at: string;
}

export interface SimulationMoveOut {
  id: string;
  simulation_run_id: string;
  employee_id: string;
  from_team_id: string;
  to_team_id: string;
  allocation_pct_change: number;
  notes: string | null;
}

export interface SimulationOutcomeOut {
  id: string;
  simulation_run_id: string;
  employee_id: string;
  metric_name: string;
  baseline_value: number | null;
  simulated_value: number;
  delta: number;
  team_scope_id: string | null;
}

export interface SimulationCreateIn {
  name: string;
  description?: string;
  snapshot_date: string;
}

export interface SimulationMoveIn {
  employee_id: string;
  from_team_id: string;
  to_team_id: string;
  allocation_pct_change?: number;
  notes?: string;
}

export function useCreateSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SimulationCreateIn) =>
      api.post<SimulationRunOut>("/simulations/", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulations"] });
    },
  });
}

export function useAddMove(simId: string) {
  return useMutation({
    mutationFn: (body: SimulationMoveIn) =>
      api.post<SimulationMoveOut>(`/simulations/${simId}/moves`, body).then((r) => r.data),
  });
}

export function useComputeSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) =>
      api.post<SimulationRunOut>(`/simulations/${simId}/compute`).then((r) => r.data),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: ["simulation", simId, "outcomes"] });
    },
  });
}

export function useSimulationOutcomes(simId: string | null) {
  return useQuery<SimulationOutcomeOut[]>({
    queryKey: ["simulation", simId, "outcomes"],
    queryFn: () =>
      api.get(`/simulations/${simId}/outcomes`).then((r) => r.data),
    enabled: !!simId,
  });
}
