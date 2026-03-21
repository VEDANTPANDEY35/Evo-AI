"""
Unit tests for tool registry.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tool_registry import ToolRegistry, ToolMetadata, ToolParameter, RiskLevel


class TestToolRegistry:
    """Test suite for ToolRegistry."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.registry = ToolRegistry(debug=False)
    
    def test_register_tool(self):
        """Test registering a new tool."""
        def dummy_function(x):
            return x * 2
        
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            function=dummy_function,
            parameters=[
                ToolParameter(name="x", type="integer", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="test"
        )
        
        success = self.registry.register_tool(metadata)
        assert success
        
        # Verify tool is registered
        tool = self.registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
    
    def test_duplicate_registration(self):
        """Test that duplicate registration is prevented."""
        def dummy_function():
            pass
        
        metadata = ToolMetadata(
            name="duplicate_tool",
            description="Test",
            function=dummy_function,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=[],
            os_support=["windows"],
            category="test"
        )
        
        # First registration should succeed
        assert self.registry.register_tool(metadata)
        
        # Second registration should fail
        assert not self.registry.register_tool(metadata)
    
    def test_validate_tool_call_success(self):
        """Test successful tool call validation."""
        def dummy_function(name, age):
            pass
        
        metadata = ToolMetadata(
            name="validate_test",
            description="Test validation",
            function=dummy_function,
            parameters=[
                ToolParameter(name="name", type="string", required=True),
                ToolParameter(name="age", type="integer", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=[],
            os_support=["windows"],
            category="test"
        )
        
        self.registry.register_tool(metadata)
        
        # Valid call
        is_valid, error = self.registry.validate_tool_call(
            "validate_test",
            {"name": "John", "age": 30}
        )
        assert is_valid
        assert error == ""
    
    def test_validate_tool_call_missing_param(self):
        """Test validation with missing required parameter."""
        def dummy_function(required_param):
            pass
        
        metadata = ToolMetadata(
            name="missing_param_test",
            description="Test",
            function=dummy_function,
            parameters=[
                ToolParameter(name="required_param", type="string", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=[],
            os_support=["windows"],
            category="test"
        )
        
        self.registry.register_tool(metadata)
        
        # Missing required parameter
        is_valid, error = self.registry.validate_tool_call(
            "missing_param_test",
            {}
        )
        assert not is_valid
        assert "required" in error.lower()
    
    def test_validate_tool_call_wrong_type(self):
        """Test validation with wrong parameter type."""
        def dummy_function(number):
            pass
        
        metadata = ToolMetadata(
            name="type_test",
            description="Test",
            function=dummy_function,
            parameters=[
                ToolParameter(name="number", type="integer", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=[],
            os_support=["windows"],
            category="test"
        )
        
        self.registry.register_tool(metadata)
        
        # Wrong type (string instead of integer)
        is_valid, error = self.registry.validate_tool_call(
            "type_test",
            {"number": "not a number"}
        )
        assert not is_valid
        assert "type" in error.lower()
    
    def test_list_tools_by_category(self):
        """Test listing tools filtered by category."""
        # Register tools in different categories
        for i, category in enumerate(["file", "process", "file"]):
            def dummy():
                pass
            
            metadata = ToolMetadata(
                name=f"tool_{i}",
                description="Test",
                function=dummy,
                parameters=[],
                risk_level=RiskLevel.SAFE,
                permissions_required=[],
                os_support=["windows"],
                category=category
            )
            self.registry.register_tool(metadata)
        
        # List file category tools
        file_tools = self.registry.list_tools(category="file")
        assert len(file_tools) == 2
        assert all(t.category == "file" for t in file_tools)
    
    def test_get_tool_descriptions(self):
        """Test getting formatted tool descriptions."""
        def dummy():
            pass
        
        metadata = ToolMetadata(
            name="desc_test",
            description="A test tool for descriptions",
            function=dummy,
            parameters=[
                ToolParameter(name="param1", type="string", required=True)
            ],
            risk_level=RiskLevel.LOW,
            permissions_required=[],
            os_support=["windows"],
            category="test"
        )
        
        self.registry.register_tool(metadata)
        
        descriptions = self.registry.get_tool_descriptions()
        assert "desc_test" in descriptions
        assert "A test tool for descriptions" in descriptions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
