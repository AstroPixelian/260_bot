"""
360账号注册状态机流转图（修正版）
Registration State Machine Flow Diagram (Corrected)
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
9. captcha_monitoring - 验证码监控（等待用户手工处理）
10. success           - 账号注册成功（终态）
11. failed            - 账号注册失败（终态）

正常流程（无验证码）:
==================
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
    ↓ no_captcha（未检测到验证码）
success（直接检测到注册成功）
或
failed（直接检测到注册失败）

验证码流程:
==========
waiting_result
    ↓ captcha_detected（检测到验证码）
captcha_monitoring
    ↓ （等待用户手工通过验证码，每5秒检测一次）
    
用户通过验证码后的两种结果:
========================

结果1: 账号已注册
captcha_monitoring（验证码消失）
    ↓ 检测页面内容包含："该账号已经注册"、"立即登录"等
    ↓ registration_failed（账号注册失败）
failed

结果2: 注册成功
captcha_monitoring（验证码消失）
    ↓ 检测页面内容包含："退出"、"个人中心"等成功标识
    ↓ registration_success（账号注册成功）
success

结果3: 超时失败
captcha_monitoring
    ↓ 等待120秒后用户仍未通过验证码
    ↓ registration_failed（超时失败）
failed（释放资源）
"""

# ==================== 转换规则定义 ====================

"""
transitions = [
    # 基本流程转换
    ['start_navigation', 'initializing', 'navigating'],
    ['navigation_complete', 'navigating', 'homepage_ready'], 
    ['click_register', 'homepage_ready', 'opening_form'],
    ['form_appeared', 'opening_form', 'form_ready'],
    ['start_filling', 'form_ready', 'filling_form'],
    ['form_filled', 'filling_form', 'submitting'],
    ['form_submitted', 'submitting', 'waiting_result'],
    
    # 无验证码分支
    ['no_captcha_success', 'waiting_result', 'success'],    # 直接成功
    ['no_captcha_failed', 'waiting_result', 'failed'],      # 直接失败
    
    # 验证码分支
    ['captcha_detected', 'waiting_result', 'captcha_monitoring'],
    
    # 验证码监控结果（从captcha_monitoring出来的三种情况）
    ['registration_failed', 'captcha_monitoring', 'failed'],   # 账号已注册 或 超时
    ['registration_success', 'captcha_monitoring', 'success'], # 注册成功
    
    # 错误处理转换
    ['fail', '*', 'failed'],
]
"""

# ==================== 验证码监控逻辑 ====================

"""
验证码监控状态 (captcha_monitoring):
================================
1. 进入状态时：
   - 显示提示："请手动完成验证码，系统每5秒检测一次状态"
   - 通知UI验证码被检测到
   - 启动异步监控任务，最大监控120秒（24次检测）

2. 每5秒检测逻辑（按优先级顺序）：
   Step 1: 检查是否超时（120秒 = 24次检测）
   - 如果超时 → 标记"验证码处理超时" → registration_failed → failed
   
   Step 2: 检查账号已注册错误（优先级最高）
   - 检测关键词：["该账号已经注册", "用户名已存在", "账号已被占用", "立即登录"]
   - 如果发现 → 标记"账号已注册" → registration_failed → failed
   
   Step 3: 检查验证码是否还存在
   - 验证码指示器：["验证码", "captcha", "滑动验证", "验证失败", "重新验证"]
   - 如果仍存在 → 继续等待用户处理
   
   Step 4: 验证码已消失，检查注册成功标识
   - 成功指示器：["退出", "logout", "个人中心", "用户中心"]
   - 如果发现 → 标记"注册成功" → registration_success → success
   
   Step 5: 验证码消失但无明确成功标识
   - 标记为"注册结果不明确" → registration_failed → failed

3. 用户通过验证码后的两种结果：
   结果1: 账号已注册
   - 用户通过验证码 → 页面显示"该账号已经注册"等提示 → registration_failed → failed
   
   结果2: 注册成功  
   - 用户通过验证码 → 页面显示"退出"、"个人中心"等成功标识 → registration_success → success
   
   结果3: 超时失败
   - 用户120秒内未通过验证码 → registration_failed → failed（释放资源）

4. 资源释放：
   - 无论成功或失败，都会在相应的终态处理器中清理浏览器资源
"""

# ==================== 状态处理器映射 ====================

"""
on_enter_initializing       → 初始化准备
on_enter_navigating         → 导航到wan.360.cn
on_enter_homepage_ready     → 等待页面加载
on_enter_opening_form       → 点击注册按钮
on_enter_form_ready         → 准备填写表单
on_enter_filling_form       → 填写用户名、密码等
on_enter_submitting         → 提交表单
on_enter_waiting_result     → 检测验证码或直接结果
on_enter_captcha_monitoring → 启动验证码监控循环
on_enter_success            → 注册成功，记录结果
on_enter_failed             → 注册失败，记录原因
"""