"""Job qualification and regulatory compliance engine for UTC TN10 engineering internships."""

import re
from datetime import datetime, timezone
from typing import Any
from src.utils.logger import log_audit_event, logger


# Positive technical domains aligned with UTC Génie Informatique (Filière IAD)
# Positive technical domains aligned with UTC Génie Informatique (Filière IAD)
IAD_CORE_KEYWORDS = [
    r"\bia\b",
    r"\bai\b",
    r"intelligence artificielle",
    r"artificial intelligence",
    r"machine learning",
    r"deep learning",
    r"data scientist",
    r"data science",
    r"science des donn[eé]es",
    r"data engineer",
    r"ing[eé]nieur donn[eé]es",
    r"ing[eé]nieur data",
    r"data analyst",
    r"data analytics",
    r"llm",
    r"large language model",
    r"rag\b",
    r"retrieval[- ]augmented generation",
    r"ia g[eé]n[eé]rative",
    r"generative ai",
    r"genai",
    r"agentic",
    r"agents ia",
    r"knowledge graph",
    r"graphe[s]? de connaissances",
    r"nlp\b",
    r"natural language processing",
    r"traitement automatique du langage",
    r"taln",
    r"computer vision",
    r"vision par ordinateur",
    r"pytorch",
    r"tensorflow",
    r"scikit[- ]learn",
    r"sklearn",
    r"langchain",
    r"transformers",
    r"hugging\s*face",
    r"llamaindex",
    r"ontolog(y|ie)",
    r"mlops",
    r"python",
    r"fastapi",
    r"recherche ia",
    r"ia frugale",
    r"mod[eè]les de fondation",
]

# Excluded keywords or domains incompatible with IAD engineering internships
EXCLUDED_KEYWORDS = [
    r"stage d'observation",
    r"stage de 3[eè]me",
    r"stage de 3e",
    r"stage de d[eé]couverte",
    r"commercial\b",
    r"comptabilit[eé]",
    r"\brh\b",
    r"ressources humaines",
    r"community manager",
    r"assistant(e)? de direction",
    r"secr[eé]tariat",
]

# Permitted geographic targets: Paris, Île-de-France tech hubs, UTC Compiègne, France, and Remote
ALLOWED_REGIONS = [
    r"paris",
    r"île-de-france",
    r"ile-de-france",
    r"idf",
    r"france",
    r"compi[eè]gne",
    r"hauts-de-france",
    r"oise",
    r"v[eé]lizy",
    r"rueil",
    r"poissy",
    r"massy",
    r"palaiseau",
    r"saclay",
    r"courbevoie",
    r"la d[eé]fense",
    r"d[eé]fense",
    r"nanterre",
    r"boulogne",
    r"issy",
    r"levallois",
    r"neuilly",
    r"clichy",
    r"saint-denis",
    r"montrouge",
    r"versailles",
    r"orsay",
    r"ch[aâ]tillon",
    r"guyancourt",
    r"ivry",
    r"fontenay",
    r"cr[eé]teil",
    r"bagneux",
    r"[eé]vry",
    r"antony",
    r"suresnes",
    r"meudon",
    r"s[eè]vres",
    r"puteaux",
    r"lyon",
    r"toulouse",
    r"grenoble",
    r"rennes",
    r"nantes",
    r"bordeaux",
    r"lille",
    r"sophia",
    r"nice",
    r"strasbourg",
    r"t[eé]l[eé]travail",
    r"remote",
    r"hybride",
    r"hybrid",
]


def check_date_compliance(start_date_str: str | None) -> tuple[bool, str]:
    """
    Validate that the internship aligns with UTC TN10 graduation schedule (P27, ~Feb 2027 onwards).
    Accepts flexible, open, or 2027 dates. Rejects only explicit past dates (e.g., 2025 or early 2026).
    """
    if not start_date_str:
        return True, "Date not explicitly declared (assumed flexible >= Feb 2027)"

    text = start_date_str.lower().strip()

    # Look for explicitly past start terms (prior to 2027 semester)
    if "janvier 2026" in text or "février 2026" in text or "fevrier 2026" in text or "2025" in text or "2024" in text:
        return False, f"Start date is in the past ({start_date_str}), incompatible with P27 schedule."

    # Look for dates prior to February 2027 (e.g. January 2027 if non-negotiable)
    if "janvier 2027" in text or "january 2027" in text or "01/2027" in text:
        return False, f"Start date in January 2027 ({start_date_str}) is earlier than allowed (Feb 2027)."

    return True, "Start date complies with UTC P27 criteria."


def check_duration_compliance(duration_weeks: int | None, description: str) -> tuple[bool, str]:
    """Validate that the internship is intended for 20 to 28 weeks (~5-6 months graduation project)."""
    if duration_weeks is not None:
        if 20 <= duration_weeks <= 28:
            return True, f"Duration of {duration_weeks} weeks is compliant (~6 months)."
        if duration_weeks < 20:
            return False, f"Duration of {duration_weeks} weeks is too short for TN10 (min 24 weeks)."

    desc_lower = description.lower()
    # Check mentions of months
    if any(m in desc_lower for m in ["6 mois", "6-month", "24 semaines", "26 semaines", "5 à 6 mois", "5-6 mois", "fin d'études", "pfe"]):
        return True, "Explicit mention of ~6-month graduation duration found in description."

    if any(m in desc_lower for m in ["1 mois", "2 mois", "3 mois", "8 semaines", "12 semaines"]):
        return False, "Detected short duration (1-3 months) incompatible with graduation TN10 internship."

    return True, "Duration not explicitly restricted, assumed standard 6-month graduation internship."


def evaluate_iad_compliance(title: str, description: str) -> tuple[bool, float, list[str]]:
    """Score the job posting for alignment with the UTC IAD curriculum."""
    combined_text = f"{title}\n{description}".lower()

    # Immediate rejection if excluded non-engineering keywords are found
    for exc in EXCLUDED_KEYWORDS:
        if re.search(exc, combined_text, re.IGNORECASE):
            return False, 0.0, [f"Excluded keyword detected: {exc}"]

    matched_keywords = []
    for kw in IAD_CORE_KEYWORDS:
        if re.search(kw, combined_text, re.IGNORECASE):
            matched_keywords.append(kw.replace(r"\b", "").replace(r"\s*", " "))

    # High priority bonus if title explicitly contains Data Scientist, IA, AI, Machine Learning, etc.
    title_lower = title.lower()
    title_matches = [
        "data scientist", "data science", "ia", "ai", "machine learning",
        "deep learning", "llm", "rag", "data engineer", "intelligence artificielle",
        "nlp", "computer vision", "ia générative", "generative ai"
    ]
    has_title_signal = any(re.search(rf"\b{re.escape(tm)}\b", title_lower) for tm in title_matches)

    # Compute a normalized score
    base_score = len(matched_keywords) * 0.25
    if has_title_signal:
        base_score = max(base_score, 0.6)
    score = min(1.0, base_score)
    is_compliant = len(matched_keywords) >= 1 or has_title_signal

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

    # 4. Location compliance: accepts any matched region, France, or unspecified/remote
    loc_ok = (
        not location
        or any(re.search(reg, location.lower()) for reg in ALLOWED_REGIONS)
        or "france" in location.lower()
    )

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
