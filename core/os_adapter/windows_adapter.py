"""
Windows OS Adapter - Windows-specific implementations.
"""
import os
import platform
import subprocess
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_adapter import BaseAdapter


class WindowsAdapter(BaseAdapter):
    """Windows-specific adapter implementation."""
    
    def open_application(self, app_name: str) -> bool:
        """Open application on Windows."""
        try:
            subprocess.Popen(app_name, shell=True)
            return True
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error opening {app_name}: {e}")
            return False
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List running processes."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info.get('cpu_percent', 0),
                        'memory': proc.info.get('memory_percent', 0)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error listing processes: {e}")
        
        return processes
    
    def kill_process(self, pid: Optional[int] = None, name: Optional[str] = None) -> bool:
        """Kill process by PID or name."""
        try:
            if pid:
                proc = psutil.Process(pid)
                proc.terminate()
                return True
            elif name:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'].lower() == name.lower():
                        proc.terminate()
                        return True
            return False
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error killing process: {e}")
            return False
    
    def take_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """Take screenshot on Windows."""
        try:
            from PIL import ImageGrab
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshot = ImageGrab.grab()
            screenshot.save(filename)
            return filename
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error taking screenshot: {e}")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'os': platform.system(),
                'os_version': platform.version(),
                'os_release': platform.release(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'cpu_cores': cpu_count,
                'cpu_threads': cpu_count_logical,
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else 0,
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_used_percent': memory.percent,
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_used_percent': disk.percent
            }
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error getting system info: {e}")
            return {'error': str(e)}
    
    def get_clipboard(self) -> Optional[str]:
        """Get clipboard contents on Windows."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData()
                return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error getting clipboard: {e}")
            return None
    
    def set_clipboard(self, text: str) -> bool:
        """Set clipboard contents on Windows."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            if self.debug:
                print(f"[WINDOWS_ADAPTER] Error setting clipboard: {e}")
            return False
