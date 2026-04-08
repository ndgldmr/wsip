"""
ETL feature builder — populates employee_feature_snapshots for a given snapshot_date.

One large CTE aggregates fact_employee_daily_activity across 7 / 14 / 30 / 90-day
windows plus a prior-30d window for self-baseline computation.  Skill utilization
and project allocation come from separate subqueries.

Idempotent: DELETE WHERE snapshot_date = :snap before INSERT.
Returns the number of rows inserted.
"""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dk(d: date) -> int:
    """Convert a date to an integer date_key (YYYYMMDD)."""
    return int(d.strftime("%Y%m%d"))


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_FEATURE_CTE = """
WITH
-- Active employee dimension rows
emp AS (
    SELECT employee_key, employee_id, role_family, job_level
    FROM   dim_employee
    WHERE  is_current = true
),
-- 90-day window: commits + avg daily activity score
w90 AS (
    SELECT f.employee_key,
           COALESCE(SUM(f.commit_count),  0)                                   AS commits_90d,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0) AS act_score_90d
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_90 AND :dk_snap
    GROUP  BY f.employee_key
),
-- 30-day window: core rolling metrics
w30 AS (
    SELECT f.employee_key,
           COALESCE(SUM(f.commit_count),          0)     AS commits_30d,
           COALESCE(SUM(f.pr_merged_count),        0)     AS prs_merged_30d,
           COALESCE(SUM(f.code_review_count),      0)     AS reviews_30d,
           COALESCE(SUM(f.experiment_count),       0)     AS experiment_runs_30d,
           COALESCE(SUM(f.meeting_minutes) / 60.0, 0)     AS meeting_load_hours_30d,
           -- collaboration breadth: distinct review + organised meeting touches
           COALESCE(SUM(f.code_review_count + f.meetings_organized), 0)          AS collab_breadth_30d,
           -- cross-team proxy: fraction of meetings the employee organised
           CASE WHEN SUM(f.meeting_count) > 0
                THEN LEAST(SUM(f.meetings_organized)::numeric / SUM(f.meeting_count), 1.0)
                ELSE 0 END                                                        AS cross_team_rate_30d,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0)  AS act_score_30d,
           -- knowledge creation: docs + research artefacts
           COALESCE(SUM(f.doc_event_count + f.research_artifact_count), 0)        AS knowledge_raw_30d
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_30 AND :dk_snap
    GROUP  BY f.employee_key
),
-- Prior 30-day window (for self baseline)
w30_prior AS (
    SELECT f.employee_key,
           NULLIF(SUM(f.commit_count), 0)                                         AS commits_prior,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0)  AS act_score_prior
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_60 AND :dk_31
    GROUP  BY f.employee_key
),
-- 14-day window
w14 AS (
    SELECT f.employee_key,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0)  AS act_score_14d
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_14 AND :dk_snap
    GROUP  BY f.employee_key
),
-- Prior 14-day window
w14_prior AS (
    SELECT f.employee_key,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0)  AS act_score_14d_prior
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_28 AND :dk_15
    GROUP  BY f.employee_key
),
-- 7-day window
w7 AS (
    SELECT f.employee_key,
           COALESCE(SUM(f.commit_count),                    0) AS commits_7d,
           COALESCE(SUM(f.pr_opened_count + f.pr_merged_count), 0) AS prs_7d,
           COALESCE(SUM(f.code_review_count),               0) AS reviews_7d,
           COALESCE(SUM(f.meeting_minutes) / 60.0,          0) AS meeting_hours_7d,
           COALESCE(AVG(CASE WHEN f.is_active THEN f.contribution_units END), 0) AS act_score_7d
    FROM   fact_employee_daily_activity f
    WHERE  f.date_key BETWEEN :dk_7 AND :dk_snap
    GROUP  BY f.employee_key
),
-- Role+level cohort average commits over 30d (for cohort baseline)
cohort AS (
    SELECT e.role_family,
           e.job_level,
           NULLIF(AVG(COALESCE(w.commits_30d, 0)), 0) AS cohort_commits_30d
    FROM   emp e
    LEFT JOIN w30 w ON w.employee_key = e.employee_key
    GROUP  BY e.role_family, e.job_level
),
-- Active project allocation
proj AS (
    SELECT epa.employee_id,
           COUNT(DISTINCT epa.project_id)                              AS active_project_count,
           COALESCE(LEAST(SUM(epa.allocation_pct) / 100.0, 1.0), 0)   AS proj_util_score
    FROM   employee_project_assignments epa
    WHERE  epa.start_date <= :snap
      AND  (epa.end_date IS NULL OR epa.end_date >= :snap)
    GROUP  BY epa.employee_id
),
-- Skill utilization: fraction of employee's skills signalled in past 90d
skill_util AS (
    SELECT e.employee_id,
           COUNT(DISTINCT ss.skill_id)::numeric
               / NULLIF(ts.total_skills, 0)                AS util_rate
    FROM   emp e
    JOIN   fact_employee_skill_signal ss ON ss.employee_key = e.employee_key
    JOIN   (
               SELECT employee_id, COUNT(*) AS total_skills,
                      AVG(confidence_score) AS avg_confidence
               FROM   employee_skills
               WHERE  (valid_to IS NULL OR valid_to >= :snap)
               GROUP  BY employee_id
           ) ts ON ts.employee_id = e.employee_id
    WHERE  ss.date_key BETWEEN :dk_90 AND :dk_snap
      AND  (ss.training_count > 0 OR ss.code_review_count > 0 OR ss.experiment_count > 0)
    GROUP  BY e.employee_id, ts.total_skills
),
skill_depth AS (
    SELECT employee_id, COALESCE(AVG(confidence_score), 0) AS avg_confidence
    FROM   employee_skills
    WHERE  (valid_to IS NULL OR valid_to >= :snap)
    GROUP  BY employee_id
)
SELECT
    e.employee_id,
    e.employee_key,
    -- 7d
    COALESCE(w7.commits_7d,        0)                                       AS commits_7d,
    COALESCE(w7.prs_7d,            0)                                       AS prs_7d,
    COALESCE(w7.reviews_7d,        0)                                       AS reviews_7d,
    COALESCE(w7.meeting_hours_7d,  0)                                       AS meeting_hours_7d,
    LEAST(COALESCE(w7.act_score_7d, 0) / 2.0, 1.0)                         AS activity_score_7d,
    -- 14d drop (signed; NULL if no prior)
    CASE WHEN COALESCE(p14.act_score_14d_prior, 0) > 0
         THEN (COALESCE(w14.act_score_14d, 0) - p14.act_score_14d_prior)
               / p14.act_score_14d_prior
         ELSE NULL
    END                                                                      AS activity_drop_14d,
    -- 30d
    COALESCE(w30.commits_30d,            0)                                 AS commits_30d,
    COALESCE(w30.prs_merged_30d,         0)                                 AS prs_merged_30d,
    COALESCE(w30.reviews_30d,            0)                                 AS reviews_30d,
    COALESCE(w30.experiment_runs_30d,    0)                                 AS experiment_runs_30d,
    COALESCE(w30.meeting_load_hours_30d, 0)                                 AS meeting_load_hours_30d,
    COALESCE(w30.collab_breadth_30d,     0)                                 AS collaboration_breadth_30d,
    COALESCE(w30.cross_team_rate_30d,    0)                                 AS cross_team_interaction_rate_30d,
    -- collaboration centrality proxy: (reviews + meetings organised) normalised to [0,1]
    LEAST(COALESCE(w30.collab_breadth_30d, 0)::numeric / 60.0, 1.0)        AS collaboration_centrality_30d,
    -- knowledge creation: docs + artefacts, normalised [0,1] at ~20 items/month = 1.0
    LEAST(COALESCE(w30.knowledge_raw_30d, 0)::numeric / 20.0, 1.0)         AS knowledge_creation_score,
    LEAST(COALESCE(w30.act_score_30d,    0) / 2.0, 1.0)                    AS activity_score_30d,
    -- 30d activity drop vs prior 30d (signed)
    CASE WHEN COALESCE(p30.act_score_prior, 0) > 0
         THEN (COALESCE(w30.act_score_30d, 0) - p30.act_score_prior) / p30.act_score_prior
         ELSE NULL
    END                                                                      AS activity_drop_30d,
    -- 90d
    COALESCE(w90.commits_90d,   0)                                          AS commits_90d,
    LEAST(COALESCE(w90.act_score_90d, 0) / 2.0, 1.0)                       AS activity_score_90d,
    -- allocation
    COALESCE(p.active_project_count,  0)                                    AS active_project_count,
    COALESCE(p.proj_util_score,       0)                                    AS project_allocation_utilization_score,
    -- skill utilization and depth
    LEAST(COALESCE(su.util_rate, 0), 1.0)                                   AS skill_utilization_score,
    LEAST(COALESCE(sd.avg_confidence, 0), 1.0)                              AS skill_depth_score,
    -- self baseline: commits_30d vs prior_30d
    CASE WHEN p30.commits_prior IS NOT NULL
         THEN COALESCE(w30.commits_30d, 0)::numeric / p30.commits_prior - 1.0
         ELSE NULL
    END                                                                      AS commits_30d_vs_self_baseline,
    -- cohort baseline
    CASE WHEN c.cohort_commits_30d IS NOT NULL
         THEN COALESCE(w30.commits_30d, 0)::numeric / c.cohort_commits_30d - 1.0
         ELSE NULL
    END                                                                      AS commits_30d_vs_role_baseline,
    -- activity vs self baseline
    CASE WHEN COALESCE(p30.act_score_prior, 0) > 0
         THEN (COALESCE(w30.act_score_30d, 0) - p30.act_score_prior) / p30.act_score_prior
         ELSE NULL
    END                                                                      AS activity_30d_vs_self_baseline
FROM       emp e
LEFT JOIN  w7        ON w7.employee_key    = e.employee_key
LEFT JOIN  w14       ON w14.employee_key   = e.employee_key
LEFT JOIN  w14_prior p14 ON p14.employee_key = e.employee_key
LEFT JOIN  w30       ON w30.employee_key   = e.employee_key
LEFT JOIN  w30_prior p30 ON p30.employee_key = e.employee_key
LEFT JOIN  w90       ON w90.employee_key   = e.employee_key
LEFT JOIN  proj      p  ON p.employee_id   = e.employee_id
LEFT JOIN  skill_util su ON su.employee_id = e.employee_id
LEFT JOIN  skill_depth sd ON sd.employee_id = e.employee_id
LEFT JOIN  cohort    c  ON c.role_family = e.role_family AND c.job_level = e.job_level
"""

