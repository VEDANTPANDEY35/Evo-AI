"""
Parameter validation and safety guards for tool execution.
Enforces path safety, command sanitization, and destructive action protection.
"""
import os
import re
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class SafetyValidator:
    """Validates tool parameters and enforces safety policies."""
    
    # System-critical directories (platform-specific)
    WINDOWS_PROTECTED_DIRS = [
        "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
        "C:\\ProgramData", "C:\\System Volume Information"
    ]
    
    UNIX_PROTECTED_DIRS = [
        "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/etc", "/sys", "/proc",
        "/boot", "/dev", "/lib", "/lib64", "/root"
    ]
    
    MACOS_PROTECTED_DIRS = [
        "/System", "/Library", "/Applications", "/private/var/db",
        "/private/var/root"
    ]
    
    # Dangerous command patterns
    DANGEROUS_COMMAND_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'del\s+/[sS]\s+/[qQ]',
        r'format\s+[cC]:',
        r'dd\s+if=',
        r'mkfs\.',
        r':(){ :|:& };:',  # Fork bomb
        r'chmod\s+-R\s+777',
        r'chown\s+-R',
    ]
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.platform = platform.system()
        self._init_protected_dirs()
    
    def _log(self, message: str):
        if self.debug:
            print(f"[SAFETY_VALIDATOR] {message}")
    
    def _init_protected_dirs(self):
        """Initialize platform-specific protected directories."""
        if self.platform == "Windows":
            self.protected_dirs = [Path(d) for d in self.WINDOWS_PROTECTED_DIRS]
        elif self.platform == "Darwin":
            self.protected_dirs = [Path(d) for d in self.UNIX_PROTECTED_DIRS + self.MACOS_PROTECTED_DIRS]
        else:  # Linux
            self.protected_dirs = [Path(d) for d in self.UNIX_PROTECTED_DIRS]
        
        self._log(f"Initialized {len(self.protected_dirs)} protected directories")
    
    def validate_path(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """
        Validate file path for safety.
        
        Args:
            path: File path to validate
            operation: "read", "write", "delete"
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Normalize and resolve path
            resolved_path = Path(path).resolve()
            
            # Check if path exists for read operations
            if operation == "read" and not resolved_path.exists():
                return False, f"Path does not exist: {path}"
            
            # Check for protected directories
            if operation in ["write", "delete"]:
                for protected in self.protected_dirs:
                    try:
                        if resolved_path.is_relative_to(protected):
                            return False, f"Cannot {operation} in protected directory: {protected}"
                    except (ValueError, AttributeError):
                        # is_relative_to not available in older Python
                        if str(resolved_path).startswith(str(protected)):
                            return False, f"Cannot {operation} in protected directory: {protected}"
            
            # Check for root-level operations
            if operation == "delete":
                if resolved_path == resolved_path.root:
                    return False, "Cannot delete root directory"
                
                # Prevent deletion of entire home directory
                home = Path.home()
                if resolved_path == home:
                    return False, "Cannot delete home directory"
            
            # Check for suspicious patterns
            path_str = str(resolved_path)
            if ".." in path_str and operation in ["write", "delete"]:
                return False, "Path traversal detected"
            
            self._log(f"Path validation passed: {path} ({operation})")
            return True, ""
            
        except Exception as e:
            return False, f"Path validation error: {e}"
    
    def validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate shell command for dangerous patterns.
        
        Returns:
            (is_safe, error_message)
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Dangerous command pattern detected: {pattern}"
        
        # Check for command chaining that might hide malicious commands
        if any(sep in command for sep in [';', '&&', '||', '|']):
            self._log(f"Command chaining detected: {command}")
            # Allow but log - user permission will be required
        
        # Check for redirection to sensitive files
        if '>' in command or '>>' in command:
            # Extract target file
            redirect_match = re.search(r'>>?\s*([^\s]+)', command)
            if redirect_match:
                target = redirect_match.group(1)
                is_valid, error = self.validate_path(target, "write")
                if not is_valid:
                    return False, f"Command redirects to unsafe location: {error}"
        
        self._log(f"Command validation passed: {command[:50]}...")
        return True, ""
    
    def sanitize_query(self, query: str) -> str:
        """
        Sanitize search query by removing sensitive information.
        """
        # Remove absolute paths
        sanitized = re.sub(r'[A-Za-z]:\\[^\s]+', '[PATH]', query)
        sanitized = re.sub(r'/[^\s]+/[^\s]+', '[PATH]', sanitized)
        
        # Remove potential API keys or tokens
        sanitized = re.sub(r'[A-Za-z0-9]{16,}\b', '[TOKEN]', sanitized)
        
        # Remove email addresses
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
        
        return sanitized
    
    def validate_process_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate process name for kill operations.
        """
        # Prevent killing critical system processes
        critical_processes = [
            "System", "csrss.exe", "smss.exe", "wininit.exe", "services.exe",
            "lsass.exe", "winlogon.exe", "explorer.exe", "systemd", "init",
            "launchd", "kernel_task"
        ]
        
        if name.lower() in [p.lower() for p in critical_processes]:
            return False, f"Cannot kill critical system process: {name}"
        
        return True, ""
    
    def validate_integer_range(self, value: int, min_val: int = None, 
                              max_val: int = None) -> Tuple[bool, str]:
        """Validate integer is within allowed range."""
        if min_val is not None and value < min_val:
            return False, f"Value {value} below minimum {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"Value {value} above maximum {max_val}"
        
        return True, ""
    
    def validate_file_extension(self, path: str, 
                               allowed_extensions: List[str]) -> Tuple[bool, str]:
        """Validate file has allowed extension."""
        ext = Path(path).suffix.lower()
        if ext not in [e.lower() for e in allowed_extensions]:
            return False, f"File extension {ext} not allowed. Allowed: {allowed_extensions}"
        
        return True, ""
    
    def check_rate_limit(self, action: str, max_per_minute: int = 60) -> Tuple[bool, str]:
        """
        Check if action exceeds rate limit.
        Simple implementation - can be enhanced with proper rate limiting.
        """
        # TODO: Implement proper rate limiting with time windows
        # For now, just return True
        return True, ""
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate URL for browser operations."""
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"
        
        # Check for suspicious patterns
        if any(pattern in url.lower() for pattern in ['javascript:', 'data:', 'file:']):
            return False, "Suspicious URL scheme detected"
        
        return True, ""
    
    def get_safe_temp_dir(self) -> Path:
        """Get safe temporary directory for code execution."""
        import tempfile
        temp_base = Path(tempfile.gettempdir()) / "Evo-AI_mogwai_sandbox"
        temp_base.mkdir(exist_ok=True)
        return temp_base


# Validation rules for common parameter types
VALIDATION_RULES = {
    "path": {
        "validator": "validate_path",
        "description": "File system path with safety checks"
    },
    "command": {
        "validator": "validate_command",
        "description": "Shell command with dangerous pattern detection"
    },
    "process_name": {
        "validator": "validate_process_name",
        "description": "Process name for kill operations"
    },
    "url": {
        "validator": "validate_url",
        "description": "URL for browser operations"
    }
}
