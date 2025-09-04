#!/usr/bin/env python3
"""
状态机实现测试脚本

验证注册状态机的核心功能和状态转换逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.automation.registration_state_machine import (
    RegistrationStateMachine, RegistrationState, StateContext
)
from src.models.account import Account, AccountStatus

def test_state_machine_creation():
    """测试状态机创建"""
    print("🧪 测试状态机创建...")
    
    account = Account(1, "test_user", "password123")
    state_machine = RegistrationStateMachine(account)
    
    assert state_machine.current_state == RegistrationState.INITIALIZING
    assert state_machine.context.account == account
    assert not state_machine.is_terminal_state()
    
    print("   ✅ 状态机创建成功")

def test_state_transitions():
    """测试状态转换"""
    print("🧪 测试状态转换...")
    
    account = Account(2, "test_user_2", "password456")
    state_machine = RegistrationStateMachine(account)
    
    # 测试正常流程转换
    success = state_machine.transition_to(RegistrationState.NAVIGATING)
    assert success, "应该能够从初始化转换到导航状态"
    assert state_machine.current_state == RegistrationState.NAVIGATING
    
    # 测试完整的状态流程转换
    state_machine.transition_to(RegistrationState.HOMEPAGE_READY)
    state_machine.transition_to(RegistrationState.OPENING_FORM)
    state_machine.transition_to(RegistrationState.FORM_READY)
    state_machine.transition_to(RegistrationState.FILLING_FORM)
    state_machine.transition_to(RegistrationState.SUBMITTING)
    state_machine.transition_to(RegistrationState.WAITING_RESULT)
    
    # 测试验证码流程
    # 设置验证码检测标志
    state_machine.context.metadata['captcha_detected'] = True
    state_machine.transition_to(RegistrationState.CAPTCHA_PENDING)
    assert state_machine.is_captcha_state()
    
    print("   ✅ 状态转换测试通过")

def test_terminal_states():
    """测试终态"""
    print("🧪 测试终态...")
    
    account = Account(3, "success_user", "password789")
    state_machine = RegistrationStateMachine(account)
    
    # 测试成功终态 - 需要先到VERIFYING_SUCCESS状态
    state_machine.transition_to(RegistrationState.NAVIGATING)
    state_machine.transition_to(RegistrationState.HOMEPAGE_READY)
    state_machine.transition_to(RegistrationState.OPENING_FORM)
    state_machine.transition_to(RegistrationState.FORM_READY)
    state_machine.transition_to(RegistrationState.FILLING_FORM)
    state_machine.transition_to(RegistrationState.SUBMITTING)
    state_machine.transition_to(RegistrationState.WAITING_RESULT)
    state_machine.transition_to(RegistrationState.VERIFYING_SUCCESS)
    
    # 设置成功标志并转换到SUCCESS
    state_machine.context.metadata['registration_success'] = True
    state_machine.transition_to(RegistrationState.SUCCESS)
    assert state_machine.is_terminal_state()
    assert account.status == AccountStatus.SUCCESS
    
    # 测试失败终态
    account2 = Account(4, "failed_user", "password000")
    state_machine2 = RegistrationStateMachine(account2)
    state_machine2.context.error_message = "测试失败"
    
    # 先转换到VERIFYING_SUCCESS状态
    state_machine2.transition_to(RegistrationState.NAVIGATING)
    state_machine2.transition_to(RegistrationState.HOMEPAGE_READY)
    state_machine2.transition_to(RegistrationState.OPENING_FORM)
    state_machine2.transition_to(RegistrationState.FORM_READY)
    state_machine2.transition_to(RegistrationState.FILLING_FORM)
    state_machine2.transition_to(RegistrationState.SUBMITTING)
    state_machine2.transition_to(RegistrationState.WAITING_RESULT)
    state_machine2.transition_to(RegistrationState.VERIFYING_SUCCESS)
    
    # 设置失败标志并转换到FAILED
    state_machine2.context.metadata['registration_failed'] = True
    state_machine2.transition_to(RegistrationState.FAILED)
    
    assert state_machine2.is_terminal_state()
    assert account2.status == AccountStatus.FAILED
    
    print("   ✅ 终态测试通过")

def test_context_management():
    """测试上下文管理"""
    print("🧪 测试上下文管理...")
    
    account = Account(5, "context_user", "passwordABC")
    state_machine = RegistrationStateMachine(account)
    
    # 测试尝试次数
    context = state_machine.context
    context.increment_attempt()
    context.increment_attempt()
    
    assert context.attempt_count == 2
    assert context.should_retry()  # 默认最大3次
    
    context.increment_attempt()
    assert not context.should_retry()  # 已达最大次数
    
    # 测试验证码计时
    context.start_captcha_timer()
    assert context.captcha_start_time is not None
    assert not context.is_captcha_timeout()  # 刚开始不应该超时
    
    print("   ✅ 上下文管理测试通过")

def test_state_info():
    """测试状态信息获取"""
    print("🧪 测试状态信息获取...")
    
    account = Account(6, "info_user", "passwordXYZ")
    state_machine = RegistrationStateMachine(account)
    
    info = state_machine.get_current_state_info()
    
    assert info['state'] == RegistrationState.INITIALIZING
    assert info['account_username'] == "info_user"
    assert info['attempt_count'] == 0
    assert not info['is_terminal']
    assert not info['is_captcha']
    
    print("   ✅ 状态信息测试通过")

def main():
    """运行所有测试"""
    print("🎯 开始状态机测试...\n")
    
    try:
        test_state_machine_creation()
        test_state_transitions()
        test_terminal_states()
        test_context_management()
        test_state_info()
        
        print("\n🎉 所有状态机测试通过！")
        print("\n📊 状态机功能验证:")
        print("   • ✅ 状态机创建和初始化")
        print("   • ✅ 状态转换和条件检查")
        print("   • ✅ 终态处理和账户状态同步")
        print("   • ✅ 验证码相关状态管理")
        print("   • ✅ 上下文数据管理")
        print("   • ✅ 状态信息查询")
        
        print("\n🚀 状态机架构优势:")
        print("   • 清晰的状态定义和转换规则")
        print("   • 强大的验证码处理能力")
        print("   • 完善的错误处理和重试机制")
        print("   • 灵活的回调和通知系统")
        print("   • 易于调试和监控的状态跟踪")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)