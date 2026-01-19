"""
enums.py - Enumerations for AI Agent Framework
"""

from enum import Enum


class AgentStatus(str, Enum):
    """Current status of the AI Agent."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_HITL = "waiting_hitl"
    SUCCESS = "success"
    FAILURE = "failure"
    STOPPED = "stopped"


class AgentMode(str, Enum):
    """Operating mode of the agent."""
    IDLE = "idle"
    TEST_EXECUTION = "test_execution"
    STANDALONE = "standalone"


class VerificationStatus(str, Enum):
    """Result of action verification."""
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"
    RETRY = "retry"


class TestResult(str, Enum):
    """Test execution result."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class VerificationEngineStatus(str, Enum):
    """Verification engine result status."""
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


class ActionType(str, Enum):
    """Types of ADB actions."""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    INPUT_TEXT = "input_text"
    PRESS_KEY = "press_key"
    PRESS_BACK = "press_back"
    PRESS_HOME = "press_home"
    VERIFY = "verify"


class LogLevel(str, Enum):
    """Log entry severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    HITL = "hitl"
    DEBUG = "debug"


class OCREngine(str, Enum):
    """Available OCR engines."""
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    TESSERACT = "tesseract"
    AI_VISION = "ai_vision"