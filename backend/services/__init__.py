"""
backend.services - Business Logic Services

Core services for agent orchestration and execution.
"""

import backend
from backend.services.agent_orchestrator import AgentOrchestrator, get_orchestrator
from backend.services.screen_streamer import ScreenStreamer, StreamManager, get_stream_manager
from backend.services.verification_engine import VerificationEngine, VerificationResult, VerificationStatus
from backend.services.device_profile_service import DeviceProfileService, get_device_profile_service
from backend.services.verification_image_service import VerificationImageService, get_verification_image_service
from backend.services.report_generator import ReportGenerator, get_report_generator
from backend.services.test_history_service import TestHistoryService, get_test_history_service
from backend.services.execution_control import ExecutionControl, get_execution_control

__all__ = [
    # Orchestration
    "AgentOrchestrator",
    "get_orchestrator",
    
    # Streaming
    "ScreenStreamer",
    "StreamManager",
    "get_stream_manager",
    
    # Verification
    "VerificationEngine",
    "VerificationResult",
    "VerificationStatus",
    "VerificationImageService",
    "get_verification_image_service",
    
    # Device Profiles
    "DeviceProfileService",
    "get_device_profile_service",

    # Reporting
    "ReportGenerator",
    "get_report_generator",

    # Test History
    "TestHistoryService",
    "get_test_history_service",

    # Execution Control
    "ExecutionControl",
    "get_execution_control",
]