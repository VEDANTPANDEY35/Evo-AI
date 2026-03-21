"""
Task executor for local operations - Registry-based with full safety integration.
"""
from typing import Dict, Any, Optional, List
from .tools import SystemTools
from .tool_registry import get_registry
from .safety_validator import SafetyValidator
from .permission_manager import PermissionManager, require_permission


class Executor:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.tools = SystemTools(debug=debug)  # This registers all tools
        self.registry = get_registry(debug=debug)
        self.validator = SafetyValidator(debug=debug)
        self.permission_manager = PermissionManager(debug=debug)
        self.execution_history: List[Dict[str, Any]] = []
        self._capability_registry = None
    
    def _log(self, message: str):
        if self.debug:
            print(f"[EXECUTOR] {message}")
    
    def _get_capability_registry(self):
        """Lazy load capability registry to avoid circular imports."""
        if self._capability_registry is None:
            from .capabilities import get_capability_registry
            self._capability_registry = get_capability_registry(debug=self.debug)
        return self._capability_registry
    
    def _record_execution(self, action: str, params: Dict[str, Any], result: Any, success: bool):
        """Record execution for history/debugging."""
        self.execution_history.append({
            "action": action,
            "params": params,
            "result": str(result)[:200],  # Truncate long results
            "success": success
        })
    
    def execute_action(self, action: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Execute action using tool registry with full safety validation."""
        params = params or {}
        self._log(f"Executing action: {action}")
        
        # Check if this is a capability action (format: "capability_name.action_name")
        if '.' in action:
            parts = action.split('.', 1)
            if len(parts) == 2:
                cap_name, action_name = parts
                registry = self._get_capability_registry()
                capability = registry.get_capability(cap_name)
                
                if capability and capability.validate_action(action_name):
                    self._log(f"Executing capability action: {cap_name}.{action_name}")
                    try:
                        result = capability.execute(action_name, params)
                        self._record_execution(action, params, result, True)
                        return result
                    except Exception as e:
                        error_msg = f"Capability execution error: {e}"
                        self._record_execution(action, params, error_msg, False)
                        return error_msg
        
        # Get tool from registry
        tool_metadata = self.registry.get_tool(action)
        if not tool_metadata:
            return f"Unknown tool: {action}"
        
        # Validate tool call against schema
        is_valid, error_msg = self.registry.validate_tool_call(action, params)
        if not is_valid:
            return f"Invalid parameters: {error_msg}"
        
        # Safety validation for specific parameter types
        for param_name, param_value in params.items():
            param_def = next((p for p in tool_metadata.parameters if p.name == param_name), None)
            if param_def and param_def.type == "path":
                # Validate path safety
                operation = "write" if action in ["write_file", "create_file", "delete_file"] else "read"
                is_safe, safety_error = self.validator.validate_path(param_value, operation)
                if not is_safe:
                    return f"Unsafe path: {safety_error}"
        
        # Check permissions
        for permission in tool_metadata.permissions_required:
            if not require_permission(
                permission, 
                action, 
                f"Execute {action}",
                tool_metadata.risk_level.value,
                params,
                self.permission_manager
            ):
                return "Permission denied"
        
        # Execute the tool
        try:
            result = tool_metadata.function(**params)
            
            # Sanitize output before formatting
            result = self._sanitize_output(result)
            
            # Format result if it's a dict (like system_info)
            if isinstance(result, dict) and action == "get_system_info":
                result = self.tools.format_system_info(result)
            elif isinstance(result, dict) and action == "get_self_info":
                result = self.tools.format_self_info(result)
            elif isinstance(result, list) and action == "list_processes":
                result = self.tools.format_processes(result)
            elif isinstance(result, dict) and action == "get_network_info":
                result = self.tools.format_network_info(result)
            
            success = result is not None and "Error" not in str(result)
            self._record_execution(action, params, result, success)
            return result
        except Exception as e:
            error_msg = f"Execution error: {e}"
            self._record_execution(action, params, error_msg, False)
            return error_msg
    
    def _sanitize_output(self, result: Any) -> Any:
        """Sanitize tool output to prevent formatting errors."""
        if result is None:
            return "No result"
        
        # Handle lists - flatten nested lists and convert to strings
        if isinstance(result, list):
            sanitized = []
            for item in result:
                if isinstance(item, list):
                    # Flatten nested list
                    sanitized.extend([str(x) for x in item])
                else:
                    sanitized.append(str(item))
            return sanitized
        
        # Handle other types
        return result
    
    def _legacy_execute_action(self, action: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Legacy execution method - kept for backward compatibility."""
        params = params or {}
        
        self._log(f"Executing action (legacy): {action}")
        
        # System info
        if action == "get_system_info":
            if not self.safety.check_permission("read_system_info"):
                if not self.safety.request_permission("read_system_info", "Read system hardware information"):
                    return "Permission denied"
            
            info = self.tools.get_system_info()
            return self.tools.format_system_info(info)
        
        # Read file
        elif action == "read_file":
            file_path = params.get("path", "")
            if not file_path:
                return "Error: No file path provided"
            
            if not self.safety.check_permission("open_file"):
                if not self.safety.request_permission("open_file", f"Read file: {file_path}"):
                    return "Permission denied"
            
            content = self.tools.read_file(file_path)
            return content if content else "Error reading file"
        
        # Write file
        elif action == "write_file":
            file_path = params.get("path", "")
            content = params.get("content", "")
            
            if not file_path:
                return "Error: No file path provided"
            
            if not self.safety.check_permission("write_file"):
                if not self.safety.request_permission("write_file", f"Write to file: {file_path}"):
                    return "Permission denied"
            
            success = self.tools.write_file(file_path, content)
            return "File written successfully" if success else "Error writing file"
        
        # Open application
        elif action == "open_application":
            app_name = params.get("app", "")
            if not app_name:
                return "Error: No application name provided"
            
            if not self.safety.check_permission("open_app"):
                if not self.safety.request_permission("open_app", f"Open application: {app_name}"):
                    return "Permission denied"
            
            success = self.tools.open_application(app_name)
            return f"Opened {app_name}" if success else f"Error opening {app_name}"
        
        # List directory
        elif action == "list_directory":
            dir_path = params.get("path", ".")
            
            if not self.safety.check_permission("open_file"):
                if not self.safety.request_permission("open_file", f"List directory: {dir_path}"):
                    return "Permission denied"
            
            items = self.tools.list_directory(dir_path)
            result = "\n".join(items) if items else "Error listing directory"
            self._record_execution(action, params, result, bool(items))
            return result
        
        # Search files
        elif action == "search_files":
            pattern = params.get("pattern", "*")
            directory = params.get("path", ".")
            
            if not self.safety.check_permission("open_file"):
                if not self.safety.request_permission("open_file", f"Search files: {pattern}"):
                    return "Permission denied"
            
            results = self.tools.search_files(pattern, directory)
            if results:
                result = f"Found {len(results)} files:\n" + "\n".join(results[:20])
                if len(results) > 20:
                    result += f"\n... and {len(results) - 20} more"
            else:
                result = "No files found"
            
            self._record_execution(action, params, result, bool(results))
            return result
        
        # Delete file
        elif action == "delete_file":
            path = params.get("path", "")
            if not path:
                return "Error: No path provided"
            
            if not self.safety.check_permission("write_file"):
                if not self.safety.request_permission("write_file", f"Delete: {path}"):
                    return "Permission denied"
            
            success = self.tools.delete_file(path)
            result = f"Deleted {path}" if success else f"Error deleting {path}"
            self._record_execution(action, params, result, success)
            return result
        
        # Copy file
        elif action == "copy_file":
            src = params.get("src", "")
            dst = params.get("dst", "")
            
            if not src or not dst:
                return "Error: Source and destination required"
            
            if not self.safety.check_permission("write_file"):
                if not self.safety.request_permission("write_file", f"Copy {src} to {dst}"):
                    return "Permission denied"
            
            success = self.tools.copy_file(src, dst)
            result = f"Copied {src} to {dst}" if success else "Error copying"
            self._record_execution(action, params, result, success)
            return result
        
        # Move file
        elif action == "move_file":
            src = params.get("src", "")
            dst = params.get("dst", "")
            
            if not src or not dst:
                return "Error: Source and destination required"
            
            if not self.safety.check_permission("write_file"):
                if not self.safety.request_permission("write_file", f"Move {src} to {dst}"):
                    return "Permission denied"
            
            success = self.tools.move_file(src, dst)
            result = f"Moved {src} to {dst}" if success else "Error moving"
            self._record_execution(action, params, result, success)
            return result
        
        # List processes
        elif action == "list_processes":
            if not self.safety.check_permission("read_system_info"):
                if not self.safety.request_permission("read_system_info", "List running processes"):
                    return "Permission denied"
            
            processes = self.tools.list_processes()
            result = self.tools.format_processes(processes)
            self._record_execution(action, params, result, bool(processes))
            return result
        
        # Kill process
        elif action == "kill_process":
            pid = params.get("pid")
            name = params.get("name")
            
            if not pid and not name:
                return "Error: Process PID or name required"
            
            if not self.safety.check_permission("run_code"):
                if not self.safety.request_permission("run_code", f"Kill process: {pid or name}"):
                    return "Permission denied"
            
            success = self.tools.kill_process(pid=pid, name=name)
            result = f"Process terminated" if success else "Error terminating process"
            self._record_execution(action, params, result, success)
            return result
        
        # Clipboard operations
        elif action == "get_clipboard":
            if not self.safety.check_permission("read_system_info"):
                if not self.safety.request_permission("read_system_info", "Read clipboard"):
                    return "Permission denied"
            
            content = self.tools.get_clipboard()
            result = f"Clipboard: {content}" if content else "Clipboard empty or error"
            self._record_execution(action, params, result, bool(content))
            return result
        
        elif action == "set_clipboard":
            text = params.get("text", "")
            if not text:
                return "Error: No text provided"
            
            if not self.safety.check_permission("write_file"):
                if not self.safety.request_permission("write_file", "Set clipboard"):
                    return "Permission denied"
            
            success = self.tools.set_clipboard(text)
            result = "Clipboard set" if success else "Error setting clipboard"
            self._record_execution(action, params, result, success)
            return result
        
        # Screenshot
        elif action == "screenshot" or action == "take_screenshot":
            filename = params.get("filename")
            
            if not self.safety.check_permission("take_screenshot"):
                if not self.safety.request_permission("take_screenshot", "Take screenshot"):
                    return "Permission denied"
            
            result_file = self.tools.take_screenshot(filename)
            result = f"Screenshot saved: {result_file}" if result_file else "Error taking screenshot"
            self._record_execution(action, params, result, bool(result_file))
            return result
        
        # Open website
        elif action == "open_website":
            url = params.get("url", "")
            if not url:
                return "Error: No URL provided"
            
            if not self.safety.check_permission("open_browser"):
                if not self.safety.request_permission("open_browser", f"Open website: {url}"):
                    return "Permission denied"
            
            from core.browser_automation import BrowserAutomation
            browser = BrowserAutomation(debug=self.debug)
            
            # Add .com if it's just a name (youtube -> youtube.com)
            if not url.startswith(('http://', 'https://')) and '.' not in url:
                url = f"{url}.com"
            
            success, message = browser.open_website(url)
            
            if success:
                result = f"✓ Opened {url} in your browser"
            else:
                result = f"✗ Error: {message}\n   Link: https://{url}"
            
            self._record_execution(action, params, result, success)
            return result
        
        # Network info
        elif action == "network_info":
            if not self.safety.check_permission("read_system_info"):
                if not self.safety.request_permission("read_system_info", "Read network info"):
                    return "Permission denied"
            
            info = self.tools.get_network_info()
            result = self.tools.format_network_info(info)
            self._record_execution(action, params, result, "error" not in info)
            return result
        
        # Run command
        elif action == "run_command":
            command = params.get("command", "")
            if not command:
                return "Error: No command provided"
            
            if not self.safety.check_permission("run_code"):
                if not self.safety.request_permission("run_code", f"Run command: {command}"):
                    return "Permission denied"
            
            result = self.tools.run_command(command)
            if result["success"]:
                output = result["stdout"] or "Command completed"
            else:
                output = f"Error: {result.get('stderr') or result.get('error')}"
            
            self._record_execution(action, params, output, result["success"])
            return output
        
        else:
            return f"Unknown action: {action}"
    
    def execute_multiple(self, actions: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple actions in sequence."""
        results = []
        for action_spec in actions:
            action = action_spec.get("action")
            params = action_spec.get("params", {})
            result = self.execute_action(action, params)
            results.append(result)
        return results
