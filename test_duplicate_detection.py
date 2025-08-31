#!/usr/bin/env python3
"""
Test duplicate account detection with already registered account
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.services.automation_service import AutomationService
from src.models.account import Account


def main():
    """Test duplicate account detection"""
    
    print("🧪 Testing Duplicate Account Detection")
    print("=" * 50)
    
    # Use the account we know is already registered
    username = "eric7114"
    password = "anRBu6vK#9p@PP"
    
    print(f"Testing with ALREADY REGISTERED account:")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    async def test_duplicate_detection():
        try:
            service = AutomationService(backend="playwright")
            account = Account(id=1, username=username, password=password)
            
            # Set up detailed logging
            def on_log_message(message: str):
                print(f"📋 LOG: {message}")
            
            def on_account_complete(account: Account):
                print(f"✅ CALLBACK: Registration complete")
                print(f"   Status: {account.status.value}")
                print(f"   Notes: {account.notes}")
                
                # Check if it correctly detected duplicate
                if "already" in account.notes.lower() or "已注册" in account.notes:
                    print("✅ SUCCESS: Correctly detected duplicate account!")
                else:
                    print("❌ FAILED: Did not detect duplicate account")
            
            service.set_callbacks(
                on_log_message=on_log_message,
                on_account_complete=on_account_complete
            )
            
            print("🔍 Testing duplicate account detection...")
            result = await service.register_single_account(account)
            
            print(f"\n🎯 Registration Result: {result}")
            print(f"Account Status: {account.status.value}")
            print(f"Account Notes: {account.notes}")
            
            # Expect this to fail but with proper duplicate detection
            if not result and ("already" in account.notes.lower() or "已注册" in account.notes):
                print("\n✅ Perfect! Correctly detected and reported duplicate account")
                return True
            elif not result:
                print(f"\n⚠️  Registration failed but reason unclear: {account.notes}")
                return False
            else:
                print(f"\n❌ Unexpected success - should have detected duplicate")
                return False
            
        except Exception as e:
            print(f"\n❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the test
    result = asyncio.run(test_duplicate_detection())
    
    print("\n" + "=" * 50)
    if result:
        print("✅ Duplicate detection test PASSED!")
    else:
        print("❌ Duplicate detection test FAILED!")
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())