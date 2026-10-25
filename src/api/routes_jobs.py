import json
from datetime import datetime, timezone
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
from src.database.session import async_session_factory, get_db
from src.engine.career_ops_evaluator import evaluate_with_career_ops
from src.engine.career_ops_sync import append_or_update_contact
from src.engine.filter_compliance import evaluate_job_posting
from src.engine.scraper import scraper
from src.utils.logger import log_audit_event, logger

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

scraping_state: dict[str, Any] = {
    "is_running": False,
    "progress": 0,
    "step": "idle",
    "message": "Pipeline idle. Ready to scrape.",
    "scraped_count": 0,
    "new_jobs_count": 0,
    "compliant_count": 0,
    "doubts_count": 0,
    "error": None,
    "last_run": None,
}


class ScrapeRequest(BaseModel):
    keywords: list[str] = ["Stage", "Intelligence Artificielle", "Data"]
    location: str = "Paris, Île-de-France, France"
    limit_per_source: int = 10


async def run_scraping_pipeline(keywords: list[str], location: str, limit: int) -> None:
    """Background task executing scraping, regulatory compliance checks, and Kanban card creation."""
    global scraping_state
    scraping_state.update({
        "is_running": True,
        "progress": 5,
        "step": "linkedin",
        "message": f"Starting scraping: Searching LinkedIn for {', '.join(keywords[:2])}...",
        "scraped_count": 0,
        "new_jobs_count": 0,
        "compliant_count": 0,
        "doubts_count": 0,
        "error": None,
        "last_run": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"Triggering asynchronous job scraping for: {keywords}")
    scraped_jobs: list[dict[str, Any]] = []

    # 1. LinkedIn scraping
    try:
        linkedin_results = await scraper.scrape_linkedin_jobs(keywords, location, limit)
        scraped_jobs.extend(linkedin_results)
        scraping_state["scraped_count"] = len(scraped_jobs)
        scraping_state["progress"] = 40
        scraping_state["step"] = "wttj"
        scraping_state["message"] = f"LinkedIn finished ({len(linkedin_results)} jobs). Searching Welcome to the Jungle..."
        logger.info(f"LinkedIn scraping extracted {len(linkedin_results)} jobs.")
    except Exception as exc:
        logger.error(f"Error during LinkedIn scraping: {exc}")
        scraping_state["message"] = f"LinkedIn scraper note: {exc}. Continuing to WTTJ..."

    # 2. Welcome to the Jungle scraping
    try:
        wttj_results = await scraper.scrape_welcome_to_the_jungle(keywords, location, limit)
        scraped_jobs.extend(wttj_results)
        scraping_state["scraped_count"] = len(scraped_jobs)
        scraping_state["progress"] = 70
        scraping_state["step"] = "evaluating"
        scraping_state["message"] = f"Scraped {len(scraped_jobs)} total listings. Evaluating compliance & syncing Kanban..."
        logger.info(f"Welcome to the Jungle scraping extracted {len(wttj_results)} jobs.")
    except Exception as exc:
        logger.error(f"Error during WTTJ scraping: {exc}")

    # 3. Process, evaluate compliance, and persist
    new_jobs_count = 0
    compliant_count = 0
    doubts_count = 0

    try:
        async with async_session_factory() as db:
            total_jobs = len(scraped_jobs)
            for idx, raw_job in enumerate(scraped_jobs):
                if total_jobs > 0:
                    scraping_state["progress"] = 70 + int((idx / total_jobs) * 25)

                existing = await get_job_by_url(db, raw_job["job_url"])
                if existing:
                    continue

                new_jobs_count += 1
                evaluation = evaluate_job_posting(raw_job)
                raw_job["is_iad_compliant"] = evaluation["is_iad_compliant"]
                raw_job["compliance_score"] = evaluation["compliance_score"]

                created_job = await create_job(db, raw_job)

                # If compliant, push to Kanban 'wishlist' column
                if created_job.is_iad_compliant:
                    compliant_count += 1
                    
                    # Run Career-Ops A-H evaluation
                    eval_res = evaluate_with_career_ops(raw_job, report_num=created_job.id)

                    app = await create_application(
                        db,
                        {
                            "job_id": created_job.id,
                            "status": "wishlist",
                            "application_mode": "semi_auto",
                            "requires_cover_letter": False,
                            "evaluation_score": eval_res["evaluation_score"],
                            "match_grade": eval_res["match_grade"],
                            "salary_range": eval_res["salary_range"],
                            "star_stories": json.dumps(eval_res["star_stories"], ensure_ascii=False),
                            "form_answers": json.dumps(eval_res["form_answers"], ensure_ascii=False),
                            "key_contact_name": eval_res["key_contact_name"],
                            "key_contact_role": eval_res["key_contact_role"],
                            "outreach_message": eval_res["outreach_message"],
                            "evaluation_report_path": eval_res["report_rel_path"],
                        },
                        source="scraper",
                        initial_note="Ingested via automated scraper and qualified for UTC TN10 P27",
                    )

                    # Record contact discovery in contacts.tsv
                    if eval_res.get("key_contact_name"):
                        append_or_update_contact(
                            name=eval_res["key_contact_name"],
                            company=created_job.company_name,
                            contact_type="recruiter",
                            title=eval_res["key_contact_role"],
                            tracker_num=app.id,
                            notes=f"Identified for {created_job.title}",
                        )
                else:
                    # If rejected or ambiguous, register in doubts for human review
                    doubts_count += 1
                    await create_doubt(db, {
                        "job_id": created_job.id,
                        "doubt_type": "compliance_rejection",
                        "question_text": f"Vaga '{created_job.title}' na {created_job.company_name} não atingiu critérios automáticos de IAD/datas. Aprovar manualmente?",
                        "suggested_answer": "Rejeitar por padrão salvo interesse explícito do candidato.",
                    })

            scraping_state.update({
                "is_running": False,
                "progress": 100,
                "step": "completed",
                "message": f"Complete! Found {new_jobs_count} new postings ({compliant_count} IAD compliant in Wishlist, {doubts_count} pending doubts).",
                "new_jobs_count": new_jobs_count,
                "compliant_count": compliant_count,
                "doubts_count": doubts_count,
            })
            logger.info(f"Scraping run completed: {new_jobs_count} new jobs ({compliant_count} compliant, {doubts_count} doubts).")
    except Exception as exc:
        logger.error(f"Error persisting scraped jobs: {exc}")
        scraping_state.update({
            "is_running": False,
            "progress": 100,
            "step": "error",
            "error": str(exc),
            "message": f"Processing finished with error: {exc}",
        })


@router.get("")
async def list_jobs(compliant_only: bool = False, db: AsyncSession = Depends(get_db)):
    """Retrieve all stored job postings."""
    jobs = await get_all_jobs(db, compliant_only=compliant_only)
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/scrape/status")
async def get_scraping_status():
    """Retrieve the current real-time scraping progress and status."""
    return scraping_state


@router.post("/scrape")
async def trigger_scraping(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger background job scraping from external sources."""
    if scraping_state["is_running"]:
        return {
            "status": "already_running",
            "message": "Scraping is already running in background.",
            "state": scraping_state,
        }

    background_tasks.add_task(
        run_scraping_pipeline,
        payload.keywords,
        payload.location,
        payload.limit_per_source,
    )
    log_audit_event(
        event_type="SCRAPE_DISPATCHED",
        entity_type="SYSTEM",
        entity_id="SCHEDULER",
        action="TRIGGER_BACKGROUND_SCRAPE",
        details={"keywords": payload.keywords, "location": payload.location},
    )
    return {
        "status": "scraping_started",
        "message": "Scraping pipeline initiated in background.",
        "state": scraping_state,
    }
