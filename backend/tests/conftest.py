"""
Pytest configuration and shared fixtures

Provides common fixtures and configuration for all tests
"""

import pytest
import sys
import os

# Add parent directory to path so tests can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
