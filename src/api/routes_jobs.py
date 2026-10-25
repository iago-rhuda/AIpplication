"""Job listings and scraping trigger endpoints."""

from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import (
    create_application,
    create_doubt,
    create_job,
    get_all_jobs,
    get_job_by_url,
)
from src.database.session import get_db
from src.engine.filter_compliance import evaluate_job_posting
from src.engine.scraper import scraper
from src.utils.logger import log_audit_event, logger

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class ScrapeRequest(BaseModel):
    keywords: list[str] = ["Stage", "Intelligence Artificielle", "Data"]
    location: str = "Paris, Île-de-France, France"
    limit_per_source: int = 10


async def run_scraping_pipeline(keywords: list[str], location: str, limit: int, db: AsyncSession) -> None:
    """Background task executing scraping, regulatory compliance checks, and Kanban card creation."""
    logger.info(f"Triggering asynchronous job scraping for: {keywords}")
    scraped_jobs: list[dict[str, Any]] = []

    # Run LinkedIn and Welcome to the Jungle scraping
    try:
        linkedin_results = await scraper.scrape_linkedin_jobs(keywords, location, limit)
        scraped_jobs.extend(linkedin_results)
    except Exception as exc:
        logger.error(f"Error during LinkedIn scraping: {exc}")

    try:
        wttj_results = await scraper.scrape_welcome_to_the_jungle(keywords, location, limit)
        scraped_jobs.extend(wttj_results)
    except Exception as exc:
        logger.error(f"Error during WTTJ scraping: {exc}")

    # Process and filter each extracted job posting
    for raw_job in scraped_jobs:
        existing = await get_job_by_url(db, raw_job["job_url"])
        if existing:
            continue

        evaluation = evaluate_job_posting(raw_job)
        raw_job["is_iad_compliant"] = evaluation["is_iad_compliant"]
        raw_job["compliance_score"] = evaluation["compliance_score"]

        created_job = await create_job(db, raw_job)

        # If compliant, push to Kanban 'wishlist' column
        if created_job.is_iad_compliant:
            await create_application(db, {
                "job_id": created_job.id,
                "status": "wishlist",
                "application_mode": "semi_auto",
                "requires_cover_letter": False,
            })
        else:
            # If rejected or ambiguous, register in doubts for human review
            await create_doubt(db, {
                "job_id": created_job.id,
                "doubt_type": "compliance_rejection",
                "question_text": f"Vaga '{created_job.title}' na {created_job.company_name} não atingiu critérios automáticos de IAD/datas. Aprovar manualmente?",
                "suggested_answer": "Rejeitar por padrão salvo interesse explícito do candidato.",
            })


@router.get("")
async def list_jobs(compliant_only: bool = False, db: AsyncSession = Depends(get_db)):
    """Retrieve all stored job postings."""
    jobs = await get_all_jobs(db, compliant_only=compliant_only)
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/scrape")
async def trigger_scraping(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger background job scraping from external sources."""
    background_tasks.add_task(
        run_scraping_pipeline,
        payload.keywords,
        payload.location,
        payload.limit_per_source,
        db,
    )
    log_audit_event(
        event_type="SCRAPE_DISPATCHED",
        entity_type="SYSTEM",
        entity_id="SCHEDULER",
        action="TRIGGER_BACKGROUND_SCRAPE",
        details={"keywords": payload.keywords, "location": payload.location},
    )
    return {"status": "scraping_started", "message": "Scraping pipeline initiated in background."}
