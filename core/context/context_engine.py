"""
Context Engine - Orchestrates all context gathering modes.
"""
from typing import Dict, Any, Optional, Tuple
from .system_context import SystemContext
from .workspace_context import WorkspaceContext
from .project_analyzer import ProjectAnalyzer
from .visual_context import VisualContext


class ContextEngine:
    """
    Orchestrates context gathering across different modes.
    
    Modes:
    1. Surface Workspace Awareness (default, fast <100ms)
    2. Deep Project Awareness (on-demand)
    3. Visual Context (explicit permission required)
    """
    
    def __init__(self, environment_manager=None, debug: bool = False):
        self.debug = debug
        self.environment = environment_manager
        
        # Initialize context modules
        self.system_context = SystemContext(debug=debug)
        self.workspace_context = WorkspaceContext(debug=debug)
        self.project_analyzer = ProjectAnalyzer(debug=debug)
        self.visual_context = VisualContext(debug=debug)
    
    def _log(self, message: str):
        if self.debug:
            print(f"[CONTEXT_ENGINE] {message}")
    
    def get_surface_context(self) -> Dict[str, Any]:
        """
        Get lightweight surface context (default mode).
        
        Fast operation (<100ms):
        - System info
        - Active window
        - Top processes
        - Recent files in standard locations
        - Current directory info
        
        Returns:
            Dict with surface context information
        """
        try:
            self._log("Gathering surface context")
            
            context = {
                'mode': 'surface',
                'system': self.system_context.get_system_info(),
                'active_window': self.system_context.get_active_window(),
                'top_processes': self.system_context.get_running_processes(limit=5),
                'workspace': {
                    'current_directory': self.workspace_context.get_current_directory_info(),
                    'recent_activity': self.workspace_context.get_standard_locations_activity()
                }
            }
            
            # Add environment info if available
            if self.environment:
                context['environment'] = {
                    'os': self.environment.os_type,
                    'username': self.environment.username,
                    'home': self.environment.home_path,
                    'standard_paths': self.environment.standard_paths
                }
            
            self._log("Surface context gathered")
            return context
            
        except Exception as e:
            self._log(f"Error gathering surface context: {e}")
            return {'error': str(e)}
    
    def analyze_project(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform deep project analysis (on-demand only).
        
        This is a temporary analysis - no persistent storage.
        Data is discarded after analysis completes.
        
        Args:
            path: Project path (defaults to current directory)
            
        Returns:
            Dict with project analysis
        """
        try:
            self._log("Starting deep project analysis")
            
            # Detect project root if not specified
            if not path:
                path = self.project_analyzer.detect_project_root()
                if not path:
                    return {
                        'error': 'No project root detected',
                        'suggestion': 'Specify a project path explicitly'
                    }
            
            # Analyze project
            analysis = self.project_analyzer.analyze_project(path)
            analysis['mode'] = 'deep_project'
            
            self._log("Project analysis complete")
            return analysis
            
        except Exception as e:
            self._log(f"Error in project analysis: {e}")
            return {'error': str(e)}
    
    def capture_screen_with_permission(self, reason: str = "Screen analysis") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Capture screenshot with explicit permission.
        
        Strict permission workflow:
        1. AI requests permission
        2. User approves/denies
        3. If approved, capture screenshot
        4. Return result
        
        Args:
            reason: Reason for screenshot request
            
        Returns:
            (success, screenshot_path, error_message)
        """
        try:
            self._log(f"Requesting screenshot permission: {reason}")
            
            success, path, error = self.visual_context.capture_screen_with_permission(reason)
            
            if success:
                self._log(f"Screenshot captured: {path}")
            else:
                self._log(f"Screenshot failed: {error}")
            
            return success, path, error
            
        except Exception as e:
            self._log(f"Error in screen capture: {e}")
            return False, None, str(e)
    
    def get_context_summary(self, mode: str = 'surface') -> str:
        """
        Get human-readable context summary.
        
        Args:
            mode: 'surface', 'deep', or 'visual'
            
        Returns:
            Formatted context summary
        """
        try:
            if mode == 'surface':
                context = self.get_surface_context()
                return self._format_surface_context(context)
            elif mode == 'deep':
                context = self.analyze_project()
                return self._format_project_context(context)
            else:
                return "Invalid context mode"
                
        except Exception as e:
            return f"Error getting context summary: {e}"
    
    def _format_surface_context(self, context: Dict[str, Any]) -> str:
        """Format surface context for display."""
        lines = ["=== Surface Context ==="]
        
        if 'system' in context:
            sys = context['system']
            lines.append(f"OS: {sys.get('os')} ({sys.get('username')})")
            lines.append(f"Memory: {sys.get('memory_gb')}GB")
        
        if 'active_window' in context and context['active_window']:
            lines.append(f"Active: {context['active_window']}")
        
        if 'workspace' in context:
            ws = context['workspace']
            if 'current_directory' in ws:
                cwd = ws['current_directory']
                lines.append(f"Directory: {cwd.get('name')} ({cwd.get('file_count')} files)")
        
        return "\n".join(lines)
    
    def _format_project_context(self, context: Dict[str, Any]) -> str:
        """Format project context for display."""
        if 'error' in context:
            return f"Project Analysis Error: {context['error']}"
        
        lines = ["=== Project Analysis ==="]
        lines.append(f"Name: {context.get('name')}")
        lines.append(f"Type: {context.get('type')}")
        lines.append(f"Root: {context.get('root')}")
        
        if 'structure' in context:
            struct = context['structure']
            lines.append(f"Files: {struct.get('total_files')}")
            lines.append(f"Folders: {struct.get('total_folders')}")
        
        if 'dependencies' in context:
            deps = context['dependencies']
            if deps:
                lines.append(f"Dependencies: {', '.join([d['name'] for d in deps])}")
        
        return "\n".join(lines)
