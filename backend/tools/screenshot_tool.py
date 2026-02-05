"""
screenshot_tool.py - Screenshot Capture Tool
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from PIL import Image
import io
import tempfile

from backend.config import settings

logger = logging.getLogger(__name__)


class ScreenshotTool:
    """Screenshot capture and management."""
    
    def __init__(self, device_serial: Optional[str] = None):
        """Initialize screenshot tool."""
        self.device_serial = device_serial or settings.adb_device_serial
        self.screenshot_dir = Path(settings.screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        self.quality = settings.screenshot_quality
        self.max_width = settings.screenshot_max_width
        self.stream_quality = settings.stream_quality
        self.stream_max_width = settings.stream_max_width
        
        logger.info("Screenshot Tool initialized")
    
    def _get_adb_cmd(self) -> list:
        """Get base ADB command."""
        cmd = ["adb"]
        if self.device_serial and self.device_serial != "auto":
            cmd.extend(["-s", self.device_serial])
        return cmd
    
    def capture(self, filename: Optional[str] = None, retry_count: int = 3) -> Optional[str]:
        """
        Capture screenshot at FULL device resolution for vision analysis.
        
        Args:
            filename: Optional filename
            retry_count: Number of retries on failure
            
        Returns:
            Path to saved screenshot or None
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.jpg"
        
        filepath = self.screenshot_dir / filename
        
        # Retry loop for reliability
        for attempt in range(retry_count):
            try:
                # Clean device file before capture
                self._cleanup_device_screenshot()
                
                # Small delay to ensure device is ready
                if attempt > 0:
                    time.sleep(0.3 * attempt)  # Exponential backoff
                
                # Get full resolution bytes (NO resize for vision)
                raw_data = self._capture_full_resolution()
                if not raw_data or len(raw_data) < 1000:
                    if attempt < retry_count - 1:
                        logger.warning(f"Capture attempt {attempt + 1}/{retry_count} failed (insufficient data), retrying...")
                        continue
                    logger.error("All capture attempts failed - insufficient data")
                    return None
                
                # Save to file
                with open(filepath, 'wb') as f:
                    f.write(raw_data)
                
                # Verify saved file is valid
                try:
                    img = Image.open(filepath)
                    img.verify()  # Check if valid image
                    # Reopen to get size (verify() closes the file)
                    img = Image.open(filepath)
                    width, height = img.size
                    if width < 100 or height < 100:
                        raise ValueError(f"Image too small: {width}x{height}")
                    
                    logger.info(f"Screenshot saved: {filepath} ({width}x{height})")
                    return str(filepath)
                    
                except Exception as verify_error:
                    logger.error(f"Saved file validation failed: {verify_error}")
                    if attempt < retry_count - 1:
                        logger.warning(f"Retrying capture (attempt {attempt + 2}/{retry_count})...")
                        # Delete invalid file
                        try:
                            Path(filepath).unlink(missing_ok=True)
                        except:
                            pass
                        continue
                    return None
                    
            except Exception as e:
                logger.error(f"Screenshot capture error (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    continue
                return None
        
        return None
    
    def _cleanup_device_screenshot(self):
        """Clean up device screenshot file before capture."""
        try:
            cmd_base = self._get_adb_cmd()
            subprocess.run(
                cmd_base + ["shell", "rm", "-f", "/sdcard/screen.png"],
                capture_output=True,
                timeout=1
            )
        except:
            pass
    
    def _capture_full_resolution(self) -> Optional[bytes]:
        """
        Capture screenshot at FULL device resolution.
        NO RESIZE - preserves exact coordinates for vision analysis.
        """
        try:
            cmd_base = self._get_adb_cmd()
            
            # Create temp file on host
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_local = tmp.name
            
            try:
                # Direct pull (most reliable for emulators)
                device_path = "/sdcard/screen.png"
                
                # Capture to device
                subprocess.run(
                    cmd_base + ["shell", "screencap", "-p", device_path],
                    capture_output=True,
                    timeout=2
                )
                
                # Pull to local temp file
                result = subprocess.run(
                    cmd_base + ["pull", device_path, temp_local],
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode != 0:
                    logger.debug("Pull method failed, trying exec-out")
                    # Fallback: exec-out
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=2
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        with open(temp_local, 'wb') as f:
                            f.write(result.stdout)
                    else:
                        return None
                
                # Read PNG file
                with open(temp_local, 'rb') as f:
                    png_data = f.read()
                
                if len(png_data) < 100:
                    logger.error("PNG data too small, retrying with exec-out")
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=3
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        png_data = result.stdout
                    else:
                        logger.error("Both methods produced insufficient data")
                        return None
                
                # Validate PNG header
                if not png_data.startswith(b'\x89PNG'):
                    logger.error(f"Invalid PNG header: {png_data[:10]}")
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=3
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        png_data = result.stdout
                        if not png_data.startswith(b'\x89PNG'):
                            logger.error("PNG validation failed on all methods")
                            return None
                    else:
                        return None
                
                # Process PNG → JPEG at FULL resolution
                try:
                    img = Image.open(io.BytesIO(png_data))
                except Exception as e:
                    logger.error(f"PIL failed to open PNG: {e}")
                    return None
                
                # Convert RGBA to RGB (JPEG doesn't support alpha)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # NO RESIZE - keep full device resolution for vision analysis
                # Vision tool needs exact coordinates matching device screen
                
                # Convert to JPEG bytes at full resolution
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=self.quality, optimize=True)
                
                return buffer.getvalue()
                
            finally:
                # Cleanup
                try:
                    Path(temp_local).unlink(missing_ok=True)
                    subprocess.run(
                        cmd_base + ["shell", "rm", "-f", device_path],
                        capture_output=True,
                        timeout=1
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Capture error: {e}")
            return None
    
    def capture_raw(self) -> Optional[bytes]:
        """
        Capture screenshot for streaming UI display.
        RESIZES to stream_max_width for efficient transmission.
        """
        try:
            cmd_base = self._get_adb_cmd()
            
            # Create temp file on host
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_local = tmp.name
            
            try:
                # Direct pull (most reliable for emulators)
                device_path = "/sdcard/screen.png"
                
                # Capture to device
                subprocess.run(
                    cmd_base + ["shell", "screencap", "-p", device_path],
                    capture_output=True,
                    timeout=2
                )
                
                # Pull to local temp file
                result = subprocess.run(
                    cmd_base + ["pull", device_path, temp_local],
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode != 0:
                    logger.debug("Pull method failed, trying exec-out")
                    # Fallback: exec-out
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=2
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        with open(temp_local, 'wb') as f:
                            f.write(result.stdout)
                    else:
                        return None
                
                # Read PNG file
                with open(temp_local, 'rb') as f:
                    png_data = f.read()
                
                if len(png_data) < 100:
                    logger.error("PNG data too small (raw), retrying exec-out")
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=3
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        png_data = result.stdout
                    else:
                        return None
                
                # Validate PNG header
                if not png_data.startswith(b'\x89PNG'):
                    logger.error("Invalid PNG header (raw), retrying")
                    result = subprocess.run(
                        cmd_base + ["exec-out", "screencap", "-p"],
                        capture_output=True,
                        timeout=3
                    )
                    if result.returncode == 0 and len(result.stdout) > 100:
                        png_data = result.stdout
                        if not png_data.startswith(b'\x89PNG'):
                            return None
                    else:
                        return None
                
                # Process PNG → JPEG
                try:
                    img = Image.open(io.BytesIO(png_data))
                except Exception as e:
                    logger.error(f"PIL failed (raw): {e}")
                    return None
                
                # Convert RGBA to RGB (JPEG doesn't support alpha)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # RESIZE for streaming (efficient transmission)
                # Dynamically scales based on device width
                if img.width > self.stream_max_width:
                    ratio = self.stream_max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((self.stream_max_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Resized for streaming: {img.width}×{img.height}")
                
                # Convert to JPEG bytes
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=self.stream_quality, optimize=True)
                
                return buffer.getvalue()
                
            finally:
                # Cleanup
                try:
                    Path(temp_local).unlink(missing_ok=True)
                    subprocess.run(
                        cmd_base + ["shell", "rm", "-f", device_path],
                        capture_output=True,
                        timeout=1
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Capture error: {e}")
            return None
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        try:
            cmd = self._get_adb_cmd() + ["shell", "wm", "size"]
            result = subprocess.run(cmd, capture_output=True, timeout=2, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Physical size:' in line or 'Override size:' in line:
                        size_str = line.split(':')[1].strip()
                        w, h = size_str.split('x')
                        return (int(w), int(h))
            
        except Exception as e:
            logger.error(f"Get dimensions error: {e}")
        
        return (1080, 1920)
    
    def cleanup_old_screenshots(self, keep_last: int = 50):
        """Delete old screenshots."""
        try:
            screenshots = sorted(
                self.screenshot_dir.glob("screenshot_*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for screenshot in screenshots[keep_last:]:
                screenshot.unlink()

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    # ═══════════════════════════════════════════════════════════
    # CROPPING METHODS (for Partial Image Verification)
    # ═══════════════════════════════════════════════════════════

    def capture_cropped(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Capture screenshot and crop to specified region in one operation.

        Args:
            x1: Left edge coordinate
            y1: Top edge coordinate
            x2: Right edge coordinate
            y2: Bottom edge coordinate
            filename: Optional output filename

        Returns:
            Path to cropped image or None
        """
        # First capture full screenshot
        full_screenshot = self.capture()
        if not full_screenshot:
            logger.error("Failed to capture screenshot for cropping")
            return None

        # Then crop it
        return self.crop_existing(full_screenshot, x1, y1, x2, y2, filename)

    def crop_existing(
        self,
        screenshot_path: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        output_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Crop an existing screenshot to specified region.

        Args:
            screenshot_path: Path to existing screenshot
            x1: Left edge coordinate
            y1: Top edge coordinate
            x2: Right edge coordinate
            y2: Bottom edge coordinate
            output_filename: Optional output filename

        Returns:
            Path to cropped image or None
        """
        try:
            # Validate coordinates
            if x2 <= x1 or y2 <= y1:
                logger.error(f"Invalid crop coordinates: ({x1},{y1}) to ({x2},{y2})")
                return None

            # Load image
            img = Image.open(screenshot_path)
            width, height = img.size

            # Clamp coordinates to image bounds
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(x1 + 1, min(x2, width))
            y2 = max(y1 + 1, min(y2, height))

            # Crop image (PIL uses left, upper, right, lower)
            cropped = img.crop((x1, y1, x2, y2))

            # Generate output filename if not provided
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"cropped_{timestamp}_{x1}_{y1}_{x2}_{y2}.jpg"

            output_path = self.screenshot_dir / output_filename

            # Save cropped image
            cropped.save(output_path, 'JPEG', quality=self.quality)

            logger.info(f"✅ Cropped image saved: {output_path} ({cropped.width}x{cropped.height})")
            return str(output_path)

        except Exception as e:
            logger.error(f"Crop error: {e}")
            return None

    def get_crop_preview(
        self,
        screenshot_path: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int
    ) -> Optional[bytes]:
        """
        Get a preview of a crop region as bytes (for API response).

        Args:
            screenshot_path: Path to screenshot
            x1, y1, x2, y2: Crop coordinates

        Returns:
            JPEG bytes of cropped region or None
        """
        try:
            img = Image.open(screenshot_path)
            width, height = img.size

            # Clamp coordinates
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(x1 + 1, min(x2, width))
            y2 = max(y1 + 1, min(y2, height))

            cropped = img.crop((x1, y1, x2, y2))

            # Convert to bytes
            buffer = io.BytesIO()
            cropped.save(buffer, 'JPEG', quality=self.quality)

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Crop preview error: {e}")
            return None