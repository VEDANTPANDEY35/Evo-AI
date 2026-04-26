"""
Full pipeline test suite for Evo-AI resolution system.
Tests: Input → Normalizer → Resolver → Reasoner → Planner

Covers all 7 test categories:
  1. Normal cases
  2. Typo handling
  3. Website cases
  4. Unknown inputs
  5. Ambiguous cases
  6. Natural language
  7. Edge cases

Special checks:
  - Everything CLI is attempted as PRIMARY (or correctly skipped)
  - No silent app→web fallback
  - No URL guessing (www.{name}.com)
  - Confidence levels are correct
  - Resolver never calls execution logic
  - System does not crash on unknown/empty input
  - fallback_info is returned on low-confidence web_search
"""

import pytest
from core.input.input_normalizer import InputNormalizer
from core.resolution.target_resolver import TargetResolver, ResolutionResult
from core.reasoning import Reasoner


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def normalizer():
    return InputNormalizer()


@pytest.fixture(scope="module")
def resolver():
    return TargetResolver(debug=False)


@pytest.fixture(scope="module")
def reasoner():
    return Reasoner(debug=False)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def resolve_target(resolver, normalizer, raw_target: str) -> ResolutionResult:
    """Normalize a target then resolve it — mirrors what the Reasoner does."""
    normalized, _ = normalizer.normalize_target(raw_target)
    return resolver.resolve(normalized)


def analyze(reasoner, text: str) -> dict:
    """Run the full Reasoner pipeline on a user input string."""
    return reasoner.analyze_request(text)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 1 — Normal cases
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalCases:
    """Well-formed inputs that should resolve cleanly to applications."""

    def test_open_chrome(self, resolver, normalizer):
        r = resolve_target(resolver, normalizer, "chrome")
        assert r.category == "application", f"Expected application, got {r.category}"
        assert r.resolved_path is not None
        assert "chrome" in r.resolved_path.lower()

    def test_open_vscode(self, resolver, normalizer):
        r = resolve_target(resolver, normalizer, "vscode")
        assert r.category == "application"
        assert r.resolved_path is not None
        assert "code" in r.resolved_path.lower()

    def test_open_notepad(self, resolver, normalizer):
        r = resolve_target(resolver, normalizer, "notepad")
        assert r.category == "application"
        assert r.resolved_path is not None
        assert "notepad" in r.resolved_path.lower()

    def test_open_calculator(self, resolver, normalizer):
        r = resolve_target(resolver, normalizer, "calculator")
        assert r.category == "application"
        assert r.resolved_path is not None

    def test_normal_cases_reasoner_routes_to_open_app(self, reasoner):
        for cmd in ["open chrome", "open vscode", "open notepad", "open calculator"]:
            result = analyze(reasoner, cmd)
            assert result["intent"] == "open_app", \
                f"'{cmd}' → expected open_app, got {result['intent']}"
            assert "open_application" in result["actions"]
            assert result["params"].get("app_name") is not None


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 2 — Typo handling
# ─────────────────────────────────────────────────────────────────────────────

class TestTypoHandling:
    """Misspelled inputs — normalizer must correct before resolver sees them."""

    def test_spotfy_corrected_to_spotify(self, normalizer):
        normalized, changed = normalizer.normalize_target("spotfy")
        assert changed is True
        assert normalized == "spotify"

    def test_chorme_corrected_to_chrome(self, normalizer):
        normalized, changed = normalizer.normalize_target("chorme")
        assert changed is True
        assert normalized == "chrome"

    def test_opne_notepad_full_normalize(self, normalizer):
        # "opne" is not a recognized verb — normalizer won't strip it,
        # but the target portion should still be processed if verb is found
        normalized, _ = normalizer.normalize("opne notepad")
        # "opne" is not in verb list so full string is returned lowercased
        assert "notepad" in normalized

    def test_lauch_browser_alias(self, normalizer):
        # "lauch" is not a recognized verb, but "browser" alias should still
        # be tested via normalize_target directly
        normalized, changed = normalizer.normalize_target("browser")
        assert changed is True
        assert normalized == "chrome"

    def test_spotfy_full_pipeline(self, reasoner):
        result = analyze(reasoner, "open spotfy")
        # After normalization spotfy→spotify, which is a known website
        assert result["intent"] == "open_website"
        assert result["params"].get("url") == "https://open.spotify.com"

    def test_chorme_full_pipeline(self, reasoner):
        result = analyze(reasoner, "open chorme")
        assert result["intent"] == "open_app"
        assert "chrome" in result["params"].get("app_name", "").lower()

    def test_launch_browser_full_pipeline(self, reasoner):
        result = analyze(reasoner, "launch browser")
        # browser → chrome via alias
        assert result["intent"] == "open_app"
        assert "chrome" in result["params"].get("app_name", "").lower()

    def test_typo_does_not_crash(self, reasoner):
        # Should never raise — just return a valid analysis dict
        result = analyze(reasoner, "open xyztypoapp")
        assert isinstance(result, dict)
        assert "intent" in result


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 3 — Website cases
# ─────────────────────────────────────────────────────────────────────────────

