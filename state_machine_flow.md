"""
360账号注册状态机流转图
Registration State Machine Flow Diagram
"""

# ==================== 状态机流转图 ====================

"""
状态定义:
========
1. initializing       - 初始化状态
2. navigating         - 导航到注册页面
3. homepage_ready     - 首页准备就绪
4. opening_form       - 打开注册表单
5. form_ready         - 表单准备就绪
6. filling_form       - 填写表单
7. submitting         - 提交表单
8. waiting_result     - 等待结果
9. captcha_monitoring - 验证码监控
10. verifying_success - 验证成功
11. success           - 注册成功（终态）
12. failed            - 注册失败（终态）

正常流程:
========
initializing
    ↓ start_navigation
navigating
    ↓ navigation_complete
homepage_ready
    ↓ click_register
opening_form
    ↓ form_appeared
form_ready
    ↓ start_filling
filling_form
    ↓ form_filled
submitting
    ↓ form_submitted
waiting_result
    ↓ (两个分支)
    
分支A: 无验证码流程
waiting_result
    ↓ no_captcha
verifying_success
    ↓ registration_success / registration_failed
success / failed

分支B: 有验证码流程
waiting_result
    ↓ captcha_detected
captcha_monitoring (每5秒检测一次)
    ↓ (三个可能结果)
    
结果1: 账号已注册
captcha_monitoring
    ↓ captcha_failed
failed

结果2: 验证码通过且注册成功
captcha_monitoring
    ↓ captcha_success
success

结果3: 验证码消失但结果不明确
captcha_monitoring
    ↓ captcha_solved
verifying_success
    ↓ registration_success / registration_failed
success / failed

错误处理:
========
任何状态
    ↓ fail (通用错误转换)
failed

重试机制:
========
navigating → retry_navigation → navigating
opening_form → retry_form → opening_form
filling_form → retry_filling → filling_form
submitting → retry_submit → submitting
"""

# ==================== 关键转换点说明 ====================

"""
1. 验证码检测关键点 (waiting_result):
   - 检测页面内容是否包含验证码标识
   - 有验证码 → captcha_monitoring
   - 无验证码 → verifying_success

2. 验证码监控关键点 (captcha_monitoring):
   优先级顺序：
   a) 检查账号已注册错误 → captcha_failed → failed
   b) 检查验证码是否消失:
      - 仍存在 → 继续监控
      - 已消失 → 检查成功标识:
        * 有成功标识 → captcha_success → success  
        * 无明确标识 → captcha_solved → verifying_success

3. 结果验证关键点 (verifying_success):
   - 使用 RegistrationResultDetector 检测最终结果
   - 成功 → registration_success → success
   - 失败 → registration_failed → failed
"""