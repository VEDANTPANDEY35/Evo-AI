"""
Input Normalizer - Deterministic pre-processing layer for Evo-AI.

Responsibilities:
  - Lowercase and strip whitespace
  - Verb typo correction  (opne → open, lauch → launch, …)
  - Alias normalization   (browser → chrome, my editor → vscode, …)
  - Target typo correction (spotfy → spotify, chorme → chrome, …)
  - Semantic intent mapping for low-confidence phrases
    (music → spotify, coding → vscode, …)

All transformations are table-driven and deterministic.
No LLM calls. No execution logic.
"""
from typing import Dict, Tuple, Optional


# ---------------------------------------------------------------------------
# VERB typo table — corrects misspelled command verbs BEFORE anything else.
# Applied to the first word of the input only.
# ---------------------------------------------------------------------------
_VERB_TYPOS: Dict[str, str] = {
    # open variants
    "opne":   "open",
    "opn":    "open",
    "oen":    "open",
    "oepn":   "open",
    "opeen":  "open",
    # launch variants
    "lauch":  "launch",
    "launhc": "launch",
    "laucnh": "launch",
    "lauhc":  "launch",
    "lnch":   "launch",
    # start variants
    "satrt":  "start",
    "srart":  "start",
    "strat":  "start",
    "strart": "start",
    # run variants
    "rnu":    "run",
    "rn":     "run",
}

# ---------------------------------------------------------------------------
# ALIAS table — maps shorthand / alternate target names to canonical names.
# Includes single-word aliases AND multi-word phrase aliases.
# Keys are lowercase. Values are canonical app/target names.
# ---------------------------------------------------------------------------
_ALIASES: Dict[str, str] = {
    # ── Browsers ────────────────────────────────────────────────────────────
    "browser":            "chrome",
    "web browser":        "chrome",
    "internet":           "chrome",
    "internet browser":   "chrome",
    "my browser":         "chrome",
    "the browser":        "chrome",
    "a browser":          "chrome",
    "chromium":           "chrome",

    # ── Editors / IDEs ──────────────────────────────────────────────────────
    "code":               "vscode",
    "vs code":            "vscode",
    "visual studio code": "vscode",
    "vsc":                "vscode",
    "editor":             "vscode",
    "my editor":          "vscode",
    "code editor":        "vscode",
    "text editor":        "notepad",
    "coding":             "vscode",
    "an editor":          "vscode",

    # ── File managers ────────────────────────────────────────────────────────
    "file manager":       "explorer",
    "file explorer":      "explorer",
    "files":              "explorer",
    "my computer":        "explorer",
    "this pc":            "explorer",

    # ── Media ────────────────────────────────────────────────────────────────
    "music":              "spotify",
    "music player":       "spotify",
    "my music":           "spotify",
    "player":             "vlc",
    "media player":       "vlc",
    "video player":       "vlc",
    "video":              "vlc",
    "videos":             "vlc",

    # ── Communication ────────────────────────────────────────────────────────
    "chat":               "discord",
    "voice chat":         "discord",
    "video call":         "zoom",
    "meeting":            "teams",
    "meetings":           "teams",

    # ── Terminals ────────────────────────────────────────────────────────────
    "terminal":           "cmd",
    "console":            "cmd",
    "shell":              "powershell",
    "command line":       "cmd",
    "command prompt":     "cmd",

    # ── Misc ─────────────────────────────────────────────────────────────────
    "calc":               "calculator",
    "paint":              "mspaint",
    "word":               "winword",
    "powerpoint":         "powerpnt",
    "ppt":                "powerpnt",
    "task manager":       "taskmgr",
    "settings":           "ms-settings:",
    "control panel":      "control",
    "registry":           "regedit",
    "device manager":     "devmgmt.msc",
}

