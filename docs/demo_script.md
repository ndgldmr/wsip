# WSIP Demo Script

End-to-end walkthrough from a clean clone. Takes ~10 minutes.

---

## Prerequisites

- Docker + Docker Compose
- Python 3.12, Node LTS
- `pip install -r backend/requirements.txt` (or use a venv)

---

## 1. Start Infrastructure

```bash
docker compose up -d
```

Wait for Postgres to become healthy (5–10 seconds).

---

## 2. Apply Migrations

```bash
cd backend
alembic upgrade head
```

Expected output: `Running upgrade ... -> 007, Performance indexes`

---

## 3. Generate Synthetic Data

```bash
curl -s -X POST \
  "http://localhost:8000/admin/generate?seed=42&start_date=2025-04-08&end_date=2026-04-08&n_employees=300" \
  -H "Authorization: Bearer admin-token" | jq .
```

Expected response:
```json
{"run_id": "...", "status": "completed", "elapsed_seconds": ..., "seed": 42, "n_employees": 300}
```

Copy the `run_id` — it confirms generation is tracked in `/admin/run_history`.

---

## 4. Run the ETL Pipeline

```bash
curl -s -X POST \
  "http://localhost:8000/admin/run_pipeline?snapshot_date=2026-04-08&run_ml=true" \
  -H "Authorization: Bearer admin-token" | jq .
```

Expected: `"status": "completed"` with `rows_written` counts across dims, facts, features, insights, archetypes, trajectories.

---

## 5. Start the Frontend

```bash
cd frontend
cp .env.local.example .env.local   # or set manually:
# VITE_API_BASE_URL=http://localhost:8000
# VITE_API_TOKEN=admin-token
npm run dev
```

Open `http://localhost:5173/orgs`.

---

## 6. Org Overview

1. Paste the org UUID from the previous step (or fetch it from the API: `GET /orgs` — not yet implemented; use `psql` or the run_history endpoint to find it).

   Quick way:
   ```bash
   curl -s "http://localhost:8000/admin/run_history" \
     -H "Authorization: Bearer admin-token" | jq '.[0].run_id'
   # alternatively, query postgres:
   # SELECT org_id, org_name FROM orgs LIMIT 1;
   ```

2. Paste the UUID into the SelectOrg input → press **Initiate Access**.

3. **Show**: 4 metric cards (underutilization, overload, disengagement, contribution units), sortable team table with risk badges.

---

## 7. Team Drill-Down

1. Click any team row with a **HIGH** risk badge.
2. **Show**: team health cards, member list with per-person risk scores, weekly trends chart.
3. Click an employee with a HIGH badge.

---

## 8. Employee Profile — RBAC Demo

**As admin** (`VITE_API_TOKEN=admin-token`): full profile visible — archetype chip, 5 metric cards, activity timeline, feature comparison, insights list.

**As analyst** (`VITE_API_TOKEN=analyst-token` in `.env.local`, restart dev server):
- Navigate to the same employee URL directly.
- **Show**: AuditGate locked panel — "Access restricted. Your access attempt has been logged."
- Verify audit log recorded it: `GET /admin/audit-log?outcome=denied` (admin token required).

---

## 9. Accept a Recommendation

1. Navigate to **Actions** (`/recommendations`).
2. Filter by priority ≥ 0.7 to show highest-priority items.
3. Expand a row → click **Accept recommendation**.
4. **Show**: row opacity drops, checkmark appears, accepted count in the header increments.

---

## 10. Simulation Sandbox

1. Navigate to **Simulation** (`/simulations`).
2. Create simulation: name = "Q3 Reorg", snapshot date = `2026-04-08` → **Create Simulation**.
3. **Add Move 1**: From team A → To team B, pick an employee, set allocation +20%.
4. **Add Move 2**: From team B → To team C, pick a different employee, set allocation -30%.
5. Click **Compute**.
6. **Show**: outcomes table with Metric / Baseline / Simulated / Delta columns. Delta cells are colored green (improvement) or red (degradation).

---

## 11. Admin Endpoints (Bonus)

```bash
# Generation history
curl -s "http://localhost:8000/admin/run_history" \
  -H "Authorization: Bearer admin-token" | jq '.[0]'

# Audit log (all denied accesses from the RBAC demo)
curl -s "http://localhost:8000/admin/audit-log?outcome=denied" \
  -H "Authorization: Bearer admin-token" | jq '.[0]'
```

---

## CI Verification

```bash
# Backend tests (unit tier — no Postgres required for stub tests)
cd backend && pytest tests/ -m "not integration" --tb=short

# Frontend tests
cd frontend && npm test

# Frontend build
cd frontend && npm run build
```
