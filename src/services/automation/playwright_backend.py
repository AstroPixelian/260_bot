"""
Playwright后端实现
Playwright Backend Implementation
"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, PlaywrightContextManager, ViewportSize
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .base_backend import AutomationBackend
from .simple_state_machine import RegistrationMachine
from ...models.account import Account, AccountStatus
from ...translation_manager import tr
from ...exceptions import BrowserInitializationError


class PlaywrightBackend(AutomationBackend):
    """Playwright自动化后端"""
    
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
        """Register a single account using simplified state machine"""
        self.logger.debug(f"开始简化状态机注册: {account.username}")
        
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
            # Create new page
            page = await self.browser_context.new_page()
            self._log(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Create simplified state machine
            state_machine = RegistrationMachine(account, page)
            
            # Set up state machine callbacks
            state_machine.on_log = self._log
            state_machine.on_captcha_detected = self._on_captcha_detected
            state_machine.on_success = self._on_registration_success
            state_machine.on_failed = self._on_registration_failed
            
            # Run the state machine
            success = await state_machine.run()
            
            self.logger.info(f"简化状态机完成 {account.username}: {'SUCCESS' if success else 'FAILED'}")
            
            return success
            
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
    
    def _on_captcha_detected(self, account: Account, message: str):
        """Handle captcha detection callback"""
        self._log(tr("⚠️ CAPTCHA DETECTED for %1: %2").replace("%1", account.username).replace("%2", message))
        self._log(tr("Browser will stay open - please solve manually"))
    
    def _on_registration_success(self, account: Account, message: str):
        """Handle registration success callback"""
        self._log(tr("SUCCESS: %1 registered successfully").replace("%1", account.username))
    
    def _on_registration_failed(self, account: Account, message: str):
        """Handle registration failure callback"""
        self._log(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", message))
    
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