_INSERT_SQL = """
INSERT INTO employee_feature_snapshots (
    employee_id, snapshot_date, employee_key,
    commits_7d, prs_7d, reviews_7d, meeting_hours_7d, activity_score_7d,
    activity_drop_14d,
    commits_30d, prs_merged_30d, reviews_30d, experiment_runs_30d,
    meeting_load_hours_30d, collaboration_breadth_30d,
    cross_team_interaction_rate_30d, collaboration_centrality_30d,
    knowledge_creation_score, activity_score_30d, activity_drop_30d,
    commits_90d, activity_score_90d,
    active_project_count, project_allocation_utilization_score,
    skill_utilization_score, skill_depth_score,
    commits_30d_vs_self_baseline, commits_30d_vs_role_baseline,
    activity_30d_vs_self_baseline
)
SELECT
    employee_id, :snap, employee_key,
    commits_7d, prs_7d, reviews_7d, meeting_hours_7d, activity_score_7d,
    activity_drop_14d,
    commits_30d, prs_merged_30d, reviews_30d, experiment_runs_30d,
    meeting_load_hours_30d, collaboration_breadth_30d,
    cross_team_interaction_rate_30d, collaboration_centrality_30d,
    knowledge_creation_score, activity_score_30d, activity_drop_30d,
    commits_90d, activity_score_90d,
    active_project_count, project_allocation_utilization_score,
    skill_utilization_score, skill_depth_score,
    commits_30d_vs_self_baseline, commits_30d_vs_role_baseline,
    activity_30d_vs_self_baseline
FROM ({cte}) AS _features
"""


