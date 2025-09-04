# 状态机架构开发者指南

## 概述

本文档为开发者提供360账号批量注册系统中状态机实现的完整技术指南。状态机架构提供了清晰的注册流程管理，包括验证码处理、错误恢复和成功验证。

## 快速开始

### 基本使用

```python
# 使用状态机驱动的后端（推荐）
from src.services.automation import PlaywrightBackendV2, AutomationService

# 方式1：通过AutomationService（推荐）
service = AutomationService()
accounts = [Account(1, "user1", "pass1"), Account(2, "user2", "pass2")]
await service.process_accounts_batch(accounts, backend_name="playwright_v2")

# 方式2：直接使用后端
backend = PlaywrightBackendV2()
success = await backend.register_account(account)

# 方式3：直接使用状态机（高级用法）
from src.services.automation import PlaywrightRegistrationStateMachine
state_machine = PlaywrightRegistrationStateMachine(account, page)
success = await state_machine.run_state_machine()
```

### 验证码处理

```python
from src.services.automation import CaptchaHandler

# 高级验证码处理
captcha_handler = CaptchaHandler(page, account)
captcha_handler.set_callbacks(
    on_status_update=handle_status,
    on_user_notification=notify_user,
    on_log=log_message
)

result = await captcha_handler.handle_captcha_workflow(timeout_seconds=300)
print(f"Captcha result: {result}")  # "completed", "timeout", "not_detected", "error"
```

## 核心架构

### 状态机流转图

```
                    Registration State Machine Flow
                    ===============================

    [INITIALIZING] ──────────────────────────────────────────────┐
        │                                                       │
        ▼                                                       │
    [NAVIGATING] ──────── retry failed ──────────────┐          │
        │                                            │          │
        ▼                                            │          │
    [HOMEPAGE_READY] ──────────────────────────────── │          │
        │                                            │          │
        ▼                                            │          │
    [OPENING_FORM] ─── retry failed ─────────────── ├──────► [ERROR]
        │                                            │          │
        ▼                                            │          │
    [FORM_READY] ──────────────────────────────────── │          │
        │                                            │          │
        ▼                                            │          │
    [FILLING_FORM] ─── retry failed ─────────────── │          │
        │                                            │          │
        ▼                                            │          │
    [SUBMITTING] ─────────────────────────────────── │          │
        │                                            │          │
        ▼                                            │          │
    [WAITING_RESULT] ───────────────────────────────             │
        │                                                       │
        ├─── captcha detected ──────────────────────┐           │
        │                                          │           │
        └─── no captcha ───────┐                    │           │
                               │                    │           │
                               ▼                    ▼           │
                        [VERIFYING_SUCCESS]  [CAPTCHA_PENDING] ──┘
                               │                    │
                    ┌──────────┴──────────┐         │
                    │                     │         ▼
                    ▼                     ▼  [CAPTCHA_MONITORING]
              [SUCCESS]               [FAILED]       │
                                                     ├─── timeout ───► [CAPTCHA_TIMEOUT]
                                                     │                       │
                                                     └─── completed ────────▲
                                                            │
                                                            ▼
                                                    [VERIFYING_SUCCESS]
```

### 状态定义

| 状态 | 描述 | 主要操作 | 下一状态 |
|------|------|---------|----------|
| `INITIALIZING` | 初始化浏览器 | 系统准备 | NAVIGATING |
| `NAVIGATING` | 导航到注册页 | 打开wan.360.cn | HOMEPAGE_READY/ERROR |
| `HOMEPAGE_READY` | 首页就绪 | 等待JavaScript加载 | OPENING_FORM |
| `OPENING_FORM` | 打开注册表单 | 点击注册按钮 | FORM_READY/ERROR |
| `FORM_READY` | 表单就绪 | 验证表单元素 | FILLING_FORM |
| `FILLING_FORM` | 填写表单 | 输入用户名/密码 | SUBMITTING/ERROR |
| `SUBMITTING` | 提交表单 | 点击注册按钮 | WAITING_RESULT |
| `WAITING_RESULT` | 等待结果 | 检测验证码/成功 | CAPTCHA_PENDING/VERIFYING_SUCCESS |
| `CAPTCHA_PENDING` | 验证码待处理 | 通知用户 | CAPTCHA_MONITORING |
| `CAPTCHA_MONITORING` | 监控验证码 | 实时检测完成 | VERIFYING_SUCCESS/CAPTCHA_TIMEOUT |
| `CAPTCHA_TIMEOUT` | 验证码超时 | 错误处理 | FAILED |
| `VERIFYING_SUCCESS` | 验证成功 | 检查登录状态 | SUCCESS/FAILED |
| `SUCCESS` | 注册成功 | 成功回调 | 终态 |
| `FAILED` | 注册失败 | 失败回调 | 终态 |
| `ERROR` | 系统错误 | 错误处理 | 终态 |

