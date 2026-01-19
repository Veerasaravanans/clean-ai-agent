"""
Non-Texted Icon Detection Tool - AI Vision First Approach + Device Profile Priority

This module detects icons WITHOUT text labels using:
1. Device Profile (stored coordinates) - INSTANT - HIGHEST PRIORITY
2. Grid pattern verification for app launcher (3x3 dots)
3. AI vision as PRIMARY method for all other icons
4. NO hardcoded positions, sizes, or layout assumptions

The system is fully dynamic and works across all Android Automotive displays.
"""

import cv2
import numpy as np
import requests
import logging
import base64
import json
import re
import os
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from sklearn.cluster import DBSCAN

# Import settings
try:
    from backend.config import settings
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Coordinates:
    """Screen coordinates."""
    x: int
    y: int


class NonTextedIconDetectionTool:
    """
    Detects icons WITHOUT text labels.
    
    Strategy:
    - Device Profile: Check stored coordinates FIRST (instant)
    - App Launcher: CV grid pattern verification (reliable)
    - All other icons: AI vision (dynamic, no assumptions)
    """
    
    def __init__(self, model_preference: Optional[str] = None):
        """
        Initialize Non-Texted Icon Detection Tool.
        
        Args:
            model_preference: Optional vision model name (for backward compatibility)
        """
        # Build VIO config from settings
        self.vio_config = {
            'base_url': settings.vio_base_url,
            'username': settings.vio_username,
            'api_token': settings.vio_api_token,
            'verify_ssl': settings.vio_verify_ssl,
            'vision_model': model_preference or settings.vio_primary_model
        }
        
        self.use_ai_vision = settings.vision_use_ai
        self.vision_model = self.vio_config['vision_model']
        self.current_model = self.vision_model
        
        logger.info(f"✅ NonTextedIconDetectionTool initialized (Device-Profile-First + AI-Vision, model: {self.vision_model})")
    
    def find_element_with_ai(self, screenshot_path: str, description: str, is_texted: bool = False) -> Optional[Coordinates]:
        """
        Find non-texted icon element.
        
        Strategy:
        1. Device Profile - Check stored coordinates FIRST (instant)
        2. If APP LAUNCHER → Use CV grid detection
        3. For ALL OTHER icons → Use AI vision (primary)
        4. Auto-save successful detections to profile
        
        Args:
            screenshot_path: Path to screenshot
            description: Icon description (e.g., "HVAC icon", "phone icon")
            is_texted: If True, return None (handled by texted tool)
        
        Returns:
            Coordinates if found, None otherwise
        """
        if is_texted:
            return None
        
        desc_lower = description.lower()
        
        # ═══════════════════════════════════════════════════════════
        # PRIORITY 1: DEVICE PROFILE (HIGHEST PRIORITY - INSTANT)
        # ═══════════════════════════════════════════════════════════
        logger.info(f"📍 Priority 1: Checking DEVICE PROFILE for '{description}'...")
        try:
            from backend.tools.device_coordinate_tool import get_device_coordinate_tool
            
            device_tool = get_device_coordinate_tool()
            profile_coords = device_tool.find_icon_coordinates(description)
            
            if profile_coords:
                logger.info(f"✅ FOUND in device profile: '{description}' at {profile_coords}")
                return Coordinates(x=profile_coords[0], y=profile_coords[1])
            else:
                logger.info(f"   → Not in profile, proceeding to detection methods...")
        except Exception as e:
            logger.warning(f"Device profile lookup failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # PRIORITY 2: CV/AI DETECTION (Original Logic)
        # ═══════════════════════════════════════════════════════════
        
        # Detect if this is app launcher request
        is_launcher = any(keyword in desc_lower for keyword in 
                         ['app launcher', 'app drawer', 'grid', 'launcher icon'])
        
        result = None
        
        if is_launcher:
            logger.info("🎯 Priority 2: Detecting APP LAUNCHER using grid pattern verification")
            result = self._detect_app_launcher_grid(screenshot_path)
        else:
            logger.info(f"🎯 Priority 2: Detecting '{description}' using AI vision (primary method)")
            result = self._detect_icon_with_ai_vision(screenshot_path, description)
        
        # ═══════════════════════════════════════════════════════════
        # AUTO-SAVE SUCCESSFUL DETECTION TO PROFILE
        # ═══════════════════════════════════════════════════════════
        if result:
            try:
                from backend.services.device_profile_service import get_device_profile_service
                
                profile_service = get_device_profile_service()
                profile_service.add_coordinate(
                    icon_name=description,
                    x=result.x,
                    y=result.y,
                    verified_by="cv_auto"
                )
                logger.info(f"💾 Auto-saved to device profile: '{description}' at ({result.x}, {result.y})")
            except Exception as e:
                logger.warning(f"Failed to auto-save coordinate: {e}")
        
        return result
    
    def _detect_app_launcher_grid(self, screenshot_path: str) -> Optional[Coordinates]:
        """
        Detect app launcher icon using 3x3 grid pattern verification.
        This is the ONLY icon we detect with CV because it has a unique pattern.
        """
        img = cv2.imread(screenshot_path)
        if img is None:
            logger.error("Failed to load screenshot")
            return None
        
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Scan navigation bars (bottom, top, sides)
        regions_to_scan = self._get_navigation_regions(width, height)
        
        all_candidates = []
        
        for region_name, (x1, y1, x2, y2) in regions_to_scan.items():
            region = img[y1:y2, x1:x2]
            if region.size == 0:
                continue
            
            region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            
            # Detect circular patterns (grid dots)
            candidates = self._find_grid_candidates(region_gray, x1, y1)
            
            for cand in candidates:
                # Verify if this is a 3x3 grid
                is_grid, grid_score = self._verify_grid_pattern(gray, cand['x'], cand['y'])
                
                if is_grid and grid_score > 0.4:  # Very lenient threshold
                    cand['score'] = grid_score * 1000  # High score for verified grids
                    cand['verified_grid'] = True
                    cand['region'] = region_name
                    all_candidates.append(cand)
                    logger.info(f"✅ Found verified grid in {region_name} at ({cand['x']}, {cand['y']}) score={grid_score:.2f}")
        
        if all_candidates:
            # Return highest scoring grid
            best = max(all_candidates, key=lambda c: c['score'])
            logger.info(f"🎯 Selected best grid at ({best['x']}, {best['y']}) from {best['region']}")
            return Coordinates(x=best['x'], y=best['y'])
        
        # FALLBACK: If no grid found, try edge detection for any grid-like pattern
        logger.warning("⚠️ Grid pattern verification failed, trying edge detection fallback...")
        return self._detect_grid_fallback(img, regions_to_scan)
    
    def _detect_grid_fallback(self, img: np.ndarray, regions_to_scan: Dict) -> Optional[Coordinates]:
        """
        Fallback method: Detect grid using edge density in navigation regions.
        This is used when circle detection fails.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        best_candidate = None
        best_density = 0
        
        for region_name, (x1, y1, x2, y2) in regions_to_scan.items():
            region_edges = edges[y1:y2, x1:x2]
            if region_edges.size == 0:
                continue
            
            # Look for grid-like patterns (small areas with high edge density)
            h, w = region_edges.shape
            cell_size = 60  # Size of area to check
            
            for y in range(0, h - cell_size, 10):
                for x in range(0, w - cell_size, 10):
                    cell = region_edges[y:y+cell_size, x:x+cell_size]
                    density = np.sum(cell > 0) / (cell_size * cell_size)
                    
                    # Grid icons typically have moderate edge density (dots create edges)
                    if 0.05 < density < 0.30 and density > best_density:
                        best_density = density
                        best_candidate = {
                            'x': x1 + x + cell_size // 2,
                            'y': y1 + y + cell_size // 2,
                            'density': density,
                            'region': region_name
                        }
        
        if best_candidate:
            logger.info(f"✅ Fallback found grid-like pattern in {best_candidate['region']} at ({best_candidate['x']}, {best_candidate['y']}) density={best_candidate['density']:.3f}")
            return Coordinates(x=best_candidate['x'], y=best_candidate['y'])
        
        logger.error("❌ No app launcher grid detected (both methods failed)")
        return None
    
    def _get_navigation_regions(self, width: int, height: int) -> Dict[str, Tuple[int, int, int, int]]:
        """
        Get regions where navigation bars might be.
        Returns dict of region_name -> (x1, y1, x2, y2)
        
        This scans all possible bar locations dynamically.
        """
        bar_height = int(height * 0.15)  # 15% of screen height
        bar_width = int(width * 0.15)    # 15% of screen width
        
        return {
            'bottom': (0, height - bar_height, width, height),
            'top': (0, 0, width, bar_height),
            'left': (0, 0, bar_width, height),
            'right': (width - bar_width, 0, width, height),
        }
    
    def _find_grid_candidates(self, gray_region: np.ndarray, offset_x: int, offset_y: int) -> List[Dict]:
        """Find potential grid icon candidates using circle detection with LENIENT parameters."""
        candidates = []
        
        # Try multiple preprocessing methods
        preprocessed_images = [
            gray_region,
            cv2.GaussianBlur(gray_region, (3, 3), 0),
            cv2.GaussianBlur(gray_region, (5, 5), 0),
            cv2.GaussianBlur(gray_region, (7, 7), 0),
            cv2.bitwise_not(gray_region),
            cv2.bitwise_not(cv2.GaussianBlur(gray_region, (3, 3), 0))
        ]
        
        for prep in preprocessed_images:
            circles = cv2.HoughCircles(
                prep, 
                cv2.HOUGH_GRADIENT, 
                dp=1.2, 
                minDist=5,  # Reduced to catch closer dots
                param1=50,  # Reduced for more sensitivity
                param2=18,  # Reduced for more sensitivity
                minRadius=1,  # Minimum possible
                maxRadius=20  # Increased range
            )
            
            if circles is not None:
                circles = circles[0]
                # Very lenient: Require at least 5 circles (allowing 4 missing from 3x3=9)
                if len(circles) >= 5:
                    # Find clusters of circles
                    centers = circles[:, :2]
                    clustering = DBSCAN(eps=60, min_samples=5).fit(centers)  # Require 5 circles per cluster
                    
                    for label in set(clustering.labels_):
                        if label == -1:
                            continue
                        
                        cluster_circles = circles[clustering.labels_ == label]
                        if len(cluster_circles) >= 5:  # At least 5 circles
                            # Calculate center of cluster
                            center_x = int(np.mean(cluster_circles[:, 0])) + offset_x
                            center_y = int(np.mean(cluster_circles[:, 1])) + offset_y
                            
                            candidates.append({
                                'x': center_x,
                                'y': center_y,
                                'num_circles': len(cluster_circles),
                                'score': 0
                            })
        
        return candidates
    
    def _verify_grid_pattern(self, gray: np.ndarray, x: int, y: int) -> Tuple[bool, float]:
        """
        Verify if location contains a 3x3 grid pattern.
        Very lenient verification to catch actual grids.
        
        Returns:
            (is_grid, confidence_score)
        """
        # Extract region around the candidate
        margin = 50
        x1 = max(0, x - margin)
        x2 = min(gray.shape[1], x + margin)
        y1 = max(0, y - margin)
        y2 = min(gray.shape[0], y + margin)
        
        region = gray[y1:y2, x1:x2]
        if region.size == 0:
            return False, 0.0
        
        # Detect circles in region with LENIENT parameters
        blurred = cv2.GaussianBlur(region, (5, 5), 0)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=5,  # Lenient
            param1=50,  # Lenient
            param2=18,  # Lenient
            minRadius=1,  # Minimum
            maxRadius=20  # Wide range
        )
        
        # Very lenient: Require 5-15 circles for a 3x3 grid
        if circles is None or len(circles[0]) < 5:
            return False, 0.0
        
        circles = circles[0]
        num_circles = min(len(circles), 15)
        
        # Check uniformity of circle sizes
        radii = circles[:num_circles, 2]
        if len(radii) == 0:
            return False, 0.0
        
        mean_radius = np.mean(radii)
        std_radius = np.std(radii)
        
        if mean_radius == 0:
            return False, 0.0
        
        # Very lenient: Uniformity should be > 0.50
        uniformity = 1.0 - (std_radius / mean_radius)
        
        # Accept grids with 5+ circles and reasonable uniformity
        if num_circles >= 5 and uniformity >= 0.50:
            return True, uniformity
        
        return False, 0.0
    
    def _detect_icon_with_ai_vision(self, screenshot_path: str, description: str) -> Optional[Coordinates]:
        """
        Detect any icon using AI vision.
        
        This is the PRIMARY method for all non-launcher icons.
        AI analyzes the screenshot and returns coordinates.
        
        Args:
            screenshot_path: Path to screenshot
            description: Icon description
        
        Returns:
            Coordinates if found, None otherwise
        """
        if not self.use_ai_vision:
            logger.warning("AI vision disabled, cannot detect non-launcher icons")
            return None
        
        try:
            # Read and encode image
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Get screen dimensions
            img = cv2.imread(screenshot_path)
            height, width = img.shape[:2]
            
            # Create AI prompt focused on visual features
            prompt = self._create_ai_detection_prompt(description, width, height)
            
            # Call AI vision API
            response = self._call_vision_api_internal(prompt, image_data)
            
            if response:
                # Parse coordinates from response
                coords = self._parse_coordinates_from_ai_response(response)
                if coords:
                    logger.info(f"✅ AI Vision found icon at ({coords.x}, {coords.y})")
                    return coords
                else:
                    logger.warning("AI Vision couldn't locate the icon")
            
        except Exception as e:
            logger.error(f"AI Vision detection failed: {e}")
        
        return None
    
    def _create_ai_detection_prompt(self, description: str, width: int, height: int) -> str:
        """
        Create optimized prompt for AI icon detection.
        
        Focus on VISUAL FEATURES, not positions or layouts.
        """
        # Extract icon type from description
        desc_lower = description.lower()
        
        # Build visual feature descriptions
        visual_features = ""
        
        if 'hvac' in desc_lower or 'climate' in desc_lower or 'fan' in desc_lower:
            visual_features = """
ICON TO FIND: HVAC/Climate control icon
VISUAL FEATURES: Circular fan pattern, radiating lines (fan blades), spiral or circular flow design, temperature/airflow symbols
TYPICAL APPEARANCE: White icon on dark background, looks like a fan or circular vent"""

        elif 'phone' in desc_lower or 'call' in desc_lower:
            visual_features = """
ICON TO FIND: Phone/Call icon
VISUAL FEATURES: Traditional phone handset shape, curved receiver, simple phone outline
TYPICAL APPEARANCE: White icon on dark background, classic telephone symbol"""

        elif 'home' in desc_lower:
            visual_features = """
ICON TO FIND: Home icon
VISUAL FEATURES: House shape with triangle roof and square base, simple house outline
TYPICAL APPEARANCE: White icon on dark background, classic home symbol"""

        elif 'notification' in desc_lower or 'bell' in desc_lower:
            visual_features = """
ICON TO FIND: Notification/Bell icon
VISUAL FEATURES: Bell shape, may have small badge or dot
TYPICAL APPEARANCE: White icon on dark background, classic bell symbol"""

        elif 'microphone' in desc_lower or 'voice' in desc_lower:
            visual_features = """
ICON TO FIND: Microphone/Voice icon
VISUAL FEATURES: Microphone shape, may show sound waves
TYPICAL APPEARANCE: White icon on dark background, classic mic symbol"""

        else:
            visual_features = f"""
ICON TO FIND: {description}
VISUAL FEATURES: Look for the icon matching this description by its shape and appearance
TYPICAL APPEARANCE: Icon in navigation bar or app grid"""

        prompt = f"""Analyze this Android Automotive screenshot ({width}x{height} pixels).

TASK: Find the exact center coordinates of this icon:
{visual_features}

SEARCH AREA: 
- Navigation bars (usually at bottom, but can be top/left/right)
- Look at the ENTIRE screenshot carefully
- The icon is likely WHITE on a DARK background
- It's a simple, clear icon design

IMPORTANT:
1. Return the CENTER point of the icon
2. Double-check your coordinates are within the image bounds (0-{width} for X, 0-{height} for Y)
3. Be as precise as possible

RESPONSE FORMAT (CRITICAL - Use EXACTLY this format):
FOUND: YES
X: <x_coordinate>
Y: <y_coordinate>
CONFIDENCE: <0-100>

If you cannot find the icon:
FOUND: NO
REASON: <why>

RESPOND NOW with coordinates:"""

        return prompt
    
    def _call_vision_api_with_path(self, screenshot_path: str, prompt: str) -> Optional[str]:
        """
        Call VIO Vision API with screenshot path (for vision_tool integration).
        This is a wrapper for backward compatibility.
        """
        try:
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            return self._call_vision_api_internal(prompt, image_data)
        except Exception as e:
            logger.error(f"Vision API call with path failed: {e}")
            return None
    
    def _call_vision_api(self, first_arg, second_arg) -> Optional[str]:
        """
        Compatibility wrapper that handles both calling conventions:
        - _call_vision_api(screenshot_path, prompt) - old vision_tool style
        - _call_vision_api(prompt, image_base64) - new style
        """
        # Detect which style based on arguments
        if isinstance(first_arg, str) and (first_arg.endswith('.jpg') or first_arg.endswith('.png') or '/' in first_arg or '\\' in first_arg):
            # Old style: first_arg is path, second_arg is prompt
            return self._call_vision_api_with_path(first_arg, second_arg)
        else:
            # New style: first_arg is prompt, second_arg is image_base64
            return self._call_vision_api_internal(first_arg, second_arg)
    
    def _call_vision_api_internal(self, prompt: str, image_base64: str) -> Optional[str]:
        """Call VIO Cloud vision API with correct payload format."""
        try:
            url = f"{self.vio_config['base_url']}/message"
            
            # Use the CORRECT VIO API format
            payload = {
                "username": self.vio_config['username'],
                "token": self.vio_config['api_token'],
                "type": "QUESTION",
                "payload": prompt,
                "vio_model": "Default",
                "ai_model": self.vision_model,
                "knowledge": False,
                "webSearch": False,
                "reason": False,
                "image": image_base64
            }
            
            response = requests.post(
                url, 
                json=payload, 
                verify=self.vio_config.get('verify_ssl', False),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # VIO API returns the response directly or in 'response' field
                if isinstance(data, str):
                    return data
                elif isinstance(data, dict):
                    if 'response' in data:
                        return data['response']
                    elif 'result' in data:
                        return data['result']
                    elif 'answer' in data:
                        return data['answer']
                    else:
                        # Try to get first string value
                        for value in data.values():
                            if isinstance(value, str):
                                return value
                
                logger.error("VIO API returned 200 but couldn't find response text")
                logger.debug(f"Response data: {data}")
            else:
                logger.error(f"VIO API error: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Error response text: {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"Vision API call failed: {e}", exc_info=True)
        
        return None
    
    def _parse_coordinates_from_ai_response(self, response: str) -> Optional[Coordinates]:
        """
        Parse coordinates from AI response.
        
        Expected format:
        FOUND: YES
        X: 742
        Y: 1050
        CONFIDENCE: 95
        """
        try:
            # Check if found
            if 'FOUND: NO' in response or 'FOUND:NO' in response:
                logger.info("AI Vision: Icon not found")
                return None
            
            # Extract X coordinate
            x_match = re.search(r'X:\s*(\d+)', response, re.IGNORECASE)
            y_match = re.search(r'Y:\s*(\d+)', response, re.IGNORECASE)
            
            if x_match and y_match:
                x = int(x_match.group(1))
                y = int(y_match.group(1))
                
                # Validate coordinates are reasonable
                if x > 0 and y > 0 and x < 5000 and y < 5000:
                    return Coordinates(x=x, y=y)
                else:
                    logger.warning(f"AI returned invalid coordinates: ({x}, {y})")
            else:
                logger.warning("Couldn't parse coordinates from AI response")
                
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
        
        return None
    
    def analyze_screen_with_ai(self, screenshot_path: str, context: str = None) -> Dict[str, Any]:
        """
        Analyze screen to detect all non-texted icons.
        Used for general screen analysis.
        """
        result = {
            'success': False,
            'detected_icons': [],
            'error': None
        }
        
        try:
            # Try to detect common icons
            common_icons = [
                'home icon',
                'app launcher icon', 
                'phone icon',
                'HVAC icon',
                'notification icon',
                'microphone icon'
            ]
            
            for icon_desc in common_icons:
                coords = self.find_element_with_ai(screenshot_path, icon_desc)
                if coords:
                    result['detected_icons'].append({
                        'description': icon_desc,
                        'x': coords.x,
                        'y': coords.y
                    })
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Screen analysis failed: {e}")
        
        return result
    
    def switch_model(self, model_name: str):
        """Switch the AI vision model."""
        self.vision_model = model_name
        self.current_model = model_name
        logger.info(f"✅ Switched vision model to: {model_name}")


def get_non_texted_tool(model_preference: Optional[str] = None) -> NonTextedIconDetectionTool:
    """Factory function to create tool instance."""
    return NonTextedIconDetectionTool(model_preference)