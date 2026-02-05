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
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List

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


class CaptureVerificationImageCroppedRequest(BaseModel):
    """Request to capture cropped verification reference image."""
    image_name: str
    x1: int
    y1: int
    x2: int
    y2: int
    description: Optional[str] = None


class PreviewCropRequest(BaseModel):
    """Request to preview a crop region."""
    x1: int
    y1: int
    x2: int
    y2: int


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


# ═══════════════════════════════════════════════════════════
# Cropped Verification Images (for Partial Image Verification)
# ═══════════════════════════════════════════════════════════

@router.post("/api/verification/capture-cropped")
async def capture_cropped_verification_image(request: CaptureVerificationImageCroppedRequest):
    """
    Capture screenshot, crop to specified region, and save as verification reference.

    Body:
        {
            "image_name": "navigation_bar",
            "x1": 0,
            "y1": 700,
            "x2": 1408,
            "y2": 792,
            "description": "Bottom navigation bar region"
        }
    """
    try:
        logger.info(f"📸 Capturing cropped verification image: {request.image_name}")
        logger.info(f"   Crop region: ({request.x1},{request.y1}) to ({request.x2},{request.y2})")

        # Validate coordinates
        if request.x2 <= request.x1 or request.y2 <= request.y1:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid crop coordinates: x2 must be > x1 and y2 must be > y1"
            )

        # Get current device info
        device_info = adb_tool.get_device_info()

        if not device_info.get("connected"):
            raise HTTPException(status_code=400, detail="No device connected")

        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)

        if screen_width == 0 or screen_height == 0:
            raise HTTPException(status_code=400, detail="Could not determine screen dimensions")

        # Validate crop region is within screen bounds
        if request.x2 > screen_width or request.y2 > screen_height:
            raise HTTPException(
                status_code=400,
                detail=f"Crop region exceeds screen dimensions ({screen_width}x{screen_height})"
            )

        # Get device ID
        verification_service = get_verification_image_service()
        device_id = verification_service.get_device_id(screen_width, screen_height)

        # Capture and crop screenshot
        cropped_path = screenshot_tool.capture_cropped(
            x1=request.x1,
            y1=request.y1,
            x2=request.x2,
            y2=request.y2,
            filename=f"cropped_temp_{request.image_name}.jpg"
        )

        if not cropped_path:
            raise HTTPException(status_code=500, detail="Failed to capture and crop screenshot")

        # Save as cropped verification image with metadata
        crop_coords = {
            "x1": request.x1,
            "y1": request.y1,
            "x2": request.x2,
            "y2": request.y2
        }

        success = verification_service.save_cropped_verification_image(
            screenshot_path=cropped_path,
            image_name=request.image_name,
            device_id=device_id,
            crop_coords=crop_coords,
            description=request.description
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save cropped verification image")

        logger.info(f"✅ Cropped verification image saved: {device_id}/{request.image_name}_cropped")

        return {
            "success": True,
            "message": "Cropped verification image captured and saved",
            "image_name": f"{request.image_name}_cropped",
            "device_id": device_id,
            "resolution": f"{screen_width}x{screen_height}",
            "crop_coords": crop_coords,
            "crop_size": f"{request.x2 - request.x1}x{request.y2 - request.y1}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Capture cropped verification image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/cropped-images")
async def list_cropped_verification_images():
    """
    List all cropped verification images for current device.

    Returns list of cropped verification reference images with coordinates.
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

        # List cropped images
        images = verification_service.list_cropped_images(device_id)

        return {
            "success": True,
            "device_id": device_id,
            "resolution": f"{screen_width}x{screen_height}",
            "images": images,
            "count": len(images)
        }

    except Exception as e:
        logger.error(f"List cropped verification images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/verification/preview-crop")
async def preview_crop_region(request: PreviewCropRequest):
    """
    Preview a crop region from the current screen.

    Captures current screen and returns the cropped region as JPEG.

    Body:
        {
            "x1": 0,
            "y1": 700,
            "x2": 1408,
            "y2": 792
        }
    """
    try:
        logger.info(f"👁️ Previewing crop region: ({request.x1},{request.y1}) to ({request.x2},{request.y2})")

        # Validate coordinates
        if request.x2 <= request.x1 or request.y2 <= request.y1:
            raise HTTPException(
                status_code=400,
                detail="Invalid crop coordinates: x2 must be > x1 and y2 must be > y1"
            )

        # Get current device info
        device_info = adb_tool.get_device_info()

        if not device_info.get("connected"):
            raise HTTPException(status_code=400, detail="No device connected")

        resolution = device_info.get("resolution", {})
        screen_width = resolution.get("width", 0)
        screen_height = resolution.get("height", 0)

        # Validate crop region is within screen bounds
        if request.x2 > screen_width or request.y2 > screen_height:
            raise HTTPException(
                status_code=400,
                detail=f"Crop region exceeds screen dimensions ({screen_width}x{screen_height})"
            )

        # Capture current screenshot
        screenshot_path = screenshot_tool.capture()
        if not screenshot_path:
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")

        # Get crop preview as bytes
        cropped_bytes = screenshot_tool.get_crop_preview(
            screenshot_path,
            request.x1,
            request.y1,
            request.x2,
            request.y2
        )

        if not cropped_bytes:
            raise HTTPException(status_code=500, detail="Failed to create crop preview")

        # Return as JPEG image
        return Response(
            content=cropped_bytes,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "inline; filename=crop_preview.jpg",
                "X-Crop-Width": str(request.x2 - request.x1),
                "X-Crop-Height": str(request.y2 - request.y1)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview crop region error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/cropped-image/{image_name}")
async def get_cropped_verification_image(image_name: str):
    """
    Get cropped verification image file.

    Returns the actual cropped image file for viewing.
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
        image_path = verification_service.get_cropped_verification_image(image_name, device_id)

        if not image_path or not image_path.exists():
            raise HTTPException(status_code=404, detail="Cropped verification image not found")

        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get cropped verification image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/verification/cropped-image/{image_name}")
async def delete_cropped_verification_image(image_name: str):
    """Delete cropped verification reference image."""
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

        # Delete cropped image
        success = verification_service.delete_cropped_image(image_name, device_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete cropped verification image")

        return {
            "success": True,
            "message": f"Cropped verification image '{image_name}' deleted",
            "device_id": device_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete cropped verification image error: {e}")
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


# ═══════════════════════════════════════════════════════════
# Verification Results Endpoints (Success/Error tabs)
# ═══════════════════════════════════════════════════════════

@router.get("/api/verification/results")
async def get_verification_results(
    category: Optional[str] = None,
    device_id: Optional[str] = None,
    test_id: Optional[str] = None,
    limit: int = 50
):
    """
    Get verification results categorized by success/error.

    Query params:
        category: 'success' or 'error' or None for both
        device_id: Filter by device
        test_id: Filter by test
        limit: Max results per category (default 50)

    Returns:
        Dict with 'success' and 'error' lists
    """
    try:
        verification_service = get_verification_image_service()
        results = verification_service.get_verification_results(
            category=category,
            device_id=device_id,
            test_id=test_id,
            limit=limit
        )

        # Get summary stats
        summary = verification_service.get_results_summary(device_id)

        return {
            "success": True,
            "data": {
                "results": results,
                "summary": summary
            }
        }

    except Exception as e:
        logger.error(f"Get verification results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/result/{result_id}")
async def get_verification_result(result_id: str):
    """
    Get full details of a specific verification result.

    Args:
        result_id: Result identifier

    Returns:
        Full result data including comparison image path
    """
    try:
        verification_service = get_verification_image_service()
        result = verification_service.get_verification_result(result_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get verification result error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/comparison/{result_id}")
async def get_comparison_image(result_id: str):
    """
    Get comparison image for a verification result.

    Args:
        result_id: Result identifier

    Returns:
        FileResponse with comparison image
    """
    try:
        verification_service = get_verification_image_service()
        image_path = verification_service.get_comparison_image_path(result_id)

        if not image_path:
            raise HTTPException(status_code=404, detail=f"Comparison image not found for {result_id}")

        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get comparison image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/results/summary")
async def get_results_summary(device_id: Optional[str] = None):
    """
    Get summary statistics for verification results.

    Query params:
        device_id: Optional device filter

    Returns:
        Summary with total, success, error counts and pass rate
    """
    try:
        verification_service = get_verification_image_service()
        summary = verification_service.get_results_summary(device_id)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Get results summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/verification/result/{result_id}")
async def delete_verification_result(result_id: str):
    """
    Delete a verification result.

    Args:
        result_id: Result identifier

    Returns:
        Success confirmation
    """
    try:
        verification_service = get_verification_image_service()
        success = verification_service.delete_verification_result(result_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

        return {
            "success": True,
            "message": f"Result {result_id} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete verification result error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Search Endpoint
# ═══════════════════════════════════════════════════════════

@router.get("/api/verification/search")
async def search_verification_results(
    test_id: Optional[str] = None,
    step: Optional[str] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100
):
    """
    Search verification results with advanced filters.

    Query params:
        test_id: Filter by test ID (partial match, case-insensitive)
        step: Filter by step number or range (e.g., "1", "1-3", "5+")
        category: 'success' or 'failed' or 'error'
        date: Filter by date (YYYY-MM-DD format)
        limit: Max results to return (default 100)

    Returns:
        Filtered list of verification results
    """
    try:
        verification_service = get_verification_image_service()

        # Get all results first
        all_results = verification_service.get_verification_results(
            category=None,  # Get all
            device_id=None,
            test_id=None,
            limit=1000  # Get more for filtering
        )

        # Combine success and error results
        combined_results = []
        if 'success' in all_results:
            combined_results.extend(all_results['success'])
        if 'error' in all_results:
            combined_results.extend(all_results['error'])

        # Apply filters
        filtered_results = combined_results

        # Filter by test_id (partial match, case-insensitive)
        if test_id:
            test_id_lower = test_id.lower()
            filtered_results = [
                r for r in filtered_results
                if r.get('test_id', '').lower().find(test_id_lower) != -1
            ]

        # Filter by step number/range
        if step:
            filtered_results = filter_by_step(filtered_results, step)

        # Filter by category (success/failed)
        if category:
            if category.lower() in ('success', 'passed'):
                filtered_results = [
                    r for r in filtered_results
                    if r.get('ssim_score', 0) >= 0.85
                ]
            elif category.lower() in ('failed', 'error'):
                filtered_results = [
                    r for r in filtered_results
                    if r.get('ssim_score', 0) < 0.85
                ]

        # Filter by date
        if date:
            filtered_results = filter_by_date(filtered_results, date)

        # Sort by timestamp (newest first)
        filtered_results.sort(
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )

        # Apply limit
        filtered_results = filtered_results[:limit]

        logger.info(f"🔍 Search found {len(filtered_results)} results (filters: test_id={test_id}, step={step}, category={category}, date={date})")

        return {
            "success": True,
            "data": {
                "results": filtered_results,
                "count": len(filtered_results),
                "filters": {
                    "test_id": test_id,
                    "step": step,
                    "category": category,
                    "date": date
                }
            }
        }

    except Exception as e:
        logger.error(f"Search verification results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def filter_by_step(results: list, step_filter: str) -> list:
    """
    Filter results by step number or range.

    Supports formats:
        - "1" - exact step 1
        - "1-3" - steps 1 through 3
        - "5+" - steps 5 and above
        - "1,3,5" - steps 1, 3, and 5
    """
    try:
        # Handle range (e.g., "1-3")
        if '-' in step_filter and not step_filter.startswith('-'):
            parts = step_filter.split('-')
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                return [
                    r for r in results
                    if start <= r.get('step_number', 0) <= end
                ]

        # Handle "5+" (5 and above)
        if step_filter.endswith('+'):
            min_step = int(step_filter[:-1].strip())
            return [
                r for r in results
                if r.get('step_number', 0) >= min_step
            ]

        # Handle comma-separated (e.g., "1,3,5")
        if ',' in step_filter:
            steps = [int(s.strip()) for s in step_filter.split(',')]
            return [
                r for r in results
                if r.get('step_number', 0) in steps
            ]

        # Handle single step number
        step_num = int(step_filter.strip())
        return [
            r for r in results
            if r.get('step_number', 0) == step_num
        ]

    except ValueError:
        # If parsing fails, return all results
        return results


def filter_by_date(results: list, date_str: str) -> list:
    """
    Filter results by date (YYYY-MM-DD format).
    """
    try:
        # Parse the filter date
        filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        filtered = []
        for r in results:
            timestamp = r.get('timestamp', '')
            if timestamp:
                try:
                    # Parse ISO timestamp
                    result_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    if result_date == filter_date:
                        filtered.append(r)
                except (ValueError, AttributeError):
                    pass

        return filtered

    except ValueError:
        # If date parsing fails, return all results
        return results


# ═══════════════════════════════════════════════════════════
# Comparison Images Endpoints (from data/verification_comparisons/)
# ═══════════════════════════════════════════════════════════

@router.get("/api/verification/comparisons")
async def list_comparison_images(limit: int = 50):
    """
    List comparison images from data/verification_comparisons/ folder.

    Query params:
        limit: Max images to return (default 50)

    Returns:
        List of comparison image info
    """
    try:
        verification_service = get_verification_image_service()
        images = verification_service.list_comparison_images(limit)

        return {
            "success": True,
            "data": {
                "images": images,
                "count": len(images)
            }
        }

    except Exception as e:
        logger.error(f"List comparison images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/verification/comparisons/{filename}")
async def get_comparison_image_file(filename: str):
    """
    Get a specific comparison image file.

    Args:
        filename: Image filename (e.g., comparison_20260120_103533.png)

    Returns:
        FileResponse with the image
    """
    try:
        verification_service = get_verification_image_service()
        image_path = verification_service.get_comparison_image_by_filename(filename)

        if not image_path:
            raise HTTPException(status_code=404, detail=f"Comparison image not found: {filename}")

        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get comparison image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/verification/comparisons/{filename}")
async def delete_comparison_image_file(filename: str):
    """
    Delete a comparison image.

    Args:
        filename: Image filename

    Returns:
        Success confirmation
    """
    try:
        verification_service = get_verification_image_service()
        success = verification_service.delete_comparison_image(filename)

        if not success:
            raise HTTPException(status_code=404, detail=f"Comparison image not found: {filename}")

        return {
            "success": True,
            "message": f"Comparison image {filename} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete comparison image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))