### 验证码处理流程

```
                    Captcha Handling Flow
                    =====================

    [WAITING_RESULT] ──── captcha detected ────► [CAPTCHA_PENDING]
                                                        │
                                                        ▼
                                              [User Notification]
                                                        │
                                                        ▼
                                            [CAPTCHA_MONITORING]
                                                   ╱         ╲
                                           completed           timeout
                                             ╱                   ╲
                                            ▼                     ▼
                                [VERIFYING_SUCCESS]      [CAPTCHA_TIMEOUT]
                                         │                       │
                                         ▼                       ▼
                               [SUCCESS/FAILED]           [FAILED]
```

## 文件结构

```
src/services/automation/
├── __init__.py                        # 模块导出和架构说明
├── automation_service.py              # 主要协调服务
├── base_backend.py                    # 抽象后端接口
├── playwright_backend.py              # 传统Playwright实现
├── playwright_backend_v2.py           # 状态机驱动实现（推荐）
├── selenium_backend.py                # Selenium实现
├── registration_state_machine.py      # 核心状态机逻辑
├── playwright_state_machine.py        # Playwright状态机实现
├── captcha_handler.py                 # 验证码处理系统
├── form_helpers.py                    # 表单选择器和工具
└── result_detector.py                 # 结果检测器
```

## 详细组件说明

### 1. RegistrationStateMachine

核心状态机类，定义了状态转换规则和回调系统。

**关键方法：**
- `transition_to(state)`: 手动状态转换
- `is_terminal_state()`: 检查是否为终态
- `is_captcha_state()`: 检查是否为验证码状态
- `get_current_state_info()`: 获取状态信息

**状态转换条件：**
```python
# 示例：从WAITING_RESULT转换到CAPTCHA_PENDING的条件
StateTransition(
    RegistrationState.WAITING_RESULT,
    RegistrationState.CAPTCHA_PENDING,
    condition=lambda ctx: ctx.metadata.get('captcha_detected', False),
    action=lambda ctx: [
        ctx.start_captcha_timer(),
        self._log("检测到验证码，等待用户处理")
    ]
)
```

### 2. PlaywrightRegistrationStateMachine

Playwright具体实现，为每个状态提供实际的浏览器自动化逻辑。

**关键特性：**
- **异步执行**: 所有操作都是异步的
- **错误恢复**: 自动重试和错误处理
- **元素等待**: 智能等待机制
- **资源管理**: 正确的清理和释放

**状态处理器示例：**
```python
async def _handle_filling_form(self, context: StateContext):
    """填写表单状态处理"""
    try:
        # 填写用户名
        await self._fill_field(FormSelectors.USERNAME_FIELDS, 
                              context.account.username, "用户名")
        
        # 填写密码
        await self._fill_field(FormSelectors.PASSWORD_FIELDS, 
                              context.account.password, "密码")
        
        # 勾选条款
        await self._check_terms_checkbox()
        
        self.transition_to(RegistrationState.SUBMITTING)
        
    except Exception as e:
        context.increment_attempt()
        if context.should_retry():
            # 重试逻辑
        else:
            # 失败处理
```

### 3. CaptchaHandler & CaptchaMonitor

验证码处理系统，提供智能检测和实时监控。

**支持的验证码类型：**
1. **滑动验证码**: "quc-slide-con" 元素
2. **图像验证码**: "quc-captcha-mask" 元素
3. **拼图验证码**: "请完成下方拼图" 文本
4. **滑块验证码**: "拖动滑块" 文本

**监控策略：**
- 检测间隔：1秒（可配置）
- 默认超时：5分钟（可配置）
- 智能分类：自动识别验证码类型
- 用户通知：非阻塞式提醒

## 错误处理

### 错误类型和处理策略

1. **网络错误**
   - 自动重试（最多3次）
   - 指数退避策略
   - 超时处理

2. **元素定位错误**
   - 多选择器尝试
   - 智能等待
   - 优雅降级

3. **验证码超时**
   - 用户通知
   - 状态保存
   - 清理资源

4. **系统错误**
   - 完整上下文记录
   - 错误状态转换
   - 资源清理

### 重试机制

