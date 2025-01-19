"""Desktop Assistant Package

This package provides a desktop assistant application with voice recognition capabilities
and a chat interface.
"""

import sys

# Platform detection
IS_MACOS = sys.platform == 'darwin'

# Import core components
from .main import DesktopAssistant

# Import platform-specific components
if IS_MACOS:
    from .macos_rumps_app import MacOSMenuBarApp
