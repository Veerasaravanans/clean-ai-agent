"""
start_server.py - Startup script with import verification
"""

import sys
import os

print("=" * 80)
print("AI AGENT FRAMEWORK - STARTUP")
print("=" * 80)

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"✅ Added to Python path: {current_dir}")

print("\n1. Verifying imports...")

try:
    from backend.config import settings
    print("   ✅ Config loaded")
except ImportError as e:
    print(f"   ❌ Config import failed: {e}")
    sys.exit(1)

try:
    from backend.models import AgentStatus
    print("   ✅ Models loaded")
except ImportError as e:
    print(f"   ❌ Models import failed: {e}")
    sys.exit(1)

try:
    from backend.tools import toolkit
    print("   ✅ Tools loaded")
except ImportError as e:
    print(f"   ❌ Tools import failed: {e}")
    sys.exit(1)

try:
    from backend.routes import (
        test_execution_router,
        standalone_router,
        hitl_router,
        status_router,
        stream_router
    )
    print("   ✅ Routes loaded")
except ImportError as e:
    print(f"   ❌ Routes import failed: {e}")
    print("\nTry running: python test_imports.py")
    sys.exit(1)

print("\n2. Starting FastAPI server...")
print("=" * 80)

import uvicorn

uvicorn.run(
    "backend.main:app",
    host=settings.host,
    port=settings.port,
    reload=settings.debug,
    log_level=settings.log_level.lower()
)