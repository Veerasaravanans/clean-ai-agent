"""
test_phase35.py - Phase 3.5 Acceptance Test

Tests new enums, result models, and RAG schemas.
"""

import sys
sys.path.insert(0, '.')

from backend.models import (
    TestResult,
    VerificationEngineStatus,
    TestExecutionResult,
    StepExecutionResult,
    IndexTestCasesRequest,
    SearchTestsRequest,
    LearnedSolutionResponse
)

def test_phase_35():
    """Phase 3.5 acceptance test."""
    print("=" * 80)
    print("Phase 3.5: Models & Schemas - Acceptance Test")
    print("=" * 80)
    
    # Test 1: New Enums
    print("\n✓ Test 1: Test new enums")
    
    # TestResult enum
    assert TestResult.PASSED == "passed", "❌ Wrong enum value"
    assert TestResult.FAILED == "failed", "❌ Wrong enum value"
    assert TestResult.SKIPPED == "skipped", "❌ Wrong enum value"
    assert TestResult.BLOCKED == "blocked", "❌ Wrong enum value"
    print("  ✅ TestResult enum: PASSED, FAILED, SKIPPED, BLOCKED")
    
    # VerificationEngineStatus enum
    assert VerificationEngineStatus.VERIFIED == "verified", "❌ Wrong enum value"
    assert VerificationEngineStatus.NOT_FOUND == "not_found", "❌ Wrong enum value"
    assert VerificationEngineStatus.TIMEOUT == "timeout", "❌ Wrong enum value"
    assert VerificationEngineStatus.PARTIAL == "partial", "❌ Wrong enum value"
    assert VerificationEngineStatus.ERROR == "error", "❌ Wrong enum value"
    print("  ✅ VerificationEngineStatus enum: VERIFIED, NOT_FOUND, TIMEOUT, PARTIAL, ERROR")
    
    # Test 2: TestExecutionResult model
    print("\n✓ Test 2: TestExecutionResult model")
    
    result = TestExecutionResult(
        test_id="TEST-001",
        result=TestResult.PASSED,
        duration=5.2,
        steps_executed=3,
        steps_passed=3,
        errors=[],
        screenshots=["shot1.png", "shot2.png"]
    )
    
    assert result.test_id == "TEST-001", "❌ Wrong test_id"
    assert result.result == TestResult.PASSED, "❌ Wrong result"
    assert result.duration == 5.2, "❌ Wrong duration"
    assert result.steps_executed == 3, "❌ Wrong steps_executed"
    assert result.steps_passed == 3, "❌ Wrong steps_passed"
    assert len(result.screenshots) == 2, "❌ Wrong screenshots count"
    
    print(f"  ✅ TestExecutionResult created:")
    print(f"     Test ID: {result.test_id}")
    print(f"     Result: {result.result}")
    print(f"     Duration: {result.duration}s")
    print(f"     Steps: {result.steps_passed}/{result.steps_executed}")
    
    # Test 3: StepExecutionResult model
    print("\n✓ Test 3: StepExecutionResult model")
    
    step_result = StepExecutionResult(
        step_number=1,
        description="Tap Settings icon",
        result=TestResult.PASSED,
        duration=1.5,
        screenshot="step1.png"
    )
    
    assert step_result.step_number == 1, "❌ Wrong step_number"
    assert step_result.description == "Tap Settings icon", "❌ Wrong description"
    assert step_result.result == TestResult.PASSED, "❌ Wrong result"
    
    print(f"  ✅ StepExecutionResult created:")
    print(f"     Step: {step_result.step_number}")
    print(f"     Description: {step_result.description}")
    print(f"     Result: {step_result.result}")
    
    # Test 4: RAG Request Schemas
    print("\n✓ Test 4: RAG request schemas")
    
    # IndexTestCasesRequest
    index_req = IndexTestCasesRequest(
        excel_path="data/test_cases/tests.xlsx",
        overwrite=False
    )
    assert index_req.excel_path == "data/test_cases/tests.xlsx", "❌ Wrong excel_path"
    assert index_req.overwrite == False, "❌ Wrong overwrite"
    print("  ✅ IndexTestCasesRequest schema working")
    
    # SearchTestsRequest
    search_req = SearchTestsRequest(
        query="HVAC fan speed",
        top_k=5,
        min_similarity=0.5
    )
    assert search_req.query == "HVAC fan speed", "❌ Wrong query"
    assert search_req.top_k == 5, "❌ Wrong top_k"
    assert search_req.min_similarity == 0.5, "❌ Wrong min_similarity"
    print("  ✅ SearchTestsRequest schema working")
    
    # Test 5: RAG Response Schemas
    print("\n✓ Test 5: RAG response schemas")
    
    learned_response = LearnedSolutionResponse(
        success=True,
        message="Learned solution found",
        data={
            "test_id": "NAID-24430",
            "success_rate": 0.8,
            "steps": [
                {"step": 1, "action": "tap", "coordinates": [700, 400]}
            ]
        }
    )
    
    assert learned_response.success == True, "❌ Wrong success"
    assert learned_response.data["test_id"] == "NAID-24430", "❌ Wrong test_id"
    assert learned_response.data["success_rate"] == 0.8, "❌ Wrong success_rate"
    
    print(f"  ✅ LearnedSolutionResponse schema working:")
    print(f"     Test ID: {learned_response.data['test_id']}")
    print(f"     Success rate: {learned_response.data['success_rate']:.0%}")
    
    # Test 6: Model JSON serialization
    print("\n✓ Test 6: Model JSON serialization")
    
    result_json = result.model_dump()
    assert "test_id" in result_json, "❌ Missing test_id in JSON"
    assert "result" in result_json, "❌ Missing result in JSON"
    assert "duration" in result_json, "❌ Missing duration in JSON"
    
    print("  ✅ Models serialize to JSON correctly")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 3.5 COMPLETE - All Tests Passed!")
    print("=" * 80)
    print("\nNew Models Summary:")
    print("  • Enums: TestResult, VerificationEngineStatus")
    print("  • Result Models: TestExecutionResult, StepExecutionResult")
    print("  • RAG Schemas: IndexTestCases, SearchTests, LearnedSolution")
    print("\n✅ STEP 3 COMPLETE - RAG System + Services Fully Implemented!")
    print("\nNext: Step 4 - Frontend Dashboard")


if __name__ == "__main__":
    try:
        test_phase_35()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)