"""Career-Ops synchronization module for status ledger, tracker markdown, and contacts.

Maintains bidirectional consistency between SQLite persistence and canonical Career-Ops files:
- data/status-log.tsv: Append-only status transition ledger
- data/applications.md: Canonical human-readable tracker table
- data/contacts.tsv: Phonebook and networking targets
- data/follow-ups.md: Follow-up cadence and alert dashboard
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.utils.logger import log_audit_event, logger


STATUS_LOG_PATH = settings.BASE_DIR / "data" / "status-log.tsv"
APPLICATIONS_MD_PATH = settings.BASE_DIR / "data" / "applications.md"
CONTACTS_TSV_PATH = settings.BASE_DIR / "data" / "contacts.tsv"
FOLLOWUPS_MD_PATH = settings.BASE_DIR / "data" / "follow-ups.md"


def ensure_data_files() -> None:
    """Ensure data files and directories exist with proper headers."""
    data_dir = settings.BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    if not STATUS_LOG_PATH.exists():
        header = "num\tdate\tfrom\tto\tsource\tnote\n"
        STATUS_LOG_PATH.write_text(header, encoding="utf-8")

    if not CONTACTS_TSV_PATH.exists():
        header = "name\tcompany\ttype\ttitle\tphone\temail\tlinkedin\ttracker_num\tnotes\n"
        CONTACTS_TSV_PATH.write_text(header, encoding="utf-8")


def append_status_log(
    tracker_num: int,
    from_status: str | None,
    to_status: str,
    source: str = "user",
    note: str | None = None,
    event_time: datetime | None = None,
) -> None:
    """Append a status change entry to canonical data/status-log.tsv."""
    ensure_data_files()
    dt = event_time or datetime.now(timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")

    from_val = from_status if from_status else "-"
    to_val = to_status
    source_val = source or "user"
    clean_note = (note or "").replace("\t", " ").replace("\n", " ").strip()

    line = f"{tracker_num}\t{date_str}\t{from_val}\t{to_val}\t{source_val}\t{clean_note}\n"

    try:
        with open(STATUS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
        logger.debug(f"Appended status-log.tsv entry: #{tracker_num} {from_val} -> {to_val}")
    except Exception as exc:
        logger.error(f"Failed to append to status-log.tsv: {exc}")


def append_or_update_contact(
    name: str,
    company: str,
    contact_type: str = "recruiter",
    title: str = "",
    phone: str = "",
    email: str = "",
    linkedin: str = "",
    tracker_num: int | str = "-",
    notes: str = "",
) -> None:
    """Record contact details in data/contacts.tsv."""
    ensure_data_files()
    clean_notes = (notes or "").replace("\t", " ").replace("\n", " ").strip()
    line = f"{name}\t{company}\t{contact_type}\t{title}\t{phone}\t{email}\t{linkedin}\t{tracker_num}\t{clean_notes}\n"

    try:
        with open(CONTACTS_TSV_PATH, "a", encoding="utf-8") as f:
            f.write(line)
        logger.debug(f"Recorded contact in contacts.tsv: {name} ({company})")
    except Exception as exc:
        logger.error(f"Failed to append to contacts.tsv: {exc}")


def sync_applications_markdown(applications: list[dict[str, Any]]) -> None:
    """Rebuild data/applications.md table reflecting the current pipeline state."""
    ensure_data_files()
    lines = [
        "# Applications Tracker (Career-Ops UTC TN10 Sync)\n",
        "> Canonical human-readable index of internship applications with full traceability and evaluation scores.\n",
        "\n",
        "| # | Date | Company | Role | Status | Score | PDF | Report | Notes | URL |",
        "|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|:---|",
    ]

    for app in applications:
        num = f"{app['id']:03d}"
        created_at = app.get("created_at") or datetime.now(timezone.utc).isoformat()
        date_str = created_at[:10]
        job = app.get("job") or {}
        company = job.get("company_name", "Unknown")
        role = job.get("title", "Stage IA")
        status = app.get("status", "wishlist")
        score = f"{app.get('evaluation_score', 4.0):.1f}/5.0"
        
        pdf_link = f"[CV]({app['cv_web_url']})" if app.get("cv_web_url") else "❌"
        report_link = f"[Report]({app['report_web_url']})" if app.get("report_web_url") else "-"
        notes = (app.get("notes") or "").replace("|", "-").replace("\n", " ")
        job_url = job.get("job_url", "")
        url_link = f"[Link]({job_url})" if job_url else "-"

        lines.append(
            f"| {num} | {date_str} | **{company}** | {role} | `{status}` | {score} | {pdf_link} | {report_link} | {notes} | {url_link} |"
        )

    lines.append("\n")
    content = "\n".join(lines)

    try:
        APPLICATIONS_MD_PATH.write_text(content, encoding="utf-8")
        logger.debug("Successfully synchronized data/applications.md")
    except Exception as exc:
        logger.error(f"Failed to sync applications.md: {exc}")


def sync_followups_markdown(applications: list[dict[str, Any]]) -> None:
    """Generate follow-up radar in data/follow-ups.md."""
    ensure_data_files()
    now = datetime.now(timezone.utc)

    lines = [
        "# Follow-up Radar & Outreach Cadence (UTC TN10)",
        "> Automated cadence monitoring: 5-7 days for direct applications, 7-10 days for recruiters.\n",
        "| # | Company | Role | Stage | Applied Date | Days Elapsed | Cadence Recommendation | Contact |",
        "|:---:|:---|:---|:---:|:---:|:---:|:---|:---|",
    ]

    active_count = 0
    for app in applications:
        if app.get("status") not in ("applied", "interview"):
            continue

        active_count += 1
        num = f"{app['id']:03d}"
        job = app.get("job") or {}
        company = job.get("company_name", "Unknown")
        role = job.get("title", "Stage IA")
        status = app.get("status")
        applied_at = app.get("applied_at") or app.get("created_at") or now.isoformat()
        
        try:
            applied_dt = datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
            if applied_dt.tzinfo is None:
                applied_dt = applied_dt.replace(tzinfo=timezone.utc)
            days = (now - applied_dt).days
        except Exception:
            days = 0

        if days <= 4:
            rec = "🟢 Recent — Waiting on response window (cadence: 7 days)"
        elif 5 <= days <= 7:
            rec = "🟡 Action Window — Send polite 1st follow-up note via LinkedIn/Email"
        elif 8 <= days <= 14:
            rec = "🟠 High Priority — 2nd follow-up with value add / project reference"
        else:
            rec = "🔴 Cold / Stale — Mark for archive or alternative contact outreach"

        contact = app.get("key_contact_name") or "Hiring Team"
        lines.append(
            f"| {num} | **{company}** | {role} | `{status}` | {applied_at[:10]} | {days}d | {rec} | {contact} |"
        )

    if active_count == 0:
        lines.append("| - | *No active applications in applied or interview stage* | - | - | - | - | - | - |")

    lines.append("\n")
    try:
        FOLLOWUPS_MD_PATH.write_text("\n".join(lines), encoding="utf-8")
        logger.debug("Successfully synchronized data/follow-ups.md")
    except Exception as exc:
        logger.error(f"Failed to sync follow-ups.md: {exc}")
