"""
Coordinate Parser Utility

Extracts explicit coordinates, durations, speeds, and drag-drop parameters
from natural language test step descriptions using regex patterns.

This utility supports the AI-driven action decision system by handling
explicit coordinate extraction as Stage 0 (before AI analysis).
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class CoordinateParser:
    """
    Extract explicit coordinates and action modifiers using regex patterns.

    Supports:
    - Single coordinates: "at 100,200", "tap 500,300"
    - Swipe coordinates: "swipe 100,200,500,600"
    - Speed modifiers: "(slow)", "(fast)", "quickly"
    - Duration: "for 3 seconds", "hold 2 seconds"
    - Drag-drop: "move playstore app 250 pixel right"
    """

    # Regex patterns for coordinate extraction
    SINGLE_COORD_PATTERNS = [
        r'at\s*\(?(\d+)\s*,\s*(\d+)\)?',          # "at 100,200" or "at (100,200)"
        r'tap\s+(\d+)\s*,\s*(\d+)',                # "tap 100,200"
        r'press\s+(\d+)\s*,\s*(\d+)',              # "press 100,200"
        r'click\s+(\d+)\s*,\s*(\d+)',              # "click 100,200"
        r'\((\d+)\s*,\s*(\d+)\)',                  # "(100,200)"
        r'coordinates?\s*[:\s]+(\d+)\s*,\s*(\d+)', # "coordinate: 100,200"
    ]

    SWIPE_COORD_PATTERNS = [
        r'swipe[\s:]+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)',  # "swipe 100,200,500,600" or "swipe:100,200,500,600"
        r'from\s+(\d+)\s*,\s*(\d+)\s+to\s+(\d+)\s*,\s*(\d+)',  # "from 100,200 to 500,600"
        r'slide[\s:]+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)',  # "slide 100,200,500,600" or "slide:100,200,500,600"
    ]

    SPEED_PATTERNS = [
        (r'\(slow\)|slow(?:ly)?', 'slow'),
        (r'\(fast\)|fast|quick(?:ly)?', 'fast'),
        (r'\(medium\)|medium', 'medium'),
    ]

    DURATION_PATTERNS = [
        r'for\s+(\d+(?:\.\d+)?)\s*sec(?:ond)?s?',  # "for 3 seconds", "for 2.5 sec"
        r'hold\s+(\d+(?:\.\d+)?)\s*sec(?:ond)?s?', # "hold 2 seconds"
        r'press\s+(\d+(?:\.\d+)?)\s*sec(?:ond)?s?',# "press 3 seconds"
        r'wait\s+(\d+(?:\.\d+)?)\s*sec(?:ond)?s?', # "wait 1.5 seconds"
    ]

    # Enhanced pattern to match multiple phrasings: "move", "drag", "drag and drop"
    # Captures multi-word app names (e.g., "Play Store") and optional "side" suffix
    DRAG_DROP_PATTERN = r'(?:move|drag(?:\s+and\s+drop)?)\s+(?:the\s+)?([A-Za-z0-9\s]+?)\s+app\s+(\d+)\s*pixel[s]?\s+(left|right|up|down)(?:\s+side)?'

    # Speed to duration mapping (in milliseconds)
    SPEED_DURATIONS = {
        'slow': 800,
        'medium': 300,
        'fast': 100,
    }

    def extract_single_coordinate(self, text: str) -> Optional[Tuple[int, int]]:
        """
        Extract single (x, y) coordinates from text.

        Args:
            text: Input text containing coordinates

        Returns:
            Tuple of (x, y) or None if not found

        Examples:
            "tap at 100,200" -> (100, 200)
            "at (500, 300)" -> (500, 300)
            "click 741,745" -> (741, 745)
        """
        for pattern in self.SINGLE_COORD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    x, y = int(match.group(1)), int(match.group(2))
                    logger.info(f"📍 Extracted single coordinate: ({x}, {y}) from pattern '{pattern}'")
                    return (x, y)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse coordinates from match: {e}")
                    continue

        return None

    def extract_swipe_coordinates(self, text: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Extract swipe coordinates (x1, y1, x2, y2) from text.

        Args:
            text: Input text containing swipe coordinates

        Returns:
            Tuple of (x1, y1, x2, y2) or None if not found

        Examples:
            "swipe 100,200,500,600" -> (100, 200, 500, 600)
            "from 100,200 to 500,600" -> (100, 200, 500, 600)
        """
        for pattern in self.SWIPE_COORD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    x1 = int(match.group(1))
                    y1 = int(match.group(2))
                    x2 = int(match.group(3))
                    y2 = int(match.group(4))
                    logger.info(f"📍 Extracted swipe coordinates: ({x1},{y1}) -> ({x2},{y2})")
                    return (x1, y1, x2, y2)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse swipe coordinates: {e}")
                    continue

        return None

    def extract_swipe_speed(self, text: str) -> Optional[str]:
        """
        Extract swipe speed modifier from text.

        Args:
            text: Input text containing speed modifier

        Returns:
            "slow", "medium", "fast", or None if not found

        Examples:
            "swipe (slow)" -> "slow"
            "quickly swipe" -> "fast"
            "swipe medium speed" -> "medium"
        """
        for pattern, speed in self.SPEED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"🏃 Extracted speed: '{speed}' from pattern '{pattern}'")
                return speed

        return None

    def extract_duration(self, text: str) -> Optional[float]:
        """
        Extract duration in seconds from text.

        Args:
            text: Input text containing duration

        Returns:
            Duration in seconds (float) or None if not found

        Examples:
            "for 3 seconds" -> 3.0
            "hold 2.5 sec" -> 2.5
            "press 1 second" -> 1.0
        """
        for pattern in self.DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    duration = float(match.group(1))
                    logger.info(f"⏱️ Extracted duration: {duration} seconds")
                    return duration
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse duration: {e}")
                    continue

        return None

    def extract_drag_drop(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract drag-drop parameters from text.

        Args:
            text: Input text containing drag-drop command

        Returns:
            Dict with keys: app_name, pixel_offset, direction
            or None if not found

        Examples:
            "move playstore app 250 pixel right" ->
                {"app_name": "playstore", "pixel_offset": 250, "direction": "right"}
        """
        match = re.search(self.DRAG_DROP_PATTERN, text, re.IGNORECASE)
        if match:
            try:
                app_name = match.group(1)
                pixel_offset = int(match.group(2))
                direction = match.group(3).lower()

                result = {
                    "app_name": app_name,
                    "pixel_offset": pixel_offset,
                    "direction": direction
                }

                logger.info(f"🎯 Extracted drag-drop: {result}")
                return result
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse drag-drop parameters: {e}")

        return None

    def speed_to_duration_ms(self, speed: str) -> int:
        """
        Convert speed modifier to duration in milliseconds.

        Args:
            speed: "slow", "medium", or "fast"

        Returns:
            Duration in milliseconds (int)

        Examples:
            "slow" -> 800
            "medium" -> 300
            "fast" -> 100
        """
        duration = self.SPEED_DURATIONS.get(speed.lower(), 300)
        logger.info(f"🔄 Speed '{speed}' -> {duration}ms duration")
        return duration

    def extract_raw_command(self, text: str) -> Optional[str]:
        """
        Extract raw ADB command from text.

        Args:
            text: Input text containing raw command

        Returns:
            Extracted command string or None if not found

        Examples:
            "execute this command:adb shell input tap 741 745" ->
                "adb shell input tap 741 745"
            "run: adb shell dumpsys activity" ->
                "adb shell dumpsys activity"
        """
        patterns = [
            r'execute\s+this\s+command\s*:\s*(.+?)(?:\s*\(|$)',  # "execute this command: ..."
            r'run\s+command\s*:\s*(.+?)(?:\s*\(|$)',             # "run command: ..."
            r'run\s*:\s*(.+?)(?:\s*\(|$)',                       # "run: ..."
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                command = match.group(1).strip()
                logger.info(f"💻 Extracted raw command: '{command}'")
                return command

        return None
