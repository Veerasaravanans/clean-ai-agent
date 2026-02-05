"""
results.py - Data classes for execution results
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Coordinates:
    """Screen coordinates with metadata."""
    x: int
    y: int
    confidence: int = 100
    source: str = "unknown"
    width: Optional[int] = None
    height: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "source": self.source,
            "width": self.width,
            "height": self.height
        }
    
    def to_tuple(self) -> tuple:
        return (self.x, self.y)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Coordinates":
        return cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            confidence=data.get("confidence", 100),
            source=data.get("source", "unknown"),
            width=data.get("width"),
            height=data.get("height")
        )


@dataclass
class ActionResult:
    """Result of an ADB action execution."""
    success: bool
    error: Optional[str] = None
    output: Optional[str] = None
    duration_ms: Optional[int] = None
    action_type: Optional[str] = None
    coordinates: Optional[tuple] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "error": self.error,
            "output": self.output,
            "duration_ms": self.duration_ms,
            "action_type": self.action_type,
            "coordinates": self.coordinates,
            "timestamp": self.timestamp
        }


@dataclass
class ChangeResult:
    """Result of screen change detection."""
    changed: bool
    change_percentage: float
    details: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "changed": self.changed,
            "change_percentage": self.change_percentage,
            "details": self.details
        }


@dataclass
class TextElement:
    """Detected text element on screen."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: int
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence
        }


@dataclass
class ScreenAnalysis:
    """AI analysis of screen content."""
    summary: str
    detected_elements: List[Dict] = field(default_factory=list)
    screen_state: str = ""
    confidence: int = 0
    
    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "detected_elements": self.detected_elements,
            "screen_state": self.screen_state,
            "confidence": self.confidence
        }


@dataclass
class LogEntry:
    """Execution log entry."""
    level: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class DeviceInfo:
    """Android device information."""
    serial: str
    model: str
    android_version: str
    resolution: tuple
    connected: bool = True
    
    def to_dict(self) -> dict:
        return {
            "serial": self.serial,
            "model": self.model,
            "android_version": self.android_version,
            "resolution": {"width": self.resolution[0], "height": self.resolution[1]},
            "connected": self.connected
        }


# ═══════════════════════════════════════════════════════════
# Pydantic Models for API Responses
# ═══════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from backend.models.enums import TestResult


class TestExecutionResult(BaseModel):
    """Test execution result model."""
    test_id: str = Field(..., description="Test case ID")
    result: TestResult = Field(..., description="Test result")
    duration: float = Field(..., description="Execution duration in seconds")
    steps_executed: int = Field(default=0, description="Number of steps executed")
    steps_passed: int = Field(default=0, description="Number of steps passed")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    screenshots: List[str] = Field(default_factory=list, description="Screenshot paths")
    started_at: Optional[str] = Field(default=None, description="Start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "NAID-24430",
                "result": "passed",
                "duration": 5.2,
                "steps_executed": 3,
                "steps_passed": 3,
                "errors": [],
                "screenshots": ["shot1.png", "shot2.png"],
                "started_at": "2025-12-28T10:00:00",
                "completed_at": "2025-12-28T10:00:05"
            }
        }


class StepExecutionResult(BaseModel):
    """Individual step execution result."""
    step_number: int = Field(..., description="Step number")
    description: str = Field(..., description="Step description")
    result: TestResult = Field(..., description="Step result")
    duration: float = Field(default=0.0, description="Step duration")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    screenshot: Optional[str] = Field(default=None, description="Screenshot path")

    class Config:
        json_schema_extra = {
            "example": {
                "step_number": 1,
                "description": "Tap Settings icon",
                "result": "passed",
                "duration": 1.5,
                "error": None,
                "screenshot": "step1.png"
            }
        }


# ═══════════════════════════════════════════════════════════
# Dynamic Verification System Data Classes
# ═══════════════════════════════════════════════════════════

from backend.models.enums import VerificationType


