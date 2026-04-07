# WSIP Implementation Sprint Plan

> Living document. Update each task's status (`[ ]` → `[x]`) as we complete it.
> Roles: **BE** Backend Dev · **DE** Data Engineer · **DS** Data Scientist · **FE** Frontend Dev · **PM** Product

---

## Finalized Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | Homebrew |
| API framework | FastAPI 0.115 + Pydantic v2 | auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 (declarative, `mapped_column`) | |
| Migrations | Alembic 1.13 | |
| Database | PostgreSQL 16 (Homebrew) | flat `public` schema, naming conventions per spec |
| Auth | Static Bearer token map (env var) | no JWT for MVP; add later |
| ETL / generator | numpy, pandas, faker, python-dateutil | |
| ML | scikit-learn, statsmodels | |
| ASGI server | Uvicorn (dev), Gunicorn+Uvicorn worker (prod) | |
| Testing | pytest + httpx (backend) | key paths |
| Node | LTS (Homebrew) | |
| Frontend | React 18 + TypeScript, Vite 5 | |
| UI components | shadcn/ui + Tailwind CSS 3 | dark mode, cockpit theme |
| Charts | Recharts | dark-themed |
| Routing | React Router 6 | |
| Data fetching | TanStack Query v5 | |
| Frontend tests | Vitest | key paths |
| CI | GitHub Actions | lint, test, build |

**DB schema approach**: single `public` schema; table names follow spec conventions (`fact_`, `dim_`, raw tables by domain).

**Auth approach**: `WSIP_TOKENS` env var contains a JSON map of `token → {user_id, username, roles[]}`. `require_role(role)` FastAPI dependency. No expiry for MVP.

**UI theme**: near-black backgrounds (`#0a0e17`), cyan (`#00d4ff`) primary accent, amber (`#f59e0b`) warnings, green (`#10b981`) healthy, red (`#ef4444`) critical. Monospace font for numbers. Data-dense layouts.

**Simulation engine**: synchronous SQL + pandas re-weighting; no job queue for MVP.

---

## Repository Structure

```
wsip/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory, router registration
│   │   ├── config.py                # Settings (pydantic-settings), DB URL, token map
│   │   ├── database.py              # SQLAlchemy engine + session factory
│   │   ├── dependencies.py          # get_db(), get_current_user(), require_role()
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── admin.py             # POST /admin/generate, POST /admin/run_pipeline
│   │       ├── orgs.py              # GET /orgs/{id}/overview, /orgs/{id}/teams
│   │       ├── teams.py             # GET /teams/{id}/health, /members, /trends
│   │       ├── employees.py         # GET /employees/{id}/profile, /timeline, /insights
│   │       ├── insights.py          # GET /insights, GET /insights/{id}
│   │       ├── recommendations.py   # GET /recommendations, POST /{id}/accept
│   │       └── simulations.py       # POST /simulations, /moves, GET /outcomes
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                  # DeclarativeBase, common mixins (timestamps, UUID PK)
│   │   ├── canonical.py             # Org, Team, Employee, Repo, Project, Assignment, Skill, etc.
│   │   ├── raw_events.py            # GitCommitEvent, PullRequestEvent, CodeReviewEvent, etc.
│   │   ├── marts.py                 # DimDate, DimEmployee, DimTeam, DimProject, DimSkill
│   │   │                            # FactEmployeeDailyActivity, FactEmployeeProjectContribution
│   │   │                            # FactTeamWeeklyHealth, FactEmployeeSkillSignal
│   │   ├── features.py              # EmployeeFeatureSnapshot
│   │   ├── insights.py              # Insight, Recommendation, EmployeeArchetypeAssignment
│   │   │                            # EmployeeTrajectoryPrediction, EmployeePrePostImpactAnalysis
│   │   │                            # SimulationRun, SimulationEmployeeMove, SimulationOutcome
│   │   └── auth.py                  # AppUser, Role, UserRole, ViewerPermission, AccessAuditLog
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── canonical.py             # OrgOut, TeamOut, EmployeeOut, ProjectOut, etc.
│   │   ├── marts.py                 # TeamHealthOut, OrgOverviewOut, DailyActivityOut, etc.
│   │   ├── features.py              # FeatureSnapshotOut, EmployeeProfileOut
│   │   └── insights.py              # InsightOut, RecommendationOut, SimulationOut, etc.
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── pipeline.py              # run_daily_pipeline(snapshot_date): orchestrates dims→facts→features→insights
│   │   ├── dims.py                  # build_dim_date(), build_dim_employee(), build_dim_team(), etc.
│   │   ├── facts.py                 # build_fact_daily_activity(), build_fact_project_contribution()
│   │   │                            # build_fact_team_weekly_health(), build_fact_skill_signal()
│   │   ├── features.py              # build_feature_snapshots(snapshot_date)
│   │   ├── metrics.py               # compute_underutilization(), compute_overload()
│   │   │                            # compute_disengagement_risk(), compute_skill_utilization()
│   │   │                            # compute_glue_score() — all return pd.DataFrame
│   │   └── insight_engine.py        # generate_insights(snapshot_date) → list[Insight]
│   ├── synthetic/
│   │   ├── __init__.py
│   │   ├── personas.py              # PERSONAS dict, PersonaConfig dataclass
│   │   ├── generate.py              # SyntheticGenerator.generate(seed, start_date, end_date, n_employees)
│   │   └── shocks.py                # inject_shocks(employee_id, shock_type, event_date, session)
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── archetypes.py            # run_archetype_clustering(snapshot_date, n_clusters=8)
│   │   ├── trajectory.py            # run_trajectory_predictions(snapshot_date, horizon_days=60)
│   │   ├── prepost.py               # run_prepost_analysis(change_event_ids, window_days=30)
│   │   └── simulation.py            # compute_simulation_outcomes(simulation_run_id)
│   ├── tests/
│   │   ├── conftest.py              # pytest fixtures: test DB session, test client, seeded data
│   │   ├── test_generator.py        # determinism, row counts, distributions
│   │   ├── test_metrics.py          # golden-row tests for each metric
│   │   ├── test_etl.py              # idempotency tests for dims/facts/features
│   │   ├── test_auth.py             # RBAC allow/deny tests
│   │   └── test_api.py              # HTTP integration tests for all routers
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_canonical_tables.py
│   │       ├── 002_raw_event_tables.py
│   │       ├── 003_mart_tables.py
│   │       ├── 004_feature_store.py
│   │       └── 005_insight_model_tables.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                  # router setup, theme provider
│   │   ├── api/
│   │   │   ├── client.ts            # axios instance with base URL + auth header
│   │   │   ├── orgs.ts              # useOrgOverview(), useOrgTeams()
│   │   │   ├── teams.ts             # useTeamHealth(), useTeamMembers(), useTeamTrends()
│   │   │   ├── employees.ts         # useEmployeeProfile(), useEmployeeTimeline()
│   │   │   ├── insights.ts          # useInsights(), useRecommendations()
│   │   │   └── simulations.ts       # useSimulation(), createSimulation(), addMove()
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui auto-generated components
│   │   │   ├── layout/
│   │   │   │   ├── Shell.tsx        # sidebar + topbar cockpit chrome
│   │   │   │   └── Sidebar.tsx
│   │   │   ├── MetricCard.tsx       # score + trend delta + severity glow
│   │   │   ├── TimeseriesChart.tsx  # Recharts area/line, dark-themed
│   │   │   ├── ContributionBar.tsx  # stacked bar by signal type
│   │   │   ├── FilterBar.tsx        # date range + org/team/role pickers
│   │   │   ├── RiskBadge.tsx        # severity pill (critical/high/medium/low)
│   │   │   └── AuditGate.tsx        # RBAC wrapper — shows "access denied" panel
│   │   ├── pages/
│   │   │   ├── OrgOverview.tsx      # /orgs/:id
│   │   │   ├── TeamView.tsx         # /teams/:id
│   │   │   ├── EmployeeProfile.tsx  # /employees/:id (RBAC gated)
│   │   │   ├── Recommendations.tsx  # /recommendations
│   │   │   └── Simulation.tsx       # /simulation
│   │   └── lib/
│   │       ├── utils.ts             # cn(), formatScore(), formatDelta()
│   │       └── theme.ts             # color constants, severity → color map
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── components.json              # shadcn/ui config
├── docs/
│   ├── mvp_scope.md                 # PM: MVP scope + non-goals + sensitive views (S1)
│   ├── features_v0.md               # DS: feature list + normalization spec (S1)
│   ├── kpis.md                      # PM: dashboard KPI set (S3)
│   ├── taxonomy.md                  # PM: severity + action taxonomy (S5)
│   ├── ethics_copy.md               # PM: data ethics UI copy (S2)
│   ├── wireframes.md                # PM: page wireframes in ASCII/Mermaid (S7)
│   └── model_cards.md               # DS: model interpretability (S9)
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── backend.yml              # lint + test backend
│       └── frontend.yml             # lint + test frontend
├── SPRINT_PLAN.md                   # this file
└── README.md
```

