"""
Automation service module for batch account registration

This module provides a clean separation between different automation backends
(Simple Playwright, Selenium) while maintaining a unified interface. Uses
transitions framework for simplified state machine-based registration workflow.

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
    ┌─────────────────────┐  ┌─────────────────────┐
    │   PlaywrightBackend │  │   SeleniumBackend   │
    │ (Transitions-based) │  │    (Legacy impl)    │
    └─────────────────────┘  └─────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────┐
    │         RegistrationMachine                     │ ← Transitions framework
    │      (12-state workflow with transitions)       │
    └─────────────────┬───────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────────────┐
    │          Captcha Monitoring                     │ ← 120-second monitoring
    │        (Enhanced captcha management)            │
    └─────────────────────────────────────────────────┘

    Supporting Components:
    ├── FormHelpers      ← Common selectors and utilities
    ├── ResultDetector   ← Registration result detection
    └── CaptchaHandler   ← Captcha detection components

Component Responsibilities:
===========================

1. **AutomationService**: 
   - Backend factory and lifecycle management
   - Callback coordination between backends and UI
   - Configuration and error handling

2. **PlaywrightBackend**: 
   - Transitions framework-based Playwright automation
   - Improved error handling and resource management
   - Callback integration for UI updates

3. **RegistrationMachine**:
   - 12-state registration workflow (transitions framework)
   - Automatic state transitions and condition checking
   - 120-second captcha monitoring with timeout

4. **Supporting Components**:
   - FormHelpers: Reusable selectors and retry logic
   - ResultDetector: Registration success/failure detection
   - SeleniumBackend: Alternative automation implementation

Usage Patterns:
===============

# Recommended usage (default backend)
service = AutomationService()  # Uses playwright by default
await service.register_single_account(account)

# Explicit backend selection
service = AutomationService(backend_type="playwright")
await service.process_accounts_batch(accounts)

# CLI usage
python src/cli.py --username "test123" --password "testpass123" --backend playwright

Key Features:
=============

✅ Transitions framework for clean state management
✅ 120-second captcha monitoring with user guidance
✅ Input validation (username 2-14 chars, password 8-20 chars)
✅ Automatic retry and error recovery
✅ Better separation of concerns
✅ Comprehensive error messages
✅ Simplified architecture with fewer components
"""

from .automation_service import AutomationService
from .base_backend import AutomationBackend
from .playwright_backend import PlaywrightBackend
from .selenium_backend import SeleniumBackend

# State machine components
from .simple_state_machine import RegistrationMachine

__all__ = [
    'AutomationService',
    'AutomationBackend', 
    'PlaywrightBackend',
    'SeleniumBackend',
    # State machine exports
    'RegistrationMachine'
]