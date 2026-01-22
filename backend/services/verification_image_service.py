"""
verification_image_service.py - Verification Image Management Service

Manages reference screenshots for SSIM-based verification.
Stores images per device profile dynamically (like device coordinates).
Tracks verification results (success/error) with comparison images.

Structure:
data/verification_images/
    ├── device_1408x792/
    │   ├── app_launcher_opened.png
    │   ├── settings_opened.png
    │   └── bluetooth_settings_opened.png
    └── device_1920x1080/
        └── ...

data/verification_results/
    ├── device_1408x792/
    │   ├── success/
    │   │   ├── {result_id}.json
    │   │   └── {result_id}_comparison.png
    │   └── error/
    │       ├── {result_id}.json
    │       └── {result_id}_comparison.png
"""

import logging
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class VerificationImageService:
    """Service for managing verification reference images per device."""
    
    def __init__(self, base_dir: str = "data/verification_images", results_dir: str = "data/verification_results"):
        """
        Initialize verification image service.

        Args:
            base_dir: Base directory for verification images
            results_dir: Base directory for verification results
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file for image registry
        self.metadata_file = self.base_dir / "metadata.json"
        self.metadata = self._load_metadata()

        # Results index
        self.results_index_file = self.results_dir / "results_index.json"
        self.results_index = self._load_results_index()

        # Initialize results index file if it doesn't exist
        if not self.results_index_file.exists():
            self._save_results_index()

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

    def _load_results_index(self) -> Dict:
        """Load verification results index."""
        if self.results_index_file.exists():
            try:
                with open(self.results_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load results index: {e}")
                return {"success": [], "error": []}
        return {"success": [], "error": []}

    def _save_results_index(self):
        """Save verification results index."""
        try:
            with open(self.results_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.results_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save results index: {e}")
    
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

    # ═══════════════════════════════════════════════════════════
    # Verification Results Management
    # ═══════════════════════════════════════════════════════════

    def save_verification_result(
        self,
        device_id: str,
        test_id: str,
        step_number: int,
        step_description: str,
        ssim_score: float,
        passed: bool,
        reference_image_path: Optional[str] = None,
        actual_image_path: Optional[str] = None,
        comparison_image_path: Optional[str] = None,
        threshold: float = 0.85
    ) -> Optional[str]:
        """
        Save a verification result with optional comparison image.

        Args:
            device_id: Device identifier
            test_id: Test case ID
            step_number: Step number
            step_description: Step description
            ssim_score: SSIM similarity score
            passed: Whether verification passed
            reference_image_path: Path to reference image
            actual_image_path: Path to actual image
            comparison_image_path: Path to comparison image (if generated)
            threshold: SSIM threshold used

        Returns:
            Result ID or None if failed
        """
        try:
            # Convert numpy types to Python native types for JSON serialization
            passed = bool(passed)
            ssim_score = float(ssim_score)
            step_number = int(step_number)
            threshold = float(threshold)

            result_id = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            category = "success" if passed else "error"

            # Create device result folder
            device_result_dir = self.results_dir / device_id / category
            device_result_dir.mkdir(parents=True, exist_ok=True)

            # Result data
            result_data = {
                "result_id": result_id,
                "device_id": device_id,
                "test_id": test_id,
                "step_number": step_number,
                "step_description": step_description,
                "ssim_score": ssim_score,
                "passed": passed,
                "threshold": threshold,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "reference_image": reference_image_path,
                "actual_image": actual_image_path,
                "comparison_image": None
            }

            # Copy comparison image if provided
            if comparison_image_path and Path(comparison_image_path).exists():
                comparison_dest = device_result_dir / f"{result_id}_comparison.png"
                shutil.copy2(comparison_image_path, comparison_dest)
                result_data["comparison_image"] = str(comparison_dest)

            # Save result JSON
            result_file = device_result_dir / f"{result_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2)

            # Update index
            self.results_index[category].insert(0, {
                "result_id": result_id,
                "device_id": device_id,
                "test_id": test_id,
                "step_number": step_number,
                "ssim_score": ssim_score,
                "timestamp": result_data["timestamp"]
            })

            # Keep index manageable (max 1000 per category)
            if len(self.results_index[category]) > 1000:
                self.results_index[category] = self.results_index[category][:1000]

            self._save_results_index()

            logger.info(f"{'✅' if passed else '❌'} Saved verification result: {result_id} (SSIM: {ssim_score:.4f})")
            return result_id

        except Exception as e:
            logger.error(f"Failed to save verification result: {e}")
            return None

    def get_verification_results(
        self,
        category: Optional[str] = None,
        device_id: Optional[str] = None,
        test_id: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        Get verification results with optional filters.

        Args:
            category: 'success' or 'error' or None for both
            device_id: Filter by device
            test_id: Filter by test
            limit: Maximum results per category

        Returns:
            Dict with 'success' and 'error' lists
        """
        results = {"success": [], "error": []}

        categories = [category] if category else ["success", "error"]

        for cat in categories:
            cat_results = self.results_index.get(cat, [])

            # Apply filters
            filtered = cat_results
            if device_id:
                filtered = [r for r in filtered if r.get("device_id") == device_id]
            if test_id:
                filtered = [r for r in filtered if r.get("test_id") == test_id]

            # Limit results
            results[cat] = filtered[:limit]

        return results

    def get_verification_result(self, result_id: str) -> Optional[Dict]:
        """
        Get full details of a specific verification result.

        Args:
            result_id: Result identifier

        Returns:
            Result data or None
        """
        # Search in index for device and category
        for category in ["success", "error"]:
            for entry in self.results_index.get(category, []):
                if entry["result_id"] == result_id:
                    device_id = entry["device_id"]
                    result_file = self.results_dir / device_id / category / f"{result_id}.json"

                    if result_file.exists():
                        try:
                            with open(result_file, 'r', encoding='utf-8') as f:
                                return json.load(f)
                        except Exception as e:
                            logger.error(f"Failed to load result {result_id}: {e}")
                            return None

        return None

    def get_comparison_image_path(self, result_id: str) -> Optional[Path]:
        """
        Get path to comparison image for a result.

        Args:
            result_id: Result identifier

        Returns:
            Path to comparison image or None
        """
        result = self.get_verification_result(result_id)
        if result and result.get("comparison_image"):
            path = Path(result["comparison_image"])
            if path.exists():
                return path
        return None

    def get_results_summary(self, device_id: Optional[str] = None) -> Dict:
        """
        Get summary statistics for verification results.

        Args:
            device_id: Optional device filter

        Returns:
            Summary statistics
        """
        success_list = self.results_index.get("success", [])
        error_list = self.results_index.get("error", [])

        if device_id:
            success_list = [r for r in success_list if r.get("device_id") == device_id]
            error_list = [r for r in error_list if r.get("device_id") == device_id]

        total = len(success_list) + len(error_list)
        success_count = len(success_list)
        error_count = len(error_list)

        # Calculate average SSIM
        all_scores = [r.get("ssim_score", 0) for r in success_list + error_list if r.get("ssim_score")]
        avg_ssim = sum(all_scores) / len(all_scores) if all_scores else 0

        return {
            "total": total,
            "success_count": success_count,
            "error_count": error_count,
            "pass_rate": (success_count / total * 100) if total > 0 else 0,
            "average_ssim": avg_ssim,
            "device_id": device_id
        }

    def delete_verification_result(self, result_id: str) -> bool:
        """
        Delete a verification result.

        Args:
            result_id: Result identifier

        Returns:
            Success boolean
        """
        try:
            # Find in index
            for category in ["success", "error"]:
                for i, entry in enumerate(self.results_index.get(category, [])):
                    if entry["result_id"] == result_id:
                        device_id = entry["device_id"]

                        # Delete files
                        result_file = self.results_dir / device_id / category / f"{result_id}.json"
                        comparison_file = self.results_dir / device_id / category / f"{result_id}_comparison.png"

                        if result_file.exists():
                            result_file.unlink()
                        if comparison_file.exists():
                            comparison_file.unlink()

                        # Remove from index
                        del self.results_index[category][i]
                        self._save_results_index()

                        logger.info(f"Deleted verification result: {result_id}")
                        return True

            return False
        except Exception as e:
            logger.error(f"Failed to delete result {result_id}: {e}")
            return False

    # ═══════════════════════════════════════════════════════════
    # Comparison Images from data/verification_comparisons/
    # ═══════════════════════════════════════════════════════════

    def list_comparison_images(self, limit: int = 50) -> List[Dict]:
        """
        List comparison images from data/verification_comparisons/ folder.

        Args:
            limit: Maximum number of images to return

        Returns:
            List of comparison image info dicts
        """
        try:
            comparisons_dir = Path("data/verification_comparisons")
            if not comparisons_dir.exists():
                return []

            images = []
            for img_path in sorted(comparisons_dir.glob("comparison_*.png"), reverse=True):
                # Parse timestamp from filename: comparison_YYYYMMDD_HHMMSS.png
                filename = img_path.stem  # e.g., comparison_20260120_103533
                parts = filename.split("_")
                if len(parts) >= 3:
                    date_str = parts[1]
                    time_str = parts[2]
                    try:
                        timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        formatted_time = "Unknown"
                else:
                    formatted_time = "Unknown"

                images.append({
                    "filename": img_path.name,
                    "path": str(img_path),
                    "timestamp": formatted_time,
                    "size_kb": round(img_path.stat().st_size / 1024, 1)
                })

                if len(images) >= limit:
                    break

            logger.info(f"Found {len(images)} comparison images")
            return images

        except Exception as e:
            logger.error(f"Failed to list comparison images: {e}")
            return []

    def get_comparison_image_by_filename(self, filename: str) -> Optional[Path]:
        """
        Get path to a comparison image by filename.

        Args:
            filename: Image filename (e.g., comparison_20260120_103533.png)

        Returns:
            Path to image or None
        """
        try:
            comparisons_dir = Path("data/verification_comparisons")
            image_path = comparisons_dir / filename

            if image_path.exists():
                return image_path
            return None

        except Exception as e:
            logger.error(f"Failed to get comparison image: {e}")
            return None

    def delete_comparison_image(self, filename: str) -> bool:
        """
        Delete a comparison image from data/verification_comparisons/.

        Args:
            filename: Image filename

        Returns:
            Success boolean
        """
        try:
            comparisons_dir = Path("data/verification_comparisons")
            image_path = comparisons_dir / filename

            if image_path.exists():
                image_path.unlink()
                logger.info(f"Deleted comparison image: {filename}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete comparison image: {e}")
            return False


# Singleton instance
_verification_image_service: Optional[VerificationImageService] = None


def get_verification_image_service() -> VerificationImageService:
    """Get or create verification image service singleton."""
    global _verification_image_service
    
    if _verification_image_service is None:
        _verification_image_service = VerificationImageService()
    
    return _verification_image_service