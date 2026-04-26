"""
Target Resolver - Core intelligence layer for Evo-AI's resolution pipeline.

Responsibilities:
  1. Accept a normalized target string (app name / site name)
  2. Classify it as: application | website | web_search | unknown
  3. For applications:
       a. Search via Everything CLI (es.exe) if available
       b. Fall back to fuzzy matching on a curated known-apps list
  4. For websites: return the canonical URL
  5. If nothing matches: fall back to a web search (NOT URL guessing)
  6. Return a structured ResolutionResult — never raise raw exceptions

This module contains NO LLM calls and NO execution logic.
All routing decisions are deterministic and rule-based.
"""
import os
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ResolutionResult:
    """
    Structured output from the resolver.

    type:
        "application"  → value is the executable path or app name to launch
        "website"      → value is the full URL to open
        "web_search"   → value is the search query to pass to search_web
        "unknown"      → could not resolve; value is the original input

    value:
        The resolved target (path, URL, or query string).

    meta:
        Optional debug / diagnostic information dict.
    """
    type: str                          # "application" | "website" | "web_search" | "unknown"
    value: str                         # Resolved target
    meta: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Known websites: maps canonical name → URL.
# This list is intentionally curated — we do NOT guess URLs.
# ---------------------------------------------------------------------------
_KNOWN_WEBSITES: Dict[str, str] = {
    "youtube":       "https://www.youtube.com",
    "google":        "https://www.google.com",
    "facebook":      "https://www.facebook.com",
    "twitter":       "https://www.twitter.com",
    "instagram":     "https://www.instagram.com",
    "linkedin":      "https://www.linkedin.com",
    "github":        "https://www.github.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit":        "https://www.reddit.com",
    "wikipedia":     "https://www.wikipedia.org",
    "amazon":        "https://www.amazon.com",
    "netflix":       "https://www.netflix.com",
    "gmail":         "https://mail.google.com",
    "outlook":       "https://outlook.live.com",
    "yahoo":         "https://www.yahoo.com",
    "bing":          "https://www.bing.com",
    "twitch":        "https://www.twitch.tv",
    "discord":       "https://discord.com",
    "slack":         "https://slack.com",
    "zoom":          "https://zoom.us",
    "teams":         "https://teams.microsoft.com",
    "whatsapp":      "https://web.whatsapp.com",
    "telegram":      "https://web.telegram.org",
    "spotify":       "https://open.spotify.com",
    "soundcloud":    "https://soundcloud.com",
    "tinkercad":     "https://www.tinkercad.com",
    "figma":         "https://www.figma.com",
    "canva":         "https://www.canva.com",
    "notion":        "https://www.notion.so",
    "trello":        "https://trello.com",
    "jira":          "https://www.atlassian.com/software/jira",
    "confluence":    "https://www.atlassian.com/software/confluence",
    "dropbox":       "https://www.dropbox.com",
    "drive":         "https://drive.google.com",
    "docs":          "https://docs.google.com",
    "sheets":        "https://sheets.google.com",
    "slides":        "https://slides.google.com",
    "meet":          "https://meet.google.com",
    "calendar":      "https://calendar.google.com",
    "maps":          "https://maps.google.com",
    "translate":     "https://translate.google.com",
    "chatgpt":       "https://chat.openai.com",
    "openai":        "https://www.openai.com",
    "claude":        "https://claude.ai",
    "perplexity":    "https://www.perplexity.ai",
    "huggingface":   "https://huggingface.co",
    "kaggle":        "https://www.kaggle.com",
    "colab":         "https://colab.research.google.com",
    "replit":        "https://replit.com",
    "codepen":       "https://codepen.io",
    "jsfiddle":      "https://jsfiddle.net",
    "medium":        "https://medium.com",
    "dev.to":        "https://dev.to",
    "hashnode":      "https://hashnode.com",
    "producthunt":   "https://www.producthunt.com",
    "hackernews":    "https://news.ycombinator.com",
    "lobsters":      "https://lobste.rs",
    "pinterest":     "https://www.pinterest.com",
    "tumblr":        "https://www.tumblr.com",
    "tiktok":        "https://www.tiktok.com",
    "snapchat":      "https://www.snapchat.com",
    "paypal":        "https://www.paypal.com",
    "stripe":        "https://stripe.com",
    "shopify":       "https://www.shopify.com",
    "ebay":          "https://www.ebay.com",
    "etsy":          "https://www.etsy.com",
    "airbnb":        "https://www.airbnb.com",
    "uber":          "https://www.uber.com",
    "lyft":          "https://www.lyft.com",
    "duolingo":      "https://www.duolingo.com",
    "coursera":      "https://www.coursera.org",
    "udemy":         "https://www.udemy.com",
    "edx":           "https://www.edx.org",
    "khanacademy":   "https://www.khanacademy.org",
    "arxiv":         "https://arxiv.org",
    "pubmed":        "https://pubmed.ncbi.nlm.nih.gov",
    "wolframalpha":  "https://www.wolframalpha.com",
}