---

## Sprint 1 — Backend Foundation

**Objective**: repo scaffolding, Docker Compose + Postgres, FastAPI skeleton with OpenAPI, Alembic + all canonical table migrations, simple auth, PM scope docs, DS feature spec.

**Definition of done**: `docker compose up` brings DB + API; `/docs` is accessible; `alembic upgrade head` creates all canonical tables; a protected endpoint rejects a bad token.

---

### PM tasks

- [ ] **Write `docs/mvp_scope.md`**
  - MVP capabilities list (verbatim from spec, refined)
  - Non-goals (explicit)
  - Sensitive views enumerated: employee profile drill-down, individual export, simulation with named employees
  - Data minimization statement
  - RBAC roles defined: `admin`, `org_analytics`, `manager`, `hrbp`

- [ ] **Write `docs/features_v0.md`** (joint with DS)
  - Feature list for `employee_feature_snapshots` with rolling windows (7/30/90d)
  - Normalization approach: min-max clamped to [0,1] per cohort (`role_family` + `job_level`)
  - Baseline definition: self-baseline = trailing 60–90d; role-baseline = cohort median

---

### DE tasks

- [ ] **`docker-compose.yml`**
  ```yaml
  services:
    db:
      image: postgres:16
      environment:
        POSTGRES_DB: wsip
        POSTGRES_USER: wsip
        POSTGRES_PASSWORD: wsip_dev
      volumes:
        - pgdata:/var/lib/postgresql/data
      ports:
        - "5432:5432"
    api:
      build: ./backend
      environment:
        DATABASE_URL: postgresql://wsip:wsip_dev@db:5432/wsip
        WSIP_TOKENS: '{"admin-token":{"user_id":"00000000-0000-0000-0000-000000000001","username":"admin","roles":["admin","org_analytics"]},"manager-token":{"user_id":"00000000-0000-0000-0000-000000000002","username":"manager","roles":["manager"]},"analyst-token":{"user_id":"00000000-0000-0000-0000-000000000003","username":"analyst","roles":["org_analytics"]}}'
      ports:
        - "8000:8000"
      depends_on:
        - db
  volumes:
    pgdata:
  ```

- [ ] **Initialize Alembic** (`backend/alembic.ini`, `backend/alembic/env.py`)
  - `env.py` must import `Base.metadata` from `backend/models/base.py`
  - `sqlalchemy.url` reads from `DATABASE_URL` env var

- [ ] **Migration `001_canonical_tables.py`** — creates all canonical tables in dependency order:
  1. `orgs`
  2. `skills` (no FKs to other canonical tables)
  3. `teams` (FK → orgs, self-ref parent_team_id)
  4. `employees` (FK → teams, orgs, self-ref manager)
  5. `repos` (FK → teams)
  6. `projects` (FK → employees, teams)
  7. `employee_project_assignments` (FK → employees, projects)
  8. `employee_skills` (FK → employees, skills)
  9. `project_skill_requirements` (FK → projects, skills)
  10. `artifacts` (FK → employees, teams, projects)
  11. `artifact_contributions` (FK → artifacts, employees)
  12. `artifact_skill_tags` (FK → artifacts, skills)
  13. `interactions` (FK → employees ×2, projects, artifacts)
  14. `employee_snapshots` (FK → employees)
  15. `employee_change_events` (FK → employees)
  16. `data_generation_runs`
  - Auth tables: `app_users`, `roles`, `user_roles`, `viewer_permissions`, `access_audit_log`
  - Indexes: `idx_employees_team(team_id)`, `idx_employees_org(org_id)`, `idx_employees_manager(manager_employee_id)`

---

### BE tasks

- [ ] **`backend/requirements.txt`**
  ```
  fastapi==0.115.*
  uvicorn[standard]==0.30.*
  sqlalchemy==2.0.*
  alembic==1.13.*
  psycopg2-binary==2.9.*
  pydantic==2.*
  pydantic-settings==2.*
  python-multipart==0.0.*
  numpy==1.26.*
  pandas==2.2.*
  faker==24.*
  scikit-learn==1.4.*
  statsmodels==0.14.*
  httpx==0.27.*          # test client
  pytest==8.*
  pytest-asyncio==0.23.*
  ```

