"""
Playwright backend implementation for automation

Handles all Playwright-specific browser automation logic for account registration.
"""

import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, PlaywrightContextManager, ViewportSize
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .base_backend import AutomationBackend
from .form_helpers import FormSelectors, RetryHelper
from .result_detector import RegistrationResultDetector
from ...models.account import Account, AccountStatus
from ...translation_manager import tr
from ...exceptions import (
    BrowserInitializationError, ElementNotFoundError, PageNavigationError,
    FormInteractionError, RegistrationFailureError, TimeoutError, 
    AccountAlreadyExistsError, CaptchaRequiredError
)


class PlaywrightBackend(AutomationBackend):
    """Playwright automation backend for account registration"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Playwright browser management
        self.playwright: Optional[PlaywrightContextManager] = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None
    
    def get_backend_name(self) -> str:
        return "playwright"
    
    def is_available(self) -> bool:
        """Check if Playwright is available"""
        try:
            import playwright
            return True
        except ImportError:
            return False
    
    async def register_account(self, account: Account) -> bool:
        """Register a single account using Playwright automation"""
        context = "playwright_registration"
        self.logger.debug(f"Starting registration for: {account.username}")
        
        # Initialize browser
        try:
            if not await self._initialize_browser():
                account.mark_failed("Failed to initialize browser")
                return False
        except Exception as e:
            account.mark_failed(f"Browser initialization error: {str(e)}")
            return False
        
        page: Optional[Page] = None
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            
            # Create new page
            page = await self.browser_context.new_page()
            self._log(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn
            account.mark_processing(tr("Navigating to 360.cn"))
            await self._safe_navigate(page, 'https://wan.360.cn/', max_retries=2, timeout=20)
            self._log(tr("Navigated to 360.cn"))
            
            # Wait for page to stabilize
            await asyncio.sleep(3)
            
            # Step 2: Click registration button
            account.mark_processing(tr("Opening registration form"))
            await asyncio.sleep(3)  # Wait for JavaScript initialization
            
            await self._safe_click_element(
                page, FormSelectors.REGISTRATION_BUTTONS, "registration_button", timeout=10
            )
            self._log(tr("Clicked registration button"))
            
            # Wait for registration form
            try:
                await self._safe_wait_for_element(page, FormSelectors.REGISTRATION_FORMS, "registration_form", timeout=10)
                self._log(tr("Registration form appeared"))
                await asyncio.sleep(2)
            except ElementNotFoundError:
                self.logger.warning("No registration form modal found, continuing anyway")
            
            # Step 3-6: Fill form fields
            account.mark_processing(tr("Filling registration form"))
            
            await self._safe_fill_element(page, FormSelectors.USERNAME_FIELDS, account.username, "username_field", timeout=10)
            self._log(tr("Filled username: %1").replace("%1", account.username))
            
            await self._safe_fill_element(page, FormSelectors.PASSWORD_FIELDS, account.password, "password_field", timeout=10)
            self._log(tr("Filled password"))
            
            await self._safe_fill_element(page, FormSelectors.CONFIRM_PASSWORD_FIELDS, account.password, "confirm_password_field", timeout=10)
            self._log(tr("Filled confirm password"))
            
            # Check terms agreement
            element, _ = await self._safe_wait_for_element(page, FormSelectors.TERMS_CHECKBOXES, "terms_checkbox", timeout=10)
            if not await element.is_checked():
                await element.check()
            self._log(tr("Checked terms agreement"))
            
            # Step 7: Submit form
            account.mark_processing(tr("Submitting registration"))
            await self._safe_click_element(page, FormSelectors.SUBMIT_BUTTONS, "submit_button", timeout=10)
            self._log(tr("Clicked registration confirm button"))
            
            # Wait for submission to process
            await asyncio.sleep(3)
            
            # Step 8: Verify result
            account.mark_processing(tr("Verifying registration result"))
            await asyncio.sleep(2)
            
            # Get page content and detect result
            page_content = await page.content()
            success, message = RegistrationResultDetector.detect_registration_result(page_content, account)
            
            if success:
                account.mark_success(message)
                self._log(tr("SUCCESS: %1 registered successfully").replace("%1", account.username))
                return True
            elif "CAPTCHA_DETECTED" in message:
                account.mark_waiting_captcha(f"等待通过验证码: {message}")
                self._log(tr("⚠️ CAPTCHA DETECTED for %1: %2").replace("%1", account.username).replace("%2", message))
                return True
            else:
                account.mark_failed(f"Unknown registration state: {message}")
                return False
            
        except (BrowserInitializationError, PageNavigationError, ElementNotFoundError,
                FormInteractionError, RegistrationFailureError, AccountAlreadyExistsError,
                CaptchaRequiredError, TimeoutError) as e:
            self.logger.error(f"Registration failed: {e}", exc_info=True)
            account.mark_failed(str(e))
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            account.mark_failed(f"Unexpected error: {str(e)}")
            return False
        finally:
            # Cleanup based on account status
            should_close_browser = account.status != AccountStatus.CAPTCHA_PENDING
            
            if should_close_browser and page:
                try:
                    await page.close()
                    await self._cleanup_browser()
                except Exception as e:
                    self.logger.warning(f"Error during browser cleanup: {e}")
    
    async def _initialize_browser(self) -> bool:
        """Initialize Playwright browser and context"""
        try:
            # Initialize Playwright
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            # Launch browser
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
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
                    ],
                    slow_mo=100,
                    timeout=60000
                )
            
            # Create browser context
            if not self.browser_context:
                self.browser_context = await self.browser.new_context(
                    viewport=ViewportSize({'width': 1280, 'height': 720}),
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Block media files but keep images for captcha
                await self.browser_context.route("**/*.{mp4,avi,mov,wmv,flv,webm,mp3,wav,ogg}", lambda route: route.abort())
            
            self._log(tr("Browser initialized successfully"))
            return True
            
        except Exception as e:
            error = BrowserInitializationError(f"Failed to initialize browser: {str(e)}")
            self.logger.error(str(error))
            raise error
    
    async def _cleanup_browser(self):
        """Clean up Playwright browser resources"""
        try:
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            self._log(tr("Browser resources cleaned up"))
        except Exception as e:
            self.logger.warning(f"Error during browser cleanup: {e}")
    
    def cleanup(self):
        """Clean up backend resources (sync interface)"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._cleanup_browser())
            else:
                asyncio.run(self._cleanup_browser())
        except Exception as e:
            self.logger.warning(f"Error in sync cleanup: {e}")
    
    # Helper methods for element interaction
    async def _safe_navigate(self, page: Page, url: str, max_retries: int = 3, timeout: int = 30):
        """Navigate to URL with retry logic and proper error handling"""
        for attempt in range(max_retries):
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
                return
            except PlaywrightTimeoutError:
                try:
                    await page.goto(url, wait_until='load', timeout=(timeout - 5) * 1000)
                    return
                except PlaywrightTimeoutError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise PageNavigationError(url, max_retries, f"Timeout after {timeout}s")
            except PlaywrightError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    raise PageNavigationError(url, max_retries, str(e))
    
    async def _safe_wait_for_element(self, page: Page, selectors: list[str], element_type: str, timeout: int = 10) -> Tuple[object, str]:
        """Wait for element with multiple selectors"""
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout * 1000)
                elements = await page.locator(selector).all()
                
                for element in elements:
                    if await element.is_visible():
                        return element, selector
                        
            except PlaywrightTimeoutError:
                continue
        
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
            return successful_selector
        except Exception as e:
            raise FormInteractionError("click", element_type, {"selector": successful_selector, "error": str(e)})
    
    async def _safe_fill_element(self, page: Page, selectors: list[str], value: str, element_type: str, timeout: int = 10) -> str:
        """Safely fill element with multiple selector fallbacks"""
        element, successful_selector = await self._safe_wait_for_element(page, selectors, element_type, timeout)
        
        try:
            await element.fill(value)
            return successful_selector
        except Exception as e:
            raise FormInteractionError("fill", element_type, {
                "selector": successful_selector,
                "error": str(e),
                "value_length": len(value)
            })