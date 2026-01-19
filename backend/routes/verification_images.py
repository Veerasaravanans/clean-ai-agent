"""
verification_images.py - API Routes for Verification Image Management

Endpoints:
- POST /api/verification/capture - Capture and save verification image
- GET /api/verification/images - List verification images for current device
- GET /api/verification/image/{name} - Get specific verification image
- DELETE /api/verification/image/{name} - Delete verification image
- GET /api/verification/devices - List all devices with images
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from backend.services.verification_image_service import get_verification_image_service
from backend.tools.screenshot_tool import ScreenshotTool
from backend.tools.adb_tool import ADBTool
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize tools
screenshot_tool = ScreenshotTool()
adb_tool = ADBTool()


class CaptureVerificationImageRequest(BaseModel):
    """Request to capture verification reference image."""
    image_name: str
    description: Optional[str] = None


class DeleteVerificationImageRequest(BaseModel):
    """Request to delete verification image."""
    image_name: str


@router.post("/api/verification/capture")
async def capture_verification_image(request: CaptureVerificationImageRequest):
    """
    Capture screenshot and save as verification reference image.
    
    Body:
        {
            "image_name": "app_launcher_opened",
            "description": "App launcher drawer opened"
        }
    """
    try:
        logger.info(f"📸 Capturing verification image: {request.image_name}")
        
        # Get current device info
        device_info = adb_tool.get_device_info()
        
        if not device_info.get("connected"):
            raise HTTPException(status_code=400, detail="No device connected")
        
        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)
        
        if screen_width == 0 or screen_height == 0:
            raise HTTPException(status_code=400, detail="Could not determine screen dimensions")
        
        # Get device ID
        verification_service = get_verification_image_service()
        device_id = verification_service.get_device_id(screen_width, screen_height)
        
        # Capture screenshot
        screenshot_path = screenshot_tool.capture(
            filename=f"verification_temp_{request.image_name}.jpg"
        )
        
        if not screenshot_path:
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")
        
        # Save as verification image
        success = verification_service.save_verification_image(
            screenshot_path=screenshot_path,
            image_name=request.image_name,
            device_id=device_id,
            description=request.description
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save verification image")
        
        logger.info(f"✅ Verification image saved: {device_id}/{request.image_name}")
        
        return {
            "success": True,
            "message": "Verification image captured and saved",
            "image_name": request.image_name,
            "device_id": device_id,
            "resolution": f"{screen_width}x{screen_height}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Capture verification image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/images")
async def list_verification_images():
    """
    List all verification images for current device.
    
    Returns list of available verification reference images.
    """
    try:
        # Get current device info
        device_info = adb_tool.get_device_info()
        
        if not device_info.get("connected"):
            return {
                "success": True,
                "device_id": None,
                "images": [],
                "message": "No device connected"
            }
        
        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)
        
        # Get device ID
        verification_service = get_verification_image_service()
        device_id = verification_service.get_device_id(screen_width, screen_height)
        
        # List images
        images = verification_service.list_verification_images(device_id)
        
        return {
            "success": True,
            "device_id": device_id,
            "resolution": f"{screen_width}x{screen_height}",
            "images": images,
            "count": len(images)
        }
        
    except Exception as e:
        logger.error(f"List verification images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/image/{image_name}")
async def get_verification_image(image_name: str):
    """
    Get verification image file.
    
    Returns the actual image file for viewing.
    """
    try:
        # Get current device info
        device_info = adb_tool.get_device_info()
        
        if not device_info.get("connected"):
            raise HTTPException(status_code=400, detail="No device connected")
        
        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)
        
        # Get device ID
        verification_service = get_verification_image_service()
        device_id = verification_service.get_device_id(screen_width, screen_height)
        
        # Get image path
        image_path = verification_service.get_verification_image(image_name, device_id)
        
        if not image_path or not image_path.exists():
            raise HTTPException(status_code=404, detail="Verification image not found")
        
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get verification image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/verification/image/{image_name}")
async def delete_verification_image(image_name: str):
    """Delete verification reference image."""
    try:
        # Get current device info
        device_info = adb_tool.get_device_info()
        
        if not device_info.get("connected"):
            raise HTTPException(status_code=400, detail="No device connected")
        
        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)
        
        # Get device ID
        verification_service = get_verification_image_service()
        device_id = verification_service.get_device_id(screen_width, screen_height)
        
        # Delete image
        success = verification_service.delete_verification_image(image_name, device_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete verification image")
        
        return {
            "success": True,
            "message": f"Verification image '{image_name}' deleted",
            "device_id": device_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete verification image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/devices")
async def list_verification_devices():
    """List all devices that have verification images."""
    try:
        verification_service = get_verification_image_service()
        devices = verification_service.get_all_devices()
        
        return {
            "success": True,
            "devices": devices,
            "count": len(devices)
        }
        
    except Exception as e:
        logger.error(f"List devices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/suggest-name")
async def suggest_verification_name(step_description: str):
    """
    Suggest verification image name based on step description.
    
    Query params:
        step_description: Test step description
    """
    try:
        verification_service = get_verification_image_service()
        suggested = verification_service.suggest_image_name(step_description)
        
        return {
            "success": True,
            "suggested_name": suggested
        }
        
    except Exception as e:
        logger.error(f"Suggest name error: {e}")
        raise HTTPException(status_code=500, detail=str(e))