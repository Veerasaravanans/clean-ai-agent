"""
Device Coordinate Tool - Interface to device profile service
Retrieves stored icon coordinates from device profiles
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DeviceCoordinateTool:
    """Tool for retrieving stored icon coordinates from device profiles."""
    
    def __init__(self):
        """Initialize device coordinate tool."""
        self.initialized = True
        logger.info("✅ Device Coordinate Tool initialized")
    
    def find_icon_coordinates(self, icon_name: str) -> Optional[Tuple[int, int]]:
        """
        Find stored coordinates for an icon.
        
        Args:
            icon_name: Name/description of icon
            
        Returns:
            (x, y) tuple or None if not found
        """
        try:
            from backend.services.device_profile_service import get_device_profile_service
            
            profile_service = get_device_profile_service()
            coords = profile_service.get_coordinate(icon_name)
            
            if coords:
                logger.info(f"📍 Retrieved from profile: '{icon_name}' → {coords}")
                return coords
            else:
                logger.debug(f"⚠️ Not in profile: '{icon_name}'")
                return None
        
        except Exception as e:
            logger.error(f"❌ Profile lookup failed: {e}")
            return None
    
    def save_icon_coordinates(
        self,
        icon_name: str,
        x: int,
        y: int,
        verified_by: str = "auto"
    ) -> bool:
        """
        Save icon coordinates to device profile.
        
        Args:
            icon_name: Name/description of icon
            x, y: Coordinates
            verified_by: Source of verification
            
        Returns:
            Success boolean
        """
        try:
            from backend.services.device_profile_service import get_device_profile_service
            
            profile_service = get_device_profile_service()
            success = profile_service.add_coordinate(
                icon_name=icon_name,
                x=x,
                y=y,
                verified_by=verified_by
            )
            
            if success:
                logger.info(f"💾 Saved to profile: '{icon_name}' at ({x}, {y})")
            else:
                logger.warning(f"⚠️ Failed to save: '{icon_name}'")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Profile save failed: {e}")
            return False
    
    def update_icon_coordinates(
        self,
        icon_name: str,
        x: int,
        y: int
    ) -> bool:
        """
        Update existing icon coordinates.
        
        Args:
            icon_name: Name/description of icon
            x, y: New coordinates
            
        Returns:
            Success boolean
        """
        try:
            from backend.services.device_profile_service import get_device_profile_service
            
            profile_service = get_device_profile_service()
            success = profile_service.update_coordinate(
                icon_name=icon_name,
                x=x,
                y=y
            )
            
            if success:
                logger.info(f"🔄 Updated in profile: '{icon_name}' to ({x}, {y})")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Profile update failed: {e}")
            return False
    
    def delete_icon_coordinates(self, icon_name: str) -> bool:
        """
        Delete icon coordinates from profile.
        
        Args:
            icon_name: Name/description of icon
            
        Returns:
            Success boolean
        """
        try:
            from backend.services.device_profile_service import get_device_profile_service
            
            profile_service = get_device_profile_service()
            success = profile_service.delete_coordinate(icon_name)
            
            if success:
                logger.info(f"🗑️ Deleted from profile: '{icon_name}'")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Profile delete failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════════════════════════

_device_coordinate_tool: Optional[DeviceCoordinateTool] = None


def get_device_coordinate_tool() -> DeviceCoordinateTool:
    """Get or create device coordinate tool singleton."""
    global _device_coordinate_tool
    
    if _device_coordinate_tool is None:
        _device_coordinate_tool = DeviceCoordinateTool()
    
    return _device_coordinate_tool