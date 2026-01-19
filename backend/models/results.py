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