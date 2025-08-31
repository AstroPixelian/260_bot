"""
Integration tests for CLI error reporting functionality
"""

import pytest
import asyncio
import json
import sys
from io import StringIO
from unittest.mock import patch, Mock, AsyncMock

from src.cli import CLIHandler
from src.services.automation_service import AutomationService
from src.models.account import Account, AccountStatus
from src.exceptions import (
    ElementNotFoundError, PageNavigationError, AccountAlreadyExistsError,
    CaptchaRequiredError, BrowserInitializationError
)


class TestCLIErrorReporting:
    """Test CLI error reporting functionality"""
    
    @pytest.fixture
    def cli_handler(self):
        """Create CLI handler for testing"""
        handler = CLIHandler()
        # Mock the automation service to avoid real browser operations
        handler.automation_service = Mock(spec=AutomationService)
        return handler
    
    def test_argument_parser_with_new_flags(self, cli_handler):
        """Test argument parser includes new error reporting flags"""
        parser = cli_handler.create_argument_parser()
        
        # Test that new arguments are available
        test_args = [
            "--username", "testuser",
            "--password", "testpass123",
            "--verbose",
            "--json",
            "--error-log",
            "--backend", "playwright"
        ]
        
        args = parser.parse_args(test_args)
        
        assert args.username == "testuser"
        assert args.password == "testpass123"
        assert args.verbose is True
        assert args.json is True
        assert args.error_log is True
        assert args.backend == "playwright"
    
    def test_format_error_details_basic_error(self, cli_handler):
        """Test formatting of basic error details"""
        error = Exception("Basic error message")
        
        details = cli_handler.format_error_details(error)
        
        assert details["error_type"] == "Exception"
        assert details["error_message"] == "Basic error message"
    
    def test_format_error_details_element_not_found(self, cli_handler):
        """Test formatting of ElementNotFoundError details"""
        error = ElementNotFoundError(".selector", "button", 10)
        
        details = cli_handler.format_error_details(error)
        
        assert details["error_type"] == "ElementNotFoundError"
        assert details["error_code"] == "ELEMENT_NOT_FOUND"
        assert details["selector"] == ".selector"
        assert details["element_type"] == "button"
        assert details["timeout"] == 10
    
    def test_format_error_details_account_exists(self, cli_handler):
        """Test formatting of AccountAlreadyExistsError details"""
        error = AccountAlreadyExistsError("testuser", "用户名已存在")
        
        details = cli_handler.format_error_details(error)
        
        assert details["error_type"] == "AccountAlreadyExistsError"
        assert details["username"] == "testuser"
        assert details["detected_message"] == "用户名已存在"
    
    def test_setup_callbacks_verbose_mode(self, cli_handler):
        """Test callback setup in verbose mode"""
        cli_handler.verbose_mode = True
        cli_handler.json_output = False
        
        with patch('builtins.print') as mock_print:
            cli_handler.setup_callbacks()
            
            # Test account start callback
            test_account = Account(1, "testuser", "testpass")
            cli_handler.automation_service.set_callbacks.call_args[1]['on_account_start'](test_account)
            mock_print.assert_called_with("Starting registration for account: testuser")
    
    def test_setup_callbacks_json_mode(self, cli_handler):
        """Test callback setup in JSON mode"""
        cli_handler.verbose_mode = False
        cli_handler.json_output = True
        
        with patch('builtins.print') as mock_print:
            cli_handler.setup_callbacks()
            
            # Test account start callback in JSON mode (should not print)
            test_account = Account(1, "testuser", "testpass")
            cli_handler.automation_service.set_callbacks.call_args[1]['on_account_start'](test_account)
            mock_print.assert_not_called()
    
    def test_display_error_log_empty(self, cli_handler):
        """Test display of empty error log"""
        cli_handler.automation_service.get_error_log.return_value = []
        cli_handler.json_output = False
        
        with patch('builtins.print') as mock_print:
            cli_handler.display_error_log()
            mock_print.assert_called_with("No errors recorded during registration attempt.")
    
    def test_display_error_log_with_errors(self, cli_handler):
        """Test display of error log with errors"""
        error_log = [
            {
                "error_type": "ElementNotFoundError",
                "error_message": "Button not found",
                "context": "registration",
                "backend": "playwright",
                "account_username": "testuser",
                "error_code": "ELEMENT_NOT_FOUND",
                "error_details": {"selector": ".btn"}
            }
        ]
        
        cli_handler.automation_service.get_error_log.return_value = error_log
        cli_handler.json_output = False
        
        with patch('builtins.print') as mock_print:
            cli_handler.display_error_log()
            
            # Check that error details were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            
            assert any("ERROR LOG" in call for call in print_calls)
            assert any("ElementNotFoundError" in call for call in print_calls)
            assert any("Button not found" in call for call in print_calls)
            assert any("Context: registration" in call for call in print_calls)
    
    def test_display_error_log_json_format(self, cli_handler):
        """Test display of error log in JSON format"""
        error_log = [{"error_type": "TestError", "error_message": "Test message"}]
        
        cli_handler.automation_service.get_error_log.return_value = error_log
        cli_handler.json_output = True
        
        with patch('builtins.print') as mock_print:
            cli_handler.display_error_log()
            
            # Should print JSON formatted error log
            printed_text = mock_print.call_args[0][0]
            parsed_json = json.loads(printed_text)
            
            assert "error_log" in parsed_json
            assert len(parsed_json["error_log"]) == 1
            assert parsed_json["error_log"][0]["error_type"] == "TestError"
    
    def test_output_result_success_json(self, cli_handler):
        """Test JSON output for successful registration"""
        cli_handler.json_output = True
        cli_handler.automation_service.get_error_log.return_value = []
        
        with patch('builtins.print') as mock_print:
            cli_handler.output_result("testuser", True)
            
            printed_text = mock_print.call_args[0][0]
            result = json.loads(printed_text)
            
            assert result["username"] == "testuser"
            assert result["success"] is True
    
    def test_output_result_failure_json(self, cli_handler):
        """Test JSON output for failed registration"""
        cli_handler.json_output = True
        error_details = {
            "error_type": "ElementNotFoundError",
            "error_message": "Button not found"
        }
        
        with patch('builtins.print') as mock_print:
            cli_handler.output_result("testuser", False, error_details)
            
            printed_text = mock_print.call_args[0][0]
            result = json.loads(printed_text)
            
            assert result["username"] == "testuser"
            assert result["success"] is False
            assert result["error"]["error_type"] == "ElementNotFoundError"
    
    @pytest.mark.asyncio
    async def test_register_account_backend_error(self, cli_handler):
        """Test registration with backend initialization error"""
        cli_handler.automation_service.set_backend.side_effect = Exception("Backend failed")
        
        result = await cli_handler.register_account("testuser", "testpass123", "invalid_backend")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_register_account_validation_error(self, cli_handler):
        """Test registration with validation error"""
        result = await cli_handler.register_account("", "short")  # Invalid inputs
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_register_account_with_custom_exception(self, cli_handler):
        """Test registration with custom automation exception"""
        cli_handler.automation_service.set_backend = Mock()
        cli_handler.automation_service.clear_error_log = Mock()
        cli_handler.automation_service.get_error_log.return_value = []
        
        # Mock the register_single_account to raise our custom exception
        cli_handler.automation_service.register_single_account = AsyncMock(
            side_effect=ElementNotFoundError(".register-btn", "button", 10)
        )
        
        cli_handler.verbose_mode = True
        cli_handler.json_output = False
        
        with patch('builtins.print') as mock_print:
            result = await cli_handler.register_account("testuser", "testpass123")
            
            assert result is False
            assert cli_handler.detailed_error is not None
            assert isinstance(cli_handler.detailed_error, ElementNotFoundError)
    
    @pytest.mark.asyncio
    async def test_register_account_success_flow(self, cli_handler):
        """Test successful registration flow"""
        cli_handler.automation_service.set_backend = Mock()
        cli_handler.automation_service.clear_error_log = Mock()
        cli_handler.automation_service.get_error_log.return_value = []
        cli_handler.automation_service.register_single_account = AsyncMock(return_value=True)
        
        # Mock the success callback
        cli_handler.success = True
        
        result = await cli_handler.register_account("testuser", "testpass123")
        
        assert result is True


