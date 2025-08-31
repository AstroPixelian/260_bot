#!/usr/bin/env python3
"""
Unit tests for TranslationManager core functionality
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from src.translation_manager import TranslationManager, tr


def test_translation_core():
    """Test core translation functionality without GUI"""
    print("Testing Translation Manager Core Functionality...")
    
    # Create minimal QApplication for translation system
    app = QApplication([])
    app.setApplicationName("Test App")
    
    # Create translation manager
    tm = TranslationManager(app)
    
    # Test available languages
    languages = tm.get_available_languages()
    print(f"Available languages: {list(languages.keys())}")
    
    # Test system locale detection
    system_locale = tm.get_system_locale()
    print(f"System locale: {system_locale}")
    
    # Test language switching
    print("\n--- Testing Language Switching ---")
    
    # Test English (default)
    success = tm.switch_language('en-US')
    print(f"Switch to en-US: {'Success' if success else 'Failed'}")
    print(f"Current locale: {tm.get_current_locale()}")
    
    # Test some translations in English
    print(f"Translation test (English): '{tr('360 Batch Account Creator')}'")
    print(f"Translation test (English): '{tr('Success')}'")
    
    # Test Chinese
    success = tm.switch_language('zh-CN')
    print(f"Switch to zh-CN: {'Success' if success else 'Failed'}")
    print(f"Current locale: {tm.get_current_locale()}")
    
    # Test some translations in Chinese
    print(f"Translation test (Chinese): '{tr('360 Batch Account Creator')}'")
    print(f"Translation test (Chinese): '{tr('Success')}'")
    print(f"Translation test (Chinese): '{tr('Import CSV File')}'")
    
    # Test display names
    print("\n--- Language Display Names ---")
    for locale in languages.keys():
        display_name = tm.get_language_display_name(locale)
        print(f"{locale}: {display_name}")
    
    print("\n✅ Core translation functionality tests completed!")
    
    return 0


if __name__ == "__main__":
    sys.exit(test_translation_core())