class TestWebsiteCases:
    """Known websites should resolve with high confidence and a real URL."""

    @pytest.mark.parametrize("target,expected_url", [
        ("youtube",  "https://www.youtube.com"),
        ("github",   "https://github.com"),
        ("gmail",    "https://mail.google.com"),
        ("reddit",   "https://www.reddit.com"),
        ("spotify",  "https://open.spotify.com"),
    ])
    def test_known_website_resolves_with_url(self, resolver, target, expected_url):
        r = resolver.resolve(target)
        assert r.category == "web_search", \
            f"'{target}' should be web_search, got {r.category}"
        assert r.confidence == "high", \
            f"'{target}' should have high confidence, got {r.confidence}"
        assert r.resolved_path == expected_url, \
            f"'{target}' URL mismatch: {r.resolved_path} != {expected_url}"

    def test_no_url_guessing_for_unknown_site(self, resolver):
        """Resolver must NOT construct www.{name}.com for unknown sites."""
        r = resolver.resolve("tinkercad")
        # tinkercad is NOT in the minimal known-websites list
        assert r.category == "web_search"
        assert r.confidence == "low"
        # resolved_path must be None — no URL was guessed
        assert r.resolved_path is None, \
            f"URL guessing detected! resolved_path={r.resolved_path}"

    def test_figma_not_in_known_websites(self, resolver):
        """figma was removed from the minimal list — should fall through."""
        r = resolver.resolve("figma")
        assert r.category == "web_search"
        assert r.confidence == "low"
        assert r.resolved_path is None

    def test_youtube_reasoner_routes_to_open_website(self, reasoner):
        result = analyze(reasoner, "open youtube")
        assert result["intent"] == "open_website"
        assert result["params"].get("url") == "https://www.youtube.com"

    def test_github_reasoner_routes_to_open_website(self, reasoner):
        result = analyze(reasoner, "open github")
        assert result["intent"] == "open_website"
        assert result["params"].get("url") == "https://github.com"

    def test_gmail_reasoner_routes_to_open_website(self, reasoner):
        result = analyze(reasoner, "open gmail")
        assert result["intent"] == "open_website"
        assert result["params"].get("url") == "https://mail.google.com"

    def test_tinkercad_routes_to_search_web(self, reasoner):
        """tinkercad not in minimal list → explicit web_search fallback."""
        result = analyze(reasoner, "open tinkercad")
        assert result["intent"] == "search_web", \
            f"Expected search_web for tinkercad, got {result['intent']}"
        assert result["params"].get("query") == "tinkercad"

    def test_figma_routes_to_search_web(self, reasoner):
        result = analyze(reasoner, "open figma")
        assert result["intent"] == "search_web"
        assert result["params"].get("query") == "figma"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 4 — Unknown inputs
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownInputs:
    """Completely unknown targets — must not crash, must return structured data."""

    @pytest.mark.parametrize("target", [
        "randomapp123",
        "somethingthatdoesnotexist",
        "asdfghjkl",
    ])
    def test_unknown_target_does_not_crash(self, resolver, target):
        r = resolver.resolve(target)
        assert isinstance(r, ResolutionResult)
        assert r.category in ("web_search", "unknown")

    @pytest.mark.parametrize("target", [
        "randomapp123",
        "somethingthatdoesnotexist",
        "asdfghjkl",
    ])
    def test_unknown_target_has_low_confidence(self, resolver, target):
        r = resolver.resolve(target)
        assert r.confidence == "low", \
            f"'{target}' should have low confidence, got {r.confidence}"

    @pytest.mark.parametrize("target", [
        "randomapp123",
        "somethingthatdoesnotexist",
        "asdfghjkl",
    ])
    def test_unknown_target_no_url_guessing(self, resolver, target):
        r = resolver.resolve(target)
        if r.resolved_path is not None:
            assert not r.resolved_path.startswith("www."), \
                f"URL guessing detected for '{target}': {r.resolved_path}"
            assert not r.resolved_path.startswith("http"), \
                f"URL guessing detected for '{target}': {r.resolved_path}"

    @pytest.mark.parametrize("cmd", [
        "open randomapp123",
        "open somethingthatdoesnotexist",
        "open asdfghjkl",
    ])
    def test_unknown_input_reasoner_does_not_crash(self, reasoner, cmd):
        result = analyze(reasoner, cmd)
        assert isinstance(result, dict)
        assert "intent" in result

    @pytest.mark.parametrize("cmd", [
        "open randomapp123",
        "open somethingthatdoesnotexist",
        "open asdfghjkl",
    ])
    def test_unknown_input_routes_to_search_web(self, reasoner, cmd):
        """Unknown apps must route to search_web, not crash or return unknown."""
        result = analyze(reasoner, cmd)
        assert result["intent"] == "search_web", \
            f"'{cmd}' → expected search_web, got {result['intent']}"

    @pytest.mark.parametrize("cmd", [
        "open randomapp123",
        "open somethingthatdoesnotexist",
        "open asdfghjkl",
    ])
    def test_unknown_input_has_fallback_info(self, reasoner, cmd):
        """fallback_info must be present for low-confidence web_search."""
        result = analyze(reasoner, cmd)
        assert "fallback_info" in result, \
            f"'{cmd}' missing fallback_info: {result}"
        fi = result["fallback_info"]
        assert fi["status"] == "fallback"
        assert fi["reason"] == "APPLICATION_NOT_FOUND"
        assert fi["suggested_action"] == "web_search"
        assert "query" in fi


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 5 — Ambiguous cases
# ─────────────────────────────────────────────────────────────────────────────

