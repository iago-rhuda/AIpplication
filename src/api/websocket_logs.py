"""Real-time log streaming WebSocket endpoint for the web dashboard."""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.config import settings
from src.utils.logger import logger

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """Stream live logs to connected web frontend clients."""
    await websocket.accept()
    log_file = settings.LOGS_DIR / "app.log"

    try:
        if not log_file.exists():
            log_file.touch()

        with open(log_file, encoding="utf-8", errors="replace") as f:
            # Move cursor towards the end of file (last 30 lines)
            lines = f.readlines()
            for line in lines[-30:]:
                await websocket.send_text(line)

            f.seek(0, 2)  # Seek to end

            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line)
                else:
                    await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from logs feed.")
    except Exception as exc:
        logger.warning(f"WebSocket logging feed exception: {exc}")
