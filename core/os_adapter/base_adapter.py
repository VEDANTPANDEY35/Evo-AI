"""
Base OS Adapter - Abstract interface for OS-specific operations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseAdapter(ABC):
    """Abstract base class for OS-specific adapters."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    @abstractmethod
    def open_application(self, app_name: str) -> bool:
        """
        Open an application.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def list_processes(self) -> List[Dict[str, Any]]:
        """
        List running processes.
        Returns list of dicts with 'pid' and 'name' keys.
        """
        pass
    
    @abstractmethod
    def kill_process(self, pid: Optional[int] = None, name: Optional[str] = None) -> bool:
        """
        Kill a process by PID or name.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def take_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Take a screenshot.
        Returns filename if successful, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information (CPU, memory, disk, OS).
        Returns dict with system info.
        """
        pass
    
    @abstractmethod
    def get_clipboard(self) -> Optional[str]:
        """
        Get clipboard contents.
        Returns clipboard text or None.
        """
        pass
    
    @abstractmethod
    def set_clipboard(self, text: str) -> bool:
        """
        Set clipboard contents.
        Returns True if successful, False otherwise.
        """
        pass
