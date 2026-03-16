import os
import sys

# Check if running on Windows
def is_windows():
    return sys.platform.startswith('win')

# Fallback for Windows to handle readline
def get_readline_module():
    if is_windows():
        try:
            import pyreadline3
            return pyreadline3
        except ImportError:
            print('pyreadline3 not found. Some functionality may be limited on Windows.')
            return None
    else:
        import readline
        return readline