# ---------------------------------------------------------------------------
# Known applications: maps canonical name → executable name / path hint.
# Used as fallback when Everything is not available.
# Values are Windows executable names (no path) — the OS adapter will
# resolve the actual path via PATH or registry.
# ---------------------------------------------------------------------------
_KNOWN_APPS: Dict[str, str] = {
    # Browsers
    "chrome":       "chrome.exe",
    "firefox":      "firefox.exe",
    "edge":         "msedge.exe",
    "brave":        "brave.exe",
    "opera":        "opera.exe",
    "vivaldi":      "vivaldi.exe",

    # Editors / IDEs
    "vscode":       "code.exe",
    "notepad":      "notepad.exe",
    "notepad++":    "notepad++.exe",
    "sublime":      "sublime_text.exe",
    "atom":         "atom.exe",
    "vim":          "vim.exe",
    "pycharm":      "pycharm64.exe",
    "intellij":     "idea64.exe",
    "webstorm":     "webstorm64.exe",
    "clion":        "clion64.exe",
    "rider":        "rider64.exe",
    "eclipse":      "eclipse.exe",
    "netbeans":     "netbeans64.exe",
    "androidstudio": "studio64.exe",

    # Terminals
    "cmd":          "cmd.exe",
    "powershell":   "powershell.exe",
    "wt":           "wt.exe",
    "windowsterminal": "wt.exe",
    "git bash":     "git-bash.exe",
    "hyper":        "hyper.exe",

    # File managers
    "explorer":     "explorer.exe",

    # Media
    "vlc":          "vlc.exe",
    "spotify":      "spotify.exe",
    "itunes":       "itunes.exe",
    "winamp":       "winamp.exe",
    "foobar2000":   "foobar2000.exe",
    "mpv":          "mpv.exe",
    "mpc":          "mpc-hc64.exe",

    # Communication
    "discord":      "discord.exe",
    "slack":        "slack.exe",
    "teams":        "teams.exe",
    "zoom":         "zoom.exe",
    "skype":        "skype.exe",
    "telegram":     "telegram.exe",
    "signal":       "signal.exe",
    "whatsapp":     "whatsapp.exe",

    # Productivity
    "winword":      "winword.exe",
    "excel":        "excel.exe",
    "powerpnt":     "powerpnt.exe",
    "onenote":      "onenote.exe",
    "outlook":      "outlook.exe",
    "access":       "msaccess.exe",
    "publisher":    "mspub.exe",
    "libreoffice":  "soffice.exe",

    # System tools
    "taskmgr":      "taskmgr.exe",
    "regedit":      "regedit.exe",
    "control":      "control.exe",
    "mspaint":      "mspaint.exe",
    "calculator":   "calc.exe",
    "snipping":     "snippingtool.exe",
    "wordpad":      "wordpad.exe",
    "paint3d":      "paint3d.exe",
    "photos":       "photos.exe",
    "camera":       "windowscamera.exe",
    "maps":         "windowsmaps.exe",
    "mail":         "hxmail.exe",
    "calendar":     "hxcal.exe",
    "weather":      "bingweather.exe",
    "news":         "bingnews.exe",
    "xbox":         "xboxapp.exe",
    "store":        "winstore.app.exe",
    "cortana":      "searchui.exe",

    # Dev tools
    "git":          "git.exe",
    "docker":       "docker desktop.exe",
    "postman":      "postman.exe",
    "insomnia":     "insomnia.exe",
    "dbeaver":      "dbeaver.exe",
    "tableplus":    "tableplus.exe",
    "sequel pro":   "sequelpro.exe",
    "filezilla":    "filezilla.exe",
    "putty":        "putty.exe",
    "winscp":       "winscp.exe",
    "wireshark":    "wireshark.exe",

    # Creative
    "photoshop":    "photoshop.exe",
    "illustrator":  "illustrator.exe",
    "premiere":     "premiere pro.exe",
    "aftereffects": "afterfx.exe",
    "audition":     "adobe audition.exe",
    "lightroom":    "lightroom.exe",
    "gimp":         "gimp-2.10.exe",
    "inkscape":     "inkscape.exe",
    "blender":      "blender.exe",
    "obs":          "obs64.exe",
    "davinci":      "resolve.exe",

    # Games / launchers
    "steam":        "steam.exe",
    "epicgames":    "epicgameslauncher.exe",
    "gog":          "gogalaxy.exe",
    "origin":       "origin.exe",
    "battlenet":    "battle.net.exe",
    "ubisoft":      "ubisoftconnect.exe",
}

