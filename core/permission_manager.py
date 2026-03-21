"""
Enhanced Permission Manager with allow-once, allow-always, deny workflows.
Includes audit logging and programmatic API for future GUI/daemon modes.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum


class PermissionResponse(Enum):
    """User response to permission request."""
    ALLOW_ONCE = "allow_once"
    ALLOW_ALWAYS = "allow_always"
    DENY = "deny"


class PermissionManager:
    """Manages permissions with audit logging and persistent storage."""
    
    def __init__(self, config_dir: str = "config", debug: bool = False):
        self.config_dir = config_dir
        self.debug = debug
        self.permissions_file = os.path.join(config_dir, "permissions.json")
        self.audit_log_file = os.path.join(config_dir, "permission_audit.jsonl")
        self.permissions = self._load_permissions()
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
    
    def _log(self, message: str):
        if self.debug:
            print(f"[PERMISSION_MGR] {message}")
    
    def _load_permissions(self) -> Dict[str, bool]:
        """Load permissions from config file."""
        try:
            if os.path.exists(self.permissions_file):
                with open(self.permissions_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self._log(f"Error loading permissions: {e}")
        
        # Default permissions - conservative by default
        return {
            "open_file": True,
            "write_file": False,
            "delete_file": False,
            "run_code": False,
            "run_command": False,
            "open_app": True,
            "kill_process": False,
            "internet_access": False,
            "read_system_info": True,
            "open_browser": True,
            "modify_clipboard": False,
            "take_screenshot": False,
            "network_access": False
        }
    
    def save_permissions(self):
        """Save current permissions to config file."""
        try:
            with open(self.permissions_file, 'w') as f:
                json.dump(self.permissions, f, indent=2)
            self._log("Permissions saved")
        except Exception as e:
            self._log(f"Error saving permissions: {e}")
    
    def _audit_log(self, action: str, permission: str, response: PermissionResponse,
                   reason: str = "", context: Dict[str, Any] = None):
        """Log permission request to audit file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "permission": permission,
                "response": response.value,
                "reason": reason,
                "context": context or {}
            }
            
            with open(self.audit_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            self._log(f"Audit logged: {action} -> {response.value}")
            
        except Exception as e:
            self._log(f"Error writing audit log: {e}")
    
    def check_permission(self, permission: str) -> bool:
        """Check if a permission is granted."""
        allowed = self.permissions.get(permission, False)
        self._log(f"Permission check '{permission}': {allowed}")
        return allowed
    
    def request_permission_interactive(self, permission: str, action: str,
                                      description: str = "",
                                      risk_level: str = "medium",
                                      context: Dict[str, Any] = None) -> PermissionResponse:
        """
        Request permission from user interactively (CLI mode).
        
        Args:
            permission: Permission key (e.g., "write_file")
            action: Action being performed (e.g., "create_file")
            description: Human-readable description
            risk_level: "safe", "low", "medium", "high", "critical"
            context: Additional context (tool params, etc.)
        
        Returns:
            PermissionResponse enum
        """
        # Check if already granted
        if self.check_permission(permission):
            self._audit_log(action, permission, PermissionResponse.ALLOW_ALWAYS,
                          "Pre-granted", context)
            return PermissionResponse.ALLOW_ALWAYS
        
        # Display permission request
        print(f"\n{'='*60}")
        print(f"⚠️  PERMISSION REQUEST")
        print(f"{'='*60}")
        print(f"Action: {action}")
        print(f"Permission: {permission}")
        print(f"Risk Level: {risk_level.upper()}")
        
        if description:
            print(f"Description: {description}")
        
        if context:
            print(f"\nDetails:")
            for key, value in context.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"  {key}: {value_str}")
        
        print(f"\nOptions:")
        print(f"  [o] Allow once (this time only)")
        print(f"  [a] Allow always (remember this choice)")
        print(f"  [d] Deny (block this action)")
        print(f"{'='*60}")
        
        # Get user response
        while True:
            response = input("Your choice [o/a/d]: ").strip().lower()
            
            if response == 'o':
                result = PermissionResponse.ALLOW_ONCE
                break
            elif response == 'a':
                result = PermissionResponse.ALLOW_ALWAYS
                # Save permission
                self.permissions[permission] = True
                self.save_permissions()
                print(f"✓ Permission '{permission}' granted permanently")
                break
            elif response == 'd':
                result = PermissionResponse.DENY
                break
            else:
                print("Invalid choice. Please enter 'o', 'a', or 'd'")
        
        # Log to audit
        self._audit_log(action, permission, result, description, context)
        
        return result
    
    def request_permission_programmatic(self, permission: str, action: str,
                                       auto_allow: bool = False) -> PermissionResponse:
        """
        Request permission programmatically (for GUI/daemon mode).
        
        Args:
            permission: Permission key
            action: Action being performed
            auto_allow: If True, auto-allow if permission is granted
        
        Returns:
            PermissionResponse enum
        """
        if self.check_permission(permission):
            return PermissionResponse.ALLOW_ALWAYS
        
        if auto_allow:
            return PermissionResponse.ALLOW_ONCE
        
        return PermissionResponse.DENY
    
    def revoke_permission(self, permission: str):
        """Revoke a previously granted permission."""
        if permission in self.permissions:
            self.permissions[permission] = False
            self.save_permissions()
            self._log(f"Revoked permission: {permission}")
    
    def grant_permission(self, permission: str):
        """Grant a permission programmatically."""
        self.permissions[permission] = True
        self.save_permissions()
        self._log(f"Granted permission: {permission}")
    
    def list_permissions(self) -> Dict[str, bool]:
        """Get all current permissions."""
        return self.permissions.copy()
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit log entries.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of audit log entries (most recent first)
        """
        try:
            if not os.path.exists(self.audit_log_file):
                return []
            
            entries = []
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
            
            # Return most recent first
            return entries[-limit:][::-1]
            
        except Exception as e:
            self._log(f"Error reading audit log: {e}")
            return []
    
    def export_audit_log(self, output_file: str, format: str = "json"):
        """Export audit log to file."""
        try:
            entries = self.get_audit_log(limit=10000)
            
            if format == "json":
                with open(output_file, 'w') as f:
                    json.dump(entries, f, indent=2)
            
            elif format == "csv":
                import csv
                with open(output_file, 'w', newline='') as f:
                    if entries:
                        writer = csv.DictWriter(f, fieldnames=entries[0].keys())
                        writer.writeheader()
                        writer.writerows(entries)
            
            self._log(f"Audit log exported to {output_file}")
            
        except Exception as e:
            self._log(f"Error exporting audit log: {e}")
    
    def clear_audit_log(self):
        """Clear audit log (use with caution)."""
        try:
            if os.path.exists(self.audit_log_file):
                os.remove(self.audit_log_file)
            self._log("Audit log cleared")
        except Exception as e:
            self._log(f"Error clearing audit log: {e}")
    
    def reset_to_defaults(self):
        """Reset all permissions to default values."""
        self.permissions = self._load_permissions()
        self.save_permissions()
        self._log("Permissions reset to defaults")


# Helper function for quick permission checks
def require_permission(permission: str, action: str, description: str = "",
                      risk_level: str = "medium", context: Dict[str, Any] = None,
                      manager: PermissionManager = None) -> bool:
    """
    Helper function to request permission and return boolean result.
    
    Returns:
        True if allowed (once or always), False if denied
    """
    if manager is None:
        manager = PermissionManager()
    
    response = manager.request_permission_interactive(
        permission, action, description, risk_level, context
    )
    
    return response in [PermissionResponse.ALLOW_ONCE, PermissionResponse.ALLOW_ALWAYS]
