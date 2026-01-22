"""
backend.routes - API Route Handlers

FastAPI endpoints for test execution, standalone commands, HITL, status, and streaming.
"""

from backend.routes.test_execution import router as test_execution_router
from backend.routes.standalone import router as standalone_router
from backend.routes.hitl import router as hitl_router
from backend.routes.status import router as status_router
from backend.routes.stream import router as stream_router
from backend.routes.model_routes import router as model_routes_router
from backend.routes.device_profile import router as device_profile_router
from backend.routes.verification_images import router as verification_images_router
from backend.routes.test_history import router as test_history_router
from backend.routes.reports import router as reports_router
from backend.routes.rag import router as rag_router
from backend.routes.excel_batch import router as excel_batch_router

__all__ = [
    "test_execution_router",
    "standalone_router",
    "hitl_router",
    "status_router",
    "stream_router",
    "device_profile_router",
    "verification_images_router",
    "model_routes_router",
    "test_history_router",
    "reports_router",
    "rag_router",
    "excel_batch_router"
]