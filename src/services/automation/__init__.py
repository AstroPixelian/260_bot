"""
Automation service module for batch account registration

This module provides a clean separation between different automation backends
(Playwright, Selenium) while maintaining a unified interface. Now includes
state machine-based registration workflow management.

Architecture Overview:
======================

                    Automation Module Architecture
                    ==============================

    Application Layer (GUI/ViewModel)
                    │
                    ▼
    ┌───────────────────────────────────────────────────┐
    │            AutomationService                      │ ← Main coordinator
    │  (Factory + Backend Management + Callbacks)       │
    └───────────────────┬───────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────┐
    │            AutomationBackend                    │ ← Abstract interface
    │         (Base class for all backends)           │
    └─────────────────┬─────────────┬─────────────────┘
                      │             │
                      ▼             ▼
    ┌─────────────────────┐  ┌─────────────────────────┐
    │  PlaywrightBackend  │  │   PlaywrightBackendV2   │ ← State machine based
    │    (Legacy impl)    │  │  (State machine impl)   │
    └─────────────────────┘  └─────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────┐
    │     PlaywrightRegistrationStateMachine          │ ← Core state machine
    │           (State-driven workflow)               │
    └─────────────────┬───────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────────────┐
    │          CaptchaHandler/Monitor                 │ ← Captcha processing
    │        (Enhanced captcha management)            │
    └─────────────────────────────────────────────────┘

    Supporting Components:
    ├── FormHelpers      ← Common selectors and utilities
    ├── ResultDetector   ← Registration result detection
    └── SeleniumBackend  ← Alternative backend implementation

Component Responsibilities:
===========================

1. **AutomationService**: 
   - Backend factory and lifecycle management
   - Callback coordination between backends and UI
   - Configuration and error handling

2. **AutomationBackend**: 
   - Abstract interface defining common operations
   - Backend detection and availability checking
   - Resource cleanup contracts

3. **PlaywrightBackendV2**: 
   - State machine-driven Playwright automation
   - Improved error handling and resource management
   - Callback integration for UI updates

4. **PlaywrightRegistrationStateMachine**:
   - 14-state registration workflow management
   - Automatic state transitions and condition checking
   - Error recovery and retry mechanisms

5. **CaptchaHandler/Monitor**:
   - Intelligent captcha detection and classification
   - Real-time monitoring with timeout management
   - User notification coordination

6. **Supporting Components**:
   - FormHelpers: Reusable selectors and retry logic
   - ResultDetector: Registration success/failure detection
   - SeleniumBackend: Alternative automation implementation

Usage Patterns:
===============

# Basic usage (recommended for new implementations)
service = AutomationService()
await service.process_accounts_batch(accounts, backend_name="playwright_v2")

# Direct state machine usage
state_machine = PlaywrightRegistrationStateMachine(account, page)
success = await state_machine.run_state_machine()

# Advanced captcha handling
captcha_handler = CaptchaHandler(page, account)
result = await captcha_handler.handle_captcha_workflow(timeout_seconds=300)

Migration Guide:
================

From legacy automation:
1. Replace PlaywrightBackend with PlaywrightBackendV2
2. State transitions are now automatic - no manual state management needed  
3. Enhanced captcha handling provides better user experience
4. Improved error messages and recovery mechanisms

Key Improvements:
=================

✅ Clear state-driven workflow management
✅ Enhanced captcha detection and handling
✅ Automatic retry and error recovery
✅ Better separation of concerns
✅ Comprehensive testing and validation
✅ Improved maintainability and debugging
"""

from .automation_service import AutomationService
from .base_backend import AutomationBackend
from .playwright_backend import PlaywrightBackend
from .playwright_backend_v2 import PlaywrightBackendV2
from .selenium_backend import SeleniumBackend

# State machine components
from .registration_state_machine import (
    RegistrationStateMachine, RegistrationState, StateContext
)
from .playwright_state_machine import PlaywrightRegistrationStateMachine
from .captcha_handler import CaptchaHandler, CaptchaMonitor

__all__ = [
    'AutomationService',
    'AutomationBackend', 
    'PlaywrightBackend',
    'PlaywrightBackendV2',
    'SeleniumBackend',
    # State machine exports
    'RegistrationStateMachine',
    'RegistrationState',
    'StateContext',
    'PlaywrightRegistrationStateMachine',
    'CaptchaHandler',
    'CaptchaMonitor'
]