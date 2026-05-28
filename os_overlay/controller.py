"""
Overlay Controller — connects OverlayWindow to Brain.

Responsibilities:
  - Translate UI events into Brain calls (generate_plan / execute_plan)
  - Drive the UI state machine (idle → listening → thinking → approval → …)
  - Handle debugger suggestion selection (no auto-execution)
  - Thread safety: all Brain calls run in daemon threads;
    UI updates are posted back via root.after()
  - Session engine integration for goal-oriented workflows

Architecture constraint: NO AI logic here. Controller is pure glue.
"""
import threading
from typing import Optional
from enum import Enum


class ExecutionState(Enum):
    """Internal execution states (maps to UIState for the window)."""
    IDLE       = "idle"
    PLANNING   = "planning"
    READY      = "ready"
    EXECUTING  = "executing"
    COMPLETED  = "completed"
    ERROR      = "error"


class OverlayController:
    """
    Controller layer — connects OverlayWindow to Brain.
    Includes state guard to prevent race conditions.
    Includes session engine for goal-oriented workflows.
    """

    def __init__(self, window, brain):
        self.window  = window
        self.brain   = brain
        self.current_plan = None
        self.state   = ExecutionState.IDLE
        self._state_lock = threading.Lock()

        # Session engine (lazy import avoids circular dependency)
        from core.session_engine import SessionEngine
        self.session_engine = SessionEngine(brain, debug=False)

        # Bind UI events
        self.window.bind_submit(self.handle_submit)
        self.window.bind_approve(self.handle_approve)
        self.window.bind_cancel(self.handle_cancel)
        self.window.bind_escape(self.handle_escape)
        self.window.bind_close(self.handle_close)
        self.window.on_suggestion_select = self._handle_suggestion_select

    # ── State management ──────────────────────────────────────────────────────
    def _set_state(self, new_state: ExecutionState):
        """Thread-safe state transition — also drives the window's UI state."""
        with self._state_lock:
            self.state = new_state
            self.window.root.after(0, self._sync_ui_state)

    def _sync_ui_state(self):
        """Map ExecutionState → UIState and update window + buttons."""
        from overlay_window import UIState

        mapping = {
            ExecutionState.IDLE:      UIState.IDLE,
            ExecutionState.PLANNING:  UIState.THINKING,
            ExecutionState.READY:     UIState.APPROVAL,
            ExecutionState.EXECUTING: UIState.EXECUTING,
            ExecutionState.COMPLETED: UIState.SUCCESS,
            ExecutionState.ERROR:     UIState.ERROR,
        }
        self.window.set_ui_state(mapping.get(self.state, UIState.IDLE))

        # Button enable/disable
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
        else:  # COMPLETED / ERROR
            self.window.enable_input()
            self.window.approve_button.config(state="disabled")
            self.window.cancel_button.config(state="disabled")

    # ── Submit handler ────────────────────────────────────────────────────────
    def handle_submit(self):
        """Enter key — generate plan or handle session commands."""
        if self.state not in (ExecutionState.IDLE, ExecutionState.COMPLETED, ExecutionState.ERROR):
            return

        user_input = self.window.get_user_input()
        if not user_input:
            return

        user_lower = user_input.lower().strip()

        if user_lower == "continue":
            if self.session_engine.is_session_active():
                self._continue_session()
            else:
                self.window.set_status("No active session", "red")
            return

        if user_lower == "abort":
            if self.session_engine.is_session_active():
                self.session_engine.abort_session()
                self.window.set_status("Session aborted", "red")
                self._set_state(ExecutionState.IDLE)
            return

        if user_input.lower().startswith("goal:"):
            self._start_goal_session(user_input[5:].strip())
        else:
            self._generate_regular_plan(user_input)

    # ── Regular plan flow ─────────────────────────────────────────────────────
    def _generate_regular_plan(self, user_input: str):
        self._set_state(ExecutionState.PLANNING)
        threading.Thread(
            target=self._generate_plan_thread,
            args=(user_input,), daemon=True
        ).start()

    def _generate_plan_thread(self, user_input: str):
        try:
            plan = self.brain.generate_plan(user_input)
            self.window.root.after(0, self._on_plan_generated, plan)
        except Exception as e:
            self.window.root.after(0, self._on_plan_error, str(e))

    def _on_plan_generated(self, plan):
        self.current_plan = plan

        # ── Debugger path ─────────────────────────────────────────────────────
        if plan.debug_report is not None:
            dr = plan.debug_report
            suggestions = dr.suggestions or ["Search web for: " + plan.original_text]
            actions     = dr.next_actions or []
            self.window.show_debugger(dr.message, suggestions, actions)
            self._set_state(ExecutionState.READY)
            return

        # ── Conversational path ───────────────────────────────────────────────
        if plan.is_conversational:
            self._set_state(ExecutionState.READY)
            self.handle_approve()
            return

        # ── Action plan path ──────────────────────────────────────────────────
        plan_text = self._format_plan(plan)
        self.window.show_plan(plan_text)
        self._set_state(ExecutionState.READY)

    def _on_plan_error(self, error_msg: str):
        self.window.set_status(f"Error: {error_msg}", "red")
        self._set_state(ExecutionState.ERROR)

    # ── Approve / execute ─────────────────────────────────────────────────────
    def handle_approve(self):
        if self.state != ExecutionState.READY:
            return
        if not self.current_plan:
            return

        if self.session_engine.is_session_active():
            self._execute_session_stage()
        else:
            self._execute_regular_plan()

    def _execute_regular_plan(self):
        self._set_state(ExecutionState.EXECUTING)
        threading.Thread(
            target=self._execute_plan_thread,
            args=(self.current_plan,), daemon=True
        ).start()

    def _execute_plan_thread(self, plan):
        try:
            result = self.brain.execute_plan(plan)
            self.window.root.after(0, self._on_execution_complete, result)
        except Exception as e:
            self.window.root.after(0, self._on_execution_error, str(e))

    def _on_execution_complete(self, result):
        self.window.show_result(result.message, result.success)
        self.current_plan = None
        self._set_state(ExecutionState.COMPLETED)

    def _on_execution_error(self, error_msg: str):
        self.window.show_result(f"Error: {error_msg}", success=False)
        self.current_plan = None
        self._set_state(ExecutionState.ERROR)

    # ── Debugger suggestion selection ─────────────────────────────────────────
    def _handle_suggestion_select(self, idx: int, action: Optional[dict]):
        """
        User selected a debugger suggestion.
        Builds a new plan from the chosen action — NO auto-execution.
        User still has to press Execute.
        """
        if not action:
            return

        action_name = action.get("action", "")
        params      = action.get("params", {})

        if not action_name:
            return

        # Build a minimal StructuredPlan from the chosen action
        from core.brain import StructuredPlan
        step = {
            "step_number": 1,
            "original_step": action.get("label", action_name),
            "intent": action_name,
            "actions": [action_name],
            "params": params,
            "requires_permission": [],
            "confidence": "high",
        }
        plan = StructuredPlan(
            steps=[step],
            risk_level="medium",
            permissions_required=[],
            confidence=0.9,
            is_compound=False,
            is_conversational=False,
            original_text=action.get("label", action_name),
        )
        self.current_plan = plan

        # Show a clean plan card for the chosen action
        plan_text = self._format_plan(plan)
        self.window.show_plan(plan_text)
        self._set_state(ExecutionState.READY)

    # ── Cancel / Escape / Close ───────────────────────────────────────────────
    def handle_cancel(self):
        if self.state in (ExecutionState.PLANNING, ExecutionState.EXECUTING):
            return
        if self.session_engine.is_session_active():
            self.session_engine.abort_session()
        self.current_plan = None
        self.window.reset()
        self._set_state(ExecutionState.IDLE)

    def handle_escape(self):
        if self.state == ExecutionState.EXECUTING:
            return
        self.current_plan = None
        self._set_state(ExecutionState.IDLE)
        self.window.hide_overlay()

    def handle_close(self):
        if self.state == ExecutionState.EXECUTING:
            return
        self.window.root.quit()

    def toggle_overlay(self):
        if self.state == ExecutionState.EXECUTING:
            return
        root = self.window.root
        if root.state() in ("withdrawn", "iconic"):
            self.window.show_overlay()
        else:
            self.window.input_entry.focus_set()

    # ── Session engine helpers ────────────────────────────────────────────────
    def _start_goal_session(self, goal_text: str):
        if self.session_engine.is_session_active():
            self.window.set_status("Session already active — abort first", "red")
            return
        self._set_state(ExecutionState.PLANNING)
        try:
            self.session_engine.start_session(goal_text)
            threading.Thread(target=self._get_next_stage_thread, daemon=True).start()
        except RuntimeError as e:
            self.window.set_status(str(e), "red")
            self._set_state(ExecutionState.ERROR)

    def _continue_session(self):
        from core.session_engine import SessionState
        session = self.session_engine.get_session_state()
        if not session or session.state != SessionState.ACTIVE:
            self.window.set_status("Cannot continue session", "red")
            return
        self._set_state(ExecutionState.PLANNING)
        threading.Thread(target=self._get_next_stage_thread, daemon=True).start()

    def _get_next_stage_thread(self):
        try:
            stage_description = self.session_engine.get_next_stage()
            if stage_description:
                self.session_engine.prepare_stage(stage_description)
                self.window.root.after(0, self._on_stage_ready)
            else:
                self.session_engine.complete_session()
                self.window.root.after(0, self._on_session_complete)
        except Exception as e:
            self.window.root.after(0, self._on_plan_error, str(e))

    def _on_stage_ready(self):
        session = self.session_engine.get_session_state()
        if not session:
            return
        self.current_plan = session.current_plan
        plan_text = self._format_session_plan(session)
        self.window.show_plan(plan_text)
        self._set_state(ExecutionState.READY)

    def _on_session_complete(self):
        session = self.session_engine.get_session_state()
        msg = f"Goal completed\n\n{session.goal}" if session else "Session complete"
        self.window.show_result(msg, success=True)
        self._set_state(ExecutionState.COMPLETED)

    def _execute_session_stage(self):
        self._set_state(ExecutionState.EXECUTING)
        threading.Thread(target=self._execute_session_stage_thread, daemon=True).start()

    def _execute_session_stage_thread(self):
        try:
            success = self.session_engine.execute_current_stage()
            self.window.root.after(0, self._on_session_stage_complete, success)
        except Exception as e:
            self.window.root.after(0, self._on_execution_error, str(e))

    def _on_session_stage_complete(self, success: bool):
        session = self.session_engine.get_session_state()
        if not session:
            return
        if success:
            last = session.completed_stages[-1]
            self.window.show_result(
                f"Stage {last.stage_number} done\n{last.result.message}", True
            )
            self.current_plan = None
            self._set_state(ExecutionState.COMPLETED)
            self.window.set_status("Type 'continue' for next stage or 'abort' to stop", "green")
        else:
            self.window.show_result(f"Stage failed\n{session.error_message}", False)
            self.current_plan = None
            self._set_state(ExecutionState.ERROR)

    # ── Plan formatters ───────────────────────────────────────────────────────
    def _format_plan(self, plan) -> str:
        """Format StructuredPlan for the window's plan parser."""
        lines = []
        lines.append(f"Original: {plan.original_text}")
        lines.append(f"Risk Level: {plan.risk_level.upper()}")
        lines.append(f"Confidence: {plan.confidence:.0%}")
        lines.append(f"Type: {'Compound' if plan.is_compound else 'Single'}")
        if plan.is_conversational:
            lines.append("Category: Conversational")
        lines.append("")
        if plan.permissions_required:
            lines.append("Permissions Required:")
            for p in plan.permissions_required:
                lines.append(f"  - {p}")
            lines.append("")
        if plan.steps:
            lines.append(f"Steps ({len(plan.steps)}):")
            for i, step in enumerate(plan.steps, 1):
                actions = step.get("actions", [])
                lines.append(f"  {i}. {', '.join(actions)}")
                for k, v in step.get("params", {}).items():
                    lines.append(f"     - {k}: {v}")
            lines.append("")
        else:
            lines.append("No executable steps")
        return "\n".join(lines)

    def _format_session_plan(self, session) -> str:
        lines = [
            f"Goal: {session.goal}",
            f"Stage: {session.current_stage_number}",
            f"Action: {session.current_stage_description}",
            "",
        ]
        if session.current_plan:
            lines.append(self._format_plan(session.current_plan))
        return "\n".join(lines)
