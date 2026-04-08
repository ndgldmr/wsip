import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface TeamHealthOut {
  team_id: string;
  team_name: string;
  week_key: number;
  active_employee_count: number;
  underutilization_rate: number;
  overload_rate: number;
  silent_disengagement_rate: number;
  cross_team_collaboration_rate: number;
  burnout_risk_rate: number;
}

export interface EmployeeSummaryOut {
  employee_id: string;
  full_name: string;
  role_family: string;
  job_level: string;
}

export interface TeamTrendPointOut {
  week_key: number;
  underutilization_rate: number;
  overload_rate: number;
  silent_disengagement_rate: number;
  burnout_risk_rate: number;
}

export function useTeamHealth(teamId: string, weekKey: number) {
  return useQuery<TeamHealthOut>({
    queryKey: ["team", teamId, "health", weekKey],
    queryFn: () =>
      api.get(`/teams/${teamId}/health`, { params: { week_key: weekKey } }).then((r) => r.data),
    enabled: !!teamId && !!weekKey,
  });
}

export function useTeamMembers(teamId: string, asOf: string) {
  return useQuery<EmployeeSummaryOut[]>({
    queryKey: ["team", teamId, "members", asOf],
    queryFn: () =>
      api.get(`/teams/${teamId}/members`, { params: { as_of: asOf } }).then((r) => r.data),
    enabled: !!teamId && !!asOf,
  });
}

export function useTeamTrends(teamId: string, fromWeek: number, toWeek: number) {
  return useQuery<TeamTrendPointOut[]>({
    queryKey: ["team", teamId, "trends", fromWeek, toWeek],
    queryFn: () =>
      api
        .get(`/teams/${teamId}/trends`, { params: { from_week: fromWeek, to_week: toWeek } })
        .then((r) => r.data),
    enabled: !!teamId && !!fromWeek && !!toWeek,
  });
}
