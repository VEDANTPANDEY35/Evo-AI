"""
Unit tests for action parser.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.action_parser import ActionParser, ParsedAction


class TestActionParser:
    """Test suite for ActionParser."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.parser = ActionParser(debug=False)
    
    def test_parse_action_block_format(self):
        """Test parsing ACTION block format."""
        text = '[ACTION: tool=create_file args={"path":"test.py","content":"hello"}]'
        actions = self.parser.parse(text)
        
        assert len(actions) == 1
        assert actions[0].tool == "create_file"
        assert actions[0].args["path"] == "test.py"
        assert actions[0].args["content"] == "hello"
        assert actions[0].format_type == "action_block"
    
    def test_parse_json_code_block_format(self):
        """Test parsing JSON code block format."""
        text = '''
        ```json
        {
          "tool": "search_files",
          "args": {
            "pattern": "*.py",
            "directory": "/home/user"
          }
        }
        ```
        '''
        actions = self.parser.parse(text)
        
        assert len(actions) == 1
        assert actions[0].tool == "search_files"
        assert actions[0].args["pattern"] == "*.py"
        assert actions[0].format_type == "json"
    
    def test_parse_multiple_actions(self):
        """Test parsing multiple actions in one response."""
        text = '''
        First action:
        [ACTION: tool=create_file args={"path":"file1.txt","content":"test"}]
        
        Second action:
        [ACTION: tool=create_file args={"path":"file2.txt","content":"test2"}]
        '''
        actions = self.parser.parse(text)
        
        assert len(actions) == 2
        assert actions[0].tool == "create_file"
        assert actions[1].tool == "create_file"
    
    def test_extract_human_response(self):
        """Test extracting human-readable text."""
        text = '''
        I'll create that file for you.
        [ACTION: tool=create_file args={"path":"test.py","content":"print('hi')"}]
        The file has been created.
        '''
        actions = self.parser.parse(text)
        human_text = self.parser.extract_human_response(text, actions)
        
        assert "[ACTION:" not in human_text
        assert "I'll create that file" in human_text
        assert "The file has been created" in human_text
    
    def test_invalid_json_ignored(self):
        """Test that invalid JSON is ignored."""
        text = '[ACTION: tool=test args={invalid json}]'
        actions = self.parser.parse(text)
        
        assert len(actions) == 0
    
    def test_no_actions_in_text(self):
        """Test text with no actions."""
        text = "This is just a regular response with no actions."
        actions = self.parser.parse(text)
        
        assert len(actions) == 0
    
    def test_validate_action_format(self):
        """Test action format validation."""
        valid_text = '[ACTION: tool=test args={"key":"value"}]'
        is_valid, error = self.parser.validate_action_format(valid_text)
        assert is_valid
        
        invalid_text = '[ACTION: invalid format]'
        is_valid, error = self.parser.validate_action_format(invalid_text)
        assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
