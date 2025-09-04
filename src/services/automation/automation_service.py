"""
Automation service coordinator

Simplified coordination service that manages automation backends and handles
batch processing workflow. This service focuses purely on orchestration
rather than implementation details.
"""

import logging
from typing import Callable, Optional, Literal, Union
from ...models.account import Account, AccountStatus
from ...translation_manager import tr
from .base_backend import AutomationBackend
from .simple_playwright_backend import SimplePlaywrightBackend
from .selenium_backend import SeleniumBackend

# Type alias for automation backend
AutomationBackendType = Literal["simple_playwright", "selenium"]


class BackendFactory:
    """Factory for creating automation backends"""
    
    @staticmethod
    def create_backend(backend_type: AutomationBackendType) -> AutomationBackend:
        """Create an automation backend instance"""
        if backend_type == "simple_playwright":
            return SimplePlaywrightBackend()
        elif backend_type == "selenium":
            return SeleniumBackend()
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
    
    @staticmethod
    def get_available_backends() -> list[AutomationBackendType]:
        """Get list of available backends"""
        available = []
        
        # Check Simple Playwright (transitions framework) - preferred
        try:
            backend = SimplePlaywrightBackend()
            if backend.is_available():
                available.append("simple_playwright")
        except Exception:
            pass
        
        # Check Selenium
        try:
            backend = SeleniumBackend()
            if backend.is_available():
                available.append("selenium")
        except Exception:
            pass
        
        return available


class CallbackManager:
    """Manages callbacks for UI updates"""
    
    def __init__(self):
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


