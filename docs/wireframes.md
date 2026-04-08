# WSIP Wireframes — Sprint 8 Pages

UI theme: cockpit dark (#0a0e17 bg, #00d4ff cyan accent, mono font for numbers).
All pages are nested inside the Shell (fixed sidebar + top bar).

---

## Team View  `/teams/:id`

```
┌─ Shell ──────────────────────────────────────────────────────┐
│ [← Back to Org]   Alpha Engineering        Week: 2025-W14 ▾  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────┐ │
│  │ Underutil   │ │ Overload    │ │ Disengagement│ │Burnout│ │
│  │  23.4%  ●  │ │  41.2%  ◆  │ │   18.1%  ●  │ │ 9.3% │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────┘ │
│                                                              │
│  ┌─ Trend (12 weeks) ─────────────────────────────────────┐ │
│  │  AreaChart: underutil / overload / disengagement lines │ │
│  │  x-axis: YYYYWW labels, y-axis: 0–100%                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Members ─────────────────────────────────────────────┐  │
│  │  Name          Role Family    Level   Overload  Risk  │  │
│  │  Alice Chen    Engineering    IC4     68.2%     Med   │  │
│  │  Bob Ramos     Research       IC3     22.1%     Low   │  │
│  │  ...                                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Data sources:**
- `GET /teams/{id}/health?week_key=YYYYWW` → 4 MetricCards
- `GET /teams/{id}/trends?from_week=…&to_week=…` → TimeseriesChart
- `GET /teams/{id}/members?as_of=…` → members table with per-employee scores from feature store

---

## Employee Profile  `/employees/:id`  *(RBAC: admin | hrbp | own manager)*

```
┌─ Shell ──────────────────────────────────────────────────────┐
│ Alice Chen  ·  IC4 Engineering  ·  Alpha Eng                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Identity ────────┐  ┌─ Archetype ───────────────────┐   │
│  │ Role: Sr. Engineer│  │  ◈  SUSTAINER                 │   │
│  │ Level: IC4        │  │  Steady contributor, collab   │   │
│  │ Joined: 2021-03   │  │  breadth above baseline       │   │
│  └───────────────────┘  └───────────────────────────────┘   │
│                                                              │
│  ┌─ 5 Scores ────────────────────────────────────────────┐  │
│  │  Underutil 0.12 ●  Overload 0.61 ◆  Disengagement 0.08│  │
│  │  Skill Util 0.74 ●  Glue Score 0.81 ●                 │  │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ 30d Activity ─────────────────────────────────────────┐ │
│  │  Commits: 47  (vs self: +12%)  (vs role: +5%)          │ │
│  │  PRs merged: 8   Meetings: 34h   Collab breadth: 9     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Activity heatmap (90d) ──────────────────────────────┐  │
│  │  [GitHub-style day grid, colored by contribution_units]│  │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Insights for this employee ──────────────────────────┐  │
│  │  ◆ HIGH  Overload risk: meeting load 2.1× role avg    │  │
│  │  ● MED   Glue dependency: only cross-team connector   │  │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**RBAC gate:** 403 → "You do not have permission to view individual employee data."
**Data sources:**
- `GET /employees/{id}/profile?as_of=…` → scores + 30d features + archetype
- `GET /employees/{id}/activity?from_date=…&to_date=…` → heatmap
- `GET /insights?scope=employee&scope_id={id}&as_of=…` → insight cards

---

## Recommendations Triage  `/recommendations`

```
┌─ Shell ──────────────────────────────────────────────────────┐
│ Recommendations                              Filter: ALL ▾   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Filter bar ─────────────────────────────────────────┐   │
│  │  Status: [Pending ▾]  Priority: [All ▾]  Scope: [All]│   │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Recommendation card ─────────────────────────────────┐  │
│  │  ◆ P1 · REBALANCE_WORKLOAD · Team: Alpha Engineering  │  │
│  │  "Move 20% of Alice Chen's meetings to async formats"  │  │
│  │  Linked insight: Overload risk (confidence: 0.91)      │  │
│  │                             [Accept]  [Dismiss]        │  │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Recommendation card ─────────────────────────────────┐  │
│  │  ● P2 · KNOWLEDGE_TRANSFER · Org: Acme Corp           │  │
│  │  "Document Bob Ramos's domain expertise (glue risk)"   │  │
│  │  Linked insight: Single-point dependency (conf: 0.84)  │  │
│  │                             [Accept]  [Dismiss]        │  │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Accept flow:** `PATCH /recommendations/{id}/accept` → optimistic UI update, refetch.
**Data sources:**
- `GET /recommendations?as_of=…&accepted_flag=false&priority=…` → card list
- Each card expands to show the linked insight detail

---

## Simulation Sandbox  `/simulations`

```
┌─ Shell ──────────────────────────────────────────────────────┐
│ Simulation Sandbox                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ New simulation ────────────────────────────────────┐    │
│  │  Name: [Q3 reorg scenario          ]                │    │
│  │  Snapshot date: [2025-04-01 ▾]    [Create Run]      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─ Moves ──────────────────────────────────────────────┐   │
│  │  Employee      From Team      To Team    Alloc Δ     │   │
│  │  Alice Chen    Alpha Eng  →   Beta Ops   +0%  [✕]    │   │
│  │  [+ Add move]                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Outcomes (after running) ───────────────────────────┐   │
│  │  Metric            Baseline   Simulated   Δ          │   │
│  │  Alice overload    0.61       0.38        -0.23 ↓●   │   │
│  │  Alpha Eng overload 0.41      0.28        -0.13 ↓●   │   │
│  │  Beta Ops overload  0.22      0.31        +0.09 ↑◆   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                [Run Simulation]              │
└──────────────────────────────────────────────────────────────┘
```

**Flow:**
1. `POST /simulations/runs` → create run, get `run_id`
2. `POST /simulations/runs/{run_id}/moves` (one per move) → add moves
3. `POST /simulations/runs/{run_id}/execute` → trigger ML scoring
4. `GET /simulations/runs/{run_id}/outcomes` → poll until status=complete, render table

---

## Cross-page Navigation Notes

- Team table rows in OrgOverview link to `/teams/:id`
- Member rows in Team View link to `/employees/:id` (RBAC check client-side; server returns 403)
- Insight cards link to `/recommendations?insight_id=:id` (pre-filtered)
- Simulation "Add move" employee picker calls `GET /teams/{id}/members` per selected team