```python
class StateContext:
    def __init__(self):
        self.attempt_count = 0
        self.max_attempts = 3
    
    def should_retry(self) -> bool:
        return self.attempt_count < self.max_attempts
    
    def increment_attempt(self):
        self.attempt_count += 1
```

## 回调和事件

### 状态机回调

```python
state_machine = PlaywrightRegistrationStateMachine(account, page)

# 设置回调
state_machine.on_state_changed = lambda state, ctx: print(f"State: {state}")
state_machine.on_success = lambda acc, msg: print(f"Success: {acc.username}")
state_machine.on_failed = lambda acc, msg: print(f"Failed: {acc.username}")
state_machine.on_captcha_detected = lambda acc, msg: print(f"Captcha: {msg}")
state_machine.on_log = print
```

### 验证码处理回调

```python
captcha_handler = CaptchaHandler(page, account)

captcha_handler.set_callbacks(
    on_status_update=lambda status, meta: update_ui(status, meta),
    on_user_notification=lambda type, msg: show_notification(type, msg),
    on_log=lambda msg: log_to_file(msg)
)
```

## 性能优化

### 关键性能指标

- **状态转换延迟**: < 100ms
- **验证码检测**: ~100-200ms
- **内存使用**: < 100MB per instance
- **超时处理**: 可配置，默认5分钟

### 优化建议

1. **并发控制**: 限制同时运行的实例数
2. **资源池**: 复用浏览器实例
3. **智能等待**: 避免固定延迟
4. **错误预防**: 主动检测问题

## 调试和测试

### 日志系统

状态机提供详细的日志记录：

```python
# 启用调试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('src.services.automation')
```

### 测试工具

```bash
# 运行状态机测试
python test_state_machine.py

# 测试验证码处理
python -c "
from src.services.automation.captcha_handler import CaptchaHandler
# 测试代码
"
```

### 调试技巧

1. **状态检查**: 使用 `get_current_state_info()` 获取详细状态
2. **上下文分析**: 检查 `context.metadata` 了解转换条件
3. **错误追踪**: 查看 `context.error_message` 获取错误信息
4. **回调监控**: 设置详细的回调函数追踪执行流程

## 常见问题和解决方案

### Q: 状态机卡在某个状态不动

**A**: 检查转换条件是否满足
```python
info = state_machine.get_current_state_info()
print(f"Current state: {info['state']}")
print(f"Context: {info}")
```

### Q: 验证码检测不准确

**A**: 检查页面内容和检测逻辑
```python
captcha_present, captcha_type = await monitor.detect_captcha()
print(f"Detected: {captcha_present}, Type: {captcha_type}")
```

### Q: 内存泄露问题

**A**: 确保资源正确清理
```python
try:
    success = await backend.register_account(account)
finally:
    backend.cleanup()  # 确保清理
```

### Q: 如何扩展新的验证码类型

**A**: 修改 `captcha_handler.py` 中的检测逻辑
```python
def _analyze_captcha_type(self, message: str, page_content: str) -> str:
    if "new-captcha-selector" in message:
        return "新验证码类型"
    # ... 现有逻辑
```

## 迁移指南

### 从传统后端迁移到状态机

1. **更改后端类型**:
```python
# 旧方式
backend = PlaywrightBackend()

# 新方式
backend = PlaywrightBackendV2()
```

2. **移除手动状态管理**:
```python
# 不再需要手动管理状态
# account.mark_processing()  # 删除
# account.mark_captcha_pending()  # 删除
```

3. **使用新的回调系统**:
```python
# 设置状态机回调
state_machine.on_captcha_detected = handle_captcha
```

## 最佳实践

1. **使用PlaywrightBackendV2**: 新项目推荐使用状态机驱动的后端
2. **设置适当的超时**: 根据网络环境调整验证码超时时间
3. **监控资源使用**: 定期检查内存和CPU使用情况
4. **日志记录**: 启用详细日志便于问题诊断
5. **错误处理**: 为所有回调设置错误处理逻辑
6. **并发控制**: 避免同时运行过多实例

## 总结

状态机架构为360账号批量注册提供了：

✅ **清晰的流程管理** - 14个明确定义的状态
✅ **智能验证码处理** - 4种类型的自动检测和监控  
✅ **强大的错误恢复** - 自动重试和优雅降级
✅ **灵活的集成接口** - 完整的回调和事件系统
✅ **优异的可维护性** - 模块化设计和详细文档

通过遵循本指南，开发者可以有效地使用和扩展状态机系统，实现稳定可靠的批量账号注册功能。