@dataclass
class CropRegion:
    """
    Defines a rectangular region for partial image verification.
    Coordinates are in device pixels.
    """
    name: str  # Region identifier (e.g., "navigation_bar")
    x1: int    # Left edge
    y1: int    # Top edge
    x2: int    # Right edge
    y2: int    # Bottom edge

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CropRegion":
        return cls(
            name=data.get("name", "region"),
            x1=data.get("x1", 0),
            y1=data.get("y1", 0),
            x2=data.get("x2", 0),
            y2=data.get("y2", 0)
        )

    @classmethod
    def from_string(cls, name: str, coords_str: str) -> "CropRegion":
        """
        Parse crop region from string format: "x1,y1,x2,y2"

        Args:
            name: Region name
            coords_str: Coordinates as "x1,y1,x2,y2"

        Returns:
            CropRegion instance
        """
        try:
            parts = [int(p.strip()) for p in coords_str.split(",")]
            if len(parts) == 4:
                return cls(name=name, x1=parts[0], y1=parts[1], x2=parts[2], y2=parts[3])
        except (ValueError, IndexError):
            pass
        # Return default region on parse error
        return cls(name=name, x1=0, y1=0, x2=0, y2=0)

    def is_valid(self) -> bool:
        """Check if region coordinates are valid."""
        return self.x2 > self.x1 and self.y2 > self.y1

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


@dataclass
class StepVerificationConfig:
    """
    Verification configuration for a single test step.
    Parsed from Excel "Verification Type" and "What Needs to Be Verified" columns.
    """
    verification_type: VerificationType = VerificationType.IMAGE

    # For OCR verification: list of texts that must ALL be present
    expected_texts: List[str] = field(default_factory=list)

    # For partial image verification: list of crop regions
    crop_regions: List[CropRegion] = field(default_factory=list)

    # For full/partial image: reference image name override (optional)
    reference_image_name: Optional[str] = None

    # SSIM threshold override (optional)
    ssim_threshold: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "verification_type": self.verification_type.value,
            "expected_texts": self.expected_texts,
            "crop_regions": [r.to_dict() for r in self.crop_regions],
            "reference_image_name": self.reference_image_name,
            "ssim_threshold": self.ssim_threshold
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StepVerificationConfig":
        return cls(
            verification_type=VerificationType(data.get("verification_type", "image_verification")),
            expected_texts=data.get("expected_texts", []),
            crop_regions=[CropRegion.from_dict(r) for r in data.get("crop_regions", [])],
            reference_image_name=data.get("reference_image_name"),
            ssim_threshold=data.get("ssim_threshold")
        )

    @classmethod
    def default(cls) -> "StepVerificationConfig":
        """Return default config (full image verification)."""
        return cls(verification_type=VerificationType.IMAGE)


@dataclass
class OCRVerificationResult:
    """
    Result of OCR-based text verification.
    """
    passed: bool
    expected_texts: List[str]
    found_texts: List[str]
    missing_texts: List[str]
    all_detected_text: str  # Full OCR output for debugging
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "expected_texts": self.expected_texts,
            "found_texts": self.found_texts,
            "missing_texts": self.missing_texts,
            "all_detected_text": self.all_detected_text[:500],  # Truncate for storage
            "confidence": self.confidence
        }


@dataclass
class PartialImageVerificationResult:
    """
    Result of partial (cropped) image verification.
    """
    passed: bool
    regions_results: List[Dict[str, Any]]  # Per-region results
    overall_ssim: float
    failed_regions: List[str]  # Names of regions that failed
    comparison_image: Optional[str] = None  # Path to comparison image

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "regions_results": self.regions_results,
            "overall_ssim": self.overall_ssim,
            "failed_regions": self.failed_regions,
            "comparison_image": self.comparison_image
        }


@dataclass
class DynamicVerificationResult:
    """
    Unified result from dynamic verification system.
    Contains results regardless of verification type used.
    """
    passed: bool
    verification_type: VerificationType
    message: str

    # Type-specific details (only one will be populated)
    ssim_result: Optional[Dict[str, Any]] = None
    ocr_result: Optional[OCRVerificationResult] = None
    partial_result: Optional[PartialImageVerificationResult] = None

    # Common metadata
    screenshot_path: Optional[str] = None
    comparison_image_path: Optional[str] = None
    result_id: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "passed": self.passed,
            "verification_type": self.verification_type.value,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
            "comparison_image_path": self.comparison_image_path,
            "result_id": self.result_id
        }

        if self.ssim_result:
            result["ssim_result"] = self.ssim_result
        if self.ocr_result:
            result["ocr_result"] = self.ocr_result.to_dict()
        if self.partial_result:
            result["partial_result"] = self.partial_result.to_dict()

        return result