- [ ] **`backend/app/config.py`**
  ```python
  class Settings(BaseSettings):
      database_url: str
      wsip_tokens: str  # JSON string parsed into dict

      @property
      def token_map(self) -> dict[str, dict]:
          return json.loads(self.wsip_tokens)

      model_config = SettingsConfigDict(env_file=".env")

  settings = Settings()
  ```

- [ ] **`backend/app/database.py`**
  ```python
  engine = create_engine(settings.database_url, pool_pre_ping=True)
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  ```

- [ ] **`backend/app/dependencies.py`**
  ```python
  def get_db() -> Generator[Session, None, None]: ...

  def get_current_user(
      authorization: str = Header(...),
      db: Session = Depends(get_db)
  ) -> dict:
      # parse "Bearer <token>", look up in settings.token_map
      # write to access_audit_log if employee-scoped
      ...

  def require_role(*roles: str):
      def dependency(current_user: dict = Depends(get_current_user)) -> dict:
          if not any(r in current_user["roles"] for r in roles):
              raise HTTPException(status_code=403, detail="Insufficient permissions")
          return current_user
      return dependency

  def require_employee_access(employee_id: UUID):
      # checks viewer_permissions or manager chain
      # writes access_audit_log row
      ...
  ```

- [ ] **`backend/app/main.py`**
  ```python
  app = FastAPI(title="WSIP", version="0.1.0", docs_url="/docs", redoc_url="/redoc")

  app.include_router(admin.router, prefix="/admin", tags=["admin"])
  app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])
  app.include_router(teams.router, prefix="/teams", tags=["teams"])
  app.include_router(employees.router, prefix="/employees", tags=["employees"])
  app.include_router(insights.router, prefix="/insights", tags=["insights"])
  app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
  app.include_router(simulations.router, prefix="/simulations", tags=["simulations"])

  @app.get("/health")
  def health(): return {"status": "ok"}
  ```

- [ ] **`backend/app/routers/admin.py`** — stub endpoints only (implementation in S2):
  ```python
  @router.post("/generate")
  def trigger_generate(
      seed: int, start_date: date, end_date: date,
      current_user: dict = Depends(require_role("admin"))
  ) -> dict: ...

  @router.post("/run_pipeline")
  def trigger_pipeline(
      snapshot_date: date,
      current_user: dict = Depends(require_role("admin"))
  ) -> dict: ...
  ```

- [ ] **`backend/models/base.py`**
  ```python
  class Base(DeclarativeBase): pass

  class UUIDMixin:
      # provides uuid PK field defaulting to uuid4

  class TimestampMixin:
      # provides created_at, updated_at with server_default=func.now()
  ```

- [ ] **`backend/models/canonical.py`** — SQLAlchemy 2.0 models for all 16 canonical tables:
  - `Org`, `Team`, `Employee`, `Repo`, `Project`
  - `EmployeeProjectAssignment`, `Skill`, `EmployeeSkill`, `ProjectSkillRequirement`
  - `Artifact`, `ArtifactContribution`, `ArtifactSkillTag`
  - `Interaction`, `EmployeeSnapshot`, `EmployeeChangeEvent`
  - `DataGenerationRun`

- [ ] **`backend/models/auth.py`** — `AppUser`, `Role`, `UserRole`, `ViewerPermission`, `AccessAuditLog`

- [ ] **`backend/Dockerfile`**
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
  ```

---

### DS tasks

- [ ] **`docs/features_v0.md`** (joint with PM)
  - 7/30/90-day rolling windows for all activity dimensions
  - Cohort baseline segmentation strategy (`role_family` × `job_level`)
  - Score normalization formula: `clamp01((x - p10) / (p90 - p10))` per cohort
  - Activity weight tables per `role_family` (engineering/research/management/ops)

---

### S1 Acceptance Criteria

- [ ] `docker compose up` starts Postgres + API with no errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /docs` and `GET /redoc` render OpenAPI UI
- [ ] `alembic upgrade head` runs cleanly; all canonical tables exist in DB
- [ ] `GET /orgs/anything` without auth header → `401`
- [ ] `GET /orgs/anything` with `Authorization: Bearer bad-token` → `401`
- [ ] `GET /orgs/anything` with `Authorization: Bearer admin-token` → `404` (not `401`/`403`)
- [ ] `docs/mvp_scope.md` and `docs/features_v0.md` exist and are substantive

---

## Sprint 2 — Raw Events Schema + Synthetic Generator

**Objective**: all raw event tables via migration, synthetic generator producing a seeded, reproducible 365-day / 300-employee dataset in < 10 minutes.

**Definition of done**: `POST /admin/generate` populates all tables; re-running same seed produces identical row counts; `data_generation_runs` records each run.

---

### DE tasks

- [ ] **Migration `002_raw_event_tables.py`** — all raw event tables:
  - `git_commit_events` — index `(employee_id, commit_ts)`
  - `pull_request_events` — index `(employee_id, opened_at)`, `(repo_id, opened_at)`
  - `code_review_events` — index `(reviewer_employee_id, review_ts)`
  - `experiment_run_events` — index `(employee_id, started_at)`, `(project_id, started_at)`
  - `research_artifact_events` — index `(employee_id, created_at)`
  - `document_events` — index `(employee_id, event_ts)`
  - `task_events` — index `(employee_id, event_ts)`
  - `meeting_events` — index `(employee_id, start_ts)`
  - `chat_metadata_events` — index `(employee_id, event_ts)`
  - `training_completion_events` — index `(employee_id, completed_at)`
  - `resume_skill_inference` — index `(employee_id)`

- [ ] **`backend/models/raw_events.py`** — SQLAlchemy models for all 11 raw event tables

---

### DS tasks

- [ ] **`backend/synthetic/personas.py`**
  ```python
  @dataclass
  class PersonaConfig:
      name: str
      role_family: str          # engineering / research / management
      job_levels: list[str]
      # per-signal daily rate parameters (mean, std or lambda for Poisson)
      commit_lambda: float
      pr_lambda: float
      review_lambda: float
      experiment_lambda: float
      meeting_lambda: float
      meeting_duration_mean: float
      doc_lambda: float
      task_lambda: float
      chat_lambda: float
      # multipliers applied to base rates
      skill_depth: float        # drives inferred_skill_score
      collab_breadth: float     # drives collaboration_edges
      trajectory: str           # stable / rising / declining / shock_manager_change / ...

  PERSONAS: dict[str, PersonaConfig] = {
      "deep_researcher": ...,
      "prolific_engineer": ...,
      "glue_person": ...,
      "underutilized_expert": ...,
      "overloaded_lead": ...,
      "silent_disengagement": ...,
      "rising_star": ...,
      "specialist_researcher": ...,
      "meeting_heavy_manager": ...,
      "new_hire_ramp": ...,
  }
  ```

