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
        self.service = AutomationService(backend="playwright")  # Explicitly set backend
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
            
            # Verify browser was launched with correct settings (matching actual implementation)
            call_kwargs = mock_playwright.chromium.launch.call_args[1]
            assert call_kwargs['headless'] is False
            assert '--disable-blink-features=AutomationControlled' in call_kwargs['args']
            assert call_kwargs['slow_mo'] == 200
            assert call_kwargs['timeout'] == 90000
            
            # Verify callback was called
            self.mock_on_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_browser_initialization_failure(self):
        """Test browser initialization failure"""
        # Test custom exception handling
        from src.exceptions import BrowserInitializationError
        
        with patch('src.services.automation_service.async_playwright') as mock_playwright_factory:
            mock_playwright_factory.return_value.start = AsyncMock(side_effect=Exception("Browser launch failed"))
            
            with pytest.raises(BrowserInitializationError):  # Expecting BrowserInitializationError
                result = await self.service._initialize_browser()
            
            assert self.service.browser is None
    
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
        with patch.object(self.service, '_initialize_browser', side_effect=Exception("Browser init failed")):
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            assert "Browser init failed" in self.test_account.notes
    
    @pytest.mark.asyncio
    async def test_register_single_account_successful_flow(self):
        """Test successful registration flow with mocked Playwright registration method"""
        # Mock the entire Playwright registration method to return success
        with patch.object(self.service, '_register_single_account_playwright', return_value=True) as mock_playwright_registration:
            # Mock successful initialization 
            with patch.object(self.service, '_initialize_browser', return_value=True):
                
                result = await self.service.register_single_account(self.test_account)
                
                assert result is True
                mock_playwright_registration.assert_called_once_with(self.test_account)
    
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
            assert "Navigation timeout" in self.test_account.notes
            
            # Verify page cleanup was attempted
            mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_single_account_form_filling_failure(self):
        """Test registration failure during form filling"""
        mock_page = AsyncMock()
        
        # Mock navigation success but element operation failure
        mock_page.goto = AsyncMock()
        mock_page.locator = AsyncMock(side_effect=Exception("Element not found"))
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        with patch.object(self.service, '_initialize_browser', return_value=True):
            self.service.browser_context = mock_context
            
            result = await self.service.register_single_account(self.test_account)
            
            assert result is False
            assert self.test_account.status == AccountStatus.FAILED
            # Should contain some error message about element interaction
            assert len(self.test_account.notes) > 0
    
    @pytest.mark.asyncio
    async def test_register_single_account_verification_failure(self):
        """Test registration failure during success verification"""
        # Mock the entire Playwright registration method to return failure
        with patch.object(self.service, '_register_single_account_playwright', return_value=False) as mock_playwright_registration:
            # Mock successful initialization 
            with patch.object(self.service, '_initialize_browser', return_value=True):
                
                result = await self.service.register_single_account(self.test_account)
                
                assert result is False
                mock_playwright_registration.assert_called_once_with(self.test_account)
    
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