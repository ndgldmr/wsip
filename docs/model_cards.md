# WSIP Model Cards

> Living document. Describes the ML models used for archetype clustering, trajectory prediction, and simulation outcomes.

---

## 1. Archetype Clustering

**File**: `backend/ml/archetypes.py`
**Trigger**: `POST /admin/run_pipeline?run_ml=true` or called directly

### Algorithm
KMeans (`k=8`, sklearn `KMeans`, default `n_init=10`, `random_state=42`) fit on `StandardScaler`-normalized feature vectors for all employees on a given snapshot date.

### Feature Inputs (10 columns from `employee_feature_snapshots`)

| Feature | Description |
|---|---|
| `experiment_runs_30d` | Research/experiment activity count |
| `commits_30d` | Code commit volume |
| `meeting_load_hours_30d` | Total meeting hours |
| `collaboration_breadth_30d` | Unique collaborators count |
| `cross_team_interaction_rate_30d` | Fraction of interactions outside own team |
| `knowledge_creation_score` | Docs/artifacts created score |
| `activity_score_30d` | Composite 30-day activity |
| `glue_person_score` | Coordination/glue work estimate |
| `underutilization_score` | Signal of capacity underuse (0–1) |
| `overload_score` | Signal of overwork (0–1) |

### Archetype Labels
Assigned by inspecting which scaled centroid dimension is highest:

| Label | Dominant Signal |
|---|---|
| Research Pioneer | `experiment_runs_30d` |
| Glue Person | `glue_person_score` |
| Meeting Heavy | `meeting_load_hours_30d` |
| Knowledge Creator | `knowledge_creation_score` |
| Deep Contributor | `commits_30d` |
| Collaborator | `collaboration_breadth_30d` |
| Overloaded | `overload_score` |
| Underutilizer | `underutilization_score` |
| Balanced Performer | fallback (no dominant signal) |

### Outputs
Writes `employee_archetype_assignments` rows (DELETE+INSERT per snapshot date) and updates `employee_feature_snapshots.archetype_label`.

### Limitations
- Requires ≥ 1 employee with feature data on snapshot date; returns 0 rows otherwise.
- Labels are heuristic — dominant-dimension assignment does not imply the cluster is *only* that signal.
- No cross-date model persistence; clustering is refit from scratch each run.

---

## 2. Trajectory Prediction

**File**: `backend/ml/trajectory.py`
**Trigger**: `POST /admin/run_pipeline?run_ml=true`

### Algorithm
Two models trained jointly:
1. **LogisticRegression** — binary classification: will `disengagement_risk_score > 0.5` at `t + horizon_days`?
2. **Ridge regression** — continuous prediction: expected `impact_score` at `t + horizon_days`

Both models use `StandardScaler` normalization. Default `horizon_days=60`.

### Feature Inputs (9 columns)

| Feature | Description |
|---|---|
| `activity_score_30d` | 30-day activity composite |
| `commits_30d` | Code commits |
| `meeting_load_hours_30d` | Meeting hours |
| `collaboration_breadth_30d` | Unique collaborators |
| `cross_team_interaction_rate_30d` | Cross-team interaction ratio |
| `activity_score_90d` | 90-day activity composite |
| `glue_person_score` | Glue work estimate |
| `underutilization_score` | Underuse signal |
| `overload_score` | Overwork signal |

### Training Data
All historical `employee_feature_snapshots` pairs `(t, t+horizon)` across all employees. Minimum training set: **20 pairs**. Falls back to `confidence=0.5` and current scores when insufficient history.

### Outputs
Writes `employee_trajectory_predictions` rows (DELETE+INSERT per snapshot date):
- `predicted_risk_label`: `"high_risk"` | `"stable"`
- `predicted_impact_score`: float
- `confidence`: logistic regression probability (or 0.5 on fallback)
- `model_version`: `"wsip-0.1"`

### Limitations
- Cold-start: predictions degrade significantly with < 20 historical pairs (fallback activates).
- No temporal cross-validation; trained on all available history including the current date.
- Binary threshold (`0.5`) is not calibrated.

---

## 3. Simulation Engine

**File**: `backend/ml/simulation.py`
**Trigger**: `POST /simulations/{id}/compute`

### Approach
Deterministic rule-based re-weighting — no stochastic simulation, no Monte Carlo. Given a set of employee moves (from-team/project, to-team/project, allocation % change), the engine:

1. Loads `FactTeamWeeklyHealth` rows for the simulation's `snapshot_date`.
2. For each move, adjusts the moving employee's contribution allocation proportionally.
3. Recomputes team-level aggregate metrics (underutilization rate, overload rate, etc.) based on adjusted allocations.
4. Stores per-metric baseline vs simulated values in `simulation_outcomes`.

### Key Assumptions
- One move does not cascade into secondary effects (no network effects modeled).
- `allocation_pct_change` is applied linearly to contribution units.
- Team health metrics are assumed additively separable across employees.
- No time-series simulation; outcomes represent the snapshot state, not multi-period trajectories.

### Outputs
Writes `simulation_outcomes` rows per metric per team:
- `metric_name`: e.g. `underutilization_rate`, `overload_rate`
- `baseline_value`: value before moves
- `simulated_value`: value after moves
- `delta`: `simulated_value - baseline_value`

### Limitations
- Linear allocation model does not capture diminishing returns or specialization effects.
- Results are sensitive to the snapshot date — simulating off a stale snapshot may not reflect current state.
- Does not account for project dependencies or sequential staffing constraints.
