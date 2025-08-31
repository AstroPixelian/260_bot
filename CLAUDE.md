# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **360 Account Batch Creator** desktop application built with **PySide6** using a strict **MVVM (Model-View-ViewModel) architecture**. The app provides a GUI for batch account registration with multilingual support (Chinese/English) and advanced password management features.

## Development Commands

### Environment Setup
```bash
# Initialize development environment
just init

# Install dependencies only (no dev tools)
just init --no-dev-group
```

### Application Execution
```bash
# Run the main application (production GUI)
uv run main.py

# Run the MVVM GUI for testing
python tests/manual/test_mvvm_gui.py
```

### Build and Development
```bash
# Build resources for development (compiles QML, translations, resources)
just build-develop

# Full production build
just build

# Clean all generated files
just clean
```

### Internationalization
```bash
# Add a new language (e.g., French)
just add-translation fr-FR

# Update existing translation files after code changes
just update-translations

# Compile .ts files to .qm (binary translation files)
pyside6-lrelease i18n/*.ts
```

### Testing
```bash
# Run all tests (Python + QML)
just test

# Run Python tests only
just test-python

# Run QML tests only
just test-qml
```

## Architecture Overview

The project follows **strict MVVM separation**:

### Layer Structure
- **Model** (`src/models/`): Data models and business entities
- **Service** (`src/services/`): Business logic and external integrations  
- **ViewModel** (`src/viewmodels/`): UI state management and service coordination
- **View** (`src/batch_creator_gui.py`): Pure UI logic

### Key Components
- **Account/AccountStatus**: Core data models with business methods
- **DataService**: Handles CSV import/export, data validation, random generation
- **AutomationService**: Manages batch processing workflow with callback-based UI updates
- **BatchCreatorViewModel**: Central coordinator using Qt signals/slots for UI communication
- **TranslationManager**: Runtime language switching with Qt Linguist integration

### Communication Pattern
UI events → ViewModel → Services → Model → Services → ViewModel (signals) → UI updates

## Critical Architecture Rules

1. **Never put business logic in GUI classes** - Use ViewModel as intermediary
2. **Use Qt signals/slots for UI updates** - Avoid direct GUI manipulation from services
3. **All file operations through DataService** - Maintain single responsibility
4. **Translation keys must use tr() function** - Support runtime language switching
5. **Password widgets use custom components** - CopyableTextWidget, PasswordWidget for security

## File Entry Points

### Main Application
- `main.py` → `src/startup.py` → Production app startup

### Testing
- `tests/manual/test_mvvm_gui.py` → MVVM GUI testing (recommended)
- `tests/unit/test_translation_manager.py` → Translation unit tests
- `tests/integration/test_i18n_integration.py` → I18n integration tests

### Current Implementation
- **Primary GUI**: `src/batch_creator_gui.py` (MVVM-compliant - USE THIS)
- **Legacy GUI**: DELETED - Use MVVM version only

## Development Patterns

### Adding New Features
1. Define data model in `src/models/`
2. Implement business logic in appropriate service in `src/services/`  
3. Add ViewModel methods in `src/viewmodels/batch_creator_viewmodel.py`
4. Create UI elements and connect signals in `src/batch_creator_gui.py`

### Signal/Slot Pattern
```python
# In ViewModel: Define signals
account_updated = Signal(Account)

# In Service: Trigger through callback
self.on_account_complete(account)  # → calls ViewModel method → emits signal

# In GUI: Connect to slot
self.view_model.account_updated.connect(self.update_account_display)
```

### Translation Integration
```python
# Always use tr() for user-facing text
message = tr("Processing completed successfully")

# Parameterized translations  
message = tr("Imported %1 accounts").arg(count)

# Context-specific translations
status_text = tr(status.value, "AccountStatus")
```

## Multilingual Development

### Language Files
- `i18n/zh-CN.ts` - Chinese translation source
- `i18n/en-US.ts` - English translation source  
- `i18n/*.qm` - Compiled binary translations (auto-generated)

### Translation Workflow
1. Add `tr("Text")` in code
2. Run `just update-translations` to extract strings
3. Edit `.ts` files with Qt Linguist or manually
4. Compile with `pyside6-lrelease` (done automatically by build process)

## Important Implementation Notes

### GUI Architecture Evolution
The project underwent major refactoring from direct GUI manipulation to MVVM:
- **Current**: `batch_creator_gui.py` with proper MVVM separation (USE THIS)
- **Legacy**: DELETED - All functionality migrated to MVVM version

### Custom Components
- **CopyableTextWidget**: Username display with copy button
- **PasswordWidget**: Password field with visibility toggle and copy functionality
- **StatusIcon**: Visual status indicators with colors and icons

### Service Layer Design
Services use callback patterns to avoid direct GUI dependencies:
```python
# AutomationService callbacks
self.automation_service.set_callbacks(
    on_account_start=self._on_account_start,
    on_account_complete=self._on_account_complete
)
```

## Resource Compilation

The project uses Qt Resource System:
- QML files in `qt/qml/` → compiled to Python
- Data files in `data/` → accessible as `qrc:/data`
- Translations in `i18n/` → accessible as `qrc:/i18n`

Always run `just build-develop` after modifying resources.

## Testing Strategy

### Test Structure
```
tests/
├── unit/                    # Unit tests for individual components
├── integration/             # Component interaction tests  
└── manual/                  # Interactive GUI and system tests
```

### Running Tests
```bash
# Unit tests
python tests/unit/test_translation_manager.py

# Integration tests
python tests/integration/test_i18n_integration.py

# Manual GUI testing
python tests/manual/test_mvvm_gui.py        # MVVM version

# Automated test suite (if configured)
just test-python
```

### Test Execution Context
Tests require resource compilation and proper Python path setup (handled automatically by `just test-python`).

## Coding Standards and Project Structure

### Directory Structure Rules
```
src/                          # Source code only
├── models/                   # Data models and business entities
├── services/                 # Business logic and external integrations
├── viewmodels/              # UI state management and service coordination
└── *.py                     # View layer files

tests/                       # ALL tests must be here
├── unit/                    # Unit tests for individual components
├── integration/             # Component interaction tests
└── manual/                  # Interactive GUI and system tests

i18n/                        # Translation files only
docs/                        # Documentation only
```

### Critical Rules - NEVER VIOLATE

#### Test Organization
- **MANDATORY**: All tests (unit, integration, manual) MUST be in `tests/` directory or subdirectories
- **FORBIDDEN**: Never put test files in project root or `src/` directory
- **FORBIDDEN**: Never mix test code with production code
- **NAMING**: Test files must follow `test_*.py` pattern

#### MVVM Architecture Compliance
- **MANDATORY**: Use `src/batch_creator_gui.py` (MVVM version - ONLY version available)
- **MANDATORY**: All business logic must go through ViewModel → Services → Models
- **FORBIDDEN**: Never put business logic directly in GUI classes

#### File Operations
- **MANDATORY**: All file operations through DataService
- **MANDATORY**: Use absolute path resolution from project root
- **FORBIDDEN**: Never use relative imports that break from different directories

#### Translation Requirements
- **MANDATORY**: All user-facing text must use `tr()` function
- **MANDATORY**: Update translations after adding new text: `just update-translations`
- **FORBIDDEN**: Never hard-code display text in any language

### Import Path Standards
```python
# Correct way for tests
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # Adjust levels as needed
sys.path.insert(0, str(project_root))

# Then import from src/
from src.models.account import Account
from src.services.data_service import DataService
```