"""
Unit tests for DeterministicPlanner - Multi-step instruction parsing.
Tests compound splitting, order preservation, and edge cases.
"""
import pytest
from core.planner import DeterministicPlanner
from core.reasoning import Reasoner


class TestPlannerSplitting:
    """Test compound instruction splitting logic."""
    
    @pytest.fixture
    def planner(self):
        """Create planner instance for testing."""
        reasoner = Reasoner(debug=False)
        return DeterministicPlanner(reasoner, debug=False)
    
    def test_simple_and_connector(self, planner):
        """Test splitting with 'and' connector."""
        result = planner.split_commands("open chrome and search youtube")
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_simple_then_connector(self, planner):
        """Test splitting with 'then' connector."""
        result = planner.split_commands("open notepad then create test.txt")
        assert len(result) == 2
        assert result[0] == "open notepad"
        assert result[1] == "create test.txt"
    
    def test_comma_then_connector(self, planner):
        """Test splitting with ', then' connector."""
        result = planner.split_commands("open chrome, then search youtube")
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_comma_and_connector(self, planner):
        """Test splitting with ', and' connector."""
        result = planner.split_commands("open chrome, and search youtube")
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_after_that_connector(self, planner):
        """Test splitting with 'after that' connector."""
        result = planner.split_commands("open notepad after that create file")
        assert len(result) == 2
        assert result[0] == "open notepad"
        assert result[1] == "create file"
    
    def test_and_then_connector(self, planner):
        """Test splitting with 'and then' connector."""
        result = planner.split_commands("open chrome and then search youtube")
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_plain_comma_connector(self, planner):
        """Test splitting with plain comma."""
        result = planner.split_commands("open chrome, search youtube, close chrome")
        assert len(result) == 3
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
        assert result[2] == "close chrome"
    
    def test_three_steps(self, planner):
        """Test splitting three-step instruction."""
        result = planner.split_commands("open chrome and search youtube then close chrome")
        assert len(result) == 3
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
        assert result[2] == "close chrome"
    
    def test_order_preservation(self, planner):
        """Test that step order is preserved."""
        result = planner.split_commands("step1 then step2 and step3")
        assert len(result) == 3
        assert result[0] == "step1"
        assert result[1] == "step2"
        assert result[2] == "step3"
    
    def test_case_insensitivity(self, planner):
        """Test case-insensitive splitting."""
        result1 = planner.split_commands("open chrome AND search youtube")
        result2 = planner.split_commands("open chrome and search youtube")
        result3 = planner.split_commands("open chrome AnD search youtube")
        
        assert result1 == result2 == result3
        assert len(result1) == 2
    
    def test_extra_whitespace(self, planner):
        """Test handling of extra whitespace."""
        result = planner.split_commands("open chrome   and    search youtube")
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_mixed_separators(self, planner):
        """Test mixed separator types in one instruction."""
        result = planner.split_commands("open chrome, then search youtube and close chrome")
        assert len(result) == 3
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
        assert result[2] == "close chrome"
    
    def test_realistic_file_explorer_workflow(self, planner):
        """Test realistic Windows workflow: file explorer."""
        result = planner.split_commands("open file explorer and go to downloads and open report.pdf")
        assert len(result) == 3
        assert result[0] == "open file explorer"
        assert result[1] == "go to downloads"
        assert result[2] == "open report.pdf"
    
    def test_realistic_notepad_workflow(self, planner):
        """Test realistic Windows workflow: notepad."""
        result = planner.split_commands("open notepad then create test.txt in documents")
        assert len(result) == 2
        assert result[0] == "open notepad"
        assert result[1] == "create test.txt in documents"
    
    def test_realistic_browser_workflow(self, planner):
        """Test realistic Windows workflow: browser."""
        result = planner.split_commands("open chrome, then search youtube, then close chrome")
        assert len(result) == 3
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
        assert result[2] == "close chrome"
    
    def test_realistic_settings_workflow(self, planner):
        """Test realistic Windows workflow: settings."""
        result = planner.split_commands("open settings and show system info")
        assert len(result) == 2
        assert result[0] == "open settings"
        assert result[1] == "show system info"
    
    def test_realistic_explorer_find_workflow(self, planner):
        """Test realistic Windows workflow: find and open."""
        result = planner.split_commands("open explorer, find report.pdf from desktop, then open it")
        assert len(result) == 3
        assert result[0] == "open explorer"
        assert result[1] == "find report.pdf from desktop"
        assert result[2] == "open it"
    
    def test_no_duplicates(self, planner):
        """Test that duplicate consecutive commands are removed."""
        result = planner.split_commands("open chrome and open chrome")
        # Should deduplicate consecutive identical commands
        assert len(result) == 1
        assert result[0] == "open chrome"
    
    def test_single_command_not_compound(self, planner):
        """Test that single command is not detected as compound."""
        assert not planner.is_compound("open chrome")
        assert not planner.is_compound("system info")
        assert not planner.is_compound("list files")
    
    def test_compound_detection(self, planner):
        """Test compound instruction detection."""
        assert planner.is_compound("open chrome and search youtube")
        assert planner.is_compound("open chrome then search youtube")
        assert planner.is_compound("open chrome, search youtube")
        assert planner.is_compound("open chrome after that search youtube")
    
    def test_empty_input(self, planner):
        """Test handling of empty input."""
        result = planner.split_commands("")
        assert len(result) == 0
    
    def test_whitespace_only_input(self, planner):
        """Test handling of whitespace-only input."""
        result = planner.split_commands("   ")
        assert len(result) == 0


