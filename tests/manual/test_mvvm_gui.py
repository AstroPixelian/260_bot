#!/usr/bin/env python3
"""
GUI test runner for the refactored MVVM version
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))  # Add src directory for translation_manager import

from PySide6.QtWidgets import QApplication
from src.batch_creator_gui import BatchCreatorMainWindow
from src.translation_manager import init_translation_manager


def run_mvvm_gui():
    """Run the MVVM refactored GUI"""
    print("Starting 360 Batch Account Creator (MVVM Version)...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("360 Batch Account Creator")
    app.setApplicationVersion("2.0")
    
    # Initialize translation system BEFORE creating GUI
    init_translation_manager(app)
    
    # Create and show main window (ViewModel is created internally)
    main_window = BatchCreatorMainWindow()
    main_window.show()
    
    print("MVVM GUI loaded successfully!")
    print("Features available:")
    print("- Multi-language support (中文/English)")
    print("- Password security management")  
    print("- CSV import/export")
    print("- Batch processing simulation")
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_mvvm_gui())