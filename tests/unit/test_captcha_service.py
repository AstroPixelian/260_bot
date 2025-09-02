"""
Unit tests for CaptchaService
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src directory to path for testing
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.captcha_service import CaptchaService
from src.models.account import Account, AccountStatus


class TestCaptchaService(unittest.TestCase):
    """Test CaptchaService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.captcha_service = CaptchaService()
        self.test_account = Account(
            id=1,
            username="test_user",
            password="test_pass"
        )
    
    def test_detect_captcha_high_specificity(self):
        """Test captcha detection with high specificity indicators"""
        # Test with quc-slide-con indicator
        page_content = '<div class="quc-slide-con">Captcha content</div>'
        detected, message = self.captcha_service.detect_captcha_in_content(page_content)
        
        self.assertTrue(detected)
        self.assertIn("CAPTCHA_DETECTED: quc-slide-con", message)
    
    def test_detect_captcha_mask_indicator(self):
        """Test captcha detection with quc-captcha-mask"""
        page_content = '<div class="quc-captcha-mask">验证码遮罩</div>'
        detected, message = self.captcha_service.detect_captcha_in_content(page_content)
        
        self.assertTrue(detected)
        self.assertIn("CAPTCHA_DETECTED: quc-captcha-mask", message)
    
    def test_detect_captcha_text_indicator(self):
        """Test captcha detection with specific text"""
        page_content = '<p>请完成下方拼图验证后继续</p>'
        detected, message = self.captcha_service.detect_captcha_in_content(page_content)
        
        self.assertTrue(detected)
        self.assertIn("请完成下方拼图验证后继续", message)
    
    def test_detect_captcha_auxiliary_indicators(self):
        """Test captcha detection with auxiliary indicators"""
        page_content = '<div class="verify-slide-con">拖动滑块完成拼图</div>'
        detected, message = self.captcha_service.detect_captcha_in_content(page_content)
        
        self.assertTrue(detected)
        self.assertIn("slide verification interface", message)
    
    def test_no_captcha_detection(self):
        """Test when no captcha is present"""
        page_content = '<div>Normal page content</div>'
        detected, message = self.captcha_service.detect_captcha_in_content(page_content)
        
        self.assertFalse(detected)
        self.assertEqual(message, "No captcha detected")
    
    def test_detect_registration_success_multiple_features(self):
        """Test registration success detection with multiple features"""
        page_content = '''
        <div class="login-container">
            <div class="login-user-info">
                <a class="wan-logout-btn">退出</a>
                <img class="user_info_avatar" />
                <span class="name-text">用户名</span>
            </div>
        </div>
        '''
        success, message = self.captcha_service.detect_registration_success(page_content)
        
        self.assertTrue(success)
        self.assertIn("login interface detected (6 features)", message)
    
    def test_detect_registration_success_explicit_message(self):
        """Test registration success with explicit message"""
        page_content = '<div>注册成功！欢迎使用360服务</div>'
        success, message = self.captcha_service.detect_registration_success(page_content)
        
        self.assertTrue(success)
        self.assertIn("detected: 注册成功", message)
    
    def test_no_registration_success(self):
        """Test when registration success is not detected"""
        page_content = '<div>Loading...</div>'
        success, message = self.captcha_service.detect_registration_success(page_content)
        
        self.assertFalse(success)
        self.assertEqual(message, "No registration success detected")
    
    def test_check_captcha_completion_success(self):
        """Test captcha completion with dual condition met"""
        # Page content with no captcha and registration success
        page_content = '''
        <div class="login-container">
            <div class="login-user-info">
                <a class="wan-logout-btn">退出</a>
                <img class="user_info_avatar" />
                <span class="name-text">用户名</span>
            </div>
        </div>
        '''
        
        completed, message = self.captcha_service.check_captcha_completion(page_content)
        
        self.assertTrue(completed)
        self.assertIn("Captcha completed successfully", message)
    
    def test_check_captcha_completion_still_present(self):
        """Test when captcha is still present"""
        page_content = '<div class="quc-slide-con">Still has captcha</div>'
        
        completed, message = self.captcha_service.check_captcha_completion(page_content)
        
        self.assertFalse(completed)
        self.assertIn("Captcha still present", message)
    
    def test_check_captcha_completion_intermediate_state(self):
        """Test intermediate state: captcha gone but no success yet"""
        page_content = '<div>Some intermediate page content</div>'
        
        completed, message = self.captcha_service.check_captcha_completion(page_content)
        
        self.assertFalse(completed)
        self.assertIn("Captcha disappeared but registration not confirmed yet", message)
    
    def test_set_callbacks(self):
        """Test callback setting"""
        mock_detected = Mock()
        mock_resolved = Mock()
        mock_timeout = Mock()
        mock_log = Mock()
        
        self.captcha_service.set_callbacks(
            on_captcha_detected=mock_detected,
            on_captcha_resolved=mock_resolved,
            on_captcha_timeout=mock_timeout,
            on_log_message=mock_log
        )
        
        self.assertEqual(self.captcha_service.on_captcha_detected, mock_detected)
        self.assertEqual(self.captcha_service.on_captcha_resolved, mock_resolved)
        self.assertEqual(self.captcha_service.on_captcha_timeout, mock_timeout)
        self.assertEqual(self.captcha_service.on_log_message, mock_log)
    
    @patch('src.services.captcha_service.PYSIDE6_AVAILABLE', False)
    def test_no_pyside6_monitoring(self):
        """Test behavior when PySide6 is not available"""
        service = CaptchaService()
        mock_page = Mock()
        
        # Should not raise exception, but log error
        service.start_monitoring(self.test_account, mock_page)
        
        # Account should not be in active timers
        self.assertEqual(len(service.active_timers), 0)


if __name__ == '__main__':
    unittest.main()