"""
Abstract base class for automation backends

Defines the common interface that all automation backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from ...models.account import Account


class AutomationBackend(ABC):
    """Abstract base class for automation backends"""
    
    def __init__(self):
        """Initialize the backend"""
        self.on_log_message: Optional[Callable[[str], None]] = None
        
    def set_log_callback(self, callback: Optional[Callable[[str], None]]):
        """Set the logging callback function"""
        self.on_log_message = callback
        
    def _log(self, message: str):
        """Internal logging helper"""
        if self.on_log_message:
            self.on_log_message(message)
    
    @abstractmethod
    async def register_account(self, account: Account) -> bool:
        """
        Register a single account
        
        Args:
            account: Account to register
            
        Returns:
            True if registration successful, False otherwise
        """
        pass
        
    @abstractmethod
    def cleanup(self):
        """Clean up backend resources"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available on the system"""
        pass
        
    @abstractmethod
    def get_backend_name(self) -> str:
        """Get the name of this backend"""
        pass