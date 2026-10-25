"""Cold outreach management and reporting endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import create_or_update_cold_target, get_all_cold_targets
from src.database.session import get_db
from src.engine.cold_outreach import CURATED_FRENCH_AI_TARGETS, generate_cold_outreach_report

router = APIRouter(prefix="/api/cold-outreach", tags=["Cold Outreach"])


@router.get("")
async def list_cold_targets(db: AsyncSession = Depends(get_db)):
    """Retrieve all mapped speculative outreach companies."""
    targets = await get_all_cold_targets(db)
    if not targets:
        # Seed default curated targets on first call
        for item in CURATED_FRENCH_AI_TARGETS:
            await create_or_update_cold_target(db, item)
        targets = await get_all_cold_targets(db)

    return {"targets": targets, "total": len(targets)}


@router.post("/generate-report")
async def build_cold_report():
    """Regenerate the markdown dossier for speculative outreach."""
    path = generate_cold_outreach_report()
    return {"status": "success", "report_path": str(path)}
