"""Human-in-the-loop doubts and resolution endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import get_pending_doubts, resolve_doubt
from src.database.session import get_db
from src.utils.logger import log_audit_event, logger

router = APIRouter(prefix="/api/doubts", tags=["Doubts"])


class DoubtResolutionRequest(BaseModel):
    user_decision: str
    status: str = "resolved"  # 'resolved', 'ignored'


@router.get("")
async def list_pending_doubts(db: AsyncSession = Depends(get_db)):
    """Retrieve all pending ambiguities requiring user review with comprehensive job details."""
    doubts = await get_pending_doubts(db)
    items = []
    for d in doubts:
        job_data = None
        if d.job:
            job_data = {
                "id": d.job.id,
                "title": d.job.title,
                "company_name": d.job.company_name,
                "location": d.job.location,
                "job_url": d.job.job_url,
                "source": d.job.source,
                "workplace_type": d.job.workplace_type,
                "start_date": d.job.start_date,
                "duration_weeks": d.job.duration_weeks,
                "description": d.job.description,
                "raw_requirements": d.job.raw_requirements,
                "compliance_score": d.job.compliance_score,
                "is_iad_compliant": d.job.is_iad_compliant,
            }
        items.append({
            "id": d.id,
            "job_id": d.job_id,
            "doubt_type": d.doubt_type,
            "question_text": d.question_text,
            "suggested_answer": d.suggested_answer,
            "user_decision": d.user_decision,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "job": job_data,
        })
    return {"doubts": items, "total": len(items)}


@router.post("/{doubt_id}/resolve")
async def answer_doubt(
    doubt_id: int,
    payload: DoubtResolutionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit user answer or decision for a pending doubt."""
    resolved_doubt, promoted_app = await resolve_doubt(db, doubt_id, payload.user_decision, payload.status)
    if not resolved_doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
    return {
        "status": "success",
        "doubt_id": resolved_doubt.id,
        "promoted_application_id": promoted_app.id if promoted_app else None,
        "message": "Doubt resolved and application promoted to Wishlist" if promoted_app else "Doubt updated",
    }


@router.post("/resolve-all")
async def resolve_all_doubts(
    payload: DoubtResolutionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch approve or discard all pending doubts."""
    doubts = await get_pending_doubts(db)
    resolved_count = 0
    promoted_count = 0
    for d in doubts:
        _, app = await resolve_doubt(db, d.id, payload.user_decision, payload.status)
        resolved_count += 1
        if app:
            promoted_count += 1
    return {
        "status": "success",
        "resolved_count": resolved_count,
        "promoted_count": promoted_count,
    }
