"""
Overlay Window — Modern AI-first command interface.

Design language:
  - Centered floating command bar, dark background (#0F1115)
  - Soft violet/indigo accent (#7C6AF7)
  - Clean sans-serif typography, high readability
  - Interaction dots: idle → listening → thinking → ready
  - Explicit UI state machine: idle/listening/thinking/approval/executing/success/debugger/error
  - Keyboard-first: Enter submit, arrows navigate suggestions, Escape close
  - Smooth fade-in/fade-out via alpha transitions
  - No blocking operations on UI thread

Migration note:
  All geometry, color, and animation constants are isolated so a future
  PySide6 port only needs to replace the Tkinter widget calls.
"""
import tkinter as tk
import math
import time
from typing import List, Optional, Callable

# ── Design tokens ────────────────────────────────────────────────────────────
BG          = "#0F1115"
BG_CARD     = "#161920"
BG_INPUT    = "#1C2028"
ACCENT      = "#7C6AF7"          # soft violet
ACCENT_DIM  = "#4A4480"
TEXT_PRI    = "#E8E8F0"
TEXT_SEC    = "#7A7A9A"
TEXT_HINT   = "#3A3A5A"
SUCCESS     = "#4ADE80"
ERROR_COL   = "#F87171"
WARN        = "#FBBF24"

FONT_MONO   = ("Consolas", 10)
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_TITLE  = ("Segoe UI", 11, "bold")

WIN_W       = 560
WIN_H_MIN   = 72          # collapsed (input only)
WIN_H_CARD  = 320         # expanded (plan card)
WIN_H_DBG   = 280         # debugger suggestions
CORNER_R    = 12
FADE_STEPS  = 12
FADE_MS     = 18           # ms per fade step  (~216ms total)
DOT_TICK_MS = 60           # animation frame rate


# ── UI State enum ─────────────────────────────────────────────────────────────
class UIState:
    IDLE       = "idle"
    LISTENING  = "listening"
    THINKING   = "thinking"
    APPROVAL   = "approval"
    EXECUTING  = "executing"
    SUCCESS    = "success"
    DEBUGGER   = "debugger"
    ERROR      = "error"


