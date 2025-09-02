#!/usr/bin/env python3
"""
临时测试脚本：启动单个账号注册流程
用于让用户观察验证码框和成功注册的页面特征
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.automation_service import AutomationService

async def test_single_registration():
    """测试单个账号注册，保持浏览器打开让用户观察"""
    
    # 创建测试账号
    test_account = Account(
        id=1,
        username="testuser2025",
        password="TestPass123!"
    )
    
    print(f"🚀 Starting registration test for: {test_account.username}")
    print(f"📝 Password: {test_account.password}")
    print("=" * 60)
    
    # 初始化自动化服务
    automation_service = AutomationService()
    
    # 设置日志回调
    def log_callback(message):
        print(f"[LOG] {message}")
    
    automation_service.set_callbacks(
        on_log_message=log_callback
    )
    
    try:
        print("🌐 Starting browser and navigating to registration page...")
        
        # 启动注册流程但在验证码处暂停
        success = await automation_service.register_single_account(test_account)
        
        if success:
            print("✅ Registration completed successfully!")
        else:
            print("❌ Registration failed or requires manual intervention")
            
        print(f"📊 Final account status: {test_account.status}")
        print(f"📝 Notes: {test_account.notes}")
        
    except Exception as e:
        print(f"❌ Error during registration: {str(e)}")
    
    print("=" * 60)
    print("💡 Browser should still be open for inspection")
    print("💡 Press Ctrl+C to exit when done observing")
    
    # 保持程序运行，让浏览器保持打开状态
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Exiting test script...")

if __name__ == "__main__":
    asyncio.run(test_single_registration())