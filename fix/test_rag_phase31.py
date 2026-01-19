"""
test_rag_phase31.py - Phase 3.1 Acceptance Test

Tests RAG foundation implementation.
"""

import sys
sys.path.insert(0, '.')

from backend.tools.rag_tool import RAGTool

def test_phase_31():
    """Phase 3.1 acceptance test."""
    print("=" * 80)
    print("Phase 3.1: RAG Foundation - Acceptance Test")
    print("=" * 80)
    
    # Test 1: Initialize RAG
    print("\n✓ Test 1: Initialize RAG")
    rag = RAGTool()
    rag.initialize()
    
    assert rag.test_cases_collection is not None, "❌ Test cases collection not created"
    assert rag.learned_solutions_collection is not None, "❌ Learned solutions collection not created"
    print("  ✅ Collections created successfully")
    
    # Test 2: Add test case
    print("\n✓ Test 2: Add test case")
    success = rag.add_test_case(
        test_id="TEST-001",
        title="Open Settings",
        component="Settings",
        steps=["Launch app", "Tap Settings", "Verify screen"],
        description="Test opening settings screen",
        expected="Settings screen displays"
    )
    assert success, "❌ Failed to add test case"
    print("  ✅ Test case added")
    
    # Test 3: Retrieve test case
    print("\n✓ Test 3: Retrieve test case")
    test = rag.get_test_description("TEST-001")
    assert test is not None, "❌ Failed to retrieve test case"
    assert test["title"] == "Open Settings", "❌ Wrong title"
    assert len(test["steps"]) == 3, "❌ Wrong step count"
    print(f"  ✅ Retrieved: {test['title']}")
    
    # Test 4: Search similar tests
    print("\n✓ Test 4: Search similar tests")
    results = rag.search_similar_tests("open settings menu", top_k=5, min_similarity=0.5)
    assert len(results) > 0, "❌ No search results"
    print(f"  ✅ Found {len(results)} similar test(s)")
    if results:
        print(f"     Best match: '{results[0]['title']}' (similarity: {results[0]['similarity']:.2%})")
    
    # Test 5: Save learned solution
    print("\n✓ Test 5: Save learned solution")
    success = rag.save_learned_solution(
        test_id="TEST-001",
        title="Open Settings",
        component="Settings",
        steps=[
            {"step": 1, "action": "tap", "coordinates": [850, 450]},
            {"step": 2, "action": "verify", "element": "Settings"}
        ]
    )
    assert success, "❌ Failed to save learned solution"
    print("  ✅ Learned solution saved")
    
    # Test 6: Retrieve learned solution
    print("\n✓ Test 6: Retrieve learned solution")
    solution = rag.get_learned_solution("TEST-001")
    assert solution is not None, "❌ Failed to retrieve learned solution"
    assert solution["success_rate"] == 1.0, "❌ Wrong success rate"
    print(f"  ✅ Retrieved: Success rate = {solution['success_rate']:.0%}")
    
    # Test 7: Get stats
    print("\n✓ Test 7: Get statistics")
    stats = rag.get_stats()
    assert stats["initialized"], "❌ Not initialized"
    assert stats["test_cases_count"] >= 1, "❌ Wrong test count"
    assert stats["learned_solutions_count"] >= 1, "❌ Wrong solution count"
    print(f"  ✅ Stats: {stats['test_cases_count']} tests, {stats['learned_solutions_count']} solutions")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 3.1 COMPLETE - All Tests Passed!")
    print("=" * 80)
    print("\nNext: Phase 3.2 - Test Case Indexing from Excel")


if __name__ == "__main__":
    try:
        test_phase_31()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)