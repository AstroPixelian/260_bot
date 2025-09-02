"""
CaptchaService for 360 Account Batch Creator

MVVM-compliant service for captcha detection and handling.
Provides intelligent captcha verification with 5-second polling and 60-second timeout.
"""

import asyncio
import time
import logging
from typing import Callable, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from ..models.account import Account, AccountStatus
from ..translation_manager import tr

try:
    from PySide6.QtCore import QObject, QTimer, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


class CaptchaService(QObject if PYSIDE6_AVAILABLE else object):
    """
    MVVM Service layer for captcha detection and monitoring.
    
    Features:
    - Automatic captcha detection using precise indicators
    - 5-second polling interval for user-friendly monitoring
    - 60-second timeout handling
    - Dual-condition validation (captcha gone AND registration success)
    - Callback-based UI updates (MVVM compliant)
    """
    
    # Qt Signals for MVVM communication (only if PySide6 available)
    if PYSIDE6_AVAILABLE:
        captcha_detected = Signal(Account, str)  # account, message
        captcha_resolved = Signal(Account, str)  # account, message
        captcha_timeout = Signal(Account, str)   # account, message
    
    def __init__(self):
        if PYSIDE6_AVAILABLE:
            super().__init__()
        
        # Logging setup
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Callback functions for ViewModel communication
        self.on_captcha_detected: Optional[Callable[[Account, str], None]] = None
        self.on_captcha_resolved: Optional[Callable[[Account, str], None]] = None
        self.on_captcha_timeout: Optional[Callable[[Account, str], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None
        
        # Active monitoring timers
        self.active_timers: dict[int, QTimer] = {}
        
        # Configuration
        self.polling_interval = 5  # seconds
        self.timeout_duration = 60  # seconds (60 seconds total timeout)
    
    def set_callbacks(self,
                     on_captcha_detected: Callable[[Account, str], None] = None,
                     on_captcha_resolved: Callable[[Account, str], None] = None,
                     on_captcha_timeout: Callable[[Account, str], None] = None,
                     on_log_message: Callable[[str], None] = None):
        """Set callback functions for ViewModel communication (MVVM pattern)"""
        self.on_captcha_detected = on_captcha_detected
        self.on_captcha_resolved = on_captcha_resolved
        self.on_captcha_timeout = on_captcha_timeout
        self.on_log_message = on_log_message
    
    def detect_captcha_in_content(self, page_content: str) -> tuple[bool, str]:
        """
        Detect captcha presence in page content using precise indicators.
        
        Args:
            page_content: HTML content of the page
            
        Returns:
            tuple: (captcha_detected: bool, detection_message: str)
        """
        # Precise captcha detection - based on actual 360.cn HTML features
        high_specificity_indicators = [
            "quc-slide-con",  # 验证码滑块外层容器 - 高度特异性
            "quc-captcha-mask",  # 验证码遮罩层 - 360独有
            "请完成下方拼图验证后继续",  # 验证码具体提示文本
        ]
        
        # Check high-specificity indicators first
        for indicator in high_specificity_indicators:
            if indicator in page_content:
                return True, f"CAPTCHA_DETECTED: {indicator}"
        
        # Auxiliary captcha detection - requires multiple conditions
        auxiliary_indicators = ["verify-slide-con", "拖动滑块完成拼图"]
        if all(indicator in page_content for indicator in auxiliary_indicators):
            return True, "CAPTCHA_DETECTED: slide verification interface"
        
        return False, "No captcha detected"
    
    def detect_registration_success(self, page_content: str) -> tuple[bool, str]:
        """
        Detect registration success using precise indicators.
        
        Args:
            page_content: HTML content of the page
            
        Returns:
            tuple: (success_detected: bool, detection_message: str)
        """
        # Precise success detection - based on login-after-registration features
        success_indicators = [
            "login-container",  # 登录成功后的容器ID
            "login-user-info",  # 用户信息区域
            "wan-logout-btn",   # 退出按钮类名 - 登录成功的关键标志
            "退出</a>",         # 退出按钮文本
            "user_info_avatar", # 用户头像链接类名
            "name-text"         # 用户名文本类名
        ]
        
        # Count matching success indicators
        success_features_found = sum(1 for indicator in success_indicators if indicator in page_content)
        if success_features_found >= 3:  # At least 3 success features must be present
            return True, f"Registration successful - login interface detected ({success_features_found} features)"
        
        # Check for explicit success messages
        explicit_success_indicators = [
            "注册成功",
            "登录成功", 
            "欢迎使用",
            "注册完成"
        ]
        
        for indicator in explicit_success_indicators:
            if indicator in page_content:
                return True, f"Registration successful (detected: {indicator})"
        
        return False, "No registration success detected"
    
    def check_captcha_completion(self, page_content: str) -> tuple[bool, str]:
        """
        Check if captcha has been completed using dual-condition validation.
        
        This is the core method that implements the AC requirement:
        "Only when captcha box disappears AND registration success flag appears"
        
        Args:
            page_content: HTML content of the page
            
        Returns:
            tuple: (completed: bool, result_message: str)
        """
        # Step 1: Check if captcha is still present
        captcha_detected, captcha_message = self.detect_captcha_in_content(page_content)
        
        if captcha_detected:
            return False, f"Captcha still present: {captcha_message}"
        
        # Step 2: Check if registration success is detected
        success_detected, success_message = self.detect_registration_success(page_content)
        
        if success_detected:
            # Dual condition met: captcha gone AND success detected
            return True, f"Captcha completed successfully: {success_message}"
        else:
            # Captcha gone but no success yet - intermediate state
            return False, "Captcha disappeared but registration not confirmed yet"
    
    def start_monitoring(self, account: Account, page: Page):
        """
        Start captcha monitoring for an account with 5-second polling.
        
        Args:
            account: Account waiting for captcha completion
            page: Playwright page instance
        """
        if not PYSIDE6_AVAILABLE:
            self._log_error("PySide6 not available - captcha monitoring disabled")
            return
        
        # Clean up any existing timer for this account
        self._cleanup_timer(account.id)
        
        # Mark account status
        account.status = AccountStatus.CAPTCHA_PENDING
        
        # Notify ViewModel through callback
        if self.on_captcha_detected:
            self.on_captcha_detected(account, "Started captcha monitoring")
        
        # Emit Qt signal if available
        if hasattr(self, 'captcha_detected'):
            self.captcha_detected.emit(account, "Started captcha monitoring")
        
        self._log_message(tr("🔍 Starting captcha monitoring for %1 - checking every 5 seconds").replace("%1", account.username))
        
        # Create and start QTimer for 5-second polling
        timer = QTimer()
        self.active_timers[account.id] = timer
        
        check_count = 0
        max_checks = self.timeout_duration // self.polling_interval  # 12 checks for 60 seconds
        
        def check_captcha_status():
            nonlocal check_count
            check_count += 1
            
            self._log_message(tr("🔍 Captcha check #{0} for {1}").format(check_count, account.username))
            
            # Check if account status changed (external update)
            if account.status != AccountStatus.CAPTCHA_PENDING:
                self._log_message(tr("✅ Account status changed - stopping monitoring for %1").replace("%1", account.username))
                self._cleanup_timer(account.id)
                return
            
            # Check timeout
            if check_count > max_checks:
                self._handle_timeout(account, timer)
                return
            
            # Perform the actual captcha completion check
            self._check_captcha_async(account, page, timer)
        
        # Connect timer and start
        timer.timeout.connect(check_captcha_status)
        timer.start(self.polling_interval * 1000)  # Convert to milliseconds
        
        self._log_message(tr("✅ Captcha monitoring started for %1 (polling every %2 seconds)").replace("%1", account.username).replace("%2", str(self.polling_interval)))
    
    def manual_check(self, account: Account, page: Page) -> bool:
        """
        Perform immediate captcha check (for manual detection button).
        
        Args:
            account: Account to check
            page: Playwright page instance
            
        Returns:
            bool: True if captcha completed, False otherwise
        """
        self._log_message(tr("🔍 Manual captcha check for %1").replace("%1", account.username))
        
        try:
            # Get page content synchronously
            page_content = asyncio.run(page.content())
            
            # Check captcha completion
            completed, message = self.check_captcha_completion(page_content)
            
            if completed:
                self._handle_success(account, message)
                return True
            else:
                self._log_message(tr("ℹ️ Manual check result: %1").replace("%1", message))
                return False
                
        except Exception as e:
            error_msg = f"Manual captcha check failed: {str(e)}"
            self._log_error(error_msg)
            return False
    
    def stop_monitoring(self, account_id: int):
        """Stop monitoring for specific account"""
        self._cleanup_timer(account_id)
    
    def stop_all_monitoring(self):
        """Stop all active monitoring"""
        for account_id in list(self.active_timers.keys()):
            self._cleanup_timer(account_id)
    
    def _check_captcha_async(self, account: Account, page: Page, timer: QTimer):
        """Perform async captcha check in background thread"""
        try:
            # Create new event loop for background operation
            def background_check():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Check if page is closed
                        if loop.run_until_complete(self._is_page_closed(page)):
                            self._handle_page_closed(account, timer)
                            return
                        
                        # Get page content
                        page_content = loop.run_until_complete(page.content())
                        
                        # Check captcha completion
                        completed, message = self.check_captcha_completion(page_content)
                        
                        if completed:
                            self._handle_success(account, message, timer)
                        else:
                            # Continue monitoring
                            self._log_message(tr("⏳ Still waiting for captcha completion: %1").replace("%1", message))
                    
                    finally:
                        loop.close()
                        
                except Exception as e:
                    self._log_error(f"Background captcha check error: {str(e)}")
            
            # Run background check in separate thread
            import threading
            thread = threading.Thread(target=background_check, daemon=True)
            thread.start()
            
        except Exception as e:
            self._log_error(f"Failed to start background captcha check: {str(e)}")
    
    async def _is_page_closed(self, page: Page) -> bool:
        """Check if page is closed"""
        try:
            return page.is_closed()
        except Exception:
            return True
    
    def _handle_success(self, account: Account, message: str, timer: QTimer = None):
        """Handle successful captcha completion"""
        account.mark_success(f"Captcha completed: {message}")
        
        if timer:
            self._cleanup_timer_instance(timer)
        else:
            self._cleanup_timer(account.id)
        
        # Notify ViewModel through callback
        if self.on_captcha_resolved:
            self.on_captcha_resolved(account, message)
        
        # Emit Qt signal if available
        if hasattr(self, 'captcha_resolved'):
            self.captcha_resolved.emit(account, message)
        
        self._log_message(tr("🎉 SUCCESS: %1 - Captcha completed!").replace("%1", account.username))
    
    def _handle_timeout(self, account: Account, timer: QTimer):
        """Handle captcha monitoring timeout"""
        timeout_message = f"Captcha timeout after {self.timeout_duration} seconds"
        account.mark_failed(timeout_message)
        
        self._cleanup_timer_instance(timer)
        
        # Notify ViewModel through callback
        if self.on_captcha_timeout:
            self.on_captcha_timeout(account, timeout_message)
        
        # Emit Qt signal if available
        if hasattr(self, 'captcha_timeout'):
            self.captcha_timeout.emit(account, timeout_message)
        
        self._log_message(tr("⏰ TIMEOUT: Captcha not resolved for %1 after %2 seconds").replace("%1", account.username).replace("%2", str(self.timeout_duration)))
    
    def _handle_page_closed(self, account: Account, timer: QTimer):
        """Handle page closed during monitoring"""
        error_message = "Browser closed during captcha monitoring"
        account.mark_failed(error_message)
        
        self._cleanup_timer_instance(timer)
        
        self._log_message(tr("🚪 Browser closed for %1 - stopping monitoring").replace("%1", account.username))
    
    def _cleanup_timer(self, account_id: int):
        """Clean up timer for specific account"""
        if account_id in self.active_timers:
            timer = self.active_timers[account_id]
            self._cleanup_timer_instance(timer)
            del self.active_timers[account_id]
    
    def _cleanup_timer_instance(self, timer: QTimer):
        """Clean up specific timer instance"""
        try:
            if timer.isActive():
                timer.stop()
            timer.deleteLater()
        except Exception as e:
            self._log_error(f"Timer cleanup error: {str(e)}")
    
    def _log_message(self, message: str):
        """Log message through callback and logger"""
        self.logger.info(message)
        if self.on_log_message:
            self.on_log_message(message)
    
    def _log_error(self, error: str):
        """Log error through callback and logger"""
        self.logger.error(error)
        if self.on_log_message:
            self.on_log_message(tr("ERROR: %1").replace("%1", error))