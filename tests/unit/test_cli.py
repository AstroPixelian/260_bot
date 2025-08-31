"""
CLI模块的单元测试
Unit tests for CLI module
"""

import argparse
import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import io

# Add src to path for testing
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from src.cli import CLIHandler
from src.models.account import Account, AccountStatus


class TestCLIHandler:
    """CLI处理器测试类"""
    
    def setup_method(self):
        """Test setup"""
        self.cli_handler = CLIHandler()
    
    def test_create_argument_parser(self):
        """测试参数解析器创建"""
        parser = self.cli_handler.create_argument_parser()
        
        # Test parser type
        assert isinstance(parser, argparse.ArgumentParser)
        
        # Test with valid arguments
        args = parser.parse_args(['--username', 'testuser', '--password', 'testpass123'])
        assert args.username == 'testuser'
        assert args.password == 'testpass123'
        
        # Test missing required arguments
        with pytest.raises(SystemExit):
            parser.parse_args(['--username', 'testuser'])  # Missing password
            
        with pytest.raises(SystemExit):
            parser.parse_args(['--password', 'testpass123'])  # Missing username
    
    def test_validate_arguments_valid(self):
        """测试有效参数验证"""
        is_valid, error_msg = self.cli_handler.validate_arguments('testuser', 'validpass123')
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_arguments_invalid_username(self):
        """测试无效用户名验证"""
        # Empty username
        is_valid, error_msg = self.cli_handler.validate_arguments('', 'validpass123')
        assert is_valid is False
        assert error_msg is not None
        
        # Whitespace only username
        is_valid, error_msg = self.cli_handler.validate_arguments('   ', 'validpass123')
        assert is_valid is False
        assert error_msg is not None
        
        # None username
        is_valid, error_msg = self.cli_handler.validate_arguments(None, 'validpass123')
        assert is_valid is False
        assert error_msg is not None
    
    def test_validate_arguments_invalid_password(self):
        """测试无效密码验证"""
        # Short password
        is_valid, error_msg = self.cli_handler.validate_arguments('testuser', 'short')
        assert is_valid is False
        assert error_msg is not None
        
        # Empty password
        is_valid, error_msg = self.cli_handler.validate_arguments('testuser', '')
        assert is_valid is False
        assert error_msg is not None
        
        # None password
        is_valid, error_msg = self.cli_handler.validate_arguments('testuser', None)
        assert is_valid is False
        assert error_msg is not None
    
    def test_setup_callbacks(self):
        """测试回调设置"""
        # Mock automation service
        self.cli_handler.automation_service = Mock()
        
        # Setup callbacks
        self.cli_handler.setup_callbacks()
        
        # Verify set_callbacks was called
        self.cli_handler.automation_service.set_callbacks.assert_called_once()
        
        # Get the callback functions
        call_args = self.cli_handler.automation_service.set_callbacks.call_args[1]
        assert 'on_account_start' in call_args
        assert 'on_account_complete' in call_args
        assert 'on_log_message' in call_args
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_callback_success(self, mock_stdout):
        """测试成功回调处理"""
        self.cli_handler.automation_service = Mock()
        self.cli_handler.setup_callbacks()
        
        # Get the callback functions
        call_args = self.cli_handler.automation_service.set_callbacks.call_args[1]
        on_account_complete = call_args['on_account_complete']
        
        # Create successful account
        account = Account(id=1, username='testuser', password='testpass123')
        account.status = AccountStatus.SUCCESS
        
        # Trigger callback
        on_account_complete(account)
        
        # Check results
        assert self.cli_handler.success is True
        assert 'Success' in mock_stdout.getvalue()
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_callback_failure(self, mock_stdout):
        """测试失败回调处理"""
        self.cli_handler.automation_service = Mock()
        self.cli_handler.setup_callbacks()
        
        # Get the callback functions
        call_args = self.cli_handler.automation_service.set_callbacks.call_args[1]
        on_account_complete = call_args['on_account_complete']
        
        # Create failed account
        account = Account(id=1, username='testuser', password='testpass123')
        account.status = AccountStatus.FAILED
        account.notes = 'Test error message'
        
        # Trigger callback
        on_account_complete(account)
        
        # Check results
        assert self.cli_handler.success is False
        assert self.cli_handler.error_message == 'Test error message'
        assert 'Error' in mock_stdout.getvalue()
    
    @pytest.mark.asyncio
    async def test_register_account_success(self):
        """测试成功的账户注册"""
        # Mock automation service
        self.cli_handler.automation_service = Mock()
        self.cli_handler.automation_service.register_single_account = AsyncMock()
        
        # Mock successful callback
        def mock_setup_callbacks():
            self.cli_handler.success = True
        
        self.cli_handler.setup_callbacks = mock_setup_callbacks
        
        # Test registration
        result = await self.cli_handler.register_account('testuser', 'validpass123')
        
        # Verify results
        assert result is True
        self.cli_handler.automation_service.register_single_account.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_register_account_validation_failure(self, mock_stdout):
        """测试参数验证失败"""
        result = await self.cli_handler.register_account('', 'validpass123')
        
        # Verify results
        assert result is False
        assert 'Error' in mock_stdout.getvalue()
    
    @pytest.mark.asyncio
    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_register_account_exception(self, mock_stdout):
        """测试异常处理"""
        # Mock automation service to raise exception
        self.cli_handler.automation_service = Mock()
        self.cli_handler.automation_service.register_single_account = AsyncMock(
            side_effect=Exception('Test exception')
        )
        
        # Mock setup_callbacks
        self.cli_handler.setup_callbacks = Mock()
        
        # Test registration
        result = await self.cli_handler.register_account('testuser', 'validpass123')
        
        # Verify results
        assert result is False
        assert 'Error' in mock_stdout.getvalue()
        assert 'Test exception' in mock_stdout.getvalue()


class TestMainFunction:
    """主函数测试类"""
    
    @patch('sys.argv', ['main.py', '--username', 'testuser', '--password', 'testpass123'])
    @patch('sys.exit')
    @patch('asyncio.run')
    @patch('src.cli.CLIHandler')
    def test_main_function_success(self, mock_cli_handler_class, mock_asyncio_run, mock_sys_exit):
        """测试主函数成功执行"""
        # Mock CLI handler instance
        mock_cli_handler = Mock()
        mock_cli_handler_class.return_value = mock_cli_handler
        mock_cli_handler.create_argument_parser.return_value.parse_args.return_value = Mock(
            username='testuser', password='testpass123'
        )
        
        # Mock successful registration
        mock_asyncio_run.return_value = True
        
        # Import and run main
        from src.cli import main
        main()
        
        # Verify exit with success code
        mock_sys_exit.assert_called_once_with(0)
    
    @patch('sys.argv', ['main.py', '--username', 'testuser', '--password', 'short'])
    @patch('sys.exit')
    @patch('asyncio.run')
    @patch('src.cli.CLIHandler')
    def test_main_function_failure(self, mock_cli_handler_class, mock_asyncio_run, mock_sys_exit):
        """测试主函数失败执行"""
        # Mock CLI handler instance
        mock_cli_handler = Mock()
        mock_cli_handler_class.return_value = mock_cli_handler
        mock_cli_handler.create_argument_parser.return_value.parse_args.return_value = Mock(
            username='testuser', password='short'
        )
        
        # Mock failed registration
        mock_asyncio_run.return_value = False
        
        # Import and run main
        from src.cli import main
        main()
        
        # Verify exit with failure code
        mock_sys_exit.assert_called_once_with(1)