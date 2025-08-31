#!/usr/bin/env python3
"""
Test script for internationalization functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.batch_creator_gui import BatchCreatorApp


def test_i18n():
    """Test internationalization functionality"""
    print("Testing 360 Batch Account Creator Internationalization...")
    
    app = BatchCreatorApp(sys.argv)
    
    # Test translation manager
    tm = app.translation_manager
    print(f"Available languages: {list(tm.get_available_languages().keys())}")
    print(f"Current locale: {tm.get_current_locale()}")
    print(f"System locale: {tm.get_system_locale()}")
    
    # Test language switching
    print("\n--- Testing Language Switch ---")
    print("Switching to Chinese...")
    success = tm.switch_language('zh-CN')
    print(f"Switch to zh-CN: {'Success' if success else 'Failed'}")
    
    print("Switching to English...")
    success = tm.switch_language('en-US')
    print(f"Switch to en-US: {'Success' if success else 'Failed'}")
    
    # Show the main window
    print("\n--- Showing Main Window ---")
    print("The GUI should now be displayed with language menu.")
    print("You can test language switching through the Settings > Language menu.")
    
    app.main_window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(test_i18n())