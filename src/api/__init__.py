"""API package exports."""

from src.api.routes_applications import router as router_applications
from src.api.routes_cold_outreach import router as router_cold_outreach
from src.api.routes_doubts import router as router_doubts
from src.api.routes_jobs import router as router_jobs
from src.api.websocket_logs import router as router_ws

__all__ = [
    "router_jobs",
    "router_applications",
    "router_doubts",
    "router_cold_outreach",
    "router_ws",
]
