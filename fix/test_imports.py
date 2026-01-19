"""
test_imports.py - Verify all imports work correctly
"""

print("Testing imports...")

try:
    print("1. Testing backend.config import...")
    from backend.config import settings
    print("   ✅ backend.config OK")
except Exception as e:
    print(f"   ❌ backend.config FAILED: {e}")
    exit(1)

try:
    print("2. Testing backend.models import...")
    from backend.models import AgentStatus, RunTestRequest
    print("   ✅ backend.models OK")
except Exception as e:
    print(f"   ❌ backend.models FAILED: {e}")
    exit(1)

try:
    print("3. Testing backend.tools import...")
    from backend.tools import toolkit
    print("   ✅ backend.tools OK")
except Exception as e:
    print(f"   ❌ backend.tools FAILED: {e}")
    exit(1)

try:
    print("4. Testing individual route files...")
    from backend.routes import test_execution
    print("   ✅ test_execution OK")
    from backend.routes import standalone
    print("   ✅ standalone OK")
    from backend.routes import hitl
    print("   ✅ hitl OK")
    from backend.routes import status
    print("   ✅ status OK")
    from backend.routes import stream
    print("   ✅ stream OK")
except Exception as e:
    print(f"   ❌ Route files FAILED: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

try:
    print("5. Testing route routers import...")
    from backend.routes import (
        test_execution_router,
        standalone_router,
        hitl_router,
        status_router,
        stream_router
    )
    print("   ✅ Route routers OK")
except Exception as e:
    print(f"   ❌ Route routers FAILED: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

try:
    print("6. Testing FastAPI app import...")
    from backend.main import app
    print("   ✅ FastAPI app OK")
except Exception as e:
    print(f"   ❌ FastAPI app FAILED: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ All imports successful!")
print("\nYou can now run:")
print("  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")