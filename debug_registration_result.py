#!/usr/bin/env python3
"""
Debug registration result detection
调试注册结果检测过程
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.automation.playwright_backend_v2 import PlaywrightBackendV2
from src.models.account import Account

async def debug_registration_result():
    """调试注册结果检测"""
    print("🔍 开始调试注册结果检测...")
    
    # 创建测试账户
    account = Account(1, f"debugtest{int(asyncio.get_event_loop().time())}", "password123")
    
    # 创建后端
    backend = PlaywrightBackendV2()
    
    try:
        print("1️⃣ 初始化浏览器...")
        if not await backend._initialize_browser():
            print("❌ 浏览器初始化失败")
            return False
        
        # 创建页面
        page = await backend.browser_context.new_page()
        
        # 运行注册状态机
        print("2️⃣ 运行注册状态机...")
        from src.services.automation.playwright_state_machine import PlaywrightRegistrationStateMachine
        
        state_machine = PlaywrightRegistrationStateMachine(account, page)
        
        # 设置详细日志
        def debug_log(message):
            print(f"   📋 状态机: {message}")
        
        state_machine.on_log = debug_log
        
        # 运行状态机
        success = await state_machine.run_state_machine()
        
        print(f"3️⃣ 状态机完成，结果: {'SUCCESS' if success else 'FAILED'}")
        print(f"   最终状态: {state_machine.current_state}")
        print(f"   账户状态: {account.status}")
        print(f"   账户备注: {account.notes}")
        
        # 获取最终页面内容进行分析
        print("4️⃣ 分析最终页面内容...")
        final_content = await page.content()
        
        # 保存页面内容到文件
        debug_file = project_root / "debug_page_content.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"   页面内容已保存到: {debug_file}")
        
        # 分析页面内容中的关键词
        from src.services.automation.result_detector import RegistrationResultDetector
        
        print("5️⃣ 检测结果分析:")
        print(f"   当前URL: {page.url}")
        print(f"   页面标题: {await page.title()}")
        
        # 检查各种指示器
        content_lower = final_content.lower()
        
        print("\n   成功指示器检查:")
        for indicator in RegistrationResultDetector.SUCCESS_INDICATORS:
            found = indicator in content_lower
            print(f"      {indicator}: {'✅' if found else '❌'}")
        
        print("\n   显式成功消息检查:")
        for message in RegistrationResultDetector.EXPLICIT_SUCCESS_MESSAGES:
            found = message in final_content
            print(f"      {message}: {'✅' if found else '❌'}")
        
        print("\n   已注册消息检查:")
        for message in RegistrationResultDetector.ALREADY_REGISTERED_MESSAGES:
            found = message in final_content
            print(f"      {message}: {'✅' if found else '❌'}")
        
        print("\n   错误消息检查:")
        for message in RegistrationResultDetector.ERROR_MESSAGES:
            found = message in final_content
            print(f"      {message}: {'✅' if found else '❌'}")
        
        print("\n   验证码指示器检查:")
        for category, indicators in RegistrationResultDetector.CAPTCHA_INDICATORS.items():
            print(f"      {category}:")
            for indicator in indicators:
                found = indicator in final_content
                print(f"         {indicator}: {'✅' if found else '❌'}")
        
        # 等待观察
        print("6️⃣ 保持浏览器开启30秒供观察...")
        await asyncio.sleep(30)
        
        return True
        
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
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
    success = await debug_registration_result()
    print("=" * 60)
    if success:
        print("✅ 注册结果调试完成")
    else:
        print("❌ 注册结果调试失败")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)