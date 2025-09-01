"""
Account service for managing account data and operations
Prepares for SQLite integration in next version
"""

from typing import List, Optional, Dict, Any
from ..models.account import Account, AccountStatus
from ..account_generator import AccountGenerator
from ..translation_manager import tr


class AccountService:
    """Service for account data management and business logic"""
    
    def __init__(self):
        """Initialize the account service"""
        self._accounts: List[Account] = []
        self.account_generator = AccountGenerator()
    
    # Core account operations
    def get_accounts(self) -> List[Account]:
        """Get all accounts"""
        return self._accounts.copy()
    
    def get_account_count(self) -> int:
        """Get total number of accounts"""
        return len(self._accounts)
    
    def get_account_by_index(self, index: int) -> Optional[Account]:
        """Get account by index"""
        if 0 <= index < len(self._accounts):
            return self._accounts[index]
        return None
    
    def get_account_by_username(self, username: str) -> Optional[Account]:
        """Get account by username"""
        for account in self._accounts:
            if account.username == username:
                return account
        return None
    
    def add_account(self, account: Account) -> bool:
        """Add a single account"""
        try:
            # Check for duplicate username
            if self.get_account_by_username(account.username):
                return False
            
            self._accounts.append(account)
            return True
        except Exception:
            return False
    
    def add_accounts(self, accounts: List[Account]) -> int:
        """Add multiple accounts, returns count of successfully added"""
        added_count = 0
        for account in accounts:
            if self.add_account(account):
                added_count += 1
        return added_count
    
    def update_account_status(self, username: str, status: AccountStatus, notes: str = "") -> bool:
        """Update account status and notes"""
        account = self.get_account_by_username(username)
        if account:
            account.status = status
            if notes:
                account.notes = notes
            return True
        return False
    
    def clear_accounts(self):
        """Clear all accounts"""
        self._accounts.clear()
    
    # Account generation
    def generate_random_accounts(self, count: int) -> List[Account]:
        """Generate random test accounts"""
        if count <= 0:
            return []
        
        generated_accounts = []
        accounts_data = self.account_generator.generate_accounts(count)
        
        for i, acc_data in enumerate(accounts_data):
            account = Account(
                id=len(self._accounts) + i + 1,  # Generate unique ID
                username=acc_data["username"],
                password=acc_data["password"],
                status=AccountStatus.QUEUED
            )
            generated_accounts.append(account)
        
        return generated_accounts
    
    # Account statistics and filtering
    def get_statistics(self) -> Dict[str, Any]:
        """Get account statistics"""
        stats = {
            'total': len(self._accounts),
            'queued': 0,
            'processing': 0,
            'success': 0,
            'failed': 0
        }
        
        for account in self._accounts:
            if account.status == AccountStatus.QUEUED:
                stats['queued'] += 1
            elif account.status == AccountStatus.PROCESSING:
                stats['processing'] += 1
            elif account.status == AccountStatus.SUCCESS:
                stats['success'] += 1
            elif account.status == AccountStatus.FAILED:
                stats['failed'] += 1
        
        return stats
    
    def get_accounts_by_status(self, status: AccountStatus) -> List[Account]:
        """Get accounts filtered by status"""
        return [account for account in self._accounts if account.status == status]
    
    def get_queued_accounts(self) -> List[Account]:
        """Get accounts ready for processing"""
        return self.get_accounts_by_status(AccountStatus.QUEUED)
    
    def get_completed_accounts(self) -> List[Account]:
        """Get accounts that completed processing (success or failed)"""
        return [account for account in self._accounts 
                if account.status in [AccountStatus.SUCCESS, AccountStatus.FAILED]]
    
    # Account validation
    def validate_account(self, account: Account) -> bool:
        """Validate account data"""
        if not account.username or len(account.username.strip()) == 0:
            return False
        if not account.password or len(account.password.strip()) == 0:
            return False
        return True
    
    def validate_accounts(self, accounts: List[Account]) -> List[Account]:
        """Filter out invalid accounts"""
        return [account for account in accounts if self.validate_account(account)]
    
    # Batch operations for processing
    def reset_processing_status(self):
        """Reset all processing accounts back to queued"""
        for account in self._accounts:
            if account.status == AccountStatus.PROCESSING:
                account.status = AccountStatus.QUEUED
    
    def get_next_account_for_processing(self) -> Optional[Account]:
        """Get next account ready for processing"""
        queued_accounts = self.get_queued_accounts()
        return queued_accounts[0] if queued_accounts else None
    
    def mark_account_processing(self, username: str) -> bool:
        """Mark account as currently being processed"""
        return self.update_account_status(username, AccountStatus.PROCESSING)
    
    def mark_account_success(self, username: str, notes: str = "") -> bool:
        """Mark account as successfully processed"""
        return self.update_account_status(username, AccountStatus.SUCCESS, notes)
    
    def mark_account_failed(self, username: str, error_message: str) -> bool:
        """Mark account as failed with error message"""
        return self.update_account_status(username, AccountStatus.FAILED, error_message)
    
    # Future SQLite integration preparation
    def prepare_for_persistence(self) -> Dict[str, Any]:
        """Prepare account data for database persistence (future SQLite integration)"""
        return {
            'accounts': [
                {
                    'username': account.username,
                    'password': account.password,
                    'status': account.status.value,
                    'notes': account.notes,
                    'created_at': account.created_at.isoformat() if hasattr(account, 'created_at') and account.created_at else None,
                    'updated_at': account.updated_at.isoformat() if hasattr(account, 'updated_at') and account.updated_at else None
                }
                for account in self._accounts
            ],
            'statistics': self.get_statistics()
        }
    
    def load_from_persistence(self, data: Dict[str, Any]) -> bool:
        """Load account data from database persistence (future SQLite integration)"""
        try:
            if 'accounts' not in data:
                return False
            
            accounts = []
            for account_data in data['accounts']:
                account = Account(
                    username=account_data['username'],
                    password=account_data['password'],
                    status=AccountStatus(account_data['status']),
                    notes=account_data.get('notes', '')
                )
                accounts.append(account)
            
            self._accounts = accounts
            return True
        except Exception:
            return False