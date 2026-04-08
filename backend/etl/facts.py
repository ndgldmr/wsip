"""
ETL fact builders — all idempotent via DELETE-then-INSERT for snapshot_date.

Heavy aggregation is done in SQL (via sqlalchemy.text) for performance.
`contribution_units` is computed in Python after the aggregation query so that
role-family-specific weights from etl/config.py are applied uniformly.

Each function returns the number of rows inserted.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from etl.config import CONTRIBUTION_WEIGHTS

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_SIGNAL_CATEGORIES = ("code", "research", "documentation", "collaboration", "strategic", "impact")


def _date_key(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def _compute_contribution_units(row: dict, role_family: str) -> float:
    """Weighted sum of normalised signal units for one employee-day."""
    lines = (row.get("lines_added") or 0) + (row.get("lines_deleted") or 0)
    code_units = lines / 100 + (row.get("files_changed") or 0) / 10
    research_units = (
        (row.get("experiment_count") or 0) * float(row.get("compute_hours") or 0) / 8
        + (row.get("research_artifact_count") or 0) * 2
    )
    documentation_units = (row.get("doc_event_count") or 0) + (row.get("doc_word_count") or 0) / 500
    collaboration_units = (row.get("code_review_count") or 0) + (row.get("meeting_minutes") or 0) / 60 * 0.5
    strategic_units = 0.0
    impact_units = (row.get("story_points_closed") or 0) / 5

    units = {
        "code": code_units,
        "research": research_units,
        "documentation": documentation_units,
        "collaboration": collaboration_units,
        "strategic": strategic_units,
        "impact": impact_units,
    }
    weights = CONTRIBUTION_WEIGHTS.get(role_family, CONTRIBUTION_WEIGHTS["default"])
    return sum(weights[k] * units[k] for k in _SIGNAL_CATEGORIES)


# ---------------------------------------------------------------------------
# fact_employee_daily_activity
# ---------------------------------------------------------------------------

_DAILY_ACTIVITY_CTE = """
WITH
commits AS (
    SELECT employee_id,
           COUNT(*)                           AS commit_count,
           COALESCE(SUM(lines_added),   0)    AS lines_added,
           COALESCE(SUM(lines_deleted), 0)    AS lines_deleted,
           COALESCE(SUM(files_changed), 0)    AS files_changed
    FROM git_commit_events
    WHERE DATE(commit_ts AT TIME ZONE 'UTC') = :snap
      AND is_merge_commit = false
    GROUP BY employee_id
),
prs AS (
    SELECT employee_id,
           COUNT(*)                                        AS pr_opened_count,
           COUNT(*) FILTER (WHERE state = 'merged')       AS pr_merged_count
    FROM pull_request_events
    WHERE DATE(opened_at AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
reviews AS (
    SELECT reviewer_employee_id                   AS employee_id,
           COUNT(*)                               AS code_review_count,
           COALESCE(SUM(comment_count), 0)        AS code_review_comment_count
    FROM code_review_events
    WHERE DATE(review_ts AT TIME ZONE 'UTC') = :snap
    GROUP BY reviewer_employee_id
),
experiments AS (
    SELECT employee_id,
           COUNT(*)                              AS experiment_count,
           COALESCE(SUM(compute_hours), 0)       AS compute_hours
    FROM experiment_run_events
    WHERE DATE(started_at AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
research AS (
    SELECT employee_id,
           COUNT(*) AS research_artifact_count
    FROM research_artifact_events
    WHERE DATE(created_at AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
docs AS (
    SELECT employee_id,
           COUNT(*)                          AS doc_event_count,
           COALESCE(SUM(word_count), 0)      AS doc_word_count
    FROM document_events
    WHERE DATE(event_ts AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
tasks_agg AS (
    SELECT employee_id,
           COUNT(*) FILTER (WHERE action = 'opened')                        AS tasks_opened,
           COUNT(*) FILTER (WHERE action = 'closed')                        AS tasks_closed,
           COALESCE(SUM(story_points) FILTER (WHERE action = 'closed'), 0)  AS story_points_closed
    FROM task_events
    WHERE DATE(event_ts AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
meetings AS (
    SELECT employee_id,
           COUNT(*)                                         AS meeting_count,
           COALESCE(SUM(duration_minutes), 0)              AS meeting_minutes,
           COUNT(*) FILTER (WHERE is_organizer = true)     AS meetings_organized
    FROM meeting_events
    WHERE DATE(start_ts AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
chats AS (
    SELECT employee_id,
           COALESCE(SUM(message_count), 0)                 AS chat_message_count,
           COUNT(*) FILTER (WHERE after_hours = true)      AS chat_after_hours_count
    FROM chat_metadata_events
    WHERE DATE(event_ts AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
training AS (
    SELECT employee_id,
           COUNT(*)                              AS training_count,
           COALESCE(SUM(duration_hours), 0)     AS training_hours
    FROM training_completion_events
    WHERE DATE(completed_at AT TIME ZONE 'UTC') = :snap
    GROUP BY employee_id
),
all_active AS (
    SELECT DISTINCT employee_id FROM (
        SELECT employee_id FROM git_commit_events       WHERE DATE(commit_ts   AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM pull_request_events   WHERE DATE(opened_at   AT TIME ZONE 'UTC') = :snap
        UNION SELECT reviewer_employee_id FROM code_review_events WHERE DATE(review_ts  AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM experiment_run_events WHERE DATE(started_at  AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM research_artifact_events WHERE DATE(created_at  AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM document_events       WHERE DATE(event_ts    AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM task_events           WHERE DATE(event_ts    AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM meeting_events        WHERE DATE(start_ts    AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM chat_metadata_events  WHERE DATE(event_ts    AT TIME ZONE 'UTC') = :snap
        UNION SELECT employee_id FROM training_completion_events WHERE DATE(completed_at AT TIME ZONE 'UTC') = :snap
    ) s
)
SELECT
    de.employee_key,
    de.employee_id,
    de.role_family,
    COALESCE(c.commit_count,               0) AS commit_count,
    COALESCE(c.lines_added,                0) AS lines_added,
    COALESCE(c.lines_deleted,              0) AS lines_deleted,
    COALESCE(c.files_changed,              0) AS files_changed,
    COALESCE(p.pr_opened_count,            0) AS pr_opened_count,
    COALESCE(p.pr_merged_count,            0) AS pr_merged_count,
    COALESCE(r.code_review_count,          0) AS code_review_count,
    COALESCE(r.code_review_comment_count,  0) AS code_review_comment_count,
    COALESCE(e.experiment_count,           0) AS experiment_count,
    COALESCE(e.compute_hours,              0) AS compute_hours,
    COALESCE(ra.research_artifact_count,   0) AS research_artifact_count,
    COALESCE(d.doc_event_count,            0) AS doc_event_count,
    COALESCE(d.doc_word_count,             0) AS doc_word_count,
    COALESCE(ta.tasks_opened,              0) AS tasks_opened,
    COALESCE(ta.tasks_closed,              0) AS tasks_closed,
    COALESCE(ta.story_points_closed,       0) AS story_points_closed,
    COALESCE(m.meeting_count,              0) AS meeting_count,
    COALESCE(m.meeting_minutes,            0) AS meeting_minutes,
    COALESCE(m.meetings_organized,         0) AS meetings_organized,
    COALESCE(ch.chat_message_count,        0) AS chat_message_count,
    COALESCE(ch.chat_after_hours_count,    0) AS chat_after_hours_count,
    COALESCE(t.training_count,             0) AS training_count,
    COALESCE(t.training_hours,             0) AS training_hours,
    (aa.employee_id IS NOT NULL)               AS is_active
FROM dim_employee de
LEFT JOIN all_active aa ON aa.employee_id = de.employee_id
LEFT JOIN commits    c  ON c.employee_id  = de.employee_id
LEFT JOIN prs        p  ON p.employee_id  = de.employee_id
LEFT JOIN reviews    r  ON r.employee_id  = de.employee_id
LEFT JOIN experiments e ON e.employee_id  = de.employee_id
LEFT JOIN research  ra  ON ra.employee_id = de.employee_id
LEFT JOIN docs       d  ON d.employee_id  = de.employee_id
LEFT JOIN tasks_agg ta  ON ta.employee_id = de.employee_id
LEFT JOIN meetings   m  ON m.employee_id  = de.employee_id
LEFT JOIN chats     ch  ON ch.employee_id = de.employee_id
LEFT JOIN training   t  ON t.employee_id  = de.employee_id
WHERE de.is_current = true
"""


def build_fact_daily_activity(snapshot_date: date, session: Session) -> int:
    """Aggregate all raw events for snapshot_date into fact_employee_daily_activity.

    Idempotent: deletes any existing rows for date_key before inserting.
    """
    dk = _date_key(snapshot_date)
    session.execute(
        text("DELETE FROM fact_employee_daily_activity WHERE date_key = :dk"),
        {"dk": dk},
    )

    agg_rows = session.execute(
        text(_DAILY_ACTIVITY_CTE),
        {"snap": snapshot_date},
    ).mappings().all()

    if not agg_rows:
        session.flush()
        return 0

    insert_rows = []
    for row in agg_rows:
        cu = _compute_contribution_units(dict(row), row["role_family"])
        insert_rows.append(
            {
                "date_key": dk,
                "employee_key": row["employee_key"],
                "commit_count": row["commit_count"],
                "lines_added": row["lines_added"],
                "lines_deleted": row["lines_deleted"],
                "files_changed": row["files_changed"],
                "pr_opened_count": row["pr_opened_count"],
                "pr_merged_count": row["pr_merged_count"],
                "code_review_count": row["code_review_count"],
                "code_review_comment_count": row["code_review_comment_count"],
                "experiment_count": row["experiment_count"],
                "compute_hours": row["compute_hours"],
                "research_artifact_count": row["research_artifact_count"],
                "doc_event_count": row["doc_event_count"],
                "doc_word_count": row["doc_word_count"],
                "tasks_opened": row["tasks_opened"],
                "tasks_closed": row["tasks_closed"],
                "story_points_closed": row["story_points_closed"],
                "meeting_count": row["meeting_count"],
                "meeting_minutes": row["meeting_minutes"],
                "meetings_organized": row["meetings_organized"],
                "chat_message_count": row["chat_message_count"],
                "chat_after_hours_count": row["chat_after_hours_count"],
                "training_count": row["training_count"],
                "training_hours": row["training_hours"],
                "is_active": row["is_active"],
                "contribution_units": round(cu, 4),
            }
        )

    session.execute(
        text("""
            INSERT INTO fact_employee_daily_activity (
                date_key, employee_key,
                commit_count, lines_added, lines_deleted, files_changed,
                pr_opened_count, pr_merged_count,
                code_review_count, code_review_comment_count,
                experiment_count, compute_hours,
                research_artifact_count,
                doc_event_count, doc_word_count,
                tasks_opened, tasks_closed, story_points_closed,
                meeting_count, meeting_minutes, meetings_organized,
                chat_message_count, chat_after_hours_count,
                training_count, training_hours,
                is_active, contribution_units
            ) VALUES (
                :date_key, :employee_key,
                :commit_count, :lines_added, :lines_deleted, :files_changed,
                :pr_opened_count, :pr_merged_count,
                :code_review_count, :code_review_comment_count,
                :experiment_count, :compute_hours,
                :research_artifact_count,
                :doc_event_count, :doc_word_count,
                :tasks_opened, :tasks_closed, :story_points_closed,
                :meeting_count, :meeting_minutes, :meetings_organized,
                :chat_message_count, :chat_after_hours_count,
                :training_count, :training_hours,
                :is_active, :contribution_units
            )
        """),
        insert_rows,
    )
    session.flush()
    return len(insert_rows)


# ---------------------------------------------------------------------------
# fact_employee_project_contribution
# ---------------------------------------------------------------------------

def build_fact_project_contribution(snapshot_date: date, session: Session) -> int:
    """Split employee daily contribution across their assigned projects.

    Uses allocation_pct from employee_project_assignments to proportion the
    contribution_units computed in fact_employee_daily_activity.
    Employees with no active assignment are excluded.
    """
    dk = _date_key(snapshot_date)
    session.execute(
        text("DELETE FROM fact_employee_project_contribution WHERE date_key = :dk"),
        {"dk": dk},
    )

    rows = session.execute(
        text("""
            WITH alloc_totals AS (
                SELECT employee_id, SUM(allocation_pct) AS total_alloc
                FROM employee_project_assignments
                WHERE start_date <= :snap
                  AND (end_date IS NULL OR end_date >= :snap)
                GROUP BY employee_id
            )
            SELECT
                fda.employee_key,
                de.employee_id,
                de.role_family,
                epa.project_id,
                epa.allocation_pct / alloc_totals.total_alloc  AS alloc_fraction,
                fda.commit_count,
                fda.lines_added,
                fda.lines_deleted,
                fda.files_changed,
                fda.experiment_count,
                fda.compute_hours,
                fda.research_artifact_count,
                fda.doc_event_count,
                fda.doc_word_count,
                fda.tasks_closed,
                fda.story_points_closed,
                fda.code_review_count,
                fda.meeting_minutes
            FROM fact_employee_daily_activity fda
            JOIN dim_employee de ON de.employee_key = fda.employee_key
            JOIN employee_project_assignments epa
                ON epa.employee_id = de.employee_id
               AND epa.start_date <= :snap
               AND (epa.end_date IS NULL OR epa.end_date >= :snap)
            JOIN alloc_totals ON alloc_totals.employee_id = de.employee_id
            WHERE fda.date_key = :dk
        """),
        {"snap": snapshot_date, "dk": dk},
    ).mappings().all()

    if not rows:
        session.flush()
        return 0

    insert_rows = []
    for row in rows:
        frac = float(row["alloc_fraction"] or 0)
        role = row["role_family"]
        weights = CONTRIBUTION_WEIGHTS.get(role, CONTRIBUTION_WEIGHTS["default"])

        scaled = {
            "lines_added": float(row["lines_added"]) * frac,
            "lines_deleted": float(row["lines_deleted"]) * frac,
            "files_changed": float(row["files_changed"]) * frac,
            "experiment_count": float(row["experiment_count"]) * frac,
            "compute_hours": float(row["compute_hours"] or 0) * frac,
            "research_artifact_count": float(row["research_artifact_count"]) * frac,
            "doc_event_count": float(row["doc_event_count"]) * frac,
            "doc_word_count": float(row["doc_word_count"]) * frac,
            "story_points_closed": float(row["story_points_closed"]) * frac,
            "code_review_count": float(row["code_review_count"]) * frac,
            "meeting_minutes": float(row["meeting_minutes"]) * frac,
        }

        code_u = (scaled["lines_added"] + scaled["lines_deleted"]) / 100 + scaled["files_changed"] / 10
        research_u = scaled["experiment_count"] * scaled["compute_hours"] / 8 + scaled["research_artifact_count"] * 2
        doc_u = scaled["doc_event_count"] + scaled["doc_word_count"] / 500
        collab_u = scaled["code_review_count"] + scaled["meeting_minutes"] / 60 * 0.5
        impact_u = scaled["story_points_closed"] / 5

        cu = (
            weights["code"] * code_u
            + weights["research"] * research_u
            + weights["documentation"] * doc_u
            + weights["collaboration"] * collab_u
            + weights["impact"] * impact_u
        )

        insert_rows.append(
            {
                "date_key": dk,
                "employee_key": row["employee_key"],
                "project_id": row["project_id"],
                "contribution_units": round(cu, 4),
                "code_units": round(code_u, 4),
                "research_units": round(research_u, 4),
                "documentation_units": round(doc_u, 4),
                "collaboration_units": round(collab_u, 4),
                "impact_units": round(impact_u, 4),
            }
        )

    session.execute(
        text("""
            INSERT INTO fact_employee_project_contribution (
                date_key, employee_key, project_id,
                contribution_units, code_units, research_units,
                documentation_units, collaboration_units, impact_units
            ) VALUES (
                :date_key, :employee_key, :project_id,
                :contribution_units, :code_units, :research_units,
                :documentation_units, :collaboration_units, :impact_units
            )
        """),
        insert_rows,
    )
    session.flush()
    return len(insert_rows)


# ---------------------------------------------------------------------------
# fact_team_weekly_health
# ---------------------------------------------------------------------------

_TEAM_WEEKLY_SQL = """
WITH week_activity AS (
    SELECT
        de.team_id,
        de.employee_key,
        SUM(
            fda.commit_count + fda.experiment_count
            + fda.research_artifact_count + fda.doc_event_count
        )                                                        AS activity_score,
        SUM(fda.meeting_minutes)                                 AS total_meeting_minutes,
        SUM(fda.chat_after_hours_count)                          AS total_after_hours,
        COUNT(*) FILTER (WHERE fda.is_active = false)            AS inactive_days,
        SUM(fda.contribution_units)                              AS total_contrib,
        SUM(
            fda.commit_count + fda.pr_opened_count + fda.code_review_count
            + fda.experiment_count + fda.research_artifact_count + fda.doc_event_count
            + fda.tasks_opened + fda.tasks_closed + fda.meeting_count
            + fda.chat_message_count
        )                                                        AS total_event_count
    FROM fact_employee_daily_activity fda
    JOIN dim_employee de ON de.employee_key = fda.employee_key
    WHERE fda.date_key IN (
        SELECT date_key FROM dim_date WHERE week_key = :wk
    )
    GROUP BY de.team_id, de.employee_key
),
team_percentiles AS (
    SELECT
        team_id,
        COALESCE(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY activity_score), 0)    AS p25_activity,
        COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_event_count), 0) AS p95_events
    FROM week_activity
    GROUP BY team_id
)
SELECT
    CAST(:wk AS INTEGER)                                        AS week_key,
    wa.team_id,
    dt.org_id,
    COUNT(DISTINCT wa.employee_key)                             AS active_employee_count,
    ROUND(
        COUNT(*) FILTER (WHERE wa.activity_score < tp.p25_activity)::numeric
        / NULLIF(COUNT(*), 0), 4
    )                                                           AS underutilization_rate,
    ROUND(
        COUNT(*) FILTER (
            WHERE wa.total_meeting_minutes > 300
               OR wa.total_event_count > tp.p95_events
        )::numeric / NULLIF(COUNT(*), 0), 4
    )                                                           AS overload_rate,
    ROUND(
        COUNT(*) FILTER (WHERE wa.inactive_days >= 3)::numeric
        / NULLIF(COUNT(*), 0), 4
    )                                                           AS silent_disengagement_rate,
    ROUND(
        COUNT(*) FILTER (
            WHERE wa.total_after_hours >= 3
              AND wa.total_meeting_minutes > 240
        )::numeric / NULLIF(COUNT(*), 0), 4
    )                                                           AS burnout_risk_rate,
    0.0::numeric(5,4)                                           AS cross_team_collaboration_rate,
    ROUND(AVG(wa.total_contrib)::numeric, 4)                    AS avg_contribution_units,
    ROUND(SUM(wa.total_contrib)::numeric, 4)                    AS total_contribution_units
FROM week_activity wa
JOIN team_percentiles tp ON tp.team_id = wa.team_id
JOIN dim_team dt ON dt.team_key = wa.team_id AND dt.is_current = true
GROUP BY wa.team_id, dt.org_id
"""


def build_fact_team_weekly_health(snapshot_date: date, session: Session) -> int:
    """Roll up daily activity facts into weekly team health for snapshot_date's ISO week.

    Idempotent: deletes any existing rows for week_key before inserting.
    Partial-week runs (e.g. running on Wednesday) produce partial-week metrics;
    this is expected and documented.
    """
    iso_year, iso_week, _ = snapshot_date.isocalendar()
    week_key = iso_year * 100 + iso_week

    session.execute(
        text("DELETE FROM fact_team_weekly_health WHERE week_key = :wk"),
        {"wk": week_key},
    )

    rows = session.execute(text(_TEAM_WEEKLY_SQL), {"wk": week_key}).mappings().all()

    if not rows:
        session.flush()
        return 0

    session.execute(
        text("""
            INSERT INTO fact_team_weekly_health (
                week_key, team_id, org_id,
                active_employee_count,
                underutilization_rate, overload_rate,
                silent_disengagement_rate, burnout_risk_rate,
                cross_team_collaboration_rate,
                avg_contribution_units, total_contribution_units
            ) VALUES (
                :week_key, :team_id, :org_id,
                :active_employee_count,
                :underutilization_rate, :overload_rate,
                :silent_disengagement_rate, :burnout_risk_rate,
                :cross_team_collaboration_rate,
                :avg_contribution_units, :total_contribution_units
            )
        """),
        [dict(r) for r in rows],
    )
    session.flush()
    return len(rows)


# ---------------------------------------------------------------------------
# fact_employee_skill_signal
# ---------------------------------------------------------------------------

def build_fact_skill_signal(snapshot_date: date, session: Session) -> int:
    """Aggregate skill-level signals for snapshot_date.

    In Sprint 3 only training_completion_events has a direct skill_id link.
    code_review and experiment skill attribution is deferred to Sprint 5.
    """
    dk = _date_key(snapshot_date)
    session.execute(
        text("DELETE FROM fact_employee_skill_signal WHERE date_key = :dk"),
        {"dk": dk},
    )

    rows = session.execute(
        text("""
            SELECT
                CAST(:dk AS INTEGER)      AS date_key,
                de.employee_key,
                t.skill_id,
                COUNT(*)                  AS training_count,
                COALESCE(SUM(t.duration_hours), 0) AS training_hours,
                0                         AS code_review_count,
                0                         AS experiment_count
            FROM training_completion_events t
            JOIN dim_employee de
                ON de.employee_id = t.employee_id
               AND de.is_current = true
            WHERE DATE(t.completed_at AT TIME ZONE 'UTC') = :snap
              AND t.skill_id IS NOT NULL
            GROUP BY de.employee_key, t.skill_id
        """),
        {"dk": dk, "snap": snapshot_date},
    ).mappings().all()

    if not rows:
        session.flush()
        return 0

    session.execute(
        text("""
            INSERT INTO fact_employee_skill_signal (
                date_key, employee_key, skill_id,
                training_count, training_hours,
                code_review_count, experiment_count
            ) VALUES (
                :date_key, :employee_key, :skill_id,
                :training_count, :training_hours,
                :code_review_count, :experiment_count
            )
        """),
        [dict(r) for r in rows],
    )
    session.flush()
    return len(rows)
