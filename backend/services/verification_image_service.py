"""
verification_image_service.py - Verification Image Management Service

Manages reference screenshots for SSIM-based verification.
Stores images per device profile dynamically (like device coordinates).

Structure:
data/verification_images/
    ├── device_1408x792/
    │   ├── app_launcher_opened.png
    │   ├── settings_opened.png
    │   └── bluetooth_settings_opened.png
    └── device_1920x1080/
        └── ...
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class VerificationImageService:
    """Service for managing verification reference images per device."""
    
    def __init__(self, base_dir: str = "data/verification_images"):
        """
        Initialize verification image service.
        
        Args:
            base_dir: Base directory for verification images
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file for image registry
        self.metadata_file = self.base_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"✅ Verification Image Service initialized - Base: {self.base_dir}")
    
    def _load_metadata(self) -> Dict:
        """Load metadata registry."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """Save metadata registry."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def get_device_id(self, screen_width: int, screen_height: int) -> str:
        """
        Get device identifier from screen dimensions.
        
        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            
        Returns:
            Device identifier string (e.g., "device_1408x792")
        """
        return f"device_{screen_width}x{screen_height}"
    
    def get_device_folder(self, device_id: str) -> Path:
        """
        Get device-specific folder path.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Path to device folder
        """
        folder = self.base_dir / device_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    
    def save_verification_image(
        self,
        screenshot_path: str,
        image_name: str,
        device_id: str,
        description: Optional[str] = None
    ) -> bool:
        """
        Save verification reference image for a device.
        
        Args:
            screenshot_path: Path to screenshot to save as reference
            image_name: Name for the reference image (e.g., "app_launcher_opened")
            device_id: Device identifier
            description: Optional description
            
        Returns:
            Success boolean
        """
        try:
            # Get device folder
            device_folder = self.get_device_folder(device_id)
            
            # Clean image name (remove special chars, add .png)
            clean_name = self._clean_image_name(image_name)
            
            # Destination path
            dest_path = device_folder / clean_name
            
            # Copy image
            shutil.copy2(screenshot_path, dest_path)
            
            # Update metadata
            if device_id not in self.metadata:
                self.metadata[device_id] = {}
            
            self.metadata[device_id][clean_name] = {
                "original_name": image_name,
                "clean_name": clean_name,
                "description": description or "",
                "created_at": datetime.now().isoformat(),
                "source_path": screenshot_path
            }
            
            self._save_metadata()
            
            logger.info(f"✅ Saved verification image: {device_id}/{clean_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save verification image: {e}")
            return False
    
    def get_verification_image(
        self,
        image_name: str,
        device_id: str
    ) -> Optional[Path]:
        """
        Get verification reference image path.
        
        Args:
            image_name: Name of reference image
            device_id: Device identifier
            
        Returns:
            Path to image or None if not found
        """
        try:
            device_folder = self.get_device_folder(device_id)
            clean_name = self._clean_image_name(image_name)
            image_path = device_folder / clean_name
            
            if image_path.exists():
                logger.info(f"✅ Found verification image: {device_id}/{clean_name}")
                return image_path
            else:
                logger.warning(f"⚠️ Verification image not found: {device_id}/{clean_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get verification image: {e}")
            return None
    
    def list_verification_images(self, device_id: str) -> List[Dict]:
        """
        List all verification images for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of image metadata dictionaries
        """
        try:
            if device_id not in self.metadata:
                return []
            
            images = []
            for clean_name, meta in self.metadata[device_id].items():
                image_path = self.get_device_folder(device_id) / clean_name
                if image_path.exists():
                    images.append({
                        "name": meta["original_name"],
                        "clean_name": clean_name,
                        "description": meta.get("description", ""),
                        "created_at": meta.get("created_at", ""),
                        "path": str(image_path)
                    })
            
            logger.info(f"📋 Found {len(images)} verification images for {device_id}")
            return images
            
        except Exception as e:
            logger.error(f"Failed to list verification images: {e}")
            return []
    
    def delete_verification_image(
        self,
        image_name: str,
        device_id: str
    ) -> bool:
        """
        Delete verification reference image.
        
        Args:
            image_name: Name of image to delete
            device_id: Device identifier
            
        Returns:
            Success boolean
        """
        try:
            device_folder = self.get_device_folder(device_id)
            clean_name = self._clean_image_name(image_name)
            image_path = device_folder / clean_name
            
            # Delete file
            if image_path.exists():
                image_path.unlink()
            
            # Update metadata
            if device_id in self.metadata and clean_name in self.metadata[device_id]:
                del self.metadata[device_id][clean_name]
                self._save_metadata()
            
            logger.info(f"🗑️ Deleted verification image: {device_id}/{clean_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete verification image: {e}")
            return False
    
    def get_all_devices(self) -> List[str]:
        """
        Get list of all devices with verification images.
        
        Returns:
            List of device identifiers
        """
        return list(self.metadata.keys())
    
    def _clean_image_name(self, name: str) -> str:
        """
        Clean image name (remove special characters, ensure .png extension).
        
        Args:
            name: Original name
            
        Returns:
            Cleaned name with .png extension
        """
        # Remove special characters, keep alphanumeric and underscores
        clean = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in name)
        
        # Convert to lowercase
        clean = clean.lower()
        
        # Remove consecutive underscores
        while '__' in clean:
            clean = clean.replace('__', '_')
        
        # Ensure .png extension
        if not clean.endswith('.png'):
            clean += '.png'
        
        return clean
    
    def suggest_image_name(self, step_description: str) -> str:
        """
        Suggest image name based on step description.
        
        Args:
            step_description: Test step description
            
        Returns:
            Suggested image name
        """
        # Extract key words
        desc_lower = step_description.lower()
        
        # Common patterns
        if 'open' in desc_lower or 'launch' in desc_lower:
            if 'app launcher' in desc_lower:
                return "app_launcher_opened"
            elif 'settings' in desc_lower:
                return "settings_opened"
            elif 'bluetooth' in desc_lower:
                return "bluetooth_opened"
        
        # Default: use first few words
        words = desc_lower.split()[:3]
        suggested = "_".join(words)
        return self._clean_image_name(suggested)


# Singleton instance
_verification_image_service: Optional[VerificationImageService] = None


def get_verification_image_service() -> VerificationImageService:
    """Get or create verification image service singleton."""
    global _verification_image_service
    
    if _verification_image_service is None:
        _verification_image_service = VerificationImageService()
    
    return _verification_image_service