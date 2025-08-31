#!/usr/bin/env python3
"""
Integration test for internationalization functionality with GUI
NOTE: This test is deprecated as it used the legacy GUI
TODO: Implement proper i18n integration test with MVVM architecture
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import MVVM components instead of legacy GUI
from PySide6.QtWidgets import QApplication
from src.batch_creator_gui import BatchCreatorMainWindow
from src.viewmodels.batch_creator_viewmodel import BatchCreatorViewModel
from src.translation_manager import init_translation_manager, get_translation_manager


def test_i18n_with_mvvm():
    """Test internationalization functionality with MVVM GUI"""
    print("Testing 360 Batch Account Creator Internationalization (MVVM)...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("360 Batch Account Creator")
    
    # Initialize translation system
    init_translation_manager(app)
    tm = get_translation_manager()
    
    # Test translation manager
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
    
    # Create MVVM GUI components
    view_model = BatchCreatorViewModel()
    main_window = BatchCreatorMainWindow(view_model)
    
    # Show the main window
    print("\n--- Showing MVVM Main Window ---")
    print("The MVVM GUI should now be displayed with language menu.")
    print("You can test language switching through the language button.")
    
    main_window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(test_i18n_with_mvvm())