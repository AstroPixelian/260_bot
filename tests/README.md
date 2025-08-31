# Test Suite Documentation

This directory contains the organized test suite for the 360 Batch Account Creator project.

## Test Directory Structure

```
tests/
├── __init__.py                               # Main tests package
├── unit/                                     # Unit tests
│   ├── __init__.py
│   └── test_translation_manager.py          # Translation manager unit tests
├── integration/                              # Integration tests  
│   ├── __init__.py
│   └── test_i18n_integration.py             # I18n with GUI integration tests
└── manual/                                   # Manual testing scripts
    ├── __init__.py
    ├── test_legacy_gui.py                   # Legacy GUI runner (for compatibility)
    └── test_mvvm_gui.py                     # MVVM GUI runner (recommended)
```

## Running Tests

### Unit Tests
```bash
# Run translation manager tests
python tests/unit/test_translation_manager.py
```

### Integration Tests  
```bash
# Run i18n integration tests
python tests/integration/test_i18n_integration.py
```

### Manual Testing
```bash
# Test MVVM GUI (recommended)
python tests/manual/test_mvvm_gui.py

# Test legacy GUI (for compatibility)
python tests/manual/test_legacy_gui.py
```

### Using Just (if configured)
```bash
# Run all automated tests
just test-python
```

## Test Categories

### Unit Tests
- **test_translation_manager.py**: Core translation functionality without GUI dependencies
- Tests language switching, locale detection, translation loading

### Integration Tests
- **test_i18n_integration.py**: Full i18n functionality with GUI integration
- Tests language switching through the actual GUI interface

### Manual Tests
- **test_mvvm_gui.py**: Interactive testing of the MVVM refactored version
- **test_legacy_gui.py**: Interactive testing of the legacy non-MVVM version

## Migration Notes

The test files were reorganized from the project root to provide better structure:
- `test_translation_core.py` → `tests/unit/test_translation_manager.py`
- `test_i18n.py` → `tests/integration/test_i18n_integration.py`  
- `test_gui.py` → `tests/manual/test_legacy_gui.py` + `tests/manual/test_mvvm_gui.py`

## Adding New Tests

When adding new tests, follow this structure:
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Manual tests**: Interactive GUI or system tests

All test files should use proper path resolution to import from the `src/` directory.