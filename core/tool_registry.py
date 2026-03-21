"""
Centralized Tool Registry with metadata, validation, and safety controls.
"""
import json
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class RiskLevel(Enum):
    """Risk levels for tool operations."""
    SAFE = "safe"           # Read-only, no system changes
    LOW = "low"             # Minor changes, easily reversible
    MEDIUM = "medium"       # Significant changes, some risk
    HIGH = "high"           # Destructive or system-level changes
    CRITICAL = "critical"   # Irreversible or dangerous operations


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""
    name: str
    type: str  # "string", "integer", "boolean", "path", "list"
    required: bool = True
    description: str = ""
    default: Any = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None  # Regex pattern for validation


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    description: str
    function: Callable
    parameters: List[ToolParameter]
    risk_level: RiskLevel
    permissions_required: List[str]
    os_support: List[str]  # ["windows", "linux", "darwin"]
    category: str  # "file", "process", "system", "network", "browser"
    examples: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['risk_level'] = self.risk_level.value
        data.pop('function')  # Don't serialize function
        return data


class ToolRegistry:
    """Centralized registry for all available tools."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._tools: Dict[str, ToolMetadata] = {}
        self._initialize_core_tools()
    
    def _log(self, message: str):
        if self.debug:
            print(f"[TOOL_REGISTRY] {message}")
    
    def register_tool(self, metadata: ToolMetadata) -> bool:
        """Register a new tool with validation."""
        try:
            # Validate metadata
            if not metadata.name or not metadata.function:
                self._log(f"Invalid tool metadata: {metadata.name}")
                return False
            
            # Check for duplicates
            if metadata.name in self._tools:
                self._log(f"Tool already registered: {metadata.name}")
                return False
            
            # Validate parameters
            for param in metadata.parameters:
                if not param.name or not param.type:
                    self._log(f"Invalid parameter in {metadata.name}: {param}")
                    return False
            
            self._tools[metadata.name] = metadata
            self._log(f"Registered tool: {metadata.name}")
            return True
            
        except Exception as e:
            self._log(f"Error registering tool {metadata.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            self._log(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None, 
                   risk_level: Optional[RiskLevel] = None) -> List[str]:
        """List all tool names, optionally filtered."""
        tools = list(self._tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]
        
        return [t.name for t in tools]
    
    def get_tool_descriptions(self, format: str = "text") -> str:
        """Get formatted tool descriptions for LLM."""
        if format == "json":
            return json.dumps([t.to_dict() for t in self._tools.values()], indent=2)
        
        # Text format for LLM system prompt
        descriptions = []
        for tool in sorted(self._tools.values(), key=lambda x: x.category):
            params_str = ", ".join([
                f"{p.name}:{p.type}{'?' if not p.required else ''}"
                for p in tool.parameters
            ])
            descriptions.append(
                f"- {tool.name}({params_str}): {tool.description} "
                f"[{tool.risk_level.value}]"
            )
        
        return "\n".join(descriptions)
    
    def validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate a tool call against its schema.
        Returns (is_valid, error_message)
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Unknown tool: {tool_name}"
        
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in args:
                return False, f"Missing required parameter: {param.name}"
        
        # Validate parameter types and values
        for param_name, param_value in args.items():
            # Find parameter definition
            param_def = next((p for p in tool.parameters if p.name == param_name), None)
            if not param_def:
                return False, f"Unknown parameter: {param_name}"
            
            # Type validation
            if not self._validate_type(param_value, param_def.type):
                return False, f"Invalid type for {param_name}: expected {param_def.type}"
            
            # Allowed values validation
            if param_def.allowed_values and param_value not in param_def.allowed_values:
                return False, f"Invalid value for {param_name}: must be one of {param_def.allowed_values}"
        
        return True, ""
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type."""
        type_map = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "path": str,
            "list": list,
            "dict": dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return True  # Unknown type, skip validation
        
        return isinstance(value, expected_python_type)
    
    def _initialize_core_tools(self):
        """Initialize core system tools."""
        # This will be populated by importing from tools.py
        # Placeholder - actual registration happens in tools.py
        pass
    
    def export_registry(self, filepath: str):
        """Export registry to JSON file."""
        try:
            data = {
                "tools": [t.to_dict() for t in self._tools.values()],
                "version": "1.0"
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            self._log(f"Registry exported to {filepath}")
        except Exception as e:
            self._log(f"Error exporting registry: {e}")


# Global registry instance
_global_registry = None


def get_registry(debug: bool = False) -> ToolRegistry:
    """Get or create global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry(debug=debug)
    return _global_registry
