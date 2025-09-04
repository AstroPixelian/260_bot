"""
Automation service module for batch account registration

This module provides a clean separation between different automation backends
(Playwright, Selenium) while maintaining a unified interface.
"""

from .automation_service import AutomationService
from .base_backend import AutomationBackend
from .playwright_backend import PlaywrightBackend
from .selenium_backend import SeleniumBackend

__all__ = [
    'AutomationService',
    'AutomationBackend', 
    'PlaywrightBackend',
    'SeleniumBackend'
]