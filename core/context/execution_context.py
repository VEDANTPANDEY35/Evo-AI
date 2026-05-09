"""
Execution Context
=================
Lightweight, ephemeral workflow context that lives only for the duration of a
single multi-step command execution.

Rules:
- Context exists ONLY during workflow execution (created per plan, discarded after).
- No long-term memory.  No persistence.  No global variables.
- Context must be explicitly passed — never imported as a singleton.
- No autonomous state tracking.  State is set only by explicit calls from Brain.

Purpose:
    When the user says "open chrome and search spotify", the context records
    that Chrome was opened so the subsequent search_web step can target Chrome
    instead of the system-default browser.

Usage:
    ctx = ExecutionContext()
    ctx.set_active_browser("chrome")
    browser = ctx.get_active_browser()   # → "chrome"
    ctx.reset()                          # clears all state
"""
from typing import Optional, Dict, Any


# Canonical browser name → executable base name used by BrowserAutomation
_BROWSER_EXE_MAP: Dict[str, str] = {
    "chrome":   "chrome",
    "brave":    "brave",
    "edge":     "msedge",
    "firefox":  "firefox",
    "safari":   "safari",
    "opera":    "opera",
}


class ExecutionContext:
    """
    Ephemeral workflow context for a single plan execution.

    Tracks:
        active_browser  — browser opened during this workflow
        active_app      — last application opened during this workflow

    All state is cleared by reset() or when the object goes out of scope.
    """

    def __init__(self):
        self._active_browser: Optional[str] = None   # canonical name, e.g. "chrome"
        self._active_app: Optional[str] = None        # e.g. "vscode"

    # ------------------------------------------------------------------
    # Browser context
    # ------------------------------------------------------------------

    def set_active_browser(self, browser_name: str) -> None:
        """
        Record that *browser_name* was opened in this workflow.

        Args:
            browser_name: Canonical browser name (chrome, brave, edge, firefox…)
        """
        canonical = browser_name.lower().strip()
        # Normalise common aliases
        aliases = {
            "google chrome": "chrome",
            "microsoft edge": "edge",
            "mozilla firefox": "firefox",
        }
        canonical = aliases.get(canonical, canonical)
        self._active_browser = canonical

    def get_active_browser(self) -> Optional[str]:
        """
        Return the canonical name of the browser opened in this workflow,
        or None if no browser has been opened yet.
        """
        return self._active_browser

    def get_browser_exe(self) -> Optional[str]:
        """
        Return the executable base name for the active browser,
        suitable for matching against BrowserAutomation.BROWSER_PATHS.

        Returns None if no browser is active.
        """
        if not self._active_browser:
            return None
        return _BROWSER_EXE_MAP.get(self._active_browser)

    def has_active_browser(self) -> bool:
        """Return True if a browser was opened earlier in this workflow."""
        return self._active_browser is not None

    # ------------------------------------------------------------------
    # App context
    # ------------------------------------------------------------------

    def set_active_app(self, app_name: str) -> None:
        """Record that *app_name* was opened in this workflow."""
        self._active_app = app_name.lower().strip()

    def get_active_app(self) -> Optional[str]:
        """Return the last app opened in this workflow, or None."""
        return self._active_app

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all context state.  Call between separate commands."""
        self._active_browser = None
        self._active_app = None

    def snapshot(self) -> Dict[str, Any]:
        """Return a read-only snapshot of current context (for logging/debug)."""
        return {
            "active_browser": self._active_browser,
            "active_app": self._active_app,
        }

    def __repr__(self) -> str:
        return f"ExecutionContext({self.snapshot()})"
