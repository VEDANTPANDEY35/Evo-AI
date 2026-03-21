"""
Brain - Pure AI logic layer (no I/O, no UI).
Orchestrates reasoning, execution, LLM, and memory.
Can be reused by CLI, voice, GUI, or background services.

REFACTORED: Supports execution gating with separate plan generation and execution.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from .reasoning import Reasoner
from .executor import Executor
from .llm_client import LLMClient
from .memory import Memory
from .action_parser import ActionParser
from .planner import DeterministicPlanner
from .environment import EnvironmentManager
from .verifier import ExecutionVerifier


@dataclass
class StructuredPlan:
    """
    Pure data container for execution plan.
    No logic, no methods - just data.
    """
    steps: List[Dict[str, Any]]
    risk_level: str  # "low", "medium", "high"
    permissions_required: List[str]
    confidence: float
    is_compound: bool = False
    is_conversational: bool = False
    original_text: str = ""


@dataclass
class ExecutionResult:
    """
    Result of plan execution.
    """
    success: bool
    completed_steps: int
    total_steps: int
    message: str
    failed_step: Optional[int] = None
    error_reason: Optional[str] = None


class Brain:
    """
    Pure intelligence layer - handles ALL AI logic.
    NO input(), NO print(), NO CLI dependencies.
    
    NEW: Supports execution gating with separate plan generation and execution.
    """
    
    def __init__(
        self,
        reasoner: Reasoner,
        executor: Executor,
        llm_client: LLMClient,
        memory: Memory,
        debug: bool = False
    ):
        self.reasoner = reasoner
        self.executor = executor
        self.llm = llm_client
        self.memory = memory
        self.action_parser = ActionParser(debug=debug)
        self.planner = DeterministicPlanner(reasoner, debug=debug)
        self.environment = EnvironmentManager()
        self.verifier = ExecutionVerifier(debug=debug)
        self.debug = debug
        self.local_available = self.llm.check_local_available()
        
        # Initialize capabilities
        self._init_capabilities()
        
        # Initialize context engine
        self._init_context_engine()
    
    def _init_capabilities(self):
        """Initialize capability framework."""
        try:
            from .capabilities import initialize_capabilities
            initialize_capabilities(debug=self.debug)
            self._log("Capabilities initialized")
        except Exception as e:
            self._log(f"Error initializing capabilities: {e}")
    
    def _init_context_engine(self):
        """Initialize context awareness system."""
        try:
            from .context import ContextEngine
            self.context_engine = ContextEngine(
                environment_manager=self.environment,
                debug=self.debug
            )
            self._log("Context engine initialized")
        except Exception as e:
            self._log(f"Error initializing context engine: {e}")
            self.context_engine = None
    
    def _log(self, message: str):
        if self.debug:
            print(f"[BRAIN] {message}")
    
    def generate_plan(self, text: str) -> StructuredPlan:
        """
        Generate execution plan WITHOUT executing anything.
        
        This method:
        - Analyzes the request
        - Builds a plan structure
        - Computes risk level
        - Extracts permissions
        - Returns StructuredPlan
        
        This method DOES NOT:
        - Execute any actions
        - Call Executor
        - Call Verifier
        - Modify system state
        
        Args:
            text: User input text
            
        Returns:
            StructuredPlan with all necessary information
        """
        self._log(f"Generating plan for: {text}")
        
        # Check for compound instruction
        if self.planner.is_compound(text):
            self._log("Compound instruction detected")
            
            # Build execution plan (no execution)
            is_valid, plan_steps, error = self.planner.build_plan(text)
            
            if not is_valid:
                # Return error plan
                return StructuredPlan(
                    steps=[],
                    risk_level="low",
                    permissions_required=[],
                    confidence=0.0,
                    is_compound=True,
                    is_conversational=False,
                    original_text=text
                )
            
            # Extract permissions and compute risk
            all_permissions = []
            max_risk = "low"
            
            for step in plan_steps:
                all_permissions.extend(step.get("requires_permission", []))
                
                # Compute risk based on actions
                for action in step.get("actions", []):
                    action_risk = self._compute_action_risk(action)
                    if self._risk_priority(action_risk) > self._risk_priority(max_risk):
                        max_risk = action_risk
            
            # Build structured plan
            return StructuredPlan(
                steps=plan_steps,
                risk_level=max_risk,
                permissions_required=list(set(all_permissions)),
                confidence=1.0,  # Compound plans are deterministic
                is_compound=True,
                is_conversational=False,
                original_text=text
            )
        
        # Single-step command - analyze
        analysis = self.reasoner.analyze_request(
            text,
            use_llm=False,
            llm_client=None
        )
        
        self._log(f"Intent: {analysis['intent']} (confidence: {analysis.get('confidence', 'unknown')})")
        
        # Fast-path: Simple responses (greetings, thanks)
        if analysis["intent"] in ["greeting", "thanks"]:
            return StructuredPlan(
                steps=[],
                risk_level="low",
                permissions_required=[],
                confidence=1.0,
                is_compound=False,
                is_conversational=True,
                original_text=text
            )
        
        # Conversational queries
        if analysis.get("use_llm") or analysis["intent"] == "conversation":
            return StructuredPlan(
                steps=[],
                risk_level="low",
                permissions_required=[],
                confidence=0.8,
                is_compound=False,
                is_conversational=True,
                original_text=text
            )
        
        # Direct actions
        if analysis["actions"] and analysis.get("confidence") in ["high", "medium"]:
            # Build steps from analysis
            steps = []
            for action in analysis["actions"]:
                step = {
                    "step_number": len(steps) + 1,
                    "original_step": text,
                    "intent": analysis["intent"],
                    "actions": [action],
                    "params": analysis.get("params", {}),
                    "requires_permission": analysis.get("requires_permission", []),
                    "confidence": analysis.get("confidence", "medium")
                }
                steps.append(step)
            
            # Compute risk level
            max_risk = "low"
            for action in analysis["actions"]:
                action_risk = self._compute_action_risk(action)
                if self._risk_priority(action_risk) > self._risk_priority(max_risk):
                    max_risk = action_risk
            
            # Map confidence to float
            confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
            confidence = confidence_map.get(analysis.get("confidence", "medium"), 0.7)
            
            return StructuredPlan(
                steps=steps,
                risk_level=max_risk,
                permissions_required=analysis.get("requires_permission", []),
                confidence=confidence,
                is_compound=False,
                is_conversational=False,
                original_text=text
            )
        
        # Fallback - unknown intent
        return StructuredPlan(
            steps=[],
            risk_level="low",
            permissions_required=[],
            confidence=0.0,
            is_compound=False,
            is_conversational=True,
            original_text=text
        )
    
    def execute_plan(self, plan: StructuredPlan) -> ExecutionResult:
        """
        Execute a previously generated plan.
        
        This method:
        - Iterates through plan steps
        - Runs pre-check (Verifier)
        - Executes via Executor
        - Runs post-check (Verifier)
        - Stops immediately on failure
        
        Args:
            plan: StructuredPlan to execute
            
        Returns:
            ExecutionResult with success status and message
        """
        self._log(f"Executing plan with {len(plan.steps)} steps")
        
        # Handle conversational plans
        if plan.is_conversational:
            # Handle greetings
            if "hi" in plan.original_text.lower() or "hello" in plan.original_text.lower():
                return ExecutionResult(
                    success=True,
                    completed_steps=0,
                    total_steps=0,
                    message="Hello! How can I help you today?"
                )
            
            if "thank" in plan.original_text.lower():
                return ExecutionResult(
                    success=True,
                    completed_steps=0,
                    total_steps=0,
                    message="You're welcome! Let me know if you need anything else."
                )
            
            # LLM conversation
            if not self.local_available:
                return ExecutionResult(
                    success=False,
                    completed_steps=0,
                    total_steps=0,
                    message="⚠️  Ollama not running! Start it with: ollama serve"
                )
            
            # Generate LLM response
            response = self._generate_llm_response(plan.original_text)
            return ExecutionResult(
                success=True,
                completed_steps=0,
                total_steps=0,
                message=response
            )
        
        # Handle empty plans
        if not plan.steps:
            return ExecutionResult(
                success=False,
                completed_steps=0,
                total_steps=0,
                message="I'm not sure how to help with that."
            )
        
        # Execute steps with verification
        results = []
        completed = 0
        total = len(plan.steps)
        
        for step in plan.steps:
            step_num = step.get("step_number", completed + 1)
            actions = step.get("actions", [])
            params = step.get("params", {})
            
            for action in actions:
                # Create verification step
                verification_step = {"action": action, "params": params}
                
                # PRE-CHECK: Validate before execution
                ok, reason = self.verifier.pre_check(verification_step, self.environment)
                if not ok:
                    self._log(f"Pre-check failed at step {step_num}: {reason}")
                    return ExecutionResult(
                        success=False,
                        completed_steps=completed,
                        total_steps=total,
                        message=f"⚠️ Pre-check failed at step {step_num}:\n{reason}",
                        failed_step=step_num,
                        error_reason=reason
                    )
                
                # EXECUTE: Run the action
                self._log(f"Executing step {step_num}: {action}")
                result = self.executor.execute_action(action, params)
                
                # POST-CHECK: Verify execution
                ok, reason = self.verifier.post_check(verification_step, result, self.environment)
                if not ok:
                    self._log(f"Post-check failed at step {step_num}: {reason}")
                    return ExecutionResult(
                        success=False,
                        completed_steps=completed,
                        total_steps=total,
                        message=f"⚠️ Execution failed at step {step_num}:\n{reason}",
                        failed_step=step_num,
                        error_reason=reason
                    )
                
                # Verification passed - store result
                if result:
                    if isinstance(result, list):
                        results.append("\n".join(str(item) for item in result))
                    else:
                        results.append(str(result))
            
            completed += 1
        
        # All steps completed successfully
        if plan.is_compound:
            # Format compound result
            message = "✓ Task completed successfully:\n"
            for i, result in enumerate(results, 1):
                message += f"{i}. {result}\n"
        else:
            # Format single-step result
            if len(results) > 1:
                message = "✓ Task completed successfully:\n"
                for i, result in enumerate(results, 1):
                    message += f"{i}. {result}\n"
            else:
                message = results[0] if results else "✓ Task completed"
        
        return ExecutionResult(
            success=True,
            completed_steps=completed,
            total_steps=total,
            message=message.strip()
        )
    
    def process(self, text: str) -> str:
        """
        Legacy method for backward compatibility.
        Generates plan and executes immediately.
        
        For new code, use generate_plan() + execute_plan() separately.
        """
        self._log(f"Processing (legacy): {text}")
        
        # Store user message
        self.memory.add_message("user", text)
        
        # Generate plan
        plan = self.generate_plan(text)
        
        # Execute plan immediately
        result = self.execute_plan(plan)
        
        # Store assistant message
        self.memory.add_message("assistant", result.message)
        
        return result.message
    
    def _compute_action_risk(self, action: str) -> str:
        """
        Compute risk level for an action.
        
        Returns: "low", "medium", or "high"
        """
        # Read-only actions (low risk)
        read_only = [
            "get_system_info", "get_network_info", "get_self_info",
            "list_directory", "read_file", "search_files",
            "list_processes", "get_clipboard"
        ]
        
        # Write operations (medium risk)
        write_ops = [
            "write_file", "create_file", "set_clipboard",
            "open_application", "open_website", "search_web",
            "take_screenshot"
        ]
        
        # Destructive operations (high risk)
        destructive = [
            "delete_file", "kill_process"
        ]
        
        if action in read_only:
            return "low"
        elif action in write_ops:
            return "medium"
        elif action in destructive:
            return "high"
        else:
            return "medium"  # Default to medium for unknown actions
    
    def _risk_priority(self, risk: str) -> int:
        """Convert risk level to priority number for comparison."""
        priority = {"low": 1, "medium": 2, "high": 3}
        return priority.get(risk, 2)
    
    def _generate_llm_response(self, text: str) -> str:
        """Generate LLM response for conversational queries."""
        # Get system prompt and conversation history
        system_prompt = self.memory.get_system_prompt()
        conversation = self.memory.get_conversation_for_llm(max_messages=4)
        
        self._log("Generating LLM response...")
        
        try:
            response_stream = self.llm.generate_local_with_history(
                text,
                system_prompt,
                conversation,
                stream=True
            )
            
            # Collect full response from stream
            full_response = self._collect_stream(response_stream)
            
            if full_response:
                # Format and return response
                formatted_response = self._format_response(full_response)
                return formatted_response
            else:
                return "I encountered an issue generating a response. Please try again."
        
        except Exception as e:
            self._log(f"LLM generation error: {e}")
            return "I encountered an issue generating a response. Please try again."
    
    def _collect_stream(self, response_stream) -> Optional[str]:
        """Collect full response from stream (no printing)."""
        if not response_stream:
            return None
        
        full_response = ""
        
        try:
            # Check if it's a generator/iterator
            if hasattr(response_stream, '__iter__') and not isinstance(response_stream, str):
                for chunk in response_stream:
                    if chunk:
                        full_response += chunk
            else:
                # Not a stream, just a regular string
                full_response = response_stream
            
            return full_response
            
        except Exception as e:
            self._log(f"Stream collection error: {e}")
            return full_response if full_response else None
    
    def _format_response(self, response: str) -> str:
        """Format response for better readability."""
        import re
        
        # Remove excessive newlines
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Remove markdown bold/italic
        response = re.sub(r'\*\*([^*]+)\*\*', r'\1', response)
        response = re.sub(r'\*([^*\n]+)\*', r'\1', response)
        
        # Convert asterisk bullets to dashes
        response = re.sub(r'^\*\s+', '- ', response, flags=re.MULTILINE)
        response = re.sub(r'\n\*\s+', '\n- ', response)
        
        # Remove any remaining stray asterisks
        response = re.sub(r'\*', '', response)
        
        # Ensure code blocks are properly formatted
        response = re.sub(r'```(\w+)?\n', r'```\1\n', response)
        
        # Remove trailing whitespace
        response = response.strip()
        
        return response
