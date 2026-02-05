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


class VerificationType(str, Enum):
    """
    Types of verification methods for test steps.
    Determined by "Verification Type" column in Excel.
    """
    IMAGE = "image_verification"  # Full screen SSIM comparison (default)
    OCR = "ocr"  # OCR text-only verification
    PARTIAL_IMAGE = "partial_image"  # Cropped region SSIM comparison
    NONE = "no_verification"  # Skip verification for this step

    @classmethod
    def from_excel_value(cls, value: str) -> "VerificationType":
        """
        Convert Excel column value to VerificationType.

        Supported values:
        - Full Image / Image: Compare full screenshot with reference image
        - Partial Image / Cropped: Compare cropped region(s) with reference
        - None / Skip: No verification for this step
        - OCR / Text: Verify text is visible on screen

        Args:
            value: Raw Excel cell value

        Returns:
            VerificationType enum value
        """
        if not value:
            return cls.IMAGE  # Default to full image verification

        value_lower = value.lower().strip()

        # Map Excel values to enum (order matters - check more specific first)
        # OCR/Text verification
        if "ocr" in value_lower or value_lower == "text":
            return cls.OCR
        # Partial/Cropped image verification (check before "image" to avoid matching "partial image")
        elif "partial" in value_lower or "cropped" in value_lower or "region" in value_lower:
            return cls.PARTIAL_IMAGE
        # No verification
        elif "no" in value_lower or "skip" in value_lower or "none" in value_lower:
            return cls.NONE
        # Full image verification (explicit or default)
        elif "full" in value_lower or "image" in value_lower:
            return cls.IMAGE
        else:
            # Default: full image verification
            return cls.IMAGE