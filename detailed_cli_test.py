#!/usr/bin/env python3
"""
Detailed test script for CLI registration debugging
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.cli import CLIHandler
from src.models.account import Account


def main():
    """Test CLI registration with detailed logging"""
    
    print("🧪 Testing CLI Registration")
    print("=" * 50)
    
    username = "eric7114"
    password = "anRBu6vK#9p@PP"
    
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    async def test_registration():
        # Create CLI handler
        cli = CLIHandler()
        
        print("📝 Setting up callbacks for detailed logging...")
        
        # Override the callback setup to capture all log messages
        original_setup = cli.setup_callbacks
        
        def enhanced_setup():
            def on_account_start(account: Account):
                print(f"🚀 CALLBACK: Account start - {account.username}")
            
            def on_account_complete(account: Account):
                print(f"✅ CALLBACK: Account complete - {account.username}, Status: {account.status.value}")
                if account.notes:
                    print(f"📝 Notes: {account.notes}")
            
            def on_log_message(message: str):
                print(f"📋 LOG: {message}")
            
            cli.automation_service.set_callbacks(
                on_account_start=on_account_start,
                on_account_complete=on_account_complete,
                on_log_message=on_log_message
            )
        
        cli.setup_callbacks = enhanced_setup
        
        print("🔄 Starting registration process...")
        try:
            result = await cli.register_account(username, password)
            print(f"\n🎯 Final Result: {result}")
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
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())