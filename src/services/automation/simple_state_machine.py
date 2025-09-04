"""
使用 transitions 框架的简化状态机实现
Simplified State Machine Implementation using transitions framework
"""

import asyncio
import logging
from typing import Optional, Callable
from transitions.extensions.asyncio import AsyncMachine
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ...models.account import Account, AccountStatus
from .captcha_handler import CaptchaHandler
from .form_helpers import FormSelectors
from .result_detector import RegistrationResultDetector


class RegistrationMachine:
    """
    使用 transitions 框架的注册状态机
    Registration State Machine using transitions framework
    """
    
    # 定义所有状态
    states = [
        'initializing',
        'navigating', 
        'homepage_ready',
        'opening_form',
        'form_ready',
        'filling_form',
        'submitting',
        'waiting_result',
        'captcha_monitoring',
        'verifying_success',
        'success',
        'failed'
    ]
    
    def __init__(self, account: Account, page: Page):
        """
        初始化状态机
        
        Args:
            account: 要注册的账户
            page: Playwright页面对象
        """
        self.account = account
        self.page = page
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 回调函数
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_captcha_detected: Optional[Callable[[Account, str], None]] = None
        self.on_success: Optional[Callable[[Account, str], None]] = None
        self.on_failed: Optional[Callable[[Account, str], None]] = None
        
        # 验证码处理器
        self.captcha_handler = CaptchaHandler(page, account)
        
        # 重试计数
        self.retry_count = 0
        self.max_retries = 3
        
        # 创建状态机
        self.machine = AsyncMachine(
            model=self,
            states=RegistrationMachine.states,
            initial='initializing',
            auto_transitions=False,
            ignore_invalid_triggers=True,
            send_event=True,
            finalize_event='finalize'
        )
        
        # 定义转换
        self._setup_transitions()
    
    def _setup_transitions(self):
        """设置状态转换"""
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
            
            # 验证码监控结果（用户通过验证码后的结果）
            ['registration_failed', 'captcha_monitoring', 'failed'],   # 账号已注册 或 超时
            ['registration_success', 'captcha_monitoring', 'success'], # 注册成功
            
            # 错误处理转换
            ['fail', '*', 'failed'],
            
            # 重试转换
            ['retry_navigation', 'navigating', 'navigating'],
            ['retry_form', 'opening_form', 'opening_form'],
            ['retry_filling', 'filling_form', 'filling_form'],
            ['retry_submit', 'submitting', 'submitting'],
        ]
        
        # 添加转换到状态机
        self.machine.add_transitions(transitions)
    
    def _log(self, message: str):
        """统一日志方法"""
        self.logger.debug(message)
        if self.on_log:
            self.on_log(message)
    
    def is_terminal(self) -> bool:
        """检查是否到达终态"""
        return self.state in ['success', 'failed']
    
    async def run(self) -> bool:
        """
        运行状态机直到完成
        
        Returns:
            True: 注册成功
            False: 注册失败
        """
        self._log("🚀 开始注册流程")
        
        try:
            # 启动状态机
            await self.start_navigation()
            
            # 运行状态机直到终态
            while not self.is_terminal():
                await asyncio.sleep(0.1)  # 防止CPU占用过高
            
            # 处理最终结果
            if self.state == 'success':
                self.account.mark_success("注册成功")
                if self.on_success:
                    self.on_success(self.account, "注册成功")
                return True
            else:
                self.account.mark_failed("注册失败")
                if self.on_failed:
                    self.on_failed(self.account, "注册失败")
                return False
                
        except Exception as e:
            self._log(f"❌ 状态机运行出错: {e}")
            self.account.mark_failed(f"状态机错误: {str(e)}")
            if self.on_failed:
                self.on_failed(self.account, str(e))
            return False
    
    # =================== 状态处理方法 ===================
    
    async def on_enter_navigating(self, event):
        """进入导航状态"""
        try:
            self._log("📍 开始导航到注册页面")
            self._log(f"   导航前URL: {self.page.url}")
            
            await self.page.goto('https://wan.360.cn/', 
                                wait_until='domcontentloaded', 
                                timeout=20000)
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 验证导航结果
            current_url = self.page.url
            page_title = await self.page.title()
            self._log(f"   导航后URL: {current_url}")
            self._log(f"   页面标题: {page_title}")
            
            if current_url == "about:blank":
                raise Exception("导航失败，页面仍为 about:blank")
            
            if "wan.360.cn" not in current_url:
                self._log(f"⚠️  警告: URL不包含期望的域名")
            
            # 自动转换到下一状态
            await self.navigation_complete()
            
        except Exception as e:
            self._log(f"❌ 导航失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_homepage_ready(self, event):
        """进入首页准备状态"""
        try:
            self._log("🏠 首页准备就绪")
            
            # 等待页面JavaScript加载
            await asyncio.sleep(2)
            
            # 自动点击注册按钮
            await self.click_register()
            
        except Exception as e:
            self._log(f"❌ 首页准备失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_opening_form(self, event):
        """进入打开表单状态"""
        try:
            self._log("📝 点击注册按钮")
            
            # 寻找并点击注册按钮
            button_clicked = False
            for selector in FormSelectors.REGISTRATION_BUTTONS:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.locator(selector).all()
                    
                    for element in elements:
                        if await element.is_visible():
                            # 处理可能的新标签页
                            href = await element.get_attribute('href')
                            target = await element.get_attribute('target')
                            
                            if target == '_blank' or (href and 'reg' in href):
                                if href:
                                    self._log(f"   直接导航到: {href}")
                                    await self.page.goto(href)
                                else:
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
                raise Exception("未找到注册按钮")
            
            # 等待表单出现
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
                await self.form_appeared()
            else:
                # 可能直接跳转到了注册页面
                await self.form_appeared()
                
        except Exception as e:
            self._log(f"❌ 打开表单失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_form_ready(self, event):
        """进入表单准备状态"""
        try:
            self._log("✏️  表单准备就绪，开始填写")
            await self.start_filling()
            
        except Exception as e:
            self._log(f"❌ 表单准备失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_filling_form(self, event):
        """进入填写表单状态"""
        try:
            self._log("📋 填写注册表单")
            
            # 验证输入参数
            self._validate_input_constraints()
            
            # 填写用户名（不允许截断）
            await self._fill_field(
                FormSelectors.USERNAME_FIELDS,
                self.account.username,
                "用户名"
            )
            
            # 填写密码
            await self._fill_field(
                FormSelectors.PASSWORD_FIELDS,
                self.account.password,
                "密码"
            )
            
            # 填写确认密码
            await self._fill_field(
                FormSelectors.CONFIRM_PASSWORD_FIELDS,
                self.account.password,
                "确认密码"
            )
            
            # 勾选条款
            await self._check_terms_checkbox()
            
            self._log("✅ 表单填写完成")
            await self.form_filled()
            
        except Exception as e:
            self._log(f"❌ 表单填写失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_submitting(self, event):
        """进入提交状态"""
        try:
            self._log("🚀 提交注册表单")
            
            # 寻找并点击提交按钮
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
                raise Exception("未找到提交按钮")
            
            # 等待提交处理
            await asyncio.sleep(3)
            
            await self.form_submitted()
            
        except Exception as e:
            self._log(f"❌ 表单提交失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_waiting_result(self, event):
        """进入等待结果状态"""
        try:
            self._log("⏳ 等待注册结果")
            
            # 等待页面响应
            await asyncio.sleep(2)
            
            # 检查是否有验证码
            page_content = await self.page.content()
            
            # 检测验证码
            captcha_indicators = ["验证码", "captcha", "滑动验证"]
            if any(indicator in page_content for indicator in captcha_indicators):
                self._log("🔍 检测到验证码")
                await self.captcha_detected()
                return
            
            # 无验证码，直接检测最终结果
            self._log("✅ 未检测到验证码，直接检测结果")
            
            # 检查账号已注册
            error_indicators = ["该账号已经注册", "用户名已存在", "账号已被占用", "立即登录"]
            if any(indicator in page_content for indicator in error_indicators):
                self._log("⚠️  检测到账号已注册")
                self.account.mark_failed("账号已注册")
                await self.no_captcha_failed()
                return
            
            # 检查注册成功
            success_indicators = ["退出", "logout", "个人中心", "用户中心"]
            if any(indicator in page_content for indicator in success_indicators):
                self._log("🎉 检测到注册成功")
                self.account.mark_success("注册成功")
                await self.no_captcha_success()
                return
            
            # 结果不明确
            self._log("⚠️  注册结果不明确")
            self.account.mark_failed("注册结果不明确")
            await self.no_captcha_failed()
                
        except Exception as e:
            self._log(f"❌ 等待结果失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_captcha_monitoring(self, event):
        """进入验证码监控状态"""
        self._log("🔍 进入验证码监控模式")
        self._log("   请手动完成验证码，系统每5秒检测一次状态")
        
        # 通知UI验证码被检测到
        if self.on_captcha_detected:
            self.on_captcha_detected(self.account, "检测到验证码，需要手动处理")
        
        # 启动监控循环
        asyncio.create_task(self._monitor_captcha_status())
    
    async def _monitor_captcha_status(self):
        """
        监控验证码状态的异步任务
        每5秒检测一次，最大监控120秒（24次检测）
        
        用户通过验证码后的两种结果：
        1. 出现账号已注册 → registration_failed → failed
        2. 执行账号成功注册的检测 → registration_success → success
        3. 120秒超时未通过 → registration_failed → failed
        """
        monitor_count = 0
        max_monitor_time = 120  # 最大监控120秒
        max_checks = max_monitor_time // 5  # 24次检测
        
        self._log(f"🔍 开始验证码监控，每5秒检测一次，最大{max_checks}次检测（{max_monitor_time}秒）")
        
        while self.state == 'captcha_monitoring' and monitor_count < max_checks:
            try:
                await asyncio.sleep(5)  # 每5秒检测一次
                monitor_count += 1
                
                self._log(f"🔍 第{monitor_count}/{max_checks}次验证码状态检测...")
                
                # Step 1: 检查是否超时（120秒 = 24次检测）
                if monitor_count >= max_checks:
                    self._log("⏰ 验证码处理超时（120秒）")
                    self.account.mark_failed("验证码处理超时")
                    await self.registration_failed()
                    return
                
                # 获取当前页面内容
                page_content = await self.page.content()
                
                # Step 2: 检查账号已注册错误（优先级最高）
                error_indicators = [
                    "该账号已经注册", 
                    "用户名已存在",
                    "账号已被占用",
                    "立即登录"
                ]
                
                if any(indicator in page_content for indicator in error_indicators):
                    self._log("⚠️  检测到账号已注册")
                    self.account.mark_failed("账号已注册")
                    await self.registration_failed()
                    return
                
                # Step 3: 检查验证码是否还存在
                captcha_indicators = ["验证码", "captcha", "滑动验证", "验证失败", "重新验证"]
                captcha_still_present = any(indicator in page_content for indicator in captcha_indicators)
                
                if captcha_still_present:
                    # 验证码仍存在，继续等待
                    self._log("⏳ 验证码仍存在，继续等待用户处理...")
                    continue
                
                # Step 4: 验证码已消失，检查注册成功标识
                self._log("✅ 验证码已消失，检查注册结果")
                success_indicators = ["退出", "logout", "个人中心", "用户中心"]
                
                if any(indicator in page_content for indicator in success_indicators):
                    self._log("🎉 检测到注册成功标识")
                    self.account.mark_success("注册成功")
                    await self.registration_success()
                    return
                
                # Step 5: 验证码消失但无明确成功标识
                self._log("⚠️  验证码已消失但结果不明确，标记为失败")
                self.account.mark_failed("注册结果不明确")
                await self.registration_failed()
                return
                    
            except Exception as e:
                self._log(f"❌ 验证码监控出错: {e}")
                self.account.mark_failed(f"验证码监控异常: {e}")
                await self.registration_failed()
                return
        
        # 正常情况不应该到这里，因为上面已经处理了超时情况
        self._log("⏰ 验证码监控结束")
        self.account.mark_failed("验证码监控异常结束")
        await self.registration_failed()
    
    async def on_enter_verifying_success(self, event):
        """进入验证成功状态"""
        try:
            self._log("🔍 验证注册结果")
            
            # 获取页面内容并检测结果
            page_content = await self.page.content()
            
            try:
                success, message = RegistrationResultDetector.detect_registration_result(
                    page_content, self.account
                )
                
                if success:
                    self._log(f"🎉 注册成功: {message}")
                    await self.registration_success()
                else:
                    self._log(f"❌ 注册失败: {message}")
                    await self.registration_failed()
                    
            except Exception as e:
                self._log(f"⚠️  结果检测异常: {e}")
                await self.registration_failed()
                
        except Exception as e:
            self._log(f"❌ 验证结果失败: {e}")
            await self._handle_error(e)
    
    async def on_enter_success(self, event):
        """进入成功状态"""
        self._log("🎉 注册流程成功完成")
    
    async def on_enter_failed(self, event):
        """进入失败状态"""
        self._log("💥 注册流程失败")
    
    # =================== 辅助方法 ===================
    
    async def _fill_field(self, selectors, value, field_name, allow_truncation=False):
        """填写表单字段"""
        filled = False
        final_filled_value = None
        
        for selector in selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=3000)
                elements = await self.page.locator(selector).all()
                
                for element in elements:
                    if await element.is_visible():
                        # 清空字段
                        await element.clear()
                        
                        # 记录输入前状态
                        self._log(f"   📝 准备填写{field_name}: '{value}' (长度: {len(value)})")
                        
                        # 使用type方法逐字符输入，避免被JS截断
                        await element.type(value, delay=50)  # 每个字符间隔50ms
                        
                        # 等待可能的JS处理
                        await asyncio.sleep(0.5)
                        
                        # 验证实际填入的值
                        actual_value = await element.input_value()
                        self._log(f"   🔍 实际填入{field_name}: '{actual_value}' (长度: {len(actual_value)})")
                        
                        # 如果值不匹配
                        if actual_value != value:
                            if allow_truncation and len(actual_value) < len(value) and value.startswith(actual_value):
                                # 允许截断且实际值是期望值的前缀
                                self._log(f"   ⚠️  {field_name}被页面截断，但允许截断：'{actual_value}'")
                                final_filled_value = actual_value
                            else:
                                # 尝试重新填写
                                self._log(f"   ⚠️  {field_name}值不匹配，尝试重新填写")
                                await element.clear()
                                await asyncio.sleep(0.2)
                                await element.fill(value)  # 使用fill方法再试一次
                                await asyncio.sleep(0.3)
                                
                                # 再次验证
                                final_value = await element.input_value()
                                self._log(f"   🔍 重新填写后{field_name}: '{final_value}' (长度: {len(final_value)})")
                                
                                if final_value != value:
                                    if allow_truncation and len(final_value) < len(value) and value.startswith(final_value):
                                        # 重新填写后仍被截断，但允许截断
                                        self._log(f"   ⚠️  {field_name}重填后仍被截断，但允许截断：'{final_value}'")
                                        final_filled_value = final_value
                                    else:
                                        self._log(f"   ❌ {field_name}填写失败：期望 '{value}', 实际 '{final_value}'")
                                        raise Exception(f"{field_name}填写不正确")
                                else:
                                    final_filled_value = final_value
                        else:
                            final_filled_value = actual_value
                        
                        filled = True
                        break
                
                if filled:
                    self._log(f"   ✅ {field_name}填写成功")
                    break
                    
            except PlaywrightTimeoutError:
                continue
        
        if not filled:
            raise Exception(f"无法填写{field_name}字段")
        
        return final_filled_value
    
    def _validate_input_constraints(self):
        """
        验证输入参数是否符合360注册页面的限制
        - 用户名：2-14个字符，支持中英文、数字或"_"
        - 密码：8-20个字符
        用户应该输入正确的长度和格式，错误时提示
        """
        username = self.account.username
        password = self.account.password
        
        # 验证用户名长度
        if len(username) < 2:
            raise Exception(f"用户名长度不足：'{username}' ({len(username)}字符) < 2字符最小要求")
        elif len(username) > 14:
            raise Exception(f"用户名长度超限：'{username}' ({len(username)}字符) > 14字符最大限制")
        
        # 验证用户名字符
        import re
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', username):
            raise Exception(f"用户名格式错误：'{username}' 只支持中英文、数字或下划线(_)")
        
        # 验证密码长度
        if len(password) < 8:
            raise Exception(f"密码长度不足：{len(password)}字符 < 8字符最小要求")
        elif len(password) > 20:
            raise Exception(f"密码长度超限：{len(password)}字符 > 20字符最大限制")
        
        self._log(f"   ✅ 输入验证通过：用户名({len(username)}字符)，密码({len(password)}字符)")
    
    async def _check_terms_checkbox(self):
        """勾选用户条款"""
        for selector in FormSelectors.TERMS_CHECKBOXES:
            try:
                await self.page.wait_for_selector(selector, timeout=3000)
                elements = await self.page.locator(selector).all()
                
                for element in elements:
                    if await element.is_visible() and not await element.is_checked():
                        await element.check()
                        self._log("   ✅ 用户条款勾选成功")
                        return
                        
            except PlaywrightTimeoutError:
                continue
    
    async def _handle_error(self, error):
        """处理错误"""
        self.retry_count += 1
        
        if self.retry_count <= self.max_retries:
            self._log(f"⚠️  第{self.retry_count}次重试")
            # 可以根据需要实现重试逻辑
        else:
            self._log("❌ 超过最大重试次数，转为失败状态")
            await self.fail()