#!/usr/bin/env python3
"""
Test script for debugging CLI registration with generated accounts
"""

import subprocess
import sys
from src.account_generator import AccountGenerator


def main():
    """Generate test accounts and try CLI registration"""
    
    print("🧪 CLI Debug Test Script")
    print("=" * 50)
    
    # Generate a test account
    print("📝 Generating test account...")
    generator = AccountGenerator()
    accounts = generator.generate_accounts(1)
    
    if not accounts:
        print("❌ Failed to generate test account")
        return 1
    
    account = accounts[0]
    username = account["username"]
    password = account["password"]
    
    print(f"✅ Generated test account:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print()
    
    # Test CLI registration
    print("🚀 Testing CLI registration...")
    print(f"Command: python main.py --username {username} --password {password}")
    print()
    
    try:
        # Run the CLI command
        result = subprocess.run([
            sys.executable, 
            "main.py", 
            "--username", username, 
            "--password", password
        ], capture_output=True, text=True, timeout=120)  # 2 minute timeout
        
        print("📋 CLI Output:")
        print("-" * 30)
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print("-" * 30)
        print(f"Exit Code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Registration completed successfully!")
        else:
            print("❌ Registration failed")
            
    except subprocess.TimeoutExpired:
        print("⏰ CLI command timed out after 2 minutes")
        return 1
    except Exception as e:
        print(f"❌ Error running CLI command: {str(e)}")
        return 1
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())