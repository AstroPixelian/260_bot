"""
Custom exceptions for automation service error handling
"""

from typing import Optional


class AutomationError(Exception):
    """Base exception class for all automation-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AUTOMATION_ERROR"
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} (Code: {self.error_code}, Details: {self.details})"
        return f"{self.message} (Code: {self.error_code})"


class BrowserInitializationError(AutomationError):
    """Exception raised when browser initialization fails"""
    
    def __init__(self, message: str, backend: str = "unknown", details: Optional[dict] = None):
        super().__init__(message, "BROWSER_INIT_ERROR", details)
        self.backend = backend


class ElementNotFoundError(AutomationError):
    """Exception raised when a required element cannot be found on the page"""
    
    def __init__(self, selector: str, element_type: str = "element", timeout: Optional[int] = None):
        message = f"Could not find {element_type} with selector: {selector}"
        if timeout:
            message += f" (timeout: {timeout}s)"
        
        details = {
            "selector": selector,
            "element_type": element_type,
            "timeout": timeout
        }
        super().__init__(message, "ELEMENT_NOT_FOUND", details)
        self.selector = selector
        self.element_type = element_type
        self.timeout = timeout


class PageNavigationError(AutomationError):
    """Exception raised when page navigation fails"""
    
    def __init__(self, url: str, attempts: int = 1, last_error: Optional[str] = None):
        message = f"Failed to navigate to {url}"
        if attempts > 1:
            message += f" after {attempts} attempts"
        
        details = {
            "url": url,
            "attempts": attempts,
            "last_error": last_error
        }
        super().__init__(message, "NAVIGATION_ERROR", details)
        self.url = url
        self.attempts = attempts
        self.last_error = last_error


class FormInteractionError(AutomationError):
    """Exception raised when form interaction fails"""
    
    def __init__(self, action: str, field: str, details: Optional[dict] = None):
        message = f"Failed to {action} on field: {field}"
        error_details = {"action": action, "field": field}
        if details:
            error_details.update(details)
        
        super().__init__(message, "FORM_INTERACTION_ERROR", error_details)
        self.action = action
        self.field = field


class RegistrationFailureError(AutomationError):
    """Exception raised when registration fails with specific reasons"""
    
    def __init__(self, reason: str, failure_type: str = "unknown", details: Optional[dict] = None):
        message = f"Registration failed: {reason}"
        error_details = {
            "reason": reason,
            "failure_type": failure_type
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, "REGISTRATION_FAILURE", error_details)
        self.reason = reason
        self.failure_type = failure_type


class TimeoutError(AutomationError):
    """Exception raised when operations timeout"""
    
    def __init__(self, operation: str, timeout: int, details: Optional[dict] = None):
        message = f"Operation '{operation}' timed out after {timeout} seconds"
        error_details = {
            "operation": operation,
            "timeout": timeout
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, "TIMEOUT_ERROR", error_details)
        self.operation = operation
        self.timeout = timeout


class NetworkError(AutomationError):
    """Exception raised when network-related errors occur"""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None):
        error_details = {}
        if url:
            error_details["url"] = url
        if status_code:
            error_details["status_code"] = status_code
        
        super().__init__(message, "NETWORK_ERROR", error_details)
        self.url = url
        self.status_code = status_code


class CaptchaRequiredError(AutomationError):
    """Exception raised when captcha verification is required"""
    
    def __init__(self, captcha_type: str = "unknown"):
        message = f"Captcha verification required: {captcha_type}"
        details = {"captcha_type": captcha_type}
        
        super().__init__(message, "CAPTCHA_REQUIRED", details)
        self.captcha_type = captcha_type


class AccountAlreadyExistsError(RegistrationFailureError):
    """Exception raised when account already exists"""
    
    def __init__(self, username: str, detected_message: Optional[str] = None):
        reason = f"Username '{username}' already exists"
        if detected_message:
            reason += f" (detected: {detected_message})"
        
        details = {
            "username": username,
            "detected_message": detected_message
        }
        
        super().__init__(reason, "account_exists", details)
        self.username = username
        self.detected_message = detected_message


class InvalidCredentialsError(RegistrationFailureError):
    """Exception raised when credentials are invalid"""
    
    def __init__(self, field: str, reason: str):
        message = f"Invalid {field}: {reason}"
        details = {
            "field": field,
            "validation_reason": reason
        }
        
        super().__init__(message, "invalid_credentials", details)
        self.field = field
        self.validation_reason = reason


class RateLimitError(AutomationError):
    """Exception raised when rate limits are exceeded"""
    
    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        
        details = {"retry_after": retry_after}
        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.retry_after = retry_after