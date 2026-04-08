import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface TeamSummary {
  team_id: string;
  team_name: string;
  active_employee_count: number;
  underutilization_rate: number;
  overload_rate: number;
}

export interface OrgOverview {
  org_id: string;
  org_name: string;
  snapshot_date: string;
  active_employee_count: number;
  underutilization_rate: number;
  overload_rate: number;
  disengagement_risk_rate: number;
  total_contribution_units: number;
  teams: TeamSummary[];
}

export function useOrgOverview(orgId: string, asOf: string) {
  return useQuery<OrgOverview>({
    queryKey: ["org", orgId, "overview", asOf],
    queryFn: () =>
      api.get(`/orgs/${orgId}/overview`, { params: { as_of: asOf } }).then((r) => r.data),
    enabled: !!orgId && !!asOf,
  });
}

export function useOrgTeams(orgId: string, asOf: string) {
  return useQuery<TeamSummary[]>({
    queryKey: ["org", orgId, "teams", asOf],
    queryFn: () =>
      api.get(`/orgs/${orgId}/teams`, { params: { as_of: asOf } }).then((r) => r.data),
    enabled: !!orgId && !!asOf,
  });
}
