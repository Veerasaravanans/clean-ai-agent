"""
adb_tool.py - Enhanced Android Debug Bridge Tool
"""

import subprocess
import time
import logging
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from backend.models import ActionResult
from backend.config import settings

logger = logging.getLogger(__name__)


class ADBTool:
    """Enhanced ADB command wrapper with automotive OS integration."""
    
    def __init__(self, device_serial: Optional[str] = None):
        """Initialize ADB tool with enhanced features."""
        self.device_serial = device_serial or settings.adb_device_serial
        self.timeout = settings.adb_timeout
        self.retry_count = settings.adb_retry_count
        self.stop_requested = False
        
        # Screen dimensions - detect immediately
        self.screen_width = 0
        self.screen_height = 0
        self._detect_screen_size()
        
        # Ensure we have valid dimensions
        if self.screen_width == 0:
            self.screen_width = 1080
            self.screen_height = 1920
        
        logger.info(f"ADB Tool initialized - {self.screen_width}x{self.screen_height}")
    
    def _detect_screen_size(self):
        """Detect actual screen size and update instance variables."""
        if self.stop_requested:
            return
        
        try:
            cmd = self._build_adb_command(['shell', 'wm', 'size'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Check for both Physical size and Override size
                for line in result.stdout.split('\n'):
                    if 'Physical size:' in line or 'Override size:' in line:
                        size_str = line.split(':')[1].strip()
                        w, h = size_str.split('x')
                        self.screen_width = int(w)
                        self.screen_height = int(h)
                        logger.info(f"Detected screen: {self.screen_width}x{self.screen_height}")
                        return
        except Exception as e:
            logger.warning(f"Screen detection failed: {e}")
    
    def _build_adb_command(self, args: List[str]) -> List[str]:
        """Build ADB command with optional device serial."""
        cmd = ['adb']
        if self.device_serial and self.device_serial != "auto":
            cmd.extend(['-s', self.device_serial])
        cmd.extend(args)
        return cmd
    
    def _execute_adb(self, args: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Execute ADB command with stop check."""
        if self.stop_requested:
            class FakeResult:
                returncode = -1
                stdout = ""
                stderr = "Stopped by user"
            return FakeResult()
        
        cmd = self._build_adb_command(args)
        timeout = timeout or self.timeout
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if self.stop_requested:
                class FakeResult:
                    returncode = -1
                    stdout = ""
                    stderr = "Stopped after execution"
                return FakeResult()
            
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"ADB timeout: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"ADB error: {e}")
            raise
    
    def _run_adb_command(self, command: str, timeout: Optional[int] = None) -> ActionResult:
        """Execute ADB command with retry logic (backward compatible)."""
        timeout = timeout or self.timeout
        args = command.split()
        
        start_time = time.time()
        
        for attempt in range(self.retry_count):
            if self.stop_requested:
                return ActionResult(success=False, error="Stopped by user")
            
            try:
                result = self._execute_adb(args, timeout)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if result.returncode == 0:
                    return ActionResult(
                        success=True,
                        output=result.stdout.strip(),
                        duration_ms=duration_ms
                    )
                else:
                    if attempt < self.retry_count - 1:
                        logger.warning(f"Retry {attempt + 1}/{self.retry_count}")
                        time.sleep(0.5)
                        continue
                    
                    return ActionResult(
                        success=False,
                        error=result.stderr.strip(),
                        duration_ms=duration_ms
                    )
            except Exception as e:
                if attempt < self.retry_count - 1:
                    time.sleep(0.5)
                    continue
                return ActionResult(success=False, error=str(e))
        
        return ActionResult(success=False, error="Max retries exceeded")
    
    def is_connected(self) -> bool:
        """Check if device is connected."""
        if self.stop_requested:
            return False
        
        try:
            result = self._execute_adb(['get-state'], timeout=5)
            return result.returncode == 0 and 'device' in result.stdout
        except Exception:
            return False
    
    def get_device_info(self) -> dict:
        """Get comprehensive device information."""
        info = {
            "connected": False,
            "serial": None,
            "model": None,
            "android_version": None,
            "resolution": {"width": 0, "height": 0},
            "density": None
        }
        
        if not self.is_connected():
            return info
        
        info["connected"] = True
        
        try:
            # Re-detect screen size to ensure fresh values
            self._detect_screen_size()
            
            # Ensure we have valid dimensions after detection
            if self.screen_width == 0:
                self.screen_width = 1080
                self.screen_height = 1920
                logger.warning("Using default resolution after failed detection")
            
            # Serial
            result = self._execute_adb(['get-serialno'])
            if result.returncode == 0:
                info["serial"] = result.stdout.strip()
            
            # Model
            result = self._execute_adb(['shell', 'getprop', 'ro.product.model'])
            if result.returncode == 0:
                info["model"] = result.stdout.strip()
            
            # Android version
            result = self._execute_adb(['shell', 'getprop', 'ro.build.version.release'])
            if result.returncode == 0:
                info["android_version"] = result.stdout.strip()
            
            # Resolution - use instance variables directly
            info["resolution"] = {"width": self.screen_width, "height": self.screen_height}
            logger.debug(f"Returning resolution: {self.screen_width}x{self.screen_height}")
            
            # Density
            result = self._execute_adb(['shell', 'wm', 'density'])
            if result.returncode == 0 and 'Physical density:' in result.stdout:
                density_str = result.stdout.split('Physical density:')[1].strip()
                info["density"] = int(density_str)
        
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
        
        return info
    
    def tap(self, x: int, y: int) -> ActionResult:
        """Execute tap at coordinates."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Tap at ({x}, {y})")
        result = self._execute_adb(['shell', 'input', 'tap', str(x), str(y)])
        
        return ActionResult(
            success=result.returncode == 0,
            action_type="tap",
            coordinates=(x, y),
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    
    def tap_percent(self, x_percent: float, y_percent: float) -> ActionResult:
        """Tap at percentage of screen (0.0-1.0)."""
        x = int(self.screen_width * x_percent)
        y = int(self.screen_height * y_percent)
        return self.tap(x, y)
    
    def double_tap(self, x: int, y: int, delay_ms: int = 50) -> ActionResult:
        """Execute double tap with configurable delay."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Double tap at ({x}, {y})")
        
        result1 = self.tap(x, y)
        if not result1.success or self.stop_requested:
            return result1
        
        time.sleep(delay_ms / 1000.0)
        
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped between taps")
        
        result2 = self.tap(x, y)
        result2.action_type = "double_tap"
        return result2
    
    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> ActionResult:
        """Execute long press."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Long press at ({x}, {y}) for {duration_ms}ms")
        result = self._execute_adb([
            'shell', 'input', 'swipe',
            str(x), str(y), str(x), str(y), str(duration_ms)
        ])
        
        return ActionResult(
            success=result.returncode == 0,
            action_type="long_press",
            coordinates=(x, y),
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> ActionResult:
        """Execute swipe gesture."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Swipe ({x1}, {y1}) → ({x2}, {y2})")
        result = self._execute_adb([
            'shell', 'input', 'swipe',
            str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        ])
        
        return ActionResult(
            success=result.returncode == 0,
            action_type="swipe",
            coordinates=(x1, y1, x2, y2),
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    
    def swipe_up(self, distance: int = 500, duration_ms: int = 300) -> ActionResult:
        """Swipe up from bottom."""
        x = self.screen_width // 2
        y1 = self.screen_height - 100
        y2 = y1 - distance
        return self.swipe(x, y1, x, y2, duration_ms)
    
    def swipe_down(self, distance: int = 500, duration_ms: int = 300) -> ActionResult:
        """Swipe down from top."""
        x = self.screen_width // 2
        y1 = 100
        y2 = y1 + distance
        return self.swipe(x, y1, x, y2, duration_ms)
    
    def swipe_left(self, distance: int = 500, duration_ms: int = 300) -> ActionResult:
        """Swipe left."""
        y = self.screen_height // 2
        x1 = self.screen_width - 100
        x2 = x1 - distance
        return self.swipe(x1, y, x2, y, duration_ms)
    
    def swipe_right(self, distance: int = 500, duration_ms: int = 300) -> ActionResult:
        """Swipe right."""
        y = self.screen_height // 2
        x1 = 100
        x2 = x1 + distance
        return self.swipe(x1, y, x2, y, duration_ms)
    
    def input_text(self, text: str) -> ActionResult:
        """Input text (spaces replaced with %s)."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Input text: {text}")
        escaped_text = text.replace(' ', '%s')
        result = self._execute_adb(['shell', 'input', 'text', escaped_text])
        
        return ActionResult(
            success=result.returncode == 0,
            action_type="input_text",
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    
    def press_key(self, keycode: int) -> ActionResult:
        """Press key by keycode."""
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")
        
        logger.info(f"Press key: {keycode}")
        result = self._execute_adb(['shell', 'input', 'keyevent', str(keycode)])
        
        return ActionResult(
            success=result.returncode == 0,
            action_type="press_key",
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    
    def press_back(self) -> ActionResult:
        """Press back button (keycode 4)."""
        return self.press_key(4)
    
    def press_home(self) -> ActionResult:
        """Press home button (keycode 3)."""
        return self.press_key(3)
    
    def press_enter(self) -> ActionResult:
        """Press enter button (keycode 66)."""
        return self.press_key(66)
    
    def press_menu(self) -> ActionResult:
        """Press menu button (keycode 82)."""
        return self.press_key(82)
    
    def execute_raw_command(self, command: str) -> Dict[str, Any]:
        """Execute raw ADB command for advanced operations."""
        if self.stop_requested:
            return {"success": False, "output": "", "error": "Stopped"}
        
        logger.info(f"Raw ADB: {command}")
        
        try:
            command = command.strip()
            if command.startswith('adb '):
                command = command[4:].strip()
            
            args = command.split()
            result = self._execute_adb(args, timeout=10)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
    
    def stop(self):
        """Request stop of all ADB operations."""
        logger.info("🛑 ADB stop requested")
        self.stop_requested = True
    
    def reset_stop(self):
        """Reset stop flag for new operations."""
        self.stop_requested = False
    
    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        # Ensure fresh detection if dimensions are still 0
        if self.screen_width == 0:
            self._detect_screen_size()
            if self.screen_width == 0:
                self.screen_width = 1080
                self.screen_height = 1920
        
        return (self.screen_width, self.screen_height)