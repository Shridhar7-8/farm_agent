"""
Farm Agent - AI-powered farm management system
"""

# Make src package importable by adding to path
import sys
import os

# Add the parent directory to the path so src imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)