# ── Interaction Dots ──────────────────────────────────────────────────────────
class InteractionDots:
    """
    Three-dot animation system inspired by Napkin AI.
    States: idle (breathing) → listening (pulse out) → thinking (orbit) → ready (stabilise)
    Runs entirely on the Tkinter canvas — no threads, no blocking.
    """
    N_DOTS   = 3
    R_DOT    = 4            # dot radius px
    R_ORBIT  = 14           # orbit radius px
    SPACING  = 22           # dot spacing in idle/listening

    def __init__(self, canvas: tk.Canvas, cx: int, cy: int):
        self.canvas = canvas
        self.cx = cx
        self.cy = cy
        self._ids: List[int] = []
        self._tick = 0
        self._state = UIState.IDLE
        self._after_id: Optional[str] = None
        self._draw_initial()

    def _draw_initial(self):
        for _ in range(self.N_DOTS):
            oid = self.canvas.create_oval(0, 0, 0, 0, fill=ACCENT_DIM, outline="")
            self._ids.append(oid)

    def set_state(self, state: str):
        self._state = state
        self._tick = 0

    def _dot_positions(self):
        """Return (x, y, r, alpha_0_1) for each dot given current state/tick."""
        t = self._tick * 0.06
        positions = []

        if self._state == UIState.IDLE:
            # Gentle breathing: all three dots in a row, size pulses slowly
            breath = 0.5 + 0.5 * math.sin(t * 0.8)
            for i in range(self.N_DOTS):
                x = self.cx + (i - 1) * self.SPACING
                y = self.cy
                r = self.R_DOT * (0.7 + 0.3 * breath)
                positions.append((x, y, r, 0.35 + 0.2 * breath))

        elif self._state == UIState.LISTENING:
            # Dots pulse outward in sequence
            for i in range(self.N_DOTS):
                phase = t - i * 0.6
                pulse = max(0.0, math.sin(phase)) ** 2
                x = self.cx + (i - 1) * self.SPACING
                y = self.cy - pulse * 5
                r = self.R_DOT * (1.0 + 0.5 * pulse)
                positions.append((x, y, r, 0.5 + 0.5 * pulse))

        elif self._state == UIState.THINKING:
            # Dots orbit a common centre at different phases
            for i in range(self.N_DOTS):
                angle = t + i * (2 * math.pi / self.N_DOTS)
                x = self.cx + self.R_ORBIT * math.cos(angle)
                y = self.cy + self.R_ORBIT * 0.45 * math.sin(angle)
                r = self.R_DOT
                positions.append((x, y, r, 0.6 + 0.4 * math.sin(angle)))

        else:
            # Stabilised row (approval / executing / success / error)
            for i in range(self.N_DOTS):
                x = self.cx + (i - 1) * self.SPACING
                y = self.cy
                positions.append((x, y, self.R_DOT, 1.0))

        return positions

    def _color_for_state(self) -> str:
        return {
            UIState.IDLE:      ACCENT_DIM,
            UIState.LISTENING: ACCENT,
            UIState.THINKING:  ACCENT,
            UIState.APPROVAL:  ACCENT,
            UIState.EXECUTING: WARN,
            UIState.SUCCESS:   SUCCESS,
            UIState.DEBUGGER:  WARN,
            UIState.ERROR:     ERROR_COL,
        }.get(self._state, ACCENT_DIM)

    def tick(self):
        self._tick += 1
        color = self._color_for_state()
        positions = self._dot_positions()
        for oid, (x, y, r, _alpha) in zip(self._ids, positions):
            self.canvas.coords(oid, x - r, y - r, x + r, y + r)
            self.canvas.itemconfig(oid, fill=color)

    def start(self, root: tk.Misc):
        self._schedule(root)

    def _schedule(self, root: tk.Misc):
        self._after_id = root.after(DOT_TICK_MS, lambda: self._frame(root))

    def _frame(self, root: tk.Misc):
        self.tick()
        self._schedule(root)

    def stop(self):
        if self._after_id:
            try:
                self.canvas.after_cancel(self._after_id)
            except Exception:
                pass


