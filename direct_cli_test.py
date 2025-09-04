#!/usr/bin/env python3
"""
简化的CLI测试 - 直接使用状态机而不通过后端封装
Simplified CLI Test - Direct state machine usage without backend wrapper
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.automation.playwright_state_machine import PlaywrightRegistrationStateMachine
from playwright.async_api import async_playwright

async def direct_cli_test():
    """直接CLI测试"""
    username = f"directtest{int(asyncio.get_event_loop().time())}"
    password = "testpass123"
    
    print("🎯 直接CLI测试开始")
    print(f"   用户名: {username}")
    print(f"   密码: {password}")
    print("=" * 50)
    
    account = Account(1, username, password)
    
    playwright = None
    browser = None
    
    try:
        # 直接初始化Playwright
        print("1️⃣ 初始化Playwright...")
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            slow_mo=100
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 创建单个页面
        print("2️⃣ 创建页面...")
        page = await context.new_page()
        
        print(f"   初始页面URL: {page.url}")
        
        # 创建状态机
        print("3️⃣ 创建状态机...")
        state_machine = PlaywrightRegistrationStateMachine(account, page)
        
        # 设置详细日志
        def verbose_log(message):
            print(f"   📋 {message}")
        
        state_machine.on_log = verbose_log
        
        # 运行状态机
        print("4️⃣ 运行状态机...")
        success = await state_machine.run_state_machine()
        
        print(f"\n5️⃣ 状态机完成")
        print(f"   成功: {'是' if success else '否'}")
        print(f"   最终状态: {state_machine.current_state}")
        print(f"   页面URL: {page.url}")
        print(f"   账户状态: {account.status}")
        print(f"   账户备注: {account.notes}")
        
        # 保持浏览器开启供用户观察
        print("\n6️⃣ 保持浏览器开启60秒供观察...")
        print("   请观察浏览器是否正确显示了页面内容")
        await asyncio.sleep(60)
        
        return success
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        print("🧹 清理完成")

async def main():
    """主函数"""
    success = await direct_cli_test()
    print("=" * 60)
    if success:
        print("✅ 直接CLI测试成功")
    else:
        print("❌ 直接CLI测试失败")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)