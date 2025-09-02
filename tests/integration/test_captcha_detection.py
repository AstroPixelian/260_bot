#!/usr/bin/env python3
"""
测试脚本：验证码检测测试
专门测试验证码检测逻辑是否能正确识别验证码状态
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.automation_service import AutomationService

async def test_captcha_detection():
    """测试验证码检测功能"""
    
    # 使用刚生成的测试账号
    test_account = Account(
        id=1,
        username="playerjasmine568",
        password="lH!L8jW!r005"
    )
    
    print(f"🧪 Testing captcha detection with account: {test_account.username}")
    print(f"🔐 Password: {test_account.password}")
    print("=" * 70)
    
    # 初始化自动化服务
    automation_service = AutomationService()
    
    # 设置详细日志回调
    def log_callback(message):
        print(f"[LOG] {message}")
    
    def account_start_callback(account):
        print(f"🔄 [CALLBACK] Account processing started: {account.username}")
    
    def account_complete_callback(account):
        print(f"✅ [CALLBACK] Account processing completed: {account.username}")
        print(f"📊 Final status: {account.status}")
        print(f"📝 Notes: {account.notes}")
    
    automation_service.set_callbacks(
        on_log_message=log_callback,
        on_account_start=account_start_callback,
        on_account_complete=account_complete_callback
    )
    
    try:
        print("🌐 Starting browser and navigating to registration page...")
        print("🎯 Focus: Testing captcha detection logic")
        print("⏰ Browser will stay open when captcha is detected")
        print()
        
        # 启动注册流程
        success = await automation_service.register_single_account(test_account)
        
        print("\n" + "=" * 70)
        if success:
            print("✅ Registration process completed successfully!")
        else:
            print("⚠️  Registration process completed with issues or requires manual intervention")
            
        print(f"📊 Final account status: {test_account.status}")
        print(f"📝 Account notes: {test_account.notes}")
        
        # 检查是否检测到验证码
        if "验证码" in str(test_account.notes):
            print("\n🎯 CAPTCHA DETECTION TEST: ✅ SUCCESS")
            print("   The system correctly detected captcha requirement")
        else:
            print("\n🎯 CAPTCHA DETECTION TEST: Result depends on actual page state")
            
    except Exception as e:
        print(f"❌ Error during captcha detection test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🔍 Test completed. Check the browser state and console output above.")
    print("💡 If captcha appeared, browser should still be open for inspection")
    print("💡 Press Ctrl+C to exit when done observing")
    
    # 保持程序运行，让浏览器保持打开状态用于检查
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Exiting captcha detection test...")

if __name__ == "__main__":
    asyncio.run(test_captcha_detection())