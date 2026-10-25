import asyncio
import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.session import async_session_factory
from sqlalchemy import text


async def reset_database():
    print("Purging SQLite database tables...")
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM status_events;"))
        await session.execute(text("DELETE FROM applications;"))
        await session.execute(text("DELETE FROM doubts;"))
        await session.execute(text("DELETE FROM jobs;"))
        await session.commit()
    print("SQLite tables successfully purged.")


def reset_ledgers():
    print("Resetting Career-Ops canonical ledgers...")
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. status-log.tsv
    with open(data_dir / "status-log.tsv", "w", encoding="utf-8") as f:
        f.write("num\tdate\tfrom\tto\tsource\tnote\n")

    # 2. applications.md
    with open(data_dir / "applications.md", "w", encoding="utf-8") as f:
        f.write(
            "# Applications Tracker (Career-Ops UTC TN10 Sync)\n\n"
            "> Canonical human-readable index of internship applications with full traceability and evaluation scores.\n\n"
            "| # | Date | Company | Role | Status | Score | PDF | Report | Notes | URL |\n"
            "|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|:---|\n"
        )

    # 3. contacts.tsv
    with open(data_dir / "contacts.tsv", "w", encoding="utf-8") as f:
        f.write("name\tcompany\ttype\ttitle\tphone\temail\tlinkedin\ttracker_num\tnotes\n")

    # 4. follow-ups.md
    with open(data_dir / "follow-ups.md", "w", encoding="utf-8") as f:
        f.write(
            "# Follow-up Radar & Outreach Cadence (UTC TN10)\n"
            "> Automated cadence monitoring: 5-7 days for direct applications, 7-10 days for recruiters.\n\n"
            "| # | Company | Role | Stage | Applied Date | Days Elapsed | Cadence Recommendation | Contact |\n"
            "|:---:|:---|:---|:---:|:---:|:---:|:---|:---|\n"
        )

    # 5. Clear reports/
    reports_dir = Path("reports")
    if reports_dir.exists():
        for item in reports_dir.glob("*.md"):
            try:
                item.unlink()
            except Exception as e:
                print(f"Could not delete {item}: {e}")

    print("Canonical ledgers and reports directory reset successfully.")


async def main():
    await reset_database()
    reset_ledgers()
    print("Full pipeline data reset completed!")


if __name__ == "__main__":
    asyncio.run(main())
