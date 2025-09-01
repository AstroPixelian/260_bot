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
    
    async def _safe_navigate(self, page: Page, url: str, max_retries: int = 3, timeout: int = 60) -> None:
        """Navigate to URL with retry logic and proper error handling"""
        context = "navigation"
        
        for attempt in range(max_retries):
            try:
                self._log_debug(f"Navigation attempt {attempt + 1}/{max_retries} to {url}", context)
                
                await page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
                self._log_debug(f"Successfully navigated to {url}", context)
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
        """Detect registration result from page content"""
        context = "result_detection"
        
        # Check for already registered messages
        already_registered_messages = [
            "该账号已经注册",
            "账号已存在", 
            "用户名已存在",
            "已注册",
            "用户名已被占用"
        ]
        
        for message in already_registered_messages:
            if message in page_content:
                self._log_debug(f"Detected already registered: {message}", context)
                raise AccountAlreadyExistsError(account.username, message)
        
        # Check for success indicators
        success_indicators = [
            "[退出]",
            "退出",
            "注册成功",
            "登录成功"
        ]
        
        for indicator in success_indicators:
            if indicator in page_content:
                self._log_debug(f"Detected success indicator: {indicator}", context)
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
        self.current_account_index = 0
        
        # Reset all accounts to queued status
        for account in accounts:
            account.reset_status()
        
        if self.on_log_message:
            self.on_log_message(tr("Started batch processing for %1 accounts").replace("%1", str(len(accounts))))
        
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
                            '--disable-background-networking'
                        ],
                        slow_mo=200,  # Increase delay between actions for stability
                        timeout=90000  # 90 second timeout for browser launch
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
                    self._log_debug("Browser context created successfully", context)
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
                await self._safe_navigate(page, 'https://wan.360.cn/', max_retries=3, timeout=60)
                if self.on_log_message:
                    self.on_log_message(tr("Navigated to 360.cn"))
                    self.on_log_message(tr("DEBUG: Current URL: %1").replace("%1", page.url))
                
                # Wait for page to stabilize
                await asyncio.sleep(10)
                self._log_debug("Waited 10 seconds for page to fully load and stabilize", context)
                
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
            
            registration_selectors = [
                'text="注册"',
                'text="立即注册"',
                'text="免费注册"',
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
                
                # Use our detection method
                success, message = self._detect_registration_result(page_content, account)
                
                if success:
                    account.mark_success(message)
                    if self.on_log_message:
                        self.on_log_message(tr("SUCCESS: %1 registered successfully").replace("%1", account.username))
                    return True
                else:
                    # No clear result - check for logout button as final verification
                    logout_selectors = [
                        'xpath=/html/body/div[1]/div/span[2]/a[2]',
                        'text="[退出]"',
                        'text="退出"',
                        '.wan-logout-btn',
                        '[data-bk="wan-public-dropout"]'
                    ]
                    
                    try:
                        element, _ = await self._safe_wait_for_element(page, logout_selectors, "logout_button", timeout=20)
                        logout_text = await element.text_content()
                        
                        if logout_text and '[退出]' in logout_text:
                            success_note = tr("Account registered successfully (logout button detected)")
                            account.mark_success(success_note)
                            if self.on_log_message:
                                self.on_log_message(tr("SUCCESS: %1 registered (logout detected)").replace("%1", account.username))
                            return True
                        else:
                            raise RegistrationFailureError(f"Logout button found but invalid text: {logout_text}", "verification_failed")
                    
                    except ElementNotFoundError:
                        raise RegistrationFailureError("Could not verify registration - no logout button found", "verification_timeout")
                    except Exception as e:
                        raise RegistrationFailureError(f"Registration verification failed: {str(e)}", "verification_error")
            
            except (AccountAlreadyExistsError, CaptchaRequiredError, RegistrationFailureError) as e:
                # These are expected error types from our detection
                self._log_error(e, context, account)
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
            # Clean up page resources
            if page:
                try:
                    self._log_debug("Closing browser page", context)
                    await page.close()
                    self._log_debug("Browser page closed successfully", context)
                except Exception as e:
                    self._log_warning(f"Error closing page: {str(e)}", context)
    
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
                (By.XPATH, '/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'),
                (By.LINK_TEXT, '注册'),
                (By.LINK_TEXT, '立即注册'),
                (By.LINK_TEXT, '免费注册'),
                (By.CSS_SELECTOR, 'a[href*="register"]'),
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