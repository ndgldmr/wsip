# WSIP KPI Definitions — Sprint 3 (Frozen)

> These definitions are authoritative for all Sprint 3 mart tables and API
> responses.  Any change requires updating both this document and `etl/config.py`
> / `etl/facts.py` together.

---

## Employee-Level (fact_employee_daily_activity)

### `is_active`

An employee is considered active on a given day if they produced at least one
signal in any of the 10 raw event tables (git commits, PRs, code reviews,
experiments, research artefacts, documents, tasks, meetings, chat, training)
for that UTC calendar day.

### `contribution_units`

A role-family-weighted sum of normalised work signals.  Produces a single
continuous score per employee per day.

**Component formulas:**

| Category | Formula | Notes |
|---|---|---|
| `code` | `(lines_added + lines_deleted) / 100 + files_changed / 10` | Normalises raw LOC |
| `research` | `experiment_count × compute_hours / 8 + research_artifact_count × 2` | Compute-hour normalised to 8 h workday |
| `documentation` | `doc_event_count + doc_word_count / 500` | ~500 words per meaningful doc unit |
| `collaboration` | `code_review_count + (meeting_minutes / 60) × 0.5` | Meeting time half-weighted |
| `strategic` | `0.0` | Placeholder — Sprint 4 |
| `impact` | `story_points_closed / 5` | Normalised to 5-point baseline |

**Weights by role_family** (from `etl/config.py`):

| role_family | code | research | documentation | collaboration | strategic | impact |
|---|---|---|---|---|---|---|
| engineering | 0.45 | 0.05 | 0.10 | 0.20 | 0.05 | 0.15 |
| research | 0.15 | 0.40 | 0.20 | 0.15 | 0.05 | 0.05 |
| management | 0.05 | 0.05 | 0.15 | 0.40 | 0.20 | 0.15 |
| ops | 0.10 | 0.05 | 0.25 | 0.30 | 0.20 | 0.10 |
| default | 0.20 | 0.15 | 0.20 | 0.25 | 0.10 | 0.10 |

---

## Team-Level Weekly (fact_team_weekly_health)

All rate columns are `Numeric(5,4)` fractions in **[0.0, 1.0]**, computed as:

```
rate = (employees meeting criterion in week) / (employees in team in week)
```

`week_key` format: `YYYYWW` using ISO week numbering (e.g. `202601` = ISO week 1 of 2026).

---

### `underutilization_rate`

Fraction of team members whose weekly **activity_score** is below the
25th-percentile of the team for that week.

```
activity_score = Σ(commit_count + experiment_count + research_artifact_count + doc_event_count)
                 over all days in the week
```

Computed with `PERCENTILE_CONT(0.25)` per team.  Employees below the p25
threshold are classified as underutilised for the week.

---

### `overload_rate`

Fraction of team members meeting **either** of:
- Total weekly `meeting_minutes > 300` (> 5 hours of meetings), OR
- Total weekly event count > 95th-percentile of the team (`PERCENTILE_CONT(0.95)`)

where event count aggregates all 10 signal types.

---

### `silent_disengagement_rate`

Fraction of team members with `is_active = false` on **3 or more days** in the
week.  Captures employees who are technically employed but producing no
observable signals — a leading indicator of voluntary attrition.

---

### `burnout_risk_rate`

Fraction of team members with **both**:
- `chat_after_hours_count ≥ 3` days in the week (consistent after-hours presence), AND
- Total weekly `meeting_minutes > 240` (> 4 hours of meetings)

Neither criterion alone is sufficient — the combination signals sustained
overextension.

---

### `cross_team_collaboration_rate`

**Set to `0.0` in Sprint 3.**  Defined as the fraction of team members with
at least one cross-team interaction signal in the week.  Implementation
deferred to Sprint 5 when `Interaction` table-based signals are aggregated.

---

### `avg_contribution_units` / `total_contribution_units`

- `avg_contribution_units` = mean of per-employee weekly `contribution_units`
- `total_contribution_units` = sum across the team

Both use the same `contribution_units` formula defined above.
