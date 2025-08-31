#!/usr/bin/env python3
"""
Test script for the 360 Batch Account Creator GUI
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from batch_creator_gui import main

if __name__ == "__main__":
    main()