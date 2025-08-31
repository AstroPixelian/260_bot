#!/usr/bin/env python

import sys


def main():
    """Main entry point - detects CLI vs GUI mode"""
    # Check if CLI arguments are provided
    if len(sys.argv) > 1:
        # Check for account generation mode
        if '--generate' in sys.argv:
            from src.account_generator import main as generator_main
            generator_main()
        # Check for registration CLI mode
        elif any(arg in ['--username', '--password', '-h', '--help', '--verbose', '-v', '--json', '--error-log', '--backend'] for arg in sys.argv):
            # CLI mode - import and run CLI handler
            from src.cli import main as cli_main
            cli_main()
        else:
            # GUI mode - use PySide6 Widgets MVVM architecture
            from src.gui_startup import start_gui_application
            start_gui_application()
    else:
        # GUI mode - use PySide6 Widgets MVVM architecture
        from src.gui_startup import start_gui_application
        start_gui_application()


if __name__ == "__main__":
    main()