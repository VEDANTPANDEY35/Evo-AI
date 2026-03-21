"""
Deterministic Multi-Step Execution Planner
Handles compound instructions without LLM-based planning.
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from .verifier import ExecutionVerifier


class DeterministicPlanner:
    """
    Deterministic planner for compound instructions.
    NO LLM planning. NO recursion. NO async.
    Includes strict execution verification to eliminate false positives.
    """
    
    def __init__(self, reasoner, debug: bool = False):
        self.reasoner = reasoner
        self.debug = debug
        self.verifier = ExecutionVerifier(debug=debug)
        self._capability_registry = None
        
        # Compound instruction connectors (order matters for regex)
        # More specific patterns first to avoid incorrect splits
        self.connectors = [
            ", then ",
            ", and then ",
            ", and ",
            ", after that ",
            " and then ",
            " then ",
            " after that ",
            " and ",
            ","  # Plain comma as last resort
        ]
    
    def _get_capability_registry(self):
        """Lazy load capability registry to avoid circular imports."""
        if self._capability_registry is None:
            from .capabilities import get_capability_registry
            self._capability_registry = get_capability_registry(debug=self.debug)
        return self._capability_registry
    
    def _log(self, message: str):
        if self.debug:
            print(f"[PLANNER] {message}")
    
    def is_compound(self, user_input: str) -> bool:
        """
        Detect if input is a compound instruction.
        Returns True if any connector is present.
        """
        user_lower = user_input.lower()
        
        for connector in self.connectors:
            if connector in user_lower:
                self._log(f"Compound detected: connector '{connector}' found")
                return True
        
        return False
    
    def split_commands(self, user_input: str) -> List[str]:
        """
        Split compound instruction into sub-commands.
        Splits ONLY on defined connectors.
        
        Handles:
        - Multiple connector types (and, then, after that, commas)
        - Mixed separators in single instruction
        - Extra whitespace
        - Case insensitivity
        - Preserves strict order
        - Trailing/leading connectors
        """
        # Normalize input: collapse multiple spaces, strip
        normalized = ' '.join(user_input.split())
        
        # Create regex pattern from connectors (case-insensitive)
        # Sort by length (longest first) to match more specific patterns first
        sorted_connectors = sorted(self.connectors, key=len, reverse=True)
        pattern = '|'.join(re.escape(conn) for conn in sorted_connectors)
        
        # Split on connectors
        sub_commands = re.split(pattern, normalized, flags=re.IGNORECASE)
        
        # Clean up whitespace and filter empty strings
        sub_commands = [cmd.strip() for cmd in sub_commands if cmd.strip()]
        
        # Remove leading/trailing connector words from each command
        connector_words = {'and', 'then', 'after', 'that'}
        cleaned_commands = []
        for cmd in sub_commands:
            words = cmd.split()
            # Remove leading connector words
            while words and words[0].lower() in connector_words:
                words.pop(0)
            # Remove trailing connector words
            while words and words[-1].lower() in connector_words:
                words.pop()
            if words:  # Only add if there's content left
                cleaned_commands.append(' '.join(words))
        
        # Remove duplicate consecutive commands (edge case)
        deduplicated = []
        for cmd in cleaned_commands:
            if not deduplicated or cmd.lower() != deduplicated[-1].lower():
                deduplicated.append(cmd)
        
        self._log(f"Split into {len(deduplicated)} sub-commands: {deduplicated}")
        
        return deduplicated
    
    def build_plan(self, user_input: str) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Build deterministic execution plan.
        
        Returns:
            (is_valid, plan, error_message)
            
        Plan structure:
        [
            {
                "step_number": 1,
                "original_step": "open chrome",
                "intent": "open_app",
                "actions": ["open_application"],
                "params": {"app_name": "chrome"},
                "requires_permission": ["open_app"],
                "confidence": "high"
            },
            ...
        ]
        """
        if not self.is_compound(user_input):
            self._log("Not a compound instruction")
            return False, [], None
        
        # Split into sub-commands
        sub_commands = self.split_commands(user_input)
        
        if len(sub_commands) < 2:
            self._log("Split resulted in less than 2 commands")
            return False, [], None
        
        # Build plan by analyzing each sub-command
        plan = []
        
        for i, sub_cmd in enumerate(sub_commands, 1):
            self._log(f"Analyzing step {i}: '{sub_cmd}'")
            
            # Check if this is a capability action first
            registry = self._get_capability_registry()
            capability = None
            capability_action = None
            
            # Simple capability action detection (format: "capability_name.action_name")
            if '.' in sub_cmd and not sub_cmd.startswith('http'):
                parts = sub_cmd.split('.', 1)
                if len(parts) == 2:
                    cap_name, action_name = parts
                    capability = registry.get_capability(cap_name.strip())
                    if capability and capability.validate_action(action_name.strip()):
                        capability_action = action_name.strip()
            
            if capability and capability_action:
                # Handle capability action
                step = {
                    "step_number": i,
                    "original_step": sub_cmd,
                    "intent": "capability",
                    "actions": [f"{capability.name}.{capability_action}"],
                    "params": {},
                    "requires_permission": [],
                    "confidence": "high"
                }
                self._log(f"Step {i} identified as capability action: {capability.name}.{capability_action}")
            else:
                # Reuse existing Reasoner for each sub-command
                analysis = self.reasoner.analyze_request(sub_cmd, use_llm=False, llm_client=None)
                
                # Validate analysis
                if not analysis.get("actions"):
                    error_msg = f"Step {i} ('{sub_cmd}') could not be analyzed into executable actions"
                    self._log(f"Invalid step: {error_msg}")
                    return False, [], error_msg
                
                # Check if it's a conversational query (not allowed in compound)
                if analysis.get("use_llm") or analysis.get("intent") == "conversation":
                    error_msg = f"Step {i} ('{sub_cmd}') is conversational and cannot be part of compound instruction"
                    self._log(f"Invalid step: {error_msg}")
                    return False, [], error_msg
                
                # Add to plan
                step = {
                    "step_number": i,
                    "original_step": sub_cmd,
                    "intent": analysis.get("intent"),
                    "actions": analysis.get("actions", []),
                    "params": analysis.get("params", {}),
                    "requires_permission": analysis.get("requires_permission", []),
                    "confidence": analysis.get("confidence", "unknown")
                }
            
            plan.append(step)
            self._log(f"Step {i} planned: {step['actions']}")
        
        self._log(f"Plan built successfully with {len(plan)} steps")
        return True, plan, None
    
    def format_success_summary(self, results: List[Dict[str, Any]]) -> str:
        """
        Format successful execution summary.
        
        Returns:
            ✓ Task completed successfully:
            1. Opened chrome
            2. Searched youtube
        """
        lines = ["✓ Task completed successfully:"]
        
        for result in results:
            step_num = result["step_number"]
            step_desc = result["description"]
            lines.append(f"{step_num}. {step_desc}")
        
        return "\n".join(lines)
    
    def format_failure_summary(self, results: List[Dict[str, Any]], failed_step: int, error: str) -> str:
        """
        Format failure summary.
        
        Returns:
            ⚠️ Task stopped at step X:
            1. Opened chrome
            2. Failed: Permission denied
        """
        lines = [f"⚠️ Task stopped at step {failed_step}:"]
        
        for result in results:
            step_num = result["step_number"]
            
            if result["success"]:
                step_desc = result["description"]
                lines.append(f"{step_num}. {step_desc}")
            else:
                lines.append(f"{step_num}. Failed: {error}")
        
        return "\n".join(lines)
    
    def execute_plan(self, plan: List[Dict[str, Any]], executor) -> Tuple[bool, str]:
        """
        Execute plan sequentially with immediate failure stop.
        Includes strict verification to eliminate false positives.
        
        Returns:
            (success, summary_message)
        """
        results = []
        
        # Get environment manager from executor's brain (if available)
        environment = None
        if hasattr(executor, 'tools') and hasattr(executor.tools, 'environment'):
            environment = executor.tools.environment
        else:
            # Fallback: create environment manager
            from .environment import EnvironmentManager
            environment = EnvironmentManager()
        
        for step in plan:
            step_num = step["step_number"]
            original_step = step["original_step"]
            actions = step["actions"]
            params = step["params"]
            
            self._log(f"Executing step {step_num}: {original_step}")
            
            # PRE-CHECK: Validate before execution
            verification_step = {
                "action": actions[0] if actions else "",
                "params": params
            }
            
            pre_ok, pre_reason = self.verifier.pre_check(verification_step, environment)
            if not pre_ok:
                self._log(f"Pre-check failed: {pre_reason}")
                result_entry = {
                    "step_number": step_num,
                    "original_step": original_step,
                    "success": False,
                    "description": original_step,
                    "error": f"Pre-check failed: {pre_reason}"
                }
                results.append(result_entry)
                summary = self.format_failure_summary(results, step_num, pre_reason)
                return False, summary
            
            # Execute each action in the step
            step_success = True
            step_error = None
            step_description = None
            execution_result = None
            
            for action in actions:
                try:
                    result = executor.execute_action(action, params)
                    execution_result = result
                    
                    # POST-CHECK: Verify execution result
                    post_ok, post_reason = self.verifier.post_check(verification_step, result, environment)
                    
                    if not post_ok:
                        self._log(f"Post-check failed: {post_reason}")
                        step_success = False
                        step_error = f"Verification failed: {post_reason}"
                        break
                    
                    # Verification passed - extract description
                    step_description = self._extract_description(result, action, original_step)
                    
                except Exception as e:
                    step_success = False
                    step_error = f"Execution error: {str(e)}"
                    break
            
            # Record result
            result_entry = {
                "step_number": step_num,
                "original_step": original_step,
                "success": step_success,
                "description": step_description or original_step,
                "error": step_error
            }
            results.append(result_entry)
            
            # IMMEDIATE STOP on failure
            if not step_success:
                self._log(f"Step {step_num} failed: {step_error}")
                summary = self.format_failure_summary(results, step_num, step_error)
                return False, summary
        
        # All steps succeeded
        self._log("All steps completed successfully")
        summary = self.format_success_summary(results)
        return True, summary
    
    def _extract_description(self, result: str, action: str, original_step: str) -> str:
        """
        Extract human-readable description from execution result.
        """
        # If result is already descriptive, use it
        if isinstance(result, str) and len(result) < 100:
            # Clean up common prefixes
            result = result.replace("✓ ", "").replace("✗ ", "")
            return result
        
        # Generate description from action and original step
        action_descriptions = {
            "open_application": f"Opened {original_step.replace('open ', '')}",
            "open_website": f"Opened {original_step.replace('open ', '')}",
            "search_web": f"Searched {original_step.replace('search ', '')}",
            "list_directory": "Listed directory",
            "read_file": "Read file",
            "write_file": "Wrote file",
            "create_file": "Created file",
            "take_screenshot": "Took screenshot",
            "get_system_info": "Retrieved system info",
            "list_processes": "Listed processes"
        }
        
        return action_descriptions.get(action, original_step)
