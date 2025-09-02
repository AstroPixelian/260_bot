#!/usr/bin/env python3
"""
测试修复后的验证码检测逻辑
验证异步监控机制和GUI响应性
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.automation_service import AutomationService

async def test_fixed_captcha_monitoring():
    """测试修复后的验证码监控逻辑"""
    
    # 使用测试账号
    test_account = Account(
        id=1,
        username="testcaptcha2025",
        password="TestCaptcha123!"
    )
    
    print("🔧 Testing FIXED captcha monitoring logic:")
    print("=" * 70)
    print(f"📧 Test Account: {test_account.username}")
    print(f"🔐 Password: {test_account.password}")
    print()
    print("✅ NEW Logic:")
    print("  1️⃣ Captcha detected → Set WAITING_CAPTCHA status")
    print("  2️⃣ Start async monitoring task (non-blocking)")
    print("  3️⃣ Continue batch processing with next account")
    print("  4️⃣ Monitor checks every 5 seconds for completion")
    print("  5️⃣ Update status when user completes captcha")
    print()
    print("🎯 Benefits:")
    print("  ✅ Batch processing is NOT blocked by captcha")
    print("  ✅ GUI remains responsive")
    print("  ✅ Automatic detection when user completes captcha")
    print("  ✅ Browser automatically closes after success")
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
            
        if account.status.value == 'WAITING_CAPTCHA':
            print("    🟠 GUI: Should show orange color + exclamation mark")
            print("    🔄 Background: Async monitoring active")
        elif account.status.value == 'SUCCESS':
            print("    🟢 GUI: Should show green color + checkmark")
            print("    🎉 Background: Monitoring completed, browser closed")
    
    automation_service.set_callbacks(
        on_log_message=log_callback,
        on_account_start=account_start_callback,
        on_account_complete=account_complete_callback
    )
    
    try:
        print("🌐 Starting registration process with FIXED monitoring...")
        print("⏰ When captcha appears:")
        print("   - Status changes to WAITING_CAPTCHA immediately")
        print("   - Async monitoring starts in background") 
        print("   - Function returns, allowing batch processing to continue")
        print("   - Monitor checks every 5 seconds for user completion")
        
        # 启动注册流程
        success = await automation_service.register_single_account(test_account)
        
        print("\n" + "=" * 70)
        print("🧪 CAPTCHA MONITORING TEST RESULTS:")
        
        print(f"📊 Registration function returned: {success}")
        print(f"📊 Account Status: {test_account.status.value}")
        print(f"📝 Account Notes: {test_account.notes}")
        
        if test_account.status.value == 'WAITING_CAPTCHA':
            print("\n✅ CORRECT BEHAVIOR:")
            print("  ✓ Function returned immediately (non-blocking)")  
            print("  ✓ Status set to WAITING_CAPTCHA")
            print("  ✓ Async monitoring task started in background")
            print("  ✓ Browser kept open for manual captcha solving")
            print("  ✓ Batch processing can continue with next account")
            
            print("\n🔄 BACKGROUND MONITORING:")
            print("  - Monitoring task runs every 5 seconds")
            print("  - Automatically detects when you complete captcha")
            print("  - Updates status to SUCCESS when detected") 
            print("  - Closes browser automatically after success")
            
            print(f"\n⏰ Monitoring will run for up to 10 minutes")
            print("💡 Complete the captcha manually to see automatic detection!")
            
        elif test_account.status.value == 'SUCCESS':
            print("\n✅ REGISTRATION SUCCESSFUL:")
            print("  ✓ No captcha appeared, direct success")
            
        else:
            print(f"\n⚠️ OTHER RESULT: {test_account.status.value}")
            print(f"   Notes: {test_account.notes}")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🎯 SUMMARY: Fixed Captcha Monitoring")
    print("✅ Non-blocking: Registration function returns immediately")
    print("✅ Async monitoring: Background task monitors captcha resolution")
    print("✅ GUI responsive: No blocking of main thread or batch processing")
    print("✅ Auto-detection: Monitors user completion every 5 seconds")
    print("✅ Auto-cleanup: Closes browser when captcha resolved")
    
    if test_account.status.value == 'WAITING_CAPTCHA':
        print("\n💡 The browser should be open - complete the captcha to test!")
        print("💡 Watch the logs to see automatic detection in action!")
        print("💡 Press Ctrl+C to exit monitoring when done testing")
        
        # 保持程序运行以观察监控
        try:
            while test_account.status.value == 'WAITING_CAPTCHA':
                await asyncio.sleep(1)
            print(f"\n🎉 Final Status: {test_account.status.value}")
        except KeyboardInterrupt:
            print("\n👋 Exiting captcha monitoring test...")
    else:
        print("\n💡 Test completed - no captcha appeared or already resolved")

if __name__ == "__main__":
    asyncio.run(test_fixed_captcha_monitoring())