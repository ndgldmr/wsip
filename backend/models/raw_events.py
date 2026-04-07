"""
Raw event tables — one row per atomic work signal from a source system.

Tables:
  git_commit_events, pull_request_events, code_review_events,
  experiment_run_events, research_artifact_events, document_events,
  task_events, meeting_events, chat_metadata_events,
  training_completion_events, resume_skill_inference
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class GitCommitEvent(Base):
    __tablename__ = "git_commit_events"

    commit_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repos.repo_id"), nullable=False)
    commit_ts: Mapped[datetime] = mapped_column(nullable=False)
    commit_hash: Mapped[str] = mapped_column(Text, nullable=False)
    lines_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_merge_commit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    branch_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class PullRequestEvent(Base):
    __tablename__ = "pull_request_events"

    pr_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repos.repo_id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)  # open / closed / merged
    additions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)


class CodeReviewEvent(Base):
    __tablename__ = "code_review_events"

    review_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reviewer_employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    pr_author_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=True)
    repo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("repos.repo_id"), nullable=True)
    review_ts: Mapped[datetime] = mapped_column(nullable=False)
    review_state: Mapped[str] = mapped_column(Text, nullable=False)  # approved / changes_requested / commented
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_to_review_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)


class ExperimentRunEvent(Base):
    __tablename__ = "experiment_run_events"

    experiment_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    experiment_type: Mapped[str] = mapped_column(Text, nullable=False)  # ab_test / model_train / simulation / analysis
    status: Mapped[str] = mapped_column(Text, nullable=False)  # running / completed / failed / cancelled
    compute_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    outcome_metric_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_metric_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)


class ResearchArtifactEvent(Base):
    __tablename__ = "research_artifact_events"

    artifact_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)  # paper / report / dataset / model / notebook
    collaboration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DocumentEvent(Base):
    __tablename__ = "document_events"

    doc_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)  # spec / wiki / proposal / notes / report
    action: Mapped[str] = mapped_column(Text, nullable=False)  # create / edit / share / comment
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collaborator_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TaskEvent(Base):
    __tablename__ = "task_events"

    task_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=True)
    event_ts: Mapped[datetime] = mapped_column(nullable=False)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)  # feature / bug / chore / review
    action: Mapped[str] = mapped_column(Text, nullable=False)  # opened / closed / assigned / commented
    priority: Mapped[str] = mapped_column(Text, nullable=False)  # high / medium / low
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cycle_time_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)


class MeetingEvent(Base):
    __tablename__ = "meeting_events"

    meeting_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    start_ts: Mapped[datetime] = mapped_column(nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    meeting_type: Mapped[str] = mapped_column(Text, nullable=False)  # standup / planning / review / 1on1 / all-hands / interview
    attendee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_organizer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ChatMetadataEvent(Base):
    __tablename__ = "chat_metadata_events"

    chat_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(nullable=False)
    channel_type: Mapped[str] = mapped_column(Text, nullable=False)  # dm / public / private / announcement
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_recipients: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_hours: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TrainingCompletionEvent(Base):
    __tablename__ = "training_completion_events"

    training_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(nullable=False)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)  # course / certification / workshop / conference
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)


class ResumeSkillInference(Base):
    __tablename__ = "resume_skill_inference"

    inference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=False)
    inferred_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)  # 0.0000 – 1.0000
    inference_source: Mapped[str] = mapped_column(Text, nullable=False)  # resume / github / linkedin
    inferred_at: Mapped[datetime] = mapped_column(nullable=False)
