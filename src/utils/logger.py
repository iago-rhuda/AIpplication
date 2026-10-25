"""Logging and audit trail configuration using Loguru."""

import json
import sys
from datetime import datetime, timezone
from typing import Any
from loguru import logger
from src.config import settings

# Clear default Loguru handlers
logger.remove()

# 1. Standard Output Sink (Colored terminal logs for development)
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# 2. Operational Application Log Sink (Daily rotation, compressed archives)
app_log_path = settings.LOGS_DIR / "app.log"
logger.add(
    app_log_path,
    level="DEBUG",
    rotation="00:00",
    retention="14 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
)

# 3. Dedicated Structured JSON Audit Trail Sink
audit_log_path = settings.LOGS_DIR / "audit.log"


def audit_filter(record: dict) -> bool:
    """Filter records to capture only audit-tagged events."""
    return bool(record["extra"].get("is_audit", False))


logger.add(
    audit_log_path,
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8",
    filter=audit_filter,
    serialize=True,
)


def log_audit_event(
    event_type: str,
    entity_type: str,
    entity_id: int | str | None,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a high-integrity structured audit record for all critical pipeline events."""
    audit_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "details": details or {},
    }

    audit_logger = logger.bind(is_audit=True)
    audit_logger.info(json.dumps(audit_payload, ensure_ascii=False))


__all__ = ["logger", "log_audit_event"]
