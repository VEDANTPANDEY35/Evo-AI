"""
Parameter Extraction Layer
==========================
Converts natural-language intent strings into structured, typed parameter dicts.

Rules:
- NO LLM.  All logic is regex + deterministic lookup tables.
- Never executes anything.
- Returns structured dicts only.
- Called AFTER intent resolution, BEFORE planner step generation.

Integration point:
    Input → Normalizer → Resolver → ParameterExtractor (HERE) → Planner → Executor
"""
import re
import os
import platform
from typing import Dict, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Natural-language file-type words → glob pattern
_FILE_TYPE_MAP: Dict[str, str] = {
    # Code
    "python":       "*.py",
    "py":           "*.py",
    "javascript":   "*.js",
    "js":           "*.js",
    "typescript":   "*.ts",
    "ts":           "*.ts",
    "java":         "*.java",
    "c":            "*.c",
    "cpp":          "*.cpp",
    "c++":          "*.cpp",
    "csharp":       "*.cs",
    "cs":           "*.cs",
    "rust":         "*.rs",
    "go":           "*.go",
    "ruby":         "*.rb",
    "php":          "*.php",
    "swift":        "*.swift",
    "kotlin":       "*.kt",
    "shell":        "*.sh",
    "bash":         "*.sh",
    "powershell":   "*.ps1",
    "batch":        "*.bat",
    # Documents
    "pdf":          "*.pdf",
    "word":         "*.docx",
    "doc":          "*.docx",
    "docx":         "*.docx",
    "excel":        "*.xlsx",
    "xls":          "*.xlsx",
    "xlsx":         "*.xlsx",
    "powerpoint":   "*.pptx",
    "ppt":          "*.pptx",
    "pptx":         "*.pptx",
    "text":         "*.txt",
    "txt":          "*.txt",
    "csv":          "*.csv",
    "json":         "*.json",
    "xml":          "*.xml",
    "yaml":         "*.yaml",
    "yml":          "*.yml",
    "markdown":     "*.md",
    "md":           "*.md",
    "html":         "*.html",
    "htm":          "*.html",
    "css":          "*.css",
    "sql":          "*.sql",
    # Images
    "image":        "*.{png,jpg,jpeg,gif,bmp,webp,svg}",
    "images":       "*.{png,jpg,jpeg,gif,bmp,webp,svg}",
    "photo":        "*.{jpg,jpeg,png,heic,raw}",
    "photos":       "*.{jpg,jpeg,png,heic,raw}",
    "picture":      "*.{png,jpg,jpeg,gif,bmp}",
    "pictures":     "*.{png,jpg,jpeg,gif,bmp}",
    "png":          "*.png",
    "jpg":          "*.jpg",
    "jpeg":         "*.jpeg",
    "gif":          "*.gif",
    "svg":          "*.svg",
    # Video
    "video":        "*.{mp4,avi,mkv,mov,wmv,flv}",
    "videos":       "*.{mp4,avi,mkv,mov,wmv,flv}",
    "movie":        "*.{mp4,avi,mkv,mov}",
    "movies":       "*.{mp4,avi,mkv,mov}",
    "mp4":          "*.mp4",
    "avi":          "*.avi",
    "mkv":          "*.mkv",
    # Audio
    "audio":        "*.{mp3,wav,flac,aac,ogg}",
    "music":        "*.{mp3,wav,flac,aac,ogg}",
    "mp3":          "*.mp3",
    "wav":          "*.wav",
    # Archives
    "zip":          "*.zip",
    "archive":      "*.{zip,tar,gz,rar,7z}",
    "compressed":   "*.{zip,tar,gz,rar,7z}",
    # Config / misc
    "config":       "*.{json,yaml,yml,ini,cfg,toml}",
    "log":          "*.log",
    "logs":         "*.log",
    "notebook":     "*.ipynb",
    "jupyter":      "*.ipynb",
}

# Natural-language directory names → resolved path (populated at runtime)
def _build_dir_map() -> Dict[str, str]:
    home = os.path.expanduser("~")
    system = platform.system()

    if system == "Windows":
        base = home
    else:
        base = home

    return {
        "documents":    os.path.join(base, "Documents"),
        "document":     os.path.join(base, "Documents"),
        "downloads":    os.path.join(base, "Downloads"),
        "download":     os.path.join(base, "Downloads"),
        "desktop":      os.path.join(base, "Desktop"),
        "pictures":     os.path.join(base, "Pictures"),
        "picture":      os.path.join(base, "Pictures"),
        "photos":       os.path.join(base, "Pictures"),
        "videos":       os.path.join(base, "Videos"),
        "video":        os.path.join(base, "Videos"),
        "music":        os.path.join(base, "Music"),
        "home":         base,
        "~":            base,
    }


