#!/usr/bin/env python3
"""
Test both backends to see which one works better
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.services.automation_service import AutomationService
from src.models.account import Account


def main():
    """Test both playwright and selenium backends"""
    
    print("🧪 Testing Both Backends")
    print("=" * 70)
    
    username = "eric7114" 
    password = "anRBu6vK#9p@PP"
    
    print(f"Test credentials - Username: {username}, Password: {password}")
    print()
    
    async def test_backend(backend_name):
        print(f"\n🔧 Testing {backend_name.upper()} Backend")
        print("-" * 40)
        
        try:
            # Create automation service
            service = AutomationService(backend=backend_name)
            
            # Create account
            account = Account(id=1, username=username, password=password)
            
            # Set up logging callbacks
            def on_log_message(message: str):
                print(f"📋 {message}")
            
            def on_account_complete(account: Account):
                print(f"✅ Registration complete - Status: {account.status.value}")
                if account.notes:
                    print(f"📝 Notes: {account.notes}")
            
            service.set_callbacks(
                on_log_message=on_log_message,
                on_account_complete=on_account_complete
            )
            
            print(f"🚀 Starting {backend_name} registration...")
            result = await service.register_single_account(account)
            
            print(f"🎯 Result: {'SUCCESS' if result else 'FAILED'}")
            return result
            
        except Exception as e:
            print(f"❌ {backend_name} backend failed: {e}")
            return False
    
    async def run_tests():
        # Test playwright first
        playwright_result = await test_backend("playwright")
        
        # Test selenium
        selenium_result = await test_backend("selenium")
        
        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY:")
        print(f"  Playwright: {'✅ SUCCESS' if playwright_result else '❌ FAILED'}")
        print(f"  Selenium:   {'✅ SUCCESS' if selenium_result else '❌ FAILED'}")
        
        if playwright_result or selenium_result:
            best_backend = "playwright" if playwright_result else "selenium"
            print(f"\n💡 Recommendation: Use {best_backend} backend")
            return True
        else:
            print("\n❌ Both backends failed")
            return False
    
    # Run the tests
    result = asyncio.run(run_tests())
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())