- [ ] **`backend/synthetic/generate.py`**
  ```python
  class SyntheticGenerator:
      def __init__(self, seed: int, db_url: str): ...

      def generate(
          self,
          start_date: date,
          end_date: date,
          n_employees: int = 300,
          n_orgs: int = 3,
          n_teams: int = 25,
          n_projects: int = 40,
          n_repos: int = 30,
          n_skills: int = 60,
      ) -> UUID:  # returns data_generation_run.run_id
          # 1. seed numpy rng, Faker
          # 2. generate orgs → teams → employees (persona assigned by distribution)
          # 3. generate skills taxonomy, assign employee_skills
          # 4. generate repos, projects, assignments
          # 5. for each employee × each day: generate raw events per persona rates
          #    - apply weekday multiplier
          #    - apply quarter-end spike (docs/meetings +20% last 10 biz days of Q)
          #    - apply milestone spikes for engineering projects
          # 6. inject shocks from shocks.py
          # 7. bulk insert all tables
          # 8. write data_generation_runs row
          ...

      def _weekday_multiplier(self, d: date) -> float:
          # Mon-Thu: 1.0, Fri: 0.8, Sat-Sun: 0.1
          ...

      def _is_quarter_end_spike(self, d: date) -> bool: ...

      def _bulk_insert(self, table_name: str, rows: list[dict]): ...
  ```

- [ ] **`backend/synthetic/shocks.py`**
  ```python
  def inject_manager_change(employee_id, event_date, session): ...
  def inject_project_reassignment(employee_id, from_project, to_project, event_date, session): ...
  def inject_burnout_episode(employee_id, start_date, end_date, session): ...
  def inject_research_breakthrough(employee_id, event_date, session): ...
  def inject_leave_of_absence(employee_id, start_date, end_date, session): ...
  ```

---

### BE tasks

- [ ] **Implement `POST /admin/generate`** (was stub in S1)
  - Calls `SyntheticGenerator(seed).generate(...)`
  - Returns `{"run_id": "...", "status": "completed", "elapsed_seconds": ...}`
  - Protected by `require_role("admin")`

- [ ] **PM task**: Write `docs/ethics_copy.md` — short data ethics text for eventual UI inclusion

---

### S2 Acceptance Criteria

- [ ] Migration `002` applies cleanly on top of `001`
- [ ] `POST /admin/generate` with `seed=20260406` completes in < 10 min
- [ ] Same seed run twice → identical row counts in all raw event tables
- [ ] `data_generation_runs` has a row with `seed`, `start_date`, `end_date`, `employee_count`
- [ ] All 300 employees have events across all signal types
- [ ] Persona distribution visible: e.g., "deep_researcher" employees have high `experiment_run_events` counts vs. "prolific_engineer" having high `git_commit_events`
- [ ] `test_generator.py`: determinism test passes

---

## Sprint 3 — Analytics Marts

**Objective**: build dimensional model (dims + daily/weekly/project facts), expose org overview and team health endpoints.

**Definition of done**: `POST /admin/run_pipeline` populates dims and facts; `GET /orgs/{id}/overview` returns real metric data < 200ms locally.

---

### DE tasks

- [ ] **Migration `003_mart_tables.py`**
  - `dim_date`, `dim_employee`, `dim_team`, `dim_project`, `dim_skill`
  - `fact_employee_daily_activity` (composite PK: `date_key` + `employee_key`)
  - `fact_employee_project_contribution` (composite PK: `date_key` + `employee_key` + `project_id`)
  - `fact_team_weekly_health` (composite PK: `week_key` + `team_id`)
  - `fact_employee_skill_signal` (composite PK: `date_key` + `employee_key` + `skill_id`)

- [ ] **`backend/models/marts.py`** — SQLAlchemy models for all mart tables

- [ ] **`backend/etl/dims.py`**
  ```python
  def build_dim_date(start_date: date, end_date: date, session: Session) -> int:
      # generates one row per day, idempotent (upsert by date_key)
      # populates: date_key (YYYYMMDD int), date, day_of_week, is_weekend, week_key, month_key
      ...

  def build_dim_employee(snapshot_date: date, session: Session) -> int:
      # SCD: for each employee, create/update dim row with effective_from/effective_to
      # sources from employees + employee_snapshots
      ...

  def build_dim_team(snapshot_date: date, session: Session) -> int: ...
  def build_dim_project(snapshot_date: date, session: Session) -> int: ...
  def build_dim_skill(session: Session) -> int: ...
  ```

- [ ] **`backend/etl/facts.py`**
  ```python
  def build_fact_daily_activity(snapshot_date: date, session: Session) -> int:
      # for each (employee, day) up to snapshot_date:
      # aggregate raw events into fact columns
      # upsert by (date_key, employee_key)
      # idempotent: delete-then-insert for date range
      ...

  def build_fact_project_contribution(snapshot_date: date, session: Session) -> int:
      # attribution by project per employee per day
      # contribution_units = weighted sum of code/research/doc/collab/strategic/impact units
      # weights from DS-defined config (role_family aware)
      ...

  def build_fact_team_weekly_health(snapshot_date: date, session: Session) -> int:
      # weekly rollup from fact_employee_daily_activity
      # underutilization_rate = fraction of team with underutilization_score > 0.6
      # overload_rate = fraction with overload_score > 0.6
      # etc.
      ...

  def build_fact_skill_signal(snapshot_date: date, session: Session) -> int: ...
  ```

- [ ] **`backend/etl/pipeline.py`**
  ```python
  def run_daily_pipeline(snapshot_date: date, session: Session) -> dict:
      results = {}
      results["dim_date"] = build_dim_date(..., session)
      results["dim_employee"] = build_dim_employee(snapshot_date, session)
      results["dim_team"] = build_dim_team(snapshot_date, session)
      results["dim_project"] = build_dim_project(snapshot_date, session)
      results["dim_skill"] = build_dim_skill(session)
      results["fact_daily_activity"] = build_fact_daily_activity(snapshot_date, session)
      results["fact_project_contribution"] = build_fact_project_contribution(snapshot_date, session)
      results["fact_team_weekly_health"] = build_fact_team_weekly_health(snapshot_date, session)
      results["fact_skill_signal"] = build_fact_skill_signal(snapshot_date, session)
      return results
  ```

---

### DS tasks

- [ ] **Contribution units mapping config** (`backend/etl/facts.py` or `backend/etl/config.py`)
  ```python
  CONTRIBUTION_WEIGHTS: dict[str, dict[str, float]] = {
      "research": {
          "code": 0.15, "research": 0.40, "documentation": 0.20,
          "collaboration": 0.15, "strategic": 0.05, "impact": 0.05
      },
      "engineering": {
          "code": 0.45, "research": 0.05, "documentation": 0.10,
          "collaboration": 0.20, "strategic": 0.05, "impact": 0.15
      },
      "management": {
          "code": 0.05, "research": 0.05, "documentation": 0.15,
          "collaboration": 0.40, "strategic": 0.20, "impact": 0.15
      },
      # ... other role families
  }
  ```

