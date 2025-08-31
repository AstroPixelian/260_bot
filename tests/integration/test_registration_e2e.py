"""
Integration tests for end-to-end registration flow
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.automation_service import AutomationService
from src.models.account import Account, AccountStatus


class TestRegistrationEndToEnd:
    """Integration test suite for end-to-end registration flow"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        self.service = AutomationService()
        
        # Setup test callbacks
        self.log_messages = []
        self.account_events = []
        
        def log_callback(message):
            self.log_messages.append(message)
            print(f"[LOG] {message}")
        
        def account_start_callback(account):
            self.account_events.append(f"START: {account.username}")
        
        def account_complete_callback(account):
            self.account_events.append(f"COMPLETE: {account.username} -> {account.status.value}")
        
        self.service.set_callbacks(
            on_log_message=log_callback,
            on_account_start=account_start_callback,
            on_account_complete=account_complete_callback
        )
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Ensure browser cleanup
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.service._cleanup_browser())
            else:
                asyncio.run(self.service._cleanup_browser())
        except:
            pass
    
    def test_generate_test_accounts_integration(self):
        """Test AccountGenerator integration produces valid accounts"""
        # Generate test accounts
        accounts = self.service.generate_test_accounts(5)
        
        # Verify accounts were generated
        assert len(accounts) == 5
        
        # Verify account properties
        for i, account in enumerate(accounts):
            assert account.id == i + 1
            assert len(account.username) >= 8
            assert len(account.username) <= 16
            assert len(account.password) >= 12
            assert len(account.password) <= 20
            assert account.status == AccountStatus.QUEUED
            assert account.notes == ""
            
            # Verify password complexity
            password = account.password
            has_lower = any(c.islower() for c in password)
            has_upper = any(c.isupper() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%^&*" for c in password)
            
            assert has_lower, f"Password {password} missing lowercase"
            assert has_upper, f"Password {password} missing uppercase"  
            assert has_digit, f"Password {password} missing digit"
            assert has_special, f"Password {password} missing special character"
        
        # Verify log callback was called
        assert len(self.log_messages) > 0
        assert "Generated 5 test accounts for registration" in self.log_messages[0]
    
    def test_browser_lifecycle_integration(self):
        """Test browser initialization and cleanup lifecycle"""
        # Test browser initialization
        init_result = asyncio.run(self.service._initialize_browser())
        
        assert init_result is True
        assert self.service.playwright is not None
        assert self.service.browser is not None
        assert self.service.browser_context is not None
        
        # Verify log messages
        assert any("Browser initialized successfully" in msg for msg in self.log_messages)
        
        # Test browser cleanup
        asyncio.run(self.service._cleanup_browser())
        
        assert self.service.playwright is None
        assert self.service.browser is None
        assert self.service.browser_context is None
        
        # Verify cleanup log messages
        assert any("Browser resources cleaned up" in msg for msg in self.log_messages)
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_registration_workflow_with_invalid_credentials(self):
        """Test registration workflow with credentials that should fail"""
        # Create account with invalid/taken username to test failure path
        test_account = Account(
            id=1,
            username="admin",  # Likely to be taken or invalid
            password="Test123456789@"
        )
        
        # Attempt registration
        result = await self.service.register_single_account(test_account)
        
        # Verify the workflow was executed (success/failure depends on actual site state)
        # But we can verify the process ran and status was updated
        assert test_account.status in [AccountStatus.SUCCESS, AccountStatus.FAILED]
        assert test_account.notes != ""  # Should have some status note
        
        # Verify log messages show registration attempt
        assert any("Starting registration for: admin" in msg for msg in self.log_messages)
        
        # If failed (expected), verify failure handling
        if test_account.status == AccountStatus.FAILED:
            assert any("FAILED: admin" in msg for msg in self.log_messages)
    
    def test_account_status_transitions_integration(self):
        """Test account status transitions during registration process"""
        test_account = Account(
            id=1,
            username="test_integration_user",
            password="TestPassword@123"
        )
        
        # Initial state
        assert test_account.status == AccountStatus.QUEUED
        assert test_account.notes == ""
        
        # Test processing state
        test_account.mark_processing("Starting registration")
        assert test_account.status == AccountStatus.PROCESSING
        assert "Starting registration" in test_account.notes
        
        # Test success state
        test_account.mark_success("Registration completed successfully")
        assert test_account.status == AccountStatus.SUCCESS
        assert "Registration completed successfully" in test_account.notes
        
        # Test reset
        test_account.reset_status()
        assert test_account.status == AccountStatus.QUEUED
        assert test_account.notes == ""
        
        # Test failure state
        test_account.mark_failed("Username already exists")
        assert test_account.status == AccountStatus.FAILED
        assert "Username already exists" in test_account.notes
    
    def test_callback_system_integration(self):
        """Test callback system integration with real operations"""
        # Clear previous events
        self.log_messages.clear()
        self.account_events.clear()
        
        # Generate test accounts to trigger callbacks
        accounts = self.service.generate_test_accounts(2)
        
        # Verify log callback was triggered
        assert len(self.log_messages) >= 1
        assert "Generated 2 test accounts for registration" in self.log_messages[0]
        
        # Test account status callbacks manually
        test_account = accounts[0]
        
        # Simulate account start
        if self.service.on_account_start:
            self.service.on_account_start(test_account)
        
        # Simulate account completion
        test_account.mark_success("Test completion")
        if self.service.on_account_complete:
            self.service.on_account_complete(test_account)
        
        # Verify callbacks were called
        expected_start = f"START: {test_account.username}"
        expected_complete = f"COMPLETE: {test_account.username} -> Success"
        
        assert expected_start in self.account_events
        assert expected_complete in self.account_events
    
    def test_error_handling_integration(self):
        """Test error handling integration across components"""
        # Test invalid account creation
        with pytest.raises(ValueError):
            Account(id=1, username="", password="test")  # Empty username
        
        with pytest.raises(ValueError):  
            Account(id=1, username="test", password="123")  # Password too short
        
        # Test service error handling with invalid count
        accounts = self.service.generate_test_accounts(0)
        assert len(accounts) == 0  # Should handle gracefully
        
        # Test cleanup when nothing to clean
        asyncio.run(self.service._cleanup_browser())  # Should not error
    
    @pytest.mark.slow
    @pytest.mark.asyncio 
    async def test_timeout_scenarios(self):
        """Test timeout scenarios in registration workflow"""
        test_account = Account(
            id=1,
            username="timeout_test_user",
            password="TimeoutTest123@"
        )
        
        # This test verifies that timeouts are handled gracefully
        # The actual result depends on network conditions and site availability
        try:
            result = await self.service.register_single_account(test_account)
            
            # Regardless of success/failure, verify the process handled timeouts
            assert test_account.status in [AccountStatus.SUCCESS, AccountStatus.FAILED]
            
            if test_account.status == AccountStatus.FAILED:
                # Verify timeout-related error messages are handled
                possible_timeout_messages = [
                    "timeout", "failed", "not found", "network", "connection"
                ]
                failure_noted = any(
                    any(keyword in test_account.notes.lower() for keyword in possible_timeout_messages)
                )
                # Should have some error description
                assert len(test_account.notes) > 0
                
        except Exception as e:
            # If exception occurs, verify it was handled gracefully
            assert test_account.status == AccountStatus.FAILED
            assert "failed" in test_account.notes.lower()
    
    def test_concurrent_browser_operations(self):
        """Test that browser operations handle concurrent access gracefully"""
        # Test multiple rapid initialization calls
        async def test_multiple_init():
            tasks = []
            for _ in range(3):
                tasks.append(self.service._initialize_browser())
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # At least one should succeed, others should be handled gracefully
            successes = [r for r in results if r is True]
            assert len(successes) >= 1
            
            # Cleanup
            await self.service._cleanup_browser()
        
        asyncio.run(test_multiple_init())
    
    def test_data_consistency_integration(self):
        """Test data consistency across Account model and service operations"""
        # Generate accounts and verify data consistency
        accounts = self.service.generate_test_accounts(3)
        
        # Verify each account maintains data integrity
        for account in accounts:
            original_username = account.username
            original_password = account.password
            original_id = account.id
            
            # Test status changes don't affect core data
            account.mark_processing("Test processing")
            assert account.username == original_username
            assert account.password == original_password
            assert account.id == original_id
            
            account.mark_success("Test success")
            assert account.username == original_username
            assert account.password == original_password
            assert account.id == original_id
            
            account.mark_failed("Test failure")
            assert account.username == original_username
            assert account.password == original_password
            assert account.id == original_id
            
            # Reset and verify
            account.reset_status()
            assert account.username == original_username
            assert account.password == original_password
            assert account.id == original_id
            assert account.status == AccountStatus.QUEUED
            assert account.notes == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])