"""
Project Analyzer - Deep project awareness (on-demand only).
"""
import os
from typing import Dict, Any, List, Optional


class ProjectAnalyzer:
    """Analyzes project structure on-demand. No persistent indexing."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        # Common project indicators
        self.project_markers = [
            'package.json',
            'requirements.txt',
            'Cargo.toml',
            'pom.xml',
            'build.gradle',
            'go.mod',
            'Gemfile',
            'composer.json',
            '.git',
            '.gitignore',
            'README.md',
            'setup.py',
            'pyproject.toml'
        ]
        
        # Common ignore patterns
        self.ignore_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            '.venv',
            'venv',
            'env',
            'dist',
            'build',
            '.pytest_cache',
            '.mypy_cache',
            'target',
            'bin',
            'obj'
        ]
    
    def _log(self, message: str):
        if self.debug:
            print(f"[PROJECT_ANALYZER] {message}")
    
    def detect_project_root(self, start_path: str = None) -> Optional[str]:
        """Detect project root by looking for project markers."""
        try:
            current = start_path or os.getcwd()
            
            # Walk up directory tree
            for _ in range(10):  # Limit depth
                for marker in self.project_markers:
                    if os.path.exists(os.path.join(current, marker)):
                        self._log(f"Project root detected: {current} (marker: {marker})")
                        return current
                
                parent = os.path.dirname(current)
                if parent == current:  # Reached root
                    break
                current = parent
            
            return None
            
        except Exception as e:
            self._log(f"Error detecting project root: {e}")
            return None
    
    def analyze_project(self, path: str) -> Dict[str, Any]:
        """
        Analyze project structure.
        Returns temporary analysis - no persistent storage.
        """
        try:
            if not os.path.exists(path):
                return {"error": "Path does not exist"}
            
            self._log(f"Analyzing project: {path}")
            
            analysis = {
                'root': path,
                'name': os.path.basename(path),
                'type': self._detect_project_type(path),
                'structure': self._analyze_structure(path),
                'dependencies': self._find_dependency_files(path),
                'file_stats': self._get_file_statistics(path)
            }
            
            return analysis
            
        except Exception as e:
            self._log(f"Error analyzing project: {e}")
            return {"error": str(e)}
    
    def _detect_project_type(self, path: str) -> str:
        """Detect project type based on files present."""
        type_indicators = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'node': ['package.json'],
            'rust': ['Cargo.toml'],
            'java': ['pom.xml', 'build.gradle'],
            'go': ['go.mod'],
            'ruby': ['Gemfile'],
            'php': ['composer.json']
        }
        
        for proj_type, indicators in type_indicators.items():
            for indicator in indicators:
                if os.path.exists(os.path.join(path, indicator)):
                    return proj_type
        
        return 'unknown'
    
    def _analyze_structure(self, path: str, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze folder structure (limited depth)."""
        try:
            structure = {
                'folders': [],
                'total_files': 0,
                'total_folders': 0
            }
            
            for root, dirs, files in os.walk(path):
                # Calculate depth
                depth = root[len(path):].count(os.sep)
                if depth >= max_depth:
                    dirs.clear()  # Don't recurse deeper
                    continue
                
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
                
                # Count files
                structure['total_files'] += len(files)
                structure['total_folders'] += len(dirs)
                
                # Record folder info
                if depth < 2:  # Only record top 2 levels
                    rel_path = os.path.relpath(root, path)
                    if rel_path != '.':
                        structure['folders'].append({
                            'path': rel_path,
                            'file_count': len(files),
                            'depth': depth
                        })
            
            return structure
            
        except Exception as e:
            self._log(f"Error analyzing structure: {e}")
            return {}
    
    def _find_dependency_files(self, path: str) -> List[Dict[str, Any]]:
        """Find dependency/configuration files."""
        dependency_files = []
        
        for marker in self.project_markers:
            file_path = os.path.join(path, marker)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    size = os.path.getsize(file_path)
                    dependency_files.append({
                        'name': marker,
                        'path': file_path,
                        'size_kb': round(size / 1024, 2)
                    })
                except:
                    continue
        
        return dependency_files
    
    def _get_file_statistics(self, path: str) -> Dict[str, Any]:
        """Get file type statistics."""
        try:
            extensions = {}
            total_size = 0
            
            for root, dirs, files in os.walk(path):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        ext = os.path.splitext(file)[1].lower()
                        if not ext:
                            ext = 'no_extension'
                        
                        size = os.path.getsize(file_path)
                        total_size += size
                        
                        if ext not in extensions:
                            extensions[ext] = {'count': 0, 'size': 0}
                        
                        extensions[ext]['count'] += 1
                        extensions[ext]['size'] += size
                        
                    except:
                        continue
            
            # Sort by count
            sorted_exts = sorted(
                extensions.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]  # Top 10
            
            return {
                'total_size_mb': round(total_size / (1024**2), 2),
                'extensions': {
                    ext: {
                        'count': data['count'],
                        'size_kb': round(data['size'] / 1024, 2)
                    }
                    for ext, data in sorted_exts
                }
            }
            
        except Exception as e:
            self._log(f"Error getting file statistics: {e}")
            return {}
