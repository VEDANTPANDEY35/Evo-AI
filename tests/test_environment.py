"""
Test suite for Environment Awareness Layer.
Tests cross-platform OS detection, path resolution, and process detection.
"""
import pytest
import platform
from pathlib import Path
from core.environment import EnvironmentManager


class TestEnvironmentManager:
    """Test EnvironmentManager functionality."""
    
    @pytest.fixture
    def env_manager(self):
        """Create EnvironmentManager instance for testing."""
        return EnvironmentManager()
    
    def test_os_detection(self, env_manager):
        """Test 1: OS detection returns correct value."""
        os_type = env_manager.detect_os()
        
        # Should return one of the three supported OS types
        assert os_type in ["windows", "linux", "macos"]
        
        # Verify it matches actual platform
        system = platform.system().lower()
        if system == "windows":
            assert os_type == "windows"
        elif system == "darwin":
            assert os_type == "macos"
        elif system == "linux":
            assert os_type == "linux"
    
    def test_username_detection(self, env_manager):
        """Test username detection."""
        username = env_manager.get_username()
        
        # Should return a non-empty string
        assert isinstance(username, str)
        assert len(username) > 0
    
    def test_home_path(self, env_manager):
        """Test home directory detection."""
        home = env_manager.get_home_path()
        
        # Should be a Path object
        assert isinstance(home, Path)
        
        # Should exist
        assert home.exists()
        
        # Should be a directory
        assert home.is_dir()
    
    def test_desktop_path_resolution(self, env_manager):
        """Test 2: Desktop path resolves correctly."""
        paths = env_manager.get_standard_paths()
        
        # Should have desktop key
        assert "desktop" in paths
        
        # Desktop should be a Path object
        assert isinstance(paths["desktop"], Path)
        
        # Desktop path should contain "Desktop" (case-insensitive check)
        assert "desktop" in str(paths["desktop"]).lower()
    
    def test_standard_paths_structure(self, env_manager):
        """Test standard paths dictionary structure."""
        paths = env_manager.get_standard_paths()
        
        # Should have all required keys
        required_keys = ["home", "desktop", "documents", "downloads"]
        for key in required_keys:
            assert key in paths
            assert isinstance(paths[key], Path)
    
    def test_natural_path_resolution_with_filename(self, env_manager, tmp_path):
        """Test 3: Natural path resolution with 'from' syntax."""
        # Create a temporary file in a known location
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")
        
        # Test direct path resolution
        resolved = env_manager.resolve_natural_path(str(test_file))
        assert resolved == test_file
    
    def test_natural_path_resolution_location_only(self, env_manager):
        """Test natural path resolution for location names."""
        # Test resolving just "desktop"
        resolved = env_manager.resolve_natural_path("desktop")
        
        if resolved:  # Only if desktop exists
            assert resolved == env_manager.standard_paths["desktop"]
        
        # Test resolving "home"
        resolved_home = env_manager.resolve_natural_path("home")
        assert resolved_home == env_manager.home_path
    
    def test_nonexistent_file_returns_none(self, env_manager):
        """Test 4: Non-existent file returns None."""
        # Try to resolve a file that definitely doesn't exist
        resolved = env_manager.resolve_natural_path("nonexistent_file_12345.xyz from desktop")
        
        # Should return None for non-existent files
        assert resolved is None
    
    def test_process_list_structure(self, env_manager):
        """Test 5: Process list returns structured list."""
        processes = env_manager.list_running_processes()
        
        # Should return a list
        assert isinstance(processes, list)
        
        # Should have at least some processes (current Python process at minimum)
        assert len(processes) > 0
        
        # Each process should have correct structure
        for proc in processes[:5]:  # Check first 5
            assert "pid" in proc
            assert "name" in proc
            assert isinstance(proc["pid"], int)
            assert isinstance(proc["name"], str)
    
    def test_process_search_by_name(self, env_manager):
        """Test finding processes by name."""
        # Python should be running (this test itself)
        python_processes = env_manager.get_process_by_name("python")
        
        # Should find at least one Python process
        assert len(python_processes) > 0
        
        # Each result should contain "python" in name (case-insensitive)
        for proc in python_processes:
            assert "python" in proc["name"].lower()
    
    def test_is_process_running(self, env_manager):
        """Test process running check."""
        # Python should be running
        assert env_manager.is_process_running("python") is True
        
        # A non-existent process should return False
        assert env_manager.is_process_running("nonexistent_process_xyz123") is False
    
    def test_path_validation(self, env_manager, tmp_path):
        """Test path existence validation."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        # Should validate existing path
        assert env_manager.validate_path_exists(str(test_file)) is True
        
        # Should return False for non-existent path
        assert env_manager.validate_path_exists(str(tmp_path / "nonexistent.txt")) is False
    
    def test_environment_info_structure(self, env_manager):
        """Test environment info summary."""
        info = env_manager.get_environment_info()
        
        # Should have all required keys
        required_keys = ["os", "username", "home", "desktop", "documents", "downloads", "platform", "python_version"]
        for key in required_keys:
            assert key in info
        
        # OS should be valid
        assert info["os"] in ["windows", "linux", "macos"]
        
        # Username should be non-empty
        assert len(info["username"]) > 0
    
    def test_cross_platform_compatibility(self, env_manager):
        """Test 6: Works on Windows, macOS, Linux."""
        # This test verifies the manager initializes without errors
        # and provides valid data regardless of platform
        
        # Should detect OS
        assert env_manager.os_type in ["windows", "linux", "macos"]
        
        # Should get username
        assert isinstance(env_manager.username, str)
        
        # Should get home path
        assert env_manager.home_path.exists()
        
        # Should get standard paths
        assert len(env_manager.standard_paths) >= 4
        
        # Should list processes
        processes = env_manager.list_running_processes()
        assert len(processes) > 0
    
    def test_error_handling_invalid_path(self, env_manager):
        """Test error handling for invalid paths."""
        # Should not raise exception, just return None
        result = env_manager.resolve_natural_path("")
        assert result is None
        
        result = env_manager.resolve_natural_path(None)
        assert result is None
    
    def test_no_exceptions_on_initialization(self):
        """Test that EnvironmentManager initializes without exceptions."""
        # Should not raise any exceptions
        try:
            manager = EnvironmentManager()
            assert manager is not None
        except Exception as e:
            pytest.fail(f"EnvironmentManager initialization raised exception: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