# ---------------------------------------------------------------------------
# TARGET TYPO table — corrects misspelled app/site names.
# Applied to the target portion only (after the verb).
# ---------------------------------------------------------------------------
_TYPO_MAP: Dict[str, str] = {
    # Spotify
    "spotfy":        "spotify",
    "spotifiy":      "spotify",
    "spottify":      "spotify",
    "spotifi":       "spotify",
    # Chrome
    "chorme":        "chrome",
    "chormo":        "chrome",
    "crhome":        "chrome",
    # Google
    "gogle":         "google",
    "googel":        "google",
    # YouTube
    "youtueb":       "youtube",
    "youtub":        "youtube",
    "yotube":        "youtube",
    "youtbe":        "youtube",
    # VS Code
    "vscod":         "vscode",
    "vsocde":        "vscode",
    "vsode":         "vscode",
    # Tinkercad
    "tinkercad.com": "tinkercad",
    # Notepad
    "noteapd":       "notepad",
    "notpad":        "notepad",
    # Firefox
    "fierfox":       "firefox",
    "fireofx":       "firefox",
    "firfox":        "firefox",
    # Discord
    "discrod":       "discord",
    "disocrd":       "discord",
    # Slack
    "slakc":         "slack",
    "slcak":         "slack",
    # Telegram
    "telegarm":      "telegram",
    "teelgram":      "telegram",
    # WhatsApp
    "whatsap":       "whatsapp",
    "watsapp":       "whatsapp",
    # Netflix
    "netflx":        "netflix",
    "netlix":        "netflix",
    # Amazon
    "amazn":         "amazon",
    "amzon":         "amazon",
    # GitHub
    "githb":         "github",
    "gihub":         "github",
    # Twitch
    "twithc":        "twitch",
    "twich":         "twitch",
    # Reddit
    "reddti":        "reddit",
    "reddt":         "reddit",
    # Instagram
    "instagarm":     "instagram",
    "insagram":      "instagram",
    # Twitter
    "twiiter":       "twitter",
    "twiter":        "twitter",
    # LinkedIn
    "lnikedin":      "linkedin",
    "linkdin":       "linkedin",
    "linkedn":       "linkedin",
    # Zoom
    "zomm":          "zoom",
    "zooom":         "zoom",
    # Teams
    "teasm":         "teams",
    "temas":         "teams",
    # Calculator
    "calulator":     "calculator",
    "calcultor":     "calculator",
    "calclator":     "calculator",
    # Explorer
    "exploer":       "explorer",
    "explrer":       "explorer",
    # PowerShell
    "powershll":     "powershell",
    "powrshell":     "powershell",
}

# ---------------------------------------------------------------------------
# SEMANTIC INTENT MAP — rule-based keyword → canonical app mapping.
# Applied ONLY when no direct match or alias was found (confidence is low).
# Maps intent keywords to the most appropriate canonical app name.
# ---------------------------------------------------------------------------
_SEMANTIC_MAP: Dict[str, str] = {
    # Music / audio
    "music":          "spotify",
    "audio":          "spotify",
    "songs":          "spotify",
    "playlist":       "spotify",
    "podcast":        "spotify",
    # Video / media
    "video":          "vlc",
    "videos":         "vlc",
    "movie":          "vlc",
    "movies":         "vlc",
    "media":          "vlc",
    # Coding / development
    "coding":         "vscode",
    "code":           "vscode",
    "programming":    "vscode",
    "development":    "vscode",
    "develop":        "vscode",
    "script":         "vscode",
    "scripts":        "vscode",
    # Chat / communication
    "chat":           "discord",
    "messaging":      "discord",
    "voice":          "discord",
    # Browsing
    "browsing":       "chrome",
    "browse":         "chrome",
    "internet":       "chrome",
    "web":            "chrome",
    # Notes / writing
    "notes":          "notepad",
    "note":           "notepad",
    "writing":        "notepad",
    "text":           "notepad",
    # Design / graphics
    "design":         "gimp",
    "drawing":        "gimp",
    "graphics":       "gimp",
    "image":          "gimp",
    "photo":          "gimp",
    # 3D / modeling
    "3d":             "blender",
    "modeling":       "blender",
    "animation":      "blender",
    # Streaming / recording
    "streaming":      "obs",
    "recording":      "obs",
    "stream":         "obs",
    # Gaming
    "gaming":         "steam",
    "games":          "steam",
    "game":           "steam",
}

# Recognized command verbs (used for verb extraction)
_KNOWN_VERBS = {"open", "launch", "start", "run"}


