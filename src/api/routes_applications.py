"""Application tracking, Career-Ops status ledger, and evaluation endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.crud import (
    add_application_event,
    get_application_by_id,
    get_applications_by_status,
    update_application_status,
)
from src.database.models import Application
from src.database.session import get_db
from src.engine.career_ops_evaluator import evaluate_with_career_ops
from src.engine.career_ops_sync import sync_applications_markdown, sync_followups_markdown
from src.engine.cover_letter_generator import generate_cover_letter
from src.engine.latex_compiler import compile_custom_cv
from src.utils.logger import log_audit_event, logger

router = APIRouter(prefix="/api/applications", tags=["Applications"])


class StatusUpdateRequest(BaseModel):
    status: str  # 'wishlist', 'to_apply', 'applied', 'interview', 'offer', 'rejected'
    notes: str | None = None
    source: str = "user"  # 'user', 'scraper', 'evaluator', 'agent'


class AddEventRequest(BaseModel):
    notes: str
    source: str = "user"


def resolve_web_url(path_str: str | None) -> str | None:
    """Compute relative /output URL for a filesystem path."""
    if not path_str:
        return None
    try:
        p = Path(path_str).resolve()
        rel = p.relative_to(settings.OUTPUT_DIR.resolve())
        return f"/output/{rel.as_posix()}"
    except Exception:
        return f"/output/{Path(path_str).name}"


def resolve_report_web_url(path_str: str | None) -> str | None:
    """Compute relative /reports URL for a report filesystem path."""
    if not path_str:
        return None
    try:
        p = Path(path_str)
        return f"/reports/{p.name}"
    except Exception:
        return None


def serialize_application(app: Application) -> dict[str, Any]:
    """Format Application model with relative web URLs and rich Career-Ops metadata."""
    cv_web_url = resolve_web_url(app.cv_pdf_path)
    lm_web_url = resolve_web_url(app.cover_letter_pdf_path)
    report_web_url = resolve_report_web_url(app.evaluation_report_path or app.report_path)

    # Safe JSON parsing
    star_stories = []
    if app.star_stories:
        try:
            star_stories = json.loads(app.star_stories)
        except Exception:
            star_stories = []

    form_answers = {}
    if app.form_answers:
        try:
            form_answers = json.loads(app.form_answers)
        except Exception:
            form_answers = {}

    # Follow-up calculations
    now_utc = datetime.now(timezone.utc)
    days_elapsed = 0
    ref_dt = app.applied_at or app.created_at
    if ref_dt:
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        days_elapsed = max(0, (now_utc - ref_dt).days)

    if app.status in ("applied", "interview"):
        if days_elapsed <= 4:
            cadence_tag = "recent"
            cadence_label = f"Recent ({days_elapsed}d)"
        elif 5 <= days_elapsed <= 7:
            cadence_tag = "due"
            cadence_label = f"Follow-up due ({days_elapsed}d)"
        else:
            cadence_tag = "overdue"
            cadence_label = f"Overdue ({days_elapsed}d)"
    else:
        cadence_tag = "normal"
        cadence_label = f"{days_elapsed}d in stage"

    # Status events timeline
    events_serialized = []
    if app.status_events:
        for ev in app.status_events:
            events_serialized.append({
                "id": ev.id,
                "from_status": ev.from_status,
                "to_status": ev.to_status,
                "source": ev.source,
                "notes": ev.notes,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })

    return {
        "id": app.id,
        "job_id": app.job_id,
        "status": app.status,
        "application_mode": app.application_mode,
        "evaluation_score": app.evaluation_score if app.evaluation_score is not None else 4.2,
        "match_grade": app.match_grade or "A",
        "salary_range": app.salary_range or "1 400€ - 1 800€ / mois",
        "followup_due_at": app.followup_due_at.isoformat() if app.followup_due_at else None,
        "days_elapsed": days_elapsed,
        "cadence_tag": cadence_tag,
        "cadence_label": cadence_label,
        "key_contact_name": app.key_contact_name,
        "key_contact_role": app.key_contact_role,
        "key_contact_linkedin": app.key_contact_linkedin,
        "key_contact_email": app.key_contact_email,
        "outreach_message": app.outreach_message,
        "star_stories": star_stories,
        "form_answers": form_answers,
        "cv_pdf_path": app.cv_pdf_path,
        "cv_web_url": cv_web_url,
        "cover_letter_pdf_path": app.cover_letter_pdf_path,
        "cover_letter_web_url": lm_web_url,
        "report_path": app.evaluation_report_path or app.report_path,
        "report_web_url": report_web_url,
        "requires_cover_letter": app.requires_cover_letter,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "notes": app.notes,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "status_events": events_serialized,
        "job": {
            "id": app.job.id,
            "company_name": app.job.company_name,
            "title": app.job.title,
            "location": app.job.location,
            "job_url": app.job.job_url,
            "source": app.job.source,
            "workplace_type": app.job.workplace_type,
            "start_date": app.job.start_date,
            "duration_weeks": app.job.duration_weeks,
            "description": app.job.description,
            "raw_requirements": app.job.raw_requirements,
            "is_iad_compliant": app.job.is_iad_compliant,
            "compliance_score": app.job.compliance_score,
        } if app.job else None,
    }


@router.get("")
async def list_applications(status: str | None = None, db: AsyncSession = Depends(get_db)):
    """Retrieve all applications grouped into Kanban columns and synchronize markdown trackers."""
    apps = await get_applications_by_status(db, status=status)
    serialized = [serialize_application(a) for a in apps]

    # Auto-sync with Career-Ops data/applications.md and data/follow-ups.md
    try:
        sync_applications_markdown(serialized)
        sync_followups_markdown(serialized)
    except Exception as exc:
        logger.warning(f"Error during markdown tracker sync: {exc}")

    return {"applications": serialized, "total": len(serialized)}


@router.get("/{app_id}")
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve complete application details including status timeline and A-H evaluation."""
    app = await get_application_by_id(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"status": "success", "application": serialize_application(app)}


