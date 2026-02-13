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
    ERROR = "error"  # Technical/infrastructure error
    BLOCKED = "blocked"  # Blocked by unresolvable issue


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


class ErrorCategory(str, Enum):
    """
    Categorizes errors to determine appropriate handling.

    TECHNICAL errors (infrastructure/system) → End test with ERROR status
    DECISION errors (AI cannot decide) → Trigger HITL after retries
    """
    # ═══════════════════════════════════════════════════════════
    # Technical Errors (DO NOT trigger HITL - humans cannot fix)
    # ═══════════════════════════════════════════════════════════
    INFRASTRUCTURE = "infrastructure"  # Network, device connection, ADB failures
    SYSTEM = "system"  # System-level errors, process crashes
    CAPTURE = "capture"  # Screenshot capture failures (PNG errors, ADB issues)
    TIMEOUT = "timeout"  # Operation timeouts, device not responding

    # ═══════════════════════════════════════════════════════════
    # Decision Errors (MAY trigger HITL - humans can help)
    # ═══════════════════════════════════════════════════════════
    ELEMENT_NOT_FOUND = "element_not_found"  # Cannot locate UI element
    VERIFICATION_FAILED = "verification_failed"  # Expected result not found
    AMBIGUOUS = "ambiguous"  # Multiple matches, unclear choice
    PLANNING_FAILED = "planning_failed"  # AI cannot determine action

    def is_technical(self) -> bool:
        """Check if this is a technical error (system/infrastructure)."""
        return self in [
            ErrorCategory.INFRASTRUCTURE,
            ErrorCategory.SYSTEM,
            ErrorCategory.CAPTURE,
            ErrorCategory.TIMEOUT
        ]

    def is_decision(self) -> bool:
        """Check if this is a decision error (AI needs help)."""
        return self in [
            ErrorCategory.ELEMENT_NOT_FOUND,
            ErrorCategory.VERIFICATION_FAILED,
            ErrorCategory.AMBIGUOUS,
            ErrorCategory.PLANNING_FAILED
        ]


class CleanupType(str, Enum):
    """
    Types of cleanup operations for post-processing and state restoration.

    Cleanup operations are executed either after each step (in-step) or at the end
    of test execution (end-of-test) based on the cleanup_trigger configuration.
    """
    NONE = "none"  # No cleanup needed
    RETURN_HOME = "return_home"  # Press home button to return to home screen
    REVERSE_ACTION = "reverse_action"  # Reverse the last action(s) performed
    RESTORE_STATE = "restore_state"  # Restore to previous state by reversing N actions
    CLOSE_DIALOG = "close_dialog"  # Close dialog/popup and return home
    REBOOT = "reboot"  # Reboot device (WARNING: destructive)
    FACTORY_RESET = "factory_reset"  # Factory reset device (CRITICAL: erases all data)
    AI_DRIVEN = "ai_driven"  # Let AI decide cleanup strategy
    REVERSE_AND_HOME = "reverse_and_home"  # Reverse action then press home
    CLOSE_AND_REBOOT = "close_and_reboot"  # Close dialog then reboot


class CleanupTrigger(str, Enum):
    """
    Determines when cleanup operations should be executed.

    Cleanup can be triggered at different points in the test lifecycle to
    ensure proper device state management.
    """
    AFTER_STEP = "after_step"  # Execute cleanup after each test step
    END_OF_TEST = "end_of_test"  # Execute cleanup only at end of test (default)
    BOTH = "both"  # Execute cleanup after each step AND at end of test
    ON_FAILURE = "on_failure"  # Execute cleanup only when step/test fails
    ALWAYS = "always"  # Always execute cleanup regardless of success/failure