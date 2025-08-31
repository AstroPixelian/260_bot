#!/usr/bin/env python3
"""
Test the selenium backend implementation
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.services.automation_service import AutomationService
from src.models.account import Account


def main():
    """Test selenium backend registration"""
    
    print("🧪 Testing Selenium Backend")
    print("=" * 50)
    
    username = "eric7114"
    password = "anRBu6vK#9p@PP"
    
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    async def test_selenium_registration():
        try:
            # Create automation service with selenium backend
            print("🔧 Creating AutomationService with selenium backend...")
            service = AutomationService(backend="selenium")
            
            # Create account
            account = Account(id=1, username=username, password=password)
            
            # Set up logging callbacks
            def on_log_message(message: str):
                print(f"📋 LOG: {message}")
            
            def on_account_complete(account: Account):
                print(f"✅ CALLBACK: Registration complete - Status: {account.status.value}")
                if account.notes:
                    print(f"📝 Notes: {account.notes}")
            
            service.set_callbacks(
                on_log_message=on_log_message,
                on_account_complete=on_account_complete
            )
            
            print("🚀 Starting selenium registration...")
            result = await service.register_single_account(account)
            
            print(f"\n🎯 Final Result: {result}")
            print(f"Account Status: {account.status.value}")
            if account.notes:
                print(f"Account Notes: {account.notes}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the async test
    result = asyncio.run(test_selenium_registration())
    
    print("\n" + "=" * 50)
    if result:
        print("✅ Selenium registration completed successfully!")
    else:
        print("❌ Selenium registration failed")
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())