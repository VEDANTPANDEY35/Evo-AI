"""
Environment Awareness Layer - Cross-platform OS detection and path resolution.
Deterministic, OS-native only. No LLM-based detection.
Works on Windows, macOS, and Linux.
"""
import os
import platform
import re
from pathlib import Path
from typing import Optional, Dict, List
import psutil


class EnvironmentManager:
    """
    Provides environment metadata and path resolution.
    Does NOT execute actions - only provides information.
    """
    
    def __init__(self):
        self.os_type = self.detect_os()
        self.username = self.get_username()
        self.home_path = self.get_home_path()
        self.standard_paths = self.get_standard_paths()
    
    def detect_os(self) -> str:
        """
        Detect operating system.
        Returns: "windows", "linux", or "macos"
        """
        system = platform.system().lower()
        
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            # Fallback for unknown systems
            return "linux"
    
    def get_username(self) -> str:
        """Get current username."""
        try:
            # Try multiple methods for cross-platform compatibility
            username = os.getenv("USER") or os.getenv("USERNAME") or os.getlogin()
            return username if username else "unknown"
        except Exception:
            return "unknown"
    
    def get_home_path(self) -> Path:
        """Get user home directory path."""
        return Path.home()
    
    def get_standard_paths(self) -> Dict[str, Path]:
        """
        Get standard user directories (Desktop, Documents, Downloads).
        Returns dict with lowercase keys for easy lookup.
        """
        home = self.get_home_path()
        paths = {"home": home}
        
        if self.os_type == "windows":
            # Windows standard paths
            paths["desktop"] = home / "Desktop"
            paths["documents"] = home / "Documents"
            paths["downloads"] = home / "Downloads"
        
        elif self.os_type == "macos":
            # macOS standard paths
            paths["desktop"] = home / "Desktop"
            paths["documents"] = home / "Documents"
            paths["downloads"] = home / "Downloads"
        
        else:  # linux
            # Linux standard paths (XDG)
            # Try XDG user dirs first, fallback to common names
            xdg_desktop = os.getenv("XDG_DESKTOP_DIR")
            xdg_documents = os.getenv("XDG_DOCUMENTS_DIR")
            xdg_downloads = os.getenv("XDG_DOWNLOAD_DIR")
            
            paths["desktop"] = Path(xdg_desktop) if xdg_desktop else home / "Desktop"
            paths["documents"] = Path(xdg_documents) if xdg_documents else home / "Documents"
            paths["downloads"] = Path(xdg_downloads) if xdg_downloads else home / "Downloads"
        
        return paths
    
    def resolve_natural_path(self, text: str) -> Optional[Path]:
        """
        Resolve natural language path references to absolute paths.
        
        Examples:
            "project.py from desktop" -> /home/user/Desktop/project.py
            "file.txt in documents" -> /home/user/Documents/file.txt
            "downloads/archive.zip" -> /home/user/Downloads/archive.zip
        
        Returns None if cannot resolve safely or path doesn't exist.
        """
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Pattern 1: "filename from location"
        match = re.search(r'([^\s]+)\s+(?:from|in|at)\s+(desktop|documents|downloads|home)', text_lower)
        if match:
            filename = match.group(1)
            location = match.group(2)
            
            if location in self.standard_paths:
                full_path = self.standard_paths[location] / filename
                if full_path.exists():
                    return full_path
                else:
                    return None
        
        # Pattern 2: "location/filename" or "location\filename"
        for location_name, location_path in self.standard_paths.items():
            # Check if text starts with location name
            if text_lower.startswith(location_name):
                # Extract the rest as relative path
                relative_part = text[len(location_name):].lstrip('/\\')
                if relative_part:
                    full_path = location_path / relative_part
                    if full_path.exists():
                        return full_path
                    else:
                        return None
        
        # Pattern 3: Just location name (return the directory itself)
        if text_lower in self.standard_paths:
            location_path = self.standard_paths[text_lower]
            if location_path.exists():
                return location_path
        
        # Pattern 4: Absolute path or relative path (validate it exists)
        try:
            path = Path(text)
            if path.exists():
                return path.resolve()
        except Exception:
            pass
        
        # Cannot resolve safely
        return None
    
    def list_running_processes(self) -> List[Dict[str, any]]:
        """
        List all running processes.
        Returns structured list: [{"pid": int, "name": str}, ...]
        
        Safe, cross-platform, no shell commands.
        """
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_info = proc.info
                    processes.append({
                        "pid": proc_info['pid'],
                        "name": proc_info['name']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process terminated or access denied - skip it
                    continue
        except Exception:
            # If psutil fails entirely, return empty list
            pass
        
        return processes
    
    def get_process_by_name(self, name: str) -> List[Dict[str, any]]:
        """
        Find processes by name (case-insensitive partial match).
        Returns list of matching processes.
        """
        name_lower = name.lower()
        all_processes = self.list_running_processes()
        
        matching = [
            proc for proc in all_processes
            if name_lower in proc['name'].lower()
        ]
        
        return matching
    
    def is_process_running(self, name: str) -> bool:
        """Check if a process with given name is running."""
        return len(self.get_process_by_name(name)) > 0
    
    def validate_path_exists(self, path: str) -> bool:
        """
        Validate that a path exists.
        Safe wrapper around Path.exists()
        """
        try:
            return Path(path).exists()
        except Exception:
            return False
    
    def get_environment_info(self) -> Dict[str, any]:
        """
        Get complete environment information summary.
        Useful for debugging and system awareness.
        """
        return {
            "os": self.os_type,
            "username": self.username,
            "home": str(self.home_path),
            "desktop": str(self.standard_paths.get("desktop", "N/A")),
            "documents": str(self.standard_paths.get("documents", "N/A")),
            "downloads": str(self.standard_paths.get("downloads", "N/A")),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }
