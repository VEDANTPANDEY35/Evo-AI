"""
Browser automation tool for opening browser and performing searches.
Supports Chrome detection with fallback to default browser.
"""
import os
import platform
import subprocess
import webbrowser
from typing import Optional, Tuple
from pathlib import Path
import urllib.parse


class BrowserAutomation:
    """Handle browser operations with Chrome/Brave preference and fallback."""
    
    # Browser executable paths by platform (in order of preference)
    BROWSER_PATHS = {
        "Windows": [
            # Brave
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
            # Chrome
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ],
        "Darwin": [  # macOS
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ],
        "Linux": [
            "/usr/bin/brave-browser",
            "/usr/bin/brave",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser"
        ]
    }
    
    # Search engine URLs
    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q={}",
        "bing": "https://www.bing.com/search?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "brave": "https://search.brave.com/search?q={}"
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.platform = platform.system()
        self.browser_path = self._find_browser()
        self.browser_name = self._get_browser_name()
    
    def _log(self, message: str):
        if self.debug:
            print(f"[BROWSER] {message}")
    
    def _find_browser(self) -> Optional[str]:
        """Find browser executable on the system (Brave or Chrome)."""
        paths = self.BROWSER_PATHS.get(self.platform, [])
        
        for path in paths:
            if os.path.exists(path):
                browser_name = "Brave" if "brave" in path.lower() else "Chrome"
                self._log(f"Found {browser_name} at: {path}")
                return path
        
        self._log("No preferred browser found, will use default browser")
        return None
    
    def _get_browser_name(self) -> str:
        """Get the name of the detected browser."""
        if not self.browser_path:
            return "default browser"
        
        if "brave" in self.browser_path.lower():
            return "Brave"
        elif "chrome" in self.browser_path.lower():
            return "Chrome"
        else:
            return "browser"
    
    def sanitize_query(self, query: str) -> str:
        """
        Sanitize search query by removing sensitive information.
        """
        import re
        
        # Remove absolute paths
        sanitized = re.sub(r'[A-Za-z]:\\[^\s]+', '', query)
        sanitized = re.sub(r'/[^\s]+/[^\s]+', '', sanitized)
        
        # Remove potential API keys or tokens (long alphanumeric strings)
        sanitized = re.sub(r'\b[A-Za-z0-9]{32,}\b', '', sanitized)
        
        # Remove email addresses
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', sanitized)
        
        # Clean up extra whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()
    
    def build_search_url(self, query: str, engine: str = "google") -> str:
        """
        Build search URL for given query and engine.
        
        Args:
            query: Search query (will be sanitized)
            engine: Search engine name
        
        Returns:
            Complete search URL
        """
        # Sanitize query
        clean_query = self.sanitize_query(query)
        
        # URL encode
        encoded_query = urllib.parse.quote_plus(clean_query)
        
        # Get search engine template
        template = self.SEARCH_ENGINES.get(engine.lower(), self.SEARCH_ENGINES["google"])
        
        return template.format(encoded_query)
    
    def _find_browser_by_name(self, name: str) -> Optional[str]:
        """
        Find the executable path for a specific browser by canonical name.

        Args:
            name: Canonical browser name (chrome, brave, edge, firefox…)

        Returns:
            Full path to the executable, or None if not found.
        """
        name = name.lower().strip()
        paths = self.BROWSER_PATHS.get(self.platform, [])
        for path in paths:
            if name in path.lower() and os.path.exists(path):
                self._log(f"Found {name!r} at: {path}")
                return path
        self._log(f"Browser {name!r} not found on this system")
        return None

    def open_url(self, url: str, use_preferred: bool = True,
                 preferred_browser: Optional[str] = None) -> Tuple[bool, str]:
        """
        Open URL in browser.

        Args:
            url:               URL to open.
            use_preferred:     Try to use preferred browser (Brave/Chrome) if available.
            preferred_browser: Optional canonical browser name to use instead of the
                               auto-detected preferred browser.  Supplied by
                               ExecutionContext for workflow continuity.

        Returns:
            (success, message)
        """
        try:
            # Resolve which browser path to use
            browser_path = None
            browser_label = "default browser"

            if preferred_browser:
                # Caller explicitly requested a specific browser (ExecutionContext)
                browser_path = self._find_browser_by_name(preferred_browser)
                browser_label = preferred_browser.title() if browser_path else "default browser"
            elif use_preferred and self.browser_path:
                browser_path = self.browser_path
                browser_label = self.browser_name

            if browser_path:
                try:
                    if self.platform == "Windows":
                        subprocess.Popen([browser_path, url])
                    elif self.platform == "Darwin":
                        subprocess.Popen(["open", "-a", browser_path, url])
                    else:  # Linux
                        subprocess.Popen([browser_path, url])

                    self._log(f"Opened in {browser_label}: {url}")
                    return True, f"Opened in {browser_label}"

                except Exception as e:
                    self._log(f"{browser_label} launch failed: {e}, falling back to default")

            # Fallback to default browser
            webbrowser.open(url)
            self._log(f"Opened in default browser: {url}")
            return True, "Opened in default browser"

        except Exception as e:
            self._log(f"Error opening URL: {e}")
            return False, f"Error: {e}"

    def search(self, query: str, engine: str = "google",
               use_preferred: bool = True,
               preferred_browser: Optional[str] = None) -> Tuple[bool, str]:
        """
        Perform web search.

        Args:
            query:             Search query.
            engine:            Search engine to use.
            use_preferred:     Try to use preferred browser (Brave/Chrome) if available.
            preferred_browser: Optional canonical browser name (from ExecutionContext).

        Returns:
            (success, message)
        """
        search_url = self.build_search_url(query, engine)
        success, message = self.open_url(
            search_url,
            use_preferred=use_preferred,
            preferred_browser=preferred_browser,
        )
        if success:
            return True, f"Searching for '{query}' on {engine}"
        return False, message
    
    def open_website(self, url: str, use_preferred: bool = True) -> Tuple[bool, str]:
        """
        Open a specific website.
        
        Args:
            url: Website URL
            use_preferred: Try to use preferred browser (Brave/Chrome) if available
        
        Returns:
            (success, message)
        """
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return self.open_url(url, use_preferred)
    
    def get_browser_info(self) -> dict:
        """Get information about available browsers."""
        return {
            "platform": self.platform,
            "browser_available": self.browser_path is not None,
            "browser_name": self.browser_name,
            "browser_path": self.browser_path,
            "default_browser": "system default",
            "supported_engines": list(self.SEARCH_ENGINES.keys())
        }


