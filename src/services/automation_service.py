"""
Automation service for batch account registration
"""

import random
import asyncio
from typing import Callable, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, PlaywrightContextManager, ViewportSize
from ..models.account import Account, AccountStatus
from ..account_generator import AccountGenerator
from ..translation_manager import tr


class AutomationService:
    """Service for automated account registration"""
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        self.success_rate = 0.8  # 80% success rate for simulation
        
        # Playwright browser management
        self.playwright: Optional[PlaywrightContextManager] = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None
        
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
        
        # Clean up browser resources
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If in an event loop, schedule cleanup
                asyncio.create_task(self._cleanup_browser())
            else:
                # If not in an event loop, run cleanup synchronously
                asyncio.run(self._cleanup_browser())
        except:
            # If cleanup fails, continue anyway
            pass
        
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
        
        # Simulate registration process (this would be replaced with real automation)
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
        """Initialize Playwright browser and context"""
        try:
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Starting browser initialization"))
            
            if not self.playwright:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Starting Playwright instance"))
                self.playwright = await async_playwright().start()
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Playwright instance started successfully"))
            
            if not self.browser:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Launching Chromium browser"))
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
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Chromium browser launched successfully"))
            
            if not self.browser_context:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Creating browser context"))
                self.browser_context = await self.browser.new_context(
                    viewport=ViewportSize({'width': 1280, 'height': 720}),
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Browser context created successfully"))
            
            if self.on_log_message:
                self.on_log_message(tr("Browser initialized successfully"))
            
            return True
        except Exception as e:
            error_msg = f"Browser initialization failed: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("ERROR: %1").replace("%1", error_msg))
            return False
    
    async def _cleanup_browser(self):
        """Clean up Playwright browser resources"""
        try:
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Starting browser cleanup"))
            
            if self.browser_context:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Closing browser context"))
                await self.browser_context.close()
                self.browser_context = None
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Browser context closed"))
            
            if self.browser:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Closing browser"))
                await self.browser.close()
                self.browser = None
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Browser closed"))
            
            if self.playwright:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Stopping Playwright"))
                await self.playwright.stop()
                self.playwright = None
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Playwright stopped"))
            
            if self.on_log_message:
                self.on_log_message(tr("Browser resources cleaned up"))
        except Exception as e:
            error_msg = f"Browser cleanup error: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("WARNING: %1").replace("%1", error_msg))
    
    async def register_single_account(self, account: Account) -> bool:
        """
        Register a single account using Playwright automation
        
        Args:
            account: Account to register
            
        Returns:
            True if registration successful, False otherwise
        """
        if self.on_log_message:
            self.on_log_message(tr("DEBUG: Starting single account registration for: %1").replace("%1", account.username))
        
        if not await self._initialize_browser():
            account.mark_failed("Failed to initialize browser")
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Browser initialization failed, aborting registration"))
            return False
        
        page: Optional[Page] = None
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Account marked as processing"))
            
            # Create new page
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Creating new browser page"))
            page = await self.browser_context.new_page()
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: New browser page created successfully"))
            
            if self.on_log_message:
                self.on_log_message(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn with retry logic
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Step 1 - Navigating to 360.cn"))
            account.mark_processing(tr("Navigating to 360.cn"))
            
            # Try navigation with multiple attempts and different wait strategies
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Navigation attempt %1/%2").replace("%1", str(attempt + 1)).replace("%2", str(max_retries)))
                    
                    # Use longer timeout and different wait strategy
                    await page.goto('https://wan.360.cn/', 
                                  wait_until='networkidle', 
                                  timeout=60000)  # 60 second timeout
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Navigation attempt %1 failed: %2, retrying...").replace("%1", str(attempt + 1)).replace("%2", str(e)))
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        # All retries failed
                        raise Exception(f"Failed to navigate to 360.cn after {max_retries} attempts: {str(e)}")
            
            if self.on_log_message:
                self.on_log_message(tr("Navigated to 360.cn"))
                self.on_log_message(tr("DEBUG: Current URL: %1").replace("%1", page.url))
            
            # Add a longer delay to ensure page is fully loaded and allow manual inspection
            await asyncio.sleep(5)
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: Waited 5 seconds for page to fully load and stabilize"))
            
            # Step 2: Click registration button
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 2 - Looking for registration button"))
                account.mark_processing(tr("Opening registration form"))
                
                # Try multiple selectors for the registration button
                registration_selectors = [
                    'text="注册"',  # Found by inspector
                    'text="立即注册"',
                    'text="免费注册"',
                    'a[href*="register"]',
                    'xpath=/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'
                ]
                
                registration_clicked = False
                for selector in registration_selectors:
                    try:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Trying registration selector: %1").replace("%1", selector))
                        
                        # Check if element exists and is visible
                        elements = await page.locator(selector).all()
                        if elements:
                            for element in elements:
                                if await element.is_visible():
                                    if self.on_log_message:
                                        text = await element.text_content()
                                        self.on_log_message(tr("DEBUG: Found visible registration element with text: %1").replace("%1", str(text)))
                                    
                                    await element.click()
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
                
                # Wait for registration modal/form to appear with multiple possible selectors
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
                
                modal_found = False
                for selector in modal_selectors:
                    try:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Waiting for registration form: %1").replace("%1", selector))
                        
                        await page.wait_for_selector(selector, timeout=5000)
                        modal_found = True
                        
                        if self.on_log_message:
                            self.on_log_message(tr("Registration form appeared"))
                        break
                        
                    except Exception as e:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Form selector %1 failed: %2").replace("%1", selector).replace("%2", str(e)))
                        continue
                
                if not modal_found:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: No registration form found, continuing anyway..."))
                
                # Add delay after modal appears
                await asyncio.sleep(2)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waited 2 seconds for form to stabilize"))
                
            except Exception as e:
                error_msg = f"Failed to open registration modal: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 2: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 3: Fill username input
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 3 - Filling username field"))
                account.mark_processing(tr("Filling registration form"))
                
                # Try multiple selectors for username field
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
                
                username_filled = False
                for selector in username_selectors:
                    try:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Trying username selector: %1").replace("%1", selector))
                        
                        elements = await page.locator(selector).all()
                        if elements:
                            for element in elements:
                                if await element.is_visible():
                                    await element.fill(account.username)
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
                
            except Exception as e:
                error_msg = f"Failed to fill username: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 3: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 4: Fill password input
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 4 - Filling password field"))
                
                # Try multiple selectors for password field
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
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        if self.on_log_message:
                            self.on_log_message(tr("DEBUG: Trying password selector: %1").replace("%1", selector))
                        
                        elements = await page.locator(selector).all()
                        if elements:
                            for element in elements:
                                if await element.is_visible():
                                    await element.fill(account.password)
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
                
            except Exception as e:
                error_msg = f"Failed to fill password: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 4: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 5: Fill confirm password input
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 5 - Filling confirm password field"))
                confirm_password_selector = 'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input'
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for confirm password field: %1").replace("%1", confirm_password_selector))
                
                await page.wait_for_selector(confirm_password_selector, timeout=5000)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Confirm password field found, filling"))
                
                await page.fill(confirm_password_selector, account.password)
                
                if self.on_log_message:
                    self.on_log_message(tr("Filled confirm password"))
                
            except Exception as e:
                error_msg = f"Failed to fill confirm password: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 5: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 6: Check registration terms agreement
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 6 - Checking terms agreement"))
                terms_checkbox_selector = 'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input'
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for terms checkbox: %1").replace("%1", terms_checkbox_selector))
                
                await page.wait_for_selector(terms_checkbox_selector, timeout=5000)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Terms checkbox found, checking"))
                
                await page.check(terms_checkbox_selector)
                
                if self.on_log_message:
                    self.on_log_message(tr("Checked terms agreement"))
                
            except Exception as e:
                error_msg = f"Failed to check terms agreement: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 6: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 7: Click confirm registration button
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 7 - Clicking registration confirm button"))
                account.mark_processing(tr("Submitting registration"))
                confirm_btn_selector = 'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[3]/input'
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for confirm button: %1").replace("%1", confirm_btn_selector))
                
                await page.wait_for_selector(confirm_btn_selector, timeout=5000)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Confirm button found, clicking"))
                
                await page.click(confirm_btn_selector)
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration confirm button"))
                
                # Add delay after clicking submit
                await asyncio.sleep(3)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waited 3 seconds after clicking submit"))
                
            except Exception as e:
                error_msg = f"Failed to click registration button: {str(e)}"
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Exception in step 7: %1").replace("%1", error_msg))
                raise Exception(error_msg)
            
            # Step 8: Wait and verify success by checking logout link
            try:
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Step 8 - Verifying registration success"))
                account.mark_processing(tr("Verifying registration success"))
                logout_link_selector = 'xpath=/html/body/div[1]/div/span[2]/a[2]'
                
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Waiting for logout link: %1").replace("%1", logout_link_selector))
                
                # Wait for registration processing (up to 30 seconds)
                await page.wait_for_selector(logout_link_selector, timeout=30000)
                if self.on_log_message:
                    self.on_log_message(tr("DEBUG: Logout link found, checking text content"))
                
                # Check if logout link contains [退出] text
                logout_element = await page.query_selector(logout_link_selector)
                if logout_element:
                    logout_text = await logout_element.text_content()
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
                        
                        return True
                    else:
                        raise Exception(f"Logout link found but doesn't contain [退出]: {logout_text}")
                else:
                    raise Exception("Logout link element not found after registration")
                    
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
                
                return False
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("DEBUG: General exception in register_single_account: %1").replace("%1", error_msg))
            account.mark_failed(error_msg)
            if self.on_log_message:
                self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
            
            # Call the completion callback for failed registration
            if self.on_account_complete:
                self.on_account_complete(account)
            
            return False
        finally:
            # Close the page
            if page:
                try:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Closing browser page"))
                    await page.close()
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Browser page closed successfully"))
                except Exception as e:
                    if self.on_log_message:
                        self.on_log_message(tr("DEBUG: Error closing page: %1").replace("%1", str(e)))
    
    def generate_test_accounts(self, count: int = 3) -> list[Account]:
        """
        Generate test accounts using AccountGenerator for registration testing
        
        Args:
            count: Number of accounts to generate
            
        Returns:
            List of Account objects ready for registration
        """
        try:
            # Create AccountGenerator with 360.cn compatible settings
            config = {
                "account_generator": {
                    "username_min_length": 8,
                    "username_max_length": 16,
                    "password_min_length": 12,
                    "password_max_length": 20,
                    "password_special_chars": "!@#$%^&*"
                }
            }
            
            generator = AccountGenerator(config)
            accounts_data = generator.generate_accounts(count)
            
            # Convert to Account objects
            accounts = []
            for i, acc_data in enumerate(accounts_data):
                account = Account(
                    id=i + 1,
                    username=acc_data["username"],
                    password=acc_data["password"]
                )
                accounts.append(account)
            
            if self.on_log_message:
                self.on_log_message(tr("Generated %1 test accounts for registration").replace("%1", str(count)))
            
            return accounts
            
        except Exception as e:
            error_msg = f"Failed to generate test accounts: {str(e)}"
            if self.on_log_message:
                self.on_log_message(tr("ERROR: %1").replace("%1", error_msg))
            return []