"""
Form interaction helpers for automation backends

Provides common utilities for finding elements, filling forms, and handling interactions
that are shared across different automation backends.
"""

from typing import List, Tuple, Any
import asyncio
from ...models.account import Account
from ...exceptions import ElementNotFoundError, FormInteractionError


class FormSelectors:
    """Common form selectors for 360.cn registration"""
    
    REGISTRATION_BUTTONS = [
        '.quc-link-sign-up',  # 360.cn 实际使用的注册按钮类名
        '.wan-register-btn',
        'text="免费注册"',
        'text="注册"', 
        'a[data-bk="wan-public-reg"]',
        'text="立即注册"',
        'a[href*="register"]',
        'xpath=/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]'
    ]
    
    REGISTRATION_FORMS = [
        'xpath=/html/body/div[9]/div[2]/div/div/div/form',
        '.modal form',
        '.popup form', 
        '.register-form',
        'form[action*="register"]',
        'form input[name="username"]',
        'form input[placeholder*="用户名"]',
        'form input[placeholder*="账号"]'
    ]
    
    USERNAME_FIELDS = [
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
    
    PASSWORD_FIELDS = [
        'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[2]/div/div/input',
        'input[name="password"]',
        'input[placeholder*="密码"]',
        'input[placeholder*="Password"]',
        'input[type="password"]:first-of-type',
        '#password',
        '.password',
        'form input[type="password"]'
    ]
    
    CONFIRM_PASSWORD_FIELDS = [
        'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[1]/div/div[3]/div/div/input',
        'input[name="confirm_password"]',
        'input[name="password_confirm"]',
        'input[placeholder*="再次输入"]',
        'input[placeholder*="确认密码"]',
        'form input[type="password"]:last-of-type'
    ]
    
    TERMS_CHECKBOXES = [
        'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[2]/label/input',
        'input[type="checkbox"]',
        '.terms input[type="checkbox"]',
        '.agreement input[type="checkbox"]',
        'label input[type="checkbox"]'
    ]
    
    SUBMIT_BUTTONS = [
        'xpath=/html/body/div[9]/div[2]/div/div/div/form/div[3]/input',
        'input[type="submit"]',
        'button[type="submit"]',
        '.submit-btn',
        '.confirm-btn',
        'input[value*="注册"]',
        'button:contains("注册")'
    ]


class RetryHelper:
    """Helper for retry operations"""
    
    @staticmethod
    async def retry_async(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
        """Retry an async function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(delay * (2 ** attempt))
    
    @staticmethod
    def retry_sync(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
        """Retry a sync function with exponential backoff"""
        import time
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(delay * (2 ** attempt))