---

### BE tasks

- [ ] **`backend/schemas/marts.py`**
  ```python
  class OrgOverviewOut(BaseModel):
      org_id: UUID
      org_name: str
      snapshot_date: date
      active_employee_count: int
      underutilization_rate: float
      overload_rate: float
      disengagement_risk_rate: float
      total_contribution_units: float
      teams: list[TeamSummaryOut]

  class TeamHealthOut(BaseModel):
      team_id: UUID
      team_name: str
      week_key: int
      active_employee_count: int
      underutilization_rate: float
      overload_rate: float
      silent_disengagement_rate: float
      cross_team_collaboration_rate: float
      burnout_risk_rate: float
  ```

- [ ] **`backend/app/routers/orgs.py`**
  ```python
  @router.get("/{org_id}/overview", response_model=OrgOverviewOut)
  def get_org_overview(
      org_id: UUID, as_of: date,
      current_user: dict = Depends(require_role("admin", "org_analytics", "manager"))
  ) -> OrgOverviewOut: ...

  @router.get("/{org_id}/teams", response_model=list[TeamSummaryOut])
  def list_org_teams(org_id: UUID, as_of: date, current_user=Depends(...)): ...
  ```

- [ ] **`backend/app/routers/teams.py`**
  ```python
  @router.get("/{team_id}/health", response_model=TeamHealthOut)
  def get_team_health(team_id: UUID, week_key: int, current_user=Depends(...)): ...

  @router.get("/{team_id}/members", response_model=list[EmployeeSummaryOut])
  def list_team_members(team_id: UUID, as_of: date, current_user=Depends(...)): ...

  @router.get("/{team_id}/trends", response_model=list[TeamTrendPointOut])
  def get_team_trends(team_id: UUID, from_week: int, to_week: int, current_user=Depends(...)): ...
  ```

- [ ] **Implement `POST /admin/run_pipeline`** (was stub in S1)
  - Calls `run_daily_pipeline(snapshot_date, db)`
  - Returns `{"snapshot_date": "...", "rows_written": {...}}`

- [ ] **PM task**: Write `docs/kpis.md` — frozen KPI list for org/team views

---

### S3 Acceptance Criteria

- [ ] Migration `003` applies cleanly
- [ ] `POST /admin/run_pipeline` populates all dims and facts without errors
- [ ] Running it twice with same `snapshot_date` produces identical fact row counts (idempotent)
- [ ] `GET /orgs/{id}/overview?as_of=...` returns non-null metric values
- [ ] `GET /teams/{id}/health?week_key=...` returns plausible rates (all between 0–1)
- [ ] Response times < 200ms locally (with indexes from migration)
- [ ] `test_etl.py`: idempotency tests pass

---

## Sprint 4 — Feature Store, Core Metrics & RBAC

**Objective**: `employee_feature_snapshots` pipeline with rolling windows; all five core metric scores computed; employee-level endpoints with RBAC + audit logging.

**Definition of done**: feature snapshots exist for all 300 employees for a given `as_of` date; employee profile endpoint enforces role; audit log gets a row on each access.

---

### DE tasks

- [ ] **Migration `004_feature_store.py`** — `employee_feature_snapshots` table

- [ ] **`backend/models/features.py`** — `EmployeeFeatureSnapshot` SQLAlchemy model (all ~35 columns)

- [ ] **`backend/etl/features.py`**
  ```python
  def build_feature_snapshots(snapshot_date: date, session: Session) -> int:
      # for each active employee:
      # - query fact_employee_daily_activity for rolling 7/30/90d windows
      # - compute vs-self baseline (trailing 60–90d median)
      # - compute vs-cohort baseline (same role_family + job_level, same period)
      # - populate all feature columns
      # - upsert by (employee_id, snapshot_date)
      # Uses SQL window functions via SQLAlchemy text() for performance
      ...
  ```

---

### DS tasks

- [ ] **`backend/etl/metrics.py`** — implement all five core metrics as Python functions operating on feature snapshot rows:

  ```python
  def compute_underutilization(snap: EmployeeFeatureSnapshot) -> float:
      return (
          0.30 * clamp01(snap.activity_drop_30d or 0)
          + 0.25 * clamp01(1 - (snap.project_allocation_utilization_score or 0))
          + 0.20 * clamp01(1 - (snap.skill_utilization_score or 0))
          + 0.15 * clamp01(1 - (snap.collaboration_breadth_30d / 30))  # norm
          + 0.10 * clamp01(1 - (snap.knowledge_creation_score or 0))
      )

  def compute_overload(snap: EmployeeFeatureSnapshot) -> float:
      # meeting_load_hours_30d > role-adjusted threshold
      # high volatility, many active projects, task cycle time inflation
      ...

  def compute_disengagement_risk(snap: EmployeeFeatureSnapshot) -> float:
      # activity_drop_14d + activity_drop_30d, collaboration_breadth drop, low cross-team rate
      ...

  def compute_skill_utilization(snap: EmployeeFeatureSnapshot) -> float:
      # skill_utilization_score from fact_employee_skill_signal
      ...

  def compute_glue_score(snap: EmployeeFeatureSnapshot) -> float:
      # collaboration_centrality_30d, cross_team_interaction_rate_30d
      ...

  def clamp01(v: float) -> float:
      return max(0.0, min(1.0, v))
  ```

  - Write metrics back to `employee_feature_snapshots.underutilization_score`, etc.
  - Unit test with fixture rows (golden values)

---

### BE tasks

- [ ] **`backend/schemas/features.py`**
  ```python
  class EmployeeProfileOut(BaseModel):
      employee_id: UUID
      full_name: str
      role_title: str
      role_family: str
      job_level: str
      team_name: str
      snapshot_date: date
      underutilization_score: float
      overload_score: float
      disengagement_risk_score: float
      skill_utilization_score: float
      glue_person_score: float
      # rolling features
      commits_30d: int
      prs_merged_30d: int
      meeting_load_hours_30d: float
      collaboration_breadth_30d: int
      experiment_runs_30d: int
      # baselines
      commits_30d_vs_self_baseline: float
      commits_30d_vs_role_baseline: float
      archetype_label: str | None
  ```

