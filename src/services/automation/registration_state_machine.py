"""
Registration state machine for account registration workflow

Provides a clean state-driven approach to manage the complex registration process,
including captcha handling, error recovery, and success verification.

State Flow Diagram:
==================

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

Legend:
-------
│ ▼ ► ─  : Flow direction
[STATE]  : State node  
├─── ── : Conditional branch
─────   : Transition path

State Categories:
- Initial: INITIALIZING → NAVIGATING
- Navigation: HOMEPAGE_READY → OPENING_FORM → FORM_READY  
- Form Processing: FILLING_FORM → SUBMITTING → WAITING_RESULT
- Result Processing: VERIFYING_SUCCESS with captcha branch
- Captcha Flow: CAPTCHA_PENDING → CAPTCHA_MONITORING → (timeout/completed)
- Terminal: SUCCESS, FAILED, ERROR, CAPTCHA_TIMEOUT

Key Features:
- Automatic retry mechanism for transient failures
- Conditional captcha handling with timeout management
- Clear success/failure determination paths
- Error state accessible from any point for critical failures
- State context preservation across transitions
"""

from enum import Enum, auto
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import time
import logging
from ...models.account import Account, AccountStatus
from ...translation_manager import tr


class RegistrationState(Enum):
    """States for account registration state machine"""
    
    # Initial states
    INITIALIZING = auto()        # 初始化浏览器和准备工作
    NAVIGATING = auto()         # 导航到注册页面
    
    # Homepage interaction
    HOMEPAGE_READY = auto()     # 首页加载完成，准备点击注册按钮
    OPENING_FORM = auto()       # 点击注册按钮，等待表单出现
    
    # Form interaction  
    FORM_READY = auto()         # 注册表单已出现，准备填写
    FILLING_FORM = auto()       # 正在填写注册表单
    SUBMITTING = auto()         # 提交注册表单
    
    # Result processing
    WAITING_RESULT = auto()     # 等待注册结果，检测验证码或成功状态
    CAPTCHA_PENDING = auto()    # 检测到验证码，需要用户介入
    CAPTCHA_MONITORING = auto() # 监控验证码完成状态
    CAPTCHA_TIMEOUT = auto()    # 验证码处理超时
    
    # Final verification
    VERIFYING_SUCCESS = auto()  # 验证注册是否成功（检查登录状态）
    
    # Terminal states
    SUCCESS = auto()            # 注册成功
    FAILED = auto()            # 注册失败
    ERROR = auto()             # 发生错误


@dataclass
class StateContext:
    """Context data for state transitions"""
    account: Account
    attempt_count: int = 0
    max_attempts: int = 3
    error_message: str = ""
    captcha_start_time: Optional[float] = None
    captcha_timeout_seconds: float = 300.0  # 5分钟验证码超时
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def increment_attempt(self):
        """增加尝试次数"""
        self.attempt_count += 1
    
    def should_retry(self) -> bool:
        """是否应该重试"""
        return self.attempt_count < self.max_attempts
    
    def start_captcha_timer(self):
        """开始验证码计时"""
        self.captcha_start_time = time.time()
    
    def is_captcha_timeout(self) -> bool:
        """检查验证码是否超时"""
        if self.captcha_start_time is None:
            return False
        return (time.time() - self.captcha_start_time) > self.captcha_timeout_seconds


class StateTransition:
    """Represents a state transition with conditions"""
    
    def __init__(self, from_state: RegistrationState, to_state: RegistrationState, 
                 condition: Optional[Callable[[StateContext], bool]] = None,
                 action: Optional[Callable[[StateContext], None]] = None):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition or (lambda ctx: True)
        self.action = action or (lambda ctx: None)
    
    def can_transition(self, context: StateContext) -> bool:
        """检查是否可以进行状态转换"""
        try:
            return self.condition(context)
        except Exception as e:
            logging.error(f"Error in transition condition: {e}")
            return False
    
    def execute_action(self, context: StateContext):
        """执行转换动作"""
        try:
            self.action(context)
        except Exception as e:
            logging.error(f"Error in transition action: {e}")
            context.error_message = f"Transition action failed: {str(e)}"


