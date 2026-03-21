"""
Goal-Oriented Session Engine
Session-level orchestration above plan execution.
LLM-assisted stage suggestion with explicit approval gates.
Includes guardrails to prevent runaway orchestration.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class SessionState(Enum):
    """Session execution states."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class StageRecord:
    """Record of a completed stage."""
    stage_number: int
    stage_description: str
    plan: Any  # StructuredPlan
    result: Any  # ExecutionResult
    success: bool


@dataclass
class Session:
    """Goal-oriented session container."""
    goal: str
    state: SessionState = SessionState.IDLE
    current_stage_number: int = 0
    current_stage_description: Optional[str] = None
    current_plan: Optional[Any] = None
    completed_stages: List[StageRecord] = field(default_factory=list)
    failed_stage: Optional[int] = None
    error_message: Optional[str] = None
    max_stages: int = 10


class SessionEngine:
    """
    Session-level orchestration engine.
    Uses LLM to suggest stages, but requires explicit approval for execution.
    Includes guardrails to prevent runaway orchestration.
    """
    
    def __init__(self, brain, debug: bool = False, max_stages: int = 10):
        self.brain = brain
        self.debug = debug
        self.max_stages = max_stages
        self.session: Optional[Session] = None
    
    def _log(self, message: str):
        if self.debug:
            print(f"[SESSION] {message}")
    
    def start_session(self, goal: str) -> Session:
        """
        Start a new goal session.
        Does NOT execute anything - only initializes session.
        
        Raises:
            RuntimeError if session already active
        """
        # Guardrail: Prevent nested sessions
        if self.is_session_active():
            raise RuntimeError("Cannot start new session: session already active")
        
        self._log(f"Starting session for goal: {goal}")
        
        self.session = Session(
            goal=goal,
            state=SessionState.ACTIVE,
            max_stages=self.max_stages
        )
        
        return self.session
    
    def get_next_stage(self) -> Optional[str]:
        """
        Ask LLM to suggest next stage for current goal.
        Does NOT execute anything - only returns stage description.
        
        Returns:
            Stage description string or None if goal complete
        """
        if not self.session or self.session.state != SessionState.ACTIVE:
            return None
        
        # Guardrail: Check max stage limit
        if self.session.current_stage_number >= self.session.max_stages:
            self._log(f"Max stage limit ({self.session.max_stages}) exceeded")
            self.session.state = SessionState.FAILED
            self.session.error_message = f"Maximum stage limit ({self.session.max_stages}) exceeded"
            return None
        
        self._log("Requesting next stage from LLM")
        
        # Build context for LLM
        context = self._build_stage_context()
        
        # Ask LLM for next stage
        prompt = self._build_stage_prompt(context)
        
        # Use Brain's LLM to generate next stage
        if not self.brain.local_available:
            self._log("LLM not available")
            self.session.state = SessionState.FAILED
            self.session.error_message = "LLM not available"
            return None
        
        try:
            # Get system prompt and conversation history
            system_prompt = self.brain.memory.get_system_prompt()
            conversation = []
            
            # Generate stage suggestion
            response_stream = self.brain.llm.generate_local_with_history(
                prompt,
                system_prompt,
                conversation,
                stream=False
            )
            
            # Collect response
            stage_description = self.brain._collect_stream(response_stream)
            
            if stage_description:
                # Clean up response
                stage_description = stage_description.strip()
                
                # Check for completion indicators
                if self._is_completion_indicator(stage_description):
                    self._log("LLM indicates goal complete")
                    return None
                
                # Guardrail: Check for duplicate stage
                if self._is_duplicate_stage(stage_description):
                    self._log("Duplicate stage detected - aborting session")
                    self.session.state = SessionState.FAILED
                    self.session.error_message = "Duplicate stage suggestion detected"
                    return None
                
                self._log(f"LLM suggested stage: {stage_description}")
                return stage_description
            
            return None
            
        except Exception as e:
            self._log(f"Error getting next stage: {e}")
            self.session.state = SessionState.FAILED
            self.session.error_message = f"Error getting next stage: {str(e)}"
            return None
    
    def prepare_stage(self, stage_description: str):
        """
        Prepare a stage for execution.
        Generates plan but does NOT execute.
        """
        if not self.session or self.session.state != SessionState.ACTIVE:
            return
        
        self._log(f"Preparing stage: {stage_description}")
        
        # Increment stage number
        self.session.current_stage_number += 1
        self.session.current_stage_description = stage_description
        
        # Generate plan using Brain
        plan = self.brain.generate_plan(stage_description)
        self.session.current_plan = plan
        
        # Transition to WAITING_APPROVAL
        self.session.state = SessionState.WAITING_APPROVAL
        
        self._log(f"Stage {self.session.current_stage_number} ready for approval")
    
    def execute_current_stage(self) -> bool:
        """
        Execute current stage (after user approval).
        
        Returns:
            True if stage succeeded, False if failed
        """
        if not self.session or not self.session.current_plan:
            return False
        
        if self.session.state != SessionState.WAITING_APPROVAL:
            return False
        
        self._log(f"Executing stage {self.session.current_stage_number}")
        
        # Transition to EXECUTING
        self.session.state = SessionState.EXECUTING
        
        # Execute plan using Brain
        result = self.brain.execute_plan(self.session.current_plan)
        
        # Record stage result
        stage_record = StageRecord(
            stage_number=self.session.current_stage_number,
            stage_description=self.session.current_stage_description,
            plan=self.session.current_plan,
            result=result,
            success=result.success
        )
        
        self.session.completed_stages.append(stage_record)
        
        # Check result
        if result.success:
            self._log(f"Stage {self.session.current_stage_number} completed successfully")
            
            # Clear current stage
            self.session.current_plan = None
            self.session.current_stage_description = None
            
            # Transition to ACTIVE (ready for next stage)
            self.session.state = SessionState.ACTIVE
            
            return True
        else:
            # Guardrail: Stage failed - mark session as FAILED immediately
            self._log(f"Stage {self.session.current_stage_number} failed - marking session FAILED")
            
            self.session.state = SessionState.FAILED
            self.session.failed_stage = self.session.current_stage_number
            self.session.error_message = result.message
            
            return False
    
    def complete_session(self):
        """Mark session as completed and clear state."""
        if not self.session:
            return
        
        self._log("Session completed")
        self.session.state = SessionState.COMPLETED
        
        # Clear session state
        self._clear_session_state()
    
    def abort_session(self):
        """Abort current session and clear state."""
        if not self.session:
            return
        
        self._log("Session aborted by user")
        self.session.state = SessionState.ABORTED
        
        # Clear session state
        self._clear_session_state()
    
    def get_session_state(self) -> Optional[Session]:
        """Get current session state."""
        return self.session
    
    def is_session_active(self) -> bool:
        """Check if session is active."""
        return self.session is not None and self.session.state in (
            SessionState.ACTIVE,
            SessionState.WAITING_APPROVAL,
            SessionState.EXECUTING
        )
    
    def _clear_session_state(self):
        """Clear all session state."""
        if self.session:
            self.session.current_plan = None
            self.session.current_stage_description = None
    
    def _is_duplicate_stage(self, stage_description: str) -> bool:
        """
        Check if stage description is duplicate of already executed stage.
        Guardrail to prevent infinite loops.
        """
        if not self.session:
            return False
        
        stage_lower = stage_description.lower().strip()
        
        for completed_stage in self.session.completed_stages:
            completed_lower = completed_stage.stage_description.lower().strip()
            
            # Check for exact match or very similar
            if stage_lower == completed_lower:
                return True
            
            # Check for substring match (80% similarity)
            if len(stage_lower) > 10 and len(completed_lower) > 10:
                if stage_lower in completed_lower or completed_lower in stage_lower:
                    return True
        
        return False
    
    def _build_stage_context(self) -> str:
        """Build context string for LLM stage generation."""
        if not self.session:
            return ""
        
        lines = []
        lines.append(f"Goal: {self.session.goal}")
        lines.append(f"Completed stages: {len(self.session.completed_stages)}/{self.session.max_stages}")
        
        if self.session.completed_stages:
            lines.append("\nCompleted:")
            for stage in self.session.completed_stages:
                status = "✓" if stage.success else "✗"
                lines.append(f"  {status} Stage {stage.stage_number}: {stage.stage_description}")
        
        return "\n".join(lines)
    
    def _build_stage_prompt(self, context: str) -> str:
        """Build prompt for LLM to suggest next stage."""
        prompt = f"""You are helping break down a goal into executable stages.

{context}

What is the next single, concrete action needed to progress toward this goal?

Respond with ONLY a short, actionable command (like "open chrome" or "create file test.txt").

If the goal is already complete, respond with: GOAL_COMPLETE

Next action:"""
        
        return prompt
    
    def _is_completion_indicator(self, response: str) -> bool:
        """Check if LLM response indicates goal completion."""
        response_lower = response.lower().strip()
        
        completion_indicators = [
            "goal_complete",
            "goal complete",
            "complete",
            "done",
            "finished",
            "no more steps",
            "nothing more"
        ]
        
        return any(indicator in response_lower for indicator in completion_indicators)
