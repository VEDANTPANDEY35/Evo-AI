"""
Capabilities Framework - Modular AI abilities.
"""
from .base_capability import BaseCapability
from .capability_registry import CapabilityRegistry, get_capability_registry
from .file_management_capability import FileManagementCapability
from .capability_initializer import initialize_capabilities

__all__ = [
    'BaseCapability',
    'CapabilityRegistry', 
    'get_capability_registry',
    'FileManagementCapability',
    'initialize_capabilities'
]