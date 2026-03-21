"""
Test suite for Execution Verification Layer.
Tests strict verification of action execution.
"""
import pytest
import tempfile
from pathlib import Path
from core.verifier import ExecutionVerifier
from core.environment import EnvironmentManager


class TestExecutionVerifier:
    """Test ExecutionVerifier functionality."""
    
    @pytest.fixture
    def verifier(self):
        """Create ExecutionVerifier instance for testing."""
        return ExecutionVerifier(debug=True)
    
    @pytest.fixture
    def environment(self):
        """Create EnvironmentManager instance for testing."""
        return EnvironmentManager()
    
    # ========== PRE-CHECK TESTS ==========
    
    def test_pre_check_no_action(self, verifier, environment):
        """Test pre-check fails when no action specified."""
        step = {"params": {}}
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "no action" in reason.lower()
    
    def test_pre_check_read_nonexistent_file(self, verifier, environment):
        """Test 3: Pre-check fails for non-existent file."""
        step = {
            "action": "read_file",
            "params": {"path": "/nonexistent/file_that_does_not_exist.txt"}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "does not exist" in reason.lower()
    
    def test_pre_check_read_existing_file(self, verifier, environment, tmp_path):
        """Test pre-check passes for existing file."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        step = {
            "action": "read_file",
            "params": {"path": str(test_file)}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is True
        assert reason == ""
    
    def test_pre_check_write_file_no_path(self, verifier, environment):
        """Test pre-check fails when no path provided for write."""
        step = {
            "action": "write_file",
            "params": {"content": "test"}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "no file path" in reason.lower()
    
    def test_pre_check_open_app_no_name(self, verifier, environment):
        """Test pre-check fails when no app name provided."""
        step = {
            "action": "open_application",
            "params": {}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "no application name" in reason.lower()
    
    def test_pre_check_open_app_with_name(self, verifier, environment):
        """Test pre-check passes when app name provided."""
        step = {
            "action": "open_application",
            "params": {"app_name": "notepad"}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is True
        assert reason == ""
    
    def test_pre_check_search_files_no_pattern(self, verifier, environment):
        """Test pre-check fails when no search pattern provided."""
        step = {
            "action": "search_files",
            "params": {}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "no search pattern" in reason.lower()
    
    def test_pre_check_web_search_no_query(self, verifier, environment):
        """Test pre-check fails when no search query provided."""
        step = {
            "action": "search_web",
            "params": {}
        }
        ok, reason = verifier.pre_check(step, environment)
        
        assert ok is False
        assert "no search query" in reason.lower()
    
    # ========== POST-CHECK TESTS ==========
    
    def test_post_check_none_result(self, verifier, environment):
        """Test post-check fails when result is None."""
        step = {"action": "test_action", "params": {}}
        ok, reason = verifier.post_check(step, None, environment)
        
        assert ok is False
        assert "no result" in reason.lower()
    
    def test_post_check_error_in_result(self, verifier, environment):
        """Test 1: Post-check detects error strings in result."""
        step = {"action": "open_application", "params": {"app_name": "fake_app"}}
        
        # Test various error messages
        error_results = [
            "Error: command not recognized",
            "Failed to open application",
            "Cannot find the application",
            "Permission denied",
            "File not found",
            "Invalid command"
        ]
        
        for error_result in error_results:
            ok, reason = verifier.post_check(step, error_result, environment)
            assert ok is False, f"Should detect error in: {error_result}"
            assert "error detected" in reason.lower()
    
    def test_post_check_file_write_verification(self, verifier, environment, tmp_path):
        """Test post-check verifies file was created."""
        test_file = tmp_path / "new_file.txt"
        
        step = {
            "action": "create_file",
            "params": {"path": str(test_file)}
        }
        
        # Test 1: File doesn't exist - should fail
        result = f"✓ Created file: {test_file}"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is False
        assert "was not created" in reason.lower()
        
        # Test 2: File exists - should pass
        test_file.write_text("test")
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
    
    def test_post_check_list_processes_empty(self, verifier, environment):
        """Test post-check fails for empty process list."""
        step = {"action": "list_processes", "params": {}}
        
        # Empty string result
        ok, reason = verifier.post_check(step, "", environment)
        assert ok is False
        assert "empty" in reason.lower()
        
        # Empty list result
        ok, reason = verifier.post_check(step, [], environment)
        assert ok is False
        assert "empty" in reason.lower()
    
    def test_post_check_list_processes_valid(self, verifier, environment):
        """Test post-check passes for valid process list."""
        step = {"action": "list_processes", "params": {}}
        
        # String result with content
        result = "PID\tNAME\n1234\tpython.exe"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
        
        # List result with content
        result = [{"pid": 1234, "name": "python.exe"}]
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
    
    def test_post_check_system_info_valid(self, verifier, environment):
        """Test post-check validates system info result."""
        step = {"action": "get_system_info", "params": {}}
        
        # Valid result with expected keywords
        result = "OS: Windows\nCPU: Intel\nMemory: 16GB"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
        
        # Invalid result missing expected data
        result = "Some random text"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is False
        assert "missing expected data" in reason.lower()
    
    def test_post_check_open_website_success(self, verifier, environment):
        """Test post-check validates website opening."""
        step = {"action": "open_website", "params": {"site_name": "youtube"}}
        
        # Success result
        result = "✓ Opened youtube (https://www.youtube.com)"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
        
        # Failure result
        result = "Error opening website"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is False
    
    def test_post_check_search_files_valid(self, verifier, environment):
        """Test post-check validates file search results."""
        step = {"action": "search_files", "params": {"pattern": "*.py"}}
        
        # No matches found (valid)
        result = "No files found"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        
        # Matches found (valid)
        result = "Found 5 files:\ntest.py\nmain.py"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        
        # List result (valid)
        result = ["test.py", "main.py"]
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
    
    def test_post_check_delete_file_verification(self, verifier, environment, tmp_path):
        """Test post-check verifies file was deleted."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("test")
        
        step = {
            "action": "delete_file",
            "params": {"path": str(test_file)}
        }
        
        # File still exists - should fail
        result = "✓ Deleted file"
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is False
        assert "still exists" in reason.lower()
        
        # File deleted - should pass
        test_file.unlink()
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
        assert reason == ""
    
    # ========== INTEGRATION TESTS ==========
    
    def test_complete_verification_flow(self, verifier, environment, tmp_path):
        """Test complete pre-check + post-check flow."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        step = {
            "action": "read_file",
            "params": {"path": str(test_file)}
        }
        
        # Pre-check should pass
        ok, reason = verifier.pre_check(step, environment)
        assert ok is True
        
        # Simulate execution result
        result = "test content"
        
        # Post-check should pass
        ok, reason = verifier.post_check(step, result, environment)
        assert ok is True
    
    def test_error_keyword_detection(self, verifier, environment):
        """Test all error keywords are detected."""
        step = {"action": "test_action", "params": {}}
        
        error_messages = [
            "not recognized",
            "error occurred",
            "failed to execute",
            "cannot proceed",
            "denied access",
            "not found",
            "does not exist",
            "no such file",
            "invalid input",
            "unable to complete",
            "could not open",
            "can't find",
            "couldn't access",
            "permission denied",
            "access denied",
            "not available",
            "unavailable"
        ]
        
        for error_msg in error_messages:
            ok, reason = verifier.post_check(step, error_msg, environment)
            assert ok is False, f"Should detect error in: {error_msg}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
