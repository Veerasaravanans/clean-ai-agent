"""
vision_tool.py - FULLY DYNAMIC Vision Tool - AI decides routing
Primary Function: Find coordinates of UI elements (text/icons) with 200% reliability
PRIORITY: Device Profile → CV/AI Detection → OCR
"""
import logging
import os
import re
import json
import base64
from typing import Optional, List, Tuple, Dict
from pathlib import Path
from difflib import SequenceMatcher
import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import requests

try:
    from backend.models import Coordinates, TextElement, ScreenAnalysis
    from backend.config import settings
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.models import Coordinates, TextElement, ScreenAnalysis
    from backend.config import settings

from .texted_icon_detection import TextedIconDetectionTool
from .non_texted_icon_detection import NonTextedIconDetectionTool

if os.name == 'nt':
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

logger = logging.getLogger(__name__)

class VisionTool:
    """FULLY DYNAMIC vision tool with device profile priority for non-texted icons."""
    
    def __init__(self, model_preference: Optional[str] = None):
        self.confidence_threshold = settings.ocr_confidence_threshold
        self.use_ai_vision = settings.vision_use_ai
        
        self.texted_tool = TextedIconDetectionTool(self.confidence_threshold)
        self.non_texted_tool = NonTextedIconDetectionTool(model_preference)
        
        logger.info("✅ Vision Tool initialized - Device Profile Priority for Non-Texted Icons")
    
    def switch_model(self, model_name: str):
        self.non_texted_tool.switch_model(model_name)
        logger.info(f"🔄 Switched vision model to: {model_name}")
    
    def _get_screen_dimensions(self, screenshot_path: str) -> Tuple[int, int]:
        try:
            img = Image.open(screenshot_path)
            return img.size
        except:
            return 1408, 792
    
    def _ask_ai_has_text_label(self, screenshot_path: str, description: str) -> bool:
        """
        CRITICAL: Let AI decide if element has text label by analyzing screenshot.
        """
        try:
            prompt = f"""Analyze this Android Automotive screenshot to determine if the element has a text label.

ELEMENT TO FIND: "{description}"

QUESTION: Does this element have visible TEXT (letters/words) as a label?

EXAMPLES OF ELEMENTS WITH TEXT LABELS (answer YES):
- "Settings" - has text "Settings" below gear icon
- "Phone" - has text "Phone" below phone icon  
- "Navigation" - has text "Navigation" below map icon
- "Media Player" - has text "Media Player" below icon
- Any app with its name written near/below the icon

EXAMPLES OF ELEMENTS WITHOUT TEXT LABELS (answer NO):
- "app launcher icon" - just a 3x3 grid of dots, no text
- "HVAC icon" - just a fan symbol, no text
- "home icon" - just a house shape, no text
- "back button" - just an arrow, no text  
- "notification bell" - just a bell symbol, no text

LOOK CAREFULLY at the screenshot:
1. Find the element matching "{description}"
2. Check if there are any TEXT LETTERS/WORDS visible as part of or near it
3. App names, button labels, icon labels = TEXT LABELS = YES
4. Pure icons/symbols without any text = NO

Answer ONLY one word:
YES or NO

Your answer:"""
            
            response = self.non_texted_tool._call_vision_api(screenshot_path, prompt)
            
            if response is None:
                logger.warning("AI decision returned None, defaulting to TEXTED")
                return True
            
            response_clean = response.strip().upper()
            has_text = 'YES' in response_clean[:30]
            
            logger.info(f"🤖 AI decision for '{description}': {'TEXTED' if has_text else 'NON-TEXTED'}")
            logger.debug(f"   AI response: {response[:100]}")
            
            return has_text
            
        except Exception as e:
            logger.error(f"AI decision error: {e}")
            return True
    
    def find_text(self, screenshot_path: str, target_text: str) -> Optional[Coordinates]:
        return self.texted_tool.find_text(screenshot_path, target_text)
    
    def analyze_screen_with_ai(self, screenshot_path: str, question: str = "", is_texted: bool = True) -> ScreenAnalysis:
        if is_texted:
            return self.texted_tool.analyze_screen_with_ai(screenshot_path, question)
        else:
            return self.non_texted_tool.analyze_screen_with_ai(screenshot_path, question)
    
    def _extract_elements_from_text(self, text: str) -> List[str]:
        """Extract app/element names from natural AI response."""
        EXPLANATION_WORDS = {
            'however', 'therefore', 'thus', 'hence', 'moreover', 'furthermore',
            'additionally', 'consequently', 'meanwhile', 'nevertheless',
            'without', 'with', 'please', 'note', 'that', 'this', 'these', 'those',
            'cannot', 'can', 'could', 'would', 'should', 'may', 'might', 'must',
            'the', 'a', 'an', 'if', 'when', 'where', 'why', 'how', 'what', 'which',
            'who', 'whom', 'whose', 'there', 'here', 'they', 'them', 'their',
            'visible', 'see', 'found', 'detect', 'show', 'display', 'appear',
            'currently', 'present', 'available', 'listed', 'shown',
            'and', 'or', 'but', 'so', 'yet', 'for', 'nor', 'as', 'at', 'by',
            'to', 'from', 'in', 'on', 'of', 'with', 'about', 'into', 'through',
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'first', 'second', 'third', 'total', 'count', 'number',
            'section', 'row', 'column', 'list', 'group', 'category',
            'intent', 'target', 'target_app', 'steps', 'action', 'action_type', 'initial_action',
            'reasoning', 'goal', 'step', 'launch', 'locate', 'tap', 'swipe', 'reveal',
            'elements', 'screen', 'launcher', 'icon', 'application', 'initial', 'type',
            'element', 'apps', 'showing', 'among', 'detected', 'current',
            'context', 'name', 'result', 'opens', 'example', 'description', 'only',
            'critical', 'task', 'rules', 'format', 'now', 'all', 'every', 'single',
            'bottom', 'rows', 'include', 'stop', 'line', 'explanations'
        }
        
        elements = []
        lines = text.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            cleaned = re.sub(r'^[\d\.\-\*\•\)]+\s*', '', line.strip())
            
            if '**' in cleaned or '::' in cleaned or '```' in cleaned:
                continue
            
            if cleaned.endswith(':'):
                continue
            
            if cleaned.lower() in EXPLANATION_WORDS:
                continue
            
            lower_start = cleaned.lower()[:15]
            if any(lower_start.startswith(word + ' ') or lower_start.startswith(word + ',')
                   for word in ['however', 'without', 'please', 'note', 'the', 'if', 'when', 'since', 'because']):
                continue
            
            quoted = re.findall(r'["\']([^"\']+)["\']', cleaned)
            for q in quoted:
                if (q.lower() not in EXPLANATION_WORDS and
                    not any(kw in q.lower() for kw in EXPLANATION_WORDS) and
                    2 <= len(q) <= 30):
                    elements.append(q)
            
            if re.match(r'^[A-Z][a-zA-Z\s0-9]{1,29}$', cleaned):
                word_lower = cleaned.lower()
                if (word_lower not in EXPLANATION_WORDS and
                    not any(kw in word_lower for kw in ['however', 'without', 'please', 'note', 'visible', 'cannot'])):
                    elements.append(cleaned)
                    continue
            
            words = cleaned.split()
            for i, word in enumerate(words):
                if word.lower() in EXPLANATION_WORDS:
                    continue
                
                if word and len(word) >= 2 and word[0].isupper():
                    app_name = word
                    for j in range(i+1, min(i+4, len(words))):
                        next_word = words[j]
                        if next_word and (next_word[0].isupper() or next_word.lower() in ['and', 'of', 'the']):
                            app_name += ' ' + next_word
                        else:
                            break
                    
                    if (2 <= len(app_name) <= 30 and
                        not app_name.endswith(('.', ',', '!', '?', ':')) and
                        app_name.lower() not in EXPLANATION_WORDS):
                        elements.append(app_name)
        
        seen = set()
        unique_elements = []
        for elem in elements:
            elem_lower = elem.lower()
            if (elem_lower not in seen and
                len(elem) >= 2 and
                elem_lower not in EXPLANATION_WORDS):
                seen.add(elem_lower)
                unique_elements.append(elem)
        
        return unique_elements
    
    def find_element_with_ai(self, screenshot_path: str, description: str, has_text: bool = True) -> Optional[Coordinates]:
        """
        PRIORITY SYSTEM:
        - For TEXTED elements: OCR first
        - For NON-TEXTED icons: Device Profile → CV/AI Detection
        """
        logger.info(f"🎯 Finding element: '{description}'")
        
        # CRITICAL: Let AI analyze screenshot and decide
        if self.use_ai_vision:
            has_text_label = self._ask_ai_has_text_label(screenshot_path, description)
        else:
            has_text_label = True
        
        # Route based on AI decision
        if has_text_label:
            # ═══════════════════════════════════════════════════════════
            # TEXTED ELEMENT PATH
            # ═══════════════════════════════════════════════════════════
            logger.info(f"   → Routing to TEXTED tool (AI detected text label)")
            
            result = self.texted_tool.find_text(screenshot_path, description)
            
            # AUTOMATIC FALLBACK: If texted fails, try non-texted
            if result is None:
                logger.warning("    Texted tool failed - AUTO FALLBACK to non-texted")
                result = self.non_texted_tool.find_element_with_ai(screenshot_path, description, is_texted=False)
            
            return result
        else:
            # ═══════════════════════════════════════════════════════════
            # NON-TEXTED ICON PATH - DEVICE PROFILE FIRST!
            # ═══════════════════════════════════════════════════════════
            logger.info(f"   → NON-TEXTED icon detected")
            logger.info(f"   → Priority 1: Checking DEVICE PROFILE...")
            
            # PRIORITY 1: Check device profile FIRST
            try:
                from backend.tools.device_coordinate_tool import get_device_coordinate_tool
                
                device_tool = get_device_coordinate_tool()
                profile_coords = device_tool.find_icon_coordinates(description)
                
                if profile_coords:
                    logger.info(f"✅ FOUND in device profile: {description} at {profile_coords}")
                    return Coordinates(
                        x=profile_coords[0],
                        y=profile_coords[1],
                        confidence=100,
                        source="device_profile"
                    )
                else:
                    logger.info(f"   → Not in profile, trying CV/AI detection...")
            except Exception as e:
                logger.warning(f"Device profile lookup failed: {e}")
            
            # PRIORITY 2: Fall back to CV/AI detection
            logger.info(f"   → Priority 2: Using CV/AI detection...")
            result = self.non_texted_tool.find_element_with_ai(screenshot_path, description, is_texted=False)
            
            # Auto-save successful CV/AI detection to profile
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
                    logger.info(f"💾 Auto-saved to device profile: {description}")
                except Exception as e:
                    logger.warning(f"Failed to auto-save coordinate: {e}")
            
            return result
    
    def find_in_app_grid(self, screenshot_path: str, app_name: str, context: str = "") -> Optional[Coordinates]:
        return self.texted_tool.find_in_app_grid(screenshot_path, app_name, context)
    
    def _verify_coordinates_with_ocr(self, screenshot_path: str, app_name: str, x: int, y: int) -> bool:
        try:
            img = Image.open(screenshot_path)
            
            left = max(0, x - 100)
            top = max(0, y - 100)
            right = min(img.width, x + 100)
            bottom = min(img.height, y + 100)
            
            region = img.crop((left, top, right, bottom))
            text = pytesseract.image_to_string(region, config='--psm 6').lower()
            
            app_lower = app_name.lower()
            found = app_lower in text
            
            if found:
                logger.debug(f"✅ OCR verification: '{app_name}' found at ({x}, {y})")
            else:
                logger.debug(f"❌ OCR verification: '{app_name}' NOT found at ({x}, {y})")
            
            return found
            
        except Exception as e:
            logger.error(f"OCR verification error: {e}")
            return False
    
    def _parse_coordinates_natural(self, ai_response: str, description: str, screen_width: int, screen_height: int) -> Optional[Coordinates]:
        not_found_keywords = ['not found', 'cannot find', 'unable to locate', 'not visible',
                              'not present', "can't find", "don't see", "isn't visible"]
        if any(keyword in ai_response.lower() for keyword in not_found_keywords):
            logger.warning(f"AI indicated '{description}' not found")
            return None
        
        patterns = [
            r'x[\s:=]+(\d+)[\s,]+y[\s:=]+(\d+)',
            r'\(?\s*(\d+)\s*,\s*(\d+)\s*\)?',
            r'(?:at|coordinates?)\s+(\d+)\s+(\d+)',
            r'(?:horizontal|x)[:\s]+(\d+).*?(?:vertical|y)[:\s]+(\d+)',
            r'\b(\d{3,4})\D+(\d{3,4})\b'
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
            if matches:
                try:
                    x = int(matches.group(1))
                    y = int(matches.group(2))
                    
                    if 0 <= x <= screen_width and 0 <= y <= screen_height:
                        logger.info(f"✅ Parsed coordinates: ({x}, {y})")
                        return Coordinates(x=x, y=y, confidence=85, source="ai_vision_natural")
                except:
                    continue
        
        logger.warning(f"Could not parse coordinates from: {ai_response[:150]}")
        return None
    
    def _create_grid_overlay(self, screenshot_path: str) -> str:
        try:
            img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(img)
            
            width, height = img.size
            grid_size = 100
            
            for x in range(0, width, grid_size):
                draw.line([(x, 0), (x, height)], fill=(0, 255, 0), width=1)
                draw.text((x + 5, 5), str(x), fill=(0, 255, 0))
            
            for y in range(0, height, grid_size):
                draw.line([(0, y), (width, y)], fill=(0, 255, 0), width=1)
                draw.text((5, y + 5), str(y), fill=(0, 255, 0))
            
            grid_path = screenshot_path.replace('.jpg', '_grid.jpg')
            img.save(grid_path)
            return grid_path
        except Exception as e:
            logger.error(f"Grid overlay error: {e}")
            return screenshot_path
    
    def _find_with_grid_overlay(self, screenshot_path: str, description: str) -> Optional[Coordinates]:
        try:
            screen_width, screen_height = self._get_screen_dimensions(screenshot_path)
            grid_path = self._create_grid_overlay(screenshot_path)
            
            prompt = f"""This image has a green grid with numbers.
Find: {description}
Using the grid numbers, tell me the center position.
Screen is {screen_width} x {screen_height} pixels.
RESPOND WITH ONLY:
X: [number]
Y: [number]
Your answer:"""
            
            ai_response = self.non_texted_tool._call_vision_api(grid_path, prompt)
            coords = self._parse_coordinates_natural(ai_response, description, screen_width, screen_height)
            
            if os.path.exists(grid_path):
                try:
                    os.remove(grid_path)
                except:
                    pass
            
            return coords
            
        except Exception as e:
            logger.error(f"Grid overlay error: {e}")
            return None
    
    def get_all_text(self, screenshot_path: str) -> List[TextElement]:
        return self.texted_tool.get_all_text(screenshot_path)


_vision_tool_instance = None

def get_vision_tool(model_preference: Optional[str] = None) -> VisionTool:
    global _vision_tool_instance
    
    if _vision_tool_instance is None:
        _vision_tool_instance = VisionTool(model_preference)
    elif model_preference and model_preference != _vision_tool_instance.non_texted_tool.current_model:
        _vision_tool_instance.switch_model(model_preference)
    
    return _vision_tool_instance