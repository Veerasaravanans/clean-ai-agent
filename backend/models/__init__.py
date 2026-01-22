"""
backend.models - Data Models and Schemas

Contains all Pydantic models, enums, dataclasses, and schemas.
"""

from backend.models.enums import (
    AgentMode,
    AgentStatus,
    ActionType,
    VerificationStatus,
    TestResult,
    VerificationEngineStatus,
    LogLevel,
    OCREngine
)
from backend.models.learned_solution import LearnedSolution, LearnedStep, LearnedSolutionStats
from backend.models.results import (
    Coordinates,
    ActionResult,
    ChangeResult,
    TextElement,
    ScreenAnalysis,
    LogEntry,
    DeviceInfo,
    TestExecutionResult,
    StepExecutionResult
)
from backend.models.schemas import (
    # Requests
    RunTestRequest,
    ExecuteCommandRequest,
    SendGuidanceRequest,
    StopRequest,
    TapRequest,
    SwipeRequest,
    InputTextRequest,
    IndexTestCasesRequest,
    SearchTestsRequest,

    # Responses
    BaseResponse,
    RunTestsResponse,
    ExecuteCommandResponse,
    SendGuidanceResponse,
    ExecutionStartResponse,
    StopResponse,
    StatusResponse,
    DeviceResponse,
    StatisticsResponse,
    HealthResponse,
    IndexTestCasesResponse,
    SearchTestsResponse,
    LearnedSolutionResponse,
    RAGStatsResponse,

    # WebSocket
    WSLogMessage,
    WSStatusMessage,
    WSHITLMessage,
    WSScreenMessage
)

# Test History Models
from backend.models.test_history import (
    ExecutionStatus,
    StepRecord,
    TestExecutionRecord,
    DailyStats,
    TestCaseStats,
    TestAnalytics,
    DashboardSummary,
    ExecutionListRequest,
    ExecutionListResponse,
    ExecutionDetailResponse,
    AnalyticsResponse,
    SummaryResponse,
    DeleteExecutionResponse
)

# Report Models
from backend.models.reports import (
    ReportFormat,
    ReportType,
    GenerateReportRequest,
    ReportMetadata,
    GenerateReportResponse,
    ReportListResponse,
    ReportDetailResponse,
    DeleteReportResponse
)

__all__ = [
    # Enums
    "AgentMode",
    "AgentStatus", 
    "ActionType",
    "VerificationStatus",
    "TestResult",
    "VerificationEngineStatus",
    "LogLevel",
    "OCREngine",
    
    # Learned Solutions
    "LearnedSolution",
    "LearnedStep",
    "LearnedSolutionStats",
    
    # Results (Dataclasses & Pydantic)
    "Coordinates",
    "ActionResult",
    "ChangeResult",
    "TextElement",
    "ScreenAnalysis",
    "LogEntry",
    "DeviceInfo",
    "TestExecutionResult",
    "StepExecutionResult",
    
    # Request Schemas
    "RunTestRequest",
    "ExecuteCommandRequest",
    "SendGuidanceRequest",
    "StopRequest",
    "TapRequest",
    "SwipeRequest",
    "InputTextRequest",
    "IndexTestCasesRequest",
    "SearchTestsRequest",
    
    # Response Schemas
    "BaseResponse",
    "RunTestsResponse",
    "ExecuteCommandResponse",
    "SendGuidanceResponse",
    "ExecutionStartResponse",
    "StopResponse",
    "StatusResponse",
    "DeviceResponse",
    "StatisticsResponse",
    "HealthResponse",
    "IndexTestCasesResponse",
    "SearchTestsResponse",
    "LearnedSolutionResponse",
    "RAGStatsResponse",
    
    # WebSocket Messages
    "WSLogMessage",
    "WSStatusMessage",
    "WSHITLMessage",
    "WSScreenMessage",

    # Test History
    "ExecutionStatus",
    "StepRecord",
    "TestExecutionRecord",
    "DailyStats",
    "TestCaseStats",
    "TestAnalytics",
    "DashboardSummary",
    "ExecutionListRequest",
    "ExecutionListResponse",
    "ExecutionDetailResponse",
    "AnalyticsResponse",
    "SummaryResponse",
    "DeleteExecutionResponse",

    # Reports
    "ReportFormat",
    "ReportType",
    "GenerateReportRequest",
    "ReportMetadata",
    "GenerateReportResponse",
    "ReportListResponse",
    "ReportDetailResponse",
    "DeleteReportResponse",
]