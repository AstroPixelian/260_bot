#!/usr/bin/env python3
"""
Rich UI 命令行界面 - Rich UI CLI Module
提供基于Rich框架的交互式批量账号注册界面

Rich UI Command Line Interface Module  
Provides Rich framework based interactive batch account registration interface
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import string

# Rich UI components
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.columns import Columns
from rich import box
from rich.rule import Rule
from rich.logging import RichHandler
from rich.markdown import Markdown
from collections import deque
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.account import Account, AccountStatus
from src.services.automation.automation_service import AutomationService
from src.services.persistence_service import PersistenceService
from src.account_generator import AccountGenerator


class RichCLIConfig:
    """Rich CLI配置类"""
    
    def __init__(self):
        self.account_count: int = 5
        self.backend: str = "playwright"
        self.verbose: bool = True
        self.headless: bool = False  # 新增无头模式选项
        self.output_dir: str = str(Path.cwd())
        self.batch_size: int = 5
        self.timeout_seconds: int = 120
        self.max_retries: int = 3


class RichCLIHandler:
    """Rich UI CLI处理器"""
    
    def __init__(self):
        self.console = Console()
        self.config = RichCLIConfig()
        self.automation_service: Optional[AutomationService] = None
        self.persistence_service: Optional[PersistenceService] = None
        self.accounts: List[Account] = []
        self.current_account_index = 0
        self.start_time = None
        
        # 日志管理
        self.log_messages = deque(maxlen=100)  # 保持最新的100条日志
        self.setup_logging()
        
        # 创建符合360注册限制的账号生成器配置
        self.account_generator_config = {
            "account_generator": {
                "username_min_length": 2,    # 360注册要求: 2-14位
                "username_max_length": 14,   # 360注册要求: 2-14位
                "password_min_length": 8,    # 常见密码要求
                "password_max_length": 20,   # 360注册要求: 最多20位
                "password_special_chars": "!@#$%^&*"  # 可选特殊字符
            }
        }
        self.account_generator = AccountGenerator(self.account_generator_config)
        
        # 统计信息
        self.stats = {
            'success': 0,
            'failed': 0,
            'processing': 0,
            'pending': 0,
            'total_duration': 0
        }
        
        # 日志更新标志
        self.log_updated = False
    
    def setup_logging(self):
        """设置日志系统"""
        # 创建自定义日志处理器，将日志消息添加到队列中
        class LogMessageHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted_msg = f"{timestamp} {msg}"
                    self.log_queue.append(formatted_msg)
                except Exception:
                    pass  # 避免日志系统本身出错
        
        # 设置自定义处理器
        self.log_handler = LogMessageHandler(self.log_messages)
        self.log_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(message)s')
        self.log_handler.setFormatter(formatter)
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """手动添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据级别添加颜色标记
        if level == "SUCCESS":
            colored_msg = f"[green]✅ {message}[/green]"
        elif level == "ERROR":
            colored_msg = f"[red]❌ {message}[/red]"
        elif level == "WARNING":
            colored_msg = f"[yellow]⚠️ {message}[/yellow]"
        elif level == "INFO":
            colored_msg = f"[blue]ℹ️ {message}[/blue]"
        else:
            colored_msg = message
        
        formatted_msg = f"{timestamp} {colored_msg}"
        self.log_messages.append(formatted_msg)
        
        # 标记有新日志需要更新显示
        self.log_updated = True
    
    def get_log_panel(self, height: int = 8) -> Panel:
        """获取日志显示面板"""
        # 获取最新的日志消息
        recent_logs = list(self.log_messages)[-height:]
        
        if not recent_logs:
            log_content = "[dim]暂无日志信息...[/dim]"
        else:
            log_content = "\n".join(recent_logs)
        
        return Panel(
            log_content,
            title="📋 实时日志",
            box=box.ROUNDED,
            style="dim",
            height=height + 2,  # +2 for border
        )
    
    def show_welcome(self):
        """显示欢迎界面"""
        self.console.clear()
        
        welcome_panel = Panel(
            Align.center(
                Text("🌟 360 Account Batch Creator 🌟\n", style="bold blue") +
                Text("State Machine Registration System", style="dim")
            ),
            box=box.DOUBLE,
            style="blue",
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        self.console.print()
    
    def show_config_interface(self) -> bool:
        """显示配置界面并获取用户输入"""
        config_panel = Panel(
            self._create_config_content(),
            title="📋 配置界面",
            box=box.DOUBLE,
            style="green"
        )
        
        self.console.print(config_panel)
        
        # 获取用户配置
        try:
            self.config.account_count = IntPrompt.ask(
                "🎯 请输入要注册的账号数量",
                default=self.config.account_count,
                show_default=True,
                console=self.console
            )
            
            if self.config.account_count < 1 or self.config.account_count > 100:
                self.console.print("[red]❌ 账号数量必须在1-100之间[/red]")
                return False
            
            backend_choice = Prompt.ask(
                "🔧 选择自动化后端",
                choices=["playwright", "selenium"],
                default=self.config.backend,
                console=self.console
            )
            self.config.backend = backend_choice
            
            self.config.verbose = Confirm.ask(
                "📋 启用详细日志输出？",
                default=self.config.verbose,
                console=self.console
            )
            
            self.config.headless = Confirm.ask(
                "🖥️ 静默运行模式（浏览器在后台运行，不显示界面）？",
                default=self.config.headless,
                console=self.console
            )
            
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ 用户取消操作[/yellow]")
            return False
    
    def _create_config_content(self) -> str:
        """创建配置界面内容"""
        return f"""
🎯 注册配置
  ├─ 账号数量: {self.config.account_count} (1-100)
  ├─ 自动化后端: {self.config.backend}
  ├─ 详细日志: {'启用' if self.config.verbose else '禁用'}
  ├─ 静默模式: {'启用' if self.config.headless else '禁用'}
  └─ 保存目录: {self.config.output_dir}

📁 输出设置
  ├─ 批量大小: {self.config.batch_size} (每{self.config.batch_size}个账号保存一次)
  └─ 备份策略: ✅ 启用文件锁保护

⚙️ 高级设置
  ├─ 超时设置: {self.config.timeout_seconds}秒 验证码等待
  ├─ 重试次数: {self.config.max_retries}次 失败重试
  └─ 账号规格: 用户名2-14位，密码8-20位
"""
    
    def show_confirmation(self) -> bool:
        """显示确认界面"""
        # 生成时间戳文件名预览
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"registration_results_{timestamp}.csv"
        
        confirmation_content = f"""
📋 即将执行的操作:
  • 生成 {self.config.account_count} 个随机账号（符合360注册规范）
  • 使用 {self.config.backend.title()} 后端自动注册
  • {'启用' if self.config.verbose else '禁用'}详细日志输出
  • {'启用' if self.config.headless else '禁用'}静默运行模式
  • 结果保存到 {csv_filename}

⏱️ 预计耗时: 约 {self.config.account_count * 1.5:.0f}-{self.config.account_count * 3:.0f} 分钟 (取决于验证码处理)

⚠️ 注意事项:
  • 账号自动生成：用户名2-14位，密码8-20位
  • {'静默模式下遇到验证码将暂停等待处理' if self.config.headless else '遇到验证码时可在浏览器中手动处理'}
  • 可以随时按 Ctrl+C 安全退出
  • 已保存的数据不会丢失
"""
        
        confirmation_panel = Panel(
            confirmation_content,
            title="⚠️ 确认执行",
            box=box.DOUBLE,
            style="yellow"
        )
        
        self.console.print(confirmation_panel)
        
        try:
            return Confirm.ask(
                "✅ 确认开始批量注册？",
                default=True,
                console=self.console
            )
        except KeyboardInterrupt:
            return False
    
    def initialize_services(self):
        """初始化服务"""
        try:
            # 初始化自动化服务 - 目前无头模式参数需要在后端实现中支持
            # TODO: 将headless参数传递给AutomationService
            self.automation_service = AutomationService(backend_type=self.config.backend)
            
            # 初始化持久化服务
            self.persistence_service = PersistenceService(
                output_dir=self.config.output_dir,
                batch_size=self.config.batch_size
            )
            
            # 使用AccountGenerator生成账号
            self.console.print(f"[blue]🎲 正在生成 {self.config.account_count} 个符合360规范的账号...[/blue]")
            
            # 生成账号字典列表
            account_dicts = self.account_generator.generate_unique_accounts(self.config.account_count)
            
            # 转换为Account对象
            self.accounts = []
            for i, account_dict in enumerate(account_dicts):
                account = Account(
                    id=i + 1,
                    username=account_dict['username'],
                    password=account_dict['password']
                )
                self.accounts.append(account)
            
            self.console.print(f"[green]✅ 成功生成 {len(self.accounts)} 个账号[/green]")
            
            # 显示生成的账号样本（前3个）
            if self.accounts and self.config.verbose:
                self.console.print("[dim]📋 账号样本（前3个）：[/dim]")
                for i, account in enumerate(self.accounts[:3]):
                    self.console.print(f"[dim]  {i+1}. {account.username} (密码长度: {len(account.password)})[/dim]")
                if len(self.accounts) > 3:
                    self.console.print(f"[dim]  ... 和其他 {len(self.accounts)-3} 个账号[/dim]")
            
            # 设置回调
            self._setup_callbacks()
            
        except Exception as e:
            self.console.print(f"[red]❌ 服务初始化失败: {e}[/red]")
            raise
    
    def _setup_callbacks(self):
        """设置自动化服务回调"""
        def on_account_start(account: Account):
            account._start_time = time.time()
            self.add_log_message(f"开始处理账号: {account.username}", "INFO")
        
        def on_account_complete(account: Account):
            # 计算耗时
            if hasattr(account, '_start_time'):
                account._duration = time.time() - account._start_time
            else:
                account._duration = 0
            
            # 添加日志
            if account.status == AccountStatus.SUCCESS:
                self.add_log_message(f"账号 {account.username} 注册成功 ({account._duration:.1f}s)", "SUCCESS")
            elif account.status == AccountStatus.FAILED:
                self.add_log_message(f"账号 {account.username} 注册失败: {account.notes}", "ERROR")
            elif account.status == AccountStatus.CAPTCHA_PENDING:
                self.add_log_message(f"账号 {account.username} 需要处理验证码", "WARNING")
            
            # 保存结果
            if self.persistence_service:
                self.persistence_service.add_result(
                    account, 
                    account._duration, 
                    self.automation_service.get_backend_name()
                )
            
            # 更新统计
            self._update_stats(account)
        
        def on_log_message(message: str):
            # 在详细模式下记录自动化服务的日志
            if self.config.verbose:
                self.add_log_message(message, "INFO")
        
        self.automation_service.set_callbacks(
            on_account_start=on_account_start,
            on_account_complete=on_account_complete,
            on_log_message=on_log_message
        )
    
    def _update_stats(self, account: Account):
        """更新统计信息"""
        if account.status == AccountStatus.SUCCESS:
            self.stats['success'] += 1
        elif account.status == AccountStatus.FAILED:
            self.stats['failed'] += 1
    
    async def run_batch_registration(self):
        """运行批量注册"""
        self.start_time = time.time()
        
        # 如果启用详细日志，使用带日志显示的布局界面
        if self.config.verbose:
            await self._run_with_log_display()
        else:
            await self._run_simple_progress()
    
    async def _run_simple_progress(self):
        """简单进度显示模式（无详细日志）"""
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            
            overall_task = progress.add_task(
                "🚀 批量注册进度", 
                total=len(self.accounts)
            )
            
            await self._process_accounts(progress, overall_task)
    
    async def _run_with_log_display(self):
        """带日志显示的进度模式"""
        from rich.layout import Layout
        from rich.live import Live
        
        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(name="progress", size=8),
            Layout(name="logs", ratio=1)
        )
        
        # 创建进度组件
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn()
        )
        
        overall_task = progress.add_task(
            "🚀 批量注册进度", 
            total=len(self.accounts)
        )
        
        # 初始化布局
        layout["progress"].update(
            Panel(progress, title="📊 注册进度", border_style="blue")
        )
        layout["logs"].update(self.get_log_panel())
        
        # 启动实时显示
        with Live(layout, console=self.console, refresh_per_second=10):
            # 创建后台任务来监控日志更新
            log_update_task = asyncio.create_task(self._monitor_log_updates(layout))
            
            try:
                # 处理账号注册
                await self._process_accounts(progress, overall_task, layout)
            finally:
                # 停止日志监控任务
                log_update_task.cancel()
                try:
                    await log_update_task
                except asyncio.CancelledError:
                    pass
    
    async def _monitor_log_updates(self, layout):
        """后台监控日志更新"""
        while True:
            if self.log_updated:
                # 更新日志显示
                layout["logs"].update(self.get_log_panel())
                self.log_updated = False
            
            # 等待一小段时间再次检查
            await asyncio.sleep(0.1)  # 100ms 检查间隔，确保实时性
    
    async def _process_accounts(self, progress, overall_task, layout=None):
        """处理账号注册逻辑"""
        for i, account in enumerate(self.accounts):
            self.current_account_index = i
            
            # 更新进度描述
            progress.update(
                overall_task, 
                description=f"🔄 正在处理: {account.username}"
            )
            
            try:
                # 注册账号
                await self.automation_service.register_single_account(account)
                
                # 在非详细模式下显示简单结果
                if not self.config.verbose:
                    if account.status == AccountStatus.SUCCESS:
                        self.console.print(f"[green]✅ {account.username} 注册成功[/green]")
                    elif account.status == AccountStatus.CAPTCHA_PENDING:
                        self.console.print(f"[yellow]🔍 {account.username} 需要处理验证码[/yellow]")
                    else:
                        self.console.print(f"[red]❌ {account.username} 注册失败: {account.notes}[/red]")
                
            except KeyboardInterrupt:
                self.add_log_message("用户中断操作", "WARNING")
                if not self.config.verbose:
                    self.console.print("\n[yellow]⚠️ 用户中断操作[/yellow]")
                break
            except Exception as e:
                account.mark_failed(f"注册异常: {str(e)}")
                error_msg = f"账号 {account.username} 发生异常: {e}"
                self.add_log_message(error_msg, "ERROR")
                if not self.config.verbose:
                    self.console.print(f"[red]💥 {error_msg}[/red]")
            
            # 更新进度
            progress.update(overall_task, advance=1)
        
        # 强制保存剩余数据
        if self.persistence_service:
            self.persistence_service.force_save()
    
    def show_results(self):
        """显示最终结果"""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        # 创建结果表格
        results_table = Table(title="📋 详细结果", box=box.ROUNDED)
        results_table.add_column("账号", style="cyan")
        results_table.add_column("状态", justify="center")
        results_table.add_column("耗时", style="magenta")
        results_table.add_column("备注", style="dim")
        
        for account in self.accounts:
            status_style = {
                AccountStatus.SUCCESS: "[green]✅ 成功[/green]",
                AccountStatus.FAILED: "[red]❌ 失败[/red]",
                AccountStatus.CAPTCHA_PENDING: "[yellow]🔍 验证码[/yellow]",
                AccountStatus.QUEUED: "[blue]⏳ 等待[/blue]",
                AccountStatus.PROCESSING: "[yellow]🔄 处理中[/yellow]"
            }.get(account.status, "[dim]❓ 未知[/dim]")
            
            duration = getattr(account, '_duration', 0)
            duration_str = f"{duration:.1f}s" if duration > 0 else "-"
            
            results_table.add_row(
                account.username,
                status_style,
                duration_str,
                account.notes or "-"
            )
        
        # 创建统计信息
        success_rate = (self.stats['success'] / len(self.accounts) * 100) if self.accounts else 0
        stats_content = f"""
📊 最终统计
  ├─ ✅ 成功注册: {self.stats['success']} 个账号 ({success_rate:.1f}%)
  ├─ ❌ 注册失败: {self.stats['failed']} 个账号 ({100-success_rate:.1f}%)
  ├─ ⏱️ 总耗时: {total_duration/60:.1f} 分钟
  └─ 💾 数据已保存: {self.persistence_service.csv_file.name if self.persistence_service else 'N/A'}

🔗 后续操作
  • 查看完整结果: cat {self.persistence_service.csv_file.name if self.persistence_service else 'results.csv'}
  • 重新运行: python rich_cli.py
  • 查看项目: https://github.com/your-repo/tanke_260_bot
"""
        
        # 显示结果
        self.console.print()
        results_panel = Panel(
            stats_content,
            title="🎉 批量注册完成",
            box=box.DOUBLE,
            style="green"
        )
        
        self.console.print(results_panel)
        self.console.print(results_table)
    
    async def run(self):
        """运行Rich UI CLI主程序"""
        try:
            # 1. 显示欢迎界面
            self.show_welcome()
            
            # 2. 显示配置界面
            if not self.show_config_interface():
                return
            
            # 3. 显示确认界面
            if not self.show_confirmation():
                self.console.print("[yellow]⚠️ 操作已取消[/yellow]")
                return
            
            # 4. 初始化服务
            self.console.print("[blue]🔧 正在初始化服务...[/blue]")
            self.initialize_services()
            
            # 5. 运行批量注册
            await self.run_batch_registration()
            
            # 6. 显示结果
            self.show_results()
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ 程序被用户中断[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]💥 程序执行出错: {e}[/red]")
            import traceback
            if self.config.verbose:
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
        finally:
            # 确保数据保存
            if self.persistence_service:
                self.persistence_service.force_save()


async def main():
    """主入口函数"""
    console = Console()
    
    # 显示启动消息
    console.print("[bold blue]🚀 360 账号批量注册器 - Rich UI 版本[/bold blue]")
    console.print("[dim]启动中...[/dim]\n")
    
    rich_cli = RichCLIHandler()
    await rich_cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 程序已退出")
        sys.exit(1)