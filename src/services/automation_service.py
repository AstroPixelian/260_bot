"""
Automation service for batch account registration
"""

import random
import asyncio
from typing import Callable, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, PlaywrightContextManager
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
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,  # Set to False for debugging
                    args=['--disable-blink-features=AutomationControlled']
                )
            
            if not self.browser_context:
                self.browser_context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            
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
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
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
        if not await self._initialize_browser():
            account.mark_failed("Failed to initialize browser")
            return False
        
        page: Optional[Page] = None
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            
            # Create new page
            page = await self.browser_context.new_page()
            
            if self.on_log_message:
                self.on_log_message(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn
            account.mark_processing(tr("Navigating to 360.cn"))
            await page.goto('https://wan.360.cn/', wait_until='domcontentloaded', timeout=30000)
            
            if self.on_log_message:
                self.on_log_message(tr("Navigated to 360.cn"))
            
            # Step 2: Click registration button
            try:
                account.mark_processing(tr("Opening registration form"))
                registration_btn_selector = '/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'
                await page.wait_for_selector(registration_btn_selector, timeout=10000)
                await page.click(registration_btn_selector)
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration button"))
                
                # Wait for registration modal to appear
                await page.wait_for_selector('/html/body/div[9]/div[2]/div/div/div/form', timeout=10000)
                
                if self.on_log_message:
                    self.on_log_message(tr("Registration modal appeared"))
                
            except Exception as e:
                raise Exception(f"Failed to open registration modal: {str(e)}")
            
            # Step 3: Fill username input
            try:
                account.mark_processing(tr("Filling registration form"))
                username_selector = '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[1]/div/div/input'
                await page.wait_for_selector(username_selector, timeout=5000)
                await page.fill(username_selector, account.username)
                
                if self.on_log_message:
                    self.on_log_message(tr("Filled username: %1").replace("%1", account.username))
                
            except Exception as e:
                raise Exception(f"Failed to fill username: {str(e)}")
            
            # Step 4: Fill password input
            try:
                password_selector = '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[2]/div/div/input'
                await page.wait_for_selector(password_selector, timeout=5000)
                await page.fill(password_selector, account.password)
                
                if self.on_log_message:
                    self.on_log_message(tr("Filled password"))
                
            except Exception as e:
                raise Exception(f"Failed to fill password: {str(e)}")
            
            # Step 5: Fill confirm password input
            try:
                confirm_password_selector = '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input'
                await page.wait_for_selector(confirm_password_selector, timeout=5000)
                await page.fill(confirm_password_selector, account.password)
                
                if self.on_log_message:
                    self.on_log_message(tr("Filled confirm password"))
                
            except Exception as e:
                raise Exception(f"Failed to fill confirm password: {str(e)}")
            
            # Step 6: Check registration terms agreement
            try:
                terms_checkbox_selector = '/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input'
                await page.wait_for_selector(terms_checkbox_selector, timeout=5000)
                await page.check(terms_checkbox_selector)
                
                if self.on_log_message:
                    self.on_log_message(tr("Checked terms agreement"))
                
            except Exception as e:
                raise Exception(f"Failed to check terms agreement: {str(e)}")
            
            # Step 7: Click confirm registration button
            try:
                account.mark_processing(tr("Submitting registration"))
                confirm_btn_selector = '/html/body/div[9]/div[2]/div/div/div/form/div[3]/input'
                await page.wait_for_selector(confirm_btn_selector, timeout=5000)
                await page.click(confirm_btn_selector)
                
                if self.on_log_message:
                    self.on_log_message(tr("Clicked registration confirm button"))
                
            except Exception as e:
                raise Exception(f"Failed to click registration button: {str(e)}")
            
            # Step 8: Wait and verify success by checking logout link
            try:
                account.mark_processing(tr("Verifying registration success"))
                logout_link_selector = '/html/body/div[1]/div/span[2]/a[2]'
                
                # Wait for registration processing (up to 30 seconds)
                await page.wait_for_selector(logout_link_selector, timeout=30000)
                
                # Check if logout link contains [退出] text
                logout_element = await page.query_selector(logout_link_selector)
                if logout_element:
                    logout_text = await logout_element.text_content()
                    if logout_text and '[退出]' in logout_text:
                        # Registration successful
                        success_note = tr("Account registered successfully and automatically logged in")
                        account.mark_success(success_note)
                        if self.on_log_message:
                            self.on_log_message(tr("SUCCESS: %1 registered and logged in").replace("%1", account.username))
                        return True
                    else:
                        raise Exception(f"Logout link found but doesn't contain [退出]: {logout_text}")
                else:
                    raise Exception("Logout link element not found after registration")
                    
            except Exception as e:
                # Registration might have failed or requires verification
                error_msg = f"Registration verification failed: {str(e)}"
                account.mark_failed(error_msg)
                if self.on_log_message:
                    self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
                return False
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}"
            account.mark_failed(error_msg)
            if self.on_log_message:
                self.on_log_message(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
            return False
        finally:
            # Close the page
            if page:
                try:
                    await page.close()
                except:
                    pass
    
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