class InputNormalizer:
    """
    Deterministic input normalization pipeline.

    Normalization order:
      1. Strip + collapse whitespace + lowercase
      2. Correct verb typos  (opne → open)
      3. Extract verb + target
      4. Correct target typos  (spotfy → spotify)
      5. Expand target aliases  (my browser → chrome)
      6. Apply semantic mapping if still unresolved  (music → spotify)

    Usage:
        normalizer = InputNormalizer()
        normalized, changed = normalizer.normalize("opne spotfy")
        # → ("open spotify", True)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, raw_input: str) -> Tuple[str, bool]:
        """
        Normalize a full user input string.

        Returns:
            (normalized_text, was_changed)
        """
        if not raw_input:
            return raw_input, False

        # Step 1: Strip, collapse, lowercase
        text = " ".join(raw_input.strip().split()).lower()

        # Step 2: Correct verb typo (first word only)
        text = self._correct_verb(text)

        # Step 3-6: Correct target (typo + alias + semantic)
        text = self._correct_target(text)

        was_changed = text != raw_input.strip().lower()
        return text, was_changed

    def normalize_target(self, target: str) -> Tuple[str, bool]:
        """
        Normalize just the target string (app name / phrase).

        Applies in order: typo correction → alias expansion → semantic mapping.

        Returns:
            (normalized_target, was_changed)
        """
        if not target:
            return target, False

        original = target.strip().lower()
        result = self._apply_target_corrections(original)
        return result, result != original

    def resolve_semantic(self, phrase: str) -> Optional[str]:
        """
        Apply semantic intent mapping to a phrase.

        Returns the canonical app name if any word in the phrase matches
        a semantic keyword, or None if no match.

        Only intended for use when confidence is already low.
        """
        phrase_lower = phrase.strip().lower()

        # Exact phrase match first
        if phrase_lower in _SEMANTIC_MAP:
            return _SEMANTIC_MAP[phrase_lower]

        # Word-by-word scan (left to right — first match wins)
        for word in phrase_lower.split():
            if word in _SEMANTIC_MAP:
                return _SEMANTIC_MAP[word]

        return None

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_aliases() -> Dict[str, str]:
        """Return a copy of the alias table."""
        return dict(_ALIASES)

    @staticmethod
    def get_typo_map() -> Dict[str, str]:
        """Return a copy of the typo correction table."""
        return dict(_TYPO_MAP)

    @staticmethod
    def get_verb_typos() -> Dict[str, str]:
        """Return a copy of the verb typo table."""
        return dict(_VERB_TYPOS)

    @staticmethod
    def get_semantic_map() -> Dict[str, str]:
        """Return a copy of the semantic intent map."""
        return dict(_SEMANTIC_MAP)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _correct_verb(self, text: str) -> str:
        """
        Correct a misspelled verb at the start of the input.

        Only the first word is examined. If it is in _VERB_TYPOS,
        it is replaced with the correct verb. The rest of the string
        is left unchanged.
        """
        if not text:
            return text
        words = text.split(" ", 1)
        first = words[0]
        if first in _VERB_TYPOS:
            corrected = _VERB_TYPOS[first]
            return corrected + (" " + words[1] if len(words) > 1 else "")
        return text

    def _correct_target(self, text: str) -> str:
        """
        Extract the target from an open/launch/start/run command and
        apply typo correction, alias expansion, and semantic mapping.

        For non-command inputs the text is returned unchanged.
        """
        # Find which verb starts the text
        verb_used = None
        for verb in _KNOWN_VERBS:
            if text.startswith(verb + " "):
                verb_used = verb
                break

        if verb_used is None:
            return text

        target = text[len(verb_used) + 1:].strip()
        if not target:
            return text

        corrected = self._apply_target_corrections(target)
        return verb_used + " " + corrected

    def _apply_target_corrections(self, target: str) -> str:
        """
        Apply the full correction chain to a target string:
          1. Typo correction
          2. Alias expansion
          3. Semantic mapping (only if still unresolved after steps 1-2)
        """
        result = target

        # Step 1: Typo correction
        if result in _TYPO_MAP:
            result = _TYPO_MAP[result]

        # Step 2: Alias expansion (exact phrase match first, then single-word)
        if result in _ALIASES:
            result = _ALIASES[result]

        # Step 3: Semantic mapping — only if the target still looks unresolved
        # (i.e. it wasn't changed by steps 1-2 and isn't a known app/site name)
        if result == target:
            semantic = self.resolve_semantic(result)
            if semantic is not None:
                result = semantic

        return result
