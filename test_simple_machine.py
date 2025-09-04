#!/usr/bin/env python3
"""
测试简化状态机
Test Simplified State Machine
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.automation.simple_playwright_backend import SimplePlaywrightBackend
from src.models.account import Account

async def test_simple_state_machine():
    """测试简化状态机"""
    username = f"simpletest{int(asyncio.get_event_loop().time())}"
    password = "testpass123"
    
    print("🎯 测试简化状态机")
    print(f"   用户名: {username}")
    print(f"   密码: {password}")
    print("=" * 50)
    
    account = Account(1, username, password)
    backend = SimplePlaywrightBackend()
    
    try:
        print("🚀 开始注册流程...")
        success = await backend.register_account(account)
        
        print("=" * 50)
        print(f"📊 注册结果:")
        print(f"   成功: {'是' if success else '否'}")
        print(f"   账户状态: {account.status}")
        print(f"   账户备注: {account.notes}")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_simple_state_machine()
    print("=" * 60)
    if success:
        print("✅ 简化状态机测试成功")
    else:
        print("❌ 简化状态机测试失败")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)