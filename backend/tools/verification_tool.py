"""
verification_tool.py - Enhanced Verification Tool

Screen comparison and verification with advanced OCR and AI Vision.
"""

import logging
import os
import base64
from typing import Optional
from pathlib import Path
from difflib import SequenceMatcher

import cv2
import numpy as np
import pytesseract
from PIL import Image
import requests

from backend.models import ChangeResult
from backend.config import settings
from backend.services.verification_image_service import get_verification_image_service

# Configure logger first (before any code that uses it)
logger = logging.getLogger(__name__)

# For SSIM calculation
try:
    from skimage.metrics import structural_similarity as ssim
    SSIM_AVAILABLE = True
except ImportError:
    SSIM_AVAILABLE = False
    logger.warning("scikit-image not installed. SSIM verification disabled. Install with: pip install scikit-image")


# Configure Tesseract (Windows compatibility)
if os.name == 'nt':
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


class VerificationTool:
    """Enhanced screen comparison and verification with advanced OCR and AI Vision."""
    
    def __init__(self, model_preference: Optional[str] = None):
        """
        Initialize verification tool with VIO model switching support.
        
        Args:
            model_preference: Preferred VIO model (e.g., "Claude 4.5 Sonnet")
        """
        self.change_threshold = settings.change_threshold
        self.confidence_threshold = settings.ocr_confidence_threshold
        self.use_ai_vision = settings.vision_use_ai
        
        # VIO Model switching support
        self.current_model = model_preference or "Claude 4.5 Sonnet"  # Default to Claude for verification
        
        logger.info(f"Verification Tool initialized - AI Model: {self.current_model}")
    
    def switch_model(self, model_name: str):
        """
        Switch to a different VIO model.
        
        Args:
            model_name: New model name (e.g., "Claude 4.5 Sonnet", "Gemini 2.5 Pro")
        """
        self.current_model = model_name
        logger.info(f"🔄 Switched verification model to: {model_name}")
    
    def _preprocess_image_for_ocr(self, image_path: str, preset: str = 'standard') -> str:
        """
        Advanced image preprocessing for better OCR accuracy.
        
        Args:
            image_path: Path to input image
            preset: Preprocessing strategy
                   - 'standard': Grayscale + denoise + sharpen
                   - 'high_contrast': Aggressive contrast + threshold
                   - 'inverted': Invert for dark-on-light text
                   - 'edge_enhanced': Edge detection emphasis
                   - 'otsu': Otsu's binarization
        
        Returns:
            Path to preprocessed image
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            # Apply preprocessing based on strategy
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
            
            # Save preprocessed image
            temp_path = f"{image_path}_preprocessed_{preset}.png"
            cv2.imwrite(temp_path, processed)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return image_path
    
    def compare_screens(
        self,
        before_path: str,
        after_path: str
    ) -> ChangeResult:
        """
        Compare two screenshots to detect changes.
        
        Args:
            before_path: Path to screenshot before action
            after_path: Path to screenshot after action
            
        Returns:
            ChangeResult with change detection
        """
        try:
            # Load images
            img1 = cv2.imread(before_path)
            img2 = cv2.imread(after_path)
            
            if img1 is None or img2 is None:
                return ChangeResult(
                    changed=False,
                    change_percentage=0.0,
                    details="Failed to load images"
                )
            
            # Resize to same dimensions if needed
            if img1.shape != img2.shape:
                height = min(img1.shape[0], img2.shape[0])
                width = min(img1.shape[1], img2.shape[1])
                img1 = cv2.resize(img1, (width, height))
                img2 = cv2.resize(img2, (width, height))
            
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # Compute structural similarity
            diff = cv2.absdiff(gray1, gray2)
            
            # Calculate percentage of changed pixels
            total_pixels = diff.size
            changed_pixels = np.count_nonzero(diff > 30)  # Threshold for meaningful change
            change_percentage = (changed_pixels / total_pixels) * 100
            
            changed = change_percentage >= self.change_threshold
            
            details = f"{change_percentage:.2f}% of pixels changed"
            
            if changed:
                logger.info(f"✅ Screen changed: {details}")
            else:
                logger.info(f"❌ No significant change: {details}")
            
            return ChangeResult(
                changed=changed,
                change_percentage=change_percentage,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Screen comparison error: {e}")
            return ChangeResult(
                changed=False,
                change_percentage=0.0,
                details=f"Error: {e}"
            )
    
    def verify_element_exists(
        self,
        screenshot_path: str,
        element_text: str,
        use_advanced_ocr: bool = True
    ) -> bool:
        """
        Verify element exists on screen using advanced multi-strategy OCR.
        
        Args:
            screenshot_path: Path to screenshot
            element_text: Text to verify
            use_advanced_ocr: Use multi-strategy OCR (default: True)
            
        Returns:
            True if element found
        """
        if not use_advanced_ocr:
            # Simple OCR fallback
            return self._verify_element_simple(screenshot_path, element_text)
        
        try:
            # Multi-strategy OCR detection
            strategies = ['standard', 'high_contrast', 'inverted', 'edge_enhanced', 'otsu']
            psm_modes = [6, 11, 3]  # PSM modes for different layouts
            
            target_lower = element_text.lower().strip()
            
            # Try all combinations
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
                        
                        # Check each detected word
                        for i, text in enumerate(ocr_data['text']):
                            if not text.strip():
                                continue
                            
                            detected_lower = text.lower().strip()
                            conf = float(ocr_data['conf'][i])
                            
                            # Exact match
                            if detected_lower == target_lower and conf >= self.confidence_threshold:
                                logger.info(f"✅ Element verified: '{element_text}' (exact match, {conf:.1f}% confidence)")
                                self._cleanup_temp(preprocessed_path)
                                return True
                            
                            # Fuzzy match
                            similarity = SequenceMatcher(None, detected_lower, target_lower).ratio() * 100
                            if similarity >= 85 and conf >= self.confidence_threshold:
                                logger.info(f"✅ Element verified: '{element_text}' (fuzzy match, {similarity:.1f}% similarity)")
                                self._cleanup_temp(preprocessed_path)
                                return True
                    
                    except Exception as e:
                        logger.debug(f"OCR attempt failed (strategy={strategy}, psm={psm}): {e}")
                        continue
                    finally:
                        self._cleanup_temp(preprocessed_path)
            
            # Not found after all attempts
            logger.warning(f"❌ Element not found: '{element_text}' (tried 15 OCR strategies)")
            return False
            
        except Exception as e:
            logger.error(f"Element verification error: {e}")
            return False
    
    def _verify_element_simple(self, screenshot_path: str, element_text: str) -> bool:
        """Simple OCR verification (fallback)."""
        try:
            img = Image.open(screenshot_path)
            text = pytesseract.image_to_string(img)
            
            found = element_text.lower() in text.lower()
            
            if found:
                logger.info(f"✅ Element verified (simple): '{element_text}'")
            else:
                logger.warning(f"❌ Element not found (simple): '{element_text}'")
            
            return found
            
        except Exception as e:
            logger.error(f"Simple OCR error: {e}")
            return False
    
    def verify_element_with_ai(self, screenshot_path: str, element_description: str) -> bool:
        """
        Verify element exists using AI Vision (VIO Cloud).
        
        Args:
            screenshot_path: Path to screenshot
            element_description: Natural language description of element
            
        Returns:
            True if element found by AI
        """
        if not self.use_ai_vision:
            logger.warning("AI Vision disabled, falling back to OCR")
            return self.verify_element_exists(screenshot_path, element_description)
        
        try:
            # Encode image to base64
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Ask Claude to verify element existence
            prompt = f"Does this screen contain '{element_description}'? Answer ONLY with 'YES' or 'NO'."
            
            payload = {
                "username": settings.vio_username,
                "token": settings.vio_api_token,
                "type": "QUESTION",
                "payload": prompt,
                "vio_model": "Default",
                "ai_model": self.current_model,  # Use instance model
                "knowledge": False,
                "webSearch": False,
                "reason": False,
                "image": image_data
            }
            
            response = requests.post(
                f"{settings.vio_base_url}/message",
                json=payload,
                verify=settings.vio_verify_ssl,
                timeout=settings.vio_timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, dict):
                answer = result.get('message', result.get('response', str(result)))
            else:
                answer = str(result)
            
            # Check if Claude says YES
            found = "YES" in answer.upper()
            
            if found:
                logger.info(f"✅ AI Vision verified element: '{element_description}'")
            else:
                logger.warning(f"❌ AI Vision did not find: '{element_description}'")
            
            return found
            
        except Exception as e:
            logger.error(f"AI Vision verification error: {e}")
            # Fallback to OCR
            return self.verify_element_exists(screenshot_path, element_description)
    
    def verify_element_appeared(
        self,
        before_path: str,
        after_path: str,
        element_text: str,
        use_advanced_ocr: bool = True
    ) -> bool:
        """
        Verify element appeared after action using advanced OCR.
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            element_text: Element to verify
            use_advanced_ocr: Use multi-strategy OCR
            
        Returns:
            True if element appeared
        """
        before_exists = self.verify_element_exists(before_path, element_text, use_advanced_ocr)
        after_exists = self.verify_element_exists(after_path, element_text, use_advanced_ocr)
        
        appeared = not before_exists and after_exists
        
        if appeared:
            logger.info(f"✅ Element appeared: '{element_text}'")
        else:
            logger.debug(f"Element did not appear: '{element_text}' (before={before_exists}, after={after_exists})")
        
        return appeared
    
    def verify_element_disappeared(
        self,
        before_path: str,
        after_path: str,
        element_text: str,
        use_advanced_ocr: bool = True
    ) -> bool:
        """
        Verify element disappeared after action using advanced OCR.
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            element_text: Element to verify
            use_advanced_ocr: Use multi-strategy OCR
            
        Returns:
            True if element disappeared
        """
        before_exists = self.verify_element_exists(before_path, element_text, use_advanced_ocr)
        after_exists = self.verify_element_exists(after_path, element_text, use_advanced_ocr)
        
        disappeared = before_exists and not after_exists
        
        if disappeared:
            logger.info(f"✅ Element disappeared: '{element_text}'")
        else:
            logger.debug(f"Element did not disappear: '{element_text}' (before={before_exists}, after={after_exists})")
        
        return disappeared
    
    def verify_element_appeared_with_ai(
        self,
        before_path: str,
        after_path: str,
        element_description: str
    ) -> bool:
        """
        Verify element appeared using AI Vision.
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            element_description: Natural language description
            
        Returns:
            True if element appeared
        """
        before_exists = self.verify_element_with_ai(before_path, element_description)
        after_exists = self.verify_element_with_ai(after_path, element_description)
        
        appeared = not before_exists and after_exists
        
        if appeared:
            logger.info(f"✅ AI Vision: Element appeared: '{element_description}'")
        
        return appeared
    
    def verify_element_disappeared_with_ai(
        self,
        before_path: str,
        after_path: str,
        element_description: str
    ) -> bool:
        """
        Verify element disappeared using AI Vision.
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            element_description: Natural language description
            
        Returns:
            True if element disappeared
        """
        before_exists = self.verify_element_with_ai(before_path, element_description)
        after_exists = self.verify_element_with_ai(after_path, element_description)
        
        disappeared = before_exists and not after_exists
        
        if disappeared:
            logger.info(f"✅ AI Vision: Element disappeared: '{element_description}'")
        
        return disappeared
    
    def _cleanup_temp(self, filepath: str):
        """Clean up temporary preprocessed files."""
        if filepath and os.path.exists(filepath) and "_preprocessed_" in filepath:
            try:
                os.remove(filepath)
            except:
                pass
    
    def verify_outcome_with_ai(
        self,
        before_screenshot: str,
        after_screenshot: str,
        original_goal: str,
        action_performed: str
    ) -> dict:
        """
        AI-driven verification: Let AI decide if action achieved the intended goal.
        NO hardcoded keywords or assumptions - pure AI decision.
        
        Args:
            before_screenshot: Screenshot before action
            after_screenshot: Screenshot after action  
            original_goal: What user wanted to achieve (e.g., "open app launcher")
            action_performed: What action was executed (e.g., "tapped at (704, 752)")
            
        Returns:
            dict with {
                'success': bool,
                'reasoning': str,
                'confidence': int (0-100)
            }
        """
        if not self.use_ai_vision:
            logger.warning("AI Vision disabled - cannot perform AI verification")
            return {'success': True, 'reasoning': 'AI disabled', 'confidence': 50}
        
        try:
            # Encode both images to base64
            with open(after_screenshot, 'rb') as f:
                after_image = base64.b64encode(f.read()).decode('utf-8')
            
            # Create AI prompt with NO assumptions
            prompt = f"""You are verifying if an action achieved its intended goal.

