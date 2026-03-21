"""
System Context - Lightweight system information gathering.
"""
import os
import platform
import psutil
from typing import Dict, Any, Optional
from datetime import datetime


class SystemContext:
    """Gathers lightweight system context information."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _log(self, message: str):
        if self.debug:
            print(f"[SYSTEM_CONTEXT] {message}")
    
    def get_active_window(self) -> Optional[str]:
        """Get active window title (Windows only for now)."""
        try:
            if platform.system() == "Windows":
                import win32gui
                window = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(window)
                return title if title else None
            return None
        except Exception as e:
            self._log(f"Error getting active window: {e}")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        try:
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "username": os.getenv("USERNAME") or os.getenv("USER"),
                "hostname": platform.node(),
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self._log(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def get_running_processes(self, limit: int = 10) -> list:
        """Get top running processes by memory usage."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    processes.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'memory_percent': round(proc.info['memory_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory and return top N
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            return processes[:limit]
        except Exception as e:
            self._log(f"Error getting processes: {e}")
            return []
