"""
status.py - Status and Information Routes

Endpoints for checking agent status and device information with orchestrator integration.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.models import (
    StatusResponse,
    DeviceResponse,
    StatisticsResponse,
    BaseResponse
)
from backend.services import get_orchestrator
from backend.tools import toolkit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get current agent status from orchestrator.
    
    Returns:
        StatusResponse with agent state
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        
        return StatusResponse(
            success=True,
            message="Status retrieved",
            data=status
        )
    
    except Exception as e:
        logger.error(f"❌ Get status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device", response_model=DeviceResponse)
async def get_device_info():
    """
    Get device connection information.
    
    Returns:
        DeviceResponse with device details
    """
    try:
        device_info = toolkit.get_device_info()
        
        return DeviceResponse(
            success=True,
            message="Device info retrieved",
            data=device_info
        )
    
    except Exception as e:
        logger.error(f"❌ Get device info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    Get system statistics.
    
    Returns:
        StatisticsResponse with metrics
    """
    try:
        # Placeholder statistics
        stats = {
            "uptime": "0h 0m",
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "commands_executed": 0
        }
        
        return StatisticsResponse(
            success=True,
            message="Statistics retrieved",
            data=stats
        )
    
    except Exception as e:
        logger.error(f"❌ Get statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learned-solutions", response_model=BaseResponse)
async def get_learned_solutions():
    """
    Get list of tests with learned solutions.
    
    Returns:
        BaseResponse with learned test IDs
    """
    try:
        orchestrator = get_orchestrator()
        learned = orchestrator.get_learned_solutions()
        
        return BaseResponse(
            success=True,
            message=f"Found {len(learned)} learned solutions",
            data={"learned_tests": learned}
        )
    
    except Exception as e:
        logger.error(f"❌ Get learned solutions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))