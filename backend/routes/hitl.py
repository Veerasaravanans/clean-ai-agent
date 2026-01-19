"""
hitl.py - Human-in-the-Loop Routes

Endpoints for human intervention with LangGraph orchestrator integration.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.models import SendGuidanceRequest, BaseResponse
from backend.services import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send-guidance", response_model=BaseResponse)
async def send_guidance(request: SendGuidanceRequest):
    """
    Send human guidance to orchestrator.
    
    Args:
        request: SendGuidanceRequest with guidance, coordinates, action_type
        
    Returns:
        BaseResponse with confirmation
    """
    logger.info(f"👤 HITL guidance received: {request.guidance}")
    
    try:
        orchestrator = get_orchestrator()
        
        # Send guidance to orchestrator (CRITICAL FIX: Added await)
        result = await orchestrator.send_guidance(
            guidance=request.guidance,
            coordinates=request.coordinates,
            action_type=request.action_type
        )
        
        return BaseResponse(
            success=result["success"],
            message=result.get("message", "Guidance received"),
            data={
                "guidance": request.guidance,
                "coordinates": request.coordinates,
                "action_type": request.action_type
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Send guidance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip-step", response_model=BaseResponse)
async def skip_step():
    """
    Skip current test step.
    
    Returns:
        BaseResponse with confirmation
    """
    logger.info("⏭️ Skip step request")
    
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.skip_step()
        
        return BaseResponse(
            success=result["success"],
            message=result["message"]
        )
    
    except Exception as e:
        logger.error(f"❌ Skip step error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/abort-test", response_model=BaseResponse)
async def abort_test():
    """
    Abort current test execution.
    
    Returns:
        BaseResponse with confirmation
    """
    logger.info("🛑 Abort test request")
    
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.abort_test()
        
        return BaseResponse(
            success=result["success"],
            message=result["message"]
        )
    
    except Exception as e:
        logger.error(f"❌ Abort test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))