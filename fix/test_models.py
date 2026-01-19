"""Test script for models module."""

print("Testing models import...")

try:
    from backend.models.enums import AgentStatus, AgentMode
    print("✅ Enums imported:", AgentStatus.RUNNING, AgentMode.TEST_EXECUTION)
except Exception as e:
    print(f"❌ Enums error: {e}")

try:
    from backend.models.results import Coordinates, ActionResult
    c = Coordinates(100, 200)
    print("✅ Data classes imported:", c.to_tuple())
except Exception as e:
    print(f"❌ Data classes error: {e}")

try:
    from backend.models.schemas import RunTestRequest, StatusResponse
    req = RunTestRequest(test_ids=['TEST-1'])
    print("✅ Schemas imported:", req.test_ids)
except Exception as e:
    print(f"❌ Schemas error: {e}")

print("\n✅ All models loaded successfully!")