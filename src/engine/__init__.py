"""Engine package exports."""

from src.engine.cold_outreach import CURATED_FRENCH_AI_TARGETS, generate_cold_outreach_report
from src.engine.cover_letter_generator import generate_cover_letter
from src.engine.filter_compliance import evaluate_job_posting
from src.engine.latex_compiler import compile_custom_cv
from src.engine.scraper import scraper

__all__ = [
    "scraper",
    "evaluate_job_posting",
    "compile_custom_cv",
    "generate_cover_letter",
    "CURATED_FRENCH_AI_TARGETS",
    "generate_cold_outreach_report",
]
