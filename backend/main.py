"""
main.py - FastAPI Application Entry Point

AI Agent Framework - VIO Cloud Integration
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes import (
    test_execution_router,
    standalone_router,
    hitl_router,
    status_router,
    stream_router,
    device_profile_router,
    verification_images_router,
    model_routes_router
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 80)
    logger.info("AI AGENT FRAMEWORK - STARTING")
    logger.info("=" * 80)
    
    # Create required directories
    settings.create_directories()
    
    # Print configuration summary
    settings.print_summary()
    
    # Validate VIO connection
    if settings.llm_provider == "vio_cloud":
        if settings.validate_vio_connection():
            logger.info("✅ VIO Cloud configuration valid")
        else:
            logger.warning("⚠️  VIO Cloud configuration issues detected")
    
    logger.info("=" * 80)
    logger.info("SERVER READY")
    logger.info(f"Access at: http://{settings.host}:{settings.port}")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("AI AGENT FRAMEWORK - SHUTTING DOWN")
    logger.info("=" * 80)


# Create FastAPI application
app = FastAPI(
    title="AI Agent Framework",
    description="Android Automotive UI Testing with VIO Cloud LLM",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(test_execution_router, prefix="/api", tags=["Test Execution"])
app.include_router(standalone_router, prefix="/api", tags=["Standalone Commands"])
app.include_router(hitl_router, prefix="/api", tags=["Human-in-the-Loop"])
app.include_router(status_router, prefix="/api", tags=["Status & Info"])
app.include_router(stream_router, prefix="/ws", tags=["WebSocket Streaming"])
app.include_router(model_routes_router, tags=["Model Management"])
app.include_router(device_profile_router, tags=["Device Profile"])
app.include_router(verification_images_router, tags=["Verification Images"])


# Health check endpoint (must be before static mount)
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status with version and uptime
    """
    from backend.models import HealthResponse
    
    # Check device connection
    from backend.tools import toolkit
    device_connected = toolkit.is_device_connected()
    
    # Check VIO connection (basic check)
    vio_connected = False
    if settings.llm_provider == "vio_cloud":
        vio_connected = settings.validate_vio_connection()
    
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime=0,  # TODO: Implement uptime tracking
        checks={
            "database": True,  # Vector DB check TODO
            "device": device_connected,
            "llm": vio_connected
        }
    )


# Mount static files (frontend) - MUST BE LAST
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"✅ Frontend mounted from: {frontend_path}")
else:
    logger.warning(f"⚠️  Frontend directory not found: {frontend_path}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )