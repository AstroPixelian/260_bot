"""
命令行接口模块 - CLI Module
提供用于单账户注册的命令行接口

Command Line Interface Module
Provides CLI functionality for single account registration
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# 添加项目根目录到路径 - Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.account import Account, AccountStatus
from src.services.automation.automation_service import AutomationService
from src.services.persistence_service import PersistenceService


# Simplified tr function for CLI mode (without Qt dependency)
def tr(text: str, context: str = "CLI") -> str:
    """Simple translation function for CLI mode - returns text as-is for now"""
    return text


class CLIHandler:
    """CLI处理器类 - CLI Handler Class"""
    
    def __init__(self):
        # Use simplified state machine backend by default for better functionality
        self.automation_service = AutomationService(backend_type="playwright")
        
        # 创建持久化服务（保存到当前目录）
        self.persistence_service = PersistenceService(
            output_dir=str(Path.cwd()),  # CLI脚本同目录
            batch_size=5  # 每5个账号批量保存
        )
        
        self.success = False
        self.error_message = ""
        self.start_time = None
    
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
            choices=["playwright", "selenium"],
            default="playwright",
            help=tr("Automation backend to use (default: playwright)")
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
        
        # 设置所有回调，包括coordination回调
        self.automation_service.set_callbacks(
            on_account_start=on_account_start,
            on_account_complete=self._get_combined_complete_callback(on_account_complete),
            on_log_message=on_log_message
        )
    
    def _get_combined_complete_callback(self, original_callback):
        """获取组合的完成回调，包含持久化逻辑"""
        def combined_callback(account):
            # 执行原始回调
            original_callback(account)
            
            # 执行持久化逻辑
            duration = getattr(account, '_duration', 0.0)
            backend = self.automation_service.get_backend_name()
            self.persistence_service.add_result(account, duration, backend)
            
            # 显示统计信息
            stats = self.persistence_service.get_stats()
            print(f"💾 已处理: {stats['total_saved'] + stats['buffer_count']} 个账号")
        
        return combined_callback
    
    async def register_account(self, username: str, password: str, verbose: bool = False, backend: str = "playwright") -> bool:
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
        if backend != "playwright":
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
            self.start_time = time.time()
            print(tr("🚀 360 Account Registration Started"))
            print(tr("   Backend: {0}").format(backend))
            print(tr("   Username: {0}").format(username))
            print(tr("   Results file: {0}").format(self.persistence_service.csv_file))
            print(tr("   State Machine: Enabled"))
            print("-" * 50)
            
            # 给account添加计时功能
            account._start_time = time.time()
            
            # Register account using automation service
            await self.automation_service.register_single_account(account)
            
            # 计算耗时
            account._duration = time.time() - account._start_time
            
            print("-" * 50)
            if self.success:
                print(tr("🎉 Registration completed successfully!"))
            else:
                print(tr("💥 Registration failed: {0}").format(self.error_message))
            
            # 显示最终统计
            stats = self.persistence_service.get_stats()
            print(f"💾 结果已保存: {stats['file_path']}")
            print(f"📊 总计处理: {stats['total_saved']} 个账号")
            
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