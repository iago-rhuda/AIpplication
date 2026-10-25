"""SQLAlchemy declarative ORM models matching storage/schema.sql."""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.database.session import Base


class Job(Base):
    """Job listing model."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    job_url = Column(String(1024), nullable=False, unique=True)
    source = Column(String(50), nullable=False)  # 'linkedin', 'wttj', 'direct'
    workplace_type = Column(String(50), nullable=False)  # 'hybrid', 'on-site', 'remote'
    start_date = Column(String(50), nullable=True)
    duration_weeks = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    raw_requirements = Column(Text, nullable=True)
    is_iad_compliant = Column(Boolean, nullable=False, default=False)
    compliance_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    doubts = relationship("Doubt", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    """Application tracking model representing cards on the Kanban board."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        String(50), nullable=False, default="wishlist"
    )  # 'wishlist', 'to_apply', 'applied', 'interview', 'offer', 'rejected'
    application_mode = Column(
        String(50), nullable=False, default="semi_auto"
    )  # 'auto', 'semi_auto'
    cv_pdf_path = Column(String(1024), nullable=True)
    cover_letter_pdf_path = Column(String(1024), nullable=True)
    requires_cover_letter = Column(Boolean, nullable=False, default=False)
    applied_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    job = relationship("Job", back_populates="applications")


class Doubt(Base):
    """Human-in-the-loop pending question and resolution model."""

    __tablename__ = "doubts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    doubt_type = Column(
        String(50), nullable=False
    )  # 'form_question', 'unclear_stack', 'unclear_duration', 'date_conflict'
    question_text = Column(Text, nullable=False)
    suggested_answer = Column(Text, nullable=True)
    user_decision = Column(Text, nullable=True)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # 'pending', 'resolved', 'ignored'
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="doubts")


class ColdOutreachTarget(Base):
    """Identified companies for speculative application outreach."""

    __tablename__ = "cold_outreach_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False, unique=True)
    website = Column(String(512), nullable=False)
    ai_domain = Column(String(255), nullable=False)
    tech_stack = Column(Text, nullable=True)
    key_contacts = Column(Text, nullable=True)  # JSON serialized contacts
    recommended_approach = Column(Text, nullable=True)
    status = Column(
        String(50), nullable=False, default="mapped"
    )  # 'mapped', 'contacted', 'replied', 'closed'
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AuditLog(Base):
    """Database audit table matching JSON audit log entries."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    action = Column(String(255), nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
