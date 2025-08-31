"""
Unit tests for AutomationService registration logic
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.automation_service import AutomationService
from src.models.account import Account, AccountStatus


class TestAutomationServiceRegistration:
    """Test suite for AutomationService registration functionality"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        self.service = AutomationService()
        self.test_account = Account(
            id=1,
            username="test_user123",
            password="TestPassword@123"
        )
        
        # Mock callbacks
        self.mock_on_log = MagicMock()
        self.service.set_callbacks(on_log_message=self.mock_on_log)
    
    @pytest.mark.asyncio
    async def test_browser_initialization_success(self):
        """Test successful browser initialization"""
        # Mock playwright components
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        with patch('src.services.automation_service.async_playwright') as mock_playwright_factory:
            mock_playwright_factory.return_value.start = AsyncMock(return_value=mock_playwright)
            
            result = await self.service._initialize_browser()
            
            assert result is True
            assert self.service.playwright == mock_playwright
            assert self.service.browser == mock_browser
            assert self.service.browser_context == mock_context
            
            # Verify browser was launched with correct settings
            mock_playwright.chromium.launch.assert_called_once_with(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Verify callback was called
            self.mock_on_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_browser_initialization_failure(self):
        """Test browser initialization failure"""
        with patch('src.services.automation_service.async_playwright') as mock_playwright_factory:
            mock_playwright_factory.return_value.start = AsyncMock(side_effect=Exception("Browser launch failed"))
            
            result = await self.service._initialize_browser()
            
            assert result is False
            assert self.service.browser is None
            
            # Verify error callback was called
            self.mock_on_log.assert_called()
            call_args = self.mock_on_log.call_args[0][0]
            assert "Browser initialization failed" in call_args
    
    @pytest.mark.asyncio
    async def test_browser_cleanup_success(self):
        """Test successful browser cleanup"""
        # Setup mock browser components
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        
        self.service.browser_context = mock_context
        self.service.browser = mock_browser
        self.service.playwright = mock_playwright
        
        await self.service._cleanup_browser()
        
        # Verify cleanup was called in correct order
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        
        # Verify attributes were reset
        assert self.service.browser_context is None
        assert self.service.browser is None
        assert self.service.playwright is None
        
        # Verify callback was called
        self.mock_on_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_browser_cleanup_with_errors(self):
        """Test browser cleanup with errors"""
        # Setup mock browser components that raise errors
        mock_context = AsyncMock()
        mock_context.close.side_effect = Exception("Context close failed")
        
        self.service.browser_context = mock_context
        self.service.browser = None  # This should not cause additional errors
        self.service.playwright = None
        
        await self.service._cleanup_browser()
        
        # Verify cleanup was attempted despite errors
        mock_context.close.assert_called_once()
        
        # Verify warning callback was called
        self.mock_on_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_register_single_account_browser_init_failure(self):
        """Test registration when browser initialization fails"""
        with patch.object(self.service, '_initialize_browser', return_value=False):
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            assert "Failed to initialize browser" in self.test_account.notes
    
    @pytest.mark.asyncio
    async def test_register_single_account_successful_flow(self):
        """Test successful registration flow with mocked Playwright"""
        # Mock all Playwright operations
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="用户中心 [退出]")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Setup successful browser initialization
        with patch.object(self.service, '_initialize_browser', return_value=True):
            self.service.browser_context = mock_context
            
            result = await self.service.register_single_account(self.test_account)
            
            assert result is True
            assert self.test_account.status == AccountStatus.SUCCESS
            
            # Verify all registration steps were called
            mock_page.goto.assert_called_once_with(
                'https://wan.360.cn/', 
                wait_until='domcontentloaded', 
                timeout=30000
            )
            
            # Verify form filling steps
            assert mock_page.fill.call_count == 3  # username, password, confirm password
            mock_page.check.assert_called_once()  # terms agreement
            assert mock_page.click.call_count == 2  # registration button + confirm
            
            # Verify success verification
            mock_page.wait_for_selector.assert_called()
            mock_page.query_selector.assert_called()
            
            # Verify page cleanup
            mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_single_account_navigation_failure(self):
        """Test registration failure during navigation"""
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Navigation timeout")
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        with patch.object(self.service, '_initialize_browser', return_value=True):
            self.service.browser_context = mock_context
            
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            assert "Registration failed" in self.test_account.notes
            
            # Verify page cleanup was attempted
            mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_single_account_form_filling_failure(self):
        """Test registration failure during form filling"""
        mock_page = AsyncMock()
        mock_page.fill.side_effect = Exception("Element not found")
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        with patch.object(self.service, '_initialize_browser', return_value=True):
            self.service.browser_context = mock_context
            
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            assert "Failed to fill username" in self.test_account.notes
    
    @pytest.mark.asyncio
    async def test_register_single_account_verification_failure(self):
        """Test registration failure during success verification"""
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="登录")  # Wrong text, no [退出]
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        with patch.object(self.service, '_initialize_browser', return_value=True):
            self.service.browser_context = mock_context
            
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            assert "doesn't contain [退出]" in self.test_account.notes
    
    def test_generate_test_accounts_success(self):
        """Test successful test account generation"""
        with patch('src.services.automation_service.AccountGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate_accounts.return_value = [
                {"username": "testuser1", "password": "TestPass1@"},
                {"username": "testuser2", "password": "TestPass2@"}
            ]
            
            accounts = self.service.generate_test_accounts(2)
            
            assert len(accounts) == 2
            assert accounts[0].username == "testuser1"
            assert accounts[0].password == "TestPass1@"
            assert accounts[0].status == AccountStatus.QUEUED
            
            # Verify generator was configured correctly
            MockGenerator.assert_called_once()
            config_arg = MockGenerator.call_args[0][0]
            assert config_arg["account_generator"]["username_min_length"] == 8
            assert config_arg["account_generator"]["password_min_length"] == 12
    
    def test_generate_test_accounts_failure(self):
        """Test test account generation failure"""
        with patch('src.services.automation_service.AccountGenerator') as MockGenerator:
            MockGenerator.side_effect = Exception("Generator failed")
            
            accounts = self.service.generate_test_accounts(2)
            
            assert len(accounts) == 0
            # Verify error callback was called
            self.mock_on_log.assert_called()
    
    def test_status_tracking_during_registration(self):
        """Test that account status is properly tracked during registration"""
        # Test account starts as queued
        account = Account(id=1, username="test", password="test123")
        assert account.status == AccountStatus.QUEUED
        
        # Test status changes
        account.mark_processing("Testing")
        assert account.status == AccountStatus.PROCESSING
        assert "Testing" in account.notes
        
        account.mark_success("Registration complete")
        assert account.status == AccountStatus.SUCCESS
        assert "Registration complete" in account.notes
        
        account.reset_status()
        assert account.status == AccountStatus.QUEUED
        assert account.notes == ""
    
    def test_error_handling_and_cleanup(self):
        """Test error handling and resource cleanup"""
        account = Account(id=1, username="test", password="test123")
        
        # Test mark_failed with error message
        error_msg = "Network timeout during registration"
        account.mark_failed(error_msg)
        
        assert account.status == AccountStatus.FAILED
        assert error_msg in account.notes
    
    def test_callback_system_integration(self):
        """Test callback system works correctly"""
        # Setup callbacks
        mock_account_start = MagicMock()
        mock_account_complete = MagicMock()
        mock_batch_complete = MagicMock()
        mock_log_message = MagicMock()
        
        self.service.set_callbacks(
            on_account_start=mock_account_start,
            on_account_complete=mock_account_complete,
            on_batch_complete=mock_batch_complete,
            on_log_message=mock_log_message
        )
        
        # Verify callbacks were set
        assert self.service.on_account_start == mock_account_start
        assert self.service.on_account_complete == mock_account_complete
        assert self.service.on_batch_complete == mock_batch_complete
        assert self.service.on_log_message == mock_log_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])