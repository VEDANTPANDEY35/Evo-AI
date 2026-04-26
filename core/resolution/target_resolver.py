"""
Target Resolver - Resolution layer for Evo-AI.

Responsibilities:
  - Accept a normalized target string
  - Classify it as: application | web_search | unknown
  - Search via Everything CLI (primary) or known-apps list (fallback)
  - Return a structured ResolutionResult

This module is PURE — it does NOT:
  - Decide which tool to execute
  - Build or guess URLs
  - Call any tools
  - Make LLM calls

All decisions are deterministic and rule-based.
"""
import os
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ResolutionResult:
    """
    Structured output from the resolver.

    category:
        "application"  → query is an executable name or full path
        "web_search"   → query should be passed to the search_web tool
        "unknown"      → could not resolve; caller decides what to do

    query:
        The normalized input string (unchanged from what was passed in).

    confidence:
        "high"   → strong match (exact name or Everything CLI hit)
        "medium" → fuzzy match on known-apps list
        "low"    → no match found

    meta:
        Optional debug / diagnostic information.
    """
    category: str                        # "application" | "web_search" | "unknown"
    query: str                           # Normalized input (not a resolved path/URL)
    confidence: str = "high"             # "high" | "medium" | "low"
    resolved_path: Optional[str] = None  # Full path if Everything CLI found it
    meta: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Minimal known-websites set (≤10 entries).
# Only sites where the canonical URL is non-obvious or commonly mistyped.
# Everything else goes through web_search fallback — no URL guessing.
# ---------------------------------------------------------------------------
_KNOWN_WEBSITES: Dict[str, str] = {
    "youtube":  "https://www.youtube.com",
    "google":   "https://www.google.com",
    "github":   "https://github.com",
    "gmail":    "https://mail.google.com",
    "reddit":   "https://www.reddit.com",
    "spotify":  "https://open.spotify.com",   # non-obvious subdomain
    "teams":    "https://teams.microsoft.com",
    "outlook":  "https://outlook.live.com",
    "drive":    "https://drive.google.com",
    "meet":     "https://meet.google.com",
}

# ---------------------------------------------------------------------------
# Known-apps fallback list.
# Used ONLY when Everything CLI is unavailable.
# Maps canonical name → executable name (no path — OS resolves via PATH).
# ---------------------------------------------------------------------------
_KNOWN_APPS: Dict[str, str] = {
    # Browsers
    "chrome":        "chrome.exe",
    "firefox":       "firefox.exe",
    "edge":          "msedge.exe",
    "brave":         "brave.exe",
    "opera":         "opera.exe",
    # Editors / IDEs
    "vscode":        "code.exe",
    "notepad":       "notepad.exe",
    "notepad++":     "notepad++.exe",
    "sublime":       "sublime_text.exe",
    "pycharm":       "pycharm64.exe",
    "intellij":      "idea64.exe",
    # Terminals
    "cmd":           "cmd.exe",
    "powershell":    "powershell.exe",
    "wt":            "wt.exe",
    # File managers
    "explorer":      "explorer.exe",
    # Media
    "vlc":           "vlc.exe",
    "spotify":       "spotify.exe",
    # Communication
    "discord":       "discord.exe",
    "slack":         "slack.exe",
    "teams":         "teams.exe",
    "zoom":          "zoom.exe",
    "skype":         "skype.exe",
    "telegram":      "telegram.exe",
    "signal":        "signal.exe",
    "whatsapp":      "whatsapp.exe",
    # Productivity
    "winword":       "winword.exe",
    "excel":         "excel.exe",
    "powerpnt":      "powerpnt.exe",
    "onenote":       "onenote.exe",
    "outlook":       "outlook.exe",
    "libreoffice":   "soffice.exe",
    # System tools
    "taskmgr":       "taskmgr.exe",
    "regedit":       "regedit.exe",
    "control":       "control.exe",
    "mspaint":       "mspaint.exe",
    "calculator":    "calc.exe",
    "wordpad":       "wordpad.exe",
    # Dev tools
    "postman":       "postman.exe",
    "docker":        "docker desktop.exe",
    "filezilla":     "filezilla.exe",
    "putty":         "putty.exe",
    "winscp":        "winscp.exe",
    "wireshark":     "wireshark.exe",
    # Creative
    "photoshop":     "photoshop.exe",
    "gimp":          "gimp-2.10.exe",
    "inkscape":      "inkscape.exe",
    "blender":       "blender.exe",
    "obs":           "obs64.exe",
    # Game launchers
    "steam":         "steam.exe",
    "epicgames":     "epicgameslauncher.exe",
}


