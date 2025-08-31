"""
Data service for managing account data operations
"""

import csv
import random
import string
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models.account import Account, AccountStatus
from translation_manager import tr


class DataService:
    """Service for handling account data operations"""
    
    def __init__(self):
        self.accounts: List[Account] = []
    
    def get_accounts(self) -> List[Account]:
        """Get all accounts"""
        return self.accounts
    
    def clear_accounts(self):
        """Clear all accounts"""
        self.accounts.clear()
    
    def add_account(self, account: Account):
        """Add a single account"""
        self.accounts.append(account)
    
    def add_accounts(self, accounts: List[Account]):
        """Add multiple accounts"""
        self.accounts.extend(accounts)
    
    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """Get account by ID"""
        return next((acc for acc in self.accounts if acc.id == account_id), None)
    
    def get_statistics(self) -> dict:
        """Get account statistics"""
        total = len(self.accounts)
        success = len([acc for acc in self.accounts if acc.status == AccountStatus.SUCCESS])
        failed = len([acc for acc in self.accounts if acc.status == AccountStatus.FAILED])
        processing = len([acc for acc in self.accounts if acc.status == AccountStatus.PROCESSING])
        queued = len([acc for acc in self.accounts if acc.status == AccountStatus.QUEUED])
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'processing': processing,
            'queued': queued,
            'remaining': total - success - failed,
            'progress': int((success + failed) * 100 / total) if total > 0 else 0
        }
    
    def import_from_csv(self, file_path: str) -> int:
        """
        Import accounts from CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Number of accounts imported
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If CSV format is invalid
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        imported_accounts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for i, row in enumerate(reader):
                    username = row.get('username', '').strip()
                    password = row.get('password', '').strip()
                    
                    if username and password:
                        account = Account(
                            id=len(self.accounts) + len(imported_accounts) + 1,
                            username=username,
                            password=password
                        )
                        imported_accounts.append(account)
            
            self.add_accounts(imported_accounts)
            return len(imported_accounts)
            
        except Exception as e:
            raise ValueError(f"Error parsing CSV file: {str(e)}")
    
    def generate_random_accounts(self, count: int) -> int:
        """
        Generate random test accounts
        
        Args:
            count: Number of accounts to generate
            
        Returns:
            Number of accounts generated
        """
        if count <= 0:
            raise ValueError("Count must be positive")
        if count > 1000:
            raise ValueError("Cannot generate more than 1000 accounts at once")
        
        generated_accounts = []
        
        for i in range(count):
            username = f"user_{''.join(random.choices(string.ascii_lowercase, k=6))}_{i+1:03d}"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            account = Account(
                id=len(self.accounts) + len(generated_accounts) + 1,
                username=username,
                password=password
            )
            generated_accounts.append(account)
        
        self.add_accounts(generated_accounts)
        return len(generated_accounts)
    
    def export_to_csv(self, file_path: str, include_results: bool = True) -> bool:
        """
        Export accounts to CSV file
        
        Args:
            file_path: Output file path
            include_results: Whether to include status and notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                if include_results:
                    fieldnames = ['username', 'password', 'status', 'notes', 'timestamp']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for account in self.accounts:
                        writer.writerow({
                            'username': account.username,
                            'password': account.password,
                            'status': account.status.value,
                            'notes': account.notes,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                else:
                    fieldnames = ['username', 'password']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for account in self.accounts:
                        writer.writerow({
                            'username': account.username,
                            'password': account.password
                        })
            
            return True
            
        except Exception as e:
            raise ValueError(f"Error exporting to CSV: {str(e)}")
    
    def reset_all_accounts(self):
        """Reset all accounts to queued status"""
        for account in self.accounts:
            account.reset_status()
    
    def validate_accounts(self) -> List[str]:
        """
        Validate all accounts and return list of validation errors
        
        Returns:
            List of validation error messages
        """
        errors = []
        usernames = set()
        
        for account in self.accounts:
            # Check for duplicate usernames
            if account.username in usernames:
                errors.append(f"Duplicate username: {account.username}")
            else:
                usernames.add(account.username)
            
            # Check username format
            if not account.username.replace('_', '').replace('-', '').isalnum():
                errors.append(f"Invalid username format: {account.username}")
            
            # Check password strength
            if len(account.password) < 6:
                errors.append(f"Password too short for user {account.username}")
        
        return errors