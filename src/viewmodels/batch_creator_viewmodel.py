"""
Main ViewModel for the Batch Account Creator application
"""

from typing import List, Callable, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

from ..models.account import Account, AccountStatus
from ..services.data_service import DataService
from ..services.automation_service import AutomationService
from ..services.account_service import AccountService
from ..translation_manager import tr, get_translation_manager, init_translation_manager


class BatchCreatorViewModel(QObject):
    """Main ViewModel for managing application state and business logic"""
    
    # Signals for UI updates
    accounts_changed = Signal()
    statistics_changed = Signal()
    processing_status_changed = Signal()
    log_message = Signal(str)
    account_processing_started = Signal(Account)
    account_processing_completed = Signal(Account)
    batch_processing_completed = Signal(int, int)  # success_count, failed_count
    language_changed = Signal(str)  # New signal for language changes
    
    def __init__(self):
        super().__init__()
        
        # Services
        self.data_service = DataService()
        self.automation_service = AutomationService()
        self.account_service = AccountService()  # New account service
        
        # Timer for processing simulation
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._process_next_account_step)
        
        # Setup automation service callbacks
        self.automation_service.set_callbacks(
            on_account_start=self._on_account_start,
            on_account_complete=self._on_account_complete,
            on_batch_complete=self._on_batch_complete,
            on_log_message=self._on_log_message
        )
        
        # Initial log message
        self._on_log_message(tr("Application started - Ready to import or generate accounts"))
    
    # Properties
    @property
    def accounts(self) -> List[Account]:
        """Get all accounts"""
        return self.data_service.get_accounts()
    
    @property
    def statistics(self) -> dict:
        """Get account statistics"""
        return self.data_service.get_statistics()
    
    @property
    def is_processing(self) -> bool:
        """Check if batch processing is running"""
        return self.automation_service.is_running
    
    @property
    def is_paused(self) -> bool:
        """Check if processing is paused"""
        return self.automation_service.is_paused
    
    # Data operations
    def import_accounts_from_csv(self, file_path: str) -> bool:
        """
        Import accounts from CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            count = self.data_service.import_from_csv(file_path)
            self.accounts_changed.emit()
            self.statistics_changed.emit()
            self._on_log_message(tr("Successfully imported %1 accounts from CSV").replace("%1", str(count)))
            return True
        
        except Exception as e:
            self._on_log_message(tr("Failed to import CSV: %1").replace("%1", str(e)))
            return False
    
    def generate_random_accounts(self, count: int) -> bool:
        """
        Generate random test accounts using AccountService
        
        Args:
            count: Number of accounts to generate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if count <= 0 or count > 1000:
                self._on_log_message(tr("Invalid account count: %1").replace("%1", str(count)))
                return False
            
            # Use AccountService for better account generation
            generated_accounts = self.account_service.generate_random_accounts(count)
            
            # Add generated accounts to DataService for storage
            self.data_service.add_accounts(generated_accounts)
            
            # Emit signals to update UI
            self.accounts_changed.emit()
            self.statistics_changed.emit()
            self._on_log_message(tr("Generated %1 random accounts with realistic usernames").replace("%1", str(len(generated_accounts))))
            return True
        
        except Exception as e:
            self._on_log_message(tr("Failed to generate accounts: %1").replace("%1", str(e)))
            return False
    
    def export_accounts_to_csv(self, file_path: str, include_results: bool = True) -> bool:
        """
        Export accounts to CSV file
        
        Args:
            file_path: Output file path
            include_results: Whether to include status and notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.data_service.export_to_csv(file_path, include_results)
            if success:
                self._on_log_message(tr("Results exported to: %1").replace("%1", file_path))
            return success
        
        except Exception as e:
            self._on_log_message(tr("Failed to export results: %1").replace("%1", str(e)))
            return False
    
    def clear_accounts(self):
        """Clear all accounts"""
        self.data_service.clear_accounts()
        self.accounts_changed.emit()
        self.statistics_changed.emit()
        self._on_log_message(tr("All accounts cleared"))
    
    # Processing operations
    def start_batch_processing(self) -> bool:
        """
        Start batch registration process
        
        Returns:
            True if started successfully, False otherwise
        """
        accounts = self.data_service.get_accounts()
        if not accounts:
            self._on_log_message(tr("No accounts to process"))
            return False
        
        # Validate accounts before starting
        validation_errors = self.data_service.validate_accounts()
        if validation_errors:
            self._on_log_message(tr("Validation errors found:"))
            for error in validation_errors[:5]:  # Show first 5 errors
                self._on_log_message(f"  - {error}")
            return False
        
        success = self.automation_service.start_batch_registration(accounts)
        if success:
            self.processing_timer.start(1500)  # Process every 1.5 seconds
            self.processing_status_changed.emit()
            self.statistics_changed.emit()
        
        return success
    
    def pause_batch_processing(self) -> bool:
        """
        Pause or resume batch processing
        
        Returns:
            True if successful, False otherwise
        """
        success = self.automation_service.pause_registration()
        if success:
            if self.automation_service.is_paused:
                self.processing_timer.stop()
            else:
                self.processing_timer.start()
            self.processing_status_changed.emit()
        
        return success
    
    def stop_batch_processing(self) -> bool:
        """
        Stop batch processing
        
        Returns:
            True if successful, False otherwise
        """
        accounts = self.data_service.get_accounts()
        success = self.automation_service.stop_registration(accounts)
        if success:
            self.processing_timer.stop()
            self.processing_status_changed.emit()
            self.accounts_changed.emit()
            self.statistics_changed.emit()
        
        return success
    
    # Utility methods
    def validate_accounts(self) -> List[str]:
        """
        Validate all accounts
        
        Returns:
            List of validation error messages
        """
        return self.data_service.validate_accounts()
    
    def reset_all_accounts(self):
        """Reset all accounts to queued status"""
        self.data_service.reset_all_accounts()
        self.accounts_changed.emit()
        self.statistics_changed.emit()
        self._on_log_message(tr("All accounts reset to queued status"))
    
    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """Get account by ID"""
        return self.data_service.get_account_by_id(account_id)
    
    def copy_text_to_clipboard(self, text: str):
        """Copy text to system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    # Language management
    def get_current_language(self) -> str:
        """Get current language locale"""
        translation_manager = get_translation_manager()
        if translation_manager is None:
            return "zh-CN"  # Default language
        return translation_manager.get_current_locale()
    
    def toggle_language(self) -> bool:
        """Toggle between Chinese and English"""
        translation_manager = get_translation_manager()
        if translation_manager is None:
            # Try to initialize
            app = QApplication.instance()
            if app:
                init_translation_manager(app)
                translation_manager = get_translation_manager()
        
        if translation_manager is None:
            self._on_log_message("Error: Could not initialize translation manager")
            return False
        
        current_locale = translation_manager.get_current_locale()
        new_locale = 'en-US' if current_locale == 'zh-CN' else 'zh-CN'
        
        success = translation_manager.switch_language(new_locale)
        if success:
            self.language_changed.emit(new_locale)
            self._on_log_message(tr("Language switched to: %1").replace("%1", new_locale))
        else:
            self._on_log_message(tr("Failed to switch language"))
        
        return success
    
    # Private methods - automation callbacks
    def _on_account_start(self, account: Account):
        """Called when account processing starts"""
        self.account_processing_started.emit(account)
        self.accounts_changed.emit()
    
    def _on_account_complete(self, account: Account):
        """Called when account processing completes"""
        self.account_processing_completed.emit(account)
        self.accounts_changed.emit()
        self.statistics_changed.emit()
    
    def _on_batch_complete(self, success_count: int, failed_count: int):
        """Called when batch processing completes"""
        self.processing_timer.stop()
        self.processing_status_changed.emit()
        self.batch_processing_completed.emit(success_count, failed_count)
    
    def _on_log_message(self, message: str):
        """Called to log a message"""
        self.log_message.emit(message)
    
    def _process_next_account_step(self):
        """Process next account in the batch (called by timer)"""
        accounts = self.data_service.get_accounts()
        
        # Check if we should continue processing
        if not self.automation_service.is_running or self.automation_service.is_paused:
            return
        
        if self.automation_service.current_account_index >= len(accounts):
            # Batch processing complete
            self._complete_batch_processing(accounts)
            return
        
        # IMPORTANT: Stop the timer to prevent multiple concurrent registrations
        if self.processing_timer.isActive():
            self.processing_timer.stop()
        
        # Get current account
        account = accounts[self.automation_service.current_account_index]
        
        # Mark account as processing
        account.mark_processing()
        
        # Notify UI of account start
        if self.automation_service.on_account_start:
            self.automation_service.on_account_start(account)
        
        self._on_log_message(tr("🚀 Starting real browser registration for: %1").replace("%1", account.username))
        
        # Use QTimer to handle async operation in a thread-safe way
        import threading
        
        def run_async_registration():
            """Run async registration in a separate thread"""
            import asyncio
            
            async def register_account():
                try:
                    success = await self.automation_service.register_single_account(account)
                    
                    # Use QTimer.singleShot to safely update UI from main thread
                    if success:
                        QTimer.singleShot(0, lambda: self._on_log_message(tr("✅ Registration completed for: %1").replace("%1", account.username)))
                    else:
                        QTimer.singleShot(0, lambda: self._on_log_message(tr("❌ Registration failed for: %1").replace("%1", account.username)))
                    
                    # Update UI on main thread
                    QTimer.singleShot(0, lambda: self._on_account_complete(account))
                    
                    # Move to next account
                    self.automation_service.current_account_index += 1
                    
                    # IMPORTANT: Restart the timer to process the next account after a delay
                    QTimer.singleShot(2000, lambda: self._resume_processing())
                    
                except Exception as e:
                    # Handle errors on main thread
                    error_msg = str(e)
                    QTimer.singleShot(0, lambda: account.mark_failed(error_msg))
                    QTimer.singleShot(0, lambda: self._on_log_message(tr("❌ Registration error for %1: %2").replace("%1", account.username).replace("%2", error_msg)))
                    QTimer.singleShot(0, lambda: self._on_account_complete(account))
                    self.automation_service.current_account_index += 1
                    
                    # IMPORTANT: Restart the timer even after error
                    QTimer.singleShot(2000, lambda: self._resume_processing())
            
            # Create and run event loop in thread
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(register_account())
                loop.close()
            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: self._on_log_message(tr("❌ Thread error: %1").replace("%1", error_msg)))
                QTimer.singleShot(0, lambda: account.mark_failed(error_msg))
                QTimer.singleShot(0, lambda: self._on_account_complete(account))
                self.automation_service.current_account_index += 1
                
                # IMPORTANT: Restart the timer even after thread error
                QTimer.singleShot(2000, lambda: self._resume_processing())
        
        # Start async registration in a separate thread
        registration_thread = threading.Thread(target=run_async_registration)
        registration_thread.daemon = True  # Thread will terminate when main program exits
        registration_thread.start()
    
    def _resume_processing(self):
        """Resume processing by checking if we should continue and restart timer if needed"""
        if (self.automation_service.is_running and 
            not self.automation_service.is_paused and 
            not self.processing_timer.isActive()):
            
            accounts = self.data_service.get_accounts()
            if self.automation_service.current_account_index < len(accounts):
                # Still have accounts to process, restart the timer
                self.processing_timer.start(1500)
            else:
                # No more accounts, complete batch processing
                self._complete_batch_processing(accounts)
    
    def _complete_batch_processing(self, accounts):
        """Complete the batch processing"""
        self.automation_service.is_running = False
        self.automation_service.is_paused = False
        
        # Calculate statistics
        success_count = len([acc for acc in accounts if acc.status == AccountStatus.SUCCESS])
        failed_count = len([acc for acc in accounts if acc.status == AccountStatus.FAILED])
        
        self._on_log_message(tr("🎉 Batch processing completed! Success: %1, Failed: %2").replace("%1", str(success_count)).replace("%2", str(failed_count)))
        
        # Stop the processing timer
        if self.processing_timer.isActive():
            self.processing_timer.stop()
        
        # Notify UI
        self.processing_status_changed.emit()
        self.batch_processing_completed.emit(success_count, failed_count)
    
    # Cleanup
    def cleanup(self):
        """Cleanup resources when application closes"""
        if self.processing_timer.isActive():
            self.processing_timer.stop()
        
        if self.automation_service.is_running:
            self.automation_service.stop_registration(self.data_service.get_accounts())