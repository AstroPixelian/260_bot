#!/usr/bin/env python3
"""
Example usage of AutomationService with undetected_chromedriver backend

This demonstrates how to switch between playwright and selenium backends
and perform account registration using the 360.cn site.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.automation_service import AutomationService
from src.models.account import Account

def log_callback(message: str):
    """Callback function to handle log messages"""
    print(f"[LOG] {message}")

def account_start_callback(account: Account):
    """Callback function called when account processing starts"""
    print(f"[START] Processing account: {account.username}")

def account_complete_callback(account: Account):
    """Callback function called when account processing completes"""
    status = account.status.value
    print(f"[COMPLETE] Account {account.username}: {status}")
    if hasattr(account, 'failure_reason') and account.failure_reason:
        print(f"[ERROR] Reason: {account.failure_reason}")

async def main():
    """Main example function"""
    print("=== AutomationService Backend Comparison Example ===\n")
    
    # Create automation service with default backend (playwright)
    automation_service = AutomationService()
    
    # Set up callbacks
    automation_service.set_callbacks(
        on_log_message=log_callback,
        on_account_start=account_start_callback,
        on_account_complete=account_complete_callback
    )
    
    print(f"Available backends: {automation_service.get_available_backends()}")
    print(f"Current backend: {automation_service.get_backend()}")
    print(f"Selenium available: {automation_service.is_selenium_available()}\n")
    
    # Generate test accounts
    print("Generating test accounts...")
    test_accounts = automation_service.generate_test_accounts(2)
    
    if not test_accounts:
        print("Failed to generate test accounts. Exiting.")
        return
    
    print(f"Generated {len(test_accounts)} test accounts:")
    for account in test_accounts:
        print(f"  - {account.username} / {account.password}")
    print()
    
    # Test with Playwright backend (default)
    print("=== Testing with Playwright Backend ===")
    try:
        result = await automation_service.register_single_account(test_accounts[0])
        print(f"Playwright registration result: {result}")
        print(f"Account status: {test_accounts[0].status.value}\n")
    except Exception as e:
        print(f"Playwright registration failed: {e}\n")
    
    # Switch to Selenium backend if available
    if automation_service.is_selenium_available():
        print("=== Switching to Selenium Backend ===")
        try:
            automation_service.set_backend("selenium")
            print(f"Switched to backend: {automation_service.get_backend()}")
            
            # Test with Selenium backend
            print("=== Testing with Selenium/undetected_chromedriver Backend ===")
            result = await automation_service.register_single_account(test_accounts[1])
            print(f"Selenium registration result: {result}")
            print(f"Account status: {test_accounts[1].status.value}")
            
        except Exception as e:
            print(f"Selenium backend error: {e}")
    else:
        print("=== Selenium Backend Not Available ===")
        print("To enable selenium backend, install undetected_chromedriver:")
        print("pip install undetected-chromedriver")
    
    print("\n=== Example Complete ===")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user.")
    except Exception as e:
        print(f"Example failed with error: {e}")
        import traceback
        traceback.print_exc()