class TestPlannerBuildPlan:
    """Test plan building logic."""
    
    @pytest.fixture
    def planner(self):
        """Create planner instance for testing."""
        reasoner = Reasoner(debug=False)
        return DeterministicPlanner(reasoner, debug=False)
    
    def test_build_plan_simple_compound(self, planner):
        """Test building plan for simple compound instruction."""
        is_valid, plan, error = planner.build_plan("open chrome and search youtube")
        
        assert is_valid is True
        assert error is None
        assert len(plan) == 2
        
        # Check first step
        assert plan[0]["step_number"] == 1
        assert plan[0]["original_step"] == "open chrome"
        assert "open_application" in plan[0]["actions"]
        
        # Check second step
        assert plan[1]["step_number"] == 2
        assert plan[1]["original_step"] == "search youtube"
    
    def test_build_plan_three_steps(self, planner):
        """Test building plan for three-step instruction."""
        is_valid, plan, error = planner.build_plan("open chrome, search youtube, close chrome")
        
        assert is_valid is True
        assert error is None
        assert len(plan) == 3
        
        # Verify step numbers are sequential
        assert plan[0]["step_number"] == 1
        assert plan[1]["step_number"] == 2
        assert plan[2]["step_number"] == 3
    
    def test_build_plan_not_compound(self, planner):
        """Test that single command returns invalid."""
        is_valid, plan, error = planner.build_plan("open chrome")
        
        assert is_valid is False
        assert len(plan) == 0
        assert error is None
    
    def test_build_plan_preserves_order(self, planner):
        """Test that plan preserves step order."""
        is_valid, plan, error = planner.build_plan("list files then open chrome then system info")
        
        assert is_valid is True
        assert len(plan) == 3
        
        # Verify order
        assert "list" in plan[0]["original_step"].lower()
        assert "chrome" in plan[1]["original_step"].lower()
        assert "system" in plan[2]["original_step"].lower()
    
    def test_build_plan_step_structure(self, planner):
        """Test that each step has required structure."""
        is_valid, plan, error = planner.build_plan("open chrome and system info")
        
        assert is_valid is True
        
        for step in plan:
            # Check required fields
            assert "step_number" in step
            assert "original_step" in step
            assert "intent" in step
            assert "actions" in step
            assert "params" in step
            assert "requires_permission" in step
            assert "confidence" in step
            
            # Check types
            assert isinstance(step["step_number"], int)
            assert isinstance(step["original_step"], str)
            assert isinstance(step["actions"], list)
            assert isinstance(step["params"], dict)
            assert isinstance(step["requires_permission"], list)


class TestPlannerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def planner(self):
        """Create planner instance for testing."""
        reasoner = Reasoner(debug=False)
        return DeterministicPlanner(reasoner, debug=False)
    
    def test_trailing_connector(self, planner):
        """Test handling of trailing connector."""
        result = planner.split_commands("open chrome and ")
        # Should handle gracefully - empty strings filtered out
        assert len(result) == 1
        assert result[0] == "open chrome"
    
    def test_leading_connector(self, planner):
        """Test handling of leading connector."""
        result = planner.split_commands("and open chrome")
        # Should handle gracefully
        assert len(result) == 1
        assert result[0] == "open chrome"
    
    def test_multiple_consecutive_connectors(self, planner):
        """Test handling of multiple consecutive connectors."""
        result = planner.split_commands("open chrome and then search youtube")
        # Should handle as single split
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_connector_in_command_name(self, planner):
        """Test that connector words within commands don't cause splits."""
        # "command" contains "and" but shouldn't split
        result = planner.split_commands("run command then open chrome")
        assert len(result) == 2
        assert result[0] == "run command"
        assert result[1] == "open chrome"
    
    def test_very_long_compound(self, planner):
        """Test handling of very long compound instruction."""
        long_instruction = " and ".join([f"step{i}" for i in range(1, 11)])
        result = planner.split_commands(long_instruction)
        
        assert len(result) == 10
        for i, step in enumerate(result, 1):
            assert step == f"step{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