@router.patch("/{app_id}/status")
async def change_application_status(
    app_id: int,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition application across Kanban columns with full audit logging and status ledger sync."""
    updated = await update_application_status(
        db, app_id, payload.status, notes=payload.notes, source=payload.source
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")

    serialized = serialize_application(updated)

    # Sync markdown trackers
    all_apps = await get_applications_by_status(db)
    sync_applications_markdown([serialize_application(a) for a in all_apps])
    sync_followups_markdown([serialize_application(a) for a in all_apps])

    return {"status": "success", "application": serialized}


@router.post("/{app_id}/events")
async def add_event_note(
    app_id: int,
    payload: AddEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a custom note or interaction to the application status ledger."""
    event = await add_application_event(db, app_id, note=payload.notes, source=payload.source)
    if not event:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await get_application_by_id(db, app_id)
    return {"status": "success", "application": serialize_application(app)}


@router.post("/{app_id}/evaluate")
async def trigger_career_ops_evaluation(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Run full Career-Ops A-H evaluation on the job posting and attach to application."""
    app = await get_application_by_id(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = app.job
    job_dict = {
        "company_name": job.company_name,
        "title": job.title,
        "location": job.location,
        "description": job.description,
        "raw_requirements": job.raw_requirements,
        "workplace_type": job.workplace_type,
    }

    eval_result = evaluate_with_career_ops(job_dict, report_num=app.id)

    app.evaluation_score = eval_result["evaluation_score"]
    app.match_grade = eval_result["match_grade"]
    app.salary_range = eval_result["salary_range"]
    app.star_stories = json.dumps(eval_result["star_stories"], ensure_ascii=False)
    app.form_answers = json.dumps(eval_result["form_answers"], ensure_ascii=False)
    app.key_contact_name = eval_result["key_contact_name"]
    app.key_contact_role = eval_result["key_contact_role"]
    app.outreach_message = eval_result["outreach_message"]
    app.evaluation_report_path = eval_result["report_rel_path"]

    await db.commit()
    await db.refresh(app)

    return {"status": "success", "application": serialize_application(app)}


@router.get("/{app_id}/report")
async def get_application_report(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the raw Markdown evaluation report text for this application."""
    app = await get_application_by_id(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    report_path_str = app.evaluation_report_path or app.report_path
    if not report_path_str:
        # If not evaluated yet, run evaluation on the fly!
        job = app.job
        job_dict = {
            "company_name": job.company_name,
            "title": job.title,
            "location": job.location,
            "description": job.description,
            "raw_requirements": job.raw_requirements,
            "workplace_type": job.workplace_type,
        }
        eval_result = evaluate_with_career_ops(job_dict, report_num=app.id)
        app.evaluation_score = eval_result["evaluation_score"]
        app.match_grade = eval_result["match_grade"]
        app.salary_range = eval_result["salary_range"]
        app.star_stories = json.dumps(eval_result["star_stories"], ensure_ascii=False)
        app.form_answers = json.dumps(eval_result["form_answers"], ensure_ascii=False)
        app.key_contact_name = eval_result["key_contact_name"]
        app.key_contact_role = eval_result["key_contact_role"]
        app.outreach_message = eval_result["outreach_message"]
        app.evaluation_report_path = eval_result["report_rel_path"]
        await db.commit()
        await db.refresh(app)
        report_path_str = app.evaluation_report_path

    full_p = settings.BASE_DIR / report_path_str
    if not full_p.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    content = full_p.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="text/markdown")


@router.post("/{app_id}/generate-documents")
async def generate_application_documents(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Compile custom single-page LaTeX CV and conditional Cover Letter for an application."""
    target_app = await get_application_by_id(db, app_id)
    if not target_app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = target_app.job
    job_dict = {
        "id": job.id,
        "company_name": job.company_name,
        "title": job.title,
        "location": job.location,
        "requires_cover_letter": target_app.requires_cover_letter,
    }

    try:
        cv_path = compile_custom_cv(job_dict)
        target_app.cv_pdf_path = str(cv_path)

        lm_path = None
        if target_app.requires_cover_letter:
            lm_path = generate_cover_letter(job_dict)
            if lm_path:
                target_app.cover_letter_pdf_path = str(lm_path)

        await db.commit()
        await db.refresh(target_app)

        cv_web_url = resolve_web_url(str(cv_path))
        lm_web_url = resolve_web_url(str(lm_path)) if lm_path else None

        return {
            "status": "success",
            "cv_pdf_path": target_app.cv_pdf_path,
            "cv_web_url": cv_web_url,
            "cover_letter_pdf_path": target_app.cover_letter_pdf_path,
            "cover_letter_web_url": lm_web_url,
        }
    except Exception as exc:
        logger.error(f"Failed to generate application documents: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