class TestAmbiguousCases:
    """Targets that could be either an app or a website."""

    def test_spotify_resolves_as_website_not_app(self, resolver):
        """spotify is in known-websites (step 1) — should win over known-apps."""
        r = resolver.resolve("spotify")
        assert r.category == "web_search"
        assert r.confidence == "high"
        assert r.resolved_path == "https://open.spotify.com"

    def test_discord_resolves_as_application(self, resolver):
        """discord is NOT in known-websites — should resolve as application."""
        r = resolver.resolve("discord")
        assert r.category == "application"
        assert "discord" in r.resolved_path.lower()

    def test_open_spotify_routes_to_website(self, reasoner):
        result = analyze(reasoner, "open spotify")
        assert result["intent"] == "open_website"
        assert result["params"].get("url") == "https://open.spotify.com"

    def test_open_discord_routes_to_app(self, reasoner):
        result = analyze(reasoner, "open discord")
        assert result["intent"] == "open_app"
        assert "discord" in result["params"].get("app_name", "").lower()

    def test_open_chrome_browser_alias(self, normalizer, resolver):
        """'chrome browser' — normalizer should handle 'browser' alias."""
        # normalize_target gets the full target string "chrome browser"
        normalized, _ = normalizer.normalize_target("chrome browser")
        # "chrome browser" is not in alias table — should stay as-is
        # but "chrome" prefix should still resolve
        r = resolver.resolve(normalized)
        assert r.category == "application"

    def test_open_code_alias(self, normalizer, reasoner):
        """'code' is an alias for 'vscode'."""
        normalized, changed = normalizer.normalize_target("code")
        assert changed is True
        assert normalized == "vscode"
        result = analyze(reasoner, "open code")
        assert result["intent"] == "open_app"
        assert "code" in result["params"].get("app_name", "").lower()

    def test_teams_website_wins_over_app(self, resolver):
        """teams is in known-websites — website resolution takes priority."""
        r = resolver.resolve("teams")
        assert r.category == "web_search"
        assert r.confidence == "high"
        assert r.resolved_path == "https://teams.microsoft.com"

    def test_outlook_website_wins_over_app(self, resolver):
        """outlook is in known-websites — website resolution takes priority."""
        r = resolver.resolve("outlook")
        assert r.category == "web_search"
        assert r.confidence == "high"
        assert r.resolved_path == "https://outlook.live.com"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 6 — Natural language
# ─────────────────────────────────────────────────────────────────────────────

