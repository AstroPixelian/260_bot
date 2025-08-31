"""
Unit tests for error handling in automation service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from src.services.automation_service import AutomationService
from src.models.account import Account, AccountStatus
from src.exceptions import (
    AutomationError, BrowserInitializationError, ElementNotFoundError,
    PageNavigationError, FormInteractionError, RegistrationFailureError,
    TimeoutError, NetworkError, CaptchaRequiredError, AccountAlreadyExistsError,
    InvalidCredentialsError, RateLimitError
)


class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_automation_error_basic(self):
        """Test basic AutomationError functionality"""
        error = AutomationError("Test error", "TEST_CODE", {"key": "value"})
        
        assert str(error) == "Test error (Code: TEST_CODE, Details: {'key': 'value'})"
        assert error.error_code == "TEST_CODE"
        assert error.details == {"key": "value"}
    
    def test_automation_error_defaults(self):
        """Test AutomationError with default values"""
        error = AutomationError("Test error")
        
        assert error.error_code == "AUTOMATION_ERROR"
        assert error.details == {}
    
    def test_browser_initialization_error(self):
        """Test BrowserInitializationError"""
        error = BrowserInitializationError("Browser failed", "playwright", {"step": "launch"})
        
        assert error.backend == "playwright"
        assert error.error_code == "BROWSER_INIT_ERROR"
        assert "Browser failed" in str(error)
    
    def test_element_not_found_error(self):
        """Test ElementNotFoundError"""
        error = ElementNotFoundError(".selector", "button", 10)
        
        assert error.selector == ".selector"
        assert error.element_type == "button"
        assert error.timeout == 10
        assert "Could not find button with selector: .selector (timeout: 10s)" in str(error)
    
    def test_page_navigation_error(self):
        """Test PageNavigationError"""
        error = PageNavigationError("http://test.com", 3, "Connection failed")
        
        assert error.url == "http://test.com"
        assert error.attempts == 3
        assert error.last_error == "Connection failed"
        assert "Failed to navigate to http://test.com after 3 attempts" in str(error)
    
    def test_form_interaction_error(self):
        """Test FormInteractionError"""
        error = FormInteractionError("click", "button", {"selector": ".btn"})
        
        assert error.action == "click"
        assert error.field == "button"
        assert error.details["selector"] == ".btn"
        assert "Failed to click on field: button" in str(error)
    
    def test_account_already_exists_error(self):
        """Test AccountAlreadyExistsError"""
        error = AccountAlreadyExistsError("testuser", "用户名已存在")
        
        assert error.username == "testuser"
        assert error.detected_message == "用户名已存在"
        assert error.failure_type == "account_exists"
        assert "testuser" in str(error) and "用户名已存在" in str(error)


class TestAutomationServiceErrorHandling:
    """Test error handling in AutomationService"""
    
    @pytest.fixture
    def automation_service(self):
        """Create AutomationService instance for testing"""
        service = AutomationService("playwright")
        return service
    
    @pytest.fixture
    def test_account(self):
        """Create test account"""
        return Account(1, "testuser", "testpass123")
    
    def test_error_logging(self, automation_service, test_account):
        """Test error logging functionality"""
        # Clear any existing errors
        automation_service.clear_error_log()
        
        # Create and log an error
        error = ElementNotFoundError(".selector", "button", 10)
        automation_service._log_error(error, "test_context", test_account)
        
        # Check error log
        error_log = automation_service.get_error_log()
        assert len(error_log) == 1
        
        log_entry = error_log[0]
        assert log_entry["error_type"] == "ElementNotFoundError"
        assert log_entry["context"] == "test_context"
        assert log_entry["account_username"] == "testuser"
        assert log_entry["error_code"] == "ELEMENT_NOT_FOUND"
    
    def test_error_log_clearing(self, automation_service):
        """Test error log clearing"""
        # Add some errors
        automation_service._log_error(AutomationError("Test1"), "ctx1")
        automation_service._log_error(AutomationError("Test2"), "ctx2")
        
        assert len(automation_service.get_error_log()) == 2
        
        # Clear log
        automation_service.clear_error_log()
        assert len(automation_service.get_error_log()) == 0
    
    @pytest.mark.asyncio
    async def test_browser_initialization_error_handling(self, automation_service):
        """Test browser initialization error handling"""
        with patch('src.services.automation_service.async_playwright') as mock_playwright:
            mock_playwright.return_value.start.side_effect = Exception("Playwright start failed")
            
            with pytest.raises(BrowserInitializationError) as exc_info:
                await automation_service._initialize_browser()
            
            assert "Failed to start Playwright" in str(exc_info.value)
            assert exc_info.value.backend == "playwright"
    
    @pytest.mark.asyncio
    async def test_safe_navigate_success(self, automation_service):
        """Test successful navigation with _safe_navigate"""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        # Should complete without error
        await automation_service._safe_navigate(mock_page, "http://test.com")
        
        mock_page.goto.assert_called_once_with("http://test.com", wait_until='networkidle', timeout=60000)
    
    @pytest.mark.asyncio
    async def test_safe_navigate_timeout_retry(self, automation_service):
        """Test navigation retry on timeout"""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.goto.side_effect = [
            PlaywrightTimeoutError("Timeout 1"),
            PlaywrightTimeoutError("Timeout 2"), 
            None  # Success on third try
        ]
        
        # Should succeed after retries
        await automation_service._safe_navigate(mock_page, "http://test.com", max_retries=3)
        
        assert mock_page.goto.call_count == 3
    
    @pytest.mark.asyncio
    async def test_safe_navigate_max_retries_exceeded(self, automation_service):
        """Test navigation failure after max retries"""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Persistent timeout"))
        
        with pytest.raises(PageNavigationError) as exc_info:
            await automation_service._safe_navigate(mock_page, "http://test.com", max_retries=2)
        
        assert exc_info.value.url == "http://test.com"
        assert exc_info.value.attempts == 2
        assert "Timeout after 60s" in exc_info.value.last_error
    
    @pytest.mark.asyncio
    async def test_safe_wait_for_element_success(self, automation_service):
        """Test successful element waiting"""
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        
        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_element])
        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value = mock_locator
        
        element, selector = await automation_service._safe_wait_for_element(
            mock_page, [".selector1", ".selector2"], "button"
        )
        
        assert element == mock_element
        assert selector == ".selector1"
    
    @pytest.mark.asyncio
    async def test_safe_wait_for_element_not_found(self, automation_service):
        """Test element not found error"""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("Not found"))
        
        with pytest.raises(ElementNotFoundError) as exc_info:
            await automation_service._safe_wait_for_element(
                mock_page, [".selector1", ".selector2"], "button", timeout=5
            )
        
        assert exc_info.value.element_type == "button"
        assert exc_info.value.timeout == 5
        assert ".selector1 or .selector2" in exc_info.value.selector
    
    @pytest.mark.asyncio
    async def test_safe_fill_element_success(self, automation_service):
        """Test successful element filling"""
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.fill = AsyncMock()
        
        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_element])
        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value = mock_locator
        
        selector = await automation_service._safe_fill_element(
            mock_page, [".input"], "test_value", "username_field"
        )
        
        assert selector == ".input"
        mock_element.fill.assert_called_once_with("test_value")
    
    @pytest.mark.asyncio
    async def test_safe_fill_element_error(self, automation_service):
        """Test element filling error"""
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.fill = AsyncMock(side_effect=Exception("Fill failed"))
        
        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_element])
        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value = mock_locator
        
        with pytest.raises(FormInteractionError) as exc_info:
            await automation_service._safe_fill_element(
                mock_page, [".input"], "test_value", "username_field"
            )
        
        assert exc_info.value.action == "fill"
        assert exc_info.value.field == "username_field"
        assert "Fill failed" in exc_info.value.details["error"]
    
    def test_detect_registration_result_already_exists(self, automation_service, test_account):
        """Test detection of already registered account"""
        page_content = "<html><body>该账号已经注册</body></html>"
        
        with pytest.raises(AccountAlreadyExistsError) as exc_info:
            automation_service._detect_registration_result(page_content, test_account)
        
        assert exc_info.value.username == "testuser"
        assert exc_info.value.detected_message == "该账号已经注册"
    
    def test_detect_registration_result_success(self, automation_service, test_account):
        """Test detection of successful registration"""
        page_content = "<html><body><a href='#'>[退出]</a></body></html>"
        
        success, message = automation_service._detect_registration_result(page_content, test_account)
        
        assert success is True
        assert "[退出]" in message
    
    def test_detect_registration_result_captcha_required(self, automation_service, test_account):
        """Test detection of captcha requirement"""
        page_content = "<html><body>请输入验证码</body></html>"
        
        with pytest.raises(CaptchaRequiredError) as exc_info:
            automation_service._detect_registration_result(page_content, test_account)
        
        assert exc_info.value.captcha_type == "text_captcha"
    
    def test_detect_registration_result_validation_error(self, automation_service, test_account):
        """Test detection of validation errors"""
        page_content = "<html><body>用户名格式不正确</body></html>"
        
        with pytest.raises(RegistrationFailureError) as exc_info:
            automation_service._detect_registration_result(page_content, test_account)
        
        assert exc_info.value.failure_type == "validation_error"
        assert "用户名格式不正确" in exc_info.value.reason
    
    def test_detect_registration_result_unclear(self, automation_service, test_account):
        """Test detection when result is unclear"""
        page_content = "<html><body>Some random content</body></html>"
        
        success, message = automation_service._detect_registration_result(page_content, test_account)
        
        assert success is False
        assert "unclear" in message.lower()


class TestErrorIntegration:
    """Integration tests for error handling flow"""
    
    @pytest.fixture
    def automation_service(self):
        """Create AutomationService with mock callbacks"""
        service = AutomationService("playwright")
        service.on_log_message = Mock()
        return service
    
    @pytest.fixture
    def test_account(self):
        """Create test account"""
        return Account(1, "testuser", "testpass123")
    
    @pytest.mark.asyncio
    async def test_registration_with_browser_init_failure(self, automation_service, test_account):
        """Test registration flow when browser initialization fails"""
        with patch.object(automation_service, '_initialize_browser') as mock_init:
            mock_init.side_effect = BrowserInitializationError("Browser failed", "playwright")
            
            result = await automation_service._register_single_account_playwright(test_account)
            
            assert result is False
            assert test_account.status == AccountStatus.FAILED
            assert "Browser failed" in test_account.notes
            assert len(automation_service.get_error_log()) > 0
    
    @pytest.mark.asyncio
    async def test_registration_with_navigation_failure(self, automation_service, test_account):
        """Test registration flow when navigation fails"""
        with patch.object(automation_service, '_initialize_browser', return_value=True):
            with patch.object(automation_service, 'browser_context') as mock_context:
                mock_page = AsyncMock()
                mock_context.new_page = AsyncMock(return_value=mock_page)
                
                with patch.object(automation_service, '_safe_navigate') as mock_nav:
                    mock_nav.side_effect = PageNavigationError("http://test.com", 3, "Network error")
                    
                    result = await automation_service._register_single_account_playwright(test_account)
                    
                    assert result is False
                    assert test_account.status == AccountStatus.FAILED
                    assert "Failed to navigate" in test_account.notes
    
    @pytest.mark.asyncio
    async def test_registration_with_element_not_found(self, automation_service, test_account):
        """Test registration flow when required elements are not found"""
        with patch.object(automation_service, '_initialize_browser', return_value=True):
            with patch.object(automation_service, 'browser_context') as mock_context:
                mock_page = AsyncMock()
                mock_page.url = "https://wan.360.cn/"
                mock_page.close = AsyncMock()
                mock_context.new_page = AsyncMock(return_value=mock_page)
                
                with patch.object(automation_service, '_safe_navigate'):
                    with patch.object(automation_service, '_safe_click_element') as mock_click:
                        mock_click.side_effect = ElementNotFoundError(".register-btn", "button", 10)
                        
                        result = await automation_service._register_single_account_playwright(test_account)
                        
                        assert result is False
                        assert test_account.status == AccountStatus.FAILED
                        assert "Could not find button" in test_account.notes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])