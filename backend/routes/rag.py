"""
rag.py - RAG Management API Routes

Provides endpoints for RAG operations: indexing, searching, and viewing learned solutions.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG Management"])

# Singleton RAG tool instance
_rag_tool = None


def get_rag_tool():
    """Get or create RAG tool singleton."""
    global _rag_tool
    if _rag_tool is None:
        from backend.tools.rag_tool import RAGTool
        _rag_tool = RAGTool(auto_initialize=True)
    return _rag_tool


# ═══════════════════════════════════════════════════════════
# RAG Statistics
# ═══════════════════════════════════════════════════════════

@router.get("/api/rag/stats")
async def get_rag_stats():
    """
    Get RAG database statistics.

    Returns:
        Stats including test case count, learned solutions count, etc.
    """
    try:
        rag = get_rag_tool()
        stats = rag.get_stats()

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Get RAG stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Test Case Operations
# ═══════════════════════════════════════════════════════════

@router.post("/api/rag/index")
async def index_test_cases():
    """
    Index test cases from Excel files in the test cases directory.

    Returns:
        Indexing result with counts
    """
    try:
        rag = get_rag_tool()
        result = rag.index_test_cases_from_directory()

        return {
            "success": True,
            "data": result,
            "message": f"Indexed {result['added']} test cases from {result['files']} files"
        }

    except Exception as e:
        logger.error(f"Index test cases error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/rag/refresh")
async def refresh_index():
    """
    Refresh RAG index - re-scan and index new files.

    Returns:
        Success confirmation
    """
    try:
        rag = get_rag_tool()
        rag.refresh_index()
        stats = rag.get_stats()

        return {
            "success": True,
            "data": stats,
            "message": "Index refreshed successfully"
        }

    except Exception as e:
        logger.error(f"Refresh index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/rag/search")
async def search_test_cases(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """
    Search for test cases by keywords or exact ID.

    Args:
        query: Search query or test ID
        limit: Maximum results

    Returns:
        List of matching test cases and/or exact match
    """
    try:
        rag = get_rag_tool()

        # First try exact ID match (if query looks like a test ID)
        exact_match = None
        query_upper = query.strip().upper()

        # Check if it looks like a test ID (e.g., NAID-NEW-001, TEST-001, etc.)
        if "-" in query or query_upper.startswith(("NAID", "TEST", "TC")):
            test_case = rag.get_test_description(query_upper)
            if test_case:
                exact_match = test_case
                logger.info(f"Found exact match for ID: {query_upper}")

        # Also do semantic search
        results = rag.search_similar_tests(query, top_k=limit)

        return {
            "success": True,
            "data": {
                "exact_match": exact_match,
                "results": results,
                "count": len(results) + (1 if exact_match else 0),
                "query": query
            }
        }

    except Exception as e:
        logger.error(f"Search test cases error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/rag/test/{test_id}")
async def get_test_case(test_id: str):
    """
    Get a specific test case by ID.

    Args:
        test_id: Test case ID

    Returns:
        Test case details
    """
    try:
        rag = get_rag_tool()
        test_case = rag.get_test_description(test_id)

        if not test_case:
            raise HTTPException(status_code=404, detail=f"Test case not found: {test_id}")

        return {
            "success": True,
            "data": test_case
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get test case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Learned Solutions Operations
# ═══════════════════════════════════════════════════════════

@router.get("/api/rag/learned")
async def get_learned_solutions():
    """
    Get all learned solutions.

    Returns:
        List of learned solution summaries
    """
    try:
        rag = get_rag_tool()

        # Get list of learned solution IDs
        learned_ids = rag.get_all_learned_solutions()

        # Get details for each
        solutions = []
        for test_id in learned_ids:
            solution = rag.get_learned_solution(test_id)
            if solution:
                solutions.append({
                    "test_id": solution.get("test_id"),
                    "title": solution.get("title"),
                    "component": solution.get("component"),
                    "step_count": len(solution.get("steps", [])),
                    "success_rate": solution.get("success_rate", 0),
                    "execution_count": solution.get("execution_count", 0),
                    "last_execution": solution.get("last_execution")
                })

        return {
            "success": True,
            "data": {
                "solutions": solutions,
                "count": len(solutions)
            }
        }

    except Exception as e:
        logger.error(f"Get learned solutions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/rag/learned/{test_id}")
async def get_learned_solution(test_id: str):
    """
    Get a specific learned solution by test ID.

    Args:
        test_id: Test case ID

    Returns:
        Learned solution details including steps with coordinates
    """
    try:
        rag = get_rag_tool()
        solution = rag.get_learned_solution(test_id)

        if not solution:
            raise HTTPException(status_code=404, detail=f"Learned solution not found: {test_id}")

        return {
            "success": True,
            "data": solution
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get learned solution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/rag/learned/{test_id}")
async def delete_learned_solution(test_id: str):
    """
    Delete a learned solution.

    Args:
        test_id: Test case ID

    Returns:
        Success confirmation
    """
    try:
        rag = get_rag_tool()

        if not rag.learned_solutions_collection:
            raise HTTPException(status_code=500, detail="RAG not initialized")

        # Check if exists
        existing = rag.get_learned_solution(test_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Learned solution not found: {test_id}")

        # Delete
        rag.learned_solutions_collection.delete(ids=[test_id])

        return {
            "success": True,
            "message": f"Deleted learned solution: {test_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete learned solution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
