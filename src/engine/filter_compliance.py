"""Job qualification and regulatory compliance engine for UTC TN10 engineering internships."""

import re
from datetime import datetime, timezone
from typing import Any
from src.utils.logger import log_audit_event, logger


# Positive technical domains aligned with UTC Génie Informatique (Filière IAD)
IAD_CORE_KEYWORDS = [
    r"\bia\b",
    r"\bai\b",
    r"intelligence artificielle",
    r"artificial intelligence",
    r"machine learning",
    r"deep learning",
    r"data science",
    r"science des donnes",
    r"science de donnes",
    r"llm",
    r"large language model",
    r"rag",
    r"retrieval[- ]augmented generation",
    r"knowledge graph",
    r"graphe[s]? de connaissances",
    r"nlp",
    r"natural language processing",
    r"computer vision",
    r"vision par ordinateur",
    r"pytorch",
    r"tensorflow",
    r"scikit[- ]learn",
    r"langchain",
    r"transformers",
    r"ontolog(y|ie)",
]

# Excluded keywords or domains incompatible with IAD engineering internships
EXCLUDED_KEYWORDS = [
    r"stage d'observation",
    r"stage de 3e",
    r"stage de dcouverte",
    r"commercial",
    r"comptabilit",
    r"rh\b",
    r"ressources humaines",
    r"community manager",
]

# Permitted geographic targets
ALLOWED_REGIONS = [
    r"paris",
    r"le-de-france",
    r"ile-de-france",
    r"idf",
    r"compi(e|g)ne",
    r"hauts-de-france",
    r"oise",
    r"tltravail",
    r"remote",
    r"hybride",
]


def check_date_compliance(start_date_str: str | None) -> tuple[bool, str]:
    """
    Validate that the internship does not start before February 1st, 2027.
    Flexibility rule: February 2027 onwards (Feb, Mar, Apr, etc.) is strictly compliant.
    """
    if not start_date_str:
        return True, "Date not explicitly declared (assumed flexible >= Feb 2027)"

    text = start_date_str.lower().strip()

    # Look for 2026 dates (Strict non-compliance)
    if "2026" in text:
        return False, f"Start date is in 2026 ({start_date_str}), violates P27 schedule."

    # Look for dates prior to February 2027
    if "janvier 2027" in text or "january 2027" in text or "01/2027" in text:
        return False, f"Start date in January 2027 ({start_date_str}) is earlier than allowed (Feb 2027)."

    return True, "Start date complies with UTC P27 criteria."


def check_duration_compliance(duration_weeks: int | None, description: str) -> tuple[bool, str]:
    """Validate that the internship is intended for 24 to 26 weeks (~6 months)."""
    if duration_weeks is not None:
        if 20 <= duration_weeks <= 28:
            return True, f"Duration of {duration_weeks} weeks is compliant (~6 months)."
        if duration_weeks < 20:
            return False, f"Duration of {duration_weeks} weeks is too short for TN10 (min 24 weeks)."

    desc_lower = description.lower()
    # Check mentions of months
    if "6 mois" in desc_lower or "6-month" in desc_lower or "24 semaines" in desc_lower or "26 semaines" in desc_lower:
        return True, "Explicit mention of 6-month duration found in description."

    if "2 mois" in desc_lower or "3 mois" in desc_lower or "8 semaines" in desc_lower or "12 semaines" in desc_lower:
        return False, "Detected short duration (2-3 months) incompatible with TN10."

    return True, "Duration not explicitly restricted, assumed 6-month standard graduation internship."


def evaluate_iad_compliance(title: str, description: str) -> tuple[bool, float, list[str]]:
    """Score the job posting for alignment with the UTC IAD curriculum."""
    combined_text = f"{title}\n{description}".lower()

    # Immediate rejection if excluded keywords are found
    for exc in EXCLUDED_KEYWORDS:
        if re.search(exc, combined_text, re.IGNORECASE):
            return False, 0.0, [f"Excluded keyword detected: {exc}"]

    matched_keywords = []
    for kw in IAD_CORE_KEYWORDS:
        if re.search(kw, combined_text, re.IGNORECASE):
            matched_keywords.append(kw.replace(r"\b", ""))

    # Compute a normalized score
    score = min(1.0, len(matched_keywords) * 0.25)
    is_compliant = len(matched_keywords) >= 1

    return is_compliant, round(score, 2), matched_keywords


def evaluate_job_posting(job_data: dict[str, Any]) -> dict[str, Any]:
    """Comprehensive qualification gate for a single job posting."""
    title = job_data.get("title", "")
    description = job_data.get("description", "")
    location = job_data.get("location", "")
    start_date = job_data.get("start_date")
    duration_weeks = job_data.get("duration_weeks")

    # 1. Date compliance
    date_ok, date_reason = check_date_compliance(start_date)

    # 2. Duration compliance
    duration_ok, duration_reason = check_duration_compliance(duration_weeks, description)

    # 3. IAD curriculum compliance
    iad_ok, iad_score, matched_skills = evaluate_iad_compliance(title, description)

    # 4. Location compliance
    loc_ok = any(re.search(reg, location.lower()) for reg in ALLOWED_REGIONS) or not location

    # Overall decision
    overall_compliant = date_ok and duration_ok and iad_ok and loc_ok

    result = {
        "is_iad_compliant": overall_compliant,
        "compliance_score": iad_score if overall_compliant else 0.0,
        "matched_skills": matched_skills,
        "audit_checks": {
            "date_compliance": {"passed": date_ok, "reason": date_reason},
            "duration_compliance": {"passed": duration_ok, "reason": duration_reason},
            "curriculum_compliance": {"passed": iad_ok, "score": iad_score},
            "location_compliance": {"passed": loc_ok, "location": location},
        },
    }

    log_audit_event(
        event_type="JOB_EVALUATED",
        entity_type="JOB",
        entity_id=job_data.get("id") or job_data.get("job_url"),
        action="EVALUATE_COMPLIANCE",
        details={
            "company_name": job_data.get("company_name"),
            "title": title,
            "overall_compliant": overall_compliant,
            "score": result["compliance_score"],
            "matched_skills": matched_skills,
        },
    )

    return result
