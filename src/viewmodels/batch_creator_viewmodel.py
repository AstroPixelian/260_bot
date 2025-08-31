"""
Main ViewModel for the Batch Account Creator application
"""

from typing import List, Callable, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

from ..models.account import Account, AccountStatus
from ..services.data_service import DataService
from ..services.automation_service import AutomationService
from ..translation_manager import tr


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
    
    def __init__(self):
        super().__init__()
        
        # Services
        self.data_service = DataService()
        self.automation_service = AutomationService()
        
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
            self._on_log_message(tr("Successfully imported %1 accounts from CSV").arg(count))
            return True
        
        except Exception as e:
            self._on_log_message(tr("Failed to import CSV: %1").arg(str(e)))
            return False
    
    def generate_random_accounts(self, count: int) -> bool:
        """
        Generate random test accounts
        
        Args:
            count: Number of accounts to generate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if count <= 0 or count > 1000:
                self._on_log_message(tr("Invalid account count: %1").arg(count))
                return False
            
            generated_count = self.data_service.generate_random_accounts(count)
            self.accounts_changed.emit()
            self.statistics_changed.emit()
            self._on_log_message(tr("Generated %1 random accounts").arg(generated_count))
            return True
        
        except Exception as e:
            self._on_log_message(tr("Failed to generate accounts: %1").arg(str(e)))
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
                self._on_log_message(tr("Results exported to: %1").arg(file_path))
            return success
        
        except Exception as e:
            self._on_log_message(tr("Failed to export results: %1").arg(str(e)))
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
        
        if not self.automation_service.process_next_account(accounts):
            # Batch processing complete
            return
        
        # Schedule completion of current account after a delay
        QTimer.singleShot(800, lambda: self.automation_service.complete_current_account(accounts))
    
    # Cleanup
    def cleanup(self):
        """Cleanup resources when application closes"""
        if self.processing_timer.isActive():
            self.processing_timer.stop()
        
        if self.automation_service.is_running:
            self.automation_service.stop_registration(self.data_service.get_accounts())