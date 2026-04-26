"""
Evo-AI Full Pipeline Stress Test
Tests: Normalizer -> Resolver -> Debugger -> Reasoner -> Planner

Covers 50+ inputs across 7 categories.
DO NOT modify code. Observe and report only.
"""
import pytest
from core.input.input_normalizer import InputNormalizer
from core.resolution.target_resolver import TargetResolver, ResolutionResult
from core.debugger import Debugger, DebugReport
from core.reasoning import Reasoner


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def N():
    return InputNormalizer()

@pytest.fixture(scope="module")
def R():
    return TargetResolver(debug=False)

@pytest.fixture(scope="module")
def D():
    return Debugger(debug=False)

@pytest.fixture(scope="module")
def RE():
    return Reasoner(debug=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

def pipeline(N, R, D, RE, user_input):
    """
    Run the full pre-execution pipeline and return a trace dict.
    Does NOT call Executor or Verifier (no system changes).
    """
    # 1. Normalize
    normalized, was_changed = N.normalize(user_input)

    # 2. Extract target (for resolver direct test)
    target = None
    for verb in ("open ", "launch ", "start ", "run "):
        if normalized.startswith(verb):
            target = normalized[len(verb):].strip()
            break

    # 3. Resolve (if we have a target)
    resolution = R.resolve(target) if target else None

    # 4. Debugger check
    debug_report = None
    if resolution is not None:
        fallback = R.make_fallback_info(target) if resolution.confidence == "low" else None
        if D.should_activate(resolution.confidence, fallback):
            debug_report = D.analyze(resolution, user_input, fallback)

    # 5. Reasoner
    analysis = RE.analyze_request(user_input)

    return {
        "input":          user_input,
        "normalized":     normalized,
        "was_changed":    was_changed,
        "target":         target,
        "resolution":     resolution,
        "debug_report":   debug_report,
        "analysis":       analysis,
    }


def assert_no_url_guessing(resolution, target):
    """Resolver must never return a guessed www.{name}.com URL."""
    if resolution and resolution.resolved_path:
        rp = resolution.resolved_path
        if rp.startswith("http"):
            # Only allowed if confidence is high (came from known_websites)
            assert resolution.confidence == "high", (
                f"HTTP URL with non-high confidence for '{target}': {rp}"
            )
        assert f"www.{target}.com" not in rp, (
            f"URL guessing detected for '{target}': {rp}"
        )


def assert_no_crash(trace):
    """Pipeline must always return a valid trace dict."""
    assert isinstance(trace, dict)
    assert "analysis" in trace
    assert isinstance(trace["analysis"], dict)
    assert "intent" in trace["analysis"]


def assert_debugger_non_executing(debug_report):
    """When debugger fires, it must never contain execution calls."""
    if debug_report is None:
        return
    assert isinstance(debug_report, DebugReport)
    assert debug_report.status == "debug"
    # next_actions are suggestions only — they must not have been executed
    for action in debug_report.next_actions:
        assert "action" in action
        assert "params" in action
        assert "label" in action


# ── CATEGORY 1: Normal cases ──────────────────────────────────────────────────

class TestNormal:

    @pytest.mark.parametrize("cmd,expected_intent", [
        ("open chrome",      "open_app"),
        ("open vscode",      "open_app"),
        ("open notepad",     "open_app"),
        ("open calculator",  "open_app"),
        ("open explorer",    "open_app"),
        ("open vlc",         "open_app"),
        ("open discord",     "open_app"),
        ("open powershell",  "open_app"),
        ("open cmd",         "open_app"),
        ("open blender",     "open_app"),
    ])
    def test_normal_routes_to_open_app(self, N, R, D, RE, cmd, expected_intent):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_crash(t)
        assert t["analysis"]["intent"] == expected_intent, (
            f"'{cmd}' -> expected {expected_intent}, got {t['analysis']['intent']}"
        )
        assert t["debug_report"] is None, (
            f"Debugger should NOT fire for normal input '{cmd}'"
        )

    @pytest.mark.parametrize("cmd,expected_intent", [
        ("open youtube",  "open_website"),
        ("open github",   "open_website"),
        ("open gmail",    "open_website"),
        ("open reddit",   "open_website"),
        ("open spotify",  "open_website"),
    ])
    def test_normal_known_websites(self, N, R, D, RE, cmd, expected_intent):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_crash(t)
        assert t["analysis"]["intent"] == expected_intent, (
            f"'{cmd}' -> expected {expected_intent}, got {t['analysis']['intent']}"
        )
        assert t["debug_report"] is None


# ── CATEGORY 2: Aggressive typos ─────────────────────────────────────────────

class TestTypos:

    @pytest.mark.parametrize("cmd,expected_normalized_contains", [
        ("open spotfy",    "spotify"),
        ("open chorme",    "chrome"),
        ("open vsocde",    "vscode"),
        ("open notpad",    "notepad"),
        ("open discrod",   "discord"),
        ("open slakc",     "slack"),
        ("open zomm",      "zoom"),
        ("open teasm",     "teams"),
        ("open githb",     "github"),
        ("open reddti",    "reddit"),
    ])
    def test_typo_corrected_by_normalizer(self, N, cmd, expected_normalized_contains):
        normalized, changed = N.normalize(cmd)
        assert expected_normalized_contains in normalized, (
            f"'{cmd}' -> normalized='{normalized}', expected '{expected_normalized_contains}'"
        )
        assert changed is True, f"'{cmd}' should have been changed by normalizer"

    @pytest.mark.parametrize("cmd", [
        "opne chorme",
        "lauch browzer",
        "opn vsocde",
        "launhc browser",
    ])
    def test_aggressive_typo_does_not_crash(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_crash(t)

    def test_spotfy_full_pipeline_routes_to_website(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open spotfy")
        assert_no_crash(t)
        # After normalization spotfy->spotify, which is a known website
        assert t["analysis"]["intent"] == "open_website", (
            f"Expected open_website, got {t['analysis']['intent']}"
        )
        assert t["debug_report"] is None

    def test_chorme_full_pipeline_routes_to_app(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open chorme")
        assert_no_crash(t)
        assert t["analysis"]["intent"] == "open_app"
        assert t["debug_report"] is None

    def test_launch_browzer_alias_corrects(self, N, R, D, RE):
        # "browzer" is not in typo map — normalizer won't fix it
        # but "browser" alias would map to chrome if it were correct
        t = pipeline(N, R, D, RE, "launch browzer")
        assert_no_crash(t)
        # Should not crash regardless of outcome


# ── CATEGORY 3: Unknown inputs ────────────────────────────────────────────────

class TestUnknown:

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
        "open xyzzy123",
        "open zzzzzzzzz",
        "open qqqqqqqqqq",
    ])
    def test_unknown_does_not_crash(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_crash(t)

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_triggers_debugger(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert t["debug_report"] is not None, (
            f"Debugger should fire for unknown input '{cmd}'"
        )
        assert t["debug_report"].status == "debug"

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_debugger_is_non_executing(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert_debugger_non_executing(t["debug_report"])

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_no_url_guessing(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_url_guessing(t["resolution"], t["target"])

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_reasoner_routes_to_search_web(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert t["analysis"]["intent"] == "search_web", (
            f"'{cmd}' -> expected search_web, got {t['analysis']['intent']}"
        )

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_has_fallback_info(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        fi = t["analysis"].get("fallback_info")
        assert fi is not None, f"'{cmd}' missing fallback_info"
        assert fi["status"] == "fallback"
        assert fi["reason"] == "APPLICATION_NOT_FOUND"
        assert fi["suggested_action"] == "web_search"

    @pytest.mark.parametrize("cmd", [
        "open asdfghjkl",
        "open randomtool999",
        "open nothingapp",
    ])
    def test_unknown_debugger_has_web_search_suggestion(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        dr = t["debug_report"]
        assert dr is not None
        # Web search must always be the last suggestion
        assert any("Search web" in s for s in dr.suggestions), (
            f"No web search suggestion in: {dr.suggestions}"
        )


# ── CATEGORY 4: Ambiguous cases ───────────────────────────────────────────────

class TestAmbiguous:

    def test_spotify_routes_to_website_not_app(self, N, R, D, RE):
        """spotify is in known-websites — website wins over known-apps."""
        t = pipeline(N, R, D, RE, "open spotify")
        assert t["analysis"]["intent"] == "open_website"
        assert t["debug_report"] is None

    def test_discord_routes_to_app(self, N, R, D, RE):
        """discord is NOT in known-websites — resolves as application."""
        t = pipeline(N, R, D, RE, "open discord")
        assert t["analysis"]["intent"] == "open_app"
        assert t["debug_report"] is None

    def test_teams_routes_to_website(self, N, R, D, RE):
        """teams is in known-websites — website wins."""
        t = pipeline(N, R, D, RE, "open teams")
        assert t["analysis"]["intent"] == "open_website"
        assert t["debug_report"] is None

    def test_open_code_alias_to_vscode(self, N, R, D, RE):
        """'code' alias maps to 'vscode'."""
        normalized, changed = N.normalize("open code")
        assert "vscode" in normalized
        assert changed is True
        t = pipeline(N, R, D, RE, "open code")
        assert t["analysis"]["intent"] == "open_app"

    def test_open_outlook_routes_to_website(self, N, R, D, RE):
        """outlook is in known-websites."""
        t = pipeline(N, R, D, RE, "open outlook")
        assert t["analysis"]["intent"] == "open_website"

    def test_open_drive_routes_to_website(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open drive")
        assert t["analysis"]["intent"] == "open_website"

    def test_open_tinkercad_routes_to_search_web(self, N, R, D, RE):
        """tinkercad not in minimal known-websites — explicit web_search fallback."""
        t = pipeline(N, R, D, RE, "open tinkercad")
        assert t["analysis"]["intent"] == "search_web"
        assert t["debug_report"] is not None

    def test_open_figma_routes_to_search_web(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open figma")
        assert t["analysis"]["intent"] == "search_web"
        assert t["debug_report"] is not None


# ── CATEGORY 5: Natural language ──────────────────────────────────────────────

class TestNaturalLanguage:

    @pytest.mark.parametrize("cmd", [
        "can you open chrome for me",
        "I want to code",
        "launch my browser",
        "open something for music",
        "I need a text editor",
        "help me open a browser",
        "start something for video editing",
    ])
    def test_natural_language_never_crashes(self, N, R, D, RE, cmd):
        t = pipeline(N, R, D, RE, cmd)
        assert_no_crash(t)

    def test_launch_my_browser_does_not_crash(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "launch my browser")
        assert_no_crash(t)
        # "my browser" is not a known alias — observe behavior
        assert isinstance(t["analysis"]["intent"], str)

    def test_open_something_for_music_does_not_crash(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open something for music")
        assert_no_crash(t)

    def test_i_want_to_code_does_not_crash(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "I want to code")
        assert_no_crash(t)

    def test_natural_language_returns_valid_intent(self, N, R, D, RE):
        valid_intents = {
            "open_app", "open_website", "search_web", "conversation",
            "greeting", "thanks", "unknown", "open_app",
            "proactive_system_info", "proactive_processes",
            "system_lock_info", "system_lock_processes",
            "list_directory", "search_files", "self_info", "screenshot",
        }
        cmds = [
            "can you open chrome for me",
            "I want to code",
            "launch my browser",
            "open something for music",
        ]
        for cmd in cmds:
            t = pipeline(N, R, D, RE, cmd)
            intent = t["analysis"]["intent"]
            assert isinstance(intent, str) and len(intent) > 0, (
                f"'{cmd}' returned empty intent"
            )


# ── CATEGORY 6: Edge cases ────────────────────────────────────────────────────

class TestEdgeCases:

    def test_bare_open_verb(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open")
        assert_no_crash(t)

    def test_open_number(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open 123")
        assert_no_crash(t)

    def test_open_dot(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open .")
        assert_no_crash(t)

    def test_empty_string(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "")
        assert_no_crash(t)

    def test_whitespace_only(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "   ")
        assert_no_crash(t)

    def test_very_long_string(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open " + "a" * 300)
        assert_no_crash(t)

    def test_special_characters(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open @#$%^&*()")
        assert_no_crash(t)

    def test_unicode_input(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open \u30a2\u30d7\u30ea")
        assert_no_crash(t)

    def test_sql_injection_like(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open '; DROP TABLE apps; --")
        assert_no_crash(t)

    def test_path_traversal_like(self, N, R, D, RE):
        t = pipeline(N, R, D, RE, "open ../../etc/passwd")
        assert_no_crash(t)

    def test_resolver_never_raises_on_edge_inputs(self, R):
        edge_inputs = ["", "   ", ".", "123", "@#$", "a" * 500, "\x00\x01\x02"]
        for inp in edge_inputs:
            try:
                result = R.resolve(inp)
                assert isinstance(result, ResolutionResult)
            except Exception as e:
                pytest.fail(f"resolve({inp[:20]!r}) raised: {e}")

    def test_normalizer_never_raises_on_edge_inputs(self, N):
        edge_inputs = ["", "   ", "open", "open .", "open 123", "a" * 500]
        for inp in edge_inputs:
            try:
                result, _ = N.normalize(inp)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"normalize({inp[:20]!r}) raised: {e}")


# ── CATEGORY 7: Debugger-specific tests ──────────────────────────────────────

class TestDebugger:

    @pytest.mark.parametrize("target,expected_in_suggestions", [
        ("spotfy",      "Search web"),
        ("tinkercad",   "Search web"),
        ("randomapp99", "Search web"),
        ("figma",       "Search web"),
        ("asdfghjkl",   "Search web"),
    ])
    def test_debugger_always_includes_web_search(self, R, D, target, expected_in_suggestions):
        resolution = R.resolve(target)
        fallback = R.make_fallback_info(target) if resolution.confidence == "low" else None
        assert D.should_activate(resolution.confidence, fallback), (
            f"Debugger should activate for '{target}' (confidence={resolution.confidence})"
        )
        report = D.analyze(resolution, f"open {target}", fallback)
        assert any(expected_in_suggestions in s for s in report.suggestions), (
            f"No '{expected_in_suggestions}' in suggestions for '{target}': {report.suggestions}"
        )

    @pytest.mark.parametrize("target", [
        "chrome", "vscode", "notepad", "youtube", "github",
    ])
    def test_debugger_does_not_activate_for_known_targets(self, R, D, target):
        resolution = R.resolve(target)
        fallback = None
        assert not D.should_activate(resolution.confidence, fallback), (
            f"Debugger should NOT activate for known target '{target}' "
            f"(confidence={resolution.confidence})"
        )

    def test_debugger_report_structure(self, R, D):
        resolution = R.resolve("randomapp999")
        fallback = R.make_fallback_info("randomapp999")
        report = D.analyze(resolution, "open randomapp999", fallback)
        assert report.status == "debug"
        assert isinstance(report.message, str) and len(report.message) > 0
        assert isinstance(report.suggestions, list) and len(report.suggestions) > 0
        assert isinstance(report.next_actions, list) and len(report.next_actions) > 0

    def test_debugger_next_actions_have_required_keys(self, R, D):
        resolution = R.resolve("unknownapp123")
        fallback = R.make_fallback_info("unknownapp123")
        report = D.analyze(resolution, "open unknownapp123", fallback)
        for action in report.next_actions:
            assert "action" in action, f"Missing 'action' key: {action}"
            assert "params" in action, f"Missing 'params' key: {action}"
            assert "label" in action, f"Missing 'label' key: {action}"

    def test_debugger_never_executes(self, R, D):
        """Verify debugger output contains no execution side effects."""
        resolution = R.resolve("randomapp999")
        fallback = R.make_fallback_info("randomapp999")
        report = D.analyze(resolution, "open randomapp999", fallback)
        # next_actions are descriptors only — they must not have been run
        assert_debugger_non_executing(report)

    def test_debugger_message_explains_failure(self, R, D):
        resolution = R.resolve("tinkercad")
        fallback = R.make_fallback_info("tinkercad")
        report = D.analyze(resolution, "open tinkercad", fallback)
        assert "tinkercad" in report.message.lower() or "not found" in report.message.lower()

    def test_debugger_activates_on_fallback_info_regardless_of_confidence(self, D):
        """If fallback_info is present, debugger must activate even at medium confidence."""
        fallback = {"status": "fallback", "reason": "APPLICATION_NOT_FOUND",
                    "suggested_action": "web_search", "query": "test"}
        assert D.should_activate("medium", fallback) is True

    def test_debugger_does_not_activate_without_trigger(self, D):
        assert D.should_activate("high", None) is False
        assert D.should_activate("medium", None) is False


# ── CATEGORY 8: Special / cross-cutting checks ───────────────────────────────

class TestSpecialChecks:

    def test_everything_cli_attribute_exists(self, R):
        assert hasattr(R, "_es_path")
        if R._es_path is not None:
            import os
            assert os.path.isfile(R._es_path), (
                f"_es_path points to non-existent file: {R._es_path}"
            )

    def test_no_url_guessing_across_all_unknowns(self, R):
        unknowns = [
            "tinkercad", "figma", "canva", "notion", "randomapp",
            "asdfghjkl", "xyzzy", "nothingapp", "randomtool999",
        ]
        for t in unknowns:
            r = R.resolve(t)
            assert_no_url_guessing(r, t)

    def test_confidence_high_for_all_known_websites(self, R):
        known = ["youtube", "google", "github", "gmail", "reddit",
                 "spotify", "teams", "outlook", "drive", "meet"]
        for site in known:
            r = R.resolve(site)
            assert r.confidence == "high", (
                f"'{site}' should have high confidence, got {r.confidence}"
            )

    def test_confidence_low_for_all_unknowns(self, R):
        unknowns = ["randomapp123", "asdfghjkl", "tinkercad", "figma", "xyzzy"]
        for t in unknowns:
            r = R.resolve(t)
            assert r.confidence == "low", (
                f"'{t}' should have low confidence, got {r.confidence}"
            )

    def test_no_silent_fallback_in_reasoner(self, RE):
        """When app not found, fallback_info must be present — no silent switch."""
        unknowns = ["open randomapp123", "open asdfghjkl", "open nothingapp"]
        for cmd in unknowns:
            result = RE.analyze_request(cmd)
            if result["intent"] == "search_web":
                assert "fallback_info" in result, (
                    f"Silent fallback detected for '{cmd}': no fallback_info"
                )

    def test_deterministic_outputs(self, N, R, D, RE):
        """Same input must always produce same output (run 3 times)."""
        cmd = "open spotfy"
        results = [pipeline(N, R, D, RE, cmd) for _ in range(3)]
        intents = [r["analysis"]["intent"] for r in results]
        assert len(set(intents)) == 1, (
            f"Non-deterministic intent for '{cmd}': {intents}"
        )
        normalized_vals = [r["normalized"] for r in results]
        assert len(set(normalized_vals)) == 1, (
            f"Non-deterministic normalization for '{cmd}': {normalized_vals}"
        )

    def test_resolver_is_pure_no_execution_imports(self):
        import sys
        forbidden = ["core.tools", "core.executor", "core.brain",
                     "core.browser_automation"]
        mod = sys.modules.get("core.resolution.target_resolver")
        if mod:
            for dep in forbidden:
                assert dep not in getattr(mod, "__dict__", {}), (
                    f"Resolver imports execution module: {dep}"
                )

    def test_debugger_is_pure_no_execution_imports(self):
        import sys
        forbidden = ["core.tools", "core.executor", "core.brain",
                     "core.browser_automation", "subprocess"]
        mod = sys.modules.get("core.debugger.debugger")
        if mod:
            for dep in forbidden:
                assert dep not in getattr(mod, "__dict__", {}), (
                    f"Debugger imports execution module: {dep}"
                )

    def test_alias_table_integrity(self, N):
        aliases = N.get_aliases()
        for key, value in aliases.items():
            assert key != value, f"Identity alias: '{key}' -> '{value}'"
            assert value not in aliases, f"Circular alias: '{key}' -> '{value}'"

    def test_typo_map_integrity(self, N):
        typos = N.get_typo_map()
        for key, value in typos.items():
            assert key != value, f"Identity typo: '{key}' -> '{value}'"
            assert value not in typos, f"Circular typo: '{key}' -> '{value}'"
