"""
Automation service for batch account registration
"""

import random
import asyncio
from typing import Callable, Optional
from models.account import Account, AccountStatus
from translation_manager import tr


class AutomationService:
    """Service for automated account registration"""
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_account_index = 0
        self.success_rate = 0.8  # 80% success rate for simulation
        
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
            self.on_log_message(tr("Started batch processing for %1 accounts").arg(len(accounts)))
        
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
            self.on_log_message(tr("Processing account: %1").arg(account.username))
        
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
                self.on_log_message(tr("SUCCESS: %1 registered successfully").arg(account.username))
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
                self.on_log_message(tr("FAILED: %1 - %2").arg(account.username, reason))
        
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