class RegistrationStateMachine:
    """
    State machine for managing account registration workflow
    
    Provides a structured approach to handling the complex registration process
    with proper state tracking, error handling, and captcha management.
    """
    
    def __init__(self, account: Account):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # State management
        self.current_state = RegistrationState.INITIALIZING
        self.context = StateContext(account=account)
        
        # Callbacks for external integration
        self.on_state_changed: Optional[Callable[[RegistrationState, StateContext], None]] = None
        self.on_success: Optional[Callable[[Account, str], None]] = None
        self.on_failed: Optional[Callable[[Account, str], None]] = None
        self.on_captcha_detected: Optional[Callable[[Account, str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        
        # Define state transitions
        self.transitions = self._define_transitions()
        
        # State handlers - actions to perform in each state
        self.state_handlers = self._define_state_handlers()
    
    def _define_transitions(self) -> Dict[RegistrationState, list[StateTransition]]:
        """定义状态转换规则"""
        return {
            RegistrationState.INITIALIZING: [
                StateTransition(
                    RegistrationState.INITIALIZING,
                    RegistrationState.NAVIGATING,
                    condition=lambda ctx: True,  # 总是可以转换
                    action=lambda ctx: self._log("开始导航到注册页面")
                )
            ],
            
            RegistrationState.NAVIGATING: [
                StateTransition(
                    RegistrationState.NAVIGATING,
                    RegistrationState.HOMEPAGE_READY,
                    condition=lambda ctx: True,  # 由实现决定
                    action=lambda ctx: self._log("页面导航完成")
                ),
                StateTransition(
                    RegistrationState.NAVIGATING,
                    RegistrationState.ERROR,
                    condition=lambda ctx: not ctx.should_retry(),
                    action=lambda ctx: setattr(ctx, 'error_message', '页面导航失败')
                )
            ],
            
            RegistrationState.HOMEPAGE_READY: [
                StateTransition(
                    RegistrationState.HOMEPAGE_READY,
                    RegistrationState.OPENING_FORM,
                    condition=lambda ctx: True,
                    action=lambda ctx: self._log("点击注册按钮")
                )
            ],
            
            RegistrationState.OPENING_FORM: [
                StateTransition(
                    RegistrationState.OPENING_FORM,
                    RegistrationState.FORM_READY,
                    condition=lambda ctx: True,  # 由实现决定
                    action=lambda ctx: self._log("注册表单已出现")
                ),
                StateTransition(
                    RegistrationState.OPENING_FORM,
                    RegistrationState.ERROR,
                    condition=lambda ctx: not ctx.should_retry(),
                    action=lambda ctx: setattr(ctx, 'error_message', '注册表单加载失败')
                )
            ],
            
            RegistrationState.FORM_READY: [
                StateTransition(
                    RegistrationState.FORM_READY,
                    RegistrationState.FILLING_FORM,
                    condition=lambda ctx: True,
                    action=lambda ctx: self._log("开始填写注册表单")
                )
            ],
            
            RegistrationState.FILLING_FORM: [
                StateTransition(
                    RegistrationState.FILLING_FORM,
                    RegistrationState.SUBMITTING,
                    condition=lambda ctx: True,  # 由实现决定
                    action=lambda ctx: self._log("表单填写完成，准备提交")
                ),
                StateTransition(
                    RegistrationState.FILLING_FORM,
                    RegistrationState.ERROR,
                    condition=lambda ctx: not ctx.should_retry(),
                    action=lambda ctx: setattr(ctx, 'error_message', '表单填写失败')
                )
            ],
            
            RegistrationState.SUBMITTING: [
                StateTransition(
                    RegistrationState.SUBMITTING,
                    RegistrationState.WAITING_RESULT,
                    condition=lambda ctx: True,
                    action=lambda ctx: self._log("表单已提交，等待结果")
                )
            ],
            
            RegistrationState.WAITING_RESULT: [
                StateTransition(
                    RegistrationState.WAITING_RESULT,
                    RegistrationState.CAPTCHA_PENDING,
                    condition=lambda ctx: ctx.metadata.get('captcha_detected', False),
                    action=lambda ctx: [
                        ctx.start_captcha_timer(),
                        self._log("检测到验证码，等待用户处理")
                    ]
                ),
                StateTransition(
                    RegistrationState.WAITING_RESULT,
                    RegistrationState.VERIFYING_SUCCESS,
                    condition=lambda ctx: not ctx.metadata.get('captcha_detected', False),
                    action=lambda ctx: self._log("未检测到验证码，验证注册结果")
                ),
                StateTransition(
                    RegistrationState.WAITING_RESULT,
                    RegistrationState.ERROR,
                    condition=lambda ctx: ctx.metadata.get('submission_failed', False),
                    action=lambda ctx: setattr(ctx, 'error_message', '表单提交失败')
                )
            ],
            
            RegistrationState.CAPTCHA_PENDING: [
                StateTransition(
                    RegistrationState.CAPTCHA_PENDING,
                    RegistrationState.CAPTCHA_MONITORING,
                    condition=lambda ctx: True,
                    action=lambda ctx: self._notify_captcha_detected()
                )
            ],
            
            RegistrationState.CAPTCHA_MONITORING: [
                StateTransition(
                    RegistrationState.CAPTCHA_MONITORING,
                    RegistrationState.VERIFYING_SUCCESS,
                    condition=lambda ctx: not ctx.metadata.get('captcha_present', True),
                    action=lambda ctx: self._log("验证码已完成，验证注册结果")
                ),
                StateTransition(
                    RegistrationState.CAPTCHA_MONITORING,
                    RegistrationState.CAPTCHA_TIMEOUT,
                    condition=lambda ctx: ctx.is_captcha_timeout(),
                    action=lambda ctx: self._log("验证码处理超时")
                ),
                StateTransition(
                    RegistrationState.CAPTCHA_MONITORING,
                    RegistrationState.ERROR,
                    condition=lambda ctx: ctx.metadata.get('captcha_error', False),
                    action=lambda ctx: setattr(ctx, 'error_message', '验证码处理出错')
                )
            ],
            
            RegistrationState.CAPTCHA_TIMEOUT: [
                StateTransition(
                    RegistrationState.CAPTCHA_TIMEOUT,
                    RegistrationState.FAILED,
                    condition=lambda ctx: True,
                    action=lambda ctx: setattr(ctx, 'error_message', '验证码处理超时')
                )
            ],
            
            RegistrationState.VERIFYING_SUCCESS: [
                StateTransition(
                    RegistrationState.VERIFYING_SUCCESS,
                    RegistrationState.SUCCESS,
                    condition=lambda ctx: ctx.metadata.get('registration_success', False),
                    action=lambda ctx: self._log("注册成功验证完成")
                ),
                StateTransition(
                    RegistrationState.VERIFYING_SUCCESS,
                    RegistrationState.FAILED,
                    condition=lambda ctx: ctx.metadata.get('registration_failed', False),
                    action=lambda ctx: self._log("注册失败")
                ),
                StateTransition(
                    RegistrationState.VERIFYING_SUCCESS,
                    RegistrationState.ERROR,
                    condition=lambda ctx: ctx.metadata.get('verification_error', False),
                    action=lambda ctx: setattr(ctx, 'error_message', '注册结果验证出错')
                )
            ],
            
            RegistrationState.ERROR: [
                StateTransition(
                    RegistrationState.ERROR,
                    RegistrationState.FAILED,
                    condition=lambda ctx: True,
                    action=lambda ctx: self._log(f"错误转换为失败: {ctx.error_message}")
                )
            ]
        }
    
    def _define_state_handlers(self) -> Dict[RegistrationState, Callable[[StateContext], None]]:
        """定义每个状态的处理逻辑（由子类实现具体逻辑）"""
        return {
            RegistrationState.INITIALIZING: self._handle_initializing,
            RegistrationState.NAVIGATING: self._handle_navigating,
            RegistrationState.HOMEPAGE_READY: self._handle_homepage_ready,
            RegistrationState.OPENING_FORM: self._handle_opening_form,
            RegistrationState.FORM_READY: self._handle_form_ready,
            RegistrationState.FILLING_FORM: self._handle_filling_form,
            RegistrationState.SUBMITTING: self._handle_submitting,
            RegistrationState.WAITING_RESULT: self._handle_waiting_result,
            RegistrationState.CAPTCHA_MONITORING: self._handle_captcha_monitoring,
            RegistrationState.VERIFYING_SUCCESS: self._handle_verifying_success,
            RegistrationState.SUCCESS: self._handle_success,
            RegistrationState.FAILED: self._handle_failed,
        }
    
    def transition_to(self, new_state: RegistrationState, metadata: Dict[str, Any] = None):
        """手动触发状态转换"""
        if metadata:
            self.context.metadata.update(metadata)
        
        # 查找可用的转换
        available_transitions = self.transitions.get(self.current_state, [])
        for transition in available_transitions:
            if transition.to_state == new_state and transition.can_transition(self.context):
                transition.execute_action(self.context)
                self._change_state(new_state)
                return True
        
        self.logger.warning(f"No valid transition from {self.current_state} to {new_state}")
        return False
    
    def _change_state(self, new_state: RegistrationState):
        """执行状态改变"""
        old_state = self.current_state
        self.current_state = new_state
        
        self._log(f"状态转换: {old_state.name} → {new_state.name}")
        
        # 更新账户状态
        self._update_account_status()
        
        # 通知状态改变
        if self.on_state_changed:
            try:
                self.on_state_changed(new_state, self.context)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
    
    def _update_account_status(self):
        """根据当前状态更新账户状态"""
        state_to_account_status = {
            RegistrationState.INITIALIZING: (AccountStatus.PROCESSING, "初始化注册流程"),
            RegistrationState.NAVIGATING: (AccountStatus.PROCESSING, "导航到注册页面"),
            RegistrationState.HOMEPAGE_READY: (AccountStatus.PROCESSING, "页面准备就绪"),
            RegistrationState.OPENING_FORM: (AccountStatus.PROCESSING, "打开注册表单"),
            RegistrationState.FORM_READY: (AccountStatus.PROCESSING, "准备填写表单"),
            RegistrationState.FILLING_FORM: (AccountStatus.PROCESSING, "填写注册信息"),
            RegistrationState.SUBMITTING: (AccountStatus.PROCESSING, "提交注册表单"),
            RegistrationState.WAITING_RESULT: (AccountStatus.PROCESSING, "等待注册结果"),
            RegistrationState.CAPTCHA_PENDING: (AccountStatus.CAPTCHA_PENDING, "检测到验证码"),
            RegistrationState.CAPTCHA_MONITORING: (AccountStatus.CAPTCHA_PENDING, "等待验证码完成"),
            RegistrationState.CAPTCHA_TIMEOUT: (AccountStatus.FAILED, "验证码处理超时"),
            RegistrationState.VERIFYING_SUCCESS: (AccountStatus.PROCESSING, "验证注册结果"),
            RegistrationState.SUCCESS: (AccountStatus.SUCCESS, "注册成功"),
            RegistrationState.FAILED: (AccountStatus.FAILED, self.context.error_message or "注册失败"),
            RegistrationState.ERROR: (AccountStatus.FAILED, self.context.error_message or "发生错误"),
        }
        
        if self.current_state in state_to_account_status:
            status, message = state_to_account_status[self.current_state]
            if status == AccountStatus.PROCESSING:
                self.context.account.mark_processing(tr(message))
            elif status == AccountStatus.SUCCESS:
                self.context.account.mark_success(tr(message))
            elif status == AccountStatus.FAILED:
                self.context.account.mark_failed(tr(message))
            elif status == AccountStatus.CAPTCHA_PENDING:
                self.context.account.mark_waiting_captcha(tr(message))
    
    def _log(self, message: str):
        """统一日志记录"""
        self.logger.info(f"[{self.context.account.username}] {message}")
        if self.on_log:
            self.on_log(message)
    
    def _notify_captcha_detected(self):
        """通知检测到验证码"""
        if self.on_captcha_detected:
            self.on_captcha_detected(
                self.context.account,
                "检测到验证码，请手动完成验证"
            )
    
    # 状态处理方法（默认实现，子类可重写）
    def _handle_initializing(self, context: StateContext):
        """处理初始化状态 - 子类实现"""
        pass
    
    def _handle_navigating(self, context: StateContext):
        """处理导航状态 - 子类实现"""
        pass
    
    def _handle_homepage_ready(self, context: StateContext):
        """处理首页准备状态 - 子类实现"""
        pass
    
    def _handle_opening_form(self, context: StateContext):
        """处理打开表单状态 - 子类实现"""
        pass
    
    def _handle_form_ready(self, context: StateContext):
        """处理表单准备状态 - 子类实现"""
        pass
    
    def _handle_filling_form(self, context: StateContext):
        """处理填写表单状态 - 子类实现"""
        pass
    
    def _handle_submitting(self, context: StateContext):
        """处理提交状态 - 子类实现"""
        pass
    
    def _handle_waiting_result(self, context: StateContext):
        """处理等待结果状态 - 子类实现"""
        pass
    
    def _handle_captcha_monitoring(self, context: StateContext):
        """处理验证码监控状态 - 子类实现"""
        pass
    
    def _handle_verifying_success(self, context: StateContext):
        """处理验证成功状态 - 子类实现"""
        pass
    
    def _handle_success(self, context: StateContext):
        """处理成功状态"""
        if self.on_success:
            self.on_success(
                self.context.account,
                "账户注册成功"
            )
    
    def _handle_failed(self, context: StateContext):
        """处理失败状态"""
        if self.on_failed:
            self.on_failed(
                self.context.account,
                self.context.error_message or "账户注册失败"
            )
    
    # 公共接口方法
    def is_terminal_state(self) -> bool:
        """检查是否为终态"""
        return self.current_state in [
            RegistrationState.SUCCESS,
            RegistrationState.FAILED
        ]
    
    def is_captcha_state(self) -> bool:
        """检查是否为验证码相关状态"""
        return self.current_state in [
            RegistrationState.CAPTCHA_PENDING,
            RegistrationState.CAPTCHA_MONITORING,
            RegistrationState.CAPTCHA_TIMEOUT
        ]
    
    def get_current_state_info(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        return {
            'state': self.current_state,
            'state_name': self.current_state.name,
            'account_username': self.context.account.username,
            'attempt_count': self.context.attempt_count,
            'error_message': self.context.error_message,
            'is_terminal': self.is_terminal_state(),
            'is_captcha': self.is_captcha_state(),
            'metadata': self.context.metadata.copy()
        }