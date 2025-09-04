"""
Registration result detection logic

Handles the detection and interpretation of registration results,
including success, failure, captcha, and error conditions.
"""

import re
from typing import Tuple
from ...models.account import Account
from ...exceptions import (
    AccountAlreadyExistsError, CaptchaRequiredError, RegistrationFailureError
)
from ...translation_manager import tr


class RegistrationResultDetector:
    """Detects registration results from page content"""
    
    # 精确的验证码检测 - 基于实际HTML特征，避免误检测
    CAPTCHA_INDICATORS = {
        'high_specificity': [
            "quc-slide-con",  # 验证码滑块外层容器 - 高度特异性
            "quc-captcha-mask",  # 验证码遮罩层 - 360独有
            "请完成下方拼图验证后继续",  # 验证码具体提示文本
        ],
        'auxiliary': [
            "quc-body-tip",  # 验证码提示样式类
            "verify-slide-con verify-con",  # 滑动验证码双重类名
            "slide-block",  # 滑动块图片 - 结合其他条件
            "拖动滑块完成拼图"  # 滑动操作指令文本
        ]
    }
    
    # 精确的成功登录检测 - 基于登录后的HTML特征
    SUCCESS_INDICATORS = [
        "login-container",  # 登录成功后的容器ID
        "login-user-info",  # 用户信息区域
        "wan-logout-btn",   # 退出按钮类名 - 登录成功的关键标志
        "退出</a>",         # 退出按钮文本
        "user_info_avatar", # 用户头像链接类名
        "name-text"         # 用户名文本类名
    ]
    
    # 已注册消息检测
    ALREADY_REGISTERED_MESSAGES = [
        "该账号已经注册",
        "账号已存在", 
        "用户名已存在",
        "已注册",
        "用户名已被占用",
        "用户名重复"
    ]
    
    # 显式成功消息
    EXPLICIT_SUCCESS_MESSAGES = [
        "注册成功",
        "登录成功", 
        "欢迎使用",
        "注册完成"
    ]
    
    # 错误消息
    ERROR_MESSAGES = [
        "注册失败",
        "用户名格式不正确",
        "密码格式不正确", 
        "验证码错误",
        "网络错误",
        "系统繁忙",
        "请输入验证码",
        "验证码不能为空"
    ]
    
    @staticmethod
    def detect_registration_result(page_content: str, account: Account) -> Tuple[bool, str]:
        """
        Detect registration result from page content with precise captcha detection
        
        Args:
            page_content: HTML content of the page
            account: Account being registered
            
        Returns:
            Tuple of (success_status, message)
            
        Raises:
            AccountAlreadyExistsError: If account already exists
            CaptchaRequiredError: If captcha is required
            RegistrationFailureError: If registration failed with specific error
        """
        
        # 检测验证码 - 只要检测到一个高特异性指标即可确认
        for indicator in RegistrationResultDetector.CAPTCHA_INDICATORS['high_specificity']:
            if indicator in page_content:
                return False, f"CAPTCHA_DETECTED: {indicator}"
        
        # 辅助验证码检测 - 需要多个条件同时满足
        auxiliary_indicators = RegistrationResultDetector.CAPTCHA_INDICATORS['auxiliary']
        auxiliary_found = [indicator for indicator in auxiliary_indicators[:2] if indicator in page_content]
        if len(auxiliary_found) >= 2:
            return False, "CAPTCHA_DETECTED: slide verification interface"
        
        # 检测成功登录 - 需要多个登录特征同时存在
        login_features_found = sum(
            1 for indicator in RegistrationResultDetector.SUCCESS_INDICATORS 
            if indicator in page_content
        )
        if login_features_found >= 3:  # 至少3个登录特征同时存在
            return True, f"Registration successful - login interface detected ({login_features_found} features)"
        
        # Check for already registered messages
        for message in RegistrationResultDetector.ALREADY_REGISTERED_MESSAGES:
            if message in page_content:
                raise AccountAlreadyExistsError(account.username, message)
        
        # Check for explicit success messages
        for indicator in RegistrationResultDetector.EXPLICIT_SUCCESS_MESSAGES:
            if indicator in page_content:
                return True, f"Registration successful (detected: {indicator})"
        
        # Check for error messages
        for message in RegistrationResultDetector.ERROR_MESSAGES:
            if message in page_content:
                if "验证码" in message:
                    raise CaptchaRequiredError("text_captcha")
                else:
                    raise RegistrationFailureError(message, "validation_error")
        
        # No clear result detected
        return False, "Registration result unclear"