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
    """Retrieve all pending ambiguities requiring user review."""
    doubts = await get_pending_doubts(db)
    return {"doubts": doubts, "total": len(doubts)}


@router.post("/{doubt_id}/resolve")
async def answer_doubt(
    doubt_id: int,
    payload: DoubtResolutionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit user answer or decision for a pending doubt."""
    resolved = await resolve_doubt(db, doubt_id, payload.user_decision, payload.status)
    if not resolved:
        raise HTTPException(status_code=404, detail="Doubt not found")
    return {"status": "success", "doubt": resolved}
