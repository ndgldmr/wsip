"""raw event tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # git_commit_events
    # -------------------------------------------------------------------------
    op.create_table(
        "git_commit_events",
        sa.Column("commit_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("repo_id", UUID(as_uuid=True), sa.ForeignKey("repos.repo_id"), nullable=False),
        sa.Column("commit_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("commit_hash", sa.Text, nullable=False),
        sa.Column("lines_added", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_deleted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("files_changed", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_merge_commit", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("branch_name", sa.Text, nullable=True),
        sa.Column("commit_message", sa.Text, nullable=True),
    )
    op.create_index("idx_git_commits_employee_ts", "git_commit_events", ["employee_id", "commit_ts"])

    # -------------------------------------------------------------------------
    # pull_request_events
    # -------------------------------------------------------------------------
    op.create_table(
        "pull_request_events",
        sa.Column("pr_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("repo_id", UUID(as_uuid=True), sa.ForeignKey("repos.repo_id"), nullable=False),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("merged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column("additions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.Text, nullable=True),
    )
    op.create_index("idx_pr_events_employee_opened", "pull_request_events", ["employee_id", "opened_at"])
    op.create_index("idx_pr_events_repo_opened", "pull_request_events", ["repo_id", "opened_at"])

    # -------------------------------------------------------------------------
    # code_review_events
    # -------------------------------------------------------------------------
    op.create_table(
        "code_review_events",
        sa.Column("review_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reviewer_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("pr_author_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("repo_id", UUID(as_uuid=True), sa.ForeignKey("repos.repo_id"), nullable=True),
        sa.Column("review_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("review_state", sa.Text, nullable=False),
        sa.Column("comment_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("time_to_review_hours", sa.Numeric(8, 2), nullable=True),
    )
    op.create_index("idx_code_review_reviewer_ts", "code_review_events", ["reviewer_employee_id", "review_ts"])

    # -------------------------------------------------------------------------
    # experiment_run_events
    # -------------------------------------------------------------------------
    op.create_table(
        "experiment_run_events",
        sa.Column("experiment_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("experiment_type", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("compute_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("outcome_metric_name", sa.Text, nullable=True),
        sa.Column("outcome_metric_value", sa.Numeric(12, 6), nullable=True),
    )
    op.create_index("idx_experiment_employee_started", "experiment_run_events", ["employee_id", "started_at"])
    op.create_index("idx_experiment_project_started", "experiment_run_events", ["project_id", "started_at"])

    # -------------------------------------------------------------------------
    # research_artifact_events
    # -------------------------------------------------------------------------
    op.create_table(
        "research_artifact_events",
        sa.Column("artifact_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("artifact_type", sa.Text, nullable=False),
        sa.Column("collaboration_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("citation_count", sa.Integer, nullable=True),
    )
    op.create_index("idx_research_artifact_employee_created", "research_artifact_events", ["employee_id", "created_at"])

    # -------------------------------------------------------------------------
    # document_events
    # -------------------------------------------------------------------------
    op.create_table(
        "document_events",
        sa.Column("doc_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("event_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("doc_type", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("collaborator_count", sa.Integer, nullable=True),
    )
    op.create_index("idx_document_events_employee_ts", "document_events", ["employee_id", "event_ts"])

    # -------------------------------------------------------------------------
    # task_events
    # -------------------------------------------------------------------------
    op.create_table(
        "task_events",
        sa.Column("task_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=True),
        sa.Column("event_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("task_type", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("priority", sa.Text, nullable=False),
        sa.Column("story_points", sa.Integer, nullable=True),
        sa.Column("cycle_time_hours", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index("idx_task_events_employee_ts", "task_events", ["employee_id", "event_ts"])

    # -------------------------------------------------------------------------
    # meeting_events
    # -------------------------------------------------------------------------
    op.create_table(
        "meeting_events",
        sa.Column("meeting_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("start_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("meeting_type", sa.Text, nullable=False),
        sa.Column("attendee_count", sa.Integer, nullable=False, server_default="2"),
        sa.Column("is_organizer", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_external", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("idx_meeting_events_employee_ts", "meeting_events", ["employee_id", "start_ts"])

    # -------------------------------------------------------------------------
    # chat_metadata_events
    # -------------------------------------------------------------------------
    op.create_table(
        "chat_metadata_events",
        sa.Column("chat_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("event_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("channel_type", sa.Text, nullable=False),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("reaction_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unique_recipients", sa.Integer, nullable=True),
        sa.Column("after_hours", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("idx_chat_events_employee_ts", "chat_metadata_events", ["employee_id", "event_ts"])

    # -------------------------------------------------------------------------
    # training_completion_events
    # -------------------------------------------------------------------------
    op.create_table(
        "training_completion_events",
        sa.Column("training_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("training_type", sa.Text, nullable=False),
        sa.Column("topic", sa.Text, nullable=True),
        sa.Column("duration_hours", sa.Numeric(6, 2), nullable=True),
    )
    op.create_index("idx_training_events_employee_completed", "training_completion_events", ["employee_id", "completed_at"])

    # -------------------------------------------------------------------------
    # resume_skill_inference
    # -------------------------------------------------------------------------
    op.create_table(
        "resume_skill_inference",
        sa.Column("inference_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("inferred_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("inference_source", sa.Text, nullable=False),
        sa.Column("inferred_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("idx_resume_skill_inference_employee", "resume_skill_inference", ["employee_id"])


def downgrade() -> None:
    op.drop_table("resume_skill_inference")
    op.drop_table("training_completion_events")
    op.drop_table("chat_metadata_events")
    op.drop_table("meeting_events")
    op.drop_table("task_events")
    op.drop_table("document_events")
    op.drop_table("research_artifact_events")
    op.drop_table("experiment_run_events")
    op.drop_table("code_review_events")
    op.drop_table("pull_request_events")
    op.drop_table("git_commit_events")
