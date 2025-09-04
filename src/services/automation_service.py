"""
Compatibility layer for the refactored automation service

This module provides backward compatibility with the existing codebase
by exposing the same interface as the original automation_service.py
while using the new modular backend architecture internally.
"""

# Import the new modular components
from .automation.automation_service import AutomationService as _AutomationService
from .automation.automation_service import AutomationBackendType

# Import types and exceptions for compatibility
from ..models.account import Account, AccountStatus
from ..exceptions import (
    AutomationError, BrowserInitializationError, ElementNotFoundError,
    PageNavigationError, FormInteractionError, RegistrationFailureError,
    TimeoutError, NetworkError, CaptchaRequiredError, AccountAlreadyExistsError,
    InvalidCredentialsError, RateLimitError
)


class AutomationService(_AutomationService):
    """
    Backward-compatible AutomationService that wraps the new modular implementation
    
    This class maintains the same API as the original AutomationService while
    using the new backend architecture internally.
    """
    
    def __init__(self, backend: AutomationBackendType = "playwright"):
        """
        Initialize AutomationService with backward compatibility
        
        Args:
            backend: Automation backend to use ('playwright' or 'selenium')
        """
        super().__init__(backend)
        
        # Maintain compatibility with original property names
        self.backend = backend  # Keep this for compatibility
        self.success_rate = 0.8
    
    # Maintain compatibility methods that may be expected by existing code
    def get_backend(self) -> AutomationBackendType:
        """Get the current automation backend (compatibility method)"""
        return self.get_backend_name()
    
    def is_selenium_available(self) -> bool:
        """Check if selenium is available (compatibility method)"""
        return self.is_backend_available("selenium")


# Re-export everything needed for compatibility
__all__ = [
    'AutomationService',
    'AutomationBackendType',
    'Account',
    'AccountStatus',
    'AutomationError',
    'BrowserInitializationError',
    'ElementNotFoundError',
    'PageNavigationError', 
    'FormInteractionError',
    'RegistrationFailureError',
    'TimeoutError',
    'NetworkError',
    'CaptchaRequiredError',
    'AccountAlreadyExistsError',
    'InvalidCredentialsError',
    'RateLimitError'
]