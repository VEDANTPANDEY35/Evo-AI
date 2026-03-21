"""
Execution Verification Layer - STRICT verification of action execution.
Eliminates false positives by verifying actual state changes.
Deterministic only - no LLM-based verification.
"""
import time
from typing import Any, Tuple, Dict
from pathlib import Path


class ExecutionVerifier:
    """
    Strict execution verifier that ensures:
    1. Actions execute without error
    2. Intended state changes are verified
    3. Target objects exist (if applicable)
    4. Processes start (if applicable)
    
    NO PARTIAL LIES. NO FAKE CONFIRMATION.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        # Error keywords that indicate failure
        self.error_keywords = [
            "not recognized",
            "error",
            "failed",
            "cannot",
            "denied",
            "not found",
            "does not exist",
            "no such",
            "invalid",
            "unable",
            "could not",
            "can't",
            "couldn't",
            "permission denied",
            "access denied",
            "not available",
            "unavailable"
        ]
    
    def _log(self, message: str):
        if self.debug:
            print(f"[VERIFIER] {message}")
    
    def pre_check(self, step: Dict[str, Any], environment) -> Tuple[bool, str]:
        """
        Pre-execution validation.
        Checks BEFORE action is executed.
        
        Returns:
            (True, "") if validation passes
            (False, reason) if validation fails
        """
        action = step.get("action", "")
        params = step.get("params", {})
        
        self._log(f"Pre-check: {action} with {params}")
        
        # Validate required parameters exist
        if not action:
            return False, "No action specified"
        
        # File read operations - validate file exists
        if action in ["read_file", "open_file"]:
            file_path = params.get("path", "")
            if not file_path:
                return False, "No file path provided"
            
            # Try to resolve natural path
            resolved_path = environment.resolve_natural_path(file_path)
            if resolved_path:
                file_path = str(resolved_path)
            
            if not environment.validate_path_exists(file_path):
                return False, f"File does not exist: {file_path}"
        
        # File write operations - validate directory exists
        if action in ["write_file", "create_file"]:
            file_path = params.get("path", "")
            if not file_path:
                return False, "No file path provided"
            
            # Check if parent directory exists
            parent_dir = Path(file_path).parent
            if not parent_dir.exists():
                return False, f"Directory does not exist: {parent_dir}"
        
        # Application opening - validate app name provided
        if action == "open_application":
            app_name = params.get("app_name", "") or params.get("app", "")
            if not app_name:
                return False, "No application name provided"
        
        # Website opening - validate site name provided
        if action == "open_website":
            site_name = params.get("site_name", "") or params.get("url", "")
            if not site_name:
                return False, "No website name provided"
        
        # Process kill - validate PID or name provided
        if action == "kill_process":
            pid = params.get("pid")
            name = params.get("name")
            if not pid and not name:
                return False, "No process PID or name provided"
        
        # Search operations - validate pattern provided
        if action == "search_files":
            pattern = params.get("pattern", "")
            if not pattern:
                return False, "No search pattern provided"
        
        # Web search - validate query provided
        if action == "search_web":
            query = params.get("query", "")
            if not query:
                return False, "No search query provided"
        
        self._log("Pre-check passed")
        return True, ""
    
    def post_check(self, step: Dict[str, Any], result: Any, environment) -> Tuple[bool, str]:
        """
        Post-execution verification.
        Checks AFTER action is executed.
        
        Verifies:
        - No error strings in result
        - Actual state changes occurred
        - Target objects exist
        - Processes started
        
        Returns:
            (True, "") if verification passes
            (False, reason) if verification fails
        """
        action = step.get("action", "")
        params = step.get("params", {})
        
        self._log(f"Post-check: {action} with result type {type(result)}")
        
        # Check if result is None
        if result is None:
            return False, "Action returned no result"
        
        # Convert result to string for error checking
        result_str = str(result).lower()
        
        # Check for error keywords in result
        for error_keyword in self.error_keywords:
            if error_keyword in result_str:
                return False, f"Execution error detected: {error_keyword}"
        
        # Action-specific verification
        
        # 1. OPEN APPLICATION - Verify process is running
        if action == "open_application":
            app_name = params.get("app_name", "") or params.get("app", "")
            
            # Give process time to start
            time.sleep(0.5)
            
            # Check if process is running
            if not environment.is_process_running(app_name):
                return False, f"Application '{app_name}' did not start (process not found)"
            
            self._log(f"Verified: {app_name} process is running")
        
        # 2. FILE WRITE/CREATE - Verify file exists
        elif action in ["write_file", "create_file"]:
            file_path = params.get("path", "")
            
            if not environment.validate_path_exists(file_path):
                return False, f"File was not created: {file_path}"
            
            self._log(f"Verified: File exists at {file_path}")
        
        # 3. SCREENSHOT - Verify file created
        elif action == "take_screenshot":
            # Result should contain filename
            if "screenshot" not in result_str:
                return False, "Screenshot filename not in result"
            
            # Try to extract filename from result
            # Result format: "Screenshot saved: filename.png"
            if "saved:" in result_str:
                filename = result_str.split("saved:", 1)[1].strip()
                if not environment.validate_path_exists(filename):
                    return False, f"Screenshot file not found: {filename}"
                
                self._log(f"Verified: Screenshot exists at {filename}")
        
        # 4. LIST PROCESSES - Verify result is list and not empty
        elif action == "list_processes":
            if isinstance(result, str):
                # Result was formatted as string, check it's not empty
                if len(result.strip()) == 0:
                    return False, "Process list is empty"
            elif isinstance(result, list):
                if len(result) == 0:
                    return False, "Process list is empty"
            else:
                return False, f"Unexpected result type for list_processes: {type(result)}"
            
            self._log("Verified: Process list is not empty")
        
        # 5. LIST DIRECTORY - Verify result is not empty
        elif action == "list_directory":
            if isinstance(result, str):
                if len(result.strip()) == 0:
                    return False, "Directory is empty or could not be read"
            elif isinstance(result, list):
                # Empty directory is valid, but None is not
                pass
            else:
                return False, f"Unexpected result type for list_directory: {type(result)}"
            
            self._log("Verified: Directory listing completed")
        
        # 6. READ FILE - Verify result is not empty (unless file is actually empty)
        elif action == "read_file":
            # Result should be string content
            if not isinstance(result, str):
                return False, f"Unexpected result type for read_file: {type(result)}"
            
            # Empty string could be valid (empty file), so we just check type
            self._log("Verified: File read completed")
        
        # 7. SEARCH FILES - Verify result format
        elif action == "search_files":
            if isinstance(result, str):
                # Check if it's an error message
                if "no files found" in result_str and "error" not in result_str:
                    # This is valid - no matches found
                    self._log("Verified: Search completed (no matches)")
                elif "found" in result_str:
                    # Valid result with matches
                    self._log("Verified: Search completed with matches")
                else:
                    # Unexpected format
                    return False, "Unexpected search result format"
            elif isinstance(result, list):
                # List of files (could be empty)
                self._log(f"Verified: Search completed ({len(result)} matches)")
            else:
                return False, f"Unexpected result type for search_files: {type(result)}"
        
        # 8. SYSTEM INFO - Verify result contains expected data
        elif action == "get_system_info":
            if isinstance(result, str):
                # Should contain OS, CPU, memory info
                required_keywords = ["os", "cpu", "memory"]
                if not any(keyword in result_str for keyword in required_keywords):
                    return False, "System info result missing expected data"
                
                self._log("Verified: System info contains expected data")
            elif isinstance(result, dict):
                # Dict format is also valid
                self._log("Verified: System info returned as dict")
            else:
                return False, f"Unexpected result type for get_system_info: {type(result)}"
        
        # 9. OPEN WEBSITE - Verify success indicator
        elif action == "open_website":
            # Result should contain success indicator (✓)
            if "✓" not in result_str and "opened" not in result_str:
                return False, "Website opening not confirmed"
            
            self._log("Verified: Website opened")
        
        # 10. WEB SEARCH - Verify success indicator
        elif action == "search_web":
            # Result should contain success indicator
            if "✓" not in result_str and "searching" not in result_str:
                return False, "Web search not confirmed"
            
            self._log("Verified: Web search initiated")
        
        # 11. KILL PROCESS - Verify success message
        elif action == "kill_process":
            if "terminated" not in result_str and "killed" not in result_str:
                return False, "Process termination not confirmed"
            
            self._log("Verified: Process terminated")
        
        # 12. DELETE FILE - Verify file no longer exists
        elif action == "delete_file":
            file_path = params.get("path", "")
            
            if environment.validate_path_exists(file_path):
                return False, f"File still exists after deletion: {file_path}"
            
            self._log(f"Verified: File deleted at {file_path}")
        
        # Default: Check for success indicators
        else:
            # For other actions, check for common success indicators
            success_indicators = ["✓", "success", "completed", "done", "opened", "created"]
            has_success = any(indicator in result_str for indicator in success_indicators)
            
            if not has_success and len(result_str) < 10:
                # Short result without success indicator might be an error
                return False, "No success confirmation in result"
            
            self._log("Verified: Action completed (generic check)")
        
        self._log("Post-check passed")
        return True, ""
    
    def verify_execution(self, step: Dict[str, Any], result: Any, environment) -> Tuple[bool, str]:
        """
        Complete verification: pre-check + post-check.
        
        This is a convenience method that combines both checks.
        Note: pre_check should be called BEFORE execution,
        and post_check should be called AFTER execution.
        
        This method is for post-execution verification only.
        """
        return self.post_check(step, result, environment)
