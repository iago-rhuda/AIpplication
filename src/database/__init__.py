"""Database package exports."""

from src.database.crud import (
    create_application,
    create_doubt,
    create_job,
    create_or_update_cold_target,
    get_all_cold_targets,
    get_all_jobs,
    get_applications_by_status,
    get_job_by_url,
    get_pending_doubts,
    record_audit_log_entry,
    resolve_doubt,
    update_application_status,
)
from src.database.models import Application, AuditLog, ColdOutreachTarget, Doubt, Job
from src.database.session import Base, get_db, init_db

__all__ = [
    "Base",
    "get_db",
    "init_db",
    "Job",
    "Application",
    "Doubt",
    "ColdOutreachTarget",
    "AuditLog",
    "create_job",
    "get_job_by_url",
    "get_all_jobs",
    "create_application",
    "update_application_status",
    "get_applications_by_status",
    "create_doubt",
    "resolve_doubt",
    "get_pending_doubts",
    "create_or_update_cold_target",
    "get_all_cold_targets",
    "record_audit_log_entry",
]
