"""
stream.py - WebSocket Streaming Routes

WebSocket endpoints for real-time screen streaming and logs.
"""

import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

router = APIRouter()

# Global log queue for WebSocket streaming
log_queue = deque(maxlen=1000)  # Keep last 1000 logs


class WebSocketLogHandler(logging.Handler):
    """Custom log handler that captures logs for WebSocket streaming."""
    
    def emit(self, record):
        try:
            # Format log entry
            log_entry = {
                "type": "log",
                "level": record.levelname.lower(),
                "message": self.format(record),
                "timestamp": datetime.now().isoformat(),
                "logger": record.name
            }
            
            # Add to queue (WebSocket clients will poll from queue)
            log_queue.append(log_entry)
            
        except Exception:
            # Avoid recursion in error handling
            pass


def setup_websocket_logging():
    """Setup WebSocket log handler for backend logs."""
    ws_handler = WebSocketLogHandler()
    ws_handler.setLevel(logging.INFO)
    
    # Format: just the message, timestamp added in emit()
    formatter = logging.Formatter('%(message)s')
    ws_handler.setFormatter(formatter)
    
    # Add to specific loggers we want to stream
    loggers_to_stream = [
        'backend.langgraph.nodes',
        'backend.tools.adb_tool',
        'backend.tools.vision_tool',
        'backend.tools.verification_tool',
        'backend.services.agent_orchestrator',
        'backend.routes.standalone',
        'backend.routes.test_execution',
        'backend.routes.hitl'
    ]
    
    for logger_name in loggers_to_stream:
        log = logging.getLogger(logger_name)
        log.addHandler(ws_handler)
        log.setLevel(logging.INFO)


@router.websocket("/screen")
async def websocket_screen_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time screen streaming.
    
    Streams screenshots as MJPEG at 2 FPS.
    """
    await websocket.accept()
    logger.info("Screen stream WebSocket connected")
    
    try:
        from backend.tools import toolkit
        
        while True:
            # Capture screenshot
            screenshot_bytes = toolkit.screenshot.capture_raw()
            
            if screenshot_bytes:
                # Send as binary WebSocket message
                await websocket.send_bytes(screenshot_bytes)
            
            # Control FPS (2 FPS = 500ms delay)
            await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        logger.info("Screen stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Screen stream error: {e}")
        await websocket.close()


@router.websocket("/logs")
async def websocket_logs_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming.
    
    Streams execution logs as JSON messages from log queue.
    """
    await websocket.accept()
    logger.info("Logs stream WebSocket connected")
    
    # Track last sent log index
    sent_count = 0
    
    try:
        # Send initial logs from queue
        current_logs = list(log_queue)
        for log_entry in current_logs:
            await websocket.send_json(log_entry)
        sent_count = len(current_logs)
        
        # Continuously check for new logs
        while True:
            current_logs = list(log_queue)
            
            # Send only new logs
            if len(current_logs) > sent_count:
                new_logs = current_logs[sent_count:]
                for log_entry in new_logs:
                    await websocket.send_json(log_entry)
                sent_count = len(current_logs)
            
            # Check every 100ms for new logs
            await asyncio.sleep(0.1)
    
    except WebSocketDisconnect:
        logger.info("Logs stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Logs stream error: {e}")
        await websocket.close()


@router.websocket("/status")
async def websocket_status_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time status updates.
    
    Streams agent status changes as JSON messages.
    """
    await websocket.accept()
    logger.info("Status stream WebSocket connected")
    
    try:
        from backend.services import get_orchestrator
        
        while True:
            # Get real status from orchestrator
            try:
                orchestrator = get_orchestrator()
                status = orchestrator.get_status()
                
                # Send status update
                await websocket.send_json({
                    "type": "status",
                    "status": status.get("status", "idle"),
                    "mode": status.get("mode", "idle"),
                    "current_step": status.get("current_step", 0),
                    "total_steps": status.get("total_steps", 0),
                    "progress_percentage": status.get("progress_percentage", 0),
                    "waiting_for_hitl": status.get("waiting_for_hitl", False)
                })
            except Exception:
                # Fallback to idle status
                await websocket.send_json({
                    "type": "status",
                    "status": "idle",
                    "mode": "idle",
                    "current_step": 0,
                    "total_steps": 0,
                    "progress_percentage": 0
                })
            
            await asyncio.sleep(2)
    
    except WebSocketDisconnect:
        logger.info("Status stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Status stream error: {e}")
        await websocket.close()


# Setup logging on module import
setup_websocket_logging()