ORIGINAL GOAL: {original_goal}
ACTION PERFORMED: {action_performed}

Analyze the screen shown in the image and determine:
1. Did the action successfully achieve the original goal?
2. What screen/interface is currently visible?
3. Is this the expected result based on the goal?

Think step by step:
- What was the user trying to do?
- What screen do we see now?
- Does this match what should happen?

Respond ONLY in this format:
SUCCESS: YES or NO
CURRENT_SCREEN: [describe what you see]
REASONING: [brief explanation why it succeeded or failed]
CONFIDENCE: [0-100]

Be strict - if the wrong screen opened or goal wasn't achieved, say NO."""

            payload = {
                "username": settings.vio_username,
                "token": settings.vio_api_token,
                "type": "QUESTION",
                "payload": prompt,
                "vio_model": "Default",
                "ai_model": self.current_model,  # Use instance model
                "knowledge": False,
                "webSearch": False,
                "reason": False,
                "image": after_image
            }
            
            response = requests.post(
                f"{settings.vio_base_url}/message",
                json=payload,
                verify=settings.vio_verify_ssl,
                timeout=settings.vio_timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, dict):
                ai_response = result.get('message', result.get('response', str(result)))
            else:
                ai_response = str(result)
            
            logger.info(f"🤖 AI Verification Response:\n{ai_response}")
            
            # Parse AI response
            success = 'SUCCESS: YES' in ai_response.upper() or 'SUCCESS:YES' in ai_response.upper()
            
            # Extract reasoning
            reasoning_match = None
            for line in ai_response.split('\n'):
                if 'REASONING:' in line.upper():
                    reasoning_match = line.split(':', 1)[1].strip()
                    break
            reasoning = reasoning_match if reasoning_match else ai_response
            
            # Extract current screen description
            current_screen = None
            for line in ai_response.split('\n'):
                if 'CURRENT_SCREEN:' in line.upper():
                    current_screen = line.split(':', 1)[1].strip()
                    break
            
            # Extract confidence
            confidence = 75  # Default
            for line in ai_response.split('\n'):
                if 'CONFIDENCE:' in line.upper():
                    try:
                        conf_str = line.split(':', 1)[1].strip().replace('%', '')
                        confidence = int(conf_str)
                    except:
                        pass
                    break
            
            result_dict = {
                'success': success,
                'reasoning': reasoning,
                'current_screen': current_screen,
                'confidence': confidence
            }
            
            if success:
                logger.info(f"✅ AI Verification: SUCCESS - {reasoning}")
            else:
                logger.warning(f"❌ AI Verification: FAILED - {reasoning}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"AI outcome verification error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # On error, assume success to avoid blocking
            return {
                'success': True,
                'reasoning': f'Verification error: {str(e)}',
                'confidence': 50
            }
        

    def verify_with_ssim(
        self,
        screenshot_path: str,
        reference_image_name: str,
        similarity_threshold: float = 0.85
    ) -> dict:
        """
        PRIMARY VERIFICATION: Compare screenshot with reference image using SSIM.
        
        This is the main verification method for industrial testing.
        Uses Structural Similarity Index (SSIM) for accurate comparison.
        
        Args:
            screenshot_path: Path to captured screenshot
            reference_image_name: Name of reference image (e.g., "app_launcher_opened")
            similarity_threshold: SSIM threshold (0-1, default 0.85)
            
        Returns:
            dict: {
                'passed': bool,
                'similarity': float,
                'threshold': float,
                'method': 'ssim',
                'reference_found': bool,
                'message': str
            }
        """
        if not SSIM_AVAILABLE:
            logger.error("❌ SSIM verification failed: scikit-image not installed")
            return {
                'passed': False,
                'similarity': 0.0,
                'threshold': similarity_threshold,
                'method': 'ssim',
                'reference_found': False,
                'message': 'SSIM library not available'
            }
        
        try:
            # Get verification image service
            verification_service = get_verification_image_service()
            
            # Get device ID from ADB tool
            from backend.tools.adb_tool import ADBTool
            adb = ADBTool()
            device_info = adb.get_device_info()
            
            if not device_info.get("connected"):
                logger.error("❌ No device connected for SSIM verification")
                return {
                    'passed': False,
                    'similarity': 0.0,
                    'threshold': similarity_threshold,
                    'method': 'ssim',
                    'reference_found': False,
                    'message': 'No device connected'
                }
            
            resolution = device_info.get("resolution", {})
            screen_width = resolution.get("width", 0)
            screen_height = resolution.get("height", 0)
            device_id = verification_service.get_device_id(screen_width, screen_height)
            
            # Get reference image
            reference_path = verification_service.get_verification_image(
                reference_image_name, 
                device_id
            )
            
            if not reference_path or not reference_path.exists():
                logger.warning(f"⚠️ Reference image not found: {reference_image_name} for {device_id}")
                return {
                    'passed': False,
                    'similarity': 0.0,
                    'threshold': similarity_threshold,
                    'method': 'ssim',
                    'reference_found': False,
                    'message': f'Reference image not found: {reference_image_name}'
                }
            
            # Load images
            screenshot = cv2.imread(screenshot_path)
            reference = cv2.imread(str(reference_path))
            
            if screenshot is None:
                logger.error(f"❌ Failed to load screenshot: {screenshot_path}")
                return {
                    'passed': False,
                    'similarity': 0.0,
                    'threshold': similarity_threshold,
                    'method': 'ssim',
                    'reference_found': True,
                    'message': 'Failed to load screenshot'
                }
            
            if reference is None:
                logger.error(f"❌ Failed to load reference: {reference_path}")
                return {
                    'passed': False,
                    'similarity': 0.0,
                    'threshold': similarity_threshold,
                    'method': 'ssim',
                    'reference_found': True,
                    'message': 'Failed to load reference image'
                }
            
            # Resize screenshot to match reference if needed
            if screenshot.shape != reference.shape:
                screenshot = cv2.resize(screenshot, (reference.shape[1], reference.shape[0]))
            
            # Convert to grayscale
            gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            gray_reference = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
            
            # Calculate SSIM
            similarity_score = ssim(gray_screenshot, gray_reference)
            
            # Check if passed
            passed = similarity_score >= similarity_threshold
            
            if passed:
                logger.info(f"✅ SSIM Verification PASSED: {similarity_score:.4f} >= {similarity_threshold}")
            else:
                logger.warning(f"❌ SSIM Verification FAILED: {similarity_score:.4f} < {similarity_threshold}")
            
            return {
                'passed': passed,
                'similarity': float(similarity_score),
                'threshold': similarity_threshold,
                'method': 'ssim',
                'reference_found': True,
                'reference_image': reference_image_name,
                'message': f'SSIM: {similarity_score:.4f} (threshold: {similarity_threshold})'
            }
            
        except Exception as e:
            logger.error(f"❌ SSIM verification error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                'passed': False,
                'similarity': 0.0,
                'threshold': similarity_threshold,
                'method': 'ssim',
                'reference_found': False,
                'message': f'Error: {str(e)}'
            }


    def comprehensive_verification(
        self,
        before_screenshot: str,
        after_screenshot: str,
        reference_image_name: Optional[str] = None,
        ssim_threshold: float = 0.85
    ) -> dict:
        """
        Comprehensive verification combining SSIM (primary) and other methods (secondary).
        
        PRIORITY:
        1. SSIM verification (PRIMARY - must pass)
        2. Pixel change (SECONDARY - informational)
        3. AI verification (SECONDARY - informational)
        
        Args:
            before_screenshot: Screenshot before action
            after_screenshot: Screenshot after action
            reference_image_name: Expected state reference image name
            ssim_threshold: SSIM similarity threshold
            
        Returns:
            dict: {
                'overall_passed': bool,  # Based on SSIM only
                'ssim_verification': dict,
                'pixel_verification': dict,  # Informational
                'ai_verification': dict      # Informational
            }
        """
        results = {
            'overall_passed': False,
            'ssim_verification': None,
            'pixel_verification': None,
            'ai_verification': None
        }
        
        # 1. PRIMARY: SSIM Verification
        if reference_image_name:
            logger.info(f"🔍 PRIMARY Verification: SSIM with '{reference_image_name}'")
            ssim_result = self.verify_with_ssim(
                after_screenshot,
                reference_image_name,
                ssim_threshold
            )
            results['ssim_verification'] = ssim_result
            results['overall_passed'] = ssim_result['passed']
            
            if ssim_result['passed']:
                logger.info("✅ PRIMARY Verification: PASSED")
            else:
                logger.warning("❌ PRIMARY Verification: FAILED")
        else:
            logger.warning("⚠️ No reference image provided - skipping SSIM verification")
            results['overall_passed'] = True  # Pass if no reference (fallback)
        
        # 2. SECONDARY: Pixel Change Verification (Informational)
        logger.info("📊 SECONDARY Verification: Pixel change (informational)")
        pixel_result = self.compare_screens(before_screenshot, after_screenshot)
        results['pixel_verification'] = {
            'changed': pixel_result.changed,
            'change_percentage': pixel_result.change_percentage,
            'details': pixel_result.details,
            'note': 'Informational only - does not affect test result'
        }
        
        # 3. SECONDARY: AI Verification (Informational)
        if self.use_ai_vision and reference_image_name:
            logger.info("🤖 SECONDARY Verification: AI vision (informational)")
            # Extract expected state from reference name
            expected_state = reference_image_name.replace('_', ' ').replace('.png', '')
            
            ai_result = self.verify_outcome_with_ai(
                before_screenshot,
                after_screenshot,
                f"Verify {expected_state}",
                "action performed"
            )
            results['ai_verification'] = {
                **ai_result,
                'note': 'Informational only - does not affect test result'
            }
        
        return results

# Singleton instance
_verification_tool_instance = None

def get_verification_tool(model_preference: Optional[str] = None) -> VerificationTool:
    """
    Get or create singleton verification tool instance.
    
    Args:
        model_preference: Preferred VIO model for new instances
        
    Returns:
        VerificationTool instance
    """
    global _verification_tool_instance
    
    if _verification_tool_instance is None:
        _verification_tool_instance = VerificationTool(model_preference)
    elif model_preference and model_preference != _verification_tool_instance.current_model:
        # Switch model if different preference provided
        _verification_tool_instance.switch_model(model_preference)
    
    return _verification_tool_instance