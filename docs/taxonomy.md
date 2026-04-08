# WSIP Insight & Recommendation Taxonomy

> Sprint 5 PM artifact. Defines the severity thresholds and recommendation action vocabulary used by the insight engine.

---

## Severity Levels

Severity is assigned per insight type based on the underlying metric score threshold.

| Severity | Meaning | Expected response SLA |
|----------|---------|-----------------------|
| **high** | Immediate attention warranted; metric signal is strong and persistent | Manager action within 1 week |
| **medium** | Elevated signal; worth monitoring and discussing in next 1:1 | Review within 2 weeks |
| **low** | Early indicator only; log for trend tracking | No action required yet |

### Thresholds by Insight Type

| Insight Type | Metric Column | Trigger Condition | `high` if | `medium` if |
|---|---|---|---|---|
| `underutilization` | `underutilization_score` | score > 0.65 | score > 0.80 | 0.65 < score ≤ 0.80 |
| `overload` | `overload_score` | score > 0.65 | score > 0.80 | 0.65 < score ≤ 0.80 |
| `disengagement_risk` | `disengagement_risk_score` | score > 0.60 | score > 0.75 | 0.60 < score ≤ 0.75 |
| `skill_underutilization` | `skill_utilization_score` | score < 0.40 | score < 0.20 | 0.20 ≤ score < 0.40 |
| `glue_person_identified` | `glue_person_score` | score > 0.70 | score > 0.85 | 0.70 < score ≤ 0.85 |

> All scores are in [0.0, 1.0]. For `skill_underutilization`, a **lower** `skill_utilization_score` means worse utilization — the threshold logic is inverted.

---

## Recommendation Action Taxonomy

Each insight generates up to two recommendations, each targeting an owner role.

| Insight Type | Action Type | Target Owner | Description |
|---|---|---|---|
| `underutilization` | `manager_checkin` | `manager` | Schedule a 1:1 to understand capacity and engagement blockers |
| `underutilization` | `reassignment_candidate` | `hrbp` | Flag employee as candidate for project or team reassignment |
| `overload` | `workload_rebalance` | `manager` | Review and redistribute workload across team |
| `overload` | `meeting_audit` | `hrbp` | Audit recurring meeting load; identify meetings to decline or delegate |
| `disengagement_risk` | `manager_checkin` | `manager` | Proactive 1:1 focused on motivation, blockers, and career trajectory |
| `disengagement_risk` | `career_path_review` | `hrbp` | Initiate a career path or role clarity conversation |
| `skill_underutilization` | `skill_deployment` | `manager` | Identify upcoming work that draws on employee's underused skills |
| `skill_underutilization` | `project_rotation` | `hrbp` | Consider rotating employee to a project better matched to their skill profile |
| `glue_person_identified` | `succession_planning` | `hrbp` | Document key knowledge dependencies; identify a backup |
| `glue_person_identified` | `knowledge_transfer` | `admin` | Schedule knowledge-sharing sessions to reduce single-point-of-failure risk |

### Owner Role Definitions

| Target Scope | Who acts | Access required |
|---|---|---|
| `manager` | Direct line manager of the employee | `manager` role |
| `hrbp` | HR Business Partner assigned to the team | `hrbp` role |
| `admin` | Platform administrator or senior leadership | `admin` role |

---

## Priority Calculation

Recommendation priority is computed as:

```
priority = confidence × severity_weight
```

Where:
- `confidence` is the insight engine's confidence score ∈ [0.0, 1.0]
- `severity_weight`: `high` → 1.0 · `medium` → 0.7 · `low` → 0.4

Higher priority recommendations surface first in `GET /recommendations` (ordered `DESC`).

---

## Idempotency

The insight engine is idempotent: running `POST /admin/run_pipeline` twice for the same `snapshot_date` produces the same insight and recommendation rows. Existing rows are deleted and rewritten on each run. The `accepted_flag` on recommendations is **not** preserved across re-runs — if a manager accepted a recommendation for a given snapshot date and the pipeline re-runs for that date, the recommendation resets to unaccepted.
