"""
test_adb_tool.py - Unit Tests for ADB Tool

Tests ADB operations, screen detection, and command execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.tools.adb_tool import ADBTool
from backend.models import ActionResult


class TestADBToolInitialization:
    """Test ADB tool initialization."""
    
    def test_init_with_device_serial(self, mock_subprocess_run):
        """Test initialization with device serial."""
        adb = ADBTool(device_serial="emulator-5554")
        assert adb.device_serial == "emulator-5554"
        assert adb.timeout == 10
    
    def test_screen_detection(self, mock_subprocess_run):
        """Test screen dimension detection."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Physical size: 1920x1080"
            mock_run.return_value = mock_result
            
            adb = ADBTool()
            assert adb.screen_width == 1920
            assert adb.screen_height == 1080


class TestADBConnection:
    """Test ADB connection methods."""
    
    def test_is_connected_success(self):
        """Test successful device connection check."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "device"
            mock_run.return_value = mock_result
            
            adb = ADBTool()
            assert adb.is_connected() == True
    
    def test_is_connected_failure(self):
        """Test failed device connection check."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Connection failed")
            
            adb = ADBTool()
            assert adb.is_connected() == False
    
    def test_get_device_info(self):
        """Test device info retrieval."""
        with patch('subprocess.run') as mock_run:
            # Mock all subprocess calls
            mock_run.return_value = Mock(returncode=0, stdout="emulator-5554", stderr="")
            
            adb = ADBTool()
            
            # Mock is_connected to return True
            with patch.object(adb, 'is_connected', return_value=True):
                info = adb.get_device_info()
                
                assert info["connected"] == True
                assert "serial" in info
                assert "resolution" in info


class TestADBActions:
    """Test ADB action methods."""
    
    def test_tap_success(self):
        """Test successful tap action."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.tap(100, 200)
            
            assert result.success == True
            assert result.action_type == "tap"
            assert result.coordinates == (100, 200)
    
    def test_tap_percent(self):
        """Test tap by percentage."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            adb.screen_width = 1920
            adb.screen_height = 1080
            
            result = adb.tap_percent(0.5, 0.5)
            
            assert result.success == True
            assert result.coordinates == (960, 540)
    
    def test_double_tap(self):
        """Test double tap action."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.double_tap(100, 200, delay_ms=50)
            
            assert result.success == True
            assert result.action_type == "double_tap"
    
    def test_long_press(self):
        """Test long press action."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.long_press(100, 200, duration_ms=1000)
            
            assert result.success == True
            assert result.action_type == "long_press"
    
    def test_swipe(self):
        """Test swipe action."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.swipe(100, 500, 100, 200, duration_ms=300)
            
            assert result.success == True
            assert result.action_type == "swipe"
            assert result.coordinates == (100, 500, 100, 200)
    
    def test_swipe_up(self):
        """Test swipe up convenience method."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.swipe_up(distance=500)
            
            assert result.success == True
    
    def test_input_text(self):
        """Test text input."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.input_text("Hello World")
            
            assert result.success == True
            assert result.action_type == "input_text"
    
    def test_press_back(self):
        """Test back button press."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.press_back()
            
            assert result.success == True
            assert result.action_type == "press_key"
    
    def test_press_home(self):
        """Test home button press."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            adb = ADBTool()
            result = adb.press_home()
            
            assert result.success == True


class TestStopControl:
    """Test stop control mechanism."""
    
    def test_stop_mechanism(self):
        """Test stop request."""
        adb = ADBTool()
        assert adb.stop_requested == False
        
        adb.stop()
        assert adb.stop_requested == True
    
    def test_reset_stop(self):
        """Test stop reset."""
        adb = ADBTool()
        adb.stop()
        assert adb.stop_requested == True
        
        adb.reset_stop()
        assert adb.stop_requested == False
    
    def test_stop_prevents_execution(self):
        """Test that stop flag prevents command execution."""
        with patch('subprocess.run') as mock_run:
            adb = ADBTool()
            adb.stop()
            
            result = adb.tap(100, 200)
            
            assert result.success == False
            assert "Stopped" in result.error


class TestRawCommands:
    """Test raw ADB command execution."""
    
    def test_execute_raw_command(self):
        """Test raw command execution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
            
            adb = ADBTool()
            result = adb.execute_raw_command("shell am start -n com.android.settings/.Settings")
            
            assert result["success"] == True
            assert result["output"] == "Success"