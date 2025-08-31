#!/usr/bin/env python3
"""
GUI Startup Module for 360 Account Batch Creator
Unified PySide6 Widgets startup with MVVM architecture
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

# Import GUI components
from .batch_creator_gui import BatchCreatorMainWindow
from .translation_manager import init_translation_manager


def configure_application():
    """Configure QApplication properties"""
    QCoreApplication.setApplicationName("360 Account Batch Creator")
    QCoreApplication.setOrganizationName("360 Tools")
    QCoreApplication.setApplicationVersion("1.0.0")


def start_gui_application():
    """
    Start the GUI application using PySide6 Widgets with MVVM architecture
    This is the unified entry point for GUI mode
    """
    print("Starting 360 Account Batch Creator (PySide6 Widgets)...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Configure application properties
    configure_application()
    
    # Initialize translation system BEFORE creating GUI
    init_translation_manager(app)
    
    # Create and show main window (ViewModel is created internally)
    main_window = BatchCreatorMainWindow()
    main_window.show()
    
    print("GUI loaded successfully!")
    print("Features available:")
    print("- Multi-language support (中文/English)")
    print("- Password security management")  
    print("- CSV import/export")
    print("- Batch processing with Playwright/Selenium backend")
    print("- MVVM architecture with Qt signals/slots")
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    """Allow direct execution of GUI startup"""
    sys.exit(start_gui_application())