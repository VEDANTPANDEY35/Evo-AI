"""
Integration tests for complete workflows.
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.action_parser import ActionParser
from core.tool_registry import ToolRegistry, ToolMetadata, ToolParameter, RiskLevel
from core.safety_validator import SafetyValidator
from core.permission_manager import PermissionManager, PermissionResponse


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.parser = ActionParser(debug=False)
        self.registry = ToolRegistry(debug=False)
        self.validator = SafetyValidator(debug=False)
        self.temp_dir = tempfile.mkdtemp()
        
        # Setup permission manager with temp config
        self.perm_manager = PermissionManager(
            config_dir=self.temp_dir,
            debug=False
        )
        
        # Register a test tool
        def create_test_file(path, content):
            Path(path).write_text(content)
            return f"Created {path}"
        
        self.registry.register_tool(ToolMetadata(
            name="create_file",
            description="Create a file",
            function=create_test_file,
            parameters=[
                ToolParameter(name="path", type="path", required=True),
                ToolParameter(name="content", type="string", required=True)
            ],
            risk_level=RiskLevel.LOW,
            permissions_required=["write_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
    
    def test_complete_workflow_parse_validate_execute(self):
        """Test complete workflow: parse -> validate -> execute."""
        # 1. Parse LLM output
        llm_output = '''
        I'll create that file for you.
        [ACTION: tool=create_file args={"path":"test.txt","content":"Hello World"}]
        '''
        
        actions = self.parser.parse(llm_output)
        assert len(actions) == 1
        
        action = actions[0]
        
        # 2. Validate tool call
        is_valid, error = self.registry.validate_tool_call(action.tool, action.args)
        assert is_valid, f"Validation failed: {error}"
        
        # 3. Validate path safety
        test_path = Path(self.temp_dir) / "test.txt"
        action.args["path"] = str(test_path)
        
        is_safe, error = self.validator.validate_path(action.args["path"], "write")
        assert is_safe, f"Path validation failed: {error}"
        
        # 4. Check permissions (grant for test)
        self.perm_manager.grant_permission("write_file")
        assert self.perm_manager.check_permission("write_file")
        
        # 5. Execute
        tool = self.registry.get_tool(action.tool)
        result = tool.function(**action.args)
        
        # 6. Verify
        assert test_path.exists()
        assert test_path.read_text() == "Hello World"
    
    def test_blocked_unsafe_path(self):
        """Test that unsafe paths are blocked."""
        # Try to create file in protected directory
        if self.validator.platform == "Windows":
            unsafe_path = "C:\\Windows\\test.txt"
        else:
            unsafe_path = "/etc/test.txt"
        
        is_safe, error = self.validator.validate_path(unsafe_path, "write")
        assert not is_safe
        assert "protected" in error.lower()
    
    def test_permission_denied_workflow(self):
        """Test workflow when permission is denied."""
        # Ensure permission is not granted
        self.perm_manager.revoke_permission("write_file")
        
        # Check permission
        has_permission = self.perm_manager.check_permission("write_file")
        assert not has_permission
        
        # In real scenario, would prompt user and they would deny
        # For test, we just verify the check works
    
    def test_invalid_tool_call_rejected(self):
        """Test that invalid tool calls are rejected."""
        # Missing required parameter
        is_valid, error = self.registry.validate_tool_call(
            "create_file",
            {"path": "test.txt"}  # Missing 'content'
        )
        assert not is_valid
        assert "required" in error.lower()
    
    def test_browser_search_workflow(self):
        """Test browser search workflow (mocked)."""
        # Register browser tool
        def mock_browser_search(query, engine="google"):
            return f"Searching for: {query} on {engine}"
        
        self.registry.register_tool(ToolMetadata(
            name="open_browser_search",
            description="Search the web",
            function=mock_browser_search,
            parameters=[
                ToolParameter(name="query", type="string", required=True),
                ToolParameter(name="engine", type="string", required=False, default="google")
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_browser"],
            os_support=["windows", "linux", "darwin"],
            category="browser"
        ))
        
        # Parse action
        llm_output = '[ACTION: tool=open_browser_search args={"query":"python tutorials","engine":"google"}]'
        actions = self.parser.parse(llm_output)
        
        assert len(actions) == 1
        action = actions[0]
        
        # Validate
        is_valid, error = self.registry.validate_tool_call(action.tool, action.args)
        assert is_valid
        
        # Sanitize query
        sanitized_query = self.validator.sanitize_query(action.args["query"])
        
        # Execute (mocked)
        tool = self.registry.get_tool(action.tool)
        result = tool.function(sanitized_query, action.args.get("engine", "google"))
        
        assert "python tutorials" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
