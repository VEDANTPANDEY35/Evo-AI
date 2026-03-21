"""
Unit tests for safety validator.
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.safety_validator import SafetyValidator


class TestSafetyValidator:
    """Test suite for SafetyValidator."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = SafetyValidator(debug=False)
        self.temp_dir = tempfile.mkdtemp()
    
    def test_validate_safe_read_path(self):
        """Test validation of safe read path."""
        # Create a test file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test")
        
        is_valid, error = self.validator.validate_path(str(test_file), "read")
        assert is_valid
        assert error == ""
    
    def test_validate_nonexistent_read_path(self):
        """Test validation of non-existent file for reading."""
        fake_path = Path(self.temp_dir) / "nonexistent.txt"
        is_valid, error = self.validator.validate_path(str(fake_path), "read")
        
        assert not is_valid
        assert "does not exist" in error
    
    def test_validate_protected_directory_write(self):
        """Test that writing to protected directories is blocked."""
        if self.validator.platform == "Windows":
            protected_path = "C:\\Windows\\test.txt"
        else:
            protected_path = "/etc/test.txt"
        
        is_valid, error = self.validator.validate_path(protected_path, "write")
        assert not is_valid
        assert "protected directory" in error.lower()
    
    def test_validate_dangerous_command(self):
        """Test detection of dangerous commands."""
        dangerous_commands = [
            "rm -rf /",
            "del /S /Q C:\\",
            "format C:",
            "dd if=/dev/zero of=/dev/sda"
        ]
        
        for cmd in dangerous_commands:
            is_safe, error = self.validator.validate_command(cmd)
            assert not is_safe, f"Command should be blocked: {cmd}"
    
    def test_validate_safe_command(self):
        """Test validation of safe commands."""
        safe_commands = [
            "echo hello",
            "ls -la",
            "dir",
            "python --version"
        ]
        
        for cmd in safe_commands:
            is_safe, error = self.validator.validate_command(cmd)
            assert is_safe, f"Command should be allowed: {cmd}"
    
    def test_sanitize_query(self):
        """Test query sanitization."""
        query = "Find files in C:\\Users\\test\\Documents with API key abc123def456ghi789"
        sanitized = self.validator.sanitize_query(query)
        
        assert "C:\\" not in sanitized
        assert "abc123def456ghi789" not in sanitized
    
    def test_validate_critical_process(self):
        """Test that critical processes cannot be killed."""
        critical_processes = ["System", "csrss.exe", "systemd", "init"]
        
        for proc in critical_processes:
            is_valid, error = self.validator.validate_process_name(proc)
            assert not is_valid
            assert "critical" in error.lower()
    
    def test_validate_integer_range(self):
        """Test integer range validation."""
        is_valid, error = self.validator.validate_integer_range(50, min_val=0, max_val=100)
        assert is_valid
        
        is_valid, error = self.validator.validate_integer_range(150, min_val=0, max_val=100)
        assert not is_valid
    
    def test_validate_url(self):
        """Test URL validation."""
        valid_urls = [
            "https://google.com",
            "http://example.org"
        ]
        
        for url in valid_urls:
            is_valid, error = self.validator.validate_url(url)
            assert is_valid
        
        invalid_urls = [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,<script>alert(1)</script>"
        ]
        
        for url in invalid_urls:
            is_valid, error = self.validator.validate_url(url)
            assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
