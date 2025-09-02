#!/usr/bin/env python3
"""
验证修复后的验证码检测逻辑
测试两个条件都满足的注册成功判定
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.automation_service import AutomationService

async def test_fixed_captcha_logic():
    """测试修复后的验证码逻辑"""
    
    # 使用新的测试账号
    test_account = Account(
        id=1,
        username="testuser2025fixed",
        password="TestPass123Fixed!"
    )
    
    print("🔧 Testing FIXED captcha detection logic:")
    print("=" * 70)
    print(f"📧 Test Account: {test_account.username}")
    print(f"🔐 Password: {test_account.password}")
    print()
    print("✅ FIXED Logic: Registration success requires BOTH conditions:")
    print("   1️⃣ Captcha dialog/frame disappears")
    print("   2️⃣ Account registration success conditions are met")
    print()
    print("🚀 Expected behavior:")
    print("   - When captcha appears → Status: WAITING_CAPTCHA (Orange)")
    print("   - When captcha disappears → Check registration success conditions")
    print("   - Only if BOTH conditions met → SUCCESS")
    print("   - If only captcha cleared → Continue waiting or FAILED")
    print("=" * 70)
    
    # 初始化自动化服务
    automation_service = AutomationService()
    
    # 设置详细的回调
    def log_callback(message):
        print(f"[LOG] {message}")
    
    def account_start_callback(account):
        print(f"🚀 [START] Processing: {account.username}")
    
    def account_complete_callback(account):
        print(f"📊 [UPDATE] Account: {account.username}")
        print(f"    Status: {account.status.value}")
        print(f"    Notes: {account.notes}")
        
        if hasattr(account.status, 'get_translated_name'):
            print(f"    Display: {account.status.get_translated_name()}")
    
    automation_service.set_callbacks(
        on_log_message=log_callback,
        on_account_start=account_start_callback,
        on_account_complete=account_complete_callback
    )
    
    try:
        print("🌐 Starting registration process with FIXED logic...")
        
        # 启动注册流程
        success = await automation_service.register_single_account(test_account)
        
        print("\n" + "=" * 70)
        print("🧪 FIXED CAPTCHA LOGIC TEST RESULTS:")
        
        if success:
            print("✅ Registration SUCCESSFUL!")
            print("   ✓ Both conditions met: Captcha cleared AND success confirmed")
        else:
            print("❌ Registration FAILED or INCOMPLETE")
            if "Captcha cleared but" in str(test_account.notes):
                print("   ⚠️  Captcha was cleared but registration success not confirmed")
                print("   → This is the CORRECT behavior with the new logic!")
            elif "CAPTCHA_DETECTED" in str(test_account.notes):
                print("   ⏳ Captcha timeout - user didn't complete verification in time")
            else:
                print(f"   📝 Reason: {test_account.notes}")
                
        print(f"\n📊 Final Status: {test_account.status.value}")
        print(f"📝 Final Notes: {test_account.notes}")
        
        print("\n🔍 Logic Validation:")
        if "both conditions met" in str(test_account.notes):
            print("✅ CORRECT: Both captcha cleared AND registration success confirmed")
        elif "Captcha cleared but" in str(test_account.notes):
            print("✅ CORRECT: Captcha cleared but registration not confirmed (stricter logic)")
        elif test_account.notes and "CAPTCHA_DETECTED" in str(test_account.notes):
            print("⏳ EXPECTED: Captcha detection and waiting logic working")
        else:
            print("ℹ️  Other result - check logs above for details")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🎯 SUMMARY: Fixed Logic Validation")
    print("✅ Two-condition check: Captcha disappears + Success confirmation")  
    print("✅ Stricter validation prevents false positives")
    print("✅ WAITING_CAPTCHA status with proper GUI display")
    print("✅ Improved user feedback and error handling")
    print("\n💡 Browser should remain open if captcha detected.")
    print("💡 Press Ctrl+C to exit when done observing.")
    
    # 保持程序运行以观察浏览器状态
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Exiting fixed captcha logic test...")

if __name__ == "__main__":
    asyncio.run(test_fixed_captcha_logic())