class TargetResolver:
    """
    Deterministic 4-step resolution pipeline.

    Step 1: Normalize (strip/lowercase — caller should already do this)
    Step 2: Everything CLI search (primary, Windows only)
    Step 3: Known-apps fallback (if Everything unavailable)
    Step 4: Web search fallback (if no local match)

    Returns ResolutionResult — never raises exceptions.
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._es_path: Optional[str] = self._find_everything_cli()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, target: str) -> ResolutionResult:
        """
        Resolve a normalized target to a ResolutionResult.

        Args:
            target: Normalized target name (e.g. "spotify", "vscode")

        Returns:
            ResolutionResult with category, query, confidence, and optional meta.
        """
        if not target or not target.strip():
            return ResolutionResult(
                category="unknown",
                query=target,
                confidence="low",
                meta={"reason": "EMPTY_TARGET"}
            )

        target = target.strip().lower()
        self._log(f"Resolving: '{target}'")

        # Step 1: Check known websites (minimal set only)
        if target in _KNOWN_WEBSITES:
            self._log(f"Known website match: {target}")
            return ResolutionResult(
                category="web_search",
                query=target,
                confidence="high",
                resolved_path=_KNOWN_WEBSITES[target],
                meta={"source": "known_websites"}
            )

        # Step 2: Everything CLI search (primary app resolution)
        if self._es_path:
            path = self._search_everything(target)
            if path:
                self._log(f"Everything CLI found: {path}")
                return ResolutionResult(
                    category="application",
                    query=target,
                    confidence="high",
                    resolved_path=path,
                    meta={"source": "everything_cli"}
                )

        # Step 3: Known-apps fallback (only when Everything is unavailable)
        exe = self._lookup_known_apps(target)
        if exe:
            self._log(f"Known-apps match: {exe}")
            return ResolutionResult(
                category="application",
                query=target,
                confidence="medium",
                resolved_path=exe,
                meta={"source": "known_apps"}
            )

        # Step 4: Web search fallback — explicit, not silent
        self._log(f"No local match for '{target}' — suggesting web_search")
        return ResolutionResult(
            category="web_search",
            query=target,
            confidence="low",
            meta={
                "source": "web_search_fallback",
                "reason": "APPLICATION_NOT_FOUND",
                "suggested_action": "web_search",
            }
        )

    def make_fallback_info(self, target: str) -> dict:
        """
        Return a structured fallback descriptor for the execution layer.

        The execution layer uses this to decide whether to prompt the user
        before performing a web search instead of launching an app.
        """
        return {
            "status": "fallback",
            "reason": "APPLICATION_NOT_FOUND",
            "suggested_action": "web_search",
            "query": target,
        }

    # ------------------------------------------------------------------
    # Step 2: Everything CLI
    # ------------------------------------------------------------------

    def _find_everything_cli(self) -> Optional[str]:
        """Locate es.exe on the system (PATH + common install dirs)."""
        es = shutil.which("es.exe") or shutil.which("es")
        if es:
            self._log(f"Everything CLI in PATH: {es}")
            return es

        candidates = [
            r"C:\Program Files\Everything\es.exe",
            r"C:\Program Files (x86)\Everything\es.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Everything\es.exe"),
            r"C:\Tools\es.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                self._log(f"Everything CLI at: {path}")
                return path

        self._log("Everything CLI not found — using known-apps fallback")
        return None

    def _search_everything(self, target: str) -> Optional[str]:
        """
        Search for <target>.exe via Everything CLI.

        Returns the best-matching absolute path, or None.
        """
        try:
            result = subprocess.run(
                [self._es_path, f"{target}.exe", "-n", "20"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            exe_lines = [l for l in lines if l.lower().endswith(".exe")]
            if not exe_lines:
                return None

            return self._rank_results(exe_lines, target)

        except subprocess.TimeoutExpired:
            self._log("Everything CLI timed out")
            return None
        except Exception as e:
            self._log(f"Everything CLI error: {e}")
            return None

    def _rank_results(self, paths: List[str], target: str) -> Optional[str]:
        """
        Rank Everything CLI results deterministically.

        Score:  3 = exact filename match
                2 = filename starts with target
                1 = filename contains target
                0 = excluded
        Tiebreak: shorter path wins (prefer system installs over deep dirs).
        """
        scored = []
        for path in paths:
            name = os.path.basename(path).lower().removesuffix(".exe")
            if name == target:
                score = 3
            elif name.startswith(target):
                score = 2
            elif target in name:
                score = 1
            else:
                continue
            scored.append((score, len(path), path))

        if not scored:
            return None

        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][2]

    # ------------------------------------------------------------------
    # Step 3: Known-apps fallback
    # ------------------------------------------------------------------

    def _lookup_known_apps(self, target: str) -> Optional[str]:
        """
        Look up target in _KNOWN_APPS.

        Match order: exact → prefix → substring.
        Returns executable name (e.g. "code.exe"), or None.
        """
        if target in _KNOWN_APPS:
            return _KNOWN_APPS[target]

        candidates = []
        for key, exe in _KNOWN_APPS.items():
            if key.startswith(target) or target.startswith(key):
                common = len(os.path.commonprefix([target, key]))
                candidates.append((common, len(key), exe))
            elif target in key:
                candidates.append((len(target), len(key), exe))

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1]))
            return candidates[0][2]

        return None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str):
        if self.debug:
            print(f"[RESOLVER] {message}")