class TestCLIMainFunction:
    """Test the main CLI function with error scenarios"""
    
    def test_main_with_verbose_flag(self):
        """Test main function with verbose flag"""
        test_args = [
            "main.py",
            "--username", "testuser",
            "--password", "testpass123",
            "--verbose"
        ]
        
        with patch('sys.argv', test_args):
            with patch('src.cli.CLIHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler.verbose_mode = False
                mock_handler.json_output = False
                mock_handler_class.return_value = mock_handler
                
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = True
                    
                    with patch('sys.exit') as mock_exit:
                        from src.cli import main
                        main()
                        
                        # Check that verbose mode was enabled
                        assert mock_handler.verbose_mode is True
                        mock_exit.assert_called_with(0)
    
    def test_main_with_json_flag(self):
        """Test main function with JSON flag"""
        test_args = [
            "main.py",
            "--username", "testuser",
            "--password", "testpass123",
            "--json"
        ]
        
        with patch('sys.argv', test_args):
            with patch('src.cli.CLIHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler.verbose_mode = False
                mock_handler.json_output = False
                mock_handler_class.return_value = mock_handler
                
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = True
                    
                    with patch('sys.exit') as mock_exit:
                        from src.cli import main
                        main()
                        
                        # Check that JSON mode was enabled
                        assert mock_handler.json_output is True
                        mock_exit.assert_called_with(0)
    
    def test_main_with_error_log_flag(self):
        """Test main function with error log flag"""
        test_args = [
            "main.py",
            "--username", "testuser",
            "--password", "testpass123",
            "--error-log"
        ]
        
        with patch('sys.argv', test_args):
            with patch('src.cli.CLIHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler.detailed_error = ElementNotFoundError(".btn", "button", 10)
                mock_handler_class.return_value = mock_handler
                
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = False  # Failure
                    
                    with patch('sys.exit') as mock_exit:
                        from src.cli import main
                        main()
                        
                        # Check that error log display was called
                        mock_handler.display_error_log.assert_called_once()
                        mock_exit.assert_called_with(1)  # Exit code 1 for failure
    
    def test_main_keyboard_interrupt(self):
        """Test main function handling keyboard interrupt"""
        test_args = [
            "main.py",
            "--username", "testuser",
            "--password", "testpass123"
        ]
        
        with patch('sys.argv', test_args):
            with patch('src.cli.CLIHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler.json_output = False
                mock_handler_class.return_value = mock_handler
                
                with patch('asyncio.run') as mock_run:
                    mock_run.side_effect = KeyboardInterrupt()
                    
                    with patch('builtins.print') as mock_print:
                        with patch('sys.exit') as mock_exit:
                            from src.cli import main
                            main()
                            
                            mock_print.assert_called_with("\nOperation cancelled by user")
                            mock_exit.assert_called_with(1)
    
    def test_main_keyboard_interrupt_json_mode(self):
        """Test main function handling keyboard interrupt in JSON mode"""
        test_args = [
            "main.py",
            "--username", "testuser",
            "--password", "testpass123",
            "--json"
        ]
        
        with patch('sys.argv', test_args):
            with patch('src.cli.CLIHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler.json_output = True
                mock_handler_class.return_value = mock_handler
                
                with patch('asyncio.run') as mock_run:
                    mock_run.side_effect = KeyboardInterrupt()
                    
                    with patch('builtins.print') as mock_print:
                        with patch('sys.exit') as mock_exit:
                            from src.cli import main
                            main()
                            
                            # Should print JSON error
                            printed_text = mock_print.call_args[0][0]
                            result = json.loads(printed_text)
                            assert result["error"]["type"] == "UserCancellation"
                            mock_exit.assert_called_with(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])