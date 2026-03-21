"""
Capability Registry - Manages registration and retrieval of capabilities.
"""
from typing import Dict, List, Optional
from .base_capability import BaseCapability


class CapabilityRegistry:
    """Registry for managing AI capabilities."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._capabilities: Dict[str, BaseCapability] = {}
    
    def register_capability(self, capability: BaseCapability) -> bool:
        """
        Register a new capability.
        
        Args:
            capability: Capability instance to register
            
        Returns:
            True if registered successfully, False if already exists
        """
        if capability.name in self._capabilities:
            if self.debug:
                print(f"[CAPABILITY_REGISTRY] Capability '{capability.name}' already registered")
            return False
        
        self._capabilities[capability.name] = capability
        if self.debug:
            print(f"[CAPABILITY_REGISTRY] Registered capability: {capability.name}")
        return True
    
    def get_capability(self, name: str) -> Optional[BaseCapability]:
        """
        Retrieve capability by name.
        
        Args:
            name: Capability name
            
        Returns:
            Capability instance or None if not found
        """
        return self._capabilities.get(name)
    
    def list_capabilities(self) -> List[str]:
        """
        Get list of all registered capability names.
        
        Returns:
            List of capability names
        """
        return list(self._capabilities.keys())
    
    def get_all_actions(self) -> Dict[str, str]:
        """
        Get all available actions across all capabilities.
        
        Returns:
            Dict mapping action names to capability names
        """
        actions = {}
        for cap_name, capability in self._capabilities.items():
            for action in capability.available_actions:
                actions[action] = cap_name
        return actions
    
    def find_capability_for_action(self, action: str) -> Optional[BaseCapability]:
        """
        Find which capability can handle a specific action.
        
        Args:
            action: Action name to find
            
        Returns:
            Capability that can handle the action, or None
        """
        for capability in self._capabilities.values():
            if capability.validate_action(action):
                return capability
        return None


# Global registry instance
_registry = None

def get_capability_registry(debug: bool = False) -> CapabilityRegistry:
    """Get the global capability registry instance."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry(debug=debug)
    return _registry