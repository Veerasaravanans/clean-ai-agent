"""
test_vision_tool.py - Unit Tests for Vision Tool

Tests OCR detection, AI Vision, and image preprocessing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.tools.vision_tool import VisionTool
from backend.models import Coordinates, ScreenAnalysis


class TestVisionToolInitialization:
    """Test vision tool initialization."""
    
    def test_init(self):
        """Test basic initialization."""
        vision = VisionTool()
        assert vision.confidence_threshold == 60
        assert vision.use_ai_vision == True


class TestImagePreprocessing:
    """Test image preprocessing strategies."""
    
    def test_preprocess_standard(self, test_screenshot):
        """Test standard preprocessing."""
        vision = VisionTool()
        result = vision._preprocess_image_for_ocr(test_screenshot, preset='standard')
        
        assert result.endswith('_standard.png')
    
    def test_preprocess_high_contrast(self, test_screenshot):
        """Test high contrast preprocessing."""
        vision = VisionTool()
        result = vision._preprocess_image_for_ocr(test_screenshot, preset='high_contrast')
        
        assert result.endswith('_high_contrast.png')
    
    def test_preprocess_invalid_image(self):
        """Test preprocessing with invalid image."""
        vision = VisionTool()
        result = vision._preprocess_image_for_ocr("/nonexistent/image.png", preset='standard')
        
        assert result == "/nonexistent/image.png"


class TestOCRDetection:
    """Test OCR text detection."""
    
    @patch('pytesseract.image_to_data')
    def test_find_text_exact_match(self, mock_ocr, test_screenshot):
        """Test exact text match."""
        # Mock OCR response
        mock_ocr.return_value = {
            'text': ['Settings', 'Bluetooth'],
            'left': [100, 100],
            'top': [100, 300],
            'width': [200, 250],
            'height': [50, 50],
            'conf': [95, 92]
        }
        
        vision = VisionTool()
        coords = vision.find_text(test_screenshot, "Settings")
        
        assert coords is not None
        assert coords.x == 200  # left + width/2
        assert coords.y == 125  # top + height/2
    
    @patch('pytesseract.image_to_data')
    def test_find_text_fuzzy_match(self, mock_ocr, test_screenshot):
        """Test fuzzy text matching."""
        mock_ocr.return_value = {
            'text': ['Settins'],  # Typo
            'left': [100],
            'top': [100],
            'width': [200],
            'height': [50],
            'conf': [95]
        }
        
        vision = VisionTool()
        coords = vision.find_text(test_screenshot, "Settings")
        
        # Should find with fuzzy match (>85% similarity)
        assert coords is not None
    
    @patch('pytesseract.image_to_data')
    def test_find_text_not_found(self, mock_ocr, test_screenshot):
        """Test text not found."""
        mock_ocr.return_value = {
            'text': ['Other', 'Text'],
            'left': [100, 100],
            'top': [100, 300],
            'width': [200, 250],
            'height': [50, 50],
            'conf': [95, 92]
        }
        
        vision = VisionTool()
        coords = vision.find_text(test_screenshot, "Settings")
        
        assert coords is None
    
    @patch('pytesseract.image_to_data')
    def test_find_text_low_confidence(self, mock_ocr, test_screenshot):
        """Test text with low confidence is filtered."""
        mock_ocr.return_value = {
            'text': ['Settings'],
            'left': [100],
            'top': [100],
            'width': [200],
            'height': [50],
            'conf': [30]  # Below threshold (60)
        }
        
        vision = VisionTool()
        coords = vision.find_text(test_screenshot, "Settings")
        
        assert coords is None


class TestAllTextExtraction:
    """Test full text extraction."""
    
    @patch('easyocr.Reader')
    def test_get_all_text(self, mock_reader, test_screenshot):
        """Test extracting all text elements."""
        mock_instance = Mock()
        mock_instance.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 50], [0, 50]], 'Settings', 0.95),
            ([[0, 100], [250, 100], [250, 150], [0, 150]], 'Bluetooth', 0.92)
        ]
        mock_reader.return_value = mock_instance
        
        vision = VisionTool()
        vision.easyocr_reader = mock_instance
        
        elements = vision.get_all_text(test_screenshot)
        
        assert len(elements) == 2
        assert elements[0].text == 'Settings'
        assert elements[1].text == 'Bluetooth'


class TestAIVision:
    """Test AI Vision integration."""
    
    @patch('requests.post')
    def test_analyze_screen_success(self, mock_post, test_screenshot, mock_vio_response):
        """Test successful AI Vision analysis."""
        mock_post.return_value = mock_vio_response
        
        vision = VisionTool()
        analysis = vision.analyze_screen_with_ai(test_screenshot)
        
        assert isinstance(analysis, ScreenAnalysis)
        assert analysis.confidence > 0
        assert analysis.screen_state == "analyzed"
    
    @patch('requests.post')
    def test_analyze_screen_failure(self, mock_post, test_screenshot):
        """Test AI Vision failure handling."""
        mock_post.side_effect = Exception("API Error")
        
        vision = VisionTool()
        analysis = vision.analyze_screen_with_ai(test_screenshot)
        
        assert analysis.screen_state == "error"
        assert analysis.confidence == 0
    
    @patch('requests.post')
    def test_find_element_with_ai(self, mock_post, test_screenshot):
        """Test finding element with AI Vision."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "X=850 Y=450"
        }
        mock_post.return_value = mock_response
        
        vision = VisionTool()
        coords = vision.find_element_with_ai(test_screenshot, "Settings button")
        
        assert coords is not None
        assert coords.x == 850
        assert coords.y == 450
        assert coords.source == "ai_vision"
    
    @patch('requests.post')
    def test_find_element_with_ai_not_found(self, mock_post, test_screenshot):
        """Test AI Vision element not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "NOT FOUND"
        }
        mock_post.return_value = mock_response
        
        vision = VisionTool()
        coords = vision.find_element_with_ai(test_screenshot, "NonExistent")
        
        assert coords is None


class TestGeometricValidation:
    """Test geometric validation and clustering."""
    
    @patch('pytesseract.image_to_data')
    def test_multiple_detections(self, mock_ocr, test_screenshot):
        """Test handling of multiple text detections."""
        # Mock multiple detections of same text
        mock_ocr.return_value = {
            'text': ['Settings', 'Settings', 'Settings'],
            'left': [100, 105, 110],
            'top': [100, 105, 110],
            'width': [200, 200, 200],
            'height': [50, 50, 50],
            'conf': [95, 94, 93]
        }
        
        vision = VisionTool()
        coords = vision.find_text(test_screenshot, "Settings")
        
        # Should return coordinates (likely averaged/clustered)
        assert coords is not None
        assert coords.x > 0
        assert coords.y > 0


class TestCoordinatesModel:
    """Test Coordinates model integration."""
    
    def test_coordinates_creation(self):
        """Test Coordinates object creation."""
        coords = Coordinates(
            x=100,
            y=200,
            confidence=95,
            source="tesseract_standard"
        )
        
        assert coords.x == 100
        assert coords.y == 200
        assert coords.confidence == 95
        assert coords.source == "tesseract_standard"