"""Async CRUD repository operations for database models with automated audit logging."""

import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Application, AuditLog, ColdOutreachTarget, Doubt, Job, StatusEvent
from src.engine.career_ops_sync import append_status_log
from src.utils.logger import log_audit_event, logger


# ==============================================================================
# Job Repository
# ==============================================================================
async def create_job(db: AsyncSession, job_data: dict) -> Job:
    """Insert a new scraped job into the database."""
    job = Job(**job_data)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    log_audit_event(
        event_type="JOB_CREATED",
        entity_type="JOB",
        entity_id=job.id,
        action="INSERT_JOB",
        details={
            "company_name": job.company_name,
            "title": job.title,
            "is_iad_compliant": job.is_iad_compliant,
            "compliance_score": job.compliance_score,
        },
    )
    return job


async def get_job_by_url(db: AsyncSession, job_url: str) -> Job | None:
    """Find a job by its unique URL."""
    stmt = select(Job).where(Job.job_url == job_url)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_jobs(
    db: AsyncSession, compliant_only: bool = False
) -> Sequence[Job]:
    """Retrieve all jobs with optional compliance filtering."""
    stmt = select(Job)
    if compliant_only:
        stmt = stmt.where(Job.is_iad_compliant.is_(True))
    stmt = stmt.order_by(Job.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ==============================================================================
# Application Repository (Kanban Pipeline)
# ==============================================================================
async def create_application(
    db: AsyncSession, application_data: dict, source: str = "system", initial_note: str | None = None
) -> Application:
    """Create a new Kanban application tracking item with initial status event ledger."""
    application = Application(**application_data)
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Initial status transition event
    status_event = StatusEvent(
        application_id=application.id,
        from_status=None,
        to_status=application.status,
        source=source,
        notes=initial_note or "Application registered in pipeline.",
    )
    db.add(status_event)
    await db.commit()

    # Append to canonical status-log.tsv
    append_status_log(
        tracker_num=application.id,
        from_status=None,
        to_status=application.status,
        source=source,
        note=initial_note or "Application registered in pipeline.",
        event_time=application.created_at,
    )

    log_audit_event(
        event_type="APPLICATION_CREATED",
        entity_type="APPLICATION",
        entity_id=application.id,
        action="INSERT_APPLICATION",
        details={
            "job_id": application.job_id,
            "status": application.status,
            "mode": application.application_mode,
        },
    )
    return application


async def update_application_status(
    db: AsyncSession,
    application_id: int,
    new_status: str,
    notes: str | None = None,
    source: str = "user",
) -> Application | None:
    """Transition an application across Kanban columns with full StatusEvent ledger and audit trail."""
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.job), selectinload(Application.status_events))
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if not application:
        return None

    old_status = application.status
    application.status = new_status
    if notes is not None:
        application.notes = notes

    now_utc = datetime.now(timezone.utc)
    if new_status == "applied":
        if not application.applied_at:
            application.applied_at = now_utc
        # Set follow-up cadence: 7 days window
        application.followup_due_at = now_utc + timedelta(days=7)
    elif new_status == "interview":
        # Interview cadence: 3-5 days
        application.followup_due_at = now_utc + timedelta(days=4)

    # Immutable transition event in DB
    event = StatusEvent(
        application_id=application.id,
        from_status=old_status,
        to_status=new_status,
        source=source,
        notes=notes,
        created_at=now_utc,
    )
    db.add(event)

    await db.commit()
    await db.refresh(application)

    # Append to canonical Career-Ops data/status-log.tsv
    append_status_log(
        tracker_num=application.id,
        from_status=old_status,
        to_status=new_status,
        source=source,
        note=notes,
        event_time=now_utc,
    )

    log_audit_event(
        event_type="APPLICATION_STATUS_UPDATED",
        entity_type="APPLICATION",
        entity_id=application.id,
        action="TRANSITION_STATUS",
        details={
            "old_status": old_status,
            "new_status": new_status,
            "job_id": application.job_id,
            "source": source,
            "notes": notes,
        },
    )
    return application


