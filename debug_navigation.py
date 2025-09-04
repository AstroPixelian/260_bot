#!/usr/bin/env python3
"""
Debug script for navigation issue
检查浏览器初始化和导航过程
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.automation.playwright_backend_v2 import PlaywrightBackendV2
from src.models.account import Account

async def test_browser_navigation():
    """测试浏览器导航过程"""
    print("🔧 开始调试浏览器导航...")
    
    # 创建测试账户
    account = Account(1, "debug_test", "password123")
    
    # 创建后端
    backend = PlaywrightBackendV2()
    
    try:
        print("1️⃣ 初始化浏览器...")
        if not await backend._initialize_browser():
            print("❌ 浏览器初始化失败")
            return False
        
        print("✅ 浏览器初始化成功")
        print(f"   Browser: {backend.browser}")
        print(f"   Context: {backend.browser_context}")
        
        # 创建页面
        print("2️⃣ 创建新页面...")
        page = await backend.browser_context.new_page()
        print(f"✅ 页面创建成功: {page}")
        print(f"   页面URL: {page.url}")
        
        # 测试直接导航
        print("3️⃣ 测试直接导航...")
        try:
            print("   导航到 https://wan.360.cn/...")
            await page.goto('https://wan.360.cn/', 
                           wait_until='domcontentloaded', 
                           timeout=20000)
            print(f"   导航后URL: {page.url}")
            print(f"   页面标题: {await page.title()}")
            
            # 等待一段时间观察
            print("   等待5秒观察...")
            await asyncio.sleep(5)
            
            print("✅ 直接导航测试成功")
            
        except Exception as e:
            print(f"❌ 直接导航失败: {e}")
            return False
        
        # 现在测试状态机导航
        print("4️⃣ 测试状态机导航...")
        from src.services.automation.playwright_state_machine import PlaywrightRegistrationStateMachine
        
        # 创建新页面用于状态机
        page2 = await backend.browser_context.new_page()
        print(f"   状态机页面: {page2}")
        print(f"   状态机页面URL: {page2.url}")
        
        # 创建状态机
        state_machine = PlaywrightRegistrationStateMachine(account, page2)
        
        # 设置日志回调
        def log_callback(message):
            print(f"   📋 状态机: {message}")
        
        state_machine.on_log = log_callback
        
        # 运行状态机（仅运行导航部分）
        print("   开始状态机...")
        try:
            # 手动触发初始化
            await state_machine._handle_initializing(state_machine.context)
            print(f"   初始化后状态: {state_machine.current_state}")
            
            # 手动触发导航
            await state_machine._handle_navigating(state_machine.context)
            print(f"   导航后状态: {state_machine.current_state}")
            print(f"   状态机页面URL: {page2.url}")
            
            # 等待观察
            await asyncio.sleep(5)
            
            print("✅ 状态机导航测试完成")
            
        except Exception as e:
            print(f"❌ 状态机导航失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 保持浏览器开启一段时间供观察
        print("5️⃣ 保持浏览器开启30秒供观察...")
        await asyncio.sleep(30)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await backend._cleanup_browser()
            print("🧹 浏览器资源清理完成")
        except Exception as e:
            print(f"⚠️  清理过程中出错: {e}")

async def main():
    """主函数"""
    try:
        success = await test_browser_navigation()
        print("=" * 60)
        if success:
            print("✅ 导航调试测试成功完成")
        else:
            print("❌ 导航调试测试失败")
        return success
    except Exception as e:
        print(f"💥 主函数出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)