"""
test_history.py - Test History API Routes

API endpoints for test execution history, analytics, and dashboard data.
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from backend.services.test_history_service import get_test_history_service
from backend.models.test_history import (
    ExecutionListResponse,
    ExecutionDetailResponse,
    AnalyticsResponse,
    SummaryResponse,
    DeleteExecutionResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["Test History"])


# ═══════════════════════════════════════════════════════════
# List Executions
# ═══════════════════════════════════════════════════════════

@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    test_id: Optional[str] = Query(default=None, description="Filter by test ID"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    date_from: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    sort_by: str = Query(default="started_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="asc or desc")
):
    """
    List all test executions with pagination and filtering.

    Returns paginated list of executions with summary data.
    """
    try:
        service = get_test_history_service()
        data = service.list_executions(
            page=page,
            page_size=page_size,
            test_id=test_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return ExecutionListResponse(success=True, data=data)

    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Get Single Execution
# ═══════════════════════════════════════════════════════════

@router.get("/execution/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(execution_id: str):
    """
    Get detailed information about a specific execution.

    Args:
        execution_id: Unique execution identifier

    Returns:
        Full execution record with all step details
    """
    try:
        service = get_test_history_service()
        record = service.get_execution(execution_id)

        if not record:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

        return ExecutionDetailResponse(
            success=True,
            data=record,
            message=f"Execution {execution_id} retrieved"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Get Test History
# ═══════════════════════════════════════════════════════════

@router.get("/test/{test_id}")
async def get_test_history(
    test_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results")
):
    """
    Get execution history for a specific test case.

    Args:
        test_id: Test case ID
        limit: Maximum number of results

    Returns:
        List of execution summaries for the test
    """
    try:
        service = get_test_history_service()
        history = service.get_test_history(test_id, limit)

        return {
            "success": True,
            "data": {
                "test_id": test_id,
                "executions": history,
                "count": len(history)
            }
        }

    except Exception as e:
        logger.error(f"Error getting test history for {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Analytics
# ═══════════════════════════════════════════════════════════

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """
    Get comprehensive test analytics.

    Returns analytics data including:
    - Overall statistics
    - Daily trends (last 30 days)
    - Most executed tests
    - Most failed tests
    - SSIM verification stats
    - Duration statistics
    """
    try:
        service = get_test_history_service()
        analytics = service.get_analytics()

        return AnalyticsResponse(
            success=True,
            data=analytics,
            message="Analytics generated successfully"
        )

    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Dashboard Summary
# ═══════════════════════════════════════════════════════════

@router.get("/summary", response_model=SummaryResponse)
async def get_summary():
    """
    Get dashboard summary statistics.

    Returns quick summary data for dashboard display including:
    - Total executions, passed, failed
    - Today's statistics
    - Trend indicator
    - Recent executions
    """
    try:
        service = get_test_history_service()
        summary = service.get_summary()

        return SummaryResponse(
            success=True,
            data=summary,
            message="Summary generated successfully"
        )

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Delete Execution
# ═══════════════════════════════════════════════════════════

@router.delete("/execution/{execution_id}", response_model=DeleteExecutionResponse)
async def delete_execution(execution_id: str):
    """
    Delete a specific execution record.

    Args:
        execution_id: Execution identifier to delete

    Returns:
        Success confirmation
    """
    try:
        service = get_test_history_service()

        # Verify exists
        record = service.get_execution(execution_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

        # Delete
        success = service.delete_execution(execution_id)

        if success:
            return DeleteExecutionResponse(
                success=True,
                message=f"Execution {execution_id} deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete execution")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Clear History
# ═══════════════════════════════════════════════════════════

@router.delete("/clear")
async def clear_history(
    older_than_days: Optional[int] = Query(default=None, ge=1, description="Delete executions older than N days")
):
    """
    Clear execution history.

    Args:
        older_than_days: If provided, only delete executions older than this many days.
                         If not provided, deletes ALL history (use with caution).

    Returns:
        Count of deleted executions
    """
    try:
        from datetime import datetime, timedelta

        service = get_test_history_service()
        deleted_count = 0

        if older_than_days:
            cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            executions_to_delete = [
                e["execution_id"] for e in service.index["executions"]
                if e["started_at"] < cutoff_date
            ]
        else:
            executions_to_delete = [e["execution_id"] for e in service.index["executions"]]

        for exec_id in executions_to_delete:
            if service.delete_execution(exec_id):
                deleted_count += 1

        return {
            "success": True,
            "message": f"Deleted {deleted_count} execution(s)",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
