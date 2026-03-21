"""
Visual Context - Screenshot capture with explicit permission.
"""
import os
from typing import Optional, Tuple
from datetime import datetime


class VisualContext:
    """Handles screen capture with strict permission requirements."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._permission_manager = None
    
    def _log(self, message: str):
        if self.debug:
            print(f"[VISUAL_CONTEXT] {message}")
    
    def _get_permission_manager(self):
        """Lazy load permission manager to avoid circular imports."""
        if self._permission_manager is None:
            from ..permission_manager import PermissionManager
            self._permission_manager = PermissionManager(debug=self.debug)
        return self._permission_manager
    
    def capture_screen_with_permission(self, reason: str = "Screen analysis") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Capture screenshot with explicit permission check.
        
        Workflow:
        1. Check permission
        2. If denied, return (False, None, error_message)
        3. If approved, capture screenshot
        4. Return (True, screenshot_path, None)
        
        Args:
            reason: Reason for screenshot request
            
        Returns:
            (success, screenshot_path, error_message)
        """
        try:
            # Check permission
            permission_manager = self._get_permission_manager()
            
            if not permission_manager.check_permission("take_screenshot"):
                # Request permission
                granted = permission_manager.request_permission(
                    "take_screenshot",
                    reason,
                    risk_level="low"
                )
                
                if not granted:
                    self._log("Screenshot permission denied")
                    return False, None, "Permission denied: User rejected screenshot request"
            
            # Permission granted - capture screenshot
            screenshot_path = self._capture_screenshot()
            
            if screenshot_path:
                self._log(f"Screenshot captured: {screenshot_path}")
                return True, screenshot_path, None
            else:
                return False, None, "Failed to capture screenshot"
                
        except Exception as e:
            self._log(f"Error capturing screenshot: {e}")
            return False, None, f"Error: {str(e)}"
    
    def _capture_screenshot(self) -> Optional[str]:
        """Capture screenshot using system tools."""
        try:
            from PIL import ImageGrab
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            
            # Capture
            screenshot = ImageGrab.grab()
            screenshot.save(filename)
            
            return filename
            
        except ImportError:
            self._log("PIL not available, trying system adapter")
            return self._capture_via_adapter()
        except Exception as e:
            self._log(f"Error in screenshot capture: {e}")
            return None
    
    def _capture_via_adapter(self) -> Optional[str]:
        """Fallback: capture via OS adapter."""
        try:
            from ..os_adapter import WindowsAdapter
            import platform
            
            if platform.system() == "Windows":
                adapter = WindowsAdapter(debug=self.debug)
                return adapter.take_screenshot()
            
            return None
            
        except Exception as e:
            self._log(f"Error in adapter screenshot: {e}")
            return None
