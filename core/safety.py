"""
Permission and safety filter for local operations.
"""
import json
import os
from typing import Dict, Any


class SafetyFilter:
    def __init__(self, config_path: str = "config/permissions.json", debug: bool = False):
        self.config_path = config_path
        self.debug = debug
        self.permissions = self._load_permissions()
    
    def _log(self, message: str):
        if self.debug:
            print(f"[SAFETY] {message}")
    
    def _load_permissions(self) -> Dict[str, bool]:
        """Load permissions from config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self._log(f"Error loading permissions: {e}")
        
        # Default permissions
        return {
            "open_file": True,
            "write_file": False,
            "run_code": False,
            "open_app": True,
            "internet_access": False,
            "read_system_info": True
        }
    
    def save_permissions(self):
        """Save current permissions to config file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.permissions, f, indent=2)
            self._log("Permissions saved")
        except Exception as e:
            self._log(f"Error saving permissions: {e}")
    
    def check_permission(self, action: str) -> bool:
        """Check if an action is permitted."""
        allowed = self.permissions.get(action, False)
        self._log(f"Permission check '{action}': {allowed}")
        return allowed
    
    def request_permission(self, action: str, description: str = "") -> bool:
        """Request permission from user for an action."""
        if self.check_permission(action):
            return True
        
        print(f"\n⚠️  Permission required: {action}")
        if description:
            print(f"   {description}")
        
        response = input("   Allow this action? [y/n/always]: ").strip().lower()
        
        if response == 'always':
            self.permissions[action] = True
            self.save_permissions()
            return True
        
        return response == 'y'
    
    def request_internet_permission(self, reason: str = "") -> bool:
        """Special handler for internet access requests."""
        print(f"\n🌐 Internet access requested")
        if reason:
            print(f"   Reason: {reason}")
        
        response = input("   Do you allow me to connect to the internet for this response? [y/n]: ").strip().lower()
        return response == 'y'