- [ ] **`backend/app/routers/employees.py`**
  ```python
  @router.get("/{employee_id}/profile", response_model=EmployeeProfileOut)
  def get_employee_profile(
      employee_id: UUID,
      as_of: date,
      current_user: dict = Depends(get_current_user),
      db: Session = Depends(get_db)
  ) -> EmployeeProfileOut:
      # 1. check viewer_permissions or manager chain → 403 if denied
      # 2. write AccessAuditLog row (action="read_profile", outcome="success"/"denied")
      # 3. return EmployeeProfileOut
      ...

  @router.get("/{employee_id}/timeline", response_model=list[DailyActivityOut])
  def get_employee_timeline(
      employee_id: UUID, from_date: date, to_date: date,
      current_user: dict = Depends(get_current_user)
  ) -> list[DailyActivityOut]:
      # also requires access + audit log
      ...

  @router.get("/{employee_id}/insights", response_model=list[InsightOut])
  def get_employee_insights(
      employee_id: UUID, as_of: date,
      current_user: dict = Depends(get_current_user)
  ) -> list[InsightOut]: ...
  ```

- [ ] **RBAC enforcement** in `dependencies.py`:
  - Manager can access their direct reports' profiles
  - `hrbp` and `admin` can access any employee
  - `org_analytics` sees aggregated views only (no individual drill-down)
  - `viewer_permissions` table checked for explicit grants

- [ ] **Negative RBAC tests** in `test_auth.py`:
  - `analyst-token` → `GET /employees/{id}/profile` → `403`
  - `manager-token` → non-direct-report → `403`
  - `manager-token` → direct report → `200` + audit log row written

---

### S4 Acceptance Criteria

- [ ] `employee_feature_snapshots` populated for all employees for `snapshot_date`
- [ ] All five metric scores are non-null and in [0, 1]
- [ ] `test_metrics.py`: golden-row tests pass for all five metrics
- [ ] `GET /employees/{id}/profile` with `analyst-token` → `403` + audit log row with `outcome="denied"`
- [ ] `GET /employees/{id}/profile` with `admin-token` → `200` + audit log row with `outcome="success"`
- [ ] `test_auth.py`: all allow/deny paths covered

---

## Sprint 5 — Insight Engine

**Objective**: rule-based insights + recommendations; `POST /admin/run_pipeline` extended to include insight generation; triage API endpoints.

**Definition of done**: insights written for all employees with severity and explanation; recommendations linked to insights; endpoints secured.

---

### DS tasks

- [ ] **`backend/etl/insight_engine.py`**
  ```python
  INSIGHT_RULES: list[InsightRule] = [
      InsightRule(
          insight_type="underutilization",
          condition=lambda s: s.underutilization_score > 0.65,
          severity_fn=lambda s: "high" if s.underutilization_score > 0.80 else "medium",
          title_fn=lambda s: "Underutilization vs allocation",
          description_fn=lambda s: (
              f"30d activity is {s.activity_drop_30d:+.0%} vs baseline; "
              f"allocation utilization is {s.project_allocation_utilization_score:.0%}"
          ),
          confidence_fn=lambda s: min(1.0, s.underutilization_score + 0.15),
      ),
      InsightRule(insight_type="overload", ...),
      InsightRule(insight_type="disengagement_risk", ...),
      InsightRule(insight_type="skill_underutilization", ...),
      InsightRule(insight_type="glue_person_identified", ...),
  ]

  def generate_insights(snapshot_date: date, session: Session) -> int:
      # for each employee feature snapshot:
      # evaluate each rule; create Insight rows
      # link Recommendation rows
      # upsert by (scope_id, insight_type, snapshot_date) — idempotent
      ...

  def generate_recommendations(insight: Insight) -> list[Recommendation]:
      # rule-based: e.g., underutilization → manager_checkin + reassignment_candidate
      ...
  ```

---

### BE tasks

- [ ] **Migration `005_insight_model_tables.py`** — `insights`, `recommendations`, `employee_archetype_assignments`, `employee_trajectory_predictions`, `employee_pre_post_impact_analysis`, `simulation_runs`, `simulation_employee_moves`, `simulation_outcomes`

- [ ] **`backend/models/insights.py`** — all insight/model/simulation ORM models

- [ ] **`backend/app/routers/insights.py`**
  ```python
  @router.get("/", response_model=list[InsightOut])
  def list_insights(
      scope: str | None = None,      # org/team/employee
      scope_id: UUID | None = None,
      insight_type: str | None = None,
      severity: str | None = None,
      as_of: date = ...,
      limit: int = 50,
      current_user: dict = Depends(require_role("admin", "org_analytics", "manager", "hrbp"))
  ) -> list[InsightOut]: ...

  @router.get("/{insight_id}", response_model=InsightOut)
  def get_insight(insight_id: UUID, current_user=Depends(...)): ...
  ```

- [ ] **`backend/app/routers/recommendations.py`**
  ```python
  @router.get("/", response_model=list[RecommendationOut])
  def list_recommendations(
      scope: str | None = None,
      target_scope: str | None = None,
      priority_min: float = 0.0,
      limit: int = 50,
      current_user=Depends(...)
  ) -> list[RecommendationOut]: ...

  @router.post("/{recommendation_id}/accept")
  def accept_recommendation(
      recommendation_id: UUID,
      current_user=Depends(require_role("admin", "manager", "hrbp"))
  ) -> dict:
      # sets accepted_flag=True, accepted_at=now()
      ...
  ```

- [ ] Extend `run_daily_pipeline` to call `generate_insights(snapshot_date, session)` as final step

- [ ] **PM task**: Write `docs/taxonomy.md` — severity levels + recommendation action taxonomy

- [ ] **Tests**: `test_api.py` — insight list returns correct severity filtering; accept roundtrip works

---

### S5 Acceptance Criteria

- [ ] `insights` table has rows for all employees after pipeline run
- [ ] Each insight has non-null `insight_description` explaining the drivers
- [ ] `GET /insights?severity=high&scope=employee` returns only high-severity employee insights
- [ ] `POST /recommendations/{id}/accept` sets `accepted_flag=True` and `accepted_at`
- [ ] `test_api.py`: insight + recommendation CRUD paths pass

---

## Sprint 6 — Modeling & Simulation

**Objective**: archetype clustering, trajectory predictions, pre/post analysis, simulation engine with endpoints.

**Definition of done**: archetypes stored for all employees; simulation endpoint computes and stores outcomes synchronously.

---

### DS tasks

- [ ] **`backend/ml/archetypes.py`**
  ```python
  def run_archetype_clustering(
      snapshot_date: date,
      session: Session,
      n_clusters: int = 8,
      model_version: str = "wsip-0.1"
  ) -> int:
      # 1. load employee_feature_snapshots for snapshot_date
      # 2. select feature columns relevant to archetypes (experiment rates, commit rates, meeting load, collab breadth, etc.)
      # 3. StandardScaler → KMeans(n_clusters) or GaussianMixture
      # 4. label clusters with human names by examining centroid values
      # 5. write EmployeeArchetypeAssignment rows with top_signal_1/2/3
      ...
  ```

