"""
OS Adapter Abstraction Layer
Provides OS-specific implementations for system operations.
"""
from .base_adapter import BaseAdapter
from .windows_adapter import WindowsAdapter
from .macos_adapter import MacOSAdapter
from .linux_adapter import LinuxAdapter

__all__ = ['BaseAdapter', 'WindowsAdapter', 'MacOSAdapter', 'LinuxAdapter']