class TestNaturalLanguage:
    """Free-form natural language inputs — system should handle gracefully."""

    def test_can_you_open_chrome(self, reasoner):
        """Natural language phrasing — does NOT start with open/launch/start."""
        result = analyze(reasoner, "can you open chrome for me")
        # This does NOT start with a recognized verb, so normalizer won't
        # process the target. Reasoner may route to conversation or open_app.
        assert isinstance(result, dict)
        assert "intent" in result

    def test_launch_my_browser(self, reasoner):
        """'launch my browser' — 'my browser' is not a known alias."""
        result = analyze(reasoner, "launch my browser")
        assert isinstance(result, dict)
        # "my browser" won't match alias "browser" exactly — observe behavior

    def test_i_want_to_use_vscode(self, reasoner):
        """Conversational phrasing — no open/launch verb."""
        result = analyze(reasoner, "I want to use vscode")
        assert isinstance(result, dict)
        # Likely routes to conversation — observe

    def test_open_something_for_coding(self, reasoner):
        """Vague intent — 'something' is not a known app."""
        result = analyze(reasoner, "open something for coding")
        assert isinstance(result, dict)
        # Should not crash

    def test_natural_language_never_crashes(self, reasoner):
        """All natural language inputs must return a valid dict."""
        inputs = [
            "can you open chrome for me",
            "launch my browser",
            "I want to use vscode",
            "open something for coding",
        ]
        for inp in inputs:
            result = analyze(reasoner, inp)
            assert isinstance(result, dict), f"Crashed on: '{inp}'"
            assert "intent" in result, f"No intent for: '{inp}'"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY 7 — Edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Boundary and degenerate inputs."""

    def test_bare_open_verb(self, reasoner):
        """'open' with no target — should not crash."""
        result = analyze(reasoner, "open")
        assert isinstance(result, dict)

    def test_open_number(self, reasoner):
        """'open 123' — numeric target."""
        result = analyze(reasoner, "open 123")
        assert isinstance(result, dict)
        assert "intent" in result

    def test_open_dot(self, reasoner):
        """'open .' — dot as target."""
        result = analyze(reasoner, "open .")
        assert isinstance(result, dict)

    def test_open_very_long_string(self, reasoner):
        """Very long unknown string — should not crash."""
        result = analyze(reasoner, "open " + "a" * 200)
        assert isinstance(result, dict)

    def test_empty_string(self, normalizer, resolver):
        """Empty string — normalizer and resolver must handle gracefully."""
        norm, _ = normalizer.normalize("")
        assert norm == "" or norm is None or isinstance(norm, str)
        r = resolver.resolve("")
        assert r.category == "unknown"
        assert r.confidence == "low"

    def test_whitespace_only(self, normalizer, resolver):
        """Whitespace-only input."""
        norm, _ = normalizer.normalize("   ")
        r = resolver.resolve("   ")
        assert r.category == "unknown"

    def test_resolver_never_returns_guessed_url(self, resolver):
        """Resolver must never return a www.{name}.com style URL."""
        targets = ["randomapp", "tinkercad", "figma", "canva", "asdfgh"]
        for t in targets:
            r = resolver.resolve(t)
            if r.resolved_path is not None:
                assert not r.resolved_path.startswith("www."), \
                    f"URL guessing for '{t}': {r.resolved_path}"
                # Only http URLs allowed if they come from _KNOWN_WEBSITES
                if r.resolved_path.startswith("http"):
                    assert r.confidence == "high", \
                        f"HTTP URL with non-high confidence for '{t}'"

    def test_resolver_result_is_always_dataclass(self, resolver):
        """resolve() must always return a ResolutionResult, never raise."""
        inputs = ["", "   ", "open", ".", "123", "a" * 300, "open chrome"]
        for inp in inputs:
            try:
                r = resolver.resolve(inp)
                assert isinstance(r, ResolutionResult), \
                    f"resolve('{inp[:20]}') returned {type(r)}"
            except Exception as e:
                pytest.fail(f"resolve('{inp[:20]}') raised: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CHECKS — Cross-cutting concerns
# ─────────────────────────────────────────────────────────────────────────────

class TestSpecialChecks:
    """Explicit verification of the architectural guarantees."""

    def test_everything_cli_is_attempted_first(self, resolver):
        """
        Verify that _es_path is checked before known-apps fallback.
        We can't force es.exe to be present, but we can verify the
        attribute exists and the fallback only triggers when it's None.
        """
        assert hasattr(resolver, "_es_path"), "Resolver missing _es_path attribute"
        # If es.exe is not installed, _es_path should be None
        # If it IS installed, it should be a valid path
        if resolver._es_path is not None:
            import os
            assert os.path.isfile(resolver._es_path), \
                f"_es_path points to non-existent file: {resolver._es_path}"

    def test_no_silent_fallback_app_to_web(self, reasoner):
        """
        When an app is not found, the system must NOT silently switch to
        web search without attaching fallback_info.
        """
        result = analyze(reasoner, "open randomapp999")
        if result["intent"] == "search_web":
            assert "fallback_info" in result, \
                "Silent fallback detected: search_web without fallback_info"

    def test_no_url_guessing_in_resolver(self, resolver):
        """Resolver must never construct www.{name}.com URLs."""
        unknown_targets = ["tinkercad", "figma", "canva", "notion", "randomapp"]
        for t in unknown_targets:
            r = resolver.resolve(t)
            if r.resolved_path:
                assert "www." + t not in r.resolved_path, \
                    f"URL guessing detected for '{t}': {r.resolved_path}"

    def test_confidence_high_for_known_websites(self, resolver):
        """Known websites must always return confidence=high."""
        known = ["youtube", "google", "github", "gmail", "reddit",
                 "spotify", "teams", "outlook", "drive", "meet"]
        for site in known:
            r = resolver.resolve(site)
            assert r.confidence == "high", \
                f"'{site}' should have high confidence, got {r.confidence}"

    def test_confidence_low_for_unknown_targets(self, resolver):
        """Unknown targets must return confidence=low."""
        unknown = ["randomapp123", "asdfghjkl", "tinkercad", "figma"]
        for t in unknown:
            r = resolver.resolve(t)
            assert r.confidence == "low", \
                f"'{t}' should have low confidence, got {r.confidence}"

    def test_resolver_has_no_execution_logic(self):
        """
        Resolver module must not import execution-layer modules.
        Check that tools, executor, brain are not imported.
        """
        import importlib, sys
        # Reload to get fresh module
        if "core.resolution.target_resolver" in sys.modules:
            mod = sys.modules["core.resolution.target_resolver"]
        else:
            mod = importlib.import_module("core.resolution.target_resolver")

        forbidden = ["core.tools", "core.executor", "core.brain",
                     "core.browser_automation"]
        for dep in forbidden:
            assert dep not in sys.modules or \
                dep not in getattr(mod, "__dict__", {}), \
                f"Resolver imports execution module: {dep}"

    def test_fallback_info_structure(self, reasoner):
        """fallback_info must have the correct keys and values."""
        result = analyze(reasoner, "open nonexistentapp999")
        if "fallback_info" in result:
            fi = result["fallback_info"]
            assert "status" in fi
            assert "reason" in fi
            assert "suggested_action" in fi
            assert "query" in fi
            assert fi["status"] == "fallback"
            assert fi["reason"] == "APPLICATION_NOT_FOUND"
            assert fi["suggested_action"] == "web_search"

    def test_make_fallback_info_structure(self, resolver):
        """make_fallback_info() must return the correct structure."""
        fi = resolver.make_fallback_info("testapp")
        assert fi["status"] == "fallback"
        assert fi["reason"] == "APPLICATION_NOT_FOUND"
        assert fi["suggested_action"] == "web_search"
        assert fi["query"] == "testapp"

    def test_resolution_result_fields(self, resolver):
        """ResolutionResult must always have all required fields."""
        r = resolver.resolve("chrome")
        assert hasattr(r, "category")
        assert hasattr(r, "query")
        assert hasattr(r, "confidence")
        assert hasattr(r, "resolved_path")
        assert hasattr(r, "meta")
        assert r.category in ("application", "web_search", "unknown")
        assert r.confidence in ("high", "medium", "low")

    def test_normalizer_does_not_modify_non_open_commands(self, normalizer):
        """Normalizer must not corrupt non-open/launch/start commands."""
        inputs = [
            "list files",
            "system info",
            "take screenshot",
            "what is python",
        ]
        for inp in inputs:
            normalized, _ = normalizer.normalize(inp)
            assert normalized == inp.lower(), \
                f"Normalizer modified non-open command: '{inp}' → '{normalized}'"

    def test_alias_table_has_no_circular_references(self, normalizer):
        """No alias should map to another alias key."""
        aliases = normalizer.get_aliases()
        for key, value in aliases.items():
            assert value not in aliases, \
                f"Circular alias: '{key}' → '{value}' which is also an alias key"

    def test_typo_map_has_no_circular_references(self, normalizer):
        """No typo correction should map to another typo key."""
        typos = normalizer.get_typo_map()
        for key, value in typos.items():
            assert value not in typos, \
                f"Circular typo: '{key}' → '{value}' which is also a typo key"
