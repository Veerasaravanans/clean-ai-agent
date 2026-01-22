"""
execution_control.py - Execution Control Service

Provides thread-safe stop and pause control for the agent workflow.
Uses threading events that can be checked by nodes during execution.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionControl:
    """
    Thread-safe execution control using threading events.

    This allows the orchestrator to signal stop/pause to running nodes
    even when the graph is executing in a separate thread.
    """

    def __init__(self):
        """Initialize execution control."""
        # Stop event - when set, execution should terminate immediately
        self._stop_event = threading.Event()

        # Pause event - when set, execution is paused
        # When clear, execution is running
        self._pause_event = threading.Event()

        # Lock for thread-safe operations
        self._lock = threading.Lock()

        # Track if execution is active
        self._execution_active = False

        logger.info("ExecutionControl initialized")

    def start_execution(self):
        """Called when a new execution starts."""
        with self._lock:
            self._stop_event.clear()
            self._pause_event.clear()
            self._execution_active = True
            logger.info("Execution started - control flags reset")

    def stop_execution(self):
        """
        Signal to stop execution immediately.

        Sets the stop event which nodes should check.
        """
        with self._lock:
            self._stop_event.set()
            # Also clear pause so we don't hang
            self._pause_event.clear()
            self._execution_active = False
            logger.info("STOP signal sent")

    def pause_execution(self):
        """
        Signal to pause execution.

        Sets the pause event which nodes should check and wait on.
        """
        with self._lock:
            if self._execution_active and not self._stop_event.is_set():
                self._pause_event.set()
                logger.info("PAUSE signal sent")
                return True
            return False

    def resume_execution(self):
        """
        Signal to resume execution after pause.

        Clears the pause event allowing nodes to continue.
        """
        with self._lock:
            self._pause_event.clear()
            logger.info("RESUME signal sent")

    def end_execution(self):
        """Called when execution completes normally."""
        with self._lock:
            self._stop_event.clear()
            self._pause_event.clear()
            self._execution_active = False
            logger.info("Execution ended - control flags cleared")

    def is_stop_requested(self) -> bool:
        """Check if stop has been requested."""
        return self._stop_event.is_set()

    def is_paused(self) -> bool:
        """Check if execution is paused."""
        return self._pause_event.is_set()

    def is_active(self) -> bool:
        """Check if execution is active."""
        with self._lock:
            return self._execution_active

    def wait_if_paused(self, timeout: float = 0.5) -> bool:
        """
        Wait while paused, checking periodically for stop.

        Args:
            timeout: Check interval in seconds

        Returns:
            True if should continue, False if stop requested
        """
        while self._pause_event.is_set():
            # Check for stop while paused
            if self._stop_event.is_set():
                logger.info("Stop requested while paused")
                return False

            # Wait a bit before checking again
            self._pause_event.wait(timeout)

            # If still paused, continue waiting
            if not self._pause_event.is_set():
                logger.info("Resumed from pause")
                break

        return not self._stop_event.is_set()

    def check_and_wait(self) -> bool:
        """
        Check control flags and wait if paused.

        This is the main method nodes should call before each action.

        Returns:
            True if execution should continue, False if should stop
        """
        # Check stop first
        if self._stop_event.is_set():
            logger.debug("Stop flag detected")
            return False

        # If paused, wait for resume or stop
        if self._pause_event.is_set():
            logger.info("Execution paused, waiting for resume...")
            return self.wait_if_paused()

        return True

    def get_status(self) -> dict:
        """Get current control status."""
        return {
            "active": self._execution_active,
            "stopped": self._stop_event.is_set(),
            "paused": self._pause_event.is_set()
        }


# ═══════════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════════

_control_instance: Optional[ExecutionControl] = None


def get_execution_control() -> ExecutionControl:
    """
    Get singleton ExecutionControl instance.

    Returns:
        ExecutionControl instance
    """
    global _control_instance

    if _control_instance is None:
        _control_instance = ExecutionControl()

    return _control_instance
