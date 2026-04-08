import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export interface RecommendationOut {
  id: string;
  insight_id: string;
  action_type: string;
  priority: number;
  target_scope: string;
  accepted_flag: boolean;
  accepted_at: string | null;
  accepted_by: string | null;
}

export interface RecommendationFilters {
  scope?: string;
  target_scope?: string;
  priority_min?: number;
  limit?: number;
}

export function useRecommendations(filters: RecommendationFilters = {}) {
  return useQuery<RecommendationOut[]>({
    queryKey: ["recommendations", filters],
    queryFn: () =>
      api
        .get("/recommendations/", {
          params: {
            ...(filters.scope && { scope: filters.scope }),
            ...(filters.target_scope && { target_scope: filters.target_scope }),
            priority_min: filters.priority_min ?? 0,
            limit: filters.limit ?? 100,
          },
        })
        .then((r) => r.data),
  });
}

export function useAcceptRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/recommendations/${id}/accept`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
}
