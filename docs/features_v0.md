# WSIP Feature Specification v0

**Role**: DS + PM
**Sprint**: S1
**Status**: Draft — to be validated against synthetic data in S4

---

## Feature Store Overview

All features are computed per `(employee_id, snapshot_date)` and stored in `employee_feature_snapshots`.
Three rolling windows: **7d** (early warning), **30d** (primary signal), **90d** (baseline anchor).

---

## Rolling Window Features

### Code signals

| Feature | Window | Source table | Notes |
|---|---|---|---|
| `commits_30d` | 30d | `git_commit_events` | raw count |
| `prs_opened_30d` | 30d | `pull_request_events` | |
| `prs_merged_30d` | 30d | `pull_request_events` | status = 'merged' |
| `review_participation_30d` | 30d | `code_review_events` | reviews given / (prs merged in team) |

### Research signals

| Feature | Window | Source table |
|---|---|---|
| `experiment_runs_30d` | 30d | `experiment_run_events` |
| `experiment_success_rate_30d` | 30d | `experiment_run_events` | status='success' / total |
| `benchmark_improvement_avg_30d` | 30d | `experiment_run_events` | avg(benchmark_delta) |
| `research_artifacts_30d` | 30d | `research_artifact_events` | |
| `gpu_hours_30d` | 30d | `experiment_run_events` | sum(gpu_hours) |

### Documentation / knowledge signals

| Feature | Window | Source table |
|---|---|---|
| `doc_contribution_30d` | 30d | `document_events` | (created + edited) / working_days |
| `docs_approved_30d` | 30d | `document_events` | approval_state='approved' |

### Execution signals

| Feature | Window | Source table |
|---|---|---|
| `task_completion_rate_30d` | 30d | `task_events` | completed / (created + assigned) |
| `task_cycle_time_median_30d` | 30d | `task_events` | median(actual_hours) for completed tasks |
| `tasks_blocked_30d` | 30d | `task_events` | event_type='blocked' count |

### Collaboration / network signals

| Feature | Window | Source table |
|---|---|---|
| `collaboration_breadth_30d` | 30d | `interactions` | distinct `to_employee_id` count |
| `collaboration_centrality_30d` | 30d | `interactions` | betweenness centrality proxy (degree / team_size) |
| `cross_team_interaction_rate_30d` | 30d | `interactions` | edges to other teams / total edges |
| `chat_messages_sent_30d` | 30d | `chat_metadata_events` | |

### Meeting / load signals

| Feature | Window | Source table |
|---|---|---|
| `meeting_load_hours_30d` | 30d | `meeting_events` | sum(duration_minutes) / 60 |
| `meeting_count_30d` | 30d | `meeting_events` | |
| `avg_attendee_count_30d` | 30d | `meeting_events` | avg(attendee_count) |

### Activity drop / early warning

| Feature | Definition |
|---|---|
| `activity_drop_14d` | `1 - (rolling_14d_activity / baseline_activity_90d)` clamped [0,1] |
| `activity_drop_30d` | `1 - (rolling_30d_activity / baseline_activity_60_90d)` clamped [0,1] |
| `volatility_score_30d` | stddev(daily_activity_score_30d) / mean — burstiness proxy |

---

## Baseline Definitions

### Self-baseline

`baseline_activity = median(daily_activity_score over [snapshot_date - 90d, snapshot_date - 31d])`

- Minimum 20 data points required; otherwise baseline = NULL (no comparison)
- Used for `activity_drop_*` features and individual trend detection

### Role-baseline (cohort)

`cohort = (role_family, job_level)` — e.g., ("research", "L5")

`role_baseline_value = median(feature_value) across all active employees in same cohort, same snapshot_date`

- Used for `*_vs_role_baseline` comparison columns
- Cohort must have ≥ 5 members; otherwise fall back to `role_family` only

---

## Normalization Formula

All scores are normalized to [0, 1] before being written to metric columns:

```
normalized = clamp01((raw_value - p10_cohort) / (p90_cohort - p10_cohort))
```

Where:
- `p10_cohort` = 10th percentile of that feature across the cohort on `snapshot_date`
- `p90_cohort` = 90th percentile
- If `p90 == p10`: normalized = 0.5 (avoid division by zero)
- `clamp01(x) = max(0.0, min(1.0, x))`

---

## Activity Score (Role-Aware)

Used as the primary input to `activity_drop_*` features.

```
activity_score_day =
  w_code(role_family)     * f_code(commits, prs_merged, reviews_given)
+ w_research(role_family) * f_research(experiment_runs, gpu_hours, benchmark_delta)
+ w_docs(role_family)     * f_docs(docs_created, docs_edited)
+ w_exec(role_family)     * f_exec(tasks_completed, task_cycle_time)
+ w_collab(role_family)   * f_collab(collaboration_edges, cross_team_rate)
```

### Role-family weight tables

| role_family | w_code | w_research | w_docs | w_exec | w_collab |
|---|---|---|---|---|---|
| `engineering` | 0.45 | 0.05 | 0.10 | 0.20 | 0.20 |
| `research` | 0.15 | 0.40 | 0.20 | 0.10 | 0.15 |
| `management` | 0.05 | 0.05 | 0.15 | 0.20 | 0.55 |
| `ops` | 0.10 | 0.05 | 0.20 | 0.40 | 0.25 |
| `design` | 0.05 | 0.10 | 0.35 | 0.25 | 0.25 |

Weights sum to 1.0 per row. Sub-functions `f_*` normalize each raw dimension to [0,1] before applying weights.

---

## Core Metric Formulas (preview — detailed in S4)

### Underutilization score

```
underutilization_score =
  0.30 * clamp01(activity_drop_30d)
+ 0.25 * clamp01(1 - project_allocation_utilization_score)
+ 0.20 * clamp01(1 - skill_utilization_score)
+ 0.15 * clamp01(1 - collaboration_breadth_norm)
+ 0.10 * clamp01(1 - knowledge_creation_score)
```

### Overload score

```
overload_score =
  0.35 * clamp01(meeting_load_norm)           # meeting_load_hours_30d / role_expected_max
+ 0.25 * clamp01(active_projects_norm)        # active projects / expected max
+ 0.20 * clamp01(tasks_blocked_rate_30d)      # blocked tasks / total tasks
+ 0.20 * clamp01(volatility_score_30d)        # burstiness
```

### Disengagement risk score

```
disengagement_risk_score =
  0.35 * clamp01(activity_drop_30d)
+ 0.25 * clamp01(activity_drop_14d)           # recent early warning
+ 0.20 * clamp01(1 - collaboration_breadth_norm)
+ 0.20 * clamp01(1 - cross_team_interaction_rate_30d)
```

### Skill utilization score

```
skill_utilization_score =
  mean(utilization_score per skill)             # from fact_employee_skill_signal
  weighted by confidence_score of each skill
```

### Glue person score

```
glue_person_score =
  0.40 * clamp01(collaboration_centrality_30d)
+ 0.35 * clamp01(cross_team_interaction_rate_30d)
+ 0.25 * clamp01(review_participation_30d)
```

---

## Open Questions (to resolve in S4)

- [ ] What is the "role_expected_max" for meeting load per `role_family`? (proposed: engineering=15h/30d, research=20h/30d, management=50h/30d)
- [ ] Minimum active days threshold before a snapshot is considered valid?
- [ ] How to handle employees on leave (activity near zero — should not trigger underutilization)?
