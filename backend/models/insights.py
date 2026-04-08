"""
Insight and Recommendation ORM models — Sprint 5.

Insights are rule-based findings derived from employee feature snapshots.
Recommendations are linked, actionable next steps targeting a specific owner role.

Both tables are idempotently populated by etl/insight_engine.py and exposed via
/insights and /recommendations endpoints.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class Insight(TimestampMixin, Base):
    __tablename__ = "insights"

    # PK defined explicitly (not via UUIDPKMixin) so the column is named `id`
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # scope identifies what entity the insight is about
    scope: Mapped[str] = mapped_column(Text, nullable=False)          # "employee" | "team" | "org"
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    insight_type: Mapped[str] = mapped_column(Text, nullable=False)   # underutilization | overload | …
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    severity: Mapped[str] = mapped_column(Text, nullable=False)       # "high" | "medium" | "low"
    title: Mapped[str] = mapped_column(Text, nullable=False)
    insight_description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("scope_id", "insight_type", "snapshot_date", name="uq_insight_scope_type_date"),
    )


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    insight_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insights.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(Text, nullable=False)    # e.g. "manager_checkin"
    priority: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    target_scope: Mapped[str] = mapped_column(Text, nullable=False)   # "manager" | "hrbp" | "admin"

    accepted_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(Text, nullable=True)