- [ ] **`backend/ml/trajectory.py`**
  ```python
  def run_trajectory_predictions(
      snapshot_date: date,
      session: Session,
      horizon_days: int = 60,
      model_version: str = "wsip-0.1"
  ) -> int:
      # Features: rolling activity features + deltas + archetype assignment
      # Target proxy: disengagement_risk_score at t+horizon (computed from trailing data)
      # Model: LogisticRegression for disengagement risk; Ridge for impact score
      # Write EmployeeTrajectoryPrediction rows
      ...
  ```

- [ ] **`backend/ml/prepost.py`**
  ```python
  def run_prepost_analysis(
      change_event_ids: list[UUID],
      session: Session,
      window_days: int = 30,
      model_version: str = "wsip-0.1"
  ) -> int:
      # For each change event:
      # - compute pre_window = [event_date - window_days, event_date - 1]
      # - compute post_window = [event_date, event_date + window_days]
      # - pull feature_snapshots for each window; compute mean
      # - write EmployeePrePostImpactAnalysis rows per metric
      ...
  ```

- [ ] **`backend/ml/simulation.py`**
  ```python
  def compute_simulation_outcomes(
      simulation_run_id: UUID,
      session: Session,
      model_version: str = "wsip-0.1"
  ) -> int:
      # 1. load simulation_employee_moves for this run
      # 2. load baseline feature_snapshots for each affected employee
      # 3. apply deterministic re-weighting:
      #    - allocation_pct_change → adjusts project_allocation_utilization_score
      #    - team change → adjusts cross_team_interaction_rate, collaboration_breadth proxy
      # 4. re-compute metric scores with adjusted features
      # 5. compute delta vs baseline
      # 6. aggregate deltas by team/org
      # 7. write SimulationOutcome rows
      ...
  ```

---

### BE tasks

- [ ] **`backend/app/routers/simulations.py`**
  ```python
  @router.post("/", response_model=SimulationRunOut)
  def create_simulation(
      body: SimulationCreateIn,
      current_user: dict = Depends(require_role("admin", "manager", "hrbp"))
  ) -> SimulationRunOut: ...

  @router.post("/{simulation_run_id}/moves", response_model=SimulationMoveOut)
  def add_simulation_move(
      simulation_run_id: UUID,
      body: SimulationMoveIn,
      current_user: dict = Depends(require_role("admin", "manager", "hrbp"))
  ) -> SimulationMoveOut: ...

  @router.post("/{simulation_run_id}/compute")
  def compute_simulation(
      simulation_run_id: UUID,
      current_user: dict = Depends(require_role("admin", "manager", "hrbp"))
  ) -> SimulationRunOut:
      # calls compute_simulation_outcomes(simulation_run_id, db)
      # synchronous for MVP (< 1s expected)
      ...

  @router.get("/{simulation_run_id}/outcomes", response_model=list[SimulationOutcomeOut])
  def get_simulation_outcomes(simulation_run_id: UUID, current_user=Depends(...)): ...
  ```

- [ ] **Extend `POST /admin/run_pipeline`** to optionally run ML steps:
  - `?run_ml=true` → also runs archetype clustering + trajectory predictions + prepost analysis

- [ ] Audit log entries for simulation creation (sensitive: named employee moves)

---

### S6 Acceptance Criteria

- [ ] All employees have `employee_archetype_assignments` row for snapshot_date
- [ ] Archetype labels are human-readable (not just "cluster_0")
- [ ] `POST /simulations` → add moves → `POST /compute` → `GET /outcomes` roundtrip works
- [ ] Simulation outcomes show non-zero deltas for moved employees' teams
- [ ] `test_api.py`: simulation roundtrip test passes

---

## Sprint 7 — Frontend Foundation

**Objective**: React + Vite + TypeScript app with cockpit dark theme, routing, API client, and working Org Overview page.

**Definition of done**: `npm run dev` renders Org Overview with real API data; theme matches cockpit spec.

---

### FE tasks

- [ ] **Scaffold**: `npm create vite@latest frontend -- --template react-ts`

- [ ] **Install dependencies**:
  ```
  tailwindcss @tailwindcss/vite
  shadcn/ui (via CLI: npx shadcn@latest init)
  recharts
  react-router-dom@6
  @tanstack/react-query@5
  axios
  clsx tailwind-merge
  lucide-react
  ```

- [ ] **`frontend/tailwind.config.ts`** — cockpit theme extension:
  ```typescript
  extend: {
    colors: {
      bg: { DEFAULT: "#0a0e17", surface: "#111827", elevated: "#1f2937" },
      accent: { cyan: "#00d4ff", amber: "#f59e0b", green: "#10b981", red: "#ef4444" },
      text: { primary: "#f9fafb", secondary: "#9ca3af", muted: "#4b5563" },
    },
    fontFamily: {
      mono: ["JetBrains Mono", "Fira Code", "monospace"],
    },
  }
  ```

- [ ] **`frontend/src/lib/theme.ts`**
  ```typescript
  export const SEVERITY_COLOR = {
    critical: "#ef4444",
    high: "#f59e0b",
    medium: "#eab308",
    low: "#10b981",
  } as const;

  export const SCORE_COLOR = (score: number): string =>
    score > 0.7 ? "#ef4444" : score > 0.4 ? "#f59e0b" : "#10b981";
  ```

- [ ] **`frontend/src/api/client.ts`**
  ```typescript
  import axios from "axios";

  export const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
    headers: {
      Authorization: `Bearer ${import.meta.env.VITE_API_TOKEN ?? "admin-token"}`,
    },
  });
  ```

- [ ] **`frontend/src/api/orgs.ts`**
  ```typescript
  export function useOrgOverview(orgId: string, asOf: string) {
    return useQuery({
      queryKey: ["org", orgId, "overview", asOf],
      queryFn: () => api.get(`/orgs/${orgId}/overview?as_of=${asOf}`).then(r => r.data),
    });
  }

  export function useOrgTeams(orgId: string, asOf: string) { ... }
  ```

- [ ] **`frontend/src/components/layout/Shell.tsx`** — cockpit chrome:
  - Fixed sidebar (dark, thin, icon + label nav)
  - Top bar: org selector, date picker, current user chip
  - Main content area with subtle grid background

- [ ] **`frontend/src/components/MetricCard.tsx`**
  ```typescript
  interface MetricCardProps {
    label: string;
    value: number;         // 0–1 score
    delta?: number;        // signed delta vs prior period
    format?: "score" | "percent" | "count";
    severity?: "critical" | "high" | "medium" | "low";
  }
  // renders: large mono number, colored severity glow border, trend arrow
  ```

