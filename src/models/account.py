"""
Account data model for 360 Batch Account Creator
"""

from dataclasses import dataclass
from enum import Enum
from ..translation_manager import tr


class AccountStatus(Enum):
    """Account registration status"""
    QUEUED = "Queued"
    PROCESSING = "Processing" 
    WAITING_CAPTCHA = "Waiting_Captcha"
    SUCCESS = "Success"
    FAILED = "Failed"
    
    def get_translated_name(self):
        """Get translated status name"""
        return tr(self.value, "AccountStatus")


@dataclass
class Account:
    """Account data model"""
    id: int
    username: str
    password: str
    status: AccountStatus = AccountStatus.QUEUED
    notes: str = ""
    
    def __post_init__(self):
        """Post initialization validation"""
        if not self.username or not self.password:
            raise ValueError("Username and password are required")
        if len(self.password) < 6:
            raise ValueError("Password must be at least 6 characters")
    
    def mark_processing(self, notes: str = ""):
        """Mark account as processing"""
        self.status = AccountStatus.PROCESSING
        self.notes = notes or tr("Registering account...")
    
    def mark_success(self, notes: str = ""):
        """Mark account as successfully registered"""
        self.status = AccountStatus.SUCCESS
        self.notes = notes or tr("Registered successfully")
    
    def mark_failed(self, notes: str = ""):
        """Mark account as failed"""
        self.status = AccountStatus.FAILED
        self.notes = notes or tr("Registration failed")
    
    def mark_waiting_captcha(self, notes: str = ""):
        """Mark account as waiting for captcha completion"""
        self.status = AccountStatus.WAITING_CAPTCHA
        self.notes = notes or tr("Waiting for captcha completion")
    
    def reset_status(self):
        """Reset account to queued status"""
        self.status = AccountStatus.QUEUED
        self.notes = ""