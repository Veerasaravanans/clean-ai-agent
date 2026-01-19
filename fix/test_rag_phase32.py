"""
test_rag_phase32.py - Phase 3.2 Acceptance Test

Tests Excel parsing and indexing.
"""

import sys
sys.path.insert(0, '.')

from backend.tools.rag_tool import RAGTool

def test_phase_32():
    """Phase 3.2 acceptance test."""
    print("=" * 80)
    print("Phase 3.2: Test Case Indexing - Acceptance Test")
    print("=" * 80)
    
    # Test 1: Initialize RAG
    print("\n✓ Test 1: Initialize RAG")
    rag = RAGTool()
    rag.initialize()
    print("  ✅ RAG initialized")
    
    # Test 2: Index test cases from directory
    print("\n✓ Test 2: Index test cases from Excel files")
    result = rag.index_test_cases_from_directory(
        directory="./data/test_cases",
        pattern="*.xlsx"
    )
    
    print(f"  📊 Indexing results:")
    print(f"     Files processed: {result['files']}")
    print(f"     Test cases added: {result['added']}")
    print(f"     Skipped: {result['skipped']}")
    print(f"     Errors: {result['errors']}")
    
    assert result["added"] > 0, "❌ No test cases indexed"
    print(f"  ✅ Indexed {result['added']} test cases")
    
    # Test 3: Retrieve specific test case by exact ID
    print("\n✓ Test 3: Retrieve test case by exact ID")
    test = rag.get_test_description("NAID-24430")  # From Paccar file
    
    if test:
        print(f"  ✅ Retrieved: {test['test_id']}")
        print(f"     Title: {test['title']}")
        print(f"     Component: {test['component']}")
        print(f"     Steps: {len(test['steps'])}")
        assert test['title'] == "HVAC: Fan Speed", f"❌ Wrong title: {test['title']}"
        assert len(test['steps']) > 0, "❌ No steps found"
    else:
        raise AssertionError("❌ Failed to retrieve test NAID-24430")
    
    # Test 4: Search similar tests
    print("\n✓ Test 4: Search similar tests")
    search_results = rag.search_similar_tests("HVAC fan speed", top_k=3, min_similarity=0.3)
    
    print(f"  🔍 Found {len(search_results)} similar test(s)")
    if search_results:
        for i, search_result in enumerate(search_results[:3], 1):
            print(f"     {i}. {search_result['test_id']}: {search_result['title'][:40]} (similarity: {search_result['similarity']:.2%})")
    
    assert len(search_results) > 0, "❌ No search results"
    print("  ✅ Similarity search working")
    
    # Test 5: Get statistics
    print("\n✓ Test 5: Get statistics")
    stats = rag.get_stats()
    
    print(f"  📊 Database stats:")
    print(f"     Test cases: {stats['test_cases_count']}")
    print(f"     Learned solutions: {stats['learned_solutions_count']}")
    print(f"     Embedding model: {stats['embedding_model']}")
    
    # Note: Some test IDs may be duplicates across files, so count may be less than added
    print(f"  ℹ️  Note: {result['added']} attempted, {stats['test_cases_count']} unique")
    assert stats['test_cases_count'] > 0, "❌ No test cases in database"
    print("  ✅ Statistics correct")
    
    # Test 6: Verify exact ID retrieval (not similarity)
    print("\n✓ Test 6: Verify exact ID retrieval")
    test1 = rag.get_test_description("NAID-24430")
    test2 = rag.get_test_description("NAID-99999")  # Non-existent
    
    assert test1 is not None, "❌ Failed to get existing test"
    assert test2 is None, "❌ Got result for non-existent test"
    print("  ✅ Exact ID retrieval working correctly")
    print("     Existing ID: Found ✓")
    print("     Non-existent ID: Not found ✓")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 3.2 COMPLETE - All Tests Passed!")
    print("=" * 80)
    print(f"\nIndexed {result['added']} test cases from {result['files']} Excel files")
    print("Next: Phase 3.3 - Learned Solutions")


if __name__ == "__main__":
    try:
        test_phase_32()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)