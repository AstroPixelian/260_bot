"""
Selenium backend implementation for automation

Handles all Selenium/undetected_chromedriver specific browser automation logic for account registration.
"""

import time
import logging
from typing import Optional

from .base_backend import AutomationBackend
from .form_helpers import FormSelectors, RetryHelper
from .result_detector import RegistrationResultDetector
from ...models.account import Account, AccountStatus
from ...translation_manager import tr
from ...exceptions import (
    BrowserInitializationError, RegistrationFailureError,
    AccountAlreadyExistsError
)

# Import selenium dependencies
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
    uc = None
    By = None
    WebDriverWait = None
    EC = None
    ActionChains = None
    TimeoutException = None
    NoSuchElementException = None
    WebDriverException = None


class SeleniumBackend(AutomationBackend):
    """Selenium/undetected_chromedriver automation backend"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.selenium_driver: Optional[object] = None
        
        if not SELENIUM_AVAILABLE:
            raise BrowserInitializationError(
                "Selenium backend requested but undetected_chromedriver is not available. "
                "Install it with: pip install undetected-chromedriver",
                backend="selenium",
                details={"selenium_available": SELENIUM_AVAILABLE}
            )
    
    def get_backend_name(self) -> str:
        return "selenium"
    
    def is_available(self) -> bool:
        """Check if Selenium/undetected_chromedriver is available"""
        return SELENIUM_AVAILABLE
    
    async def register_account(self, account: Account) -> bool:
        """Register a single account using Selenium automation"""
        # Selenium backend is synchronous, so we implement this directly
        return self._register_account_sync(account)
    
    def _register_account_sync(self, account: Account) -> bool:
        """Synchronous account registration implementation"""
        self.logger.debug(f"Starting selenium registration for: {account.username}")
        
        if not self._initialize_selenium_driver():
            account.mark_failed("Failed to initialize selenium driver")
            return False
        
        try:
            # Mark account as processing
            account.mark_processing(tr("Initializing browser for registration"))
            self._log(tr("Starting registration for: %1").replace("%1", account.username))
            
            # Step 1: Navigate to 360.cn with retry logic
            account.mark_processing(tr("Navigating to 360.cn"))
            self._navigate_with_retry('https://wan.360.cn/', max_retries=3)
            self._log(tr("Navigated to 360.cn"))
            
            # Wait for page to load completely
            time.sleep(5)
            
            # Step 2: Click registration button
            account.mark_processing(tr("Opening registration form"))
            self._click_registration_button()
            self._log(tr("Clicked registration button"))
            
            # Wait for registration form
            self._wait_for_registration_form()
            time.sleep(2)
            
            # Step 3-6: Fill form fields
            account.mark_processing(tr("Filling registration form"))
            
            self._fill_username_field(account.username)
            self._log(tr("Filled username: %1").replace("%1", account.username))
            
            self._fill_password_field(account.password)
            self._log(tr("Filled password"))
            
            self._fill_confirm_password_field(account.password)
            self._log(tr("Filled confirm password"))
            
            self._check_terms_agreement()
            self._log(tr("Checked terms agreement"))
            
            # Step 7: Submit form
            account.mark_processing(tr("Submitting registration"))
            self._click_submit_button()
            self._log(tr("Clicked registration confirm button"))
            
            time.sleep(3)  # Wait for submission processing
            
            # Step 8: Verify result using selenium-specific method
            account.mark_processing(tr("Verifying registration result"))
            self._verify_registration_success(account)
            
            return account.status == AccountStatus.SUCCESS
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            account.mark_failed(error_msg)
            self._log(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))
            return False
        finally:
            # Always cleanup selenium driver after registration attempt
            self._cleanup_selenium_driver()
    
    def _initialize_selenium_driver(self) -> bool:
        """Initialize undetected_chromedriver instance"""
        try:
            self._log(tr("DEBUG: Starting selenium driver initialization"))
            
            if not self.selenium_driver:
                # Configure Chrome options for anti-detection
                options = uc.ChromeOptions()
                
                # Add anti-detection arguments
                anti_detection_args = [
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
                    '--disable-ipc-flooding-protection',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--force-color-profile=srgb',
                    '--metrics-recording-only',
                    '--use-mock-keychain',
                    '--disable-background-networking',
                    '--window-size=1280,720'
                ]
                
                for arg in anti_detection_args:
                    options.add_argument(arg)
                
                # Create the undetected Chrome driver
                self.selenium_driver = uc.Chrome(
                    options=options,
                    headless=False,
                    use_subprocess=True,
                    suppress_welcome=True
                )
                
                self._log(tr("DEBUG: Undetected Chrome driver created successfully"))
            
            self._log(tr("Selenium driver initialized successfully"))
            return True
            
        except Exception as e:
            error_msg = f"Selenium driver initialization failed: {str(e)}"
            self._log(tr("ERROR: %1").replace("%1", error_msg))
            return False
    
    def _cleanup_selenium_driver(self):
        """Clean up selenium driver resources"""
        try:
            if self.selenium_driver:
                self._log(tr("DEBUG: Closing selenium driver"))
                self.selenium_driver.quit()
                self.selenium_driver = None
                self._log(tr("DEBUG: Selenium driver closed"))
            
            self._log(tr("Selenium driver resources cleaned up"))
        except Exception as e:
            error_msg = f"Selenium driver cleanup error: {str(e)}"
            self._log(tr("WARNING: %1").replace("%1", error_msg))
    
    def cleanup(self):
        """Clean up backend resources"""
        self._cleanup_selenium_driver()
    
    # Helper methods for form interaction using Selenium
    def _navigate_with_retry(self, url: str, max_retries: int = 3):
        """Navigate to URL with retry logic"""
        for attempt in range(max_retries):
            try:
                self._log(tr("DEBUG: Navigation attempt %1/%2").replace("%1", str(attempt + 1)).replace("%2", str(max_retries)))
                
                self.selenium_driver.get(url)
                
                # Wait for page to load
                WebDriverWait(self.selenium_driver, 60).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                return
                
            except Exception as e:
                if attempt < max_retries - 1:
                    self._log(tr("DEBUG: Navigation attempt %1 failed: %2, retrying...").replace("%1", str(attempt + 1)).replace("%2", str(e)))
                    time.sleep(2)
                    continue
                else:
                    raise Exception(f"Failed to navigate to {url} after {max_retries} attempts: {str(e)}")
    
    def _click_registration_button(self):
        """Click registration button using multiple selector strategies"""
        selenium_selectors = [
            (By.CSS_SELECTOR, '.quc-link-sign-up'),
            (By.CSS_SELECTOR, '.wan-register-btn'),
            (By.CSS_SELECTOR, 'a[data-bk="wan-public-reg"]'),
            (By.LINK_TEXT, '免费注册'),
            (By.LINK_TEXT, '注册'),
            (By.LINK_TEXT, '立即注册'),
            (By.CSS_SELECTOR, 'a[href*="register"]'),
            (By.XPATH, '/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'),
        ]
        
        for by, selector in selenium_selectors:
            try:
                elements = self.selenium_driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        return
            except Exception:
                continue
        
        raise Exception("Could not find or click any registration button")
    
    def _wait_for_registration_form(self):
        """Wait for registration form to appear"""
        modal_selectors = [
            (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form'),
            (By.CSS_SELECTOR, '.modal form'),
            (By.CSS_SELECTOR, '.popup form'),
            (By.CSS_SELECTOR, '.register-form'),
        ]
        
        for by, selector in modal_selectors:
            try:
                WebDriverWait(self.selenium_driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                return
            except TimeoutException:
                continue
    
    def _fill_username_field(self, username: str):
        """Fill username field using multiple selector strategies"""
        username_selectors = [
            (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[1]/div/div/input'),
            (By.NAME, 'username'),
            (By.CSS_SELECTOR, 'input[placeholder*="用户名"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="账号"]'),
            (By.CSS_SELECTOR, 'form input[type="text"]:first-of-type'),
        ]
        
        for by, selector in username_selectors:
            try:
                elements = self.selenium_driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed():
                        element.clear()
                        element.send_keys(username)
                        return
            except Exception:
                continue
        
        raise Exception("Could not find or fill username field")
    
    def _fill_password_field(self, password: str):
        """Fill password field"""
        password_selectors = [
            (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[2]/div/div/input'),
            (By.NAME, 'password'),
            (By.CSS_SELECTOR, 'input[placeholder*="密码"]'),
            (By.CSS_SELECTOR, 'input[type="password"]:first-of-type'),
        ]
        
        for by, selector in password_selectors:
            try:
                elements = self.selenium_driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed():
                        element.clear()
                        element.send_keys(password)
                        return
            except Exception:
                continue
        
        raise Exception("Could not find or fill password field")
    
    def _fill_confirm_password_field(self, password: str):
        """Fill confirm password field"""
        confirm_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input')
        
        try:
            element = WebDriverWait(self.selenium_driver, 5).until(
                EC.element_to_be_clickable(confirm_selector)
            )
            element.clear()
            element.send_keys(password)
        except Exception as e:
            raise Exception(f"Failed to fill confirm password: {str(e)}")
    
    def _check_terms_agreement(self):
        """Check terms agreement checkbox"""
        terms_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input')
        
        try:
            element = WebDriverWait(self.selenium_driver, 5).until(
                EC.element_to_be_clickable(terms_selector)
            )
            if not element.is_selected():
                element.click()
        except Exception as e:
            raise Exception(f"Failed to check terms agreement: {str(e)}")
    
    def _click_submit_button(self):
        """Click submit button"""
        submit_selector = (By.XPATH, '/html/body/div[9]/div[2]/div/div/div/form/div[3]/input')
        
        try:
            element = WebDriverWait(self.selenium_driver, 5).until(
                EC.element_to_be_clickable(submit_selector)
            )
            element.click()
        except Exception as e:
            raise Exception(f"Failed to click registration button: {str(e)}")
    
    def _verify_registration_success(self, account: Account):
        """Verify registration success by checking for logout link"""
        logout_selector = (By.XPATH, '/html/body/div[1]/div/span[2]/a[2]')
        
        try:
            # Wait for registration processing (up to 30 seconds)
            element = WebDriverWait(self.selenium_driver, 30).until(
                EC.presence_of_element_located(logout_selector)
            )
            
            # Check if logout link contains [退出] text
            logout_text = element.text
            
            if logout_text and '[退出]' in logout_text:
                # Registration successful
                success_note = tr("Account registered successfully and automatically logged in")
                account.mark_success(success_note)
                self._log(tr("SUCCESS: %1 registered and logged in").replace("%1", account.username))
            else:
                raise Exception(f"Logout link found but doesn't contain [退出]: {logout_text}")
                
        except Exception as e:
            # Registration might have failed or requires verification
            error_msg = f"Registration verification failed: {str(e)}"
            account.mark_failed(error_msg)
            self._log(tr("FAILED: %1 - %2").replace("%1", account.username).replace("%2", error_msg))