async def add_application_event(
    db: AsyncSession,
    application_id: int,
    note: str,
    source: str = "user",
) -> StatusEvent | None:
    """Record an interaction or note in the application status ledger without changing columns."""
    app = await get_application_by_id(db, application_id)
    if not app:
        return None

    now_utc = datetime.now(timezone.utc)
    event = StatusEvent(
        application_id=application_id,
        from_status=app.status,
        to_status=app.status,
        source=source,
        notes=note,
        created_at=now_utc,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    append_status_log(
        tracker_num=application_id,
        from_status=app.status,
        to_status=app.status,
        source=source,
        note=note,
        event_time=now_utc,
    )
    return event


async def get_application_by_id(
    db: AsyncSession, application_id: int
) -> Application | None:
    """Retrieve application by ID with eager loading for job and status history."""
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.job), selectinload(Application.status_events))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_applications_by_status(
    db: AsyncSession, status: str | None = None
) -> Sequence[Application]:
    """List applications optionally filtered by Kanban column status, with eager loaded relations."""
    stmt = select(Application).options(
        selectinload(Application.job), selectinload(Application.status_events)
    )
    if status:
        stmt = stmt.where(Application.status == status)
    stmt = stmt.order_by(Application.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ==============================================================================
# Doubts Repository (Human-in-the-Loop)
# ==============================================================================
async def create_doubt(db: AsyncSession, doubt_data: dict) -> Doubt:
    """Register an ambiguity or required decision for user intervention."""
    doubt = Doubt(**doubt_data)
    db.add(doubt)
    await db.commit()
    await db.refresh(doubt)

    log_audit_event(
        event_type="DOUBT_REGISTERED",
        entity_type="DOUBT",
        entity_id=doubt.id,
        action="RAISE_QUESTION",
        details={
            "job_id": doubt.job_id,
            "doubt_type": doubt.doubt_type,
            "question_text": doubt.question_text,
        },
    )
    return doubt


async def resolve_doubt(
    db: AsyncSession, doubt_id: int, user_decision: str, status: str = "resolved"
) -> Doubt | None:
    """Record user resolution for a pending doubt."""
    stmt = select(Doubt).where(Doubt.id == doubt_id)
    result = await db.execute(stmt)
    doubt = result.scalar_one_or_none()
    if not doubt:
        return None

    doubt.user_decision = user_decision
    doubt.status = status
    doubt.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(doubt)

    log_audit_event(
        event_type="DOUBT_RESOLVED",
        entity_type="DOUBT",
        entity_id=doubt.id,
        action="RECORD_DECISION",
        details={
            "job_id": doubt.job_id,
            "user_decision": user_decision,
            "status": status,
        },
    )
    return doubt


async def get_pending_doubts(db: AsyncSession) -> Sequence[Doubt]:
    """Retrieve all pending doubts requiring user attention."""
    stmt = (
        select(Doubt)
        .where(Doubt.status == "pending")
        .order_by(Doubt.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ==============================================================================
# Cold Outreach Targets Repository
# ==============================================================================
async def create_or_update_cold_target(
    db: AsyncSession, target_data: dict
) -> ColdOutreachTarget:
    """Insert or update a speculative application target company."""
    stmt = select(ColdOutreachTarget).where(
        ColdOutreachTarget.company_name == target_data["company_name"]
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        for key, value in target_data.items():
            setattr(existing, key, value)
        await db.commit()
        await db.refresh(existing)
        target = existing
    else:
        target = ColdOutreachTarget(**target_data)
        db.add(target)
        await db.commit()
        await db.refresh(target)

    log_audit_event(
        event_type="COLD_TARGET_SAVED",
        entity_type="COLD_TARGET",
        entity_id=target.id,
        action="UPSERT_TARGET",
        details={
            "company_name": target.company_name,
            "ai_domain": target.ai_domain,
            "status": target.status,
        },
    )
    return target


async def get_all_cold_targets(db: AsyncSession) -> Sequence[ColdOutreachTarget]:
    """List all mapped speculative outreach companies."""
    stmt = select(ColdOutreachTarget).order_by(ColdOutreachTarget.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ==============================================================================
# Persistent Audit Logs
# ==============================================================================
async def record_audit_log_entry(
    db: AsyncSession,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    action: str,
    payload: dict,
) -> AuditLog:
    """Store an immutable audit entry in the database."""
    entry = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        action=action,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
