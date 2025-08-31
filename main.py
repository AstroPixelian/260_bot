#!/usr/bin/env python

import sys


def main():
    """Main entry point - detects CLI vs GUI mode"""
    # Check if CLI arguments are provided
    if len(sys.argv) > 1 and any(arg in ['--username', '--password', '-h', '--help'] for arg in sys.argv):
        # CLI mode - import and run CLI handler
        from src.cli import main as cli_main
        cli_main()
    else:
        # GUI mode - run existing startup
        # Import resources (will be needed when we set up proper resource compilation)
        # import rc_project  # noqa
        
        from src.startup import perform_startup
        perform_startup()


if __name__ == "__main__":
    main()