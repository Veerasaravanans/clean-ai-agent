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

    # Messages to filter out (spam/noise) - these are initialization/internal messages
    FILTERED_PATTERNS = [
        'Detected screen:',
        'ADB Tool initialized',
        'Screen detection failed',
        'wm size',
        'Screenshot Tool initialized',
        'Device Coordinate Tool initialized',
        'Verification Tool initialized',
        'Vision Tool initialized',
        'Agent Toolkit initialized',
        'Initializing Agent Toolkit',
        'Texted Icon Detection Tool initialized',
        'NonTextedIconDetectionTool initialized',
        'EasyOCR initialized',
        'PaddleOCR initialized',
        'RAG system initialized',
        'RAG already initialized',
        'Initializing RAG system',
    ]

    # Track recent messages to deduplicate
    _recent_messages = {}
    _dedup_window_seconds = 5  # Don't repeat same message within 5 seconds
    _dedup_window_short = 1  # Shorter window for step-specific messages (1 second)

    def emit(self, record):
        try:
            message = self.format(record)

            # Filter out noisy/spammy messages
            for pattern in self.FILTERED_PATTERNS:
                if pattern in message:
                    return  # Skip this message

            # CRITICAL FIX: Extract step context for step-specific messages
            # This prevents deduplication from blocking same messages from different steps
            step_context = None
            step_indicators = [
                "Direct execute step",
                "⚡ Direct execute step",
                "Moving to next step:",
                "➡️ Moving to next step:",
                "Next step:",
                "📝 Next step:",
                "Step",  # General step references
            ]

            for indicator in step_indicators:
                if indicator in message:
                    # Try to extract step number from message
                    import re
                    # Patterns: "step 0", "step: 1/3", "step 2:", etc.
                    match = re.search(r'[Ss]tep[\s:]+(\d+)', message)
                    if match:
                        step_context = match.group(1)
                        break

            # Deduplicate repeated messages with step-aware key
            # Include step context in key to allow same message for different steps
            if step_context:
                msg_key = f"{record.name}:{step_context}:{message}"
                dedup_window = self._dedup_window_short  # Use shorter window (1s) for step messages
            else:
                msg_key = f"{record.name}:{message}"
                dedup_window = self._dedup_window_seconds  # Use normal window (5s)

            current_time = datetime.now().timestamp()
            if msg_key in self._recent_messages:
                last_time = self._recent_messages[msg_key]
                if current_time - last_time < dedup_window:
                    return  # Skip duplicate within time window
            self._recent_messages[msg_key] = current_time

            # Clean old entries from dedup cache (keep last 100)
            if len(self._recent_messages) > 100:
                sorted_keys = sorted(self._recent_messages.keys(),
                                   key=lambda k: self._recent_messages[k])
                for old_key in sorted_keys[:50]:
                    del self._recent_messages[old_key]

            # Format log entry
            log_entry = {
                "type": "log",
                "level": record.levelname.lower(),
                "message": message,
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
                statistics = orchestrator.get_statistics()

                # Send status update including statistics
                await websocket.send_json({
                    "type": "status",
                    "status": status.get("status", "idle"),
                    "mode": status.get("mode", "idle"),
                    "current_step": status.get("current_step", 0),
                    "total_steps": status.get("total_steps", 0),
                    "progress_percentage": status.get("progress_percentage", 0),
                    "waiting_for_hitl": status.get("waiting_for_hitl", False),
                    "tests_executed": statistics.get("tests_executed", 0),
                    "tests_passed": statistics.get("tests_passed", 0),
                    "tests_failed": statistics.get("tests_failed", 0)
                })
            except Exception:
                # Fallback to idle status
                await websocket.send_json({
                    "type": "status",
                    "status": "idle",
                    "mode": "idle",
                    "current_step": 0,
                    "total_steps": 0,
                    "progress_percentage": 0,
                    "tests_executed": 0,
                    "tests_passed": 0,
                    "tests_failed": 0
                })

            await asyncio.sleep(2)
    
    except WebSocketDisconnect:
        logger.info("Status stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Status stream error: {e}")
        await websocket.close()


# Setup logging on module import
setup_websocket_logging()