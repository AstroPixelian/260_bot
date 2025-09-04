"""
命令行接口模块 - CLI Module
提供用于单账户注册的命令行接口

Command Line Interface Module
Provides CLI functionality for single account registration
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional, Tuple

# 添加项目根目录到路径 - Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.account import Account, AccountStatus
from src.services.automation.automation_service import AutomationService


# Simplified tr function for CLI mode (without Qt dependency)
def tr(text: str, context: str = "CLI") -> str:
    """Simple translation function for CLI mode - returns text as-is for now"""
    return text


class CLIHandler:
    """CLI处理器类 - CLI Handler Class"""
    
    def __init__(self):
        # Use simplified state machine backend by default for better functionality
        self.automation_service = AutomationService(backend_type="simple_playwright")
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
        
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=tr("Enable verbose logging output")
        )
        
        parser.add_argument(
            "--backend",
            type=str,
            choices=["simple_playwright", "selenium"],
            default="simple_playwright",
            help=tr("Automation backend to use (default: simple_playwright)")
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
    
    def setup_callbacks(self, verbose: bool = False):
        """设置自动化服务回调 - Setup automation service callbacks"""
        def on_account_start(account: Account):
            print(tr("🔄 Starting registration for account: {0}").format(account.username))
        
        def on_account_complete(account: Account):
            if account.status == AccountStatus.SUCCESS:
                self.success = True
                print(tr("✅ Success: Account {0} registered successfully").format(account.username))
            elif account.status == AccountStatus.CAPTCHA_PENDING:
                print(tr("⚠️  CAPTCHA detected for {0} - Please solve manually").format(account.username))
                print(tr("   Browser will remain open. Complete the CAPTCHA and press Enter..."))
                input()  # Wait for user to complete captcha
            else:
                self.success = False
                self.error_message = account.notes or tr("Registration failed")
                print(tr("❌ Error: Account {0} failed - {1}").format(account.username, self.error_message))
        
        def on_log_message(message: str):
            # Show detailed logs in CLI mode when verbose is enabled
            if verbose:
                print(tr("📋 {0}").format(message))
        
        self.automation_service.set_callbacks(
            on_account_start=on_account_start,
            on_account_complete=on_account_complete,
            on_log_message=on_log_message
        )
    
    async def register_account(self, username: str, password: str, verbose: bool = False, backend: str = "playwright_v2") -> bool:
        """
        注册单个账户
        Register a single account
        
        Args:
            username: Account username
            password: Account password
            verbose: Enable verbose logging
            backend: Automation backend to use
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        # Validate arguments
        is_valid, error_msg = self.validate_arguments(username, password)
        if not is_valid:
            print(tr("❌ Error: {0}").format(error_msg))
            return False
        
        # Update backend if specified
        if backend != "simple_playwright":
            try:
                self.automation_service = AutomationService(backend_type=backend)
                print(tr("🔧 Using backend: {0}").format(backend))
            except Exception as e:
                print(tr("❌ Error initializing backend {0}: {1}").format(backend, str(e)))
                return False
        
        # Create account object
        account = Account(
            id=1,  # Single account for CLI mode
            username=username.strip(),
            password=password
        )
        
        # Setup callbacks with verbose option
        self.setup_callbacks(verbose)
        
        try:
            print(tr("🚀 360 Account Registration Started"))
            print(tr("   Backend: {0}").format(backend))
            print(tr("   Username: {0}").format(username))
            print(tr("   Verbose: {0}").format("Enabled" if verbose else "Disabled"))
            print(tr("   State Machine: Enabled" if backend == "playwright_v2" else "   State Machine: Disabled"))
            print("-" * 50)
            
            # Register account using automation service
            await self.automation_service.register_single_account(account)
            
            print("-" * 50)
            if self.success:
                print(tr("🎉 Registration completed successfully!"))
            else:
                print(tr("💥 Registration failed: {0}").format(self.error_message))
            
            return self.success
        
        except Exception as e:
            print(tr("❌ Unexpected error: {0}").format(str(e)))
            return False


def main():
    """CLI主入口点 - CLI main entry point"""
    cli_handler = CLIHandler()
    
    try:
        # Parse command line arguments
        parser = cli_handler.create_argument_parser()
        args = parser.parse_args()
        
        # Show welcome message
        print("=" * 60)
        print("🌟 360 Account Batch Creator - CLI Mode")
        print("   State Machine Enabled Registration System")
        print("=" * 60)
        
        # Run registration
        success = asyncio.run(
            cli_handler.register_account(
                args.username, 
                args.password, 
                verbose=args.verbose,
                backend=args.backend
            )
        )
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(tr("\n⚠️  Operation cancelled by user"))
        sys.exit(1)
    except Exception as e:
        print(tr("💥 Unexpected error: {0}").format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()