#!/usr/bin/env python3
"""
Test with fresh generated account
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.services.automation_service import AutomationService
from src.models.account import Account


def main():
    """Test with fresh account"""
    
    print("🧪 Testing Fresh Generated Account")
    print("=" * 50)
    
    # Use fresh generated credentials
    username = "charles5123"
    password = "oXsYuQx0@yW%curgC"
    
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    async def test_registration():
        try:
            # Use playwright backend (seems to work better)
            service = AutomationService(backend="playwright")
            
            # Create account
            account = Account(id=1, username=username, password=password)
            
            # Set up detailed logging
            def on_log_message(message: str):
                print(f"📋 LOG: {message}")
            
            def on_account_start(account: Account):
                print(f"🚀 CALLBACK: Starting registration for {account.username}")
            
            def on_account_complete(account: Account):
                print(f"✅ CALLBACK: Registration complete")
                print(f"   Status: {account.status.value}")
                print(f"   Notes: {account.notes}")
            
            service.set_callbacks(
                on_log_message=on_log_message,
                on_account_start=on_account_start,
                on_account_complete=on_account_complete
            )
            
            print("🚀 Starting registration with fresh account...")
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
    result = asyncio.run(test_registration())
    
    print("\n" + "=" * 50)
    if result:
        print("✅ Registration completed successfully!")
    else:
        print("❌ Registration failed")
        print("Note: This might be due to:")
        print("  - Network connectivity issues")
        print("  - 360.cn server response problems")
        print("  - Verification step timing issues")
        print("  - Account already exists (less likely with generated account)")
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())