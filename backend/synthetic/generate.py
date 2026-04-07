"""
Synthetic data generator.

Produces a seeded, reproducible dataset of canonical entities + raw events
for a configurable number of employees over a date range.

Usage:
    gen = SyntheticGenerator(seed=20260406, db_url=settings.database_url)
    run_id = gen.generate(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import sqlalchemy as sa
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models.canonical import (
    DataGenerationRun,
    Employee,
    EmployeeProjectAssignment,
    EmployeeSkill,
    EmployeeSnapshot,
    Org,
    Project,
    ProjectSkillRequirement,
    Repo,
    Skill,
    Team,
)
from models.raw_events import (
    ChatMetadataEvent,
    CodeReviewEvent,
    DocumentEvent,
    ExperimentRunEvent,
    GitCommitEvent,
    MeetingEvent,
    PullRequestEvent,
    ResearchArtifactEvent,
    ResumeSkillInference,
    TaskEvent,
    TrainingCompletionEvent,
)
from synthetic.personas import PERSONA_NAMES, PERSONA_WEIGHTS, PERSONAS, PersonaConfig
from synthetic.shocks import (
    inject_burnout_episode,
    inject_leave_of_absence,
    inject_manager_change,
    inject_research_breakthrough,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SKILL_CATEGORIES = ["languages", "frameworks", "infrastructure", "ml_methods", "domain", "tooling"]
_SKILL_NAMES_BY_CATEGORY: dict[str, list[str]] = {
    "languages": ["Python", "Go", "Rust", "TypeScript", "Scala", "Julia", "C++", "Java", "R", "Kotlin"],
    "frameworks": ["FastAPI", "Django", "React", "PyTorch", "TensorFlow", "JAX", "Spark", "Kafka", "gRPC", "Ray"],
    "infrastructure": ["Kubernetes", "Terraform", "AWS", "GCP", "Azure", "Docker", "Airflow", "dbt", "Prometheus", "Grafana"],
    "ml_methods": ["Transformers", "RL", "Causal Inference", "Bayesian Optimization", "XGBoost", "VAE", "Diffusion Models", "Graph NN", "RLHF", "RAG"],
    "domain": ["NLP", "Computer Vision", "Time Series", "RecSys", "Genomics", "Drug Discovery", "Robotics", "Autonomous Vehicles", "Cybersecurity", "FinTech"],
    "tooling": ["Git", "CI/CD", "Jira", "Confluence", "Slack", "Notion", "dbt", "Snowflake", "BigQuery", "Metaflow"],
}
_ORG_NAMES = ["Cortex Labs", "Meridian AI", "Helix Research"]
_MEETING_TYPES = ["standup", "planning", "review", "1on1", "all-hands", "interview"]
_DOC_TYPES = ["spec", "wiki", "proposal", "notes", "report"]
_DOC_ACTIONS = ["create", "edit", "share", "comment"]
_TASK_TYPES = ["feature", "bug", "chore", "review"]
_TASK_ACTIONS = ["opened", "closed", "assigned", "commented"]
_TASK_PRIORITIES = ["high", "medium", "low"]
_TASK_PRIORITY_WEIGHTS = [0.2, 0.5, 0.3]
_CHANNEL_TYPES = ["dm", "public", "private", "announcement"]
_CHANNEL_WEIGHTS = [0.4, 0.3, 0.25, 0.05]
_REVIEW_STATES = ["approved", "changes_requested", "commented"]
_REVIEW_STATE_WEIGHTS = [0.5, 0.3, 0.2]
_EXPERIMENT_TYPES = ["ab_test", "model_train", "simulation", "analysis"]
_ARTIFACT_TYPES = ["paper", "report", "dataset", "model", "notebook"]
_TRAINING_TYPES = ["course", "certification", "workshop", "conference"]
_INFERENCE_SOURCES = ["resume", "github", "linkedin"]
_FUNCTION_TYPES = ["engineering", "research", "product", "operations", "management"]
_PROFICIENCY_LEVELS = ["beginner", "intermediate", "advanced", "expert"]
_EVIDENCE_TYPES = ["self_reported", "manager_assessed", "inferred"]
_STAFFING_SOURCES = ["internal", "rotational", "external"]
_PROJECT_TYPES = ["product", "research", "platform", "tooling", "experiment"]
_PRIORITY_TIERS = ["p0", "p1", "p2", "p3"]

# Quarter-end: last 10 business days of each quarter
# We precompute a set of dates at generate() time


class SyntheticGenerator:
    def __init__(self, seed: int, db_url: str) -> None:
        self.seed = seed
        self.db_url = db_url
        self.rng = np.random.default_rng(seed)
        self.fake = Faker()
        Faker.seed(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
    ) -> uuid.UUID:
        """
        Generate and persist a full synthetic dataset.

        Returns the run_id of the DataGenerationRun record.
        """
        engine = create_engine(self.db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        try:
            # --- Run ID and prefix (scopes unique fields across runs) ---
            run_id = uuid.uuid4()
            run_prefix = run_id.hex[:8]  # short prefix for unique refs

            # --- Precompute calendar helpers ----------------------------
            all_dates = self._date_range(start_date, end_date)
            quarter_end_spike_dates = self._quarter_end_spike_dates(all_dates)

            # --- Entity layer (flush after each tier to satisfy FK ordering) ---
            org_ids = self._gen_orgs(session, n_orgs)
            session.flush()

            team_ids = self._gen_teams(session, org_ids, n_teams)
            session.flush()

            skill_ids = self._gen_skills(session, n_skills)
            session.flush()

            repo_ids = self._gen_repos(session, team_ids, n_repos)
            session.flush()

            employee_ids, employee_personas, employee_hire_dates = self._gen_employees(
                session, org_ids, team_ids, n_employees, start_date, run_prefix
            )
            session.flush()

            project_ids = self._gen_projects(session, team_ids, employee_ids, n_projects, start_date, end_date)
            session.flush()

            self._gen_employee_skills(session, employee_ids, skill_ids)
            self._gen_project_assignments(session, employee_ids, project_ids, start_date)
            self._gen_project_skill_requirements(session, project_ids, skill_ids)
            self._gen_employee_snapshots(session, employee_ids, employee_hire_dates, start_date)
            self._gen_resume_skill_inferences(session, employee_ids, skill_ids, start_date)
            session.commit()

            # --- Raw events (one table at a time for bounded memory) ----
            self._gen_git_commits(session, employee_ids, repo_ids, employee_personas, employee_hire_dates, all_dates, quarter_end_spike_dates)
            session.commit()

            self._gen_pull_requests(session, employee_ids, repo_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_code_reviews(session, employee_ids, repo_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_experiments(session, employee_ids, project_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_research_artifacts(session, employee_ids, project_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_documents(session, employee_ids, employee_personas, employee_hire_dates, all_dates, quarter_end_spike_dates)
            session.commit()

            self._gen_tasks(session, employee_ids, project_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_meetings(session, employee_ids, employee_personas, employee_hire_dates, all_dates, quarter_end_spike_dates)
            session.commit()

            self._gen_chat(session, employee_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            self._gen_training(session, employee_ids, skill_ids, employee_personas, employee_hire_dates, all_dates)
            session.commit()

            # --- Shocks -------------------------------------------------
            self._apply_shocks(session, employee_ids, employee_personas, project_ids, start_date, end_date)
            session.commit()

            # --- Generation run record ----------------------------------
            run = DataGenerationRun(
                run_id=run_id,
                seed=self.seed,
                start_date=start_date,
                end_date=end_date,
                employee_count=n_employees,
                notes_json={
                    "n_orgs": n_orgs,
                    "n_teams": n_teams,
                    "n_projects": n_projects,
                    "n_repos": n_repos,
                    "n_skills": n_skills,
                    "date_range_days": len(all_dates),
                },
            )
            session.add(run)
            session.commit()
            return run_id

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Calendar helpers
    # ------------------------------------------------------------------

    def _date_range(self, start: date, end: date) -> list[date]:
        days = (end - start).days + 1
        return [start + timedelta(days=i) for i in range(days)]

    def _weekday_multiplier(self, d: date) -> float:
        dow = d.weekday()  # 0=Mon
        if dow < 4:
            return 1.0
        if dow == 4:
            return 0.8
        return 0.1  # Sat, Sun

    def _trajectory_multiplier(self, d: date, start: date, end: date, trajectory: str) -> float:
        if trajectory == "stable":
            return 1.0
        total = max((end - start).days, 1)
        progress = (d - start).days / total  # 0.0 → 1.0
        if trajectory == "rising":
            return 0.3 + 0.7 * progress
        if trajectory == "declining":
            return 1.0 - 0.7 * progress
        return 1.0

    def _quarter_end_spike_dates(self, all_dates: list[date]) -> set[date]:
        """Return dates that fall in the last 10 business days of a quarter."""
        spike_dates: set[date] = set()
        quarters = {(d.year, (d.month - 1) // 3) for d in all_dates}
        for year, q in quarters:
            q_end_month = (q + 1) * 3
            if q_end_month == 12:
                q_end = date(year, 12, 31)
            else:
                q_end = date(year, q_end_month, 1) - timedelta(days=1)
            biz_count = 0
            check = q_end
            while biz_count < 10:
                if check.weekday() < 5:
                    spike_dates.add(check)
                    biz_count += 1
                check -= timedelta(days=1)
                if check.year < year:
                    break
        return spike_dates

    def _ts_on_day(self, d: date, hour_range: tuple[int, int] = (8, 18)) -> datetime:
        """Random datetime on a given calendar day within working hours."""
        hour = int(self.rng.integers(hour_range[0], hour_range[1]))
        minute = int(self.rng.integers(0, 60))
        return datetime(d.year, d.month, d.day, hour, minute)

    def _is_after_hire(self, d: date, hire_date: date) -> bool:
        return d >= hire_date

    # ------------------------------------------------------------------
    # Entity generators
    # ------------------------------------------------------------------

    def _gen_orgs(self, session: Session, n: int) -> list[uuid.UUID]:
        ids = []
        for i in range(min(n, len(_ORG_NAMES))):
            org_id = uuid.uuid4()
            session.add(Org(org_id=org_id, org_name=_ORG_NAMES[i]))
            ids.append(org_id)
        return ids

    def _gen_teams(self, session: Session, org_ids: list[uuid.UUID], n: int) -> list[uuid.UUID]:
        ids = []
        for i in range(n):
            team_id = uuid.uuid4()
            org_id = org_ids[int(self.rng.integers(0, len(org_ids)))]
            session.add(Team(
                team_id=team_id,
                team_name=f"Team {self.fake.word().capitalize()} {i+1}",
                org_id=org_id,
                function_type=_FUNCTION_TYPES[int(self.rng.integers(0, len(_FUNCTION_TYPES)))],
                mission_area=self.fake.bs(),
            ))
            ids.append(team_id)
        return ids

    def _gen_skills(self, session: Session, n: int) -> list[uuid.UUID]:
        ids = []
        skill_pool: list[tuple[str, str]] = []
        for cat, names in _SKILL_NAMES_BY_CATEGORY.items():
            for name in names:
                skill_pool.append((name, cat))

        chosen = self.rng.choice(len(skill_pool), size=min(n, len(skill_pool)), replace=False)
        for idx in chosen:
            name, cat = skill_pool[int(idx)]
            skill_id = uuid.uuid4()
            session.add(Skill(skill_id=skill_id, skill_name=name, skill_category=cat))
            ids.append(skill_id)
        return ids

    def _gen_repos(self, session: Session, team_ids: list[uuid.UUID], n: int) -> list[uuid.UUID]:
        ids = []
        for i in range(n):
            repo_id = uuid.uuid4()
            team_id = team_ids[int(self.rng.integers(0, len(team_ids)))]
            session.add(Repo(
                repo_id=repo_id,
                source_system="github",
                repo_name=f"{self.fake.word()}-{self.fake.word()}",
                owning_team_id=team_id,
                is_monorepo=bool(self.rng.random() < 0.1),
            ))
            ids.append(repo_id)
        return ids

    def _gen_employees(
        self,
        session: Session,
        org_ids: list[uuid.UUID],
        team_ids: list[uuid.UUID],
        n: int,
        start_date: date,
        run_prefix: str = "",
    ) -> tuple[list[uuid.UUID], list[str], list[date]]:
        """Returns (employee_ids, persona_names, hire_dates)."""
        weights = np.array(PERSONA_WEIGHTS, dtype=float)
        weights /= weights.sum()

        ids: list[uuid.UUID] = []
        personas: list[str] = []
        hire_dates: list[date] = []

        persona_indices = self.rng.choice(len(PERSONA_NAMES), size=n, p=weights)

        for i in range(n):
            emp_id = uuid.uuid4()
            persona_name = PERSONA_NAMES[int(persona_indices[i])]
            persona = PERSONAS[persona_name]

            org_id = org_ids[int(self.rng.integers(0, len(org_ids)))]
            team_id = team_ids[int(self.rng.integers(0, len(team_ids)))]
            job_level = persona.job_levels[int(self.rng.integers(0, len(persona.job_levels)))]

            # New hires start after generation start; most are already hired
            if self.rng.random() < 0.1:
                days_offset = int(self.rng.integers(0, 180))
                hire_date = start_date + timedelta(days=days_offset)
            else:
                days_before = int(self.rng.integers(30, 1460))
                hire_date = start_date - timedelta(days=days_before)

            ref_prefix = f"{run_prefix}-" if run_prefix else ""
            session.add(Employee(
                employee_id=emp_id,
                external_employee_ref=f"{ref_prefix}EMP{i+1:05d}",
                full_name=self.fake.name(),
                preferred_name=None,
                email=f"{ref_prefix}emp{i+1}@wsip-synthetic.internal",
                role_title=self.fake.job(),
                role_family=persona.role_family,
                job_level=job_level,
                employment_status="active",
                manager_employee_id=None,  # wired below
                team_id=team_id,
                org_id=org_id,
                hire_date=hire_date,
            ))
            ids.append(emp_id)
            personas.append(persona_name)
            hire_dates.append(hire_date)

        session.flush()

        # Wire managers — each non-management employee gets a random manager
        manager_pool = [ids[i] for i in range(n) if PERSONAS[personas[i]].role_family == "management"]
        if not manager_pool:
            manager_pool = ids[:max(1, n // 10)]

        for i, emp_id in enumerate(ids):
            if PERSONAS[personas[i]].role_family != "management":
                mgr = manager_pool[int(self.rng.integers(0, len(manager_pool)))]
                if mgr != emp_id:
                    session.execute(
                        sa.update(Employee).where(Employee.employee_id == emp_id).values(manager_employee_id=mgr)
                    )
        session.flush()
        return ids, personas, hire_dates

    def _gen_projects(
        self,
        session: Session,
        team_ids: list[uuid.UUID],
        employee_ids: list[uuid.UUID],
        n: int,
        start_date: date,
        end_date: date,
    ) -> list[uuid.UUID]:
        ids = []
        total_days = (end_date - start_date).days
        for i in range(n):
            proj_id = uuid.uuid4()
            team_id = team_ids[int(self.rng.integers(0, len(team_ids)))]
            owner_id = employee_ids[int(self.rng.integers(0, len(employee_ids)))]
            proj_start_offset = int(self.rng.integers(0, max(1, total_days // 2)))
            proj_start = start_date + timedelta(days=proj_start_offset)
            session.add(Project(
                project_id=proj_id,
                project_name=f"{self.fake.catch_phrase()} v{i+1}",
                project_type=_PROJECT_TYPES[int(self.rng.integers(0, len(_PROJECT_TYPES)))],
                priority_tier=_PRIORITY_TIERS[int(self.rng.integers(0, len(_PRIORITY_TIERS)))],
                status="active",
                owner_employee_id=owner_id,
                owning_team_id=team_id,
                start_date=proj_start,
                target_end_date=end_date,
            ))
            ids.append(proj_id)
        return ids

    def _gen_employee_skills(
        self, session: Session, employee_ids: list[uuid.UUID], skill_ids: list[uuid.UUID]
    ) -> None:
        for emp_id in employee_ids:
            n_skills = int(self.rng.integers(3, 12))
            chosen = self.rng.choice(len(skill_ids), size=min(n_skills, len(skill_ids)), replace=False)
            for idx in chosen:
                session.add(EmployeeSkill(
                    employee_id=emp_id,
                    skill_id=skill_ids[int(idx)],
                    proficiency_level=_PROFICIENCY_LEVELS[int(self.rng.integers(0, 4))],
                    evidence_type=_EVIDENCE_TYPES[int(self.rng.integers(0, 3))],
                    confidence_score=round(float(self.rng.uniform(0.4, 1.0)), 4),
                    valid_from=date(2020, 1, 1),
                ))

    def _gen_project_assignments(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        project_ids: list[uuid.UUID],
        start_date: date,
    ) -> None:
        for emp_id in employee_ids:
            n_proj = int(self.rng.integers(1, 4))
            chosen = self.rng.choice(len(project_ids), size=min(n_proj, len(project_ids)), replace=False)
            for idx in chosen:
                session.add(EmployeeProjectAssignment(
                    employee_id=emp_id,
                    project_id=project_ids[int(idx)],
                    assignment_role="contributor",
                    allocation_pct=round(float(self.rng.uniform(0.25, 1.0)), 2),
                    start_date=start_date,
                    staffing_source=_STAFFING_SOURCES[int(self.rng.integers(0, 3))],
                ))

    def _gen_project_skill_requirements(
        self,
        session: Session,
        project_ids: list[uuid.UUID],
        skill_ids: list[uuid.UUID],
    ) -> None:
        for proj_id in project_ids:
            n_req = int(self.rng.integers(2, 6))
            chosen = self.rng.choice(len(skill_ids), size=min(n_req, len(skill_ids)), replace=False)
            for idx in chosen:
                session.add(ProjectSkillRequirement(
                    project_id=proj_id,
                    skill_id=skill_ids[int(idx)],
                    desired_level=_PROFICIENCY_LEVELS[int(self.rng.integers(1, 4))],
                    weight=round(float(self.rng.uniform(0.1, 1.0)), 4),
                ))

    def _gen_employee_snapshots(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        hire_dates: list[date],
        snapshot_date: date,
    ) -> None:
        for emp_id, hire_date in zip(employee_ids, hire_dates):
            emp = session.get(Employee, emp_id)
            if emp is None:
                continue
            tenure = max(0, (snapshot_date - hire_date).days)
            session.add(EmployeeSnapshot(
                employee_id=emp_id,
                snapshot_date=snapshot_date,
                role_title=emp.role_title,
                role_family=emp.role_family,
                job_level=emp.job_level,
                manager_employee_id=emp.manager_employee_id,
                team_id=emp.team_id,
                org_id=emp.org_id,
                tenure_days=tenure,
            ))

    def _gen_resume_skill_inferences(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        skill_ids: list[uuid.UUID],
        inferred_at_date: date,
    ) -> None:
        inferred_ts = datetime(inferred_at_date.year, inferred_at_date.month, inferred_at_date.day, 0, 0, 0)
        for emp_id in employee_ids:
            n_inferred = int(self.rng.integers(2, 8))
            chosen = self.rng.choice(len(skill_ids), size=min(n_inferred, len(skill_ids)), replace=False)
            for idx in chosen:
                session.add(ResumeSkillInference(
                    employee_id=emp_id,
                    skill_id=skill_ids[int(idx)],
                    inferred_score=round(float(self.rng.uniform(0.3, 1.0)), 4),
                    inference_source=_INFERENCE_SOURCES[int(self.rng.integers(0, 3))],
                    inferred_at=inferred_ts,
                ))

    # ------------------------------------------------------------------
    # Raw event generators
    # ------------------------------------------------------------------

    def _effective_lambda(
        self,
        base_lambda: float,
        d: date,
        hire_date: date,
        start_date: date,
        end_date: date,
        trajectory: str,
        weekday_mult: float,
        spike_mult: float = 1.0,
    ) -> float:
        if not self._is_after_hire(d, hire_date):
            return 0.0
        traj = self._trajectory_multiplier(d, start_date, end_date, trajectory)
        return base_lambda * weekday_mult * traj * spike_mult

    def _gen_git_commits(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        repo_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
        spike_dates: set[date],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> None:
        _start = all_dates[0] if start_date is None else start_date
        _end = all_dates[-1] if end_date is None else end_date
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.commit_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    rows.append({
                        "commit_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "repo_id": repo_ids[int(self.rng.integers(0, len(repo_ids)))],
                        "commit_ts": self._ts_on_day(d),
                        "commit_hash": self.fake.sha1(),
                        "lines_added": int(self.rng.integers(1, 300)),
                        "lines_deleted": int(self.rng.integers(0, 100)),
                        "files_changed": int(self.rng.integers(1, 20)),
                        "is_merge_commit": bool(self.rng.random() < 0.1),
                        "branch_name": f"feature/{self.fake.word()}",
                        "commit_message": None,
                    })
        if rows:
            session.execute(sa.insert(GitCommitEvent), rows)

    def _gen_pull_requests(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        repo_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.pr_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    state = self.rng.choice(["open", "closed", "merged"], p=[0.1, 0.3, 0.6])
                    opened = self._ts_on_day(d)
                    merged_at = (opened + timedelta(hours=int(self.rng.integers(1, 72)))) if state == "merged" else None
                    closed_at = merged_at if state == "merged" else (
                        (opened + timedelta(hours=int(self.rng.integers(1, 24)))) if state == "closed" else None
                    )
                    rows.append({
                        "pr_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "repo_id": repo_ids[int(self.rng.integers(0, len(repo_ids)))],
                        "opened_at": opened,
                        "closed_at": closed_at,
                        "merged_at": merged_at,
                        "state": str(state),
                        "additions": int(self.rng.integers(1, 500)),
                        "deletions": int(self.rng.integers(0, 200)),
                        "review_count": int(self.rng.integers(0, 5)),
                        "comment_count": int(self.rng.integers(0, 15)),
                        "title": None,
                    })
        if rows:
            session.execute(sa.insert(PullRequestEvent), rows)

    def _gen_code_reviews(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        repo_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.review_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    review_state = str(self.rng.choice(_REVIEW_STATES, p=_REVIEW_STATE_WEIGHTS))
                    rows.append({
                        "review_event_id": uuid.uuid4(),
                        "reviewer_employee_id": emp_id,
                        "pr_author_employee_id": employee_ids[int(self.rng.integers(0, len(employee_ids)))] if len(employee_ids) > 1 else None,
                        "repo_id": repo_ids[int(self.rng.integers(0, len(repo_ids)))],
                        "review_ts": self._ts_on_day(d),
                        "review_state": review_state,
                        "comment_count": int(self.rng.integers(0, 10)),
                        "time_to_review_hours": round(float(self.rng.uniform(0.5, 24.0)), 2),
                    })
        if rows:
            session.execute(sa.insert(CodeReviewEvent), rows)

    def _gen_experiments(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        project_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.experiment_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    compute = round(float(self.rng.uniform(0.5, 48.0)), 2)
                    started = self._ts_on_day(d)
                    rows.append({
                        "experiment_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "project_id": project_ids[int(self.rng.integers(0, len(project_ids)))] if project_ids else None,
                        "started_at": started,
                        "completed_at": started + timedelta(hours=compute),
                        "experiment_type": _EXPERIMENT_TYPES[int(self.rng.integers(0, len(_EXPERIMENT_TYPES)))],
                        "status": "completed",
                        "compute_hours": compute,
                        "outcome_metric_name": "loss",
                        "outcome_metric_value": round(float(self.rng.uniform(0.01, 2.0)), 6),
                    })
        if rows:
            session.execute(sa.insert(ExperimentRunEvent), rows)

    def _gen_research_artifacts(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        project_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.research_artifact_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    rows.append({
                        "artifact_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "project_id": project_ids[int(self.rng.integers(0, len(project_ids)))] if project_ids else None,
                        "created_at": self._ts_on_day(d),
                        "artifact_type": _ARTIFACT_TYPES[int(self.rng.integers(0, len(_ARTIFACT_TYPES)))],
                        "collaboration_count": int(self.rng.integers(0, 5)),
                        "word_count": int(self.rng.integers(500, 8000)),
                        "citation_count": None,
                    })
        if rows:
            session.execute(sa.insert(ResearchArtifactEvent), rows)

    def _gen_documents(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
        spike_dates: set[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                spike = 1.2 if d in spike_dates else 1.0
                lam = self._effective_lambda(p.doc_lambda, d, hire_date, _start, _end, p.trajectory, wm, spike)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    rows.append({
                        "doc_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "event_ts": self._ts_on_day(d),
                        "doc_type": _DOC_TYPES[int(self.rng.integers(0, len(_DOC_TYPES)))],
                        "action": _DOC_ACTIONS[int(self.rng.integers(0, len(_DOC_ACTIONS)))],
                        "word_count": int(self.rng.integers(50, 2000)),
                        "collaborator_count": int(self.rng.integers(0, 5)),
                    })
        if rows:
            session.execute(sa.insert(DocumentEvent), rows)

    def _gen_tasks(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        project_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.task_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    rows.append({
                        "task_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "project_id": project_ids[int(self.rng.integers(0, len(project_ids)))] if project_ids else None,
                        "event_ts": self._ts_on_day(d),
                        "task_type": _TASK_TYPES[int(self.rng.integers(0, len(_TASK_TYPES)))],
                        "action": _TASK_ACTIONS[int(self.rng.integers(0, len(_TASK_ACTIONS)))],
                        "priority": str(self.rng.choice(_TASK_PRIORITIES, p=_TASK_PRIORITY_WEIGHTS)),
                        "story_points": int(self.rng.choice([1, 2, 3, 5, 8])),
                        "cycle_time_hours": round(float(self.rng.uniform(1.0, 120.0)), 2),
                    })
        if rows:
            session.execute(sa.insert(TaskEvent), rows)

    def _gen_meetings(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
        spike_dates: set[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                spike = 1.2 if d in spike_dates else 1.0
                lam = self._effective_lambda(p.meeting_lambda, d, hire_date, _start, _end, p.trajectory, wm, spike)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    dur_mean = p.meeting_duration_mean
                    duration = max(15, int(self.rng.normal(dur_mean, dur_mean * 0.2)))
                    rows.append({
                        "meeting_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "start_ts": self._ts_on_day(d, (8, 17)),
                        "duration_minutes": duration,
                        "meeting_type": _MEETING_TYPES[int(self.rng.integers(0, len(_MEETING_TYPES)))],
                        "attendee_count": int(self.rng.integers(2, 15)),
                        "is_organizer": bool(self.rng.random() < 0.3),
                        "is_external": bool(self.rng.random() < 0.1),
                    })
        if rows:
            session.execute(sa.insert(MeetingEvent), rows)

    def _gen_chat(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for d in all_dates:
                wm = self._weekday_multiplier(d)
                lam = self._effective_lambda(p.chat_lambda, d, hire_date, _start, _end, p.trajectory, wm)
                if lam <= 0:
                    continue
                n = int(self.rng.poisson(lam))
                for _ in range(n):
                    hour = int(self.rng.integers(0, 24))
                    after_hours = hour < 7 or hour >= 20
                    rows.append({
                        "chat_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "event_ts": datetime(d.year, d.month, d.day, hour, int(self.rng.integers(0, 60))),
                        "channel_type": str(self.rng.choice(_CHANNEL_TYPES, p=_CHANNEL_WEIGHTS)),
                        "message_count": int(self.rng.integers(1, 20)),
                        "reaction_count": int(self.rng.integers(0, 5)),
                        "unique_recipients": int(self.rng.integers(1, 10)),
                        "after_hours": after_hours,
                    })
        if rows:
            session.execute(sa.insert(ChatMetadataEvent), rows)

    def _gen_training(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        skill_ids: list[uuid.UUID],
        personas: list[str],
        hire_dates: list[date],
        all_dates: list[date],
    ) -> None:
        _start, _end = all_dates[0], all_dates[-1]
        rows: list[dict[str, Any]] = []
        # Training is sparse — check once per month per employee
        month_starts = sorted({d.replace(day=1) for d in all_dates})
        for emp_id, persona_name, hire_date in zip(employee_ids, personas, hire_dates):
            p = PERSONAS[persona_name]
            for m_start in month_starts:
                if not self._is_after_hire(m_start, hire_date):
                    continue
                if self.rng.random() < p.training_lambda:
                    # Pick a random day in that month
                    month_dates = [d for d in all_dates if d.month == m_start.month and d.year == m_start.year]
                    if not month_dates:
                        continue
                    d = month_dates[int(self.rng.integers(0, len(month_dates)))]
                    duration = round(float(self.rng.uniform(1.0, 40.0)), 2)
                    rows.append({
                        "training_event_id": uuid.uuid4(),
                        "employee_id": emp_id,
                        "skill_id": skill_ids[int(self.rng.integers(0, len(skill_ids)))] if skill_ids else None,
                        "completed_at": self._ts_on_day(d),
                        "training_type": _TRAINING_TYPES[int(self.rng.integers(0, len(_TRAINING_TYPES)))],
                        "topic": self.fake.bs(),
                        "duration_hours": duration,
                    })
        if rows:
            session.execute(sa.insert(TrainingCompletionEvent), rows)

    # ------------------------------------------------------------------
    # Shock application
    # ------------------------------------------------------------------

    def _apply_shocks(
        self,
        session: Session,
        employee_ids: list[uuid.UUID],
        personas: list[str],
        project_ids: list[uuid.UUID],
        start_date: date,
        end_date: date,
    ) -> None:
        """Apply shocks to 5–10 % of employees, chosen deterministically."""
        n = len(employee_ids)
        n_shock = max(1, int(n * self.rng.uniform(0.05, 0.10)))
        shock_indices = self.rng.choice(n, size=n_shock, replace=False)
        total_days = (end_date - start_date).days

        for idx in shock_indices:
            emp_id = employee_ids[int(idx)]
            persona_name = personas[int(idx)]

            shock_type = self.rng.choice(
                ["burnout", "leave", "manager_change", "breakthrough"],
                p=[0.35, 0.25, 0.25, 0.15],
            )

            mid_offset = int(self.rng.integers(30, max(31, total_days - 30)))
            shock_start = start_date + timedelta(days=mid_offset)
            shock_end = shock_start + timedelta(days=int(self.rng.integers(14, 60)))
            if shock_end > end_date:
                shock_end = end_date

            try:
                if shock_type == "burnout":
                    inject_burnout_episode(emp_id, shock_start, shock_end, session)
                elif shock_type == "leave":
                    inject_leave_of_absence(emp_id, shock_start, shock_end, session)
                elif shock_type == "manager_change":
                    other = employee_ids[int(self.rng.integers(0, n))]
                    if other != emp_id:
                        inject_manager_change(emp_id, other, shock_start, session)
                elif shock_type == "breakthrough":
                    proj_id = project_ids[int(self.rng.integers(0, len(project_ids)))] if project_ids else None
                    inject_research_breakthrough(emp_id, shock_start, proj_id, session)
            except Exception:
                session.rollback()
                # Non-fatal: skip this shock and continue
