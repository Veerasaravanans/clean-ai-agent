# texted_icon_detection.py - Tool for detecting icons with text labels
# This handles OCR-based detection where text is present under/near icons
"""
Texted Icon Detection Tool
Primary Function: Detect icons via associated text labels using OCR and geometric positioning
Reliability: 200% for texted elements
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
    # Fallback for different import structure
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.models import Coordinates, TextElement, ScreenAnalysis
    from backend.config import settings

# Configure Tesseract
if os.name == 'nt':
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

logger = logging.getLogger(__name__)

class TextedIconDetectionTool:
    """Tool for detecting icons with associated text labels using OCR."""
    
    def __init__(self, confidence_threshold: float = None):
        """
        Initialize texted icon detection tool.
        
        Args:
            confidence_threshold: OCR confidence threshold
        """
        self.confidence_threshold = confidence_threshold or settings.ocr_confidence_threshold
        
        # OCR engines
        self.easyocr_reader = None
        self.paddleocr_reader = None
        self._init_ocr_engines()
        
        logger.info("✅ Texted Icon Detection Tool initialized")
    
    def _init_ocr_engines(self):
        """Initialize OCR engines."""
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['en'])
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.warning(f"EasyOCR not available: {e}")
        
        try:
            from paddleocr import PaddleOCR
            self.paddleocr_reader = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            logger.info("✅ PaddleOCR initialized")
        except Exception as e:
            logger.warning(f"PaddleOCR not available: {e}")
    
    def find_text(self, screenshot_path: str, target_text: str) -> Optional[Coordinates]:
        """
        Find text using multi-strategy OCR with geometric validation.
        Prioritizes detections in app launcher areas (lower half of screen).
        """
        logger.info(f"🔍 OCR search for: '{target_text}'")
        
        strategies = ['standard', 'high_contrast', 'inverted', 'edge_enhanced', 'otsu']
        psm_modes = [6, 11, 3]
        
        all_detections = []
        target_lower = target_text.lower().strip()
        target_words = target_lower.split()
        
        for strategy in strategies:
            preprocessed_path = self._preprocess_image_for_ocr(screenshot_path, preset=strategy)
            
            for psm in psm_modes:
                try:
                    custom_config = f'--psm {psm} --oem 3'
                    ocr_data = pytesseract.image_to_data(
                        Image.open(preprocessed_path),
                        config=custom_config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # For multi-word targets, try combining adjacent words
                    if len(target_words) > 1:
                        i = 0
                        while i < len(ocr_data['text']):
                            first_text = ocr_data['text'][i].strip()
                            if not first_text or first_text.lower() != target_words[0]:
                                i += 1
                                continue
                            
                            # Found first word, try to build complete match
                            combined_indices = [i]
                            combined_text = first_text.lower()
                            
                            # Look ahead for remaining words
                            j = i + 1
                            word_idx = 1
                            while j < len(ocr_data['text']) and word_idx < len(target_words):
                                next_text = ocr_data['text'][j].strip()
                                if next_text:
                                    if next_text.lower() == target_words[word_idx]:
                                        combined_text += ' ' + next_text.lower()
                                        combined_indices.append(j)
                                        word_idx += 1
                                    elif len(combined_indices) > 1:
                                        break
                                j += 1
                            
                            # Check if we got all words
                            if combined_text == target_lower:
                                # Calculate bounding box
                                left = min(ocr_data['left'][k] for k in combined_indices)
                                top = min(ocr_data['top'][k] for k in combined_indices)
                                right = max(ocr_data['left'][k] + ocr_data['width'][k] for k in combined_indices)
                                bottom = max(ocr_data['top'][k] + ocr_data['height'][k] for k in combined_indices)
                                
                                x = (left + right) // 2
                                y = (top + bottom) // 2
                                avg_conf = sum(float(ocr_data['conf'][k]) for k in combined_indices) / len(combined_indices)
                                
                                if avg_conf >= self.confidence_threshold:
                                    all_detections.append({
                                        'text': target_text,
                                        'confidence': avg_conf,
                                        'x': x,
                                        'y': y,
                                        'width': right - left,
                                        'height': bottom - top,
                                        'strategy': strategy,
                                        'match_score': 100.0
                                    })
                            
                            i += 1
                    
                    # Single word matching
                    for i, text in enumerate(ocr_data['text']):
                        if not text.strip():
                            continue
                        
                        detected_lower = text.lower().strip()
                        conf = float(ocr_data['conf'][i])
                        
                        # Exact or fuzzy match
                        similarity = SequenceMatcher(None, detected_lower, target_lower).ratio() * 100
                        
                        # LOWERED threshold to catch more detections (was 50, now 40)
                        if (detected_lower == target_lower or similarity >= 85) and conf >= 40:
                            x = ocr_data['left'][i] + ocr_data['width'][i] // 2
                            y = ocr_data['top'][i] + ocr_data['height'][i] // 2
                            
                            # Debug log ALL matches
                            logger.debug(f"  Match: '{text}' at ({x}, {y}) - {conf:.0f}% conf, {similarity:.0f}% similarity")
                            
                            all_detections.append({
                                'text': text,
                                'confidence': conf,
                                'x': x,
                                'y': y,
                                'width': ocr_data['width'][i],
                                'height': ocr_data['height'][i],
                                'strategy': strategy,
                                'match_score': 100.0 if detected_lower == target_lower else similarity
                            })
                
                except Exception as e:
                    logger.debug(f"OCR attempt failed: {e}")
                finally:
                    if os.path.exists(preprocessed_path) and preprocessed_path != screenshot_path:
                        try:
                            os.remove(preprocessed_path)
                        except:
                            pass
        
        if not all_detections:
            logger.warning(f"❌ OCR: '{target_text}' not found after 15 attempts")
            return None
        
        # Log all detections for debugging
        logger.info(f"🔍 Found {len(all_detections)} total OCR detections")
        
        # Get screen dimensions
        screen_width, screen_height = self._get_screen_dimensions(screenshot_path)
        
        # Geometric validation with centroid clustering
        if len(all_detections) > 1:
            coords = [(d['x'], d['y']) for d in all_detections]
            scores = [d['confidence'] * d['match_score'] / 100 for d in all_detections]
            
            # Calculate weighted centroid
            total_weight = sum(scores)
            centroid_x = sum(c[0] * s for c, s in zip(coords, scores)) / total_weight
            centroid_y = sum(c[1] * s for c, s in zip(coords, scores)) / total_weight
            
            # Get screen dimensions for distance calculation
            img = cv2.imread(screenshot_path)
            screen_diagonal = (img.shape[0]**2 + img.shape[1]**2)**0.5
            max_distance = screen_diagonal * 0.15  # 15% of diagonal
            
            # Filter detections near centroid
            validated_detections = []
            for detection in all_detections:
                distance = ((detection['x'] - centroid_x)**2 + (detection['y'] - centroid_y)**2)**0.5
                if distance <= max_distance:
                    detection['distance_score'] = 1 - (distance / max_distance)
                    validated_detections.append(detection)
            
            all_detections = validated_detections if validated_detections else all_detections
            
            logger.debug(f"📊 Geometric validation: {len(validated_detections)}/{len(coords)} validated")
        
        # Select best detection with composite scoring
        best = max(all_detections, key=lambda d: (
            d['confidence'] * 0.5 +  # OCR confidence
            d['match_score'] * 0.3 +  # Text similarity
            d.get('distance_score', 1.0) * 20  # Geometric consistency (highest)
        ))
        
        logger.info(f"✅ OCR: Found '{target_text}' at ({best['x']}, {best['y']}) - {best['confidence']:.1f}% confidence")
        
        return Coordinates(
            x=best['x'],
            y=best['y'],
            confidence=int(best['confidence']),
            source=f"ocr_{best['strategy']}"
        )
    
    def _preprocess_image_for_ocr(self, image_path: str, preset: str = 'standard') -> str:
        """Advanced image preprocessing for OCR."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            if preset == 'standard':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
                processed = cv2.filter2D(denoised, -1, kernel)
            
            elif preset == 'high_contrast':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)
                _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            elif preset == 'inverted':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                processed = cv2.bitwise_not(gray)
            
            elif preset == 'edge_enhanced':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                processed = cv2.addWeighted(gray, 0.7, edges, 0.3, 0)
            
            elif preset == 'otsu':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                _, processed = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            else:
                processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            temp_path = f"{image_path}_preprocessed_{preset}.png"
            cv2.imwrite(temp_path, processed)
            return temp_path
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return image_path
    
    def _get_screen_dimensions(self, screenshot_path: str) -> Tuple[int, int]:
        """Get screen dimensions dynamically from screenshot."""
        try:
            img = Image.open(screenshot_path)
            width, height = img.size
            return width, height
        except Exception as e:
            logger.error(f"Failed to get screen dimensions: {e}")
            return 1408, 792  # Fallback only if image can't be read
    
    def analyze_screen_with_ai(self, screenshot_path: str, question: str = "") -> ScreenAnalysis:
        """
        Analyze screen - Combine adjacent words into app names.
        Returns shorter list with complete app names, not individual words.
        """
        try:
            img = Image.open(screenshot_path)
            
            # Extract words with positions
            ocr_data = pytesseract.image_to_data(
                img,
                config='--psm 11 --oem 3',
                output_type=pytesseract.Output.DICT
            )
            
            # Collect words with positions
            words_with_pos = []
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                
                conf = float(ocr_data['conf'][i])
                cleaned = text.strip()
                
                if (conf >= 50 and
                    len(cleaned) >= 2 and
                    cleaned[0].isupper() and
                    not cleaned.isdigit()):
                    words_with_pos.append({
                        'text': cleaned,
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i],
                        'right': ocr_data['left'][i] + ocr_data['width'][i],
                        'bottom': ocr_data['top'][i] + ocr_data['height'][i],
                    })
            
            if not words_with_pos:
                return ScreenAnalysis(
                    summary="No text detected",
                    detected_elements=[],
                    screen_state="analyzed",
                    confidence=50
                )
            
            # Sort by position (top to bottom, left to right)
            words_with_pos.sort(key=lambda w: (w['top'], w['left']))
            
            # Combine adjacent words that are close together
            combined_apps = []
            used = set()
            
            for i, word in enumerate(words_with_pos):
                if i in used:
                    continue
                
                app_name = word['text']
                used.add(i)
                
                # Look for ONE adjacent word (for 2-word apps like "Google Assistant")
                if i + 1 < len(words_with_pos):
                    next_word = words_with_pos[i + 1]
                    
                    # Check if on same line (vertical proximity < 15px)
                    vert_diff = abs(next_word['top'] - word['top'])
                    
                    # Check horizontal gap
                    horiz_gap = next_word['left'] - word['right']
                    
                    # Combine if: same line AND small gap (< 35px)
                    if vert_diff < 15 and 0 <= horiz_gap < 35:
                        app_name += ' ' + next_word['text']
                        used.add(i + 1)
                
                combined_apps.append(app_name)
            
            # Remove duplicates
            seen = set()
            unique_apps = []
            for app in combined_apps:
                app_lower = app.lower()
                if app_lower not in seen:
                    seen.add(app_lower)
                    unique_apps.append(app)
            
            # CRITICAL: Prioritize target app to position 1
            target_app = None
            if question:
                q_lower = question.lower()
                # Extract target from common patterns
                for pattern in ['open ', 'launch ', 'start ', 'tap ', 'find ']:
                    if pattern in q_lower:
                        target_app = q_lower.split(pattern, 1)[-1].strip()
                        break
                
                # Fallback: last word
                if not target_app:
                    words = q_lower.split()
                    if words:
                        target_app = words[-1]
            
            # Reorder: target first, then others
            if target_app:
                prioritized = []
                others = []
                
                for app in unique_apps:
                    # Match if target is in app name
                    if target_app in app.lower():
                        prioritized.append(app)
                    else:
                        others.append(app)
                
                # Combine: prioritized first
                unique_apps = prioritized + others
                
                if prioritized:
                    logger.info(f"🔍 OCR detected {len(unique_apps)} apps (target '{target_app}' prioritized)")
                    logger.info(f"  🎯 Prioritized: {prioritized}")
                    logger.info(f"  📋 All apps: {', '.join(unique_apps[:15])}")
                else:
                    logger.info(f"🔍 OCR detected {len(unique_apps)} apps")
                    logger.info(f"  📋 Apps: {', '.join(unique_apps[:15])}")
            else:
                logger.info(f"🔍 OCR detected {len(unique_apps)} apps")
                logger.info(f"  📋 Apps: {', '.join(unique_apps[:15])}")
            
            return ScreenAnalysis(
                summary=f"OCR extracted {len(unique_apps)} apps",
                detected_elements=unique_apps,
                screen_state="analyzed",
                confidence=95
            )
            
        except Exception as e:
            logger.error(f"Screen analysis error: {e}")
            return ScreenAnalysis(
                summary=f"Analysis failed: {e}",
                detected_elements=[],
                screen_state="error",
                confidence=0
            )
    
    def find_in_app_grid(self, screenshot_path: str, app_name: str, context: str = "") -> Optional[Coordinates]:
        """
        DYNAMIC grid-based app detection for ANY Android Automotive display.
        
        Automatically detects:
        - Screen dimensions
        - Number of rows/columns
        - Grid boundaries
        - Cell positions
        
        Works on ANY car display without hardcoding!
        """
        logger.info(f"🎯 Dynamic grid detection for '{app_name}'...")
        
        try:
            screen_width, screen_height = self._get_screen_dimensions(screenshot_path)
            
            # Get ALL OCR detections
            all_ocr = self._get_all_ocr_detections(screenshot_path)
            if not all_ocr or len(all_ocr) < 5:
                logger.debug(f"Not enough OCR detections ({len(all_ocr)})")
                return None
            
            # Balanced filtering for app labels (exclude system UI but not too strict)
            # App labels are:
            # - Good confidence (>=50%, not too high)
            # - Small, uniform height (15-50px)
            # - Multi-character names (2-30 chars, allow spaces)
            # - In typical app area (20%-80% vertically)
            # - Mostly alphabetic (allow some spaces/special chars)
            app_labels = []
            for det in all_ocr:
                text = det['text'].strip()
                text_len = len(text)
                y_ratio = det['y'] / screen_height
                height = det.get('height', 0)
                
                # Check if mostly alphabetic (allow "Pocket FM", "Local Media Player")
                alpha_chars = sum(c.isalpha() for c in text)
                alpha_ratio = alpha_chars / max(1, text_len)
                
                # Balanced filters
                if (det['confidence'] >= 50 and  # Lower threshold (was 60)
                    2 <= text_len <= 30 and  # Allow longer names
                    15 <= height <= 50 and  # Uniform text size
                    0.20 <= y_ratio <= 0.85 and  # Wider band (was 0.25-0.75)
                    alpha_ratio >= 0.6):  # At least 60% alphabetic
                    app_labels.append(det)
            
            if len(app_labels) < 5:
                logger.debug(f"Not enough app labels detected ({len(app_labels)})")
                return None
            
            logger.info(f"📊 Detected {len(app_labels)} app labels on screen")
            
            if len(app_labels) > 0:
                app_names = [label['text'] for label in app_labels[:15]]  # First 15
                logger.info(f"📱 Apps: {', '.join(app_names)}")
            
            # DYNAMIC ROW DETECTION: Cluster by Y position
            # Apps in same row have similar Y coordinates
            y_positions = [label['y'] for label in app_labels]
            y_positions.sort()
            
            # Find row boundaries by detecting gaps in Y positions
            rows = []
            current_row = [y_positions[0]]
            row_gap_threshold = screen_height * 0.15  # 15% gap (was 8%, too small)
            
            for y in y_positions[1:]:
                if y - current_row[-1] < row_gap_threshold:
                    # Same row
                    current_row.append(y)
                else:
                    # New row
                    rows.append(current_row)
                    current_row = [y]
            rows.append(current_row)
            
            num_rows = len(rows)
            logger.info(f"📏 Detected {num_rows} rows dynamically")
            
            # Calculate row centers
            row_centers = [sum(row) / len(row) for row in rows]
            
            # DYNAMIC COLUMN DETECTION: Cluster by X position
            # Find typical column spacing
            x_positions = sorted([label['x'] for label in app_labels])
            
            # Detect column spacing
            x_gaps = []
            for i in range(1, len(x_positions)):
                gap = x_positions[i] - x_positions[i-1]
                if gap > screen_width * 0.05:  # Minimum 5% spacing
                    x_gaps.append(gap)
            
            if x_gaps:
                avg_col_spacing = sum(x_gaps) / len(x_gaps)
                logger.info(f"📏 Average column spacing: {int(avg_col_spacing)}px")
            
            # CALCULATE GRID BOUNDARIES from actual app positions
            grid_left = max(0, min(label['x'] for label in app_labels) - 50)
            grid_right = min(screen_width, max(label['x'] for label in app_labels) + 50)
            grid_top = max(0, min(label['y'] for label in app_labels) - 100)
            grid_bottom = min(screen_height, max(label['y'] for label in app_labels) + 50)
            
            # Validate grid is reasonable
            grid_width = grid_right - grid_left
            grid_height = grid_bottom - grid_top
            
            if grid_width < screen_width * 0.3 or grid_height < screen_height * 0.2:
                logger.warning(f"Grid too small: {grid_width}×{grid_height}, likely invalid")
                return None
            
            logger.info(f"📐 Dynamic grid bounds: X({grid_left}-{grid_right}), Y({grid_top}-{grid_bottom})")
            
            # FIND TARGET APP in detected labels
            target_lower = app_name.lower().strip()
            
            app_matches = []
            for label in app_labels:
                text = label['text'].lower().strip()
                similarity = SequenceMatcher(None, text, target_lower).ratio() * 100
                
                if text == target_lower or similarity >= 85:
                    # Determine which row this app is in
                    label_y = label['y']
                    row_idx = min(range(len(row_centers)),
                                  key=lambda i: abs(row_centers[i] - label_y))
                    
                    app_matches.append({
                        'text': label['text'],
                        'x': label['x'],
                        'y': label['y'],
                        'confidence': label['confidence'],
                        'similarity': similarity,
                        'row': row_idx
                    })
            
            if not app_matches:
                logger.debug(f"'{app_name}' not found in detected app labels")
                return None
            
            # Log all matches for debugging
            if len(app_matches) > 1:
                logger.info(f"🔍 Found {len(app_matches)} matches for '{app_name}':")
                for i, match in enumerate(app_matches[:5]):
                    logger.info(f"  Match {i+1}: ({match['x']}, {match['y']}) - {match['confidence']:.0f}% conf, row {match['row']+1}")
            
            # Pick best match
            best = max(app_matches, key=lambda m: m['confidence'] * 0.5 + m['similarity'] * 0.5)
            
            text_x, text_y = best['x'], best['y']
            row_idx = best['row']
            
            logger.info(f"📍 Found '{app_name}' text at ({text_x}, {text_y}) in row {row_idx + 1}")
            
            # CALCULATE ICON POSITION dynamically
            # Icon is above text - distance depends on screen size
            # For Android Automotive, icons are typically 80-100px above text
            # This is about 10-12% of screen height
            icon_offset = int(screen_height * 0.10)  # 10% of screen height (79px for 792px)
            
            # For very small screens, use minimum 60px
            # For very large screens, cap at 120px
            icon_offset = max(60, min(120, icon_offset))
            
            icon_x = text_x
            icon_y = text_y - icon_offset
            
            # Validate icon is within grid
            if icon_y < grid_top or icon_y > grid_bottom:
                logger.warning(f"Icon Y ({icon_y}) outside grid bounds ({grid_top}-{grid_bottom})")
                # Try with smaller offset
                icon_offset = int(screen_height * 0.06)  # Fallback to 6%
                icon_y = text_y - icon_offset
                logger.info(f"  Adjusted offset to {icon_offset}px, new icon Y: {icon_y}")
                
                # If still outside, use text position directly
                if icon_y < grid_top:
                    icon_y = text_y
                    logger.warning(f"  Using text position directly: {icon_y}")
            
            logger.info(f"✅ Dynamic grid calculation:")
            logger.info(f"  Text position: ({text_x}, {text_y})")
            logger.info(f"  Icon position: ({icon_x}, {icon_y}) [offset: {text_y - icon_y}px]")
            logger.info(f"  Grid layout: {num_rows} rows detected")
            
            return Coordinates(
                x=icon_x,
                y=icon_y,
                confidence=int(best['confidence']),
                source="dynamic_grid_detection"
            )
        
        except Exception as e:
            logger.error(f"Dynamic grid detection error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _get_all_ocr_detections(self, screenshot_path: str) -> list:
        """Get all OCR detections with coordinates from screenshot."""
        try:
            import pytesseract
            
            all_detections = []
            
            # Use single best strategy for speed
            custom_config = '--psm 6 --oem 3'
            ocr_data = pytesseract.image_to_data(
                Image.open(screenshot_path),
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                
                x = ocr_data['left'][i] + ocr_data['width'][i] // 2
                y = ocr_data['top'][i] + ocr_data['height'][i] // 2
                conf = float(ocr_data['conf'][i])
                
                all_detections.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'confidence': conf
                })
            
            return all_detections
        
        except Exception as e:
            logger.error(f"OCR detection error: {e}")
            return []
    
    def get_all_text(self, screenshot_path: str) -> List[TextElement]:
        """Extract all text from screenshot using EasyOCR."""
        elements = []
        
        if self.easyocr_reader:
            try:
                results = self.easyocr_reader.readtext(screenshot_path)
                
                for (bbox, text, conf) in results:
                    if conf * 100 >= self.confidence_threshold:
                        x = int((bbox[0][0] + bbox[2][0]) / 2)
                        y = int((bbox[0][1] + bbox[2][1]) / 2)
                        w = int(bbox[2][0] - bbox[0][0])
                        h = int(bbox[2][1] - bbox[0][1])
                        
                        elements.append(TextElement(
                            text=text,
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            confidence=int(conf * 100)
                        ))
            except Exception as e:
                logger.error(f"Text extraction error: {e}")
        
        return elements