# ── Main overlay window ───────────────────────────────────────────────────────
class OverlayWindow:
    """
    Modern AI-first command interface.

    Public API (unchanged from original — controller compatibility preserved):
        get_user_input()        → str
        clear_input()
        set_status(text, color)
        show_plan(plan_text)
        show_result(text, success)
        show_debugger(message, suggestions)
        reset()
        enable_input() / disable_input()
        bind_submit(cb) / bind_approve(cb) / bind_cancel(cb)
        bind_escape(cb) / bind_close(cb)
        show_overlay() / hide_overlay()

    New public API:
        set_ui_state(UIState.*)   — drives dots + microcopy
        get_selected_suggestion() → int | None
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._ui_state = UIState.IDLE
        self._suggestions: List[str] = []
        self._suggestion_actions: List[dict] = []
        self._selected_idx: int = 0
        self._fade_alpha: float = 0.0
        self._fade_target: float = 0.0
        self._fade_after: Optional[str] = None

        # Callbacks
        self.on_close: Optional[Callable] = None
        self.on_submit: Optional[Callable] = None
        self.on_approve: Optional[Callable] = None
        self.on_cancel: Optional[Callable] = None
        self.on_escape: Optional[Callable] = None
        self.on_suggestion_select: Optional[Callable] = None

        self._build_window()
        self._build_ui()
        self._dots.start(self.root)

    # ── Window chrome ─────────────────────────────────────────────────────────
    def _build_window(self):
        self.root.title("Evo-AI")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # borderless
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)       # start invisible for fade-in
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_size(WIN_W, WIN_H_MIN)

    def _set_size(self, w: int, h: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - w) // 2
        y  = int(sh * 0.32)          # slightly above centre — Spotlight feel
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        """Build all layers. Order matters for stacking."""
        # Root canvas for rounded background
        self._bg_canvas = tk.Canvas(
            self.root, bg=BG, highlightthickness=0,
            width=WIN_W, height=WIN_H_MIN
        )
        self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # ── Input row ────────────────────────────────────────────────────────
        input_row = tk.Frame(self.root, bg=BG)
        input_row.place(x=0, y=0, width=WIN_W, height=WIN_H_MIN)

        # Dots canvas (left side of input row)
        self._dot_canvas = tk.Canvas(
            input_row, bg=BG, highlightthickness=0, width=56, height=WIN_H_MIN
        )
        self._dot_canvas.pack(side=tk.LEFT, padx=(12, 0))
        self._dots = InteractionDots(self._dot_canvas, cx=28, cy=WIN_H_MIN // 2)

        # Text input
        self.input_entry = tk.Entry(
            input_row,
            font=("Segoe UI", 13),
            bg=BG, fg=TEXT_PRI,
            insertbackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        # Hint label (right side)
        self._hint_lbl = tk.Label(
            input_row, text="↵ run", font=FONT_SMALL,
            bg=BG, fg=TEXT_HINT
        )
        self._hint_lbl.pack(side=tk.RIGHT, padx=(0, 14))

        # ── Separator line ────────────────────────────────────────────────────
        self._sep = tk.Frame(self.root, bg=TEXT_HINT, height=1)
        self._sep.place(x=16, y=WIN_H_MIN - 1, width=WIN_W - 32, height=1)
        self._sep.place_forget()

        # ── Expandable card frame ─────────────────────────────────────────────
        self._card = tk.Frame(self.root, bg=BG_CARD)
        self._card.place_forget()

        # Status / microcopy line
        self._status_lbl = tk.Label(
            self._card, text="", font=FONT_SMALL,
            bg=BG_CARD, fg=TEXT_SEC, anchor="w"
        )
        self._status_lbl.pack(fill=tk.X, padx=16, pady=(10, 2))

        # Plan steps container
        self._steps_frame = tk.Frame(self._card, bg=BG_CARD)
        self._steps_frame.pack(fill=tk.X, padx=16, pady=(0, 6))

        # Suggestion list container (debugger mode)
        self._sugg_frame = tk.Frame(self._card, bg=BG_CARD)
        self._sugg_frame.pack(fill=tk.X, padx=16, pady=(0, 6))

        # Result text (scrollable, shown after execution)
        self._result_var = tk.StringVar()
        self._result_lbl = tk.Label(
            self._card, textvariable=self._result_var,
            font=FONT_BODY, bg=BG_CARD, fg=TEXT_PRI,
            anchor="w", justify=tk.LEFT, wraplength=WIN_W - 48
        )
        self._result_lbl.pack(fill=tk.X, padx=16, pady=(0, 6))
        self._result_lbl.pack_forget()

        # ── Button row ────────────────────────────────────────────────────────
        self._btn_row = tk.Frame(self._card, bg=BG_CARD)
        self._btn_row.pack(fill=tk.X, padx=16, pady=(4, 12))

        self.approve_button = self._make_btn(
            self._btn_row, "Execute", ACCENT, TEXT_PRI, state=tk.DISABLED
        )
        self.approve_button.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_button = self._make_btn(
            self._btn_row, "Cancel", BG_INPUT, TEXT_SEC, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT)

        # ── Key bindings ──────────────────────────────────────────────────────
        self.input_entry.bind("<Return>",  lambda e: self.on_submit() if self.on_submit else None)
        self.input_entry.bind("<Escape>",  lambda e: self.on_escape() if self.on_escape else None)
        self.input_entry.bind("<Up>",      lambda e: self._navigate_suggestions(-1))
        self.input_entry.bind("<Down>",    lambda e: self._navigate_suggestions(+1))
        self.input_entry.bind("<KeyPress>", self._on_keypress)
        # Allow dragging the borderless window
        self.root.bind("<ButtonPress-1>",  self._drag_start)
        self.root.bind("<B1-Motion>",      self._drag_motion)
        self._drag_x = self._drag_y = 0

    def _make_btn(self, parent, text, bg, fg, state=tk.NORMAL) -> tk.Button:
        return tk.Button(
            parent, text=text, font=("Segoe UI", 10),
            bg=bg, fg=fg, activebackground=ACCENT, activeforeground=TEXT_PRI,
            relief=tk.FLAT, bd=0, padx=18, pady=6,
            cursor="hand2", state=state
        )

    # ── Drag support (borderless window) ─────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Fade transitions ──────────────────────────────────────────────────────
    def _fade_to(self, target: float, on_done: Optional[Callable] = None):
        """Animate window alpha from current to target."""
        if self._fade_after:
            try:
                self.root.after_cancel(self._fade_after)
            except Exception:
                pass
        self._fade_target = target
        self._fade_step(on_done)

    def _fade_step(self, on_done: Optional[Callable]):
        current = self.root.attributes("-alpha")
        diff = self._fade_target - current
        if abs(diff) < 0.04:
            self.root.attributes("-alpha", self._fade_target)
            if on_done:
                on_done()
            return
        step = diff / FADE_STEPS
        self.root.attributes("-alpha", current + step)
        self._fade_after = self.root.after(
            FADE_MS, lambda: self._fade_step(on_done)
        )

    # ── Card expand/collapse ──────────────────────────────────────────────────
    def _show_card(self, height: int = WIN_H_CARD):
        self._set_size(WIN_W, height)
        self._sep.place(x=16, y=WIN_H_MIN - 1, width=WIN_W - 32, height=1)
        self._card.place(x=0, y=WIN_H_MIN, width=WIN_W, height=height - WIN_H_MIN)

    def _hide_card(self):
        self._card.place_forget()
        self._sep.place_forget()
        self._set_size(WIN_W, WIN_H_MIN)

    def _clear_steps(self):
        for w in self._steps_frame.winfo_children():
            w.destroy()

    def _clear_suggestions(self):
        for w in self._sugg_frame.winfo_children():
            w.destroy()
        self._suggestions = []
        self._suggestion_actions = []

    # ── UI State machine ──────────────────────────────────────────────────────
    def set_ui_state(self, state: str):
        """Drive dots animation and microcopy from a single state string."""
        self._ui_state = state
        self._dots.set_state(state)

        microcopy = {
            UIState.IDLE:      "",
            UIState.LISTENING: "Listening…",
            UIState.THINKING:  "Working on it…",
            UIState.APPROVAL:  "Ready to execute",
            UIState.EXECUTING: "Running…",
            UIState.SUCCESS:   "Done",
            UIState.DEBUGGER:  "I found a few possibilities",
            UIState.ERROR:     "Something went wrong",
        }
        color = {
            UIState.IDLE:      TEXT_HINT,
            UIState.LISTENING: TEXT_SEC,
            UIState.THINKING:  TEXT_SEC,
            UIState.APPROVAL:  ACCENT,
            UIState.EXECUTING: WARN,
            UIState.SUCCESS:   SUCCESS,
            UIState.DEBUGGER:  WARN,
            UIState.ERROR:     ERROR_COL,
        }
        self._status_lbl.config(
            text=microcopy.get(state, ""),
            fg=color.get(state, TEXT_SEC)
        )
        self._hint_lbl.config(
            text="↵ run" if state in (UIState.IDLE, UIState.LISTENING) else ""
        )

    # ── Keypress → listening state ────────────────────────────────────────────
    def _on_keypress(self, event):
        if self._ui_state == UIState.IDLE and event.char and event.char.isprintable():
            self.set_ui_state(UIState.LISTENING)

    # ── Public API ────────────────────────────────────────────────────────────
    def get_user_input(self) -> str:
        return self.input_entry.get().strip()

    def clear_input(self):
        self.input_entry.delete(0, tk.END)

    def set_status(self, text: str, color: str = "gray"):
        """Compatibility shim — maps old color names to design tokens."""
        _map = {
            "gray":   TEXT_SEC,
            "green":  SUCCESS,
            "red":    ERROR_COL,
            "blue":   ACCENT,
            "orange": WARN,
        }
        self._status_lbl.config(text=text, fg=_map.get(color, color))

    def show_plan(self, plan_text: str):
        """
        Display a structured plan card.
        Parses the plan_text produced by controller._format_plan() and renders
        it as clean step rows instead of raw monospace text.
        """
        self._clear_steps()
        self._clear_suggestions()
        self._result_lbl.pack_forget()

        steps = self._parse_plan_steps(plan_text)

        if steps:
            for i, step in enumerate(steps):
                row = tk.Frame(self._steps_frame, bg=BG_CARD)
                row.pack(fill=tk.X, pady=2)
                num_lbl = tk.Label(
                    row, text=f"{i+1}",
                    font=("Segoe UI", 9), bg=ACCENT_DIM, fg=TEXT_PRI,
                    width=2, anchor="center"
                )
                num_lbl.pack(side=tk.LEFT, padx=(0, 8))
                tk.Label(
                    row, text=step, font=FONT_BODY,
                    bg=BG_CARD, fg=TEXT_PRI, anchor="w"
                ).pack(side=tk.LEFT, fill=tk.X)
        else:
            # Fallback: show raw text in a label
            tk.Label(
                self._steps_frame, text=plan_text,
                font=FONT_MONO, bg=BG_CARD, fg=TEXT_SEC,
                anchor="w", justify=tk.LEFT, wraplength=WIN_W - 48
            ).pack(fill=tk.X)

        self.approve_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        self._show_card(WIN_H_CARD)
        self.set_ui_state(UIState.APPROVAL)

    def show_debugger(self, message: str, suggestions: List[str],
                      actions: Optional[List[dict]] = None):
        """
        Show selectable suggestion list (debugger mode).
        Arrow keys navigate, Enter confirms, Escape closes.
        """
        self._clear_steps()
        self._clear_suggestions()
        self._result_lbl.pack_forget()

        self._suggestions = suggestions
        self._suggestion_actions = actions or []
        self._selected_idx = 0

        # Header
        tk.Label(
            self._sugg_frame, text=message,
            font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC,
            anchor="w", wraplength=WIN_W - 48
        ).pack(fill=tk.X, pady=(0, 6))

        # Suggestion rows
        self._sugg_labels: List[tk.Label] = []
        for i, s in enumerate(suggestions):
            lbl = tk.Label(
                self._sugg_frame, text=f"  {s}",
                font=FONT_BODY, bg=BG_CARD, fg=TEXT_PRI,
                anchor="w", cursor="hand2", pady=4
            )
            lbl.pack(fill=tk.X)
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_suggestion(idx))
            self._sugg_labels.append(lbl)

        self._highlight_suggestion(0)

        self.approve_button.config(state=tk.NORMAL, text="Select")
        self.cancel_button.config(state=tk.NORMAL)
        self._show_card(WIN_H_DBG)
        self.set_ui_state(UIState.DEBUGGER)

        # Wire Enter to confirm selection
        self.input_entry.bind("<Return>", lambda e: self._confirm_suggestion())

    def _highlight_suggestion(self, idx: int):
        for i, lbl in enumerate(self._sugg_labels):
            if i == idx:
                lbl.config(bg=ACCENT_DIM, fg=TEXT_PRI)
            else:
                lbl.config(bg=BG_CARD, fg=TEXT_PRI)

    def _select_suggestion(self, idx: int):
        self._selected_idx = idx
        self._highlight_suggestion(idx)

    def _navigate_suggestions(self, delta: int):
        if not self._suggestions:
            return
        self._selected_idx = (self._selected_idx + delta) % len(self._suggestions)
        self._highlight_suggestion(self._selected_idx)

    def _confirm_suggestion(self):
        if self.on_suggestion_select and self._suggestions:
            action = (
                self._suggestion_actions[self._selected_idx]
                if self._selected_idx < len(self._suggestion_actions)
                else None
            )
            self.on_suggestion_select(self._selected_idx, action)

    def get_selected_suggestion(self) -> Optional[int]:
        return self._selected_idx if self._suggestions else None

    def show_result(self, result_text: str, success: bool = True):
        """Display execution result inside the card."""
        self._clear_steps()
        self._clear_suggestions()

        self._result_var.set(result_text)
        self._result_lbl.config(fg=SUCCESS if success else ERROR_COL)
        self._result_lbl.pack(fill=tk.X, padx=16, pady=(0, 6))

        self.approve_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED, text="Cancel")
        self._show_card(WIN_H_CARD)
        self.set_ui_state(UIState.SUCCESS if success else UIState.ERROR)

    def reset(self):
        self.clear_input()
        self._clear_steps()
        self._clear_suggestions()
        self._result_lbl.pack_forget()
        self._result_var.set("")
        self.approve_button.config(state=tk.DISABLED, text="Execute")
        self.cancel_button.config(state=tk.DISABLED, text="Cancel")
        self._hide_card()
        self.set_ui_state(UIState.IDLE)
        # Restore normal Enter binding
        self.input_entry.bind("<Return>", lambda e: self.on_submit() if self.on_submit else None)

    def enable_input(self):
        self.input_entry.config(state=tk.NORMAL)

    def disable_input(self):
        self.input_entry.config(state=tk.DISABLED)

    # ── Bind helpers (controller API) ─────────────────────────────────────────
    def bind_submit(self, callback):
        self.on_submit = callback
        self.input_entry.bind("<Return>", lambda e: callback())

    def bind_approve(self, callback):
        self.on_approve = callback
        self.approve_button.config(command=callback)

    def bind_cancel(self, callback):
        self.on_cancel = callback
        self.cancel_button.config(command=callback)

    def bind_escape(self, callback):
        self.on_escape = callback

    def bind_close(self, callback):
        self.on_close = callback

    def _on_close(self):
        if self.on_close:
            self.on_close()

    # ── Show / hide with fade ─────────────────────────────────────────────────
    def show_overlay(self):
        self._set_size(WIN_W, WIN_H_MIN)
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.input_entry.focus_set()
        self.set_ui_state(UIState.IDLE)
        self._fade_to(0.96)

    def hide_overlay(self):
        self._fade_to(0.0, on_done=lambda: self.root.withdraw())
        self.reset()

    # ── Plan text parser ──────────────────────────────────────────────────────
    @staticmethod
    def _parse_plan_steps(plan_text: str) -> List[str]:
        """
        Extract human-readable step descriptions from controller's plan text.
        Returns a list of clean strings for the card UI.
        """
        steps = []
        # Action-label map for clean microcopy
        _labels = {
            "open_application": "Opening {}",
            "open_website":     "Opening {}",
            "search_web":       "Searching {}",
            "search_files":     "Searching files for {}",
            "get_system_info":  "Reading system info",
            "list_processes":   "Listing running processes",
            "take_screenshot":  "Taking a screenshot",
            "read_file":        "Reading {}",
            "write_file":       "Writing {}",
            "create_file":      "Creating {}",
            "list_directory":   "Listing directory",
            "kill_process":     "Stopping {}",
            "get_clipboard":    "Reading clipboard",
            "set_clipboard":    "Writing to clipboard",
            "get_network_info": "Reading network info",
        }

        lines = plan_text.splitlines()
        current_action = None
        current_params: dict = {}

        for line in lines:
            stripped = line.strip()
            # Detect step lines like "  1. open_application"
            if stripped and stripped[0].isdigit() and ". " in stripped:
                if current_action:
                    steps.append(_format_step(current_action, current_params, _labels))
                parts = stripped.split(". ", 1)
                current_action = parts[1].strip() if len(parts) > 1 else ""
                current_params = {}
            # Detect param lines like "     - app_name: chrome"
            elif stripped.startswith("- ") and current_action and ": " in stripped:
                kv = stripped[2:].split(": ", 1)
                if len(kv) == 2:
                    current_params[kv[0].strip()] = kv[1].strip()

        if current_action:
            steps.append(_format_step(current_action, current_params, _labels))

        return steps


def _format_step(action: str, params: dict, labels: dict) -> str:
    """Produce a clean human-readable step string."""
    template = labels.get(action)
    if not template:
        return action.replace("_", " ").title()

    # Find the most meaningful param value
    value = (
        params.get("app_name") or params.get("site_name") or
        params.get("query") or params.get("pattern") or
        params.get("path") or params.get("name") or ""
    )
    if "{}" in template and value:
        return template.format(value.title() if len(value) < 20 else value)
    return template.replace(" {}", "")
