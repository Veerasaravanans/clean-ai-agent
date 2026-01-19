"""
verification_engine.py - Enhanced Verification Engine

Provides comprehensive verification capabilities for test execution.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification status."""
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Verification result."""
    verified: bool
    status: VerificationStatus
    confidence: float = 0.0
    details: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class VerificationEngine:
    """Enhanced verification engine."""
    
    def __init__(self):
        """Initialize verification engine."""
        # Lazy load tools
        self._verification_tool = None
        self._vision_tool = None
        self._screenshot_tool = None
        
        logger.info("VerificationEngine initialized")
    
    @property
    def verification_tool(self):
        """Lazy load verification tool."""
        if self._verification_tool is None:
            from backend.tools import toolkit
            self._verification_tool = toolkit.verification
        return self._verification_tool
    
    @property
    def vision_tool(self):
        """Lazy load vision tool."""
        if self._vision_tool is None:
            from backend.tools import toolkit
            self._vision_tool = toolkit.vision
        return self._vision_tool
    
    @property
    def screenshot_tool(self):
        """Lazy load screenshot tool."""
        if self._screenshot_tool is None:
            from backend.tools import toolkit
            self._screenshot_tool = toolkit.screenshot
        return self._screenshot_tool
    
    # ═══════════════════════════════════════════════════════════════
    # Screen Comparison
    # ═══════════════════════════════════════════════════════════════
    
    def compare_screens(
        self,
        before_path: str,
        after_path: str,
        threshold: float = 1.0
    ) -> VerificationResult:
        """
        Compare two screenshots.
        
        Args:
            before_path: Path to before screenshot
            after_path: Path to after screenshot
            threshold: Change threshold percentage
            
        Returns:
            VerificationResult
        """
        try:
            result = self.verification_tool.compare_screens(before_path, after_path)
            
            changed = result.change_percentage >= threshold
            
            return VerificationResult(
                verified=changed,
                status=VerificationStatus.VERIFIED if changed else VerificationStatus.NOT_FOUND,
                confidence=min(result.change_percentage / 100.0, 1.0),
                details=f"Screen changed: {result.change_percentage:.2f}%",
                metrics={
                    "change_percentage": result.change_percentage,
                    "different_pixels": result.different_pixels,
                    "total_pixels": result.total_pixels,
                    "threshold": threshold
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Screen comparison error: {e}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.ERROR,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Element Verification
    # ═══════════════════════════════════════════════════════════════
    
    def verify_element_exists(
        self,
        element_text: str,
        screenshot_path: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify element exists on screen.
        
        Args:
            element_text: Text to find
            screenshot_path: Screenshot path (captures new if None)
            
        Returns:
            VerificationResult
        """
        try:
            # Capture screenshot if not provided
            if screenshot_path is None:
                screenshot_path = self.screenshot_tool.capture()
                if not screenshot_path:
                    return VerificationResult(
                        verified=False,
                        status=VerificationStatus.ERROR,
                        error="Failed to capture screenshot"
                    )
            
            # Use OCR to find text
            elements = self.vision_tool.get_all_text(screenshot_path)
            
            if not elements:
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.NOT_FOUND,
                    details="No text elements detected"
                )
            
            # Search for element
            found = False
            best_match = None
            best_confidence = 0.0
            
            for elem in elements:
                if element_text.lower() in elem.text.lower():
                    found = True
                    if elem.confidence > best_confidence:
                        best_confidence = elem.confidence
                        best_match = elem
            
            if found and best_match:
                return VerificationResult(
                    verified=True,
                    status=VerificationStatus.VERIFIED,
                    confidence=best_confidence / 100.0,
                    details=f"Found '{best_match.text}' at ({best_match.x}, {best_match.y})",
                    metrics={
                        "text": best_match.text,
                        "x": best_match.x,
                        "y": best_match.y,
                        "confidence": best_confidence
                    }
                )
            else:
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.NOT_FOUND,
                    details=f"Text '{element_text}' not found in {len(elements)} elements"
                )
            
        except Exception as e:
            logger.error(f"❌ Element verification error: {e}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.ERROR,
                error=str(e)
            )
    
    def verify_element_at_position(
        self,
        x: int,
        y: int,
        screenshot_path: Optional[str] = None,
        tolerance: int = 50
    ) -> VerificationResult:
        """
        Verify element exists at specific position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            screenshot_path: Screenshot path
            tolerance: Position tolerance in pixels
            
        Returns:
            VerificationResult
        """
        try:
            if screenshot_path is None:
                screenshot_path = self.screenshot_tool.capture()
                if not screenshot_path:
                    return VerificationResult(
                        verified=False,
                        status=VerificationStatus.ERROR,
                        error="Failed to capture screenshot"
                    )
            
            elements = self.vision_tool.get_all_text(screenshot_path)
            
            if not elements:
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.NOT_FOUND,
                    details="No elements detected"
                )
            
            # Find elements near position
            for elem in elements:
                dx = abs(elem.x - x)
                dy = abs(elem.y - y)
                
                if dx <= tolerance and dy <= tolerance:
                    return VerificationResult(
                        verified=True,
                        status=VerificationStatus.VERIFIED,
                        confidence=elem.confidence / 100.0,
                        details=f"Found '{elem.text}' at ({elem.x}, {elem.y})",
                        metrics={
                            "text": elem.text,
                            "x": elem.x,
                            "y": elem.y,
                            "distance": (dx**2 + dy**2)**0.5,
                            "tolerance": tolerance
                        }
                    )
            
            return VerificationResult(
                verified=False,
                status=VerificationStatus.NOT_FOUND,
                details=f"No element found near ({x}, {y}) within {tolerance}px"
            )
            
        except Exception as e:
            logger.error(f"❌ Position verification error: {e}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.ERROR,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Image Verification
    # ═══════════════════════════════════════════════════════════════
    
    def verify_image_match(
        self,
        reference_path: str,
        current_path: Optional[str] = None,
        threshold: float = 0.9
    ) -> VerificationResult:
        """
        Verify current screen matches reference image.
        
        Args:
            reference_path: Reference image path
            current_path: Current screenshot (captures if None)
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            VerificationResult
        """
        try:
            if current_path is None:
                current_path = self.screenshot_tool.capture()
                if not current_path:
                    return VerificationResult(
                        verified=False,
                        status=VerificationStatus.ERROR,
                        error="Failed to capture screenshot"
                    )
            
            result = self.verification_tool.verify_screen_match(reference_path, current_path)
            
            similarity = 1.0 - (result.change_percentage / 100.0)
            matches = similarity >= threshold
            
            return VerificationResult(
                verified=matches,
                status=VerificationStatus.VERIFIED if matches else VerificationStatus.NOT_FOUND,
                confidence=similarity,
                details=f"Similarity: {similarity:.2%} (threshold: {threshold:.2%})",
                metrics={
                    "similarity": similarity,
                    "change_percentage": result.change_percentage,
                    "threshold": threshold,
                    "matches": matches
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Image match error: {e}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.ERROR,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # State Verification
    # ═══════════════════════════════════════════════════════════════
    
    def verify_state(
        self,
        expected_elements: List[str],
        screenshot_path: Optional[str] = None,
        require_all: bool = False
    ) -> VerificationResult:
        """
        Verify screen state contains expected elements.
        
        Args:
            expected_elements: List of expected text elements
            screenshot_path: Screenshot path
            require_all: If True, all elements must be present
            
        Returns:
            VerificationResult
        """
        try:
            if screenshot_path is None:
                screenshot_path = self.screenshot_tool.capture()
                if not screenshot_path:
                    return VerificationResult(
                        verified=False,
                        status=VerificationStatus.ERROR,
                        error="Failed to capture screenshot"
                    )
            
            elements = self.vision_tool.get_all_text(screenshot_path)
            
            if not elements:
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.NOT_FOUND,
                    details="No elements detected"
                )
            
            # Extract all text
            detected_text = [elem.text.lower() for elem in elements]
            
            # Check each expected element
            found_elements = []
            missing_elements = []
            
            for expected in expected_elements:
                found = any(expected.lower() in text for text in detected_text)
                if found:
                    found_elements.append(expected)
                else:
                    missing_elements.append(expected)
            
            # Determine result
            if require_all:
                verified = len(missing_elements) == 0
                status = VerificationStatus.VERIFIED if verified else VerificationStatus.NOT_FOUND
            else:
                verified = len(found_elements) > 0
                if len(found_elements) == len(expected_elements):
                    status = VerificationStatus.VERIFIED
                elif len(found_elements) > 0:
                    status = VerificationStatus.PARTIAL
                else:
                    status = VerificationStatus.NOT_FOUND
            
            return VerificationResult(
                verified=verified,
                status=status,
                confidence=len(found_elements) / len(expected_elements),
                details=f"Found {len(found_elements)}/{len(expected_elements)} elements",
                metrics={
                    "expected": expected_elements,
                    "found": found_elements,
                    "missing": missing_elements,
                    "require_all": require_all
                }
            )
            
        except Exception as e:
            logger.error(f"❌ State verification error: {e}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.ERROR,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get verification performance metrics."""
        return {
            "ocr_available": self.vision_tool is not None,
            "screenshot_available": self.screenshot_tool is not None,
            "verification_available": self.verification_tool is not None
        }