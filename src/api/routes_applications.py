from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.crud import (
    get_applications_by_status,
    update_application_status,
)
from src.database.models import Application
from src.database.session import get_db
from src.engine.cover_letter_generator import generate_cover_letter
from src.engine.latex_compiler import compile_custom_cv
from src.utils.logger import log_audit_event, logger

router = APIRouter(prefix="/api/applications", tags=["Applications"])


class StatusUpdateRequest(BaseModel):
    status: str  # 'wishlist', 'to_apply', 'applied', 'interview', 'offer', 'rejected'
    notes: str | None = None


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


def serialize_application(app: Application) -> dict[str, Any]:
    """Format Application model with relative web URLs for browser downloads."""
    cv_web_url = resolve_web_url(app.cv_pdf_path)
    lm_web_url = resolve_web_url(app.cover_letter_pdf_path)

    return {
        "id": app.id,
        "job_id": app.job_id,
        "status": app.status,
        "application_mode": app.application_mode,
        "cv_pdf_path": app.cv_pdf_path,
        "cv_web_url": cv_web_url,
        "cover_letter_pdf_path": app.cover_letter_pdf_path,
        "cover_letter_web_url": lm_web_url,
        "requires_cover_letter": app.requires_cover_letter,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "notes": app.notes,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "job": {
            "id": app.job.id,
            "company_name": app.job.company_name,
            "title": app.job.title,
            "location": app.job.location,
            "job_url": app.job.job_url,
            "source": app.job.source,
            "workplace_type": app.job.workplace_type,
            "is_iad_compliant": app.job.is_iad_compliant,
            "compliance_score": app.job.compliance_score,
        } if app.job else None,
    }


@router.get("")
async def list_applications(status: str | None = None, db: AsyncSession = Depends(get_db)):
    """Retrieve all applications grouped into Kanban columns."""
    apps = await get_applications_by_status(db, status=status)
    serialized = [serialize_application(a) for a in apps]
    return {"applications": serialized, "total": len(serialized)}


@router.patch("/{app_id}/status")
async def change_application_status(
    app_id: int,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition application across Kanban columns with full audit logging."""
    updated = await update_application_status(db, app_id, payload.status, payload.notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"status": "success", "application": serialize_application(updated)}


@router.post("/{app_id}/generate-documents")
async def generate_application_documents(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Compile custom single-page LaTeX CV and conditional Cover Letter for an application."""
    apps = await get_applications_by_status(db)
    target_app = next((a for a in apps if a.id == app_id), None)
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
