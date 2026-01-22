"""
test_execution.py - Test Execution Routes

Endpoints for running test cases with LangGraph orchestrator.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.models import (
    RunTestRequest,
    ExecutionStartResponse,
    StopResponse,
    BaseResponse
)
from backend.services import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run-tests", response_model=ExecutionStartResponse)
async def run_tests(request: RunTestRequest):
    """
    Run one or more test cases using LangGraph workflow.
    
    Handles multiple input formats:
    - ["NAID-001", "NAID-002"] - Array of separate IDs
    - ["NAID-001, NAID-002"] - Single string with comma-separated IDs
    
    Args:
        request: RunTestRequest with test_ids, use_learned, max_retries
        
    Returns:
        ExecutionStartResponse with execution status
    """
    logger.info(f"🚀 Run tests request (raw): {request.test_ids}")
    
    try:
        orchestrator = get_orchestrator()
        
        if not request.test_ids:
            raise HTTPException(status_code=400, detail="No test IDs provided")
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL: Parse and split test IDs properly
        # ═══════════════════════════════════════════════════════════
        parsed_test_ids = []
        for item in request.test_ids:
            if isinstance(item, str):
                # Split by comma or semicolon
                for part in item.replace(";", ",").split(","):
                    cleaned = part.strip()
                    # Skip empty strings
                    if cleaned:
                        parsed_test_ids.append(cleaned)
            else:
                parsed_test_ids.append(str(item))
        
        if not parsed_test_ids:
            raise HTTPException(status_code=400, detail="No valid test IDs after parsing")
        
        logger.info(f"🚀 Run tests request (parsed): {parsed_test_ids}")
        logger.info(f"   Total tests to run: {len(parsed_test_ids)}")
        
        # ═══════════════════════════════════════════════════════════
        # Execute tests sequentially
        # ═══════════════════════════════════════════════════════════
        all_results = []
        total_passed = 0
        total_failed = 0
        
        for i, test_id in enumerate(parsed_test_ids):
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"▶️ Running test {i + 1}/{len(parsed_test_ids)}: {test_id}")
            
            # Execute single test
            result = await orchestrator.run_test(
                test_id=test_id,
                use_learned=request.use_learned,
                max_retries=request.max_retries
            )
            
            # ═══════════════════════════════════════════════════════════
            # CRITICAL FIX: Correctly interpret status from orchestrator
            # ═══════════════════════════════════════════════════════════
            # The orchestrator returns status as one of:
            # - "passed" (all steps completed successfully)
            # - "failed" (errors occurred)
            # - "incomplete" (not all steps completed)
            # - "waiting" (waiting for HITL)
            
            status = result.get("status", "unknown").lower()
            
            # Determine if test passed based on status
            if status == "passed":
                test_success = True
            elif status in ["failed", "incomplete", "unknown", "waiting"]:
                test_success = False
            else:
                # Fallback: check legacy "success" field
                test_success = result.get("success", False)
            
            # Count passed/failed
            if test_success:
                total_passed += 1
            else:
                total_failed += 1
            
            # Store result
            all_results.append({
                "test_id": test_id,
                "status": status,
                "success": test_success,
                "steps_completed": result.get("steps_completed", result.get("completed_steps", 0)),
                "total_steps": result.get("total_steps", 0),
                "errors": result.get("errors", [])
            })
            
            # Log result with correct interpretation
            logger.info(f"   Result: {'✅ PASSED' if test_success else '❌ FAILED'}")
        
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"📊 Test Run Summary: {total_passed}/{len(parsed_test_ids)} passed")
        
        # Determine overall success
        overall_success = total_failed == 0
        
        # Build response message
        if len(parsed_test_ids) == 1:
            message = f"Test execution completed: {all_results[0]['status']}"
        else:
            message = f"Test batch completed: {total_passed}/{len(parsed_test_ids)} passed"
        
        return ExecutionStartResponse(
            success=overall_success,
            message=message,
            data={
                "tests_run": len(parsed_test_ids),
                "passed": total_passed,
                "failed": total_failed,
                "results": all_results,
                # For backward compatibility, include first test details
                "test_id": parsed_test_ids[0] if len(parsed_test_ids) == 1 else None,
                "status": all_results[0]["status"] if len(parsed_test_ids) == 1 else "batch_complete",
                "steps_completed": all_results[0]["steps_completed"] if len(parsed_test_ids) == 1 else sum(r["steps_completed"] for r in all_results),
                "total_steps": all_results[0]["total_steps"] if len(parsed_test_ids) == 1 else sum(r["total_steps"] for r in all_results),
                "errors": all_results[0]["errors"] if len(parsed_test_ids) == 1 else [e for r in all_results for e in r.get("errors", [])]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Test execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=StopResponse)
async def stop_execution():
    """
    Stop current test execution immediately.

    Returns:
        StopResponse with confirmation
    """
    logger.info("🛑 Stop execution request")

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.stop()

        return StopResponse(
            success=result["success"],
            message=result["message"]
        )

    except Exception as e:
        logger.error(f"❌ Stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause", response_model=BaseResponse)
async def pause_execution():
    """
    Pause current test execution.

    Execution will wait at the next checkpoint until resumed.

    Returns:
        BaseResponse with confirmation
    """
    logger.info("⏸️ Pause execution request")

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.pause()

        return BaseResponse(
            success=result["success"],
            message=result["message"]
        )

    except Exception as e:
        logger.error(f"❌ Pause error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=BaseResponse)
async def resume_execution():
    """
    Resume paused test execution.

    Returns:
        BaseResponse with confirmation
    """
    logger.info("▶️ Resume execution request")

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.resume()

        return BaseResponse(
            success=result["success"],
            message=result["message"]
        )

    except Exception as e:
        logger.error(f"❌ Resume error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=BaseResponse)
async def reset_agent():
    """
    Reset agent state.
    
    Returns:
        BaseResponse with confirmation
    """
    logger.info("🔄 Reset agent request")
    
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.reset()
        
        return BaseResponse(
            success=result["success"],
            message=result["message"]
        )
    
    except Exception as e:
        logger.error(f"❌ Reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))