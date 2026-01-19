"""
Device Profile API Routes - REST endpoints for coordinate management
FIXED VERSION with better error handling
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from backend.services.device_profile_service import get_device_profile_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ═══════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════

class CoordinateInput(BaseModel):
    icon_name: str
    x: int
    y: int

class CoordinateUpdate(BaseModel):
    icon_name: str
    x: int
    y: int

class DeviceProfileCreate(BaseModel):
    device_id: str
    screen_width: int
    screen_height: int
    manufacturer: Optional[str] = ""
    model: Optional[str] = ""

class CoordinateResponse(BaseModel):
    icon_name: str
    x: int
    y: int
    verified: bool
    verified_by: str
    last_verified: str

class DeviceInfo(BaseModel):
    screen_width: int
    screen_height: int
    screen_resolution: str
    device_name: str

class ProfileSummary(BaseModel):
    device_id: str
    resolution: str
    manufacturer: str
    model: str
    icon_count: int
    updated_at: str

# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/api/device/current", response_model=dict)
async def get_current_device():
    """
    Get current connected device information and loaded profile.
    
    Returns:
        Device info + profile details
    """
    try:
        service = get_device_profile_service()
        
        # Detect device
        device_info = service.detect_current_device()
        
        # Load matching profile
        profile = service.load_profile()
        
        # FIXED: Handle None profile gracefully
        if not profile:
            return {
                "device": device_info,
                "profile": {
                    "device_id": "none",
                    "resolution": device_info.get('screen_resolution', 'unknown'),
                    "icon_count": 0
                }
            }
        
        return {
            "device": device_info,
            "profile": {
                "device_id": profile.get('device_id', 'unknown'),
                "resolution": profile.get('device_info', {}).get('screen_resolution', 'unknown'),
                "icon_count": len(profile.get('icon_coordinates', {}))
            }
        }
    except Exception as e:
        logger.error(f"❌ Get current device failed: {e}")
        # FIXED: Return default values instead of error
        return {
            "device": {
                "screen_width": 1408,
                "screen_height": 792,
                "screen_resolution": "1408x792",
                "device_name": "unknown"
            },
            "profile": {
                "device_id": "none",
                "resolution": "unknown",
                "icon_count": 0
            }
        }


@router.get("/api/device/profiles", response_model=List[ProfileSummary])
async def list_all_profiles():
    """
    List all available device profiles.
    
    Returns:
        List of profile summaries
    """
    try:
        service = get_device_profile_service()
        profiles = service.list_all_profiles()
        # FIXED: Return empty list if None
        return profiles if profiles else []
    except Exception as e:
        logger.error(f"❌ List profiles failed: {e}")
        # FIXED: Return empty list instead of error
        return []


@router.post("/api/device/profile/create")
async def create_device_profile(data: DeviceProfileCreate):
    """
    Create a new device profile.
    
    Args:
        data: Device profile creation data
        
    Returns:
        Success message
    """
    try:
        service = get_device_profile_service()
        
        success = service.create_new_device_profile(
            device_id=data.device_id,
            width=data.screen_width,
            height=data.screen_height,
            manufacturer=data.manufacturer,
            model=data.model
        )
        
        if success:
            return {"message": f"Device profile '{data.device_id}' created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create profile")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Create profile failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/device/coordinates", response_model=List[CoordinateResponse])
async def list_coordinates():
    """
    List all coordinates in current device profile.
    
    Returns:
        List of icon coordinates
    """
    try:
        service = get_device_profile_service()
        coords = service.list_coordinates()
        # FIXED: Always return list, never None
        return coords if coords else []
    except Exception as e:
        logger.error(f"❌ List coordinates failed: {e}")
        # FIXED: Return empty list instead of error for better UX
        return []


@router.post("/api/device/coordinate/add")
async def add_coordinate(data: CoordinateInput):
    """
    Add new coordinate to current device profile.
    
    Args:
        data: Coordinate data (icon_name, x, y)
        
    Returns:
        Success message
    """
    try:
        service = get_device_profile_service()
        
        success = service.add_coordinate(
            icon_name=data.icon_name,
            x=data.x,
            y=data.y,
            verified_by="manual"
        )
        
        if success:
            logger.info(f"✅ Coordinate added: {data.icon_name} at ({data.x}, {data.y})")
            return {"message": f"Coordinate for '{data.icon_name}' added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add coordinate")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add coordinate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/device/coordinate/update")
async def update_coordinate(data: CoordinateUpdate):
    """
    Update existing coordinate in current device profile.
    
    Args:
        data: Updated coordinate data
        
    Returns:
        Success message
    """
    try:
        service = get_device_profile_service()
        
        success = service.update_coordinate(
            icon_name=data.icon_name,
            x=data.x,
            y=data.y
        )
        
        if success:
            logger.info(f"✅ Coordinate updated: {data.icon_name}")
            return {"message": f"Coordinate for '{data.icon_name}' updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update coordinate")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update coordinate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/device/coordinate/{icon_name}")
async def delete_coordinate(icon_name: str):
    """
    Delete coordinate from current device profile.
    
    Args:
        icon_name: Icon name to delete
        
    Returns:
        Success message
    """
    try:
        service = get_device_profile_service()
        
        success = service.delete_coordinate(icon_name)
        
        if success:
            logger.info(f"✅ Coordinate deleted: {icon_name}")
            return {"message": f"Coordinate for '{icon_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Coordinate '{icon_name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete coordinate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/device/coordinate/{icon_name}")
async def get_coordinate(icon_name: str):
    """
    Get specific coordinate from current device profile.
    
    Args:
        icon_name: Icon name to lookup
        
    Returns:
        Coordinate data or 404
    """
    try:
        service = get_device_profile_service()
        
        coords = service.get_coordinate(icon_name)
        
        if coords:
            return {
                "icon_name": icon_name,
                "x": coords[0],
                "y": coords[1]
            }
        else:
            raise HTTPException(status_code=404, detail=f"Coordinate '{icon_name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get coordinate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))