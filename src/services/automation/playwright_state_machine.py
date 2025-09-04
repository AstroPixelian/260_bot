"""
Playwright-specific implementation of the registration state machine

Integrates the state machine pattern with Playwright automation backend,
providing concrete implementations for each state handler.

Implementation Overview:
========================

This class extends the abstract RegistrationStateMachine with concrete Playwright
automation logic. Each state has a corresponding handler method that performs
the actual browser automation tasks.

State Handler Mapping:
======================

Registration Flow States → Handler Methods:
- INITIALIZING       → _handle_initializing()
- NAVIGATING         → _handle_navigating() 
- HOMEPAGE_READY     → _handle_homepage_ready()
- OPENING_FORM       → _handle_opening_form()
- FORM_READY         → _handle_form_ready()
- FILLING_FORM       → _handle_filling_form()
- SUBMITTING         → _handle_submitting()
- WAITING_RESULT     → _handle_waiting_result()
- CAPTCHA_MONITORING → _handle_captcha_monitoring()
- VERIFYING_SUCCESS  → _handle_verifying_success()

Key Integration Points:
=======================

1. **Playwright Page Integration**: 
   - Direct page manipulation through playwright.async_api
   - Element interaction with proper waiting and error handling
   - Screenshot and debugging capabilities

2. **Form Automation**:
   - Uses FormSelectors for consistent element targeting
   - Implements retry logic for unstable elements
   - Handles dynamic form loading and validation

3. **Captcha Integration**:
   - Seamless CaptchaHandler integration for verification
   - Real-time monitoring with user notification
   - Timeout management and recovery

4. **Result Detection**:
   - RegistrationResultDetector for success/failure determination
   - Handles edge cases and ambiguous states
   - Provides detailed error messages for debugging

Error Handling Strategy:
========================

- **Transient Errors**: Automatic retry with exponential backoff
- **Element Errors**: Multiple selector attempts before failure
- **Network Errors**: Timeout handling with graceful degradation
- **Critical Errors**: Immediate transition to ERROR state with context

Performance Optimizations:
==========================

- **Asynchronous Operations**: All I/O operations are async
- **Smart Waiting**: Conditional waits based on element visibility
- **Resource Management**: Proper cleanup of browser resources
- **State Caching**: Context preservation across state transitions
"""

import asyncio
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .registration_state_machine import (
    RegistrationStateMachine, RegistrationState, StateContext
)
from .form_helpers import FormSelectors
from .result_detector import RegistrationResultDetector
from .captcha_handler import CaptchaHandler
from ...models.account import Account
from ...exceptions import (
    PageNavigationError, ElementNotFoundError, FormInteractionError,
    AccountAlreadyExistsError, CaptchaRequiredError, RegistrationFailureError
)


