"""
conftest.py - Pytest Fixtures and Configuration

Shared fixtures for unit and integration tests.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
import subprocess

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)


@pytest.fixture
def mock_adb_device():
    """Mock ADB device connection."""
    mock_device = Mock()
    mock_device.serial = "emulator-5554"
    mock_device.model = "Android Automotive Emulator"
    mock_device.android_version = "13"
    return mock_device


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for ADB commands."""
    def mock_run(*args, **kwargs):
        result = Mock()
        result.returncode = 0
        result.stdout = "device"
        result.stderr = ""
        return result
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def test_screenshot():
    """Create a test screenshot image."""
    import cv2
    import numpy as np
    
    # Create 1920x1080 test image
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # Add some test text
    cv2.putText(img, "Settings", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(img, "Bluetooth", (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    # Save to test data
    screenshot_path = TEST_DATA_DIR / "test_screenshot.png"
    cv2.imwrite(str(screenshot_path), img)
    
    yield str(screenshot_path)
    
    # Cleanup
    if screenshot_path.exists():
        screenshot_path.unlink()


@pytest.fixture
def test_screenshot_pair():
    """Create pair of test screenshots (before/after)."""
    import cv2
    import numpy as np
    
    # Before screenshot
    img_before = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(img_before, "Loading", (500, 500), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    before_path = TEST_DATA_DIR / "before.png"
    cv2.imwrite(str(before_path), img_before)
    
    # After screenshot (different)
    img_after = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(img_after, "Settings", (500, 500), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    after_path = TEST_DATA_DIR / "after.png"
    cv2.imwrite(str(after_path), img_after)
    
    yield str(before_path), str(after_path)
    
    # Cleanup
    for path in [before_path, after_path]:
        if path.exists():
            path.unlink()


@pytest.fixture
def mock_vio_response():
    """Mock VIO Cloud API response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": "The Settings button is located at X=850 Y=450"
    }
    return mock_response


@pytest.fixture
def mock_ocr_result():
    """Mock OCR detection result."""
    return {
        'text': ['Settings', 'Bluetooth', 'Wi-Fi'],
        'left': [100, 100, 100],
        'top': [100, 300, 500],
        'width': [200, 250, 180],
        'height': [50, 50, 50],
        'conf': [95, 92, 88]
    }


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
    
    # Clean up any leftover test files
    if TEST_DATA_DIR.exists():
        for file in TEST_DATA_DIR.glob("*_temp*"):
            try:
                file.unlink()
            except:
                pass