- [ ] **`frontend/src/components/TimeseriesChart.tsx`** — Recharts `AreaChart`, dark-themed, responsive

- [ ] **`frontend/src/pages/OrgOverview.tsx`** — `/orgs/:id`:
  - Top row: 4 MetricCards (underutilization_rate, overload_rate, disengagement_risk_rate, cross_team_collab_rate)
  - Team table: sortable by any metric, risk badges
  - Date picker synced to `as_of` query param

- [ ] **PM task**: Write `docs/wireframes.md` — ASCII/Mermaid wireframes for team view, employee profile, recommendations, simulation

---

### S7 Acceptance Criteria

- [ ] `npm run dev` renders with no errors
- [ ] Dark cockpit theme applied (correct colors, mono font for numbers)
- [ ] Org Overview loads and shows non-zero metrics from real API
- [ ] MetricCard severity glow matches score thresholds
- [ ] 401/403 API errors render a clear "access denied" state (not a blank page)

---

## Sprint 8 — Frontend Features

**Objective**: Team View, Employee Profile (RBAC-gated), Recommendations triage, Simulation sandbox UI.

**Definition of done**: all five pages render with real data; RBAC gating works end-to-end; accept recommendation roundtrip works.

---

### FE tasks

- [ ] **`frontend/src/components/ContributionBar.tsx`** — stacked bar (code/research/docs/collab/strategic/impact units)

- [ ] **`frontend/src/components/RiskBadge.tsx`** — pill with severity color + label

- [ ] **`frontend/src/components/AuditGate.tsx`**
  ```typescript
  // Wraps children; if API returns 403, shows locked panel instead:
  // "Access restricted. Your access attempt has been logged."
  ```

- [ ] **`frontend/src/components/FilterBar.tsx`** — date range picker, team selector, role family filter

- [ ] **`frontend/src/pages/TeamView.tsx`** — `/teams/:id`:
  - Health MetricCards
  - Member table with per-person risk badges + scores
  - Trends chart (weekly health metrics over time)
  - ContributionBar showing team-level mix

- [ ] **`frontend/src/pages/EmployeeProfile.tsx`** — `/employees/:id`:
  - Wrapped in `<AuditGate>`
  - Personal header: name, role, team, archetype label chip
  - 5 core metric cards
  - Rolling activity timeline chart
  - Feature comparison: vs self-baseline + vs role-baseline
  - Insights list for this employee

- [ ] **`frontend/src/pages/Recommendations.tsx`** — `/recommendations`:
  - Filterable table: scope, type, severity, priority
  - Expandable row: insight description + recommendation text + affected employee
  - Accept button → `POST /recommendations/{id}/accept`

- [ ] **`frontend/src/pages/Simulation.tsx`** — `/simulation`:
  - Create simulation: name + scenario type
  - Move builder: employee selector → from/to team + from/to project + allocation %
  - Rationale text field
  - "Compute" button → calls `/simulations/{id}/compute`
  - Outcomes diff table: per-team expected metric deltas (colored ±)

- [ ] **BE**: API polish for frontend-support (pagination on lists, consistent error shapes, CORS headers)
  ```python
  # In main.py:
  app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
  ```

---

### S8 Acceptance Criteria

- [ ] All 5 pages render without errors with seeded data
- [ ] Employee Profile: `VITE_API_TOKEN=analyst-token` → AuditGate shows locked panel
- [ ] Recommendations: accept button sets `accepted_flag`, row updates in UI
- [ ] Simulation: create → add 2 moves → compute → outcomes diff renders with colored deltas
- [ ] No blank screens for empty states (zero insights, no employees in team, etc.)

---

## Sprint 9 — Hardening & Demo

**Objective**: performance pass, end-to-end validation, CI workflows, docs finalization, demo package.

---

### DE tasks

- [ ] **Performance pass**: `EXPLAIN ANALYZE` on 5 key queries; add any missing indexes; target < 300ms for all endpoints locally

### BE tasks

- [ ] **Structured logging**: `structlog` or `logging` with JSON formatter; request ID middleware
- [ ] **Audit log review endpoint**: `GET /admin/audit-log?accessed_id=...&from=...&to=...` (admin only)
- [ ] **`GET /admin/run_history`**: list `data_generation_runs`

### FE tasks

- [ ] UI polish: loading skeletons, error boundaries, empty state illustrations
- [ ] Responsive layout (sidebar collapses on narrow screens)

### DS tasks

- [ ] Write `docs/model_cards.md`: archetype descriptions, trajectory model inputs/outputs, simulation assumptions
- [ ] Evaluation notebook: archetype silhouette score, trajectory AUC on held-out employees

### PM tasks

- [ ] Demo script: seed → generate → run pipeline → show org overview → drill team → employee profile → accept recommendation → run simulation
- [ ] Acceptance checklist

### All

- [ ] **`.github/workflows/backend.yml`**:
  - `ruff check` + `mypy`
  - `pytest tests/` with test DB (Postgres service container)
- [ ] **`.github/workflows/frontend.yml`**:
  - `tsc --noEmit`
  - `vitest run`
  - `vite build`

---

### S9 Acceptance Criteria

- [ ] All key API endpoints respond in < 300ms locally against seeded 300-employee dataset
- [ ] `pytest` green on main branch
- [ ] `vitest run` green on main branch
- [ ] Demo script runs end-to-end from clean repo clone

---

## Quick Reference

### Running locally (after S1)

```bash
# Start DB + API
docker compose up

# Apply migrations
cd backend && alembic upgrade head

# Generate synthetic data (seed reproducible)
curl -X POST "http://localhost:8000/admin/generate?seed=20260406&start_date=2025-04-07&end_date=2026-04-06" \
  -H "Authorization: Bearer admin-token"

# Run pipeline for today
curl -X POST "http://localhost:8000/admin/run_pipeline?snapshot_date=2026-04-06" \
  -H "Authorization: Bearer admin-token"

# Run frontend
cd frontend && npm run dev
```

### Token reference (dev only)

| Token | Roles | Use |
|---|---|---|
| `admin-token` | admin, org_analytics | Full access |
| `manager-token` | manager | Team + direct reports only |
| `analyst-token` | org_analytics | Aggregates only, no individual drill-down |

### Environment variables

```bash
# backend/.env
DATABASE_URL=postgresql://wsip:wsip_dev@localhost:5432/wsip
WSIP_TOKENS={"admin-token":{"user_id":"...","username":"admin","roles":["admin","org_analytics"]},...}

# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TOKEN=admin-token
```
