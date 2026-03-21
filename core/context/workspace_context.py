"""
Workspace Context - Surface-level workspace awareness.
"""
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta


class WorkspaceContext:
    """Gathers lightweight workspace context (fast, <100ms)."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _log(self, message: str):
        if self.debug:
            print(f"[WORKSPACE_CONTEXT] {message}")
    
    def get_recent_files(self, directory: str, days: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently modified files in a directory."""
        try:
            if not os.path.exists(directory):
                return []
            
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_files = []
            
            # Only scan top level (no recursion for speed)
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                if os.path.isfile(item_path):
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                        if mod_time > cutoff_time:
                            recent_files.append({
                                'name': item,
                                'path': item_path,
                                'modified': mod_time.isoformat(),
                                'size_kb': round(os.path.getsize(item_path) / 1024, 2)
                            })
                    except:
                        continue
            
            # Sort by modification time (newest first)
            recent_files.sort(key=lambda x: x['modified'], reverse=True)
            return recent_files[:limit]
            
        except Exception as e:
            self._log(f"Error getting recent files: {e}")
            return []
    
    def get_standard_locations_activity(self) -> Dict[str, Any]:
        """Get recent activity from standard user locations."""
        try:
            locations = {
                'desktop': os.path.expanduser("~/Desktop"),
                'documents': os.path.expanduser("~/Documents"),
                'downloads': os.path.expanduser("~/Downloads")
            }
            
            activity = {}
            for name, path in locations.items():
                if os.path.exists(path):
                    recent = self.get_recent_files(path, days=1, limit=5)
                    activity[name] = {
                        'path': path,
                        'recent_files': recent,
                        'file_count': len(recent)
                    }
            
            return activity
            
        except Exception as e:
            self._log(f"Error getting location activity: {e}")
            return {}
    
    def get_current_directory_info(self) -> Dict[str, Any]:
        """Get information about current working directory."""
        try:
            cwd = os.getcwd()
            
            # Count files and folders (top level only)
            files = []
            folders = []
            
            for item in os.listdir(cwd):
                item_path = os.path.join(cwd, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path):
                    folders.append(item)
            
            return {
                'path': cwd,
                'name': os.path.basename(cwd),
                'file_count': len(files),
                'folder_count': len(folders),
                'sample_files': files[:10],
                'sample_folders': folders[:10]
            }
            
        except Exception as e:
            self._log(f"Error getting current directory info: {e}")
            return {}