# ---------------------------------------------------------------------------
# public function
# ---------------------------------------------------------------------------

def build_feature_snapshots(snapshot_date: date, session: Session) -> int:
    """Populate employee_feature_snapshots for snapshot_date.

    Aggregates fact_employee_daily_activity across rolling windows to produce
    per-employee feature rows.  Metric score columns are left NULL — they are
    written in the subsequent metrics step.

    Idempotent: existing rows for snapshot_date are deleted before insert.
    Returns the number of rows inserted.
    """
    snap = snapshot_date
    params = {
        "snap":   snap,
        "dk_snap": _dk(snap),
        "dk_7":   _dk(snap - timedelta(days=6)),
        "dk_14":  _dk(snap - timedelta(days=13)),
        "dk_15":  _dk(snap - timedelta(days=14)),
        "dk_28":  _dk(snap - timedelta(days=27)),
        "dk_30":  _dk(snap - timedelta(days=29)),
        "dk_31":  _dk(snap - timedelta(days=30)),
        "dk_60":  _dk(snap - timedelta(days=59)),
        "dk_90":  _dk(snap - timedelta(days=89)),
    }

    # idempotency
    session.execute(
        text("DELETE FROM employee_feature_snapshots WHERE snapshot_date = :snap"),
        {"snap": snap},
    )

    result = session.execute(
        text(_INSERT_SQL.format(cte=_FEATURE_CTE)),
        params,
    )
    session.flush()
    return result.rowcount
