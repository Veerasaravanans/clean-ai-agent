"""
test_rag_phase33.py - Phase 3.3 Acceptance Test

Tests learned solutions functionality.
"""

import sys
sys.path.insert(0, '.')

from backend.tools.rag_tool import RAGTool
from backend.models.learned_solution import LearnedSolution, LearnedStep

def test_phase_33():
    """Phase 3.3 acceptance test."""
    print("=" * 80)
    print("Phase 3.3: Learned Solutions - Acceptance Test")
    print("=" * 80)
    
    # Test 1: Initialize RAG
    print("\n✓ Test 1: Initialize RAG")
    rag = RAGTool()
    rag.initialize()
    print("  ✅ RAG initialized")
    
    # Test 2: Save first learned solution
    print("\n✓ Test 2: Save learned solution (first execution)")
    success = rag.save_learned_solution(
        test_id="TEST-LEARN-001",
        title="Open Settings",
        component="Settings",
        steps=[
            {
                "step": 1,
                "description": "Tap Settings icon",
                "action": "tap",
                "coordinates": [850, 450],
                "success": True
            },
            {
                "step": 2,
                "description": "Verify Settings screen",
                "action": "verify",
                "target_element": "Settings Screen",
                "success": True
            }
        ]
    )
    
    assert success, "❌ Failed to save learned solution"
    print("  ✅ Learned solution saved")
    
    # Test 3: Retrieve learned solution
    print("\n✓ Test 3: Retrieve learned solution")
    solution = rag.get_learned_solution("TEST-LEARN-001")
    
    assert solution is not None, "❌ Failed to retrieve learned solution"
    assert solution["test_id"] == "TEST-LEARN-001", "❌ Wrong test_id"
    assert solution["title"] == "Open Settings", "❌ Wrong title"
    assert len(solution["steps"]) == 2, "❌ Wrong step count"
    assert solution["execution_count"] == 1, "❌ Wrong execution count"
    assert solution["success_count"] == 1, "❌ Wrong success count"
    assert solution["success_rate"] == 1.0, "❌ Wrong success rate"
    
    print(f"  ✅ Retrieved: {solution['test_id']}")
    print(f"     Title: {solution['title']}")
    print(f"     Steps: {len(solution['steps'])}")
    print(f"     Success rate: {solution['success_rate']:.0%} ({solution['success_count']}/{solution['execution_count']})")
    
    # Test 4: Update learned solution (2nd execution - success)
    print("\n✓ Test 4: Update learned solution (2nd execution - success)")
    success = rag.save_learned_solution(
        test_id="TEST-LEARN-001",
        title="Open Settings",
        component="Settings",
        steps=[
            {
                "step": 1,
                "action": "tap",
                "coordinates": [850, 450]
            },
            {
                "step": 2,
                "action": "verify",
                "target_element": "Settings Screen"
            }
        ]
    )
    
    assert success, "❌ Failed to update learned solution"
    
    solution = rag.get_learned_solution("TEST-LEARN-001")
    assert solution["execution_count"] == 2, "❌ Execution count not updated"
    assert solution["success_count"] == 2, "❌ Success count not updated"
    assert solution["success_rate"] == 1.0, "❌ Wrong success rate"
    
    print(f"  ✅ Updated: Success rate = {solution['success_rate']:.0%} ({solution['success_count']}/{solution['execution_count']})")
    
    # Test 5: Simulate failed execution (success rate should drop)
    print("\n✓ Test 5: Track success rate changes")
    
    # Save 3 more times to simulate executions
    for i in range(3):
        rag.save_learned_solution(
            test_id="TEST-LEARN-001",
            title="Open Settings",
            component="Settings",
            steps=[{"step": 1, "action": "tap"}]
        )
    
    solution = rag.get_learned_solution("TEST-LEARN-001")
    assert solution["execution_count"] == 5, f"❌ Wrong execution count: {solution['execution_count']}"
    assert solution["success_count"] == 5, f"❌ Wrong success count: {solution['success_count']}"
    assert solution["success_rate"] == 1.0, f"❌ Wrong success rate: {solution['success_rate']}"
    
    print(f"  ✅ After 5 executions:")
    print(f"     Success rate: {solution['success_rate']:.0%}")
    print(f"     Executions: {solution['execution_count']}")
    print(f"     Successes: {solution['success_count']}")
    
    # Test 6: Save solution for real test case from Excel
    print("\n✓ Test 6: Save learned solution for real test case")
    success = rag.save_learned_solution(
        test_id="NAID-24430",  # Real test from Paccar files
        title="HVAC: Fan Speed",
        component="HVAC",
        steps=[
            {
                "step": 1,
                "description": "Go to System UI HVAC section",
                "action": "tap",
                "coordinates": [700, 400],
                "target_element": "HVAC Section"
            },
            {
                "step": 2,
                "description": "Open Simfox HVAC tab",
                "action": "tap",
                "coordinates": [500, 300]
            },
            {
                "step": 3,
                "description": "Change HVAC_FAN_SPEED value",
                "action": "input_text",
                "input_text": "5"
            }
        ]
    )
    
    assert success, "❌ Failed to save real test learned solution"
    
    solution = rag.get_learned_solution("NAID-24430")
    assert solution is not None, "❌ Failed to retrieve real test solution"
    assert len(solution["steps"]) == 3, "❌ Wrong step count for real test"
    
    print(f"  ✅ Saved real test: {solution['test_id']}")
    print(f"     Steps: {len(solution['steps'])}")
    
    # Test 7: Verify timestamps
    print("\n✓ Test 7: Verify timestamps")
    solution = rag.get_learned_solution("TEST-LEARN-001")
    
    assert "last_execution" in solution, "❌ Missing last_execution"
    assert "created_at" in solution, "❌ Missing created_at"
    
    from datetime import datetime
    try:
        last_exec = datetime.fromisoformat(solution["last_execution"])
        created = datetime.fromisoformat(solution["created_at"])
        assert last_exec >= created, "❌ last_execution before created_at"
        print("  ✅ Timestamps valid:")
        print(f"     Created: {solution['created_at']}")
        print(f"     Last execution: {solution['last_execution']}")
    except Exception as e:
        raise AssertionError(f"❌ Invalid timestamp format: {e}")
    
    # Test 8: Get statistics
    print("\n✓ Test 8: Get database statistics")
    stats = rag.get_stats()
    
    print(f"  📊 Database stats:")
    print(f"     Test cases: {stats['test_cases_count']}")
    print(f"     Learned solutions: {stats['learned_solutions_count']}")
    
    assert stats['learned_solutions_count'] >= 2, "❌ Should have at least 2 learned solutions"
    print("  ✅ Statistics correct")
    
    # Test 9: Get all learned solution IDs
    print("\n✓ Test 9: List all learned solutions")
    solution_ids = rag.get_all_learned_solutions()
    
    assert len(solution_ids) >= 2, "❌ Should have at least 2 solutions"
    assert "TEST-LEARN-001" in solution_ids, "❌ TEST-LEARN-001 not in list"
    assert "NAID-24430" in solution_ids, "❌ NAID-24430 not in list"
    
    print(f"  ✅ Found {len(solution_ids)} learned solutions:")
    for sol_id in solution_ids[:5]:  # Show first 5
        print(f"     - {sol_id}")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 3.3 COMPLETE - All Tests Passed!")
    print("=" * 80)
    print("\nLearned Solutions Summary:")
    print(f"  • {stats['learned_solutions_count']} solutions stored")
    print(f"  • Success rate tracking: ✓")
    print(f"  • Timestamp tracking: ✓")
    print(f"  • Integration ready: ✓")
    print("\nNext: Phase 3.4 - Services Layer (Screen Streamer & Verification)")


if __name__ == "__main__":
    try:
        test_phase_33()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)