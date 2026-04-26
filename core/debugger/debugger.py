"""
Debugger - Repair suggestion layer for Evo-AI.

Activates ONLY when resolution confidence is "low" or a fallback_info is present.

Responsibilities:
  - Inspect a ResolutionResult and optional fallback_info
  - Generate human-readable suggestions (closest app matches, web search option)
  - Return a structured DebugReport

This module is NON-EXECUTING:
  - It never calls tools
  - It never launches applications
  - It never modifies system state
  - It never calls an LLM
  - All suggestions are deterministic (fuzzy match on known data)

Integration point:
  After resolver, before execution — the Brain checks whether a DebugReport
  should be returned instead of proceeding to the Planner/Executor.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# DebugReport — structured output of the debugger
# ---------------------------------------------------------------------------

@dataclass
class DebugReport:
    """
    Output of the Debugger.

    status:
        Always "debug".

    message:
        A single human-readable explanation of what went wrong.

    suggestions:
        Ordered list of repair suggestions.
        Each suggestion is a plain string the user can act on.
        Examples:
          "Open application: spotify"
          "Search web for: spotify"

    next_actions:
        Ordered list of machine-readable action descriptors.
        Each entry is a dict with keys:
          "action"  — tool name (e.g. "open_application", "search_web")
          "params"  — parameter dict for that tool
          "label"   — short human label shown alongside the action
        The execution layer presents these to the user; the user picks one.
        Nothing is executed automatically.
    """
    status: str = "debug"
    message: str = ""
    suggestions: List[str] = field(default_factory=list)
    next_actions: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Known-apps reference (mirrors resolver — kept local to avoid coupling)
# Only the canonical names are needed here, not the exe paths.
# ---------------------------------------------------------------------------
_KNOWN_APP_NAMES: List[str] = [
    "chrome", "firefox", "edge", "brave", "opera",
    "vscode", "notepad", "notepad++", "sublime", "pycharm", "intellij",
    "cmd", "powershell", "wt", "explorer",
    "vlc", "spotify",
    "discord", "slack", "teams", "zoom", "skype", "telegram", "signal", "whatsapp",
    "winword", "excel", "powerpnt", "onenote", "outlook", "libreoffice",
    "taskmgr", "regedit", "control", "mspaint", "calculator", "wordpad",
    "postman", "docker", "filezilla", "putty", "winscp", "wireshark",
    "photoshop", "gimp", "inkscape", "blender", "obs",
    "steam", "epicgames",
]

_KNOWN_WEBSITE_NAMES: List[str] = [
    "youtube", "google", "github", "gmail", "reddit",
    "spotify", "teams", "outlook", "drive", "meet",
]


class Debugger:
    """
    Non-executing repair suggestion engine.

    Usage:
        debugger = Debugger(debug=False)
        report = debugger.analyze(
            resolution=resolution_result,
            original_input="open spotfy",
            fallback_info=fallback_info_dict,   # optional
        )
        if report:
            # Return report to user instead of executing
            ...
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_activate(
        self,
        resolution_confidence: str,
        fallback_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine whether the debugger should activate.

        Activates when:
          - resolution confidence is "low"
          - OR fallback_info is present (app not found locally)

        Args:
            resolution_confidence: "high" | "medium" | "low"
            fallback_info: dict from resolver.make_fallback_info(), or None

        Returns:
            True if the debugger should produce a report.
        """
        if resolution_confidence == "low":
            return True
        if fallback_info is not None:
            return True
        return False

    def analyze(
        self,
        resolution,                          # ResolutionResult
        original_input: str,
        fallback_info: Optional[Dict[str, Any]] = None,
    ) -> DebugReport:
        """
        Analyze a low-confidence or failed resolution and produce repair suggestions.

        Args:
            resolution:     ResolutionResult from the resolver.
            original_input: The raw user input string (before normalization).
            fallback_info:  Optional fallback descriptor from make_fallback_info().

        Returns:
            DebugReport with message, suggestions, and next_actions.
        """
        query = resolution.query or original_input.strip().lower()
        report = DebugReport()

        self._log(f"Analyzing: query='{query}' confidence={resolution.confidence}")

        # ── Build the human-readable message ────────────────────────────────
        if fallback_info and fallback_info.get("reason") == "APPLICATION_NOT_FOUND":
            report.message = (
                f"Application '{query}' was not found on this system. "
                f"You can search the web for it instead, or try a similar app name."
            )
        elif resolution.confidence == "low" and resolution.category == "unknown":
            report.message = (
                f"Could not understand '{query}'. "
                f"Try a more specific app name or search the web."
            )
        else:
            report.message = (
                f"'{query}' could not be resolved with high confidence. "
                f"Here are some options:"
            )

        # ── Generate suggestions ─────────────────────────────────────────────
        close_apps = self._fuzzy_match_apps(query)
        close_sites = self._fuzzy_match_websites(query)

        # App suggestions
        for app_name in close_apps:
            report.suggestions.append(f"Open application: {app_name}")
            report.next_actions.append({
                "action": "open_application",
                "params": {"app_name": app_name},
                "label": f"Open {app_name}",
            })

        # Website suggestions
        for site_name in close_sites:
            report.suggestions.append(f"Open website: {site_name}")
            report.next_actions.append({
                "action": "open_website",
                "params": {"site_name": site_name},
                "label": f"Open {site_name} website",
            })

        # Web search is always offered as the last option
        report.suggestions.append(f"Search web for: {query}")
        report.next_actions.append({
            "action": "search_web",
            "params": {"query": query},
            "label": f"Search the web for '{query}'",
        })

        self._log(
            f"Report: {len(report.suggestions)} suggestions, "
            f"{len(report.next_actions)} next_actions"
        )
        return report

    # ------------------------------------------------------------------
    # Fuzzy matching helpers — deterministic, no LLM
    # ------------------------------------------------------------------

    def _fuzzy_match_apps(self, query: str, max_results: int = 3) -> List[str]:
        """
        Find known app names that are close to the query.

        Scoring (deterministic):
          3 — exact match
          2 — query is a prefix of the app name
          2 — app name is a prefix of the query
          1 — query is a substring of the app name
          1 — app name is a substring of the query

        Returns up to max_results names, sorted by score descending.
        """
        return self._score_candidates(query, _KNOWN_APP_NAMES, max_results)

    def _fuzzy_match_websites(self, query: str, max_results: int = 2) -> List[str]:
        """
        Find known website names that are close to the query.
        Same scoring as _fuzzy_match_apps.
        """
        return self._score_candidates(query, _KNOWN_WEBSITE_NAMES, max_results)

    def _score_candidates(
        self,
        query: str,
        candidates: List[str],
        max_results: int,
        min_score: int = 2,  # NEW: minimum score threshold
    ) -> List[str]:
        """
        Score a list of candidate names against the query.

        Returns the top max_results names with score >= min_score,
        sorted by score descending then name length ascending.

        min_score threshold filters out weak matches:
          3 = exact match
          2 = prefix match (meaningful)
          1 = substring or character overlap (weak — excluded by default)
        """
        query = query.lower().strip()
        scored = []

        for name in candidates:
            name_lower = name.lower()
            if name_lower == query:
                score = 3
            elif name_lower.startswith(query) or query.startswith(name_lower):
                score = 2
            elif query in name_lower or name_lower in query:
                score = 1
            else:
                # Character overlap as a last-resort signal
                overlap = self._char_overlap(query, name_lower)
                if overlap >= max(2, len(query) // 2):
                    score = 1
                else:
                    continue

            # Filter: only include if score meets threshold
            if score >= min_score:
                scored.append((score, len(name), name))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [name for _, _, name in scored[:max_results]]

    @staticmethod
    def _char_overlap(a: str, b: str) -> int:
        """Count characters that appear in both strings (order-independent)."""
        set_a = set(a)
        set_b = set(b)
        return len(set_a & set_b)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str):
        if self.debug:
            print(f"[DEBUGGER] {message}")
