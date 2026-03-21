"""
File Management Capability - High-level file operations.
"""
import os
import glob
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .base_capability import BaseCapability


class FileManagementCapability(BaseCapability):
    """Capability for advanced file management operations."""
    
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self._tools = None
    
    @property
    def name(self) -> str:
        return "file_management"
    
    @property
    def description(self) -> str:
        return "Advanced file management operations like organizing downloads, finding files, and listing recent files"
    
    @property
    def available_actions(self) -> List[str]:
        return [
            "organize_downloads",
            "find_file",
            "list_recent_files"
        ]
    
    def _get_tools(self):
        """Lazy load SystemTools to avoid circular imports."""
        if self._tools is None:
            from ..tools import SystemTools
            self._tools = SystemTools(debug=self.debug)
        return self._tools
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Any:
        """Execute file management action."""
        params = params or {}
        
        if not self.validate_action(action):
            return f"Unknown action: {action}"
        
        try:
            if action == "organize_downloads":
                return self._organize_downloads(params)
            elif action == "find_file":
                return self._find_file(params)
            elif action == "list_recent_files":
                return self._list_recent_files(params)
        except Exception as e:
            self._log(f"Error executing {action}: {e}")
            return f"Error: {e}"
    
    def _organize_downloads(self, params: Dict[str, Any]) -> str:
        """Organize files in downloads folder by type."""
        try:
            downloads_path = os.path.expanduser("~/Downloads")
            if not os.path.exists(downloads_path):
                return "Downloads folder not found"
            
            # Get file types and counts
            file_types = {}
            files = os.listdir(downloads_path)
            
            for file in files:
                if os.path.isfile(os.path.join(downloads_path, file)):
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        file_types[ext] = file_types.get(ext, 0) + 1
            
            if not file_types:
                return "No files found in Downloads folder"
            
            # Format results
            result = ["Downloads folder analysis:"]
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                result.append(f"  {ext}: {count} files")
            
            result.append(f"\nTotal: {sum(file_types.values())} files")
            result.append("Note: Use file manager to organize files into folders")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"Error organizing downloads: {e}"
    
    def _find_file(self, params: Dict[str, Any]) -> str:
        """Find files matching a pattern."""
        try:
            pattern = params.get("pattern", "*")
            directory = params.get("directory", ".")
            
            tools = self._get_tools()
            results = tools.search_files(pattern, directory)
            
            if not results:
                return f"No files found matching '{pattern}'"
            
            # Limit results and format
            limited_results = results[:20]
            output = [f"Found {len(results)} files matching '{pattern}':"]
            
            for file_path in limited_results:
                # Show relative path if possible
                try:
                    rel_path = os.path.relpath(file_path)
                    if len(rel_path) < len(file_path):
                        output.append(f"  {rel_path}")
                    else:
                        output.append(f"  {file_path}")
                except:
                    output.append(f"  {file_path}")
            
            if len(results) > 20:
                output.append(f"  ... and {len(results) - 20} more files")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error finding files: {e}"
    
    def _list_recent_files(self, params: Dict[str, Any]) -> str:
        """List recently modified files."""
        try:
            directory = params.get("directory", ".")
            days = params.get("days", 7)
            
            if not os.path.exists(directory):
                return f"Directory not found: {directory}"
            
            # Find files modified in last N days
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_files = []
            
            for root, dirs, files in os.walk(directory):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                for file in files:
                    if file.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if mod_time > cutoff_time:
                            recent_files.append((file_path, mod_time))
                    except:
                        continue
            
            if not recent_files:
                return f"No files modified in the last {days} days"
            
            # Sort by modification time (newest first)
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            output = [f"Files modified in the last {days} days:"]
            
            for file_path, mod_time in recent_files[:15]:  # Show top 15
                try:
                    rel_path = os.path.relpath(file_path)
                    if len(rel_path) < len(file_path):
                        display_path = rel_path
                    else:
                        display_path = file_path
                    
                    time_str = mod_time.strftime("%Y-%m-%d %H:%M")
                    output.append(f"  {time_str} - {display_path}")
                except:
                    output.append(f"  {mod_time.strftime('%Y-%m-%d %H:%M')} - {file_path}")
            
            if len(recent_files) > 15:
                output.append(f"  ... and {len(recent_files) - 15} more files")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error listing recent files: {e}"