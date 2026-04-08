import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export interface EmployeeProfileOut {
  employee_id: string;
  full_name: string;
  role_title: string;
  role_family: string;
  job_level: string;
  team_name: string;
  snapshot_date: string;
  underutilization_score: number;
  overload_score: number;
  disengagement_risk_score: number;
  skill_utilization_score: number;
  glue_person_score: number;
  commits_30d: number;
  prs_merged_30d: number;
  meeting_load_hours_30d: number;
  collaboration_breadth_30d: number;
  experiment_runs_30d: number;
  commits_30d_vs_self_baseline: number | null;
  commits_30d_vs_role_baseline: number | null;
  archetype_label: string | null;
}

export interface DailyActivityOut {
  date_key: string;
  commit_count: number;
  pr_opened_count: number;
  pr_merged_count: number;
  code_review_count: number;
  experiment_count: number;
  research_artifact_count: number;
  doc_event_count: number;
  meeting_count: number;
  meeting_minutes: number;
  chat_message_count: number;
  is_active: boolean;
  contribution_units: number;
}

export interface InsightOut {
  id: string;
  scope: string;
  scope_id: string;
  insight_type: string;
  snapshot_date: string;
  severity: "high" | "medium" | "low";
  title: string;
  insight_description: string;
  confidence: number;
  is_active: boolean;
}

export function useEmployeeProfile(employeeId: string, asOf: string) {
  return useQuery<EmployeeProfileOut>({
    queryKey: ["employee", employeeId, "profile", asOf],
    queryFn: () =>
      api
        .get(`/employees/${employeeId}/profile`, { params: { as_of: asOf } })
        .then((r) => r.data),
    enabled: !!employeeId && !!asOf,
    retry: false,
  });
}

export function useEmployeeTimeline(employeeId: string, fromDate: string, toDate: string) {
  return useQuery<DailyActivityOut[]>({
    queryKey: ["employee", employeeId, "timeline", fromDate, toDate],
    queryFn: () =>
      api
        .get(`/employees/${employeeId}/timeline`, {
          params: { from_date: fromDate, to_date: toDate },
        })
        .then((r) => r.data),
    enabled: !!employeeId && !!fromDate && !!toDate,
  });
}

export function useEmployeeInsights(employeeId: string, asOf: string) {
  return useQuery<InsightOut[]>({
    queryKey: ["employee", employeeId, "insights", asOf],
    queryFn: () =>
      api
        .get("/insights/", { params: { scope: "employee", scope_id: employeeId, as_of: asOf } })
        .then((r) => r.data),
    enabled: !!employeeId && !!asOf,
  });
}
