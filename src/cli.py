"""
命令行接口模块 - CLI Module
提供用于单账户注册的命令行接口

Command Line Interface Module
Provides CLI functionality for single account registration
"""

import argparse
import asyncio
import sys
from typing import Optional, Tuple

from .models.account import Account, AccountStatus
from .services.automation_service import AutomationService


# Simplified tr function for CLI mode (without Qt dependency)
def tr(text: str, context: str = "CLI") -> str:
    """Simple translation function for CLI mode - returns text as-is for now"""
    return text


class CLIHandler:
    """CLI处理器类 - CLI Handler Class"""
    
    def __init__(self):
        self.automation_service = AutomationService()
        self.success = False
        self.error_message = ""
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """
        创建命令行参数解析器
        Create command line argument parser
        """
        parser = argparse.ArgumentParser(
            description=tr("360 Account Batch Creator - CLI Mode"),
            prog="main.py",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help=tr("Username for account registration (required)")
        )
        
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help=tr("Password for account registration (required, min 6 characters)")
        )
        
        return parser
    
    def validate_arguments(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        验证命令行参数
        Validate command line arguments
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not username or not username.strip():
            return False, tr("Username cannot be empty")
        
        if not password or len(password) < 6:
            return False, tr("Password must be at least 6 characters long")
        
        return True, None
    
    def setup_callbacks(self):
        """设置自动化服务回调 - Setup automation service callbacks"""
        def on_account_start(account: Account):
            print(tr("Starting registration for account: {0}").format(account.username))
        
        def on_account_complete(account: Account):
            if account.status == AccountStatus.SUCCESS:
                self.success = True
                print(tr("Success"))
            else:
                self.success = False
                self.error_message = account.notes or tr("Registration failed")
                print(tr("Error: {0}").format(self.error_message))
        
        def on_log_message(message: str):
            # In CLI mode, we keep log messages minimal
            pass
        
        self.automation_service.set_callbacks(
            on_account_start=on_account_start,
            on_account_complete=on_account_complete,
            on_log_message=on_log_message
        )
    
    async def register_account(self, username: str, password: str) -> bool:
        """
        注册单个账户
        Register a single account
        
        Args:
            username: Account username
            password: Account password
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        # Validate arguments
        is_valid, error_msg = self.validate_arguments(username, password)
        if not is_valid:
            print(tr("Error: {0}").format(error_msg))
            return False
        
        # Create account object
        account = Account(
            id=1,  # Single account for CLI mode
            username=username.strip(),
            password=password
        )
        
        # Setup callbacks
        self.setup_callbacks()
        
        try:
            # Register account using existing automation service
            await self.automation_service.register_single_account(account)
            return self.success
        
        except Exception as e:
            print(tr("Error: {0}").format(str(e)))
            return False


def main():
    """CLI主入口点 - CLI main entry point"""
    cli_handler = CLIHandler()
    
    try:
        # Parse command line arguments
        parser = cli_handler.create_argument_parser()
        args = parser.parse_args()
        
        # Run registration
        success = asyncio.run(
            cli_handler.register_account(args.username, args.password)
        )
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(tr("\nOperation cancelled by user"))
        sys.exit(1)
    except Exception as e:
        print(tr("Unexpected error: %1").arg(str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()