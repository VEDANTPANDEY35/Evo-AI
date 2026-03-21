"""
Base Capability - Abstract interface for modular AI capabilities.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseCapability(ABC):
    """Abstract base class for AI capabilities."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Capability name identifier."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this capability does."""
        pass
    
    @property
    @abstractmethod
    def available_actions(self) -> List[str]:
        """List of action names this capability can execute."""
        pass
    
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any] = None) -> Any:
        """
        Execute a capability action.
        
        Args:
            action: Action name to execute
            params: Parameters for the action
            
        Returns:
            Action result
        """
        pass
    
    def _log(self, message: str):
        """Log debug message if debug enabled."""
        if self.debug:
            print(f"[{self.name.upper()}] {message}")
    
    def validate_action(self, action: str) -> bool:
        """Check if action is supported by this capability."""
        return action in self.available_actions