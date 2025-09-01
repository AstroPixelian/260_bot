"""
Automation service for batch account registration
"""

import random
import asyncio
import time
import logging
from typing import Callable, Optional, Literal
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, PlaywrightContextManager, ViewportSize
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from ..models.account import Account, AccountStatus
from ..translation_manager import tr
from ..exceptions import (
    AutomationError, BrowserInitializationError, ElementNotFoundError,
    PageNavigationError, FormInteractionError, RegistrationFailureError,
    TimeoutError, NetworkError, CaptchaRequiredError, AccountAlreadyExistsError,
    InvalidCredentialsError, RateLimitError
)

# Import undetected_chromedriver and related dependencies
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


# Type alias for automation backend
AutomationBackend = Literal["playwright", "selenium"]


class AutomationService:
    """Service for automated account registration with multiple backend support"""
    
    def __init__(self, backend: AutomationBackend = "playwright"):
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        self.success_rate = 0.8  # 80% success rate for simulation
        
        # Backend selection
        self.backend = backend
        
        # 定时器管理 - 保存活跃的验证码监控定时器
        self.captcha_timers = {}  # {account_id: QTimer}
        
        # Error logging setup
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.error_log = []  # Store errors for debugging
        
        # Validate backend availability
        if backend == "selenium" and not SELENIUM_AVAILABLE:
            raise BrowserInitializationError(
                "Selenium backend requested but undetected_chromedriver is not available. "
                "Install it with: pip install undetected-chromedriver",
                backend="selenium",
                details={"selenium_available": SELENIUM_AVAILABLE}
            )
        
        # Playwright browser management
        self.playwright: Optional[PlaywrightContextManager] = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None
        
        # Selenium/undetected_chromedriver management
        self.selenium_driver: Optional[object] = None
        
        # Callback functions for UI updates
        self.on_account_start: Optional[Callable[[Account], None]] = None
        self.on_account_complete: Optional[Callable[[Account], None]] = None
        self.on_batch_complete: Optional[Callable[[int, int], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None
    
    def set_callbacks(self, 
                     on_account_start: Callable[[Account], None] = None,
                     on_account_complete: Callable[[Account], None] = None,
                     on_batch_complete: Callable[[int, int], None] = None,
                     on_log_message: Callable[[str], None] = None):
        """Set callback functions for UI updates"""
        self.on_account_start = on_account_start
        self.on_account_complete = on_account_complete
        self.on_batch_complete = on_batch_complete
        self.on_log_message = on_log_message
    
    def _log_error(self, error: Exception, context: str = "", account: Optional[Account] = None) -> None:
        """Log error with context for debugging"""
        error_entry = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "account_username": account.username if account else None,
            "backend": self.backend
        }
        
        # Add additional details for custom exceptions
        if isinstance(error, AutomationError):
            error_entry["error_code"] = error.error_code
            error_entry["error_details"] = error.details
        
        self.error_log.append(error_entry)
        self.logger.error(f"[{context}] {error}", exc_info=True)
        
        # Also send to UI if callback available
        if self.on_log_message:
            self.on_log_message(tr("ERROR: %1").replace("%1", str(error)))
    
    def _log_warning(self, message: str, context: str = "") -> None:
        """Log warning message"""
        self.logger.warning(f"[{context}] {message}")
        if self.on_log_message:
            self.on_log_message(tr("WARNING: %1").replace("%1", message))
    
    def _log_debug(self, message: str, context: str = "") -> None:
        """Log debug message"""
        self.logger.debug(f"[{context}] {message}")
        if self.on_log_message:
            self.on_log_message(tr("DEBUG: [%1] %2").replace("%1", context).replace("%2", message))
    
    def get_error_log(self) -> list[dict]:
        """Get the error log for debugging"""
        return self.error_log.copy()
    
    def clear_error_log(self) -> None:
        """Clear the error log"""
        self.error_log.clear()
    
    async def _safe_navigate(self, page: Page, url: str, max_retries: int = 3, timeout: int = 30) -> None:
        """Navigate to URL with retry logic and proper error handling"""
        context = "navigation"
        
        for attempt in range(max_retries):
            try:
                self._log_debug(f"Navigation attempt {attempt + 1}/{max_retries} to {url}", context)
                
                # 使用更宽松的等待策略，优先使用 domcontentloaded
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
                    self._log_debug(f"Successfully navigated to {url} (domcontentloaded)", context)
                    
                    # 额外等待一下让页面稳定
                    await asyncio.sleep(2)
                    return
                except PlaywrightTimeoutError:
                    # 如果 domcontentloaded 也超时，尝试 load
                    self._log_debug(f"domcontentloaded timeout, trying load strategy", context)
                    await page.goto(url, wait_until='load', timeout=(timeout - 5) * 1000)
                    self._log_debug(f"Successfully navigated to {url} (load)", context)
                    return
                
            except PlaywrightTimeoutError as e:
                if attempt < max_retries - 1:
                    self._log_warning(f"Navigation timeout (attempt {attempt + 1}), retrying...", context)
                    await asyncio.sleep(2)
                    continue
                else:
                    raise PageNavigationError(url, max_retries, f"Timeout after {timeout}s")
            except PlaywrightError as e:
                if attempt < max_retries - 1:
                    self._log_warning(f"Navigation error (attempt {attempt + 1}): {str(e)}, retrying...", context)
                    await asyncio.sleep(2)
                    continue
                else:
                    raise PageNavigationError(url, max_retries, str(e))
        
        # Should never reach here, but just in case
        raise PageNavigationError(url, max_retries, "Unknown navigation failure")
    
    async def _safe_wait_for_element(self, page: Page, selectors: list[str], element_type: str, timeout: int = 10) -> tuple[object, str]:
        """Wait for element with multiple selectors, return element and successful selector"""
        context = f"wait_for_{element_type}"
        
        for selector in selectors:
            try:
                self._log_debug(f"Trying {element_type} selector: {selector}", context)
                
                # Wait for element to be present
                await page.wait_for_selector(selector, timeout=timeout * 1000)
                
                # Get all matching elements
                elements = await page.locator(selector).all()
                
                # Find first visible element
                for element in elements:
                    if await element.is_visible():
                        self._log_debug(f"Found visible {element_type} with selector: {selector}", context)
                        return element, selector
                
                self._log_debug(f"Selector {selector} found elements but none visible", context)
                
            except PlaywrightTimeoutError:
                self._log_debug(f"Timeout waiting for {element_type} selector: {selector}", context)
                continue
            except Exception as e:
                self._log_debug(f"Error with selector {selector}: {str(e)}", context)
                continue
        
        # No selector worked
        raise ElementNotFoundError(
            selector=" or ".join(selectors),
            element_type=element_type,
            timeout=timeout
        )
    
    async def _safe_click_element(self, page: Page, selectors: list[str], element_type: str, timeout: int = 10) -> str:
        """Safely click element with multiple selector fallbacks"""
        element, successful_selector = await self._safe_wait_for_element(page, selectors, element_type, timeout)
        
        try:
            await element.click()
            self._log_debug(f"Successfully clicked {element_type}", f"click_{element_type}")
            return successful_selector
        except Exception as e:
            raise FormInteractionError("click", element_type, {"selector": successful_selector, "error": str(e)})
    
    async def _safe_fill_element(self, page: Page, selectors: list[str], value: str, element_type: str, timeout: int = 10) -> str:
        """Safely fill element with multiple selector fallbacks"""
        element, successful_selector = await self._safe_wait_for_element(page, selectors, element_type, timeout)
        
        try:
            await element.fill(value)
            self._log_debug(f"Successfully filled {element_type} with value", f"fill_{element_type}")
            return successful_selector
        except Exception as e:
            raise FormInteractionError("fill", element_type, {
                "selector": successful_selector, 
                "error": str(e), 
                "value_length": len(value)
            })
    
    def _detect_registration_result(self, page_content: str, account: Account) -> tuple[bool, str]:
        """Detect registration result from page content with precise captcha detection"""
        context = "result_detection"
        
        # 精确的验证码检测 - 基于实际HTML特征，避免误检测
        captcha_indicators = [
            "quc-slide-con",  # 验证码滑块外层容器 - 高度特异性
            "quc-captcha-mask",  # 验证码遮罩层 - 360独有
            "请完成下方拼图验证后继续",  # 验证码具体提示文本
            "quc-body-tip",  # 验证码提示样式类
            "verify-slide-con verify-con",  # 滑动验证码双重类名
            "slide-block",  # 滑动块图片 - 结合其他条件
            "拖动滑块完成拼图"  # 滑动操作指令文本
        ]
        
        # 检测验证码 - 只要检测到一个高特异性指标即可确认
        high_specificity_indicators = [
            "quc-slide-con",
            "quc-captcha-mask", 
            "请完成下方拼图验证后继续"
        ]
        
        for indicator in high_specificity_indicators:
            if indicator in page_content:
                self._log_debug(f"Detected captcha with high specificity: {indicator}", context)
                return False, f"CAPTCHA_DETECTED: {indicator}"
        
        # 辅助验证码检测 - 需要多个条件同时满足
        auxiliary_indicators = ["verify-slide-con", "拖动滑块完成拼图"]
        if all(indicator in page_content for indicator in auxiliary_indicators):
            self._log_debug("Detected captcha with auxiliary indicators", context)
            return False, "CAPTCHA_DETECTED: slide verification interface"
        
        # 精确的成功登录检测 - 基于登录后的HTML特征
        success_indicators = [
            "login-container",  # 登录成功后的容器ID
            "login-user-info",  # 用户信息区域
            "wan-logout-btn",   # 退出按钮类名 - 登录成功的关键标志
            "退出</a>",         # 退出按钮文本
            "user_info_avatar", # 用户头像链接类名
            "name-text"         # 用户名文本类名
        ]
        
        # 检测成功登录 - 需要多个登录特征同时存在
        login_features_found = sum(1 for indicator in success_indicators if indicator in page_content)
        if login_features_found >= 3:  # 至少3个登录特征同时存在
            self._log_debug(f"Detected successful login with {login_features_found} features", context)
            return True, f"Registration successful - login interface detected ({login_features_found} features)"
        
        # Check for already registered messages
        already_registered_messages = [
            "该账号已经注册",
            "账号已存在", 
            "用户名已存在",
            "已注册",
            "用户名已被占用",
            "用户名重复"
        ]
        
        for message in already_registered_messages:
            if message in page_content:
                self._log_debug(f"Detected already registered: {message}", context)
                raise AccountAlreadyExistsError(account.username, message)
        
        # Check for explicit success messages
        explicit_success_indicators = [
            "注册成功",
            "登录成功", 
            "欢迎使用",
            "注册完成"
        ]
        
        for indicator in explicit_success_indicators:
            if indicator in page_content:
                self._log_debug(f"Detected explicit success indicator: {indicator}", context)
                return True, f"Registration successful (detected: {indicator})"
        
        # Check for error messages
        error_messages = [
            "注册失败",
            "用户名格式不正确",
            "密码格式不正确", 
            "验证码错误",
            "网络错误",
            "系统繁忙",
            "请输入验证码",
            "验证码不能为空"
        ]
        
        for message in error_messages:
            if message in page_content:
                self._log_debug(f"Detected error message: {message}", context)
                if "验证码" in message:
                    raise CaptchaRequiredError("text_captcha")
                else:
                    raise RegistrationFailureError(message, "validation_error")
        
        # No clear result detected
        return False, "Registration result unclear"
    
    async def _check_page_closed(self, page):
        """检查页面是否已关闭"""
        try:
            return page.is_closed()
        except Exception:
            return True  # 如果无法检查，假设已关闭

    def start_batch_registration(self, accounts: list[Account]) -> bool:
        """
        Start batch registration process
        
        Args:
            accounts: List of accounts to register
            
        Returns:
            True if started successfully, False if already running
        """
        if self.is_running:
            return False
        
        self.is_running = True
        self.is_paused = False
        
        # Check if this is a fresh start or resuming
        # If all accounts are QUEUED, this is a fresh start
        all_queued = all(account.status == AccountStatus.QUEUED for account in accounts)
        
        if all_queued:
            # Fresh start - reset index and keep all accounts queued
            self.current_account_index = 0
            if self.on_log_message:
                self.on_log_message(tr("Started fresh batch processing for %1 accounts").replace("%1", str(len(accounts))))
        else:
            # Resuming - find first account that needs processing (QUEUED status)
            self.current_account_index = 0
            for i, account in enumerate(accounts):
                if account.status == AccountStatus.QUEUED:
                    self.current_account_index = i
                    break
            else:
                # No queued accounts found, find first non-success account
                for i, account in enumerate(accounts):
                    if account.status not in [AccountStatus.SUCCESS]:
                        self.current_account_index = i
                        # Reset this account to queued if it was processing/failed
                        if account.status in [AccountStatus.PROCESSING, AccountStatus.FAILED]:
                            account.reset_status()
                        break
                else:
                    # All accounts are successful, nothing to do
                    self.is_running = False
                    if self.on_log_message:
                        self.on_log_message(tr("All accounts already processed successfully"))
                    return False
            
            if self.on_log_message:
                self.on_log_message(tr("Resuming batch processing from account %1").replace("%1", str(self.current_account_index + 1)))
        
        return True
    
    def pause_registration(self) -> bool:
        """
        Pause the registration process
        
        Returns:
            True if paused, False if not running
        """
        if not self.is_running:
            return False
        
        self.is_paused = not self.is_paused
        
        if self.on_log_message:
            if self.is_paused:
                self.on_log_message(tr("Processing paused"))
            else:
                self.on_log_message(tr("Processing resumed"))
        
        return True
    
    def stop_registration(self, accounts: list[Account]) -> bool:
        """
        Stop the registration process
        
        Args:
            accounts: List of accounts to reset
            
        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            return False
        
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        
        # 停止所有验证码监控定时器
        self._cleanup_captcha_timers()
        
        # Reset any processing accounts to queued
        for account in accounts:
            if account.status == AccountStatus.PROCESSING:
                account.reset_status()
        
        # Clean up browser resources based on backend with proper error handling
        try:
            if self.backend == "playwright":
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If in an event loop, schedule cleanup
                        asyncio.create_task(self._cleanup_browser())
                    else:
                        # If not in an event loop, run cleanup synchronously
                        asyncio.run(self._cleanup_browser())
                except Exception as e:
                    self._log_warning(f"Browser cleanup failed: {str(e)}", "stop_registration")
            else:
                # For selenium backend, use synchronous cleanup
                try:
                    self._cleanup_selenium_driver()
                except Exception as e:
                    self._log_warning(f"Selenium cleanup failed: {str(e)}", "stop_registration")
        except Exception as e:
            self._log_error(AutomationError(f"Cleanup error: {str(e)}"), "stop_registration")
        
        if self.on_log_message:
            self.on_log_message(tr("Processing stopped"))
        
        return True
    
    def process_next_account(self, accounts: list[Account]) -> bool:
        """
        Process the next account in the queue
        
        Args:
            accounts: List of accounts to process
            
        Returns:
            True if there are more accounts to process, False if batch is complete
        """
        if not self.is_running or self.is_paused:
            return True
        
        if self.current_account_index >= len(accounts):
            # Batch processing complete
            self._complete_batch_processing(accounts)
            return False
        
        # Get current account
        account = accounts[self.current_account_index]
        
        # Mark account as processing
        account.mark_processing()
        
        if self.on_account_start:
            self.on_account_start(account)
        
        if self.on_log_message:
            self.on_log_message(tr("Processing account: %1").replace("%1", account.username))
        
        # Use the appropriate registration method based on backend
        if self.backend == "selenium":
            self._register_with_selenium(account)
        else:
            # For playwright or other backends, use the existing approach
            self._simulate_registration(account)
        
        return True
    
    def complete_current_account(self, accounts: list[Account]):
        """Complete processing of current account"""
        if self.current_account_index >= len(accounts):
            return
        
        account = accounts[self.current_account_index]
        
        # Simulate registration result
        if random.random() < self.success_rate:
            account.mark_success()
            if self.on_log_message:
                self.on_log_message(tr("SUCCESS: %1 registered successfully").replace("%1", account.username))
        else:
            # Simulate random failure reasons
            failure_reasons = [
                tr("Username already taken"),
                tr("Invalid email format"),
                tr("Network timeout"),
                tr("Captcha required"),
                tr("Rate limit exceeded")
            ]
            reason = random.choice(failure_reasons)
            account.mark_failed(reason)
            if self.on_log_message:
                self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", reason))
        
        if self.on_account_complete:
            self.on_account_complete(account)
        
        self.current_account_index += 1
    
    def _simulate_registration(self, account: Account):
        """Simulate the registration process"""
        # In a real implementation, this would use Playwright to:
        # 1. Open the registration page
        # 2. Fill in the form with account details
        # 3. Submit the form
        # 4. Handle captchas or other challenges
        # 5. Check for success/failure
        pass
    
    def _start_captcha_monitoring(self, account: Account, page):
        """启动验证码监控定时器"""
        try:
            from PySide6.QtCore import QTimer
            import threading
            
            if self.on_log_message:
                self.on_log_message(tr("🔧 Starting captcha monitoring for {0}").format(account.username))
                self.on_log_message(tr("🧵 Current thread: {0}").format(threading.current_thread().name))
            
            def create_timer():
                """在主线程中创建QTimer"""
                # 停止该账号的任何已存在的定时器
                if account.id in self.captcha_timers:
                    old_timer = self.captcha_timers[account.id]
                    if old_timer and old_timer.isActive():
                        old_timer.stop()
                        if self.on_log_message:
                            self.on_log_message(tr("🔧 Stopped existing timer for {0}").format(account.username))
                
                # 创建新的定时器
                timer = QTimer()
                self.captcha_timers[account.id] = timer
                
                check_count = [0]
                max_checks = 120  # 10分钟 (120 * 5秒)
                
                def check_captcha():
                    """定时检查函数 - 简化版本"""
                    try:
                        check_count[0] += 1
                        
                        if self.on_log_message:
                            self.on_log_message(tr("🔍 Captcha check #{0} for {1}").format(check_count[0], account.username))
                        
                        # 检查账号状态是否已改变
                        if account.status != AccountStatus.WAITING_CAPTCHA:
                            if self.on_log_message:
                                self.on_log_message(tr("✅ Account status changed to {0}, stopping timer").format(account.status.value))
                            timer.stop()
                            if account.id in self.captcha_timers:
                                del self.captcha_timers[account.id]
                            return
                        
                        # 检查是否超时
                        if check_count[0] > max_checks:
                            if self.on_log_message:
                                self.on_log_message(tr("⏰ Captcha monitoring timeout for {0}").format(account.username))
                            timer.stop()
                            if account.id in self.captcha_timers:
                                del self.captcha_timers[account.id]
                            account.mark_failed("Captcha resolution timeout (10 minutes)")
                            if self.on_account_complete:
                                self.on_account_complete(account)
                            return
                        
                        # 异步检查页面状态
                        def check_page_in_background():
                            """在后台线程中检查页面"""
                            try:
                                # 创建新的异步事件循环
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                try:
                                    # 检查页面是否关闭
                                    is_closed = loop.run_until_complete(self._check_page_closed(page))
                                    if is_closed:
                                        if self.on_log_message:
                                            self.on_log_message(tr("🚪 Browser closed for {0}").format(account.username))
                                        account.mark_failed("Browser closed during captcha")
                                        if self.on_account_complete:
                                            self.on_account_complete(account)
                                        # 在主线程中停止定时器
                                        from PySide6.QtCore import QMetaObject, Qt
                                        QMetaObject.invokeMethod(timer, "stop", Qt.QueuedConnection)
                                        return
                                    
                                    # 获取页面内容
                                    content = loop.run_until_complete(page.content())
                                    if not content:
                                        if self.on_log_message:
                                            self.on_log_message(tr("❌ Failed to get page content, will retry next time"))
                                        return
                                    
                                    # 检测注册结果
                                    success, result_message = self._detect_registration_result(content, account)
                                    
                                    if self.on_log_message:
                                        self.on_log_message(tr("🔍 Detection result: success={0}, message={1}").format(success, result_message[:100]))
                                    
                                    if success:
                                        # 注册成功
                                        account.mark_success("Captcha completed successfully")
                                        if self.on_account_complete:
                                            self.on_account_complete(account)
                                        if self.on_log_message:
                                            self.on_log_message(tr("🎉 SUCCESS: {0} - Captcha completed!").format(account.username))
                                        # 在主线程中停止定时器
                                        from PySide6.QtCore import QMetaObject, Qt
                                        QMetaObject.invokeMethod(timer, "stop", Qt.QueuedConnection)
                                        return
                                    else:
                                        if self.on_log_message:
                                            self.on_log_message(tr("⏳ Captcha still present, will check again in 5 seconds"))
                                
                                finally:
                                    loop.close()
                                    
                            except Exception as e:
                                if self.on_log_message:
                                    self.on_log_message(tr("❌ Error during background captcha check: {0}").format(str(e)))
                                # 不停止定时器，继续下次检查
                        
                        # 启动后台检查线程
                        import threading
                        check_thread = threading.Thread(target=check_page_in_background, daemon=True)
                        check_thread.start()
                        
                    except Exception as e:
                        if self.on_log_message:
                            self.on_log_message(tr("❌ Error in timer callback: {0}").format(str(e)))
                
                # 设置定时器
                timer.timeout.connect(check_captcha)
                timer.start(5000)  # 5秒间隔
                
                if self.on_log_message:
                    self.on_log_message(tr("✅ Captcha monitoring started for {0} (Timer ID: {1})").format(account.username, id(timer)))
                    self.on_log_message(tr("🔧 Timer active: {0}, interval: {1}ms").format(timer.isActive(), timer.interval()))
            
            # 使用QTimer.singleShot确保在主线程中创建定时器
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, create_timer)
            
        except ImportError:
            if self.on_log_message:
                self.on_log_message(tr("❌ PySide6 not available, captcha monitoring disabled"))
        except Exception as e:
            if self.on_log_message:
                self.on_log_message(tr("❌ Failed to start captcha monitoring: {0}").format(str(e)))
    
    def _cleanup_captcha_timers(self):
        """清理所有验证码监控定时器"""
        if not hasattr(self, 'captcha_timers'):
            return
            
        try:
            if self.on_log_message:
                self.on_log_message(tr("🧹 Cleaning up {0} captcha timers").format(len(self.captcha_timers)))
            
            for account_id, timer in list(self.captcha_timers.items()):
                if timer and timer.isActive():
                    timer.stop()
                    if self.on_log_message:
                        self.on_log_message(tr("🔧 Stopped timer for account {0}").format(account_id))
            
            self.captcha_timers.clear()
            
            if self.on_log_message:
                self.on_log_message(tr("✅ All captcha timers cleaned up"))
                
        except Exception as e:
            if self.on_log_message:
                self.on_log_message(tr("❌ Error cleaning up timers: {0}").format(str(e)))
    
    async def check_waiting_captcha_accounts(self, accounts: list[Account]) -> bool:
        """
        检查等待验证码的账号，看是否有已经完成验证码的账号
        
        Args:
            accounts: 账号列表
            
        Returns:
            True if any account status changed, False otherwise
        """
        if not accounts:
            return False
            
        status_changed = False
        
        # 找到所有等待验证码的账号
        waiting_accounts = [acc for acc in accounts if acc.status == AccountStatus.WAITING_CAPTCHA]
        
        if not waiting_accounts:
            return False
            
        self._log_debug(f"Checking {len(waiting_accounts)} accounts waiting for captcha resolution")
        
        # 检查每个等待验证码的账号
        for account in waiting_accounts:
            try:
                # 如果该账号有浏览器实例，检查其状态
                # 注意：这里需要访问保留的浏览器实例
                # 由于当前架构，我们需要重新连接到可能存在的浏览器窗口
                
                # 暂时使用简化检测：检查是否有打开的浏览器窗口
                # 在实际实现中，这里需要维护账号与浏览器实例的映射
                
                if self.on_log_message:
                    self.on_log_message(tr("Checking captcha status for account: %1").replace("%1", account.username))
                
                # TODO: 实现实际的状态检测逻辑
                # 这里需要连接到该账号对应的浏览器实例并检查页面状态
                
                status_changed = True
                
            except Exception as e:
                self._log_debug(f"Error checking captcha account {account.username}: {str(e)}")
                continue
                
        return status_changed
    
    async def _monitor_captcha_account(self, account: Account, page) -> None:
        """
        异步监控验证码账号，检测用户是否已完成验证码
        不阻塞批量处理流程，保证GUI响应性
        
        Args:
            account: 等待验证码的账号
            page: Playwright页面实例
        """
        context = f"captcha_monitor_{account.username}"
        self._log_debug(f"Starting captcha monitoring for {account.username}", context)
        
        if self.on_log_message:
            self.on_log_message(tr("🔍 Starting captcha monitoring for %1 - checking every 5 seconds").replace("%1", account.username))
        
        max_checks = 120  # 最多检查120次（10分钟）
        check_interval = 5  # 每5秒检查一次
        
        try:
            for check_count in range(max_checks):
                # 等待5秒
                await asyncio.sleep(check_interval)
                
                # 添加调试信息
                if self.on_log_message:
                    self.on_log_message(tr("🔍 Captcha check #%1 for %2").replace("%1", str(check_count + 1)).replace("%2", account.username))
                
                # 如果账号状态已经不是WAITING_CAPTCHA，说明已经被其他地方更新了
                if account.status != AccountStatus.WAITING_CAPTCHA:
                    self._log_debug(f"Account {account.username} status changed to {account.status.value}, stopping monitor", context)
                    if self.on_log_message:
                        self.on_log_message(tr("✅ Monitor stopped for %1 - status changed to %2").replace("%1", account.username).replace("%2", account.status.value))
                    return
                
                try:
                    # 检查页面状态
                    if self.on_log_message:
                        self.on_log_message(tr("🔍 Checking page content for %1").replace("%1", account.username))
                    
                    current_content = await page.content()
                    success, current_message = self._detect_registration_result(current_content, account)
                    
                    if self.on_log_message:
                        self.on_log_message(tr("🔍 Detection result for %1: success=%2, message=%3").replace("%1", account.username).replace("%2", str(success)).replace("%3", current_message[:100]))
                    
                    if success:
                        # 注册成功！
                        if self.on_log_message:
                            self.on_log_message(tr("🎉 SUCCESS DETECTED: %1 - Registration completed!").replace("%1", account.username))
                        
                        account.mark_success("Manual captcha resolution successful")
                        if self.on_account_complete:
                            self.on_account_complete(account)
                        if self.on_log_message:
                            self.on_log_message(tr("✅ SUCCESS: %1 - Captcha resolved successfully!").replace("%1", account.username))
                        
                        # 关闭浏览器
                        try:
                            if self.on_log_message:
                                self.on_log_message(tr("🔧 Closing browser for %1 after success").replace("%1", account.username))
                            await page.close()
                            if hasattr(self, 'browser_context') and self.browser_context:
                                await self.browser_context.close()
                            if hasattr(self, 'browser') and self.browser:
                                await self.browser.close()
                            if self.on_log_message:
                                self.on_log_message(tr("✅ Browser closed for %1").replace("%1", account.username))
                        except Exception as browser_error:
                            if self.on_log_message:
                                self.on_log_message(tr("⚠️ Browser close error for %1: %2").replace("%1", account.username).replace("%2", str(browser_error)))
                        
                        return
                        
                    elif "CAPTCHA_DETECTED" not in current_message:
                        # 验证码消失，检查是否成功
                        if self.on_log_message:
                            self.on_log_message(tr("🔍 Captcha cleared for %1 - verifying success").replace("%1", account.username))
                        
                        await asyncio.sleep(2)  # 等待页面稳定
                        stable_content = await page.content()
                        stable_success, stable_message = self._detect_registration_result(stable_content, account)
                        
                        if self.on_log_message:
                            self.on_log_message(tr("🔍 Stable check for %1: success=%2, message=%3").replace("%1", account.username).replace("%2", str(stable_success)).replace("%3", stable_message[:100]))
                        
                        if stable_success:
                            # 成功！
                            if self.on_log_message:
                                self.on_log_message(tr("🎉 SUCCESS CONFIRMED: %1 - Registration verified!").replace("%1", account.username))
                                
                            account.mark_success("Manual captcha resolution - success confirmed")
                            if self.on_account_complete:
                                self.on_account_complete(account)
                            if self.on_log_message:
                                self.on_log_message(tr("✅ SUCCESS: %1 - Registration confirmed after captcha").replace("%1", account.username))
                            
                            # 关闭浏览器
                            try:
                                if self.on_log_message:
                                    self.on_log_message(tr("🔧 Closing browser for %1 after confirmed success").replace("%1", account.username))
                                await page.close()
                                if hasattr(self, 'browser_context') and self.browser_context:
                                    await self.browser_context.close()
                                if hasattr(self, 'browser') and self.browser:
                                    await self.browser.close()
                                if self.on_log_message:
                                    self.on_log_message(tr("✅ Browser closed for %1").replace("%1", account.username))
                            except Exception as browser_error:
                                if self.on_log_message:
                                    self.on_log_message(tr("⚠️ Browser close error for %1: %2").replace("%1", account.username).replace("%2", str(browser_error)))
                            
                            return
                        
                        # 验证码消失但未检测到成功，继续等待
                        if self.on_log_message:
                            self.on_log_message(tr("⏳ Captcha cleared but success not confirmed for %1 - continuing check").replace("%1", account.username))
                    else:
                        # 验证码仍然存在
                        if self.on_log_message:
                            self.on_log_message(tr("⏳ Captcha still present for %1 - user needs to complete it").replace("%1", account.username))
                    
                    # 每30秒提示一次
                    if check_count % 6 == 0 and check_count > 0:
                        remaining_time = (max_checks - check_count) * check_interval
                        if self.on_log_message:
                            self.on_log_message(tr("⏰ Still monitoring %1 for captcha resolution... %2 seconds remaining").replace("%1", account.username).replace("%2", str(remaining_time)))
                    
                except Exception as check_error:
                    self._log_debug(f"Error during captcha monitoring for {account.username}: {str(check_error)}", context)
                    if self.on_log_message:
                        self.on_log_message(tr("❌ Error checking %1: %2").replace("%1", account.username).replace("%2", str(check_error)))
                    continue
            
            # 超时，标记为失败
            if self.on_log_message:
                self.on_log_message(tr("⏰ TIMEOUT: Captcha monitoring timeout for %1").replace("%1", account.username))
            account.mark_failed("Captcha monitoring timeout - user did not complete verification")
            if self.on_account_complete:
                self.on_account_complete(account)
            if self.on_log_message:
                self.on_log_message(tr("⏰ TIMEOUT: Captcha not resolved for %1 after 10 minutes").replace("%1", account.username))
                
        except Exception as e:
            self._log_debug(f"Error in captcha monitoring for {account.username}: {str(e)}", context)
            if self.on_log_message:
                self.on_log_message(tr("❌ Captcha monitoring error for %1: %2").replace("%1", account.username).replace("%2", str(e)))
            account.mark_failed(f"Captcha monitoring error: {str(e)}")
            if self.on_account_complete:
                self.on_account_complete(account)
        
        finally:
            self._log_debug(f"Captcha monitoring completed for {account.username}", context)
            if self.on_log_message:
                self.on_log_message(tr("🏁 Captcha monitoring finished for %1").replace("%1", account.username))
    
    def _complete_batch_processing(self, accounts: list[Account]):
        """Complete the batch processing"""
        self.is_running = False
        self.is_paused = False
        
        # Calculate statistics
        success_count = len([acc for acc in accounts if acc.status == AccountStatus.SUCCESS])
        failed_count = len([acc for acc in accounts if acc.status == AccountStatus.FAILED])
        
        if self.on_log_message:
            self.on_log_message(tr("Batch processing completed!"))
        
        if self.on_batch_complete:
            self.on_batch_complete(success_count, failed_count)
    
    def get_progress_info(self, accounts: list[Account]) -> dict:
        """Get current progress information"""
        total = len(accounts)
        completed = self.current_account_index
        
        if total == 0:
            return {
                'total': 0,
                'completed': 0,
                'progress_percent': 0,
                'is_running': self.is_running,
                'is_paused': self.is_paused
            }
        
        return {
            'total': total,
            'completed': completed,
            'progress_percent': int(completed * 100 / total),
            'is_running': self.is_running,
            'is_paused': self.is_paused
        }
    
    def set_success_rate(self, rate: float):
        """Set the success rate for simulation (0.0 to 1.0)"""
        if 0.0 <= rate <= 1.0:
            self.success_rate = rate
    
    async def _initialize_browser(self) -> bool:
        """Initialize Playwright browser and context with comprehensive error handling"""
        context = "browser_initialization"
        
        try:
            self._log_debug("Starting browser initialization", context)
            
            # Initialize Playwright
            if not self.playwright:
                try:
                    self._log_debug("Starting Playwright instance", context)
                    self.playwright = await async_playwright().start()
                    self._log_debug("Playwright instance started successfully", context)
                except Exception as e:
                    raise BrowserInitializationError(
                        f"Failed to start Playwright: {str(e)}",
                        backend="playwright",
                        details={"step": "playwright_start"}
                    )
            
            # Launch browser
            if not self.browser:
                try:
                    self._log_debug("Launching Chromium browser", context)
                    self.browser = await self.playwright.chromium.launch(
                        headless=False,  # Set to False for debugging
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-dev-shm-usage',
                            '--disable-extensions',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--no-sandbox',
                            '--disable-ipc-flooding-protection',
                            '--disable-hang-monitor',
                            '--disable-prompt-on-repost',
                            '--disable-sync',
                            '--force-color-profile=srgb',
                            '--metrics-recording-only',
                            '--use-mock-keychain',
                            '--disable-background-networking',
                            # 网络优化参数
                            '--aggressive-cache-discard',
                            '--disable-background-downloads',
                            '--disable-component-extensions-with-background-pages',
                            '--disable-default-apps',
                            '--disable-popup-blocking',
                            '--disable-translate',
                            '--disable-backing-store-limit',
                            '--disable-blink-features=BlockCredentialedSubresources'
                        ],
                        slow_mo=100,  # 减少延迟提高速度
                        timeout=60000  # 60秒浏览器启动超时
                    )
                    self._log_debug("Chromium browser launched successfully", context)
                except PlaywrightTimeoutError as e:
                    raise TimeoutError("browser_launch", 90, {"step": "browser_launch", "original_error": str(e)})
                except PlaywrightError as e:
                    raise BrowserInitializationError(
                        f"Failed to launch Chromium browser: {str(e)}",
                        backend="playwright",
                        details={"step": "browser_launch", "args_count": 23}
                    )
            
            # Create browser context
            if not self.browser_context:
                try:
                    self._log_debug("Creating browser context", context)
                    self.browser_context = await self.browser.new_context(
                        viewport=ViewportSize({'width': 1280, 'height': 720}),
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    
                    # 暂时移除图片阻止，以便验证码图片能正常显示
                    # await self.browser_context.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                    # 也阻止视频和音频文件
                    await self.browser_context.route("**/*.{mp4,avi,mov,wmv,flv,webm,mp3,wav,ogg}", lambda route: route.abort())
                    # 阻止字体文件（可选，但保留以免影响显示）
                    # await self.browser_context.route("**/*.{woff,woff2,ttf,eot,otf}", lambda route: route.abort())
                    
                    self._log_debug("Browser context created successfully - images enabled for captcha", context)
                except Exception as e:
                    raise BrowserInitializationError(
                        f"Failed to create browser context: {str(e)}",
                        backend="playwright",
                        details={"step": "context_creation"}
                    )
            
            if self.on_log_message:
                self.on_log_message(tr("Browser initialized successfully"))
            
            return True
        
        except BrowserInitializationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            error = BrowserInitializationError(
                f"Unexpected error during browser initialization: {str(e)}",
                backend="playwright",
                details={"step": "unknown", "original_error": str(e)}
            )
            self._log_error(error, context)
            raise error
    
    async def _cleanup_browser(self):
        """Clean up Playwright browser resources with proper error handling"""
        context = "browser_cleanup"
        
        try:
            self._log_debug("Starting browser cleanup", context)
            
            # Close browser context
            if self.browser_context:
                try:
                    self._log_debug("Closing browser context", context)
                    await self.browser_context.close()
                    self.browser_context = None
                    self._log_debug("Browser context closed", context)
                except Exception as e:
                    self._log_warning(f"Error closing browser context: {str(e)}", context)
                    self.browser_context = None
            
            # Close browser
            if self.browser:
                try:
                    self._log_debug("Closing browser", context)
                    await self.browser.close()
                    self.browser = None
                    self._log_debug("Browser closed", context)
                except Exception as e:
                    self._log_warning(f"Error closing browser: {str(e)}", context)
                    self.browser = None
            
            # Stop Playwright
            if self.playwright:
                try:
                    self._log_debug("Stopping Playwright", context)
                    await self.playwright.stop()
                    self.playwright = None
                    self._log_debug("Playwright stopped", context)
                except Exception as e:
                    self._log_warning(f"Error stopping Playwright: {str(e)}", context)
                    self.playwright = None
            
            if self.on_log_message:
                self.on_log_message(tr("Browser resources cleaned up"))
        
        except Exception as e:
            error = AutomationError(
                f"Unexpected error during browser cleanup: {str(e)}",
                "CLEANUP_ERROR",
                {"step": "unknown"}
            )
            self._log_error(error, context)
    
    async def register_single_account(self, account: Account) -> bool:
        """
        Register a single account using the configured automation backend with error handling
        
        Args:
            account: Account to register
            
        Returns:
            True if registration successful, False otherwise
        """
        context = "register_single_account"
        self._log_debug(f"Starting single account registration for: {account.username}", context)
        
        try:
            if self.backend == "selenium":
                # For selenium backend, use synchronous registration
                self._register_with_selenium(account)
                return account.status == AccountStatus.SUCCESS
            else:
                # For playwright backend, use existing async method
                return await self._register_single_account_playwright(account)
                
        except Exception as e:
            error = AutomationError(
                f"Backend selection error: {str(e)}",
                "BACKEND_ERROR",
                {"backend": self.backend, "account_username": account.username}
            )
            self._log_error(error, context, account)
            account.mark_failed(str(error))
            return False
    
    async def _register_single_account_playwright(self, account: Account) -> bool:
        """
        Register a single account using Playwright automation with comprehensive error handling
        
        Args:
            account: Account to register
            
        Returns:
            True if registration successful, False otherwise
        """
        context = "playwright_registration"
        self._log_debug(f"Starting single account registration for: {account.username}", context)
        
        # Initialize browser
        try:
            if not await self._initialize_browser():
                error = BrowserInitializationError("Browser initialization returned False")
                self._log_error(error, context, account)
                account.mark_failed("Failed to initialize browser")
                return False
        except BrowserInitializationError as e:
            self._log_error(e, context, account)
            account.mark_failed(str(e))
            return False
        except Exception as e:
            error = BrowserInitializationError(f"Unexpected browser initialization error: {str(e)}")
            self._log_error(error, context, account)
            account.mark_failed(str(error))
            return False
        
        page: Optional[Page] = None
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            self._log_debug("Account marked as processing", context)
            
            # Create new page
            try:
                self._log_debug("Creating new browser page", context)
                page = await self.browser_context.new_page()
                self._log_debug("New browser page created successfully", context)
            except Exception as e:
                raise BrowserInitializationError(
                    f"Failed to create new page: {str(e)}",
                    backend="playwright",
                    details={"step": "page_creation"}
                )
            
            if self.on_log_message:
                self.on_log_message(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn
            self._log_debug("Step 1 - Navigating to 360.cn", context)
            account.mark_processing(tr("Navigating to 360.cn"))
            
            # Navigate to 360.cn with comprehensive error handling
            try:
                await self._safe_navigate(page, 'https://wan.360.cn/', max_retries=2, timeout=20)
                if self.on_log_message:
                    self.on_log_message(tr("Navigated to 360.cn"))
                    self.on_log_message(tr("DEBUG: Current URL: %1").replace("%1", page.url))
                
                # Wait for page to stabilize - 减少等待时间
                await asyncio.sleep(3)
                self._log_debug("Waited 3 seconds for page to fully load and stabilize", context)
                
            except PageNavigationError as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = PageNavigationError('https://wan.360.cn/', 1, str(e))
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 2: Click registration button
            self._log_debug("Step 2 - Looking for registration button", context)
            account.mark_processing(tr("Opening registration form"))
            
            # Wait for JavaScript to initialize the page elements
            self._log_debug("Waiting for page JavaScript to initialize elements", context)
            await asyncio.sleep(3)
            
            registration_selectors = [
                '.quc-link-sign-up',  # 360.cn 实际使用的注册按钮类名
                '.wan-register-btn',
                'text="免费注册"',
                'text="注册"',
                'a[data-bk="wan-public-reg"]',
                'text="立即注册"',
                'a[href*="register"]',
                'xpath=/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'
            ]
            
            try:
                successful_selector = await self._safe_click_element(
                    page, registration_selectors, "registration_button", timeout=10
                )
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration button"))
                
                # Wait for registration form to appear
                modal_selectors = [
                    'xpath=/html/body/div[9]/div[2]/div/div/div/form',
                    '.modal form',
                    '.popup form',
                    '.register-form',
                    'form[action*="register"]',
                    'form input[name="username"]',
                    'form input[placeholder*="用户名"]',
                    'form input[placeholder*="账号"]'
                ]
                
                try:
                    await self._safe_wait_for_element(page, modal_selectors, "registration_form", timeout=10)
                    if self.on_log_message:
                        self.on_log_message(tr("Registration form appeared"))
                    
                    # Wait for form to stabilize
                    await asyncio.sleep(2)
                    self._log_debug("Waited 2 seconds for form to stabilize", context)
                    
                except ElementNotFoundError:
                    # Form may not be modal-based, continue anyway
                    self._log_warning("No registration form modal found, continuing anyway", context)
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("click", "registration_button", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 3: Fill username input
            self._log_debug("Step 3 - Filling username field", context)
            account.mark_processing(tr("Filling registration form"))
            
            username_selectors = [
                'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[1]/div/div/input',
                'input[name="username"]',
                'input[placeholder*="用户名"]',
                'input[placeholder*="账号"]',
                'input[placeholder*="Username"]',
                'form input[type="text"]:first-of-type',
                '#username',
                '.username',
                'form input[type="text"]'
            ]
            
            try:
                await self._safe_fill_element(page, username_selectors, account.username, "username_field", timeout=10)
                if self.on_log_message:
                    self.on_log_message(tr("Filled username: %1").replace("%1", account.username))
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("fill", "username_field", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 4: Fill password input
            self._log_debug("Step 4 - Filling password field", context)
            
            password_selectors = [
                'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[2]/div/div/input',
                'input[name="password"]',
                'input[placeholder*="密码"]',
                'input[placeholder*="Password"]',
                'input[type="password"]:first-of-type',
                '#password',
                '.password',
                'form input[type="password"]'
            ]
            
            try:
                await self._safe_fill_element(page, password_selectors, account.password, "password_field", timeout=10)
                if self.on_log_message:
                    self.on_log_message(tr("Filled password"))
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("fill", "password_field", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 5: Fill confirm password input
            self._log_debug("Step 5 - Filling confirm password field", context)
            
            confirm_password_selectors = [
                'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input',
                'input[name="confirm_password"]',
                'input[name="password_confirm"]',
                'input[placeholder*="再次输入"]',
                'input[placeholder*="确认密码"]',
                'form input[type="password"]:last-of-type'
            ]
            
            try:
                await self._safe_fill_element(page, confirm_password_selectors, account.password, "confirm_password_field", timeout=10)
                if self.on_log_message:
                    self.on_log_message(tr("Filled confirm password"))
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("fill", "confirm_password_field", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 6: Check registration terms agreement
            self._log_debug("Step 6 - Checking terms agreement", context)
            
            terms_checkbox_selectors = [
                'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input',
                'input[type="checkbox"]',
                '.terms input[type="checkbox"]',
                '.agreement input[type="checkbox"]',
                'label input[type="checkbox"]'
            ]
            
            try:
                element, selector = await self._safe_wait_for_element(page, terms_checkbox_selectors, "terms_checkbox", timeout=10)
                
                # Check if already checked
                is_checked = await element.is_checked()
                if not is_checked:
                    await element.check()
                    self._log_debug("Checked terms agreement", context)
                else:
                    self._log_debug("Terms agreement already checked", context)
                
                if self.on_log_message:
                    self.on_log_message(tr("Checked terms agreement"))
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("check", "terms_checkbox", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 7: Click confirm registration button
            self._log_debug("Step 7 - Clicking registration confirm button", context)
            account.mark_processing(tr("Submitting registration"))
            
            confirm_btn_selectors = [
                'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[3]/input',
                'input[type="submit"]',
                'button[type="submit"]',
                '.submit-btn',
                '.confirm-btn',
                'input[value*="注册"]',
                'button:contains("注册")'
            ]
            
            try:
                await self._safe_click_element(page, confirm_btn_selectors, "submit_button", timeout=10)
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration confirm button"))
                
                # Wait for submission to process
                await asyncio.sleep(3)
                self._log_debug("Waited 3 seconds after clicking submit", context)
                
            except (FormInteractionError, ElementNotFoundError) as e:
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = FormInteractionError("click", "submit_button", {"error": str(e)})
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
            
            # Step 8: Wait and verify registration result
            self._log_debug("Step 8 - Verifying registration result", context)
            account.mark_processing(tr("Verifying registration result"))
            
            # Wait for registration processing
            await asyncio.sleep(2)
            
            try:
                # Get current page content for analysis
                page_content = await page.content()
                
                # Use our improved detection method
                success, message = self._detect_registration_result(page_content, account)
                
                if success:
                    account.mark_success(message)
                    if self.on_log_message:
                        self.on_log_message(tr("SUCCESS: %1 registered successfully").replace("%1", account.username))
                    return True
                elif "CAPTCHA_DETECTED" in message:
                    # 检测到验证码 - 使用Account模型方法设置状态
                    account.mark_waiting_captcha(f"等待通过验证码: {message}")
                    
                    # 通知GUI更新状态
                    if self.on_account_complete:
                        self.on_account_complete(account)
                    
                    if self.on_log_message:
                        self.on_log_message(tr("⚠️ CAPTCHA DETECTED for %1: %2").replace("%1", account.username).replace("%2", message))
                        self.on_log_message(tr("Browser will stay open - please solve manually"))
                        self.on_log_message(tr("Starting main-thread QTimer captcha monitoring..."))
                    
                    # 启动验证码监控定时器
                    self._start_captcha_monitoring(account, page)
                    
                    # 立即返回True，表示这个账号已经开始处理
                    return True
                else:
                    # 其他未知状态
                    if self.on_log_message:
                        self.on_log_message(tr("UNKNOWN: %1 - %2").replace("%1", account.username).replace("%2", message))
                    account.mark_failed(f"Unknown registration state: {message}")
                    return False
                        
            except (AccountAlreadyExistsError, RegistrationFailureError) as e:
                # These are expected error types from our detection
                self._log_error(e, context, account)
                account.mark_failed(str(e))
                return False
            except Exception as e:
                error = RegistrationFailureError(f"Unexpected error during result verification: {str(e)}", "unexpected_error")
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
                account.mark_failed(str(e))
                return False
            
            except Exception as e:
                error = RegistrationFailureError(f"Unexpected error during result verification: {str(e)}", "unexpected_error")
                self._log_error(error, context, account)
                account.mark_failed(str(error))
                return False
                
            # All steps completed successfully if we reach here
            if self.on_account_complete:
                self.on_account_complete(account)
            
            return account.status == AccountStatus.SUCCESS
            
        except (BrowserInitializationError, PageNavigationError, ElementNotFoundError, 
                FormInteractionError, RegistrationFailureError, AccountAlreadyExistsError,
                CaptchaRequiredError, TimeoutError) as e:
            # These are our expected custom exceptions
            self._log_error(e, context, account)
            account.mark_failed(str(e))
            
            if self.on_account_complete:
                self.on_account_complete(account)
            
            return False
            
        except Exception as e:
            # Unexpected errors
            error = AutomationError(
                f"Unexpected error during registration: {str(e)}",
                "UNEXPECTED_ERROR",
                {"account_username": account.username, "step": "unknown"}
            )
            self._log_error(error, context, account)
            account.mark_failed(str(error))
            
            if self.on_account_complete:
                self.on_account_complete(account)
            
            return False
            
        finally:
            # 根据账号状态决定是否关闭浏览器
            should_close_browser = True
            
            # 只有在验证码等待状态时才保持浏览器打开
            # 如果启动了异步监控，浏览器由监控任务管理
            if (account.status == AccountStatus.WAITING_CAPTCHA):
                should_close_browser = False
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Keeping browser open - captcha monitoring active for %1").replace("%1", account.username))
            else:
                # 成功或其他失败情况都关闭浏览器，为下一个账号准备干净环境
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Closing browser for next account (Status: %1)").replace("%1", account.status.value))
            
            if should_close_browser:
                # 正常情况：关闭浏览器实例
                if page:
                    try:
                        self._log_debug("Closing browser page after registration", context)
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Closing browser page after registration"))
                        await page.close()
                        self._log_debug("Browser page closed successfully", context)
                    except Exception as e:
                        self._log_warning(f"Error closing page: {str(e)}", context)
                
                # 关闭浏览器上下文和实例
                try:
                    if self.browser_context:
                        self._log_debug("Closing browser context after registration", context)
                        await self.browser_context.close()
                        self.browser_context = None
                        self._log_debug("Browser context closed and reset", context)
                    
                    if self.browser:
                        self._log_debug("Closing browser instance after registration", context)
                        await self.browser.close()
                        self.browser = None
                        self._log_debug("Browser instance closed and reset", context)
                    
                    if self.playwright:
                        self._log_debug("Stopping playwright instance after registration", context)
                        await self.playwright.stop()
                        self.playwright = None
                        self._log_debug("Playwright instance stopped and reset", context)
                        
                except Exception as cleanup_error:
                    self._log_warning(f"Error during browser cleanup: {str(cleanup_error)}", context)
                    # 强制重置
                    self.browser_context = None
                    self.browser = None
                    self.playwright = None
            else:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Browser kept open for manual captcha resolution"))
    
    # ===== SELENIUM/UNDETECTED_CHROMEDRIVER METHODS =====
    
    def _initialize_selenium_driver(self) -> bool:
        """Initialize undetected_chromedriver instance"""
        if not SELENIUM_AVAILABLE:
            if self.on_log_message:
                self.on_log_message(tr("ERROR: Selenium backend not available"))
            return False
        
        try:
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Starting selenium driver initialization"))
            
            if not self.selenium_driver:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Creating undetected_chromedriver instance"))
                
                # Configure Chrome options for anti-detection
                options = uc.ChromeOptions()
                
                # Add anti-detection arguments similar to Playwright
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--no-first-run')
                options.add_argument('--no-default-browser-check')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-background-timer-throttling')
                options.add_argument('--disable-backgrounding-occluded-windows')
                options.add_argument('--disable-renderer-backgrounding')
                options.add_argument('--disable-ipc-flooding-protection')
                options.add_argument('--disable-hang-monitor')
                options.add_argument('--disable-prompt-on-repost')
                options.add_argument('--disable-sync')
                options.add_argument('--force-color-profile=srgb')
                options.add_argument('--metrics-recording-only')
                options.add_argument('--use-mock-keychain')
                options.add_argument('--disable-background-networking')
                options.add_argument('--window-size=1280,720')
                
                # Create the undetected Chrome driver
                self.selenium_driver = uc.Chrome(
                    options=options,
                    headless=False,  # Set to False for debugging
                    use_subprocess=True,
                    suppress_welcome=True
                )
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Undetected Chrome driver created successfully"))
            
            if self.on_log_message:
                self.on_log_message(tr("Selenium driver initialized successfully"))
            
            return True
        except Exception as e:
            error_msg = f"Selenium driver initialization failed: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("ERROR: %1").replace("%1", error_msg))
            return False
    
    def _cleanup_selenium_driver(self):
        """Clean up selenium driver resources"""
        try:
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Starting selenium driver cleanup"))
            
            if self.selenium_driver:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Closing selenium driver"))
                self.selenium_driver.quit()
                self.selenium_driver = None
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Selenium driver closed"))
            
            if self.on_log_message:
                self.on_log_message(tr("Selenium driver resources cleaned up"))
        except Exception as e:
            error_msg = f"Selenium driver cleanup error: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("WARNING: %1").replace("%1", error_msg))
    
    def _register_with_selenium(self, account: Account):
        """Register a single account using selenium/undetected_chromedriver"""
        if self.on_log_message:
            self.on_log_message(tr("DEBUG: Starting selenium registration for: %1").replace("%1", account.username))
        
        if not self._initialize_selenium_driver():
            account.mark_failed("Failed to initialize selenium driver")
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Selenium driver initialization failed, aborting registration"))
            return
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Account marked as processing"))
                self.on_log_message(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn with retry logic
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 1 - Navigating to 360.cn"))
            account.mark_processing(tr("Navigating to 360.cn"))
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Navigation attempt %1/%2").replace("%1", str(attempt + 1)).replace("%2", str(max_retries)))
                    
                    self.selenium_driver.get('https://wan.360.cn/')
                    
                    # Wait for page to load
                    WebDriverWait(self.selenium_driver, 60).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Navigation attempt %1 failed: %2, retrying...").replace("%1", str(attempt + 1)).replace("%2", str(e)))
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        # All retries failed
                        raise Exception(f"Failed to navigate to 360.cn after {max_retries} attempts: {str(e)}")
            
            if self.on_log_message:
                self.on_log_message(tr("Navigated to 360.cn"))
                self.on_log_message(tr("DEBUG: Current URL: %1").replace("%1", self.selenium_driver.current_url))
            
            # Add delay to ensure page is fully loaded
            time.sleep(5)
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Waited 5 seconds for page to fully load and stabilize"))
            
            # Step 2: Click registration button
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 2 - Looking for registration button"))
            account.mark_processing(tr("Opening registration form"))
            
            # Try multiple selectors for the registration button
            registration_selectors = [
                (By.CSS_SELECTOR, '.quc-link-sign-up'),  # 360.cn 实际使用的注册按钮类名
                (By.CSS_SELECTOR, '.wan-register-btn'),
                (By.CSS_SELECTOR, 'a[data-bk="wan-public-reg"]'),
                (By.LINK_TEXT, '免费注册'),
                (By.LINK_TEXT, '注册'),
                (By.LINK_TEXT, '立即注册'),
                (By.CSS_SELECTOR, 'a[href*="register"]'),
                (By.XPATH, '/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'),
            ]
            
            registration_clicked = False
            for by, selector in registration_selectors:
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Trying registration selector: %1").replace("%1", selector))
                    
                    elements = self.selenium_driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed():
                            if self.on_log_message:
                                text = element.text
                                self.on_log_message(tr("DEBUG: Found visible registration element with text: %1").replace("%1", str(text)))
                            
                            element.click()
                            registration_clicked = True
                            
                            if self.on_log_message:
                                self.on_log_message(tr("DEBUG: Clicked registration button"))
                            break
                    
                    if registration_clicked:
                        break
                        
                except Exception as e:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Selector %1 failed: %2").replace("%1", selector).replace("%2", str(e)))
                    continue
            
            if not registration_clicked:
                raise Exception("Could not find or click any registration button")
            
            if self.on_log_message:
                self.on_log_message(tr("Clicked registration button"))
            
            # Wait for registration modal/form to appear
            modal_selectors = [
                (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form'),
                (By.CSS_SELECTOR, '.modal form'),
                (By.CSS_SELECTOR, '.popup form'),
                (By.CSS_SELECTOR, '.register-form'),
                (By.CSS_SELECTOR, 'form[action*="register"]'),
                (By.CSS_SELECTOR, 'form input[name="username"]'),
                (By.CSS_SELECTOR, 'form input[placeholder*="用户名"]'),
                (By.CSS_SELECTOR, 'form input[placeholder*="账号"]')
            ]
            
            modal_found = False
            for by, selector in modal_selectors:
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Waiting for registration form: %1").replace("%1", selector))
                    
                    WebDriverWait(self.selenium_driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    modal_found = True
                    
                    if self.on_log_message:
                        self.on_log_message(tr("Registration form appeared"))
                    break
                    
                except TimeoutException as e:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Form selector %1 failed: %2").replace("%1", selector).replace("%2", str(e)))
                    continue
            
            if not modal_found:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: No registration form found, continuing anyway..."))
            
            # Add delay after modal appears
            time.sleep(2)
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Waited 2 seconds for form to stabilize"))
            
            # Step 3: Fill username input
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 3 - Filling username field"))
            account.mark_processing(tr("Filling registration form"))
            
            username_selectors = [
                (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[1]/div/div/input'),
                (By.NAME, 'username'),
                (By.CSS_SELECTOR, 'input[placeholder*="用户名"]'),
                (By.CSS_SELECTOR, 'input[placeholder*="账号"]'),
                (By.CSS_SELECTOR, 'input[placeholder*="Username"]'),
                (By.CSS_SELECTOR, 'form input[type="text"]:first-of-type'),
                (By.ID, 'username'),
                (By.CSS_SELECTOR, '.username'),
                (By.CSS_SELECTOR, 'form input[type="text"]')
            ]
            
            username_filled = False
            for by, selector in username_selectors:
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Trying username selector: %1").replace("%1", selector))
                    
                    elements = self.selenium_driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.clear()
                            element.send_keys(account.username)
                            username_filled = True
                            
                            if self.on_log_message:
                                self.on_log_message(tr("DEBUG: Successfully filled username with selector: %1").replace("%1", selector))
                            break
                    
                    if username_filled:
                        break
                        
                except Exception as e:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Username selector %1 failed: %2").replace("%1", selector).replace("%2", str(e)))
                    continue
            
            if not username_filled:
                raise Exception("Could not find or fill username field")
            
            if self.on_log_message:
                self.on_log_message(tr("Filled username: %1").replace("%1", account.username))
            
            # Step 4: Fill password input
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 4 - Filling password field"))
            
            password_selectors = [
                (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[2]/div/div/input'),
                (By.NAME, 'password'),
                (By.CSS_SELECTOR, 'input[placeholder*="密码"]'),
                (By.CSS_SELECTOR, 'input[placeholder*="Password"]'),
                (By.CSS_SELECTOR, 'input[type="password"]:first-of-type'),
                (By.ID, 'password'),
                (By.CSS_SELECTOR, '.password'),
                (By.CSS_SELECTOR, 'form input[type="password"]')
            ]
            
            password_filled = False
            for by, selector in password_selectors:
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Trying password selector: %1").replace("%1", selector))
                    
                    elements = self.selenium_driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.clear()
                            element.send_keys(account.password)
                            password_filled = True
                            
                            if self.on_log_message:
                                self.on_log_message(tr("DEBUG: Successfully filled password with selector: %1").replace("%1", selector))
                            break
                    
                    if password_filled:
                        break
                        
                except Exception as e:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Password selector %1 failed: %2").replace("%1", selector).replace("%2", str(e)))
                    continue
            
            if not password_filled:
                raise Exception("Could not find or fill password field")
            
            if self.on_log_message:
                self.on_log_message(tr("Filled password"))
            
            # Step 5: Fill confirm password input
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 5 - Filling confirm password field"))
            
            confirm_password_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input')
            
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for confirm password field"))
                
                element = WebDriverWait(self.selenium_driver, 5).until(
                    EC.element_to_be_clickable(confirm_password_selector)
                )
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Confirm password field found, filling"))
                
                element.clear()
                element.send_keys(account.password)
                
                if self.on_log_message:
                    self.on_log_message(tr("Filled confirm password"))
                
            except Exception as e:
                error_msg = f"Failed to fill confirm password: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 5: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 6: Check registration terms agreement
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 6 - Checking terms agreement"))
            
            terms_checkbox_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input')
            
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for terms checkbox"))
                
                element = WebDriverWait(self.selenium_driver, 5).until(
                    EC.element_to_be_clickable(terms_checkbox_selector)
                )
                
                if not element.is_selected():
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Terms checkbox found, checking"))
                    element.click()
                
                if self.on_log_message:
                    self.on_log_message(tr("Checked terms agreement"))
                
            except Exception as e:
                error_msg = f"Failed to check terms agreement: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 6: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 7: Click confirm registration button
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 7 - Clicking registration confirm button"))
            account.mark_processing(tr("Submitting registration"))
            
            confirm_btn_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[3]/input')
            
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for confirm button"))
                
                element = WebDriverWait(self.selenium_driver, 5).until(
                    EC.element_to_be_clickable(confirm_btn_selector)
                )
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Confirm button found, clicking"))
                
                element.click()
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration confirm button"))
                
                # Add delay after clicking submit
                time.sleep(3)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waited 3 seconds after clicking submit"))
                
            except Exception as e:
                error_msg = f"Failed to click registration button: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 7: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 8: Wait and verify success by checking logout link
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 8 - Verifying registration success"))
            account.mark_processing(tr("Verifying registration success"))
            
            logout_link_selector = (By.XPATH, '/html/body/div[1]/div/span[2]/a[2]')
            
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for logout link"))
                
                # Wait for registration processing (up to 30 seconds)
                element = WebDriverWait(self.selenium_driver, 30).until(
                    EC.presence_of_element_located(logout_link_selector)
                )
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Logout link found, checking text content"))
                
                # Check if logout link contains [退出] text
                logout_text = element.text
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Logout link text: %1").replace("%1", str(logout_text)))
                
                if logout_text and '[退出]' in logout_text:
                    # Registration successful
                    success_note = tr("Account registered successfully and automatically logged in")
                    account.mark_success(success_note)
                    if self.on_log_message:
                        self.on_log_message(tr("SUCCESS: %1 registered and logged in").replace("%1", account.username))
                    
                    # Call the completion callback
                    if self.on_account_complete:
                        self.on_account_complete(account)
                    
                    return
                else:
                    raise Exception(f"Logout link found but doesn't contain [退出]: {logout_text}")
                    
            except Exception as e:
                # Registration might have failed or requires verification
                error_msg = f"Registration verification failed: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 8: %1").replace("%1", error_msg))
                account.mark_failed(error_msg)
                if self.on_log_message:
                    self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
                
                # Call the completion callback for failed registration
                if self.on_account_complete:
                    self.on_account_complete(account)
                
                return
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: General exception in _register_with_selenium: %1").replace("%1", error_msg))
            account.mark_failed(error_msg)
            if self.on_log_message:
                self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
            
            # Call the completion callback for failed registration
            if self.on_account_complete:
                self.on_account_complete(account)
    
    def register_single_account_selenium(self, account: Account) -> bool:
        """
        Register a single account using undetected_chromedriver
        
        Args:
            account: Account to register
            
        Returns:
            True if registration successful, False otherwise
        """
        if self.backend != "selenium":
            raise ValueError("This method is only available when using selenium backend")
        
        if self.on_log_message:
            self.on_log_message(tr("DEBUG: Starting single account selenium registration for: %1").replace("%1", account.username))
        
        # Use the internal selenium registration method
        self._register_with_selenium(account)
        
        # Return success based on account status
        return account.status == AccountStatus.SUCCESS
    
    # ===== UTILITY METHODS =====
    
    def get_backend(self) -> AutomationBackend:
        """Get the current automation backend"""
        return self.backend
    
    def set_backend(self, backend: AutomationBackend):
        """
        Set the automation backend
        
        Args:
            backend: Backend to use ('playwright' or 'selenium')
            
        Raises:
            ImportError: If selenium backend is requested but not available
            ValueError: If trying to switch while automation is running
        """
        if self.is_running:
            raise ValueError("Cannot change backend while automation is running")
        
        if backend == "selenium" and not SELENIUM_AVAILABLE:
            raise ImportError("Selenium backend requested but undetected_chromedriver is not available. "
                            "Install it with: pip install undetected-chromedriver")
        
        # Clean up current backend resources
        if self.backend != backend:
            try:
                if self.backend == "playwright":
                    if self.browser_context or self.browser or self.playwright:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._cleanup_browser())
                        else:
                            asyncio.run(self._cleanup_browser())
                else:
                    self._cleanup_selenium_driver()
            except Exception:
                pass
        
        self.backend = backend
        
        if self.on_log_message:
            self.on_log_message(tr("Backend switched to: %1").replace("%1", backend))
    
    def is_selenium_available(self) -> bool:
        """Check if selenium/undetected_chromedriver is available"""
        return SELENIUM_AVAILABLE
    
    def get_available_backends(self) -> list[AutomationBackend]:
        """Get list of available backends"""
        backends = ["playwright"]
        if SELENIUM_AVAILABLE:
            backends.append("selenium")
        return backends