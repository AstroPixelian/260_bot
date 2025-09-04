#!/usr/bin/env python3
"""
步步调试状态机执行
Step-by-step debugging of state machine execution
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from playwright.async_api import async_playwright

async def step_by_step_debug():
    """逐步调试每个状态"""
    username = f"steptest{int(asyncio.get_event_loop().time())}"
    password = "testpass123"
    
    print("🔧 逐步调试开始")
    print(f"   用户名: {username}")
    print("=" * 50)
    
    account = Account(1, username, password)
    
    playwright = None
    browser = None
    page = None
    
    try:
        # 初始化Playwright
        print("1️⃣ 初始化Playwright...")
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            slow_mo=500  # 更慢的操作以便观察
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        print(f"   页面创建成功，初始URL: {page.url}")
        
        # 手动执行导航步骤
        print("2️⃣ 手动执行导航...")
        print("   导航前URL:", page.url)
        
        await page.goto('https://wan.360.cn/', 
                       wait_until='domcontentloaded', 
                       timeout=20000)
        
        print("   导航后URL:", page.url)
        print("   页面标题:", await page.title())
        
        # 等待观察
        print("   等待10秒观察页面...")
        await asyncio.sleep(10)
        
        # 检查页面内容
        print("3️⃣ 检查页面内容...")
        try:
            # 检查页面中的关键元素
            content = await page.content()
            print(f"   页面内容长度: {len(content)} 字符")
            
            if "360游戏" in content:
                print("   ✅ 发现360游戏相关内容")
            else:
                print("   ❌ 未发现360游戏相关内容")
            
            if "注册" in content:
                print("   ✅ 发现注册相关内容")
            else:
                print("   ❌ 未发现注册相关内容")
                
        except Exception as e:
            print(f"   ❌ 页面内容检查失败: {e}")
        
        # 尝试寻找注册按钮
        print("4️⃣ 寻找注册按钮...")
        from src.services.automation.form_selectors import FormSelectors
        
        for selector in FormSelectors.REGISTRATION_BUTTONS:
            try:
                elements = await page.locator(selector).all()
                print(f"   选择器 '{selector}': 找到 {len(elements)} 个元素")
                
                for i, element in enumerate(elements):
                    visible = await element.is_visible()
                    text = await element.inner_text() if visible else "不可见"
                    print(f"      元素{i+1}: {text} ({'可见' if visible else '不可见'})")
                    
            except Exception as e:
                print(f"   选择器 '{selector}': 错误 - {e}")
        
        # 保持开启以便观察
        print("5️⃣ 保持浏览器开启60秒...")
        print("   请观察浏览器窗口中的实际内容")
        await asyncio.sleep(60)
        
        return True
        
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        print("🧹 清理完成")

if __name__ == "__main__":
    success = asyncio.run(step_by_step_debug())
    sys.exit(0 if success else 1)