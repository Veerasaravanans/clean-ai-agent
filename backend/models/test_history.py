"""
test_history.py - Pydantic models for Test History Dashboard

Models for tracking test execution records, analytics, and history management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """Test execution status."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    STOPPED = "stopped"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════
# Step Execution Record
# ═══════════════════════════════════════════════════════════

class StepRecord(BaseModel):
    """Record of a single test step execution."""
    step_number: int = Field(..., description="Step number (1-based)")
    description: str = Field(default="", description="Step description from test case")
    goal: Optional[str] = Field(default=None, description="Goal/expected outcome of this step")

    # Action details
    action_type: Optional[str] = Field(default=None, description="Action type (tap, swipe, etc.)")
    action_target: Optional[str] = Field(default=None, description="Target element name")
    action_details: Optional[Dict[str, Any]] = Field(default=None, description="Action parameters")

    # Coordinates used
    coordinates_x: Optional[int] = Field(default=None, description="X coordinate used")
    coordinates_y: Optional[int] = Field(default=None, description="Y coordinate used")
    coordinate_source: Optional[str] = Field(default=None, description="Source: learned, device_profile, ai_detection")

    # Execution status
    status: str = Field(default="pending", description="Step status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    duration_ms: Optional[int] = Field(default=None, description="Step execution duration in ms")

    # Verification results
    ssim_score: Optional[float] = Field(default=None, description="SSIM verification score")
    ssim_passed: Optional[bool] = Field(default=None, description="Whether SSIM verification passed")
    ssim_threshold: Optional[float] = Field(default=None, description="SSIM threshold used")
    reference_image_name: Optional[str] = Field(default=None, description="Reference image name used")

    # Screenshot and comparison images
    before_screenshot_path: Optional[str] = Field(default=None, description="Screenshot before action")
    after_screenshot_path: Optional[str] = Field(default=None, description="Screenshot after action")
    screenshot_path: Optional[str] = Field(default=None, description="Alias for after_screenshot_path")
    comparison_image_path: Optional[str] = Field(default=None, description="Side-by-side comparison image")

    # Learned solution info
    used_learned_solution: Optional[bool] = Field(default=None, description="Whether learned solution was used")
    learned_solution_confidence: Optional[float] = Field(default=None, description="Confidence of learned solution")

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════
# Test Execution Record
# ═══════════════════════════════════════════════════════════

class TestExecutionRecord(BaseModel):
    """Complete record of a test execution."""
    execution_id: str = Field(..., description="Unique execution identifier")
    test_id: str = Field(..., description="Test case ID")
    test_title: Optional[str] = Field(default=None, description="Test case title")

    # Execution metadata
    status: ExecutionStatus = Field(default=ExecutionStatus.RUNNING)
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None, description="Total execution duration")

    # Progress tracking
    total_steps: int = Field(default=0)
    completed_steps: int = Field(default=0)
    passed_steps: int = Field(default=0)
    failed_steps: int = Field(default=0)

    # Step details
    steps: List[StepRecord] = Field(default_factory=list)

    # Verification summary
    ssim_verifications: int = Field(default=0, description="Total SSIM verifications")
    ssim_passed: int = Field(default=0, description="Passed SSIM verifications")
    ssim_failed: int = Field(default=0, description="Failed SSIM verifications")
    average_ssim: Optional[float] = Field(default=None, description="Average SSIM score")

    # Configuration used
    use_learned: bool = Field(default=True)
    max_retries: int = Field(default=3)

    # Device info
    device_id: Optional[str] = Field(default=None)
    device_model: Optional[str] = Field(default=None)
    device_resolution: Optional[str] = Field(default=None)

    # Model used
    model_used: Optional[str] = Field(default=None, description="VIO model used")

    # Error tracking
    errors: List[str] = Field(default_factory=list)

    # Additional metadata
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)


# ═══════════════════════════════════════════════════════════
# Analytics Models
# ═══════════════════════════════════════════════════════════

class DailyStats(BaseModel):
    """Statistics for a single day."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    total_executions: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    pass_rate: float = Field(default=0.0)
    average_duration_ms: Optional[float] = Field(default=None)
    average_ssim: Optional[float] = Field(default=None)


class TestCaseStats(BaseModel):
    """Statistics for a specific test case."""
    test_id: str
    test_title: Optional[str] = None
    total_executions: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    pass_rate: float = Field(default=0.0)
    last_execution: Optional[str] = Field(default=None)
    last_status: Optional[str] = Field(default=None)
    average_duration_ms: Optional[float] = Field(default=None)


class TestAnalytics(BaseModel):
    """Overall test analytics data."""
    # Summary stats
    total_executions: int = Field(default=0)
    total_passed: int = Field(default=0)
    total_failed: int = Field(default=0)
    overall_pass_rate: float = Field(default=0.0)

    # Time-based stats
    executions_today: int = Field(default=0)
    executions_this_week: int = Field(default=0)
    executions_this_month: int = Field(default=0)

    # Trends (last 30 days)
    daily_stats: List[DailyStats] = Field(default_factory=list)

    # Top test cases
    most_executed_tests: List[TestCaseStats] = Field(default_factory=list)
    most_failed_tests: List[TestCaseStats] = Field(default_factory=list)

    # SSIM stats
    total_ssim_verifications: int = Field(default=0)
    ssim_pass_rate: float = Field(default=0.0)
    average_ssim_score: Optional[float] = Field(default=None)

    # Duration stats
    average_execution_duration_ms: Optional[float] = Field(default=None)
    fastest_execution_ms: Optional[int] = Field(default=None)
    slowest_execution_ms: Optional[int] = Field(default=None)

    # Recent activity
    last_execution_time: Optional[str] = Field(default=None)

    # Generated timestamp
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class DashboardSummary(BaseModel):
    """Summary data for dashboard display."""
    # Quick stats
    total_executions: int = Field(default=0)
    total_passed: int = Field(default=0)
    total_failed: int = Field(default=0)
    pass_rate: float = Field(default=0.0)

    # Today's stats
    today_executions: int = Field(default=0)
    today_passed: int = Field(default=0)
    today_failed: int = Field(default=0)

    # Recent executions (last 10)
    recent_executions: List[Dict[str, Any]] = Field(default_factory=list)

    # Trend indicator
    trend: str = Field(default="stable", description="up, down, or stable")
    trend_percentage: float = Field(default=0.0)

    # SSIM summary
    ssim_pass_rate: float = Field(default=0.0)

    # Generated timestamp
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════
# API Request/Response Models
# ═══════════════════════════════════════════════════════════

class ExecutionListRequest(BaseModel):
    """Request for listing executions with filters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    test_id: Optional[str] = Field(default=None, description="Filter by test ID")
    status: Optional[str] = Field(default=None, description="Filter by status")
    date_from: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    sort_by: str = Field(default="started_at", description="Sort field")
    sort_order: str = Field(default="desc", description="asc or desc")


class ExecutionListResponse(BaseModel):
    """Response for execution list."""
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "executions": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 0
    })


class ExecutionDetailResponse(BaseModel):
    """Response for single execution details."""
    success: bool = True
    data: Optional[TestExecutionRecord] = None
    message: str = ""


class AnalyticsResponse(BaseModel):
    """Response for analytics data."""
    success: bool = True
    data: Optional[TestAnalytics] = None
    message: str = ""


class SummaryResponse(BaseModel):
    """Response for dashboard summary."""
    success: bool = True
    data: Optional[DashboardSummary] = None
    message: str = ""


class DeleteExecutionResponse(BaseModel):
    """Response for execution deletion."""
    success: bool = True
    message: str = ""
