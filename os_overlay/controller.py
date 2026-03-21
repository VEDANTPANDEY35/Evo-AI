"""
Overlay Controller - Connects UI to Brain.
Handles user interactions and coordinates between UI and AI core.
Includes execution state guard to prevent race conditions.
Includes session engine integration for goal-oriented workflows.
"""
import threading
from typing import Optional
from enum import Enum


class ExecutionState(Enum):
    """Execution states for overlay."""
    IDLE = "idle"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class OverlayController:
    """
    Controller layer - connects OverlayWindow to Brain.
    Handles threading and coordinates plan generation/execution.
    Includes state guard to prevent race conditions.
    Includes session engine for goal-oriented workflows.
    """
    
    def __init__(self, window, brain):
        self.window = window
        self.brain = brain
        self.current_plan = None
        self.state = ExecutionState.IDLE
        self._state_lock = threading.Lock()
        
        # Session engine (lazy import to avoid circular dependency)
        from core.session_engine import SessionEngine
        self.session_engine = SessionEngine(brain, debug=False)
        
        # Bind UI events
        self.window.bind_submit(self.handle_submit)
        self.window.bind_approve(self.handle_approve)
        self.window.bind_cancel(self.handle_cancel)
        self.window.bind_escape(self.handle_escape)
        self.window.bind_close(self.handle_close)
    
    def _set_state(self, new_state: ExecutionState):
        """Thread-safe state transition."""
        with self._state_lock:
            self.state = new_state
            self._update_ui_for_state()
    
    def _update_ui_for_state(self):
        """Update UI elements based on current state."""
        if self.state == ExecutionState.IDLE:
            self.window.enable_input()
            self.window.approve_button.config(state="disabled")
            self.window.cancel_button.config(state="disabled")
        
        elif self.state == ExecutionState.PLANNING:
            self.window.disable_input()
            self.window.approve_button.config(state="disabled")
            self.window.cancel_button.config(state="disabled")
        
        elif self.state == ExecutionState.READY:
            self.window.enable_input()
            self.window.approve_button.config(state="normal")
            self.window.cancel_button.config(state="normal")
        
        elif self.state == ExecutionState.EXECUTING:
            self.window.disable_input()
            self.window.approve_button.config(state="disabled")
            self.window.cancel_button.config(state="disabled")
        
        elif self.state in (ExecutionState.COMPLETED, ExecutionState.ERROR):
            self.window.enable_input()
            self.window.approve_button.config(state="disabled")
            self.window.cancel_button.config(state="disabled")
    
    def handle_submit(self):
        """Handle Enter key press - generate plan or start session."""
        # Guard: Only allow submit in IDLE or COMPLETED/ERROR states
        if self.state not in (ExecutionState.IDLE, ExecutionState.COMPLETED, ExecutionState.ERROR):
            return
        
        user_input = self.window.get_user_input()
        
        if not user_input:
            return
        
        # Check for session control commands
        user_lower = user_input.lower().strip()
        
        if user_lower == "continue":
            # Continue session - get next stage
            if self.session_engine.is_session_active():
                self._continue_session()
            else:
                self.window.show_plan("No active session to continue")
                self.window.set_status("No active session", "red")
            return
        
        if user_lower == "abort":
            # Abort session
            if self.session_engine.is_session_active():
                self.session_engine.abort_session()
                self.window.show_plan("Session aborted")
                self.window.set_status("Session aborted", "red")
                self._set_state(ExecutionState.IDLE)
            else:
                self.window.show_plan("No active session to abort")
                self.window.set_status("No active session", "red")
            return
        
        # Check if input is a goal (starts with "goal:")
        if user_input.lower().startswith("goal:"):
            goal_text = user_input[5:].strip()
            self._start_goal_session(goal_text)
        else:
            # Regular plan generation
            self._generate_regular_plan(user_input)
    
    def _continue_session(self):
        """Continue active session - get next stage."""
        session = self.session_engine.get_session_state()
        if not session:
            return
        
        # Guard: Only allow continue if session in ACTIVE state
        from core.session_engine import SessionState
        if session.state != SessionState.ACTIVE:
            self.window.show_plan(f"Cannot continue - session state is {session.state.value}")
            self.window.set_status("Cannot continue session", "red")
            return
        
        self._set_state(ExecutionState.PLANNING)
        self.window.set_status("Getting next stage...", "blue")
        
        # Get next stage in background
        thread = threading.Thread(
            target=self._get_next_stage_thread,
            daemon=True
        )
        thread.start()
    
    def _start_goal_session(self, goal_text: str):
        """Start a goal-oriented session."""
        # Guard: Prevent starting session if one already active
        if self.session_engine.is_session_active():
            self.window.show_plan("ERROR: Session already active. Abort current session first.")
            self.window.set_status("Cannot start session - one already active", "red")
            return
        
        self._set_state(ExecutionState.PLANNING)
        self.window.set_status("Starting goal session...", "blue")
        
        try:
            # Start session
            self.session_engine.start_session(goal_text)
            
            # Get first stage in background
            thread = threading.Thread(
                target=self._get_next_stage_thread,
                daemon=True
            )
            thread.start()
        except RuntimeError as e:
            # Session engine prevented nested session
            self.window.show_plan(f"ERROR: {str(e)}")
            self.window.set_status("Cannot start session", "red")
            self._set_state(ExecutionState.ERROR)
    
    def _get_next_stage_thread(self):
        """Background thread to get next stage from LLM."""
        try:
            stage_description = self.session_engine.get_next_stage()
            
            if stage_description:
                # Prepare stage
                self.session_engine.prepare_stage(stage_description)
                
                # Update UI in main thread
                self.window.root.after(0, self._on_stage_ready)
            else:
                # No more stages - complete session
                self.session_engine.complete_session()
                self.window.root.after(0, self._on_session_complete)
                
        except Exception as e:
            self.window.root.after(0, self._on_plan_error, str(e))
    
    def _on_stage_ready(self):
        """Handle stage ready (main thread)."""
        session = self.session_engine.get_session_state()
        if not session:
            return
        
        self.current_plan = session.current_plan
        
        # Format plan for display
        plan_text = self._format_session_plan(session)
        
        # Show plan in UI
        self.window.show_plan(plan_text)
        
        # Update status
        self.window.set_status(f"Session Stage {session.current_stage_number} ready - approve to execute", "orange")
        
        # Transition to READY
        self._set_state(ExecutionState.READY)
    
    def _on_session_complete(self):
        """Handle session completion (main thread)."""
        session = self.session_engine.get_session_state()
        if not session:
            return
        
        # Show completion message
        message = f"✓ Goal session completed!\n\nGoal: {session.goal}\nCompleted stages: {len(session.completed_stages)}"
        self.window.show_plan(message)
        self.window.set_status("Session completed", "green")
        
        # Transition to COMPLETED
        self._set_state(ExecutionState.COMPLETED)
    
    def _generate_regular_plan(self, user_input: str):
        """Generate regular plan (non-session)."""
        # Transition to PLANNING
        self._set_state(ExecutionState.PLANNING)
        self.window.set_status("Analyzing request...", "blue")
        
        # Generate plan in background thread
        thread = threading.Thread(
            target=self._generate_plan_thread,
            args=(user_input,),
            daemon=True
        )
        thread.start()
    
    def _generate_plan_thread(self, user_input: str):
        """Background thread for plan generation."""
        try:
            # Call Brain to generate plan (NO EXECUTION)
            plan = self.brain.generate_plan(user_input)
            
            # Update UI in main thread
            self.window.root.after(0, self._on_plan_generated, plan)
            
        except Exception as e:
            # Handle errors
            self.window.root.after(0, self._on_plan_error, str(e))
    
    def _on_plan_generated(self, plan):
        """Handle plan generation completion (main thread)."""
        self.current_plan = plan
        
        # Format plan for display
        plan_text = self._format_plan(plan)
        
        # Show plan in UI
        self.window.show_plan(plan_text)
        
        # Update status
        if plan.is_conversational:
            self.window.set_status("Conversational query - no confirmation needed", "green")
            # Transition to READY then auto-execute conversational queries
            self._set_state(ExecutionState.READY)
            self.handle_approve()
        else:
            self.window.set_status("Plan ready - approve to execute", "orange")
            # Transition to READY
            self._set_state(ExecutionState.READY)
    
    def _format_session_plan(self, session) -> str:
        """Format session stage plan for display."""
        lines = []
        
        lines.append("="*50)
        lines.append("SESSION MODE")
        lines.append("="*50)
        lines.append("")
        
        lines.append(f"Goal: {session.goal}")
        lines.append(f"Stage: {session.current_stage_number}")
        lines.append(f"Action: {session.current_stage_description}")
        lines.append("")
        
        if session.completed_stages:
            lines.append(f"Completed stages: {len(session.completed_stages)}")
            for stage in session.completed_stages[-3:]:  # Show last 3
                status = "✓" if stage.success else "✗"
                lines.append(f"  {status} {stage.stage_description}")
            lines.append("")
        
        # Show current plan details
        if session.current_plan:
            plan = session.current_plan
            lines.append(f"Risk Level: {plan.risk_level.upper()}")
            lines.append(f"Confidence: {plan.confidence:.0%}")
            
            if plan.steps:
                lines.append(f"\nSteps ({len(plan.steps)}):")
                for i, step in enumerate(plan.steps, 1):
                    actions = step.get("actions", [])
                    lines.append(f"  {i}. {', '.join(actions)}")
        
        lines.append("")
        lines.append("="*50)
        
        return "\n".join(lines)
    
    def _on_plan_error(self, error_msg: str):
        """Handle plan generation error (main thread)."""
        self.window.show_plan(f"ERROR: {error_msg}")
        self.window.set_status("Error generating plan", "red")
        # Transition to ERROR
        self._set_state(ExecutionState.ERROR)
    
    def handle_approve(self):
        """Handle Approve button click - execute plan."""
        # Guard: Only allow approve in READY state
        if self.state != ExecutionState.READY:
            return
        
        if not self.current_plan:
            return
        
        # Check if in session mode
        if self.session_engine.is_session_active():
            self._execute_session_stage()
        else:
            self._execute_regular_plan()
    
    def _execute_session_stage(self):
        """Execute current session stage."""
        # Transition to EXECUTING
        self._set_state(ExecutionState.EXECUTING)
        self.window.set_status("Executing stage...", "blue")
        
        # Execute in background thread
        thread = threading.Thread(
            target=self._execute_session_stage_thread,
            daemon=True
        )
        thread.start()
    
    def _execute_session_stage_thread(self):
        """Background thread for session stage execution."""
        try:
            success = self.session_engine.execute_current_stage()
            
            # Update UI in main thread
            self.window.root.after(0, self._on_session_stage_complete, success)
            
        except Exception as e:
            self.window.root.after(0, self._on_execution_error, str(e))
    
    def _on_session_stage_complete(self, success: bool):
        """Handle session stage completion (main thread)."""
        session = self.session_engine.get_session_state()
        if not session:
            return
        
        if success:
            # Show stage result
            last_stage = session.completed_stages[-1]
            result_text = f"✓ Stage {last_stage.stage_number} completed: {last_stage.stage_description}\n\n{last_stage.result.message}"
            self.window.show_result(result_text, True)
            
            # Clear current plan
            self.current_plan = None
            
            # Transition to COMPLETED (will allow getting next stage)
            self._set_state(ExecutionState.COMPLETED)
            
            # Update status to show session is active
            self.window.set_status(f"Session active - Type 'continue' for next stage or 'abort' to stop", "green")
        else:
            # Stage failed - show error and reset session reference
            self.window.show_result(f"✗ Stage failed:\n{session.error_message}", False)
            self.current_plan = None
            self._set_state(ExecutionState.ERROR)
            
            # Session is now FAILED - will be cleaned up on next action
    
    def _execute_regular_plan(self):
        """Execute regular plan (non-session)."""
        # Transition to EXECUTING
        self._set_state(ExecutionState.EXECUTING)
        self.window.set_status("Executing...", "blue")
        
        # Execute plan in background thread
        thread = threading.Thread(
            target=self._execute_plan_thread,
            args=(self.current_plan,),
            daemon=True
        )
        thread.start()
    
    def _execute_plan_thread(self, plan):
        """Background thread for plan execution."""
        try:
            # Call Brain to execute plan
            result = self.brain.execute_plan(plan)
            
            # Update UI in main thread
            self.window.root.after(0, self._on_execution_complete, result)
            
        except Exception as e:
            # Handle errors
            self.window.root.after(0, self._on_execution_error, str(e))
    
    def _on_execution_complete(self, result):
        """Handle execution completion (main thread)."""
        # Show result in UI
        self.window.show_result(result.message, result.success)
        
        # Clear current plan
        self.current_plan = None
        
        # Transition to COMPLETED
        self._set_state(ExecutionState.COMPLETED)
    
    def _on_execution_error(self, error_msg: str):
        """Handle execution error (main thread)."""
        self.window.show_result(f"ERROR: {error_msg}", success=False)
        self.current_plan = None
        # Transition to ERROR
        self._set_state(ExecutionState.ERROR)
    
    def handle_cancel(self):
        """Handle Cancel button click - reset UI or abort session."""
        # Guard: Don't allow cancel during PLANNING or EXECUTING
        if self.state in (ExecutionState.PLANNING, ExecutionState.EXECUTING):
            return
        
        # Check if in session mode
        if self.session_engine.is_session_active():
            # Abort session
            self.session_engine.abort_session()
            self.window.show_plan("Session aborted by user")
            self.window.set_status("Session aborted", "red")
        
        self.current_plan = None
        self.window.reset()
        # Transition to IDLE
        self._set_state(ExecutionState.IDLE)
    
    def handle_escape(self):
        """Handle Escape key - hide overlay."""
        # Guard: Don't allow hide during EXECUTING
        if self.state == ExecutionState.EXECUTING:
            return
        
        # Clear state and hide
        self.current_plan = None
        self._set_state(ExecutionState.IDLE)
        self.window.hide_overlay()
    
    def handle_close(self):
        """Handle window close button."""
        # Guard: Block close during EXECUTING
        if self.state == ExecutionState.EXECUTING:
            return
        
        # Clean shutdown
        self.window.root.quit()
    
    def toggle_overlay(self):
        """Toggle overlay visibility and focus."""
        # Guard: Don't allow toggle during EXECUTING
        if self.state == ExecutionState.EXECUTING:
            return
        
        root = self.window.root
        
        # Check window state
        if root.state() == 'withdrawn':
            # Hidden - show it
            self.window.show_overlay()
        elif root.state() == 'iconic':
            # Minimized - restore and focus
            self.window.show_overlay()
        else:
            # Visible - just focus input
            self.window.input_entry.focus_set()
    
    def _format_plan(self, plan) -> str:
        """Format StructuredPlan for display."""
        lines = []
        
        lines.append("="*50)
        lines.append("EXECUTION PLAN")
        lines.append("="*50)
        lines.append("")
        
        # Basic info
        lines.append(f"Original: {plan.original_text}")
        lines.append(f"Risk Level: {plan.risk_level.upper()}")
        lines.append(f"Confidence: {plan.confidence:.0%}")
        lines.append(f"Type: {'Compound' if plan.is_compound else 'Single'}")
        
        if plan.is_conversational:
            lines.append("Category: Conversational (no confirmation needed)")
        
        lines.append("")
        
        # Permissions
        if plan.permissions_required:
            lines.append("Permissions Required:")
            for perm in plan.permissions_required:
                lines.append(f"  - {perm}")
            lines.append("")
        
        # Steps
        if plan.steps:
            lines.append(f"Steps ({len(plan.steps)}):")
            for i, step in enumerate(plan.steps, 1):
                actions = step.get("actions", [])
                lines.append(f"  {i}. {', '.join(actions)}")
                
                # Show params if present
                params = step.get("params", {})
                if params:
                    for key, value in params.items():
                        lines.append(f"     - {key}: {value}")
            lines.append("")
        else:
            lines.append("No executable steps (conversational query)")
            lines.append("")
        
        lines.append("="*50)
        
        return "\n".join(lines)