# Search-engine name → canonical key used by BrowserAutomation
_SEARCH_ENGINE_MAP: Dict[str, str] = {
    "google":       "google",
    "bing":         "bing",
    "duckduckgo":   "duckduckgo",
    "duck duck go": "duckduckgo",
    "ddg":          "duckduckgo",
    "brave":        "brave",
    "yahoo":        "google",   # fallback
}

# Browser name → canonical key used by ExecutionContext
_BROWSER_NAME_MAP: Dict[str, str] = {
    "chrome":   "chrome",
    "google chrome": "chrome",
    "brave":    "brave",
    "edge":     "edge",
    "microsoft edge": "edge",
    "firefox":  "firefox",
    "mozilla":  "firefox",
    "safari":   "safari",
    "opera":    "opera",
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ParameterExtractor:
    """
    Deterministic parameter extractor.

    Usage:
        extractor = ParameterExtractor()
        enriched_params = extractor.extract("search_files", raw_params, user_input)
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._dir_map = _build_dir_map()

    def _log(self, msg: str):
        if self.debug:
            print(f"[EXTRACTOR] {msg}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        tool: str,
        existing_params: Dict[str, Any],
        user_input: str,
    ) -> Dict[str, Any]:
        """
        Enrich *existing_params* with structured values extracted from
        *user_input* for the given *tool*.

        Only fills in keys that are missing or empty — never overwrites a
        value that was already resolved by the resolver/reasoner.

        Returns the enriched params dict (may be the same object).
        """
        params = dict(existing_params)  # shallow copy — don't mutate caller's dict
        lower = user_input.lower()

        if tool == "search_files":
            params = self._extract_search_files(params, lower)

        elif tool == "search_web":
            params = self._extract_search_web(params, lower)

        elif tool in ("open_application", "open_website"):
            params = self._extract_open(params, lower)

        elif tool in ("read_file", "write_file", "create_file", "delete_file", "list_directory"):
            params = self._extract_file_op(params, lower)

        elif tool in ("kill_process", "list_processes"):
            params = self._extract_process(params, lower)

        self._log(f"extract({tool!r}) → {params}")
        return params

    # ------------------------------------------------------------------
    # Tool-specific extractors
    # ------------------------------------------------------------------

    def _extract_search_files(
        self, params: Dict[str, Any], lower: str
    ) -> Dict[str, Any]:
        """
        Extract `pattern` and `directory` for search_files.

        Examples:
            "find all python files in Documents"
                → pattern="*.py", directory="<home>/Documents"
            "find pdf files in Downloads"
                → pattern="*.pdf", directory="<home>/Downloads"
            "search images on Desktop"
                → pattern="*.{png,jpg,...}", directory="<home>/Desktop"
        """
        # ── pattern ──────────────────────────────────────────────────────────
        if not params.get("pattern"):
            pattern = self._detect_file_type(lower)
            if pattern:
                params["pattern"] = pattern
                self._log(f"  pattern detected: {pattern!r}")

        # ── directory ────────────────────────────────────────────────────────
        if not params.get("directory"):
            directory = self._detect_directory(lower)
            if directory:
                params["directory"] = directory
                self._log(f"  directory detected: {directory!r}")

        return params

    def _extract_search_web(
        self, params: Dict[str, Any], lower: str
    ) -> Dict[str, Any]:
        """
        Extract `query` and optionally `engine` for search_web.

        Examples:
            "search for spotify"       → query="spotify"
            "google python tutorials"  → query="python tutorials", engine="google"
        """
        # ── query ─────────────────────────────────────────────────────────────
        if not params.get("query"):
            query = self._extract_search_query(lower)
            if query:
                params["query"] = query

        # ── engine ────────────────────────────────────────────────────────────
        if not params.get("engine"):
            engine = self._detect_search_engine(lower)
            if engine:
                params["engine"] = engine

        return params

    def _extract_open(
        self, params: Dict[str, Any], lower: str
    ) -> Dict[str, Any]:
        """
        Extract `app_name` / `site_name` for open_application / open_website.
        Mostly already handled by the resolver; this fills gaps.
        """
        # Nothing to add — resolver handles this well.
        # Kept as extension point for future enrichment.
        return params

    def _extract_file_op(
        self, params: Dict[str, Any], lower: str
    ) -> Dict[str, Any]:
        """
        Extract `path` for file operations when not already present.
        Resolves natural directory names to absolute paths.
        """
        if params.get("path"):
            # Resolve natural directory names inside the path
            path = params["path"]
            for name, resolved in self._dir_map.items():
                if path.lower() == name:
                    params["path"] = resolved
                    break
        return params

    def _extract_process(
        self, params: Dict[str, Any], lower: str
    ) -> Dict[str, Any]:
        """
        Extract process `name` for kill_process when not already present.

        Example:
            "kill chrome"  → name="chrome"
        """
        if not params.get("name") and not params.get("pid"):
            # Patterns: "kill <name>", "stop <name>", "terminate <name>"
            m = re.search(
                r'\b(?:kill|stop|terminate|end|close)\s+([a-z0-9_\-\.]+)',
                lower
            )
            if m:
                params["name"] = m.group(1)
        return params

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_file_type(self, lower: str) -> Optional[str]:
        """
        Return a glob pattern for the file type mentioned in *lower*.

        Matches phrases like:
            "all python files", "pdf files", "image files", "*.py files"
        """
        # Direct glob pattern already present (e.g. user typed "*.py")
        m = re.search(r'\*\.[a-z0-9]+', lower)
        if m:
            return m.group(0)

        # "all <type> files" / "<type> files" / "files of type <type>"
        patterns = [
            r'\ball\s+(\w+)\s+files?\b',
            r'\b(\w+)\s+files?\b',
            r'\bfiles?\s+of\s+type\s+(\w+)\b',
            r'\b(\w+)\s+documents?\b',
            r'\b(\w+)\s+photos?\b',
            r'\b(\w+)\s+images?\b',
            r'\b(\w+)\s+videos?\b',
        ]
        for pat in patterns:
            m = re.search(pat, lower)
            if m:
                word = m.group(1).lower()
                if word in _FILE_TYPE_MAP:
                    return _FILE_TYPE_MAP[word]

        # Bare type word anywhere in the string
        for word, glob in _FILE_TYPE_MAP.items():
            # Only match whole words to avoid false positives
            if re.search(r'\b' + re.escape(word) + r'\b', lower):
                return glob

        return None

    def _detect_directory(self, lower: str) -> Optional[str]:
        """
        Return an absolute path for the directory mentioned in *lower*.

        Matches phrases like:
            "in Documents", "from Downloads", "on Desktop", "inside Pictures"
        """
        # Preposition + directory name
        prep_pattern = r'\b(?:in|from|on|inside|under|within|at)\s+(\w+)\b'
        for m in re.finditer(prep_pattern, lower):
            word = m.group(1).lower()
            if word in self._dir_map:
                return self._dir_map[word]

        # Bare directory name (last resort — only if unambiguous)
        for name, path in self._dir_map.items():
            if re.search(r'\b' + re.escape(name) + r'\b', lower):
                return path

        return None

    def _extract_search_query(self, lower: str) -> Optional[str]:
        """
        Extract a clean search query string.

        Strips leading verbs/prepositions:
            "search for spotify"     → "spotify"
            "find information about python" → "information about python"
            "google machine learning" → "machine learning"
        """
        # Remove leading verb phrases
        cleaned = re.sub(
            r'^(?:search\s+(?:for|about|on|the\s+web\s+for)?|'
            r'find\s+(?:information\s+about|info\s+about|about)?|'
            r'look\s+up|google|bing|lookup)\s+',
            '',
            lower.strip()
        )
        # Remove trailing noise
        cleaned = re.sub(r'\s+(?:online|on\s+the\s+web|on\s+google|on\s+bing)$', '', cleaned)
        cleaned = cleaned.strip()
        return cleaned if cleaned else None

    def _detect_search_engine(self, lower: str) -> Optional[str]:
        """Return canonical engine name if one is mentioned."""
        for phrase, engine in _SEARCH_ENGINE_MAP.items():
            if re.search(r'\b' + re.escape(phrase) + r'\b', lower):
                return engine
        return None

    # ------------------------------------------------------------------
    # Browser name detection (used by ExecutionContext)
    # ------------------------------------------------------------------

    def detect_browser(self, lower: str) -> Optional[str]:
        """
        Return canonical browser name if one is mentioned in *lower*.

        Examples:
            "open chrome and search spotify" → "chrome"
            "open edge and search youtube"   → "edge"
        """
        for phrase, name in _BROWSER_NAME_MAP.items():
            if re.search(r'\b' + re.escape(phrase) + r'\b', lower):
                return name
        return None
