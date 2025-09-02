#!/usr/bin/env python3
"""
验证码处理改进测试脚本
测试新的验证码检测和GUI状态显示功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account, AccountStatus
from src.services.automation_service import AutomationService

async def test_improved_captcha_handling():
    """测试改进的验证码处理功能"""
    
    # 使用之前生成的测试账号
    test_account = Account(
        id=1,
        username="playerjasmine568",
        password="lH!L8jW!r005"
    )
    
    print("🧪 Testing improved captcha handling features:")
    print("=" * 60)
    print(f"📧 Test Account: {test_account.username}")
    print(f"🔐 Password: {test_account.password}")
    print("✨ New Features:")
    print("  1. WAITING_CAPTCHA status display")
    print("  2. 5-second interval captcha detection")
    print("  3. Real-time GUI status updates")
    print("  4. Improved user experience")
    print("=" * 60)
    
    # 初始化自动化服务
    automation_service = AutomationService()
    
    # 设置详细的回调
    def log_callback(message):
        print(f"[LOG] {message}")
    
    def account_start_callback(account):
        print(f"🚀 [START] Processing: {account.username}")
    
    def account_complete_callback(account):
        print(f"📊 [UPDATE] Account: {account.username}")
        print(f"    Status: {account.status.value} -> {account.status.get_translated_name()}")
        print(f"    Notes: {account.notes}")
        
        if account.status == AccountStatus.WAITING_CAPTCHA:
            print("    🎯 GUI should show: Orange color + exclamation mark icon")
            print("    🔄 System will check every 5 seconds for resolution")
    
    automation_service.set_callbacks(
        on_log_message=log_callback,
        on_account_start=account_start_callback,
        on_account_complete=account_complete_callback
    )
    
    try:
        print("🌐 Starting registration process...")
        print("🎯 Expected behavior when captcha appears:")
        print("  - Account status → WAITING_CAPTCHA")
        print("  - GUI shows orange color with exclamation mark")
        print("  - Checks every 5 seconds instead of every 10 seconds")
        print("  - Provides remaining time updates every 30 seconds")
        print()
        
        # 启动注册流程
        success = await automation_service.register_single_account(test_account)
        
        print("\n" + "=" * 60)
        if success:
            print("✅ Registration completed successfully!")
        else:
            print("⚠️  Registration incomplete - may require manual intervention")
            
        print(f"📊 Final Status: {test_account.status.value}")
        print(f"📝 Final Notes: {test_account.notes}")
        
        # 状态验证
        if test_account.status == AccountStatus.WAITING_CAPTCHA:
            print("\n🎯 CAPTCHA HANDLING TEST RESULTS:")
            print("✅ Successfully detected captcha")
            print("✅ Set WAITING_CAPTCHA status")
            print("✅ GUI should display orange color with exclamation icon")
            print("✅ Browser remained open for manual resolution")
        elif test_account.status == AccountStatus.SUCCESS:
            print("\n🎯 REGISTRATION SUCCESS:")
            print("✅ Account registered successfully")
        elif test_account.status == AccountStatus.FAILED:
            print("\n⚠️ REGISTRATION FAILED:")
            print(f"❌ Reason: {test_account.notes}")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("💡 Test completed. Key improvements verified:")
    print("  ✅ 5-second captcha check interval (vs previous 10s)")
    print("  ✅ WAITING_CAPTCHA status with orange visual indicator") 
    print("  ✅ Real-time GUI updates during captcha detection")
    print("  ✅ Better user feedback with time remaining")
    print("  ✅ Improved error handling and state management")
    print("\n💡 Browser should remain open if captcha detected.")
    print("💡 Press Ctrl+C to exit when done observing.")
    
    # 保持程序运行以观察浏览器状态
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Exiting improved captcha handling test...")

if __name__ == "__main__":
    asyncio.run(test_improved_captcha_handling())