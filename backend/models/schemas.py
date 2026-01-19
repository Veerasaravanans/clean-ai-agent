"""
schemas.py - Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from .enums import AgentStatus, AgentMode


# ═══════════════════════════════════════════════════════════
# Request Schemas
# ═══════════════════════════════════════════════════════════

class RunTestRequest(BaseModel):
    """Request to run test case(s)."""
    test_ids: List[str] = Field(..., description="List of test case IDs")
    use_learned: bool = Field(default=True, description="Use learned solutions")
    max_retries: int = Field(default=3, description="Max retry attempts")
    verify_each_step: bool = Field(default=True, description="Verify each step")


class ExecuteCommandRequest(BaseModel):
    """Request to execute standalone command."""
    command: str = Field(..., description="Natural language command")
    timeout: int = Field(default=30, description="Timeout in seconds")
    verify: bool = Field(default=True, description="Verify execution")


class SendGuidanceRequest(BaseModel):
    """Request to send HITL guidance."""
    guidance: str = Field(default="", description="Human guidance text")
    action_type: Optional[str] = Field(default=None, description="Action type")
    coordinates: Optional[List[int]] = Field(default=None, description="Tap coordinates [x, y]")
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        """Validate coordinates format."""
        if v is not None and len(v) != 2:
            raise ValueError('coordinates must be [x, y]')
        return tuple(v) if v else None


class TapRequest(BaseModel):
    """Request to execute manual tap."""
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")


class SwipeRequest(BaseModel):
    """Request to execute manual swipe."""
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration_ms: int = Field(default=300, description="Swipe duration")


class InputTextRequest(BaseModel):
    """Request to input text."""
    text: str = Field(..., description="Text to input")


class StopRequest(BaseModel):
    """Request to stop execution."""
    force: bool = Field(default=False, description="Force stop immediately")


# ═══════════════════════════════════════════════════════════
# Response Schemas
# ═══════════════════════════════════════════════════════════

class BaseResponse(BaseModel):
    """Base response model."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class RunTestsResponse(BaseModel):
    """Response for test execution request."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "test_id": "",
            "status": "",
            "steps_completed": 0,
            "total_steps": 0,
            "errors": []
        }
    )


class ExecuteCommandResponse(BaseModel):
    """Response for command execution."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "command": "",
            "status": "",
            "execution_log": []
        }
    )
    error: Optional[str] = None


class SendGuidanceResponse(BaseModel):
    """Response for HITL guidance."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "guidance": "",
            "coordinates": None,
            "action_type": None
        }
    )
    error: Optional[str] = None


class ExecutionStartResponse(BaseModel):
    """Response when execution starts."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "execution_id": "",
            "test_ids": [],
            "status": "running"
        }
    )


class StopResponse(BaseModel):
    """Response when execution stops."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "stopped_at": "",
            "completed_steps": 0,
            "total_steps": 0,
            "status": "stopped"
        }
    )


class StatusResponse(BaseModel):
    """Current agent status response."""
    success: bool
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "status": "idle",
            "mode": "idle",
            "current_test_id": None,
            "current_step": 0,
            "total_steps": 0,
            "progress_percentage": 0,
            "waiting_for_hitl": False,
            "hitl_problem": None,
            "last_action": None,
            "device": None
        }
    )


class DeviceResponse(BaseModel):
    """Device information response."""
    success: bool
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "connected": False,
            "serial": "",
            "model": "",
            "android_version": "",
            "resolution": {"width": 0, "height": 0}
        }
    )


class StatisticsResponse(BaseModel):
    """System statistics response."""
    success: bool
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "uptime_seconds": 0,
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "commands_executed": 0,
            "hitl_requests": 0,
            "learned_solutions": 0
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Health status")
    version: str = Field(default="1.0.0", description="Application version")
    uptime: int = Field(default=0, description="Uptime in seconds")
    checks: Dict[str, bool] = Field(
        default_factory=lambda: {
            "database": True,
            "device": False,
            "llm": False
        }
    )


# ═══════════════════════════════════════════════════════════
# WebSocket Message Schemas
# ═══════════════════════════════════════════════════════════

class WSLogMessage(BaseModel):
    """WebSocket log message."""
    type: str = "log"
    level: str
    message: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class WSStatusMessage(BaseModel):
    """WebSocket status update message."""
    type: str = "status"
    status: str
    mode: str
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0


class WSHITLMessage(BaseModel):
    """WebSocket HITL request message."""
    type: str = "hitl_request"
    problem: str
    screenshot_path: Optional[str] = None
    attempts: int = 0


class WSScreenMessage(BaseModel):
    """WebSocket screen frame message (metadata only, image as binary)."""
    type: str = "screen"
    timestamp: str
    width: int
    height: int


# ═══════════════════════════════════════════════════════════
# RAG-Related Schemas
# ═══════════════════════════════════════════════════════════

class IndexTestCasesRequest(BaseModel):
    """Request to index test cases from Excel."""
    excel_path: str = Field(..., description="Path to Excel file")
    overwrite: bool = Field(default=False, description="Overwrite existing test cases")


class IndexTestCasesResponse(BaseModel):
    """Response for test case indexing."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "added": 0,
            "skipped": 0,
            "errors": 0,
            "files": 0
        }
    )


class SearchTestsRequest(BaseModel):
    """Request to search for test cases."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    min_similarity: float = Field(default=0.5, description="Minimum similarity threshold")


class SearchTestsResponse(BaseModel):
    """Response for test case search."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "query": "",
            "results": [],
            "count": 0
        }
    )


class LearnedSolutionResponse(BaseModel):
    """Response for learned solution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Learned solution data"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Learned solution found",
                "data": {
                    "test_id": "NAID-24430",
                    "title": "HVAC: Fan Speed",
                    "success_rate": 0.8,
                    "execution_count": 5,
                    "steps": [
                        {"step": 1, "action": "tap", "coordinates": [700, 400]},
                        {"step": 2, "action": "verify", "element": "HVAC Screen"}
                    ]
                }
            }
        }


class RAGStatsResponse(BaseModel):
    """Response for RAG statistics."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "test_cases_count": 0,
            "learned_solutions_count": 0,
            "embedding_model": "",
            "db_path": ""
        }
    )