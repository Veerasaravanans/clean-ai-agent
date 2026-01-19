"""
Device Profile Service - Manages device-specific coordinate profiles
FIXED VERSION - Consistent filename format (no more recreating files)
"""
import json
import os
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceProfileService:
    def __init__(self):
        # Store in project data/ folder
        self.profiles_dir = Path("./data/device-profiles").resolve()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self._current_profile = None
        self._current_device_info = None
        
        logger.info(f"✅ Device profiles directory: {self.profiles_dir}")
        
        # Initialize default files if not exist
        self._init_default_files()
    
    def _init_default_files(self):
        """Initialize default profile files if they don't exist"""
        schema_path = self.profiles_dir / "profile_schema.json"
        catalog_path = self.profiles_dir / "device_catalog.json"
        default_path = self.profiles_dir / "default_1200x1754.json"
        
        # Copy from /home/claude if not exist
        source_dir = Path("/home/claude/device-profiles")
        
        if source_dir.exists():
            for filename in ["profile_schema.json", "device_catalog.json", "default_1200x1754.json"]:
                src = source_dir / filename
                dst = self.profiles_dir / filename
                if src.exists() and not dst.exists():
                    import shutil
                    shutil.copy(src, dst)
                    logger.info(f"✅ Initialized {filename}")
    
    def detect_current_device(self) -> Dict:
        """
        Detect current device from ADB and match to profile.
        
        Returns:
            Device info dict with screen resolution and device details
        """
        try:
            from backend.tools.adb_tool import ADBTool
            adb = ADBTool()
            
            # Use get_screen_dimensions() not get_screen_size()
            screen_size = adb.get_screen_dimensions()
            
            # Check if screen_size is valid
            if not screen_size or len(screen_size) != 2:
                raise ValueError("Invalid screen dimensions")
            
            width, height = screen_size
            
            # Get device name
            device_name = adb.get_device_name() if hasattr(adb, 'get_device_name') else "unknown"
            
            device_info = {
                "screen_width": width,
                "screen_height": height,
                "screen_resolution": f"{width}x{height}",
                "device_name": device_name
            }
            
            self._current_device_info = device_info
            logger.info(f"📱 Detected device: {device_info['screen_resolution']}")
            
            return device_info
            
        except Exception as e:
            logger.error(f"❌ Device detection failed: {e}")
            # Return fallback device info
            fallback_info = {
                "screen_width": 1408,
                "screen_height": 792,
                "screen_resolution": "1408x792",
                "device_name": "unknown"
            }
            self._current_device_info = fallback_info
            return fallback_info
    
    def load_profile(self, device_id: Optional[str] = None) -> Dict:
        """
        Load device profile from JSON file.
        
        Args:
            device_id: Specific device ID or None for auto-detect
            
        Returns:
            Profile dict
        """
        try:
            if device_id:
                profile_file = self.profiles_dir / f"{device_id}.json"
            else:
                # Auto-detect
                device_info = self._current_device_info or self.detect_current_device()
                profile_file = self._find_matching_profile(device_info)
            
            if not profile_file.exists():
                logger.warning(f"⚠️ Profile not found: {profile_file.name}, creating default")
                # Create default profile if not exists
                return self._create_default_profile_for_device(device_info)
            
            with open(profile_file, 'r') as f:
                profile = json.load(f)
            
            # Ensure icon_coordinates exists
            if 'icon_coordinates' not in profile:
                profile['icon_coordinates'] = {}
            
            self._current_profile = profile
            logger.info(f"✅ Loaded existing profile: {profile['device_id']}")
            logger.info(f"📂 From: {profile_file}")
            logger.info(f"📊 Coordinates: {len(profile.get('icon_coordinates', {}))}")
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Failed to load profile: {e}")
            # Return valid empty profile instead of crashing
            device_info = self._current_device_info or self.detect_current_device()
            return self._create_default_profile_for_device(device_info)
    
    def _create_default_profile_for_device(self, device_info: Dict) -> Dict:
        """Create and save default profile for detected device"""
        # CRITICAL FIX: Use consistent filename format (underscores, not 'x')
        device_id = f"default_{device_info['screen_resolution'].replace('x', '_')}"
        
        profile = {
            "device_id": device_id,
            "device_info": {
                "manufacturer": "",
                "model": "",
                "screen_resolution": device_info['screen_resolution'],
                "android_version": "",
                "description": f"Auto-created profile for {device_info['screen_resolution']}"
            },
            "detection_rules": {
                "screen_width": device_info['screen_width'],
                "screen_height": device_info['screen_height'],
                "device_name_pattern": ".*"
            },
            "icon_coordinates": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save to file
        try:
            profile_path = self.profiles_dir / f"{device_id}.json"
            with open(profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            logger.info(f"✅ Created NEW profile: {device_id}")
            logger.info(f"📂 Saved to: {profile_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save default profile: {e}")
        
        self._current_profile = profile
        return profile
    
    def _find_matching_profile(self, device_info: Dict) -> Path:
        """Find profile matching device info from catalog"""
        try:
            catalog_path = self.profiles_dir / "device_catalog.json"
            
            if not catalog_path.exists():
                # CRITICAL FIX: Use underscore format to match _create_default_profile_for_device
                resolution = device_info['screen_resolution'].replace('x', '_')
                return self.profiles_dir / f"default_{resolution}.json"
            
            with open(catalog_path, 'r') as f:
                catalog = json.load(f)
            
            # Match by screen resolution
            for device in catalog['devices']:
                conditions = device['match_conditions']
                if (conditions['screen_width'] == device_info['screen_width'] and 
                    conditions['screen_height'] == device_info['screen_height']):
                    return self.profiles_dir / device['profile_file']
            
            # Fallback
            return self.profiles_dir / catalog.get('fallback_profile', 'default_1200x1754.json')
            
        except Exception as e:
            logger.error(f"❌ Catalog matching failed: {e}")
            # CRITICAL FIX: Use underscore format here too
            resolution = device_info['screen_resolution'].replace('x', '_')
            return self.profiles_dir / f"default_{resolution}.json"
    
    def get_coordinate(self, icon_name: str) -> Optional[Tuple[int, int]]:
        """
        Get coordinates for specific icon.
        
        Args:
            icon_name: Icon name (normalized)
            
        Returns:
            (x, y) tuple or None
        """
        # Check if profile is None
        if not self._current_profile:
            self.load_profile()
        
        # Handle None profile after loading
        if not self._current_profile:
            logger.warning("⚠️ No profile loaded")
            return None
        
        icon_coords = self._current_profile.get('icon_coordinates', {})
        
        # Check if icon_coords is None
        if not icon_coords:
            return None
        
        # Normalize icon name
        normalized_name = self._normalize_icon_name(icon_name)
        
        # Direct match
        if normalized_name in icon_coords:
            coord = icon_coords[normalized_name]
            logger.info(f"✅ Found coordinate for '{icon_name}': ({coord['x']}, {coord['y']})")
            return (coord['x'], coord['y'])
        
        # Fuzzy match
        for key in icon_coords.keys():
            if self._fuzzy_match(normalized_name, key):
                coord = icon_coords[key]
                logger.info(f"✅ Fuzzy matched '{icon_name}' → '{key}': ({coord['x']}, {coord['y']})")
                return (coord['x'], coord['y'])
        
        logger.warning(f"⚠️ No coordinate found for '{icon_name}'")
        return None
    
    def add_coordinate(self, icon_name: str, x: int, y: int, verified_by: str = "manual") -> bool:
        """
        Add new coordinate to current profile.
        
        Args:
            icon_name: Icon identifier
            x, y: Coordinates
            verified_by: Source of verification
            
        Returns:
            Success boolean
        """
        try:
            # Ensure profile is loaded
            if not self._current_profile:
                self.load_profile()
            
            # Check if profile is still None after loading
            if not self._current_profile:
                logger.error("❌ Cannot add coordinate - no profile loaded")
                return False
            
            normalized_name = self._normalize_icon_name(icon_name)
            
            # Update in memory
            if 'icon_coordinates' not in self._current_profile:
                self._current_profile['icon_coordinates'] = {}
            
            self._current_profile['icon_coordinates'][normalized_name] = {
                "x": x,
                "y": y,
                "alternatives": [],
                "location_hint": "",
                "verified": True,
                "verified_by": verified_by,
                "last_verified": datetime.now().isoformat()
            }
            
            self._current_profile['updated_at'] = datetime.now().isoformat()
            
            # Save to file
            self._save_current_profile()
            
            logger.info(f"✅ Added coordinate for '{icon_name}': ({x}, {y})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add coordinate: {e}")
            return False
    
    def update_coordinate(self, icon_name: str, x: int, y: int) -> bool:
        """Update existing coordinate"""
        return self.add_coordinate(icon_name, x, y, verified_by="update")
    
    def delete_coordinate(self, icon_name: str) -> bool:
        """Remove coordinate from profile"""
        try:
            # Check profile loaded
            if not self._current_profile:
                self.load_profile()
            
            if not self._current_profile:
                return False
            
            normalized_name = self._normalize_icon_name(icon_name)
            
            icon_coords = self._current_profile.get('icon_coordinates', {})
            
            if icon_coords and normalized_name in icon_coords:
                del self._current_profile['icon_coordinates'][normalized_name]
                self._save_current_profile()
                logger.info(f"✅ Deleted coordinate for '{icon_name}'")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete coordinate: {e}")
            return False
    
    def list_coordinates(self) -> List[Dict]:
        """
        List all coordinates in current profile.
        
        Returns:
            List of dicts with icon info
        """
        # Check profile loaded
        if not self._current_profile:
            self.load_profile()
        
        # Return empty list if still no profile
        if not self._current_profile:
            logger.warning("⚠️ No profile loaded, returning empty list")
            return []
        
        coords = []
        icon_coords = self._current_profile.get('icon_coordinates', {})
        
        # Check if icon_coords is None
        if not icon_coords:
            return []
        
        for name, data in icon_coords.items():
            coords.append({
                "icon_name": name,
                "x": data['x'],
                "y": data['y'],
                "verified": data.get('verified', False),
                "verified_by": data.get('verified_by', 'unknown'),
                "last_verified": data.get('last_verified', '')
            })
        
        return coords
    
    def create_new_device_profile(self, device_id: str, width: int, height: int, 
                                   manufacturer: str = "", model: str = "") -> bool:
        """
        Create new device profile.
        
        Args:
            device_id: Unique device identifier
            width, height: Screen dimensions
            manufacturer, model: Device info
            
        Returns:
            Success boolean
        """
        try:
            profile = {
                "device_id": device_id,
                "device_info": {
                    "manufacturer": manufacturer,
                    "model": model,
                    "screen_resolution": f"{width}x{height}",
                    "android_version": "",
                    "description": f"Custom profile for {device_id}"
                },
                "detection_rules": {
                    "screen_width": width,
                    "screen_height": height,
                    "device_name_pattern": ".*"
                },
                "icon_coordinates": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save new profile
            profile_path = self.profiles_dir / f"{device_id}.json"
            with open(profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            # Add to catalog
            self._add_to_catalog(device_id, width, height)
            
            logger.info(f"✅ Created new device profile: {device_id}")
            logger.info(f"📂 Saved to: {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create profile: {e}")
            return False
    
    def list_all_profiles(self) -> List[Dict]:
        """List all available device profiles"""
        profiles = []
        
        for profile_file in self.profiles_dir.glob("*.json"):
            if profile_file.name in ['profile_schema.json', 'device_catalog.json']:
                continue
            
            try:
                with open(profile_file, 'r') as f:
                    profile = json.load(f)
                
                profiles.append({
                    "device_id": profile['device_id'],
                    "resolution": profile['device_info']['screen_resolution'],
                    "manufacturer": profile['device_info'].get('manufacturer', ''),
                    "model": profile['device_info'].get('model', ''),
                    "icon_count": len(profile.get('icon_coordinates', {})),
                    "updated_at": profile.get('updated_at', '')
                })
            except Exception as e:
                logger.warning(f"⚠️ Could not load {profile_file.name}: {e}")
        
        return profiles
    
    def _save_current_profile(self):
        """Save current profile to disk"""
        # Check if profile exists
        if not self._current_profile:
            logger.warning("⚠️ No profile to save")
            return
        
        try:
            device_id = self._current_profile['device_id']
            profile_path = self.profiles_dir / f"{device_id}.json"
            
            with open(profile_path, 'w') as f:
                json.dump(self._current_profile, f, indent=2)
            
            logger.debug(f"💾 Saved profile: {device_id}")
            logger.debug(f"📂 Location: {profile_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save profile: {e}")
    
    def _add_to_catalog(self, device_id: str, width: int, height: int):
        """Add new device to catalog"""
        try:
            catalog_path = self.profiles_dir / "device_catalog.json"
            
            # Check if catalog exists
            if not catalog_path.exists():
                # Create new catalog
                catalog = {
                    "devices": [],
                    "fallback_profile": "default_1200x1754.json"
                }
            else:
                with open(catalog_path, 'r') as f:
                    catalog = json.load(f)
            
            # Check if already exists
            for device in catalog['devices']:
                if device['profile_file'] == f"{device_id}.json":
                    return
            
            # Add new entry
            catalog['devices'].append({
                "profile_file": f"{device_id}.json",
                "priority": len(catalog['devices']) + 1,
                "match_conditions": {
                    "screen_width": width,
                    "screen_height": height
                }
            })
            
            with open(catalog_path, 'w') as f:
                json.dump(catalog, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to update catalog: {e}")
    
    def _normalize_icon_name(self, name: str) -> str:
        """Normalize icon name for consistent lookup"""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    def _fuzzy_match(self, query: str, target: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy string matching"""
        # Exact match
        if query == target:
            return True
        
        # Contains match
        if query in target or target in query:
            return True
        
        # Similarity score (simple character overlap)
        common = set(query) & set(target)
        similarity = len(common) / max(len(query), len(target))
        
        return similarity >= threshold
    
    def _create_empty_profile(self) -> Dict:
        """Create empty profile as fallback"""
        device_info = self._current_device_info or self.detect_current_device()
        
        return {
            "device_id": "unknown",
            "device_info": {
                "screen_resolution": device_info['screen_resolution']
            },
            "detection_rules": {
                "screen_width": device_info['screen_width'],
                "screen_height": device_info['screen_height']
            },
            "icon_coordinates": {}
        }


# Global instance
_service_instance = None

def get_device_profile_service() -> DeviceProfileService:
    """Get singleton device profile service"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DeviceProfileService()
        logger.info("✅ Device profile service initialized")
    return _service_instance