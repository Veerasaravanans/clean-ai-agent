"""
standalone.py - Standalone Command Routes

Endpoints for natural language command execution with LangGraph orchestrator.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.models import (
    ExecuteCommandRequest,
    TapRequest,
    SwipeRequest,
    InputTextRequest,
    BaseResponse
)
from backend.services import get_orchestrator
from backend.tools import toolkit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute-command", response_model=BaseResponse)
async def execute_command(request: ExecuteCommandRequest):
    """
    Execute natural language command using LangGraph workflow.
    
    Args:
        request: ExecuteCommandRequest with command string
        
    Returns:
        BaseResponse with execution result
    """
    logger.info(f"🗣️ Execute command: {request.command}")
    
    try:
        orchestrator = get_orchestrator()
        
        result = await orchestrator.execute_command(
            command=request.command,
            max_retries=3
        )
        
        return BaseResponse(
            success=result["success"],
            message=f"Command executed: {result['status']}",
            data=result
        )
    
    except Exception as e:
        logger.error(f"❌ Command execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tap", response_model=BaseResponse)
async def tap(request: TapRequest):
    """
    Execute manual tap action.
    
    Args:
        request: TapRequest with x, y coordinates
        
    Returns:
        BaseResponse with result
    """
    logger.info(f"👆 Manual tap: ({request.x}, {request.y})")
    
    try:
        result = toolkit.tap(request.x, request.y)
        
        return BaseResponse(
            success=result.success,
            message=f"Tap executed at ({request.x}, {request.y})",
            data={"output": result.output}
        )
    
    except Exception as e:
        logger.error(f"❌ Tap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swipe", response_model=BaseResponse)
async def swipe(request: SwipeRequest):
    """
    Execute manual swipe action.
    
    Args:
        request: SwipeRequest with start/end coordinates
        
    Returns:
        BaseResponse with result
    """
    logger.info(f"👆 Manual swipe: ({request.start_x}, {request.start_y}) → ({request.end_x}, {request.end_y})")
    
    try:
        result = toolkit.swipe(
            request.start_x,
            request.start_y,
            request.end_x,
            request.end_y,
            request.duration_ms
        )
        
        return BaseResponse(
            success=result.success,
            message="Swipe executed",
            data={"output": result.output}
        )
    
    except Exception as e:
        logger.error(f"❌ Swipe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/input-text", response_model=BaseResponse)
async def input_text(request: InputTextRequest):
    """
    Execute manual text input.
    
    Args:
        request: InputTextRequest with text
        
    Returns:
        BaseResponse with result
    """
    logger.info(f"⌨️ Manual text input: {request.text}")
    
    try:
        result = toolkit.input_text(request.text)
        
        return BaseResponse(
            success=result.success,
            message=f"Text input: {request.text}",
            data={"output": result.output}
        )
    
    except Exception as e:
        logger.error(f"❌ Text input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/press-back", response_model=BaseResponse)
async def press_back():
    """
    Press back button.
    
    Returns:
        BaseResponse with result
    """
    logger.info("⬅️ Press back button")
    
    try:
        result = toolkit.press_back()
        
        return BaseResponse(
            success=result.success,
            message="Back button pressed",
            data={"output": result.output}
        )
    
    except Exception as e:
        logger.error(f"❌ Press back error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/press-home", response_model=BaseResponse)
async def press_home():
    """
    Press home button.
    
    Returns:
        BaseResponse with result
    """
    logger.info("🏠 Press home button")
    
    try:
        result = toolkit.press_home()
        
        return BaseResponse(
            success=result.success,
            message="Home button pressed",
            data={"output": result.output}
        )
    
    except Exception as e:
        logger.error(f"❌ Press home error: {e}")
        raise HTTPException(status_code=500, detail=str(e))