# ---------------------------------------------------------------------------
# Web-only targets: names that should ALWAYS resolve to a website,
# even if a local app with the same name exists.
# ---------------------------------------------------------------------------
_WEB_ONLY: set = {
    "tinkercad", "figma", "canva", "notion", "trello", "jira",
    "confluence", "chatgpt", "claude", "perplexity", "colab",
    "replit", "codepen", "jsfiddle", "medium", "dev.to", "hashnode",
    "producthunt", "hackernews", "arxiv", "pubmed", "wolframalpha",
    "duolingo", "coursera", "udemy", "edx", "khanacademy",
    "huggingface", "kaggle",
}


class TargetResolver:
    """
    Deterministic resolution pipeline for open/launch targets.

    Resolution order:
      1. Check _WEB_ONLY set → website
      2. Check _KNOWN_WEBSITES → website
      3. Try Everything CLI (es.exe) → application path
      4. Check _KNOWN_APPS (fuzzy fallback) → application name
      5. Fall back to web_search (NOT URL guessing)
      6. If all else fails → unknown (structured failure)

    All decisions are rule-based. No LLM. No URL guessing.
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._es_path: Optional[str] = self._find_everything_cli()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, target: str) -> ResolutionResult:
        """
        Resolve a target string to a typed ResolutionResult.

        Args:
            target: Normalized target name (e.g. "spotify", "vscode", "tinkercad")

        Returns:
            ResolutionResult with type, value, and optional meta.
        """
        if not target or not target.strip():
            return ResolutionResult(
                type="unknown",
                value=target,
                meta={"reason": "EMPTY_TARGET", "stage": "resolution"}
            )

        target = target.strip().lower()
        self._log(f"Resolving target: '{target}'")

        # Step 1: Web-only targets (always open as website)
        if target in _WEB_ONLY:
            url = _KNOWN_WEBSITES.get(target, "")
            if url:
                self._log(f"Web-only target → {url}")
                return ResolutionResult(
                    type="website",
                    value=url,
                    meta={"source": "web_only_list", "target": target}
                )

        # Step 2: Known website lookup
        if target in _KNOWN_WEBSITES:
            url = _KNOWN_WEBSITES[target]
            self._log(f"Known website → {url}")
            return ResolutionResult(
                type="website",
                value=url,
                meta={"source": "known_websites", "target": target}
            )

        # Step 3: Everything CLI search (Windows only)
        if self._es_path:
            result = self._search_everything(target)
            if result:
                self._log(f"Everything CLI found → {result}")
                return ResolutionResult(
                    type="application",
                    value=result,
                    meta={"source": "everything_cli", "target": target}
                )

        # Step 4: Known apps fallback (fuzzy match on curated list)
        app_result = self._fuzzy_app_lookup(target)
        if app_result:
            self._log(f"Known apps match → {app_result}")
            return ResolutionResult(
                type="application",
                value=app_result,
                meta={"source": "known_apps", "target": target}
            )

        # Step 5: Web search fallback (NOT URL guessing)
        self._log(f"No match found — falling back to web search for '{target}'")
        return ResolutionResult(
            type="web_search",
            value=target,
            meta={
                "source": "web_search_fallback",
                "target": target,
                "reason": "APPLICATION_NOT_FOUND"
            }
        )

    def failure_result(self, target: str, stage: str = "resolution") -> dict:
        """
        Return a structured failure dict (for debugger / future use).

        This is used when type == "unknown" and the caller wants a
        machine-readable failure record.
        """
        return {
            "status": "failure",
            "reason": "APPLICATION_NOT_FOUND",
            "input": target,
            "stage": stage
        }

    # ------------------------------------------------------------------
    # Everything CLI integration
    # ------------------------------------------------------------------

    def _find_everything_cli(self) -> Optional[str]:
        """
        Locate es.exe (Everything CLI) on the system.

        Checks:
          1. PATH
          2. Common installation directories
        """
        # Check PATH first
        es = shutil.which("es.exe") or shutil.which("es")
        if es:
            self._log(f"Everything CLI found in PATH: {es}")
            return es

        # Common Windows installation paths
        common_paths = [
            r"C:\Program Files\Everything\es.exe",
            r"C:\Program Files (x86)\Everything\es.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Everything\es.exe"),
            r"C:\Tools\es.exe",
            r"C:\Utils\es.exe",
        ]
        for path in common_paths:
            if os.path.isfile(path):
                self._log(f"Everything CLI found at: {path}")
                return path

        self._log("Everything CLI (es.exe) not found — will use fallback")
        return None

    def _search_everything(self, target: str) -> Optional[str]:
        """
        Search for an executable using Everything CLI.

        Strategy:
          - Search for '<target>.exe'
          - Filter results to .exe files only
          - Rank by closest name match (deterministic scoring)
          - Return best match path, or None if nothing found

        Returns:
            Absolute path to best matching .exe, or None.
        """
        if not self._es_path:
            return None

        try:
            # Search for the target as an exe
            query = f"{target}.exe"
            result = subprocess.run(
                [self._es_path, query, "-n", "20"],  # limit to 20 results
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0 or not result.stdout.strip():
                self._log(f"Everything search returned no results for '{query}'")
                return None

            lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

            # Filter: only .exe files
            exe_lines = [l for l in lines if l.lower().endswith(".exe")]
            if not exe_lines:
                self._log("Everything results contained no .exe files")
                return None

            # Rank by name similarity (deterministic: exact > startswith > contains)
            target_lower = target.lower()
            best = self._rank_everything_results(exe_lines, target_lower)
            return best

        except subprocess.TimeoutExpired:
            self._log("Everything CLI search timed out")
            return None
        except Exception as e:
            self._log(f"Everything CLI error: {e}")
            return None

    def _rank_everything_results(self, paths: list, target: str) -> Optional[str]:
        """
        Rank Everything CLI results deterministically.

        Scoring (higher = better):
          3 — filename (without .exe) exactly matches target
          2 — filename starts with target
          1 — filename contains target
          0 — no match (excluded)

        Returns the highest-scoring path, or None if no path scores > 0.
        """
        scored = []
        for path in paths:
            filename = os.path.basename(path).lower().replace(".exe", "")
            if filename == target:
                score = 3
            elif filename.startswith(target):
                score = 2
            elif target in filename:
                score = 1
            else:
                score = 0

            if score > 0:
                scored.append((score, path))

        if not scored:
            return None

        # Sort descending by score, then ascending by path length (prefer shorter paths)
        scored.sort(key=lambda x: (-x[0], len(x[1])))
        return scored[0][1]

    # ------------------------------------------------------------------
    # Known-apps fuzzy fallback
    # ------------------------------------------------------------------

    def _fuzzy_app_lookup(self, target: str) -> Optional[str]:
        """
        Look up target in the curated _KNOWN_APPS dictionary.

        Matching order (deterministic):
          1. Exact match
          2. Target is a prefix of a known key
          3. Known key is a prefix of target
          4. Target is a substring of a known key

        Returns the executable name (e.g. "chrome.exe"), or None.
        """
        # Exact match
        if target in _KNOWN_APPS:
            return _KNOWN_APPS[target]

        # Prefix / substring matching
        candidates = []
        for key, exe in _KNOWN_APPS.items():
            if key.startswith(target) or target.startswith(key):
                # Score: longer common prefix = better
                common = len(os.path.commonprefix([target, key]))
                candidates.append((common, key, exe))
            elif target in key:
                candidates.append((len(target), key, exe))

        if candidates:
            # Sort by score descending, then key length ascending (prefer shorter/more specific)
            candidates.sort(key=lambda x: (-x[0], len(x[1])))
            return candidates[0][2]

        return None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str):
        if self.debug:
            print(f"[RESOLVER] {message}")
