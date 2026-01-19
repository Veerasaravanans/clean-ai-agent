"""
toolkit.py - Unified Tool Interface

Single interface for all agent tools.
"""

import logging
from typing import Optional
from functools import lru_cache

from .adb_tool import ADBTool
from .screenshot_tool import ScreenshotTool
from .vision_tool import VisionTool
from .verification_tool import VerificationTool
from .rag_tool import RAGTool

logger = logging.getLogger(__name__)


class AgentToolkit:
    """
    Unified interface for all agent tools.
    
    Provides single access point for:
    - ADB commands
    - Screenshot capture
    - OCR and Vision
    - Verification
    - RAG and learned solutions
    """
    
    def __init__(self, device_serial: Optional[str] = None):
        """
        Initialize all tools.
        
        Args:
            device_serial: Device serial number
        """
        logger.info("Initializing Agent Toolkit...")
        
        self.adb = ADBTool(device_serial)
        self.screenshot = ScreenshotTool(device_serial)
        self.vision = VisionTool()
        self.verification = VerificationTool()
        self.rag = RAGTool()
        
        logger.info("✅ Agent Toolkit initialized")
    
    # ═══════════════════════════════════════════════════════════
    # ADB Actions (Direct Access)
    # ═══════════════════════════════════════════════════════════
    
    def tap(self, x: int, y: int):
        """Execute tap action."""
        return self.adb.tap(x, y)
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Execute swipe action."""
        return self.adb.swipe(x1, y1, x2, y2, duration_ms)
    
    def input_text(self, text: str):
        """Input text."""
        return self.adb.input_text(text)
    
    def press_back(self):
        """Press back button."""
        return self.adb.press_back()
    
    def press_home(self):
        """Press home button."""
        return self.adb.press_home()
    
    # ═══════════════════════════════════════════════════════════
    # Screenshot Actions
    # ═══════════════════════════════════════════════════════════
    
    def capture_screenshot(self, filename: Optional[str] = None):
        """Capture screenshot."""
        return self.screenshot.capture(filename)
    
    def get_screen_dimensions(self):
        """Get screen dimensions."""
        return self.screenshot.get_dimensions()
    
    # ═══════════════════════════════════════════════════════════
    # Vision Actions
    # ═══════════════════════════════════════════════════════════
    
    def find_text(self, screenshot_path: str, target_text: str):
        """Find text on screen."""
        return self.vision.find_text(screenshot_path, target_text)
    
    def find_element(self, screenshot_path: str, description: str):
        """Find element using AI vision."""
        return self.vision.find_element_with_ai(screenshot_path, description)
    
    def analyze_screen(self, screenshot_path: str, question: str = ""):
        """Analyze screen with AI."""
        return self.vision.analyze_screen_with_ai(screenshot_path, question)
    
    # ═══════════════════════════════════════════════════════════
    # Verification Actions
    # ═══════════════════════════════════════════════════════════
    
    def compare_screens(self, before_path: str, after_path: str):
        """Compare two screenshots."""
        return self.verification.compare_screens(before_path, after_path)
    
    def verify_element_exists(self, screenshot_path: str, element_text: str):
        """Verify element exists."""
        return self.verification.verify_element_exists(screenshot_path, element_text)
    
    # ═══════════════════════════════════════════════════════════
    # RAG Actions
    # ═══════════════════════════════════════════════════════════
    
    def get_test_case(self, test_id: str):
        """Get test case description."""
        return self.rag.get_test_description(test_id)
    
    def get_learned_solution(self, test_id: str):
        """Check for learned solution."""
        return self.rag.get_learned_solution(test_id)
    
    def save_learned_solution(self, test_id: str, title: str, component: str, steps: list):
        """Save successful execution as learned solution."""
        return self.rag.save_learned_solution(test_id, title, component, steps)
    
    # ═══════════════════════════════════════════════════════════
    # Device Info
    # ═══════════════════════════════════════════════════════════
    
    def get_device_info(self):
        """Get device information."""
        return self.adb.get_device_info()
    
    def is_device_connected(self):
        """Check if device is connected."""
        return self.adb.is_connected()


@lru_cache()
def get_toolkit(device_serial: Optional[str] = None) -> AgentToolkit:
    """
    Get cached toolkit instance (Singleton pattern).
    
    Args:
        device_serial: Device serial number
        
    Returns:
        AgentToolkit instance
    """
    return AgentToolkit(device_serial)


# Global toolkit instance
toolkit = get_toolkit()