class AutomationService:
    """
    Automation service coordinator
    
    Simplified service that focuses on batch processing workflow control
    and backend lifecycle management. All automation implementation details
    are delegated to specific backend implementations.
    """
    
    def __init__(self, backend_type: AutomationBackendType = "simple_playwright"):
        """Initialize automation service with specified backend"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # State management
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        self.success_rate = 0.8  # For simulation mode
        
        # Backend management - prefer state machine backend
        self._backend_type = backend_type
        self._backend: Optional[AutomationBackend] = None
        
        # Callback management
        self._callbacks = CallbackManager()
        
        # Error tracking
        self.error_log = []
        
        # Initialize backend
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the automation backend"""
        try:
            self._backend = BackendFactory.create_backend(self._backend_type)
            self._backend.set_log_callback(self._log_message)
            self._log_message(tr("Backend initialized: %1").replace("%1", self._backend_type))
        except Exception as e:
            error_msg = f"Failed to initialize {self._backend_type} backend: {str(e)}"
            self.logger.error(error_msg)
            self._log_message(tr("ERROR: %1").replace("%1", error_msg))
            raise
    
    def _log_message(self, message: str):
        """Internal logging and callback"""
        self.logger.info(message)
        if self._callbacks.on_log_message:
            self._callbacks.on_log_message(message)
    
    # Backend management methods
    def get_backend_name(self) -> str:
        """Get the current backend name"""
        return self._backend.get_backend_name() if self._backend else self._backend_type
    
    def set_backend(self, backend_type: AutomationBackendType):
        """Switch to a different backend"""
        if self.is_running:
            raise ValueError("Cannot change backend while automation is running")
        
        if backend_type == self._backend_type:
            return  # No change needed
        
        # Cleanup old backend
        if self._backend:
            try:
                self._backend.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up old backend: {e}")
        
        # Initialize new backend
        self._backend_type = backend_type
        self._initialize_backend()
        
        self._log_message(tr("Backend switched to: %1").replace("%1", backend_type))
    
    def get_available_backends(self) -> list[AutomationBackendType]:
        """Get list of available backends"""
        return BackendFactory.get_available_backends()
    
    def is_backend_available(self, backend_type: AutomationBackendType) -> bool:
        """Check if a backend is available"""
        return backend_type in self.get_available_backends()
    
    # Callback management
    def set_callbacks(self, 
                     on_account_start: Callable[[Account], None] = None,
                     on_account_complete: Callable[[Account], None] = None,
                     on_batch_complete: Callable[[int, int], None] = None,
                     on_log_message: Callable[[str], None] = None):
        """Set callback functions for UI updates"""
        self._callbacks.set_callbacks(on_account_start, on_account_complete, 
                                     on_batch_complete, on_log_message)
    
    # Batch processing control methods
    def start_batch_registration(self, accounts: list[Account]) -> bool:
        """Start batch registration process"""
        if self.is_running:
            return False
        
        self.is_running = True
        self.is_paused = False
        
        # Determine starting point
        all_queued = all(account.status == AccountStatus.QUEUED for account in accounts)
        
        if all_queued:
            self.current_account_index = 0
            self._log_message(tr("Started fresh batch processing for %1 accounts").replace("%1", str(len(accounts))))
        else:
            # Resume from first queued account
            self.current_account_index = 0
            for i, account in enumerate(accounts):
                if account.status == AccountStatus.QUEUED:
                    self.current_account_index = i
                    break
            else:
                # No queued accounts, find first non-success
                for i, account in enumerate(accounts):
                    if account.status not in [AccountStatus.SUCCESS]:
                        self.current_account_index = i
                        if account.status in [AccountStatus.PROCESSING, AccountStatus.FAILED]:
                            account.reset_status()
                        break
                else:
                    # All successful
                    self.is_running = False
                    self._log_message(tr("All accounts already processed successfully"))
                    return False
            
            self._log_message(tr("Resuming batch processing from account %1").replace("%1", str(self.current_account_index + 1)))
        
        return True
    
    def pause_registration(self) -> bool:
        """Pause/resume the registration process"""
        if not self.is_running:
            return False
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self._log_message(tr("Processing paused"))
        else:
            self._log_message(tr("Processing resumed"))
        
        return True
    
    def stop_registration(self, accounts: list[Account]) -> bool:
        """Stop the registration process"""
        if not self.is_running:
            return False
        
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        
        # Reset any processing accounts
        for account in accounts:
            if account.status == AccountStatus.PROCESSING:
                account.reset_status()
        
        # Cleanup backend resources
        if self._backend:
            try:
                self._backend.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during backend cleanup: {e}")
        
        self._log_message(tr("Processing stopped"))
        return True
    
    def process_next_account(self, accounts: list[Account]) -> bool:
        """Process the next account in the queue"""
        if not self.is_running or self.is_paused:
            return True
        
        if self.current_account_index >= len(accounts):
            self._complete_batch_processing(accounts)
            return False
        
        # Get current account
        account = accounts[self.current_account_index]
        
        # Mark as processing and notify
        account.mark_processing()
        
        if self._callbacks.on_account_start:
            self._callbacks.on_account_start(account)
        
        self._log_message(tr("Processing account: %1").replace("%1", account.username))
        
        # Process account through backend
        try:
            import asyncio
            success = asyncio.run(self._backend.register_account(account))
        except Exception as e:
            self.logger.error(f"Backend registration error: {e}")
            account.mark_failed(f"Backend error: {str(e)}")
            success = False
        
        # Notify completion
        if self._callbacks.on_account_complete:
            self._callbacks.on_account_complete(account)
        
        return True
    
    def complete_current_account(self, accounts: list[Account]):
        """Complete processing of current account and move to next"""
        if self.current_account_index < len(accounts):
            self.current_account_index += 1
    
    def _complete_batch_processing(self, accounts: list[Account]):
        """Complete the batch processing"""
        self.is_running = False
        self.is_paused = False
        
        # Calculate statistics
        success_count = len([acc for acc in accounts if acc.status == AccountStatus.SUCCESS])
        failed_count = len([acc for acc in accounts if acc.status == AccountStatus.FAILED])
        
        self._log_message(tr("Batch processing completed!"))
        
        if self._callbacks.on_batch_complete:
            self._callbacks.on_batch_complete(success_count, failed_count)
    
    # Progress tracking
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
    
    # Single account registration
    async def register_single_account(self, account: Account) -> bool:
        """Register a single account with full callback support"""
        if not self._backend:
            account.mark_failed("No backend available")
            return False
        
        try:
            # Notify start of account processing
            if self._callbacks.on_account_start:
                self._callbacks.on_account_start(account)
            
            self._log_message(f"Starting registration for: {account.username}")
            
            # Register account through backend
            success = await self._backend.register_account(account)
            
            # Log result
            if success:
                self._log_message(f"Registration successful for: {account.username}")
            else:
                self._log_message(f"Registration failed for: {account.username} - {account.notes}")
            
            # Notify completion
            if self._callbacks.on_account_complete:
                self._callbacks.on_account_complete(account)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Single account registration error: {e}")
            error_msg = f"Registration error: {str(e)}"
            account.mark_failed(error_msg)
            self._log_message(f"Registration error for {account.username}: {error_msg}")
            
            # Notify completion even on error
            if self._callbacks.on_account_complete:
                self._callbacks.on_account_complete(account)
            
            return False
    
    # Error management
    def get_error_log(self) -> list[dict]:
        """Get the error log for debugging"""
        return self.error_log.copy()
    
    def clear_error_log(self):
        """Clear the error log"""
        self.error_log.clear()
    
    # Simulation settings (for testing)
    def set_success_rate(self, rate: float):
        """Set success rate for simulation"""
        if 0.0 <= rate <= 1.0:
            self.success_rate = rate
    
    # Cleanup
    def cleanup(self):
        """Cleanup service resources"""
        if self._backend:
            try:
                self._backend.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during service cleanup: {e}")
        
        self.is_running = False
        self.is_paused = False