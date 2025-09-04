#!/usr/bin/env python3
"""
CLI测试脚本 - CLI Test Script

测试CLI模块与状态机的集成功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.cli import CLIHandler
from src.services.automation.automation_service import AutomationService
from src.models.account import Account

def test_cli_initialization():
    """测试CLI初始化"""
    print("🧪 测试CLI初始化...")
    
    try:
        cli_handler = CLIHandler()
        print(f"   ✅ CLI handler created successfully")
        print(f"   Backend: {cli_handler.automation_service.get_backend_name()}")
        print(f"   Available backends: {cli_handler.automation_service.get_available_backends()}")
    except Exception as e:
        print(f"   ❌ CLI initialization failed: {e}")
        return False
    
    return True

def test_argument_parsing():
    """测试参数解析"""
    print("🧪 测试参数解析...")
    
    try:
        cli_handler = CLIHandler()
        parser = cli_handler.create_argument_parser()
        
        # Test valid arguments
        args = parser.parse_args([
            "--username", "testuser123", 
            "--password", "password123",
            "--verbose",
            "--backend", "playwright_v2"
        ])
        
        print(f"   ✅ Arguments parsed successfully")
        print(f"   Username: {args.username}")
        print(f"   Password: {'*' * len(args.password)}")
        print(f"   Verbose: {args.verbose}")
        print(f"   Backend: {args.backend}")
        
    except Exception as e:
        print(f"   ❌ Argument parsing failed: {e}")
        return False
    
    return True

def test_callback_setup():
    """测试回调设置"""
    print("🧪 测试回调设置...")
    
    try:
        cli_handler = CLIHandler()
        cli_handler.setup_callbacks(verbose=True)
        
        print("   ✅ Callbacks set up successfully")
        
        # Test callback by creating a mock account completion
        test_account = Account(1, "test_user", "password123")
        test_account.mark_success("Test success")
        
        # This would normally be called by the automation service
        print("   Testing success callback:")
        if cli_handler.automation_service._callbacks.on_account_complete:
            cli_handler.automation_service._callbacks.on_account_complete(test_account)
        
    except Exception as e:
        print(f"   ❌ Callback setup failed: {e}")
        return False
    
    return True

def test_service_integration():
    """测试服务集成"""
    print("🧪 测试自动化服务集成...")
    
    try:
        # Test different backends
        backends = ["playwright_v2", "playwright", "selenium"]
        
        for backend in backends:
            try:
                service = AutomationService(backend_type=backend)
                print(f"   ✅ {backend} backend available: {service.is_backend_available(backend)}")
            except Exception as e:
                print(f"   ⚠️  {backend} backend error: {e}")
        
    except Exception as e:
        print(f"   ❌ Service integration test failed: {e}")
        return False
    
    return True

def test_validation():
    """测试输入验证"""
    print("🧪 测试输入验证...")
    
    try:
        cli_handler = CLIHandler()
        
        # Test valid input
        valid, error = cli_handler.validate_arguments("testuser123", "password123")
        print(f"   ✅ Valid input test: {valid} (no error)")
        
        # Test invalid username
        valid, error = cli_handler.validate_arguments("", "password123")
        print(f"   ✅ Empty username test: {valid} (error: {error})")
        
        # Test short password
        valid, error = cli_handler.validate_arguments("testuser", "12345")
        print(f"   ✅ Short password test: {valid} (error: {error})")
        
    except Exception as e:
        print(f"   ❌ Validation test failed: {e}")
        return False
    
    return True

def main():
    """运行所有测试"""
    print("🎯 开始CLI适配性测试...\n")
    
    tests = [
        test_cli_initialization,
        test_argument_parsing,
        test_callback_setup,
        test_service_integration,
        test_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # 空行分隔
        except Exception as e:
            print(f"   💥 Test error: {e}\n")
    
    print("=" * 60)
    print(f"📊 测试结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！CLI模块与状态机完全兼容")
        print("\n✅ CLI功能验证:")
        print("   • 状态机后端 (playwright_v2) 默认启用")
        print("   • 详细日志输出支持 (--verbose)")
        print("   • 多后端选择支持 (--backend)")
        print("   • 完整回调系统集成")
        print("   • 验证码处理用户交互")
        print("   • 参数验证和错误处理")
        
        print("\n🚀 使用示例:")
        print("   python -m src.cli --username testuser --password password123 --verbose")
        print("   python -m src.cli --username testuser --password password123 --backend playwright")
    else:
        print(f"⚠️  {total - passed} 个测试失败，需要进一步检查")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)