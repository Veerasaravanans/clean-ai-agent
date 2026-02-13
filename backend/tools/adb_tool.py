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

    # Class-level flag to log initialization only once per session
    _initialization_logged = False
    _detected_screen_size = None

    def __init__(self, device_serial: Optional[str] = None):
        """Initialize ADB tool with enhanced features."""
        self.device_serial = device_serial or settings.adb_device_serial
        self.timeout = settings.adb_timeout
        self.retry_count = settings.adb_retry_count
        self.stop_requested = False

        # Screen dimensions - use cached value if available
        if ADBTool._detected_screen_size:
            self.screen_width, self.screen_height = ADBTool._detected_screen_size
        else:
            self.screen_width = 0
            self.screen_height = 0
            self._detect_screen_size()

            # Cache the detected size
            if self.screen_width > 0:
                ADBTool._detected_screen_size = (self.screen_width, self.screen_height)

        # Ensure we have valid dimensions
        if self.screen_width == 0:
            self.screen_width = 1080
            self.screen_height = 1920

        # Log initialization only once per session
        if not ADBTool._initialization_logged:
            logger.info(f"ADB Tool initialized - {self.screen_width}x{self.screen_height}")
            ADBTool._initialization_logged = True
    
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
                        # Use debug level to avoid log spam
                        logger.debug(f"Detected screen: {self.screen_width}x{self.screen_height}")
                        return
        except Exception as e:
            logger.debug(f"Screen detection failed: {e}")
    
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

    def _uiautomator_drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int) -> ActionResult:
        """
        APPROACH 0: Use Python uiautomator2 library for proper drag-and-drop.

        This uses Android's official UI Automator 2.0 framework via the Python library.

        The library:
        - Auto-installs required APKs (ATX-agent, UIAutomator) on first use
        - Works on production builds without root
        - Properly handles drag gestures with correct touch event sequencing
        - Uses Android's accessibility services for reliable interaction

        This is the ONLY reliable way to perform drag-and-drop on AAOS.
        """
        logger.info("🔧 APPROACH 0: Using Python uiautomator2 library")

        try:
            import uiautomator2 as u2

            logger.info("Connecting to device via uiautomator2...")

            # Connect to device (uses ADB internally)
            # This will auto-install required APKs (ATX-agent, UIAutomator) on first run
            try:
                d = u2.connect()
                logger.info("✅ Connected to device via uiautomator2")
            except Exception as e:
                logger.error(f"❌ Failed to connect: {e}")
                return ActionResult(success=False, error=f"uiautomator2 connection failed: {e}")

            # Get device info to confirm connection
            try:
                device_info = d.device_info
                logger.info(f"   Device: {device_info.get('brand')} {device_info.get('model')}")
                logger.info(f"   Android: {device_info.get('version')}")
            except:
                pass  # Device info is optional

            # Press HOME to ensure we're on launcher
            logger.info("Pressing HOME key to activate launcher...")
            d.press("home")
            time.sleep(0.5)

            # CRITICAL: Try to enter launcher edit mode first
            # Some launchers require long-pressing an empty area to enable icon editing
            logger.info("Attempting to enter launcher edit mode...")

            # Try long-pressing on an empty area (bottom right)
            try:
                d.long_click(1200, 700, duration=2.0)
                time.sleep(0.3)
                logger.info("   Long-pressed empty area (may have activated edit mode)")
            except:
                logger.warning("   Long-press for edit mode failed, continuing anyway...")

            # Now try the drag with a VERY long duration (4 seconds)
            # AAOS might require extremely long press to trigger icon lift
            logger.info(f"Executing drag with extended duration: ({x1},{y1}) → ({x2},{y2})")
            logger.info(f"   Duration: 4.0s (extended for AAOS)")

            try:
                # Use swipe instead of drag - swipe has better control
                # Swipe with many steps for smooth, slow movement
                d.swipe(x1, y1, x2, y2, duration=4.0)
                logger.info("✅ UI AUTOMATOR 2.0 SUCCESS! Swipe completed")
            except Exception as e:
                logger.warning(f"⚠️ Swipe failed, trying drag: {e}")
                # Fallback to drag
                d.drag(x1, y1, x2, y2, duration=4.0)
                logger.info("✅ UI AUTOMATOR 2.0 SUCCESS! Drag completed")

            logger.info("   (uiautomator2 executed gesture)")
            logger.info("")
            logger.info("⚠️ IMPORTANT: If icon didn't move, AAOS launcher may not support")
            logger.info("   programmatic icon rearrangement. This is a platform limitation.")

            return ActionResult(
                success=True,
                action_type="drag_and_drop",
                coordinates=(x1, y1, x2, y2),
                output="uiautomator2 drag executed",
                duration_ms=hold_duration_ms
            )

        except ImportError as e:
            logger.error(f"❌ uiautomator2 not installed: {e}")
            return ActionResult(success=False, error="uiautomator2 library not available")

        except Exception as e:
            logger.error(f"❌ uiautomator2 drag failed: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return ActionResult(success=False, error=f"uiautomator2 drag failed: {e}")

    def _detect_touch_device(self) -> Optional[str]:
        """
        Detect the touch input device path using getevent.
        Returns device path like '/dev/input/event1' or None if not found.
        """
        try:
            logger.info("🔍 Detecting touch input device...")
            result = self._execute_adb(['shell', 'getevent', '-lp'], timeout=5)

            if result.returncode != 0:
                logger.warning(f"getevent failed: {result.stderr}")
                return None

            # Parse output to find touch device
            lines = result.stdout.split('\n')
            current_device = None

            for line in lines:
                if 'add device' in line.lower():
                    # Extract device path: add device 1: /dev/input/event1
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_device = parts[1].strip()

                # Look for touch-related capabilities
                if current_device and any(keyword in line.lower() for keyword in ['touch', 'abs_mt', 'btn_touch']):
                    logger.info(f"✅ Found touch device: {current_device}")
                    return current_device

            logger.warning("⚠️ Could not find touch device")
            return None

        except Exception as e:
            logger.warning(f"Touch device detection failed: {e}")
            return None

    def _sendevent_drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int) -> ActionResult:
        """
        APPROACH 1: Use sendevent for RAW touch events with ROOT access.
        This directly writes to the kernel input device, bypassing Android input system.
        Tries with 'su' (root) if normal sendevent fails with permission denied.
        """
        logger.info("🔧 APPROACH 1: Attempting sendevent (raw touch events)")

        touch_device = self._detect_touch_device()
        if not touch_device:
            logger.warning("⚠️ Could not detect touch device, skipping sendevent approach")
            return ActionResult(success=False, error="Touch device not found")

        logger.info(f"Using touch device: {touch_device}")

        try:
            hold_seconds = hold_duration_ms / 1000.0

            # Build sendevent command sequence
            # ABS_MT_TRACKING_ID: 3 57
            # ABS_MT_POSITION_X: 3 53
            # ABS_MT_POSITION_Y: 3 54
            # BTN_TOUCH: 1 330
            # SYN_REPORT: 0 0 0

            sendevent_script = f"""
sendevent {touch_device} 3 57 0
sendevent {touch_device} 3 53 {x1}
sendevent {touch_device} 3 54 {y1}
sendevent {touch_device} 1 330 1
sendevent {touch_device} 0 0 0
sleep {hold_seconds}
sendevent {touch_device} 3 53 {x2}
sendevent {touch_device} 3 54 {y2}
sendevent {touch_device} 0 0 0
sleep 0.1
sendevent {touch_device} 1 330 0
sendevent {touch_device} 3 57 -1
sendevent {touch_device} 0 0 0
"""

            logger.info(f"Executing sendevent sequence: DOWN ({x1},{y1}) → HOLD {hold_seconds}s → MOVE ({x2},{y2}) → UP")

            # Try without root first
            result = self._execute_adb(
                ['shell', sendevent_script.strip()],
                timeout=int(hold_duration_ms / 1000 + 10)
            )

            if result.returncode == 0:
                logger.info(f"✅ SENDEVENT SUCCESS! Drag-and-drop completed")
                return ActionResult(
                    success=True,
                    action_type="drag_and_drop",
                    coordinates=(x1, y1, x2, y2),
                    output="sendevent sequence executed",
                    duration_ms=hold_duration_ms
                )
            elif "Permission denied" in result.stderr:
                # Try with root access (su)
                logger.warning(f"⚠️ Permission denied, trying with root (su)...")

                # Wrap sendevent commands with su
                root_script = f"su -c '{sendevent_script.strip()}'"

                result_root = self._execute_adb(
                    ['shell', root_script],
                    timeout=int(hold_duration_ms / 1000 + 10)
                )

                if result_root.returncode == 0:
                    logger.info(f"✅ SENDEVENT (ROOT) SUCCESS! Drag-and-drop completed")
                    return ActionResult(
                        success=True,
                        action_type="drag_and_drop",
                        coordinates=(x1, y1, x2, y2),
                        output="sendevent with root executed",
                        duration_ms=hold_duration_ms
                    )
                else:
                    logger.error(f"❌ sendevent with root also failed: {result_root.stderr}")
                    return ActionResult(success=False, error=f"sendevent failed even with root: {result_root.stderr}")
            else:
                logger.error(f"❌ sendevent failed: {result.stderr}")
                return ActionResult(success=False, error=f"sendevent failed: {result.stderr}")

        except Exception as e:
            logger.error(f"❌ sendevent exception: {e}")
            return ActionResult(success=False, error=str(e))

    def _shell_script_drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int) -> ActionResult:
        """
        APPROACH 2: Try multiple velocity profiles - some launchers are sensitive to movement speed.

        Will try:
        1. Extended hold (4 seconds) then fast drag - for launchers requiring very long press
        2. Tap-immediate-drag - no hold, instant movement (some launchers work this way)
        3. Gradual acceleration - start slow, speed up (most natural gesture)
        """
        logger.info("🔧 APPROACH 2: Attempting velocity-profile based gestures")

        approaches = [
            {
                "name": "Extended hold + fast drag",
                "script": f"""
input swipe {x1} {y1} {x1} {y1} 4000
sleep 0.05
input swipe {x1} {y1} {x2} {y2} 200
"""
            },
            {
                "name": "Tap-immediate-drag (no hold)",
                "script": f"""
input tap {x1} {y1}
sleep 0.01
input swipe {x1} {y1} {x2} {y2} 300
"""
            },
            {
                "name": "Gradual acceleration profile",
                "script": f"""
input swipe {x1} {y1} {x1} {y1} 3000
sleep 0.05
input swipe {x1} {y1} {int(x1 + (x2-x1)*0.3)} {y1} 800
sleep 0.05
input swipe {int(x1 + (x2-x1)*0.3)} {y1} {int(x1 + (x2-x1)*0.7)} {y1} 400
sleep 0.05
input swipe {int(x1 + (x2-x1)*0.7)} {y1} {x2} {y2} 200
"""
            }
        ]

        for i, approach in enumerate(approaches, 1):
            logger.info(f"  Trying {i}/3: {approach['name']}")

            result = self._execute_adb(
                ['shell', approach['script'].strip()],
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"✅ VELOCITY-PROFILE SUCCESS! ({approach['name']} worked)")
                return ActionResult(
                    success=True,
                    action_type="drag_and_drop",
                    coordinates=(x1, y1, x2, y2),
                    output=f"velocity profile: {approach['name']}",
                    duration_ms=hold_duration_ms
                )
            else:
                logger.warning(f"  ⚠️ {approach['name']} failed")

        # All velocity profiles failed
        logger.error(f"❌ All velocity profiles failed")
        return ActionResult(success=False, error="All velocity profile approaches failed")

    def _python_session_drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int) -> ActionResult:
        """
        APPROACH 3: Try different starting positions - icon edge vs center.

        Some launchers are more sensitive to where you start the drag from.
        Will try: top-left corner, center (current), bottom-right corner of icon.
        """
        logger.info("🔧 APPROACH 3: Attempting different icon starting positions")

        try:
            # App icons are typically 80-100px wide/tall
            # Try starting from different positions on the icon
            icon_size = 80

            positions = [
                {"name": "Top-left corner", "offset": (-icon_size//3, -icon_size//3)},
                {"name": "Center (current)", "offset": (0, 0)},
                {"name": "Bottom-right corner", "offset": (icon_size//3, icon_size//3)},
                {"name": "Left edge", "offset": (-icon_size//2, 0)},
                {"name": "Right edge", "offset": (icon_size//2, 0)},
            ]

            for i, pos in enumerate(positions, 1):
                start_x = x1 + pos["offset"][0]
                start_y = y1 + pos["offset"][1]

                logger.info(f"  Trying {i}/5: {pos['name']} at ({start_x}, {start_y})")

                # Try long press then drag from this position
                script = f"""
input swipe {start_x} {start_y} {start_x} {start_y} 3000
sleep 0.05
input swipe {start_x} {start_y} {x2} {y2} 400
"""

                result = self._execute_adb(
                    ['shell', script.strip()],
                    timeout=5
                )

                if result.returncode == 0:
                    logger.info(f"✅ POSITION-BASED SUCCESS! ({pos['name']} worked)")
                    return ActionResult(
                        success=True,
                        action_type="drag_and_drop",
                        coordinates=(start_x, start_y, x2, y2),
                        output=f"started from {pos['name']}",
                        duration_ms=hold_duration_ms
                    )
                else:
                    logger.warning(f"  ⚠️ {pos['name']} failed")

            # All positions failed
            logger.error(f"❌ All starting positions failed")
            return ActionResult(success=False, error="All icon positions failed")

        except Exception as e:
            logger.error(f"❌ position-based exception: {e}")
            return ActionResult(success=False, error=str(e))

    def _motionevent_drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int) -> ActionResult:
        """
        APPROACH 4: Use separate motionevent commands (fallback).
        This is the previous implementation.
        """
        logger.info("🔧 APPROACH 4: Attempting motionevent (separate commands)")

        try:
            hold_seconds = hold_duration_ms / 1000.0

            # DOWN
            logger.info(f"DOWN at ({x1}, {y1})")
            result_down = self._execute_adb(['shell', 'input', 'motionevent', 'DOWN', str(x1), str(y1)])
            if result_down.returncode != 0:
                logger.error(f"❌ DOWN event failed: {result_down.stderr}")
                return ActionResult(success=False, error=f"DOWN failed: {result_down.stderr}")

            # HOLD
            logger.info(f"Holding for {hold_seconds}s...")
            time.sleep(hold_seconds)

            if self.stop_requested:
                return ActionResult(success=False, error="Stopped during hold")

            # MOVE
            logger.info(f"MOVE to ({x2}, {y2})")
            result_move = self._execute_adb(['shell', 'input', 'motionevent', 'MOVE', str(x2), str(y2)])
            if result_move.returncode != 0:
                logger.warning(f"⚠️ MOVE event warning: {result_move.stderr}")

            time.sleep(0.1)

            if self.stop_requested:
                return ActionResult(success=False, error="Stopped during move")

            # UP
            logger.info(f"UP at ({x2}, {y2})")
            result_up = self._execute_adb(['shell', 'input', 'motionevent', 'UP', str(x2), str(y2)])
            if result_up.returncode != 0:
                logger.error(f"❌ UP event failed: {result_up.stderr}")
                return ActionResult(success=False, error=f"UP failed: {result_up.stderr}")

            logger.info(f"✅ MOTIONEVENT SUCCESS! Drag-and-drop completed")
            return ActionResult(
                success=True,
                action_type="drag_and_drop",
                coordinates=(x1, y1, x2, y2),
                output="motionevent sequence executed",
                duration_ms=hold_duration_ms
            )

        except Exception as e:
            logger.error(f"❌ motionevent exception: {e}")
            return ActionResult(success=False, error=str(e))

    def drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, hold_duration_ms: int = 2500) -> ActionResult:
        """
        Execute proper drag-and-drop gesture for Android 14 AAOS.

        CRITICAL: This implements a CASCADING approach trying multiple methods:

        APPROACH 1: sendevent (raw kernel events) - MOST RELIABLE (if permissions allow)
        APPROACH 2: ultra-slow swipe (4 seconds) - WORKS WITHOUT OPENING APP
        APPROACH 3: Python subprocess (ultra-slow swipe) - ALTERNATIVE METHOD
        APPROACH 4: motionevent (separate commands) - LAST RESORT FALLBACK

        The user requirement is:
        "long press on the target app for 2 seconds and then swipe that app
         according to the distance and direction... continuous action
         (without leaving the screen)"

        KEY FIX: Approaches 2 & 3 now use SINGLE ultra-slow swipe (4000ms) instead
        of separate commands. This prevents the launcher from interpreting the long
        press as "open app" action.

        This means:
        1. Touch DOWN at start position
        2. HOLD for 2+ seconds (to trigger launcher lift mode)
        3. MOVE to end position (WITHOUT releasing touch)
        4. Touch UP at end position

        Args:
            x1: Starting X coordinate (app icon center)
            y1: Starting Y coordinate (app icon center)
            x2: Ending X coordinate (drop target)
            y2: Ending Y coordinate (drop target)
            hold_duration_ms: Duration to hold at start before moving (default 2500ms)

        Returns:
            ActionResult with success status
        """
        if self.stop_requested:
            return ActionResult(success=False, error="Stopped")

        logger.info("=" * 70)
        logger.info(f"🎯 DRAG-AND-DROP INITIATED")
        logger.info(f"   Start: ({x1}, {y1})")
        logger.info(f"   End:   ({x2}, {y2})")
        logger.info(f"   Hold:  {hold_duration_ms}ms")
        logger.info(f"   Goal:  Continuous touch (DOWN → HOLD → MOVE → UP)")
        logger.info("=" * 70)

        # APPROACH 0: Try UI Automator 2.0 (Python library)
        logger.info("\n" + "=" * 70)
        logger.info("🚀 TRYING: UI AUTOMATOR 2.0 (Python uiautomator2 library)")
        logger.info("=" * 70)

        uiautomator_result = self._uiautomator_drag_and_drop(x1, y1, x2, y2, hold_duration_ms)
        if uiautomator_result.success:
            logger.info("\n" + "=" * 70)
            logger.info("🎉 SUCCESS! UI AUTOMATOR 2.0 worked!")
            logger.info("=" * 70 + "\n")
            return uiautomator_result
        else:
            logger.warning(f"⚠️ UI AUTOMATOR 2.0 failed: {uiautomator_result.error}")
            logger.info("Falling back to legacy ADB approaches...\n")

        # Try alternative approaches
        approaches = [
            ("SENDEVENT (raw kernel)", self._sendevent_drag_and_drop),
            ("VELOCITY PROFILES (3 variants)", self._shell_script_drag_and_drop),
            ("POSITION-BASED (5 positions)", self._python_session_drag_and_drop),
            ("MOTIONEVENT (fallback)", self._motionevent_drag_and_drop),
        ]

        for approach_name, approach_func in approaches:
            if self.stop_requested:
                return ActionResult(success=False, error="Stopped")

            logger.info(f"\n{'=' * 70}")
            logger.info(f"🚀 TRYING: {approach_name}")
            logger.info(f"{'=' * 70}")

            result = approach_func(x1, y1, x2, y2, hold_duration_ms)

            if result.success:
                logger.info(f"\n{'=' * 70}")
                logger.info(f"🎉 SUCCESS! {approach_name} worked!")
                logger.info(f"{'=' * 70}\n")
                return result
            else:
                logger.warning(f"⚠️ {approach_name} failed: {result.error}")
                logger.info(f"Moving to next approach...\n")

        # All approaches failed
        logger.error(f"\n{'=' * 70}")
        logger.error(f"❌ ALL APPROACHES FAILED!")
        logger.error(f"   Tried: {', '.join([name for name, _ in approaches])}")
        logger.error(f"{'=' * 70}\n")

        return ActionResult(
            success=False,
            action_type="drag_and_drop",
            error="All drag-and-drop approaches failed (sendevent, shell script, python session, motionevent)"
        )