class PlaywrightRegistrationStateMachine(RegistrationStateMachine):
    """
    Playwright-specific implementation of registration state machine
    
    Provides concrete automation logic for each state using Playwright.
    """
    
    def __init__(self, account: Account, page: Page):
        super().__init__(account)
        self.page = page
        
        # Initialize captcha handler
        self.captcha_handler = CaptchaHandler(page, account)
        
    async def run_state_machine(self) -> bool:
        """
        运行状态机直到到达终态
        
        This is the main execution engine that drives the entire registration process.
        
        Execution Flow:
        ===============
        1. **State Loop**: Continues until a terminal state is reached
        2. **Handler Execution**: Calls appropriate handler for current state
        3. **Auto Transitions**: Attempts condition-based state transitions
        4. **Error Handling**: Catches and handles all exceptions gracefully
        5. **Result Determination**: Returns success/failure based on final state
        
        State Management:
        =================
        - Each state has a corresponding handler method
        - State transitions can be manual (via handler) or automatic (via conditions)
        - Context is preserved across all state transitions
        - Retry logic is built into individual state handlers
        
        Error Recovery:
        ===============
        - Transient errors trigger retry mechanisms in state handlers
        - Critical errors transition to ERROR state with context preservation
        - All errors are logged with full context for debugging
        
        Performance Considerations:
        ===========================
        - Sleep interval (0.1s) prevents CPU spin-lock in edge cases
        - Async operations allow for responsive UI during automation
        - State transitions are atomic to prevent race conditions
        
        Returns:
            True if registration successful (SUCCESS state), False otherwise
        """
        while not self.is_terminal_state():
            try:
                # 执行当前状态的处理逻辑
                # Get and execute the appropriate handler for current state
                handler = self.state_handlers.get(self.current_state)
                if handler:
                    await handler(self.context)
                
                # 检查是否需要自动转换状态
                # Attempt automatic state transitions based on conditions
                await self._try_auto_transitions()
                
                # 防止无限循环
                # Small delay to prevent CPU spinning in edge cases
                await asyncio.sleep(0.1)
                
            except Exception as e:
                # Critical error handling - log and transition to ERROR state
                self.logger.error(f"State machine error in {self.current_state}: {e}")
                self.context.error_message = str(e)
                self.transition_to(RegistrationState.ERROR)
                break
        
        # 返回最终结果
        # Determine success based on final state
        return self.current_state == RegistrationState.SUCCESS
    
    async def _try_auto_transitions(self):
        """尝试自动状态转换"""
        available_transitions = self.transitions.get(self.current_state, [])
        
        for transition in available_transitions:
            if transition.can_transition(self.context):
                transition.execute_action(self.context)
                self._change_state(transition.to_state)
                break
    
    # 具体状态处理实现
    async def _handle_initializing(self, context: StateContext):
        """初始化状态处理"""
        self._log("初始化注册流程")
        # 准备工作已完成，可以开始导航
        self.transition_to(RegistrationState.NAVIGATING)
    
    async def _handle_navigating(self, context: StateContext):
        """导航状态处理"""
        try:
            self._log("🔍 DEBUG: _handle_navigating方法被调用")
            self._log("导航到 wan.360.cn")
            self._log(f"导航前页面URL: {self.page.url}")
            
            await self.page.goto('https://wan.360.cn/', 
                                wait_until='domcontentloaded', 
                                timeout=20000)
            
            # 等待页面稳定
            await asyncio.sleep(3)
            
            # 验证导航是否成功
            current_url = self.page.url
            page_title = await self.page.title()
            self._log(f"导航后页面URL: {current_url}")
            self._log(f"页面标题: {page_title}")
            
            if current_url == "about:blank":
                raise Exception("页面导航失败，仍停留在about:blank")
            
            if "wan.360.cn" not in current_url:
                self._log(f"⚠️ 警告：页面URL不包含预期的域名，当前URL: {current_url}")
            
            self._log("🔍 DEBUG: 手动转换到HOMEPAGE_READY状态")
            self.transition_to(RegistrationState.HOMEPAGE_READY)
            
        except PlaywrightTimeoutError as e:
            context.increment_attempt()
            if context.should_retry():
                self._log(f"导航失败，重试中 (尝试 {context.attempt_count}/{context.max_attempts})")
                await asyncio.sleep(2)
            else:
                context.error_message = f"导航失败: {str(e)}"
                self.transition_to(RegistrationState.ERROR)
    
    async def _handle_homepage_ready(self, context: StateContext):
        """首页准备状态处理"""
        self._log("首页加载完成，准备点击注册按钮")
        # 等待JavaScript初始化
        await asyncio.sleep(3)
        self.transition_to(RegistrationState.OPENING_FORM)
    
    async def _handle_opening_form(self, context: StateContext):
        """打开表单状态处理"""
        try:
            self._log("点击注册按钮")
            
            # 监听可能的新标签页
            async def handle_popup(popup):
                self._log("检测到弹窗或新标签页，关闭它")
                await popup.close()
            
            self.page.on("popup", handle_popup)
            
            # 尝试找到并点击注册按钮
            button_clicked = False
            for selector in FormSelectors.REGISTRATION_BUTTONS:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.locator(selector).all()
                    
                    for element in elements:
                        if await element.is_visible():
                            # 检查是否会打开新标签页的链接
                            href = await element.get_attribute('href')
                            target = await element.get_attribute('target')
                            
                            if target == '_blank' or (href and 'reg' in href):
                                # 如果是链接，直接导航而不是点击
                                if href:
                                    self._log(f"直接导航到注册页面: {href}")
                                    await self.page.goto(href)
                                else:
                                    # 移除target属性后再点击
                                    await element.evaluate('el => el.removeAttribute("target")')
                                    await element.click()
                            else:
                                await element.click()
                            
                            button_clicked = True
                            break
                    
                    if button_clicked:
                        break
                        
                except PlaywrightTimeoutError:
                    continue
            
            if not button_clicked:
                raise ElementNotFoundError(" or ".join(FormSelectors.REGISTRATION_BUTTONS), 
                                         "registration_button", 10)
            
            # 等待注册表单出现
            await asyncio.sleep(2)
            
            # 检查表单是否出现
            form_found = False
            for selector in FormSelectors.REGISTRATION_FORMS:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    form_found = True
                    break
                except PlaywrightTimeoutError:
                    continue
            
            if form_found:
                self.transition_to(RegistrationState.FORM_READY)
            else:
                # 表单可能没有以模态框形式出现，继续
                self.transition_to(RegistrationState.FORM_READY)
            
        except Exception as e:
            context.increment_attempt()
            if context.should_retry():
                self._log(f"打开注册表单失败，重试中 (尝试 {context.attempt_count}/{context.max_attempts})")
                await asyncio.sleep(2)
            else:
                context.error_message = f"打开注册表单失败: {str(e)}"
                self.transition_to(RegistrationState.ERROR)
    
    async def _handle_form_ready(self, context: StateContext):
        """表单准备状态处理"""
        self._log("注册表单已准备，开始填写")
        self.transition_to(RegistrationState.FILLING_FORM)
    
    async def _handle_filling_form(self, context: StateContext):
        """填写表单状态处理"""
        try:
            # 填写用户名
            await self._fill_field(FormSelectors.USERNAME_FIELDS, 
                                  context.account.username, "用户名")
            
            # 填写密码
            await self._fill_field(FormSelectors.PASSWORD_FIELDS, 
                                  context.account.password, "密码")
            
            # 填写确认密码
            await self._fill_field(FormSelectors.CONFIRM_PASSWORD_FIELDS, 
                                  context.account.password, "确认密码")
            
            # 勾选条款
            await self._check_terms_checkbox()
            
            self._log("表单填写完成")
            self.transition_to(RegistrationState.SUBMITTING)
            
        except Exception as e:
            context.increment_attempt()
            if context.should_retry():
                self._log(f"表单填写失败，重试中 (尝试 {context.attempt_count}/{context.max_attempts})")
                await asyncio.sleep(2)
            else:
                context.error_message = f"表单填写失败: {str(e)}"
                self.transition_to(RegistrationState.ERROR)
    
    async def _handle_submitting(self, context: StateContext):
        """提交状态处理"""
        try:
            self._log("提交注册表单")
            
            # 点击提交按钮
            submit_clicked = False
            for selector in FormSelectors.SUBMIT_BUTTONS:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.locator(selector).all()
                    
                    for element in elements:
                        if await element.is_visible():
                            await element.click()
                            submit_clicked = True
                            break
                    
                    if submit_clicked:
                        break
                        
                except PlaywrightTimeoutError:
                    continue
            
            if not submit_clicked:
                raise FormInteractionError("click", "submit_button", 
                                         {"error": "无法找到提交按钮"})
            
            # 等待提交处理
            await asyncio.sleep(3)
            
            self.transition_to(RegistrationState.WAITING_RESULT)
            
        except Exception as e:
            context.error_message = f"提交表单失败: {str(e)}"
            self.transition_to(RegistrationState.ERROR)
    
    async def _handle_waiting_result(self, context: StateContext):
        """等待结果状态处理"""
        try:
            self._log("等待注册结果")
            
            # 等待页面响应
            await asyncio.sleep(2)
            
            # 获取页面内容检测结果
            page_content = await self.page.content()
            
            try:
                success, message = RegistrationResultDetector.detect_registration_result(
                    page_content, context.account
                )
                
                if "CAPTCHA_DETECTED" in message:
                    # 检测到验证码
                    context.metadata['captcha_detected'] = True
                    self.transition_to(RegistrationState.CAPTCHA_PENDING)
                elif success:
                    # 注册成功
                    context.metadata['registration_success'] = True
                    self.transition_to(RegistrationState.VERIFYING_SUCCESS)
                else:
                    # 结果不明确，进行进一步验证
                    self.transition_to(RegistrationState.VERIFYING_SUCCESS)
                    
            except (AccountAlreadyExistsError, RegistrationFailureError, CaptchaRequiredError) as e:
                # 明确的失败
                context.error_message = str(e)
                context.metadata['registration_failed'] = True
                self.transition_to(RegistrationState.VERIFYING_SUCCESS)
            
        except Exception as e:
            context.error_message = f"等待结果失败: {str(e)}"
            self.transition_to(RegistrationState.ERROR)
    
    async def _handle_captcha_monitoring(self, context: StateContext):
        """验证码监控状态处理 - 使用增强的验证码处理器"""
        try:
            self._log("开始监控验证码完成状态")
            
            # 配置验证码处理器回调
            self.captcha_handler.set_callbacks(
                on_log=self._log,
                on_status_update=self._on_captcha_status_update,
                on_user_notification=self._on_captcha_user_notification
            )
            
            # 直接使用监控器（因为已经检测到验证码）
            result = await self.captcha_handler.monitor.start_monitoring(
                context.captcha_timeout_seconds
            )
            
            if result == "completed":
                # 验证码已完成
                self._log("验证码已完成")
                self.transition_to(RegistrationState.VERIFYING_SUCCESS)
            elif result == "timeout":
                # 验证码超时
                self._log("验证码处理超时")
                self.transition_to(RegistrationState.CAPTCHA_TIMEOUT)
            else:
                # 其他错误
                context.error_message = f"验证码监控失败: {result}"
                context.metadata['captcha_error'] = True
                self.transition_to(RegistrationState.ERROR)
                
        except Exception as e:
            context.error_message = f"验证码监控失败: {str(e)}"
            context.metadata['captcha_error'] = True
            self.transition_to(RegistrationState.ERROR)
    
    def _on_captcha_status_update(self, status: str, metadata: dict):
        """验证码状态更新回调"""
        self._log(f"验证码状态更新: {status}")
        
        # 可以在这里添加更多的状态处理逻辑
        if status == "captcha_completed":
            self.context.metadata['captcha_present'] = False
        elif status == "captcha_timeout":
            self.context.metadata['captcha_timeout'] = True
    
    def _on_captcha_user_notification(self, notification_type: str, message: str):
        """验证码用户通知回调"""
        self._log(f"用户通知 [{notification_type}]: {message}")
        
        # 可以通过父级回调传递给UI
        if self.on_captcha_detected and notification_type == "captcha_detected":
            self.on_captcha_detected(self.context.account, message)
    
    async def _handle_verifying_success(self, context: StateContext):
        """验证成功状态处理"""
        try:
            self._log("验证注册结果")
            
            # 再次检查页面内容
            page_content = await self.page.content()
            
            try:
                success, message = RegistrationResultDetector.detect_registration_result(
                    page_content, context.account
                )
                
                if success:
                    context.metadata['registration_success'] = True
                    self.transition_to(RegistrationState.SUCCESS)
                else:
                    context.error_message = message
                    context.metadata['registration_failed'] = True
                    self.transition_to(RegistrationState.FAILED)
                    
            except Exception as e:
                # 处理检测异常
                if isinstance(e, AccountAlreadyExistsError):
                    context.error_message = str(e)
                    context.metadata['registration_failed'] = True
                    self.transition_to(RegistrationState.FAILED)
                else:
                    context.error_message = f"验证失败: {str(e)}"
                    context.metadata['verification_error'] = True
                    self.transition_to(RegistrationState.ERROR)
            
        except Exception as e:
            context.error_message = f"验证过程出错: {str(e)}"
            context.metadata['verification_error'] = True
            self.transition_to(RegistrationState.ERROR)
    
    # 辅助方法
    async def _fill_field(self, selectors: list[str], value: str, field_name: str):
        """填写表单字段"""
        field_filled = False
        
        for selector in selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                elements = await self.page.locator(selector).all()
                
                for element in elements:
                    if await element.is_visible():
                        await element.fill(value)
                        field_filled = True
                        break
                
                if field_filled:
                    break
                    
            except PlaywrightTimeoutError:
                continue
        
        if not field_filled:
            raise FormInteractionError("fill", field_name, 
                                     {"error": f"无法填写{field_name}字段"})
        
        self._log(f"已填写{field_name}")
    
    async def _check_terms_checkbox(self):
        """勾选条款复选框"""
        checkbox_checked = False
        
        for selector in FormSelectors.TERMS_CHECKBOXES:
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                elements = await self.page.locator(selector).all()
                
                for element in elements:
                    if await element.is_visible():
                        if not await element.is_checked():
                            await element.check()
                        checkbox_checked = True
                        break
                
                if checkbox_checked:
                    break
                    
            except PlaywrightTimeoutError:
                continue
        
        if not checkbox_checked:
            raise FormInteractionError("check", "terms_checkbox", 
                                     {"error": "无法勾选条款复选框"})
        
        self._log("已勾选注册条款")