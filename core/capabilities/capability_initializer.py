"""
Capability Initializer - Registers all available capabilities.
"""
from .capability_registry import get_capability_registry
from .file_management_capability import FileManagementCapability


def initialize_capabilities(debug: bool = False):
    """Initialize and register all available capabilities."""
    registry = get_capability_registry(debug=debug)
    
    # Register file management capability
    file_mgmt = FileManagementCapability(debug=debug)
    registry.register_capability(file_mgmt)
    
    if debug:
        print(f"[CAPABILITY_INIT] Initialized {len(registry.list_capabilities())} capabilities")
    
    return registry