# Tool registration helper
def register_browser_tools(registry):
    """Register browser automation tools in the tool registry."""
    from .tool_registry import ToolMetadata, ToolParameter, RiskLevel
    
    browser = BrowserAutomation()
    
    # Search tool
    registry.register_tool(ToolMetadata(
        name="open_browser_search",
        description="Open browser and search for a query",
        function=lambda query, engine="google": browser.search(query, engine),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                required=True,
                description="Search query (will be sanitized)"
            ),
            ToolParameter(
                name="engine",
                type="string",
                required=False,
                default="google",
                description="Search engine to use",
                allowed_values=["google", "bing", "duckduckgo", "brave"]
            )
        ],
        risk_level=RiskLevel.SAFE,
        permissions_required=["open_browser"],
        os_support=["windows", "linux", "darwin"],
        category="browser",
        examples=[
            "open_browser_search(query='python tutorials')",
            "open_browser_search(query='weather forecast', engine='duckduckgo')"
        ]
    ))
    
    # Open website tool
    registry.register_tool(ToolMetadata(
        name="open_website",
        description="Open a specific website in browser",
        function=lambda url: browser.open_website(url),
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                required=True,
                description="Website URL to open"
            )
        ],
        risk_level=RiskLevel.SAFE,
        permissions_required=["open_browser"],
        os_support=["windows", "linux", "darwin"],
        category="browser",
        examples=[
            "open_website(url='github.com')",
            "open_website(url='https://python.org')"
        ]
    ))
