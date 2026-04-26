"""
Input Normalizer - Deterministic pre-processing layer for Evo-AI.

Responsibilities:
  - Lowercase and strip whitespace
  - Alias normalization (browser → chrome, code → vscode, etc.)
  - Basic typo correction for known app names (deterministic table-based)

This module contains NO LLM calls and NO execution logic.
It is a pure transformation layer: string in → string out.
"""
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Alias table: maps common shorthand / alternate names to canonical names.
# Keys are lowercase. Values are the canonical app/target name.
# ---------------------------------------------------------------------------
_ALIASES: Dict[str, str] = {
    # Browsers
    "browser":          "chrome",
    "web browser":      "chrome",
    "internet":         "chrome",
    "internet browser": "chrome",
    "chromium":         "chrome",

    # Editors / IDEs
    "code":             "vscode",
    "vs code":          "vscode",
    "visual studio code": "vscode",
    "vsc":              "vscode",
    "editor":           "vscode",
    "text editor":      "notepad",

    # File managers
    "file manager":     "explorer",
    "file explorer":    "explorer",
    "files":            "explorer",
    "my computer":      "explorer",
    "this pc":          "explorer",

    # Media
    "music":            "spotify",
    "player":           "vlc",
    "media player":     "vlc",
    "video player":     "vlc",

    # Communication
    "chat":             "discord",
    "voice chat":       "discord",
    "video call":       "zoom",
    "meeting":          "teams",

    # Terminals
    "terminal":         "cmd",
    "console":          "cmd",
    "shell":            "powershell",
    "command line":     "cmd",
    "command prompt":   "cmd",

    # Misc
    "calc":             "calculator",
    "paint":            "mspaint",
    "word":             "winword",
    "excel":            "excel",
    "powerpoint":       "powerpnt",
    "ppt":              "powerpnt",
    "task manager":     "taskmgr",
    "settings":         "ms-settings:",
    "control panel":    "control",
    "registry":         "regedit",
    "device manager":   "devmgmt.msc",
}

# ---------------------------------------------------------------------------
# Typo correction table: maps known misspellings to correct names.
# Deterministic — no fuzzy logic here.
# ---------------------------------------------------------------------------
_TYPO_MAP: Dict[str, str] = {
    "spotfy":       "spotify",
    "spotifiy":     "spotify",
    "spottify":     "spotify",
    "spotifi":      "spotify",
    "chorme":       "chrome",
    "chormo":       "chrome",
    "crhome":       "chrome",
    "gogle":        "google",
    "googel":       "google",
    "youtueb":      "youtube",
    "youtub":       "youtube",
    "yotube":       "youtube",
    "youtbe":       "youtube",
    "vscod":        "vscode",
    "vsocde":       "vscode",
    "vsode":        "vscode",
    "tinkercad":    "tinkercad",   # already correct — keep for completeness
    "tinkercad.com": "tinkercad",
    "noteapd":      "notepad",
    "notpad":       "notepad",
    "fierfox":      "firefox",
    "fireofx":      "firefox",
    "firfox":       "firefox",
    "discrod":      "discord",
    "disocrd":      "discord",
    "slakc":        "slack",
    "slcak":        "slack",
    "telegarm":     "telegram",
    "teelgram":     "telegram",
    "whatsap":      "whatsapp",
    "watsapp":      "whatsapp",
    "netflx":       "netflix",
    "netlix":       "netflix",
    "amazn":        "amazon",
    "amzon":        "amazon",
    "githb":        "github",
    "gihub":        "github",
    "twithc":       "twitch",
    "twich":        "twitch",
    "reddti":       "reddit",
    "reddt":        "reddit",
    "instagarm":    "instagram",
    "insagram":     "instagram",
    "twiiter":      "twitter",
    "twiter":       "twitter",
    "lnikedin":     "linkedin",
    "linkdin":      "linkedin",
    "linkedn":      "linkedin",
    "zomm":         "zoom",
    "zooom":        "zoom",
    "teasm":        "teams",
    "temas":        "teams",
    "calulator":    "calculator",
    "calcultor":    "calculator",
    "calclator":    "calculator",
    "exploer":      "explorer",
    "explrer":      "explorer",
    "powershll":    "powershell",
    "powrshell":    "powershell",
}


class InputNormalizer:
    """
    Deterministic input normalization pipeline.

    Usage:
        normalizer = InputNormalizer()
        normalized, was_changed = normalizer.normalize("open spotfy")
        # → ("open spotify", True)
    """

    def normalize(self, raw_input: str) -> Tuple[str, bool]:
        """
        Normalize raw user input.

        Steps:
          1. Strip leading/trailing whitespace
          2. Collapse internal whitespace
          3. Lowercase
          4. Correct known typos in the target word
          5. Expand aliases in the target word

        Returns:
            (normalized_text, was_changed)
            was_changed is True if any transformation was applied.
        """
        if not raw_input:
            return raw_input, False

        original = raw_input

        # Step 1-3: Strip, collapse, lowercase
        text = " ".join(raw_input.strip().split()).lower()

        # Step 4-5: Apply corrections to the target portion only.
        # We only transform the *target* (the word after the verb) to avoid
        # accidentally lowercasing file paths or other content.
        text = self._correct_target(text)

        was_changed = text != original.lower().strip()
        return text, was_changed

    def normalize_target(self, target: str) -> Tuple[str, bool]:
        """
        Normalize just the target word (app name / site name).

        Returns:
            (normalized_target, was_changed)
        """
        if not target:
            return target, False

        original = target.strip().lower()
        result = original

        # Typo correction
        if result in _TYPO_MAP:
            result = _TYPO_MAP[result]

        # Alias expansion
        if result in _ALIASES:
            result = _ALIASES[result]

        return result, result != original

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _correct_target(self, text: str) -> str:
        """
        Identify the target word in an 'open/launch/start X' command and
        apply typo correction + alias expansion to it.

        For non-open commands the full text is returned unchanged.
        """
        verbs = ("open ", "launch ", "start ", "run ")
        for verb in verbs:
            if text.startswith(verb):
                target = text[len(verb):].strip()
                corrected, _ = self.normalize_target(target)
                return verb.rstrip() + " " + corrected

        return text

    # ------------------------------------------------------------------
    # Introspection helpers (useful for debugging / tests)
    # ------------------------------------------------------------------

    @staticmethod
    def get_aliases() -> Dict[str, str]:
        """Return a copy of the alias table."""
        return dict(_ALIASES)

    @staticmethod
    def get_typo_map() -> Dict[str, str]:
        """Return a copy of the typo correction table."""
        return dict(_TYPO_MAP)
