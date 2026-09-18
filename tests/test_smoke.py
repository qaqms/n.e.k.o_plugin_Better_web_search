import json
import re
from pathlib import Path

PANEL_ENTRY_IDS = [
    "panel_context",
    "save_exa_key",
    "clear_exa_key",
    "test_exa_key",
    "set_host_search",
    "get_host_search",
    "set_onboarding",
    "show_guide",
    "diagnose_network",
]

# ui/ has no test harness of its own, so a missing copy string would only show
# up as a raw key rendered in the panel -- these static checks are the guard.
T_KEY = re.compile(r'(?<![A-Za-z0-9_])t\("([a-zA-Z0-9_.]+)"')


def _load_locale(locale: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "i18n" / f"{locale}.json").read_text(encoding="utf-8"))


def test_every_panel_copy_key_exists_in_both_locales() -> None:
    root = Path(__file__).resolve().parents[1]
    tsx = (root / "ui" / "panel.tsx").read_text(encoding="utf-8")
    used = set(T_KEY.findall(tsx))
    assert len(used) > 40, "the extractor stopped matching t() calls"
    for locale in ("zh-CN", "en"):
        catalog = _load_locale(locale)
        missing = sorted(key for key in used if key not in catalog)
        assert not missing, f"i18n/{locale}.json missing: {missing}"


def test_both_locales_carry_the_same_keys() -> None:
    zh, en = _load_locale("zh-CN"), _load_locale("en")
    assert set(zh) - set(en) == set() and set(en) - set(zh) == set()


def test_panel_copy_tries_the_silent_paths_before_the_host_hook() -> None:
    """The host's useClipboard() reports its own rejections to the panel frame.

    Its hook only checks that writeText *exists*, so under a blocking
    Permissions-Policy it awaits, catches the DOMException and calls
    reportHostedRuntimeError('clipboard.write') -> the user sees
    "插件界面控件错误" even though the hook returns a clean false. Calling it first
    therefore painted the banner on every attempt; the paths that can fail
    silently have to come first.
    """
    root = Path(__file__).resolve().parents[1]
    tsx = (root / "ui" / "panel.tsx").read_text(encoding="utf-8")
    body = tsx[tsx.index("async function copyRegisterUrl"):][:600]
    order = [body.index(call) for call in ("nativeCopy(", "legacyCopy(", "clipboard.write(")]
    assert order == sorted(order), f"copy fallback order regressed: {order}"


def test_host_switch_states_intent_not_status() -> None:
    """The built-in-search control must not read like a status line.

    It used to be labelled "内置「网络搜索」正在运行" with checked=running, so after the
    user stopped it the sentence stayed on screen and looked like a failed toggle.
    The badge is the only status claim now; the switch carries the (inverted) intent.
    """
    root = Path(__file__).resolve().parents[1]
    tsx = (root / "ui" / "panel.tsx").read_text(encoding="utf-8")
    body = tsx[tsx.index("function renderHostCard"):][:1400]
    assert "checked={hostKnown && !hostRunning}" in body
    assert "toggleHostSearch(!value)" in body
    assert "正在运行" not in _load_locale("zh-CN")["panel.host.label"]
    assert "is running" not in _load_locale("en")["panel.host.label"]


def test_plugin_manifest_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "plugin.toml"
    assert manifest.is_file()
    text = manifest.read_text(encoding="utf-8")
    assert 'id = "free_web_search"' in text
    assert 'entry = "plugin.plugins.free_web_search:FreeWebSearchPlugin"' in text


def test_manifest_declares_panel_and_guide() -> None:
    """W5 owns the manifest; W4's ui/panel.tsx and docs/quickstart.md bind to it.

    Suffix drives the render mode on the host side (ui_manifest.py:217-227), so
    the manifest must not declare ``mode`` at all -- assert its absence too.
    """
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.toml").read_text(encoding="utf-8")
    assert "[plugin.ui]" in text
    assert 'entry = "ui/panel.tsx"' in text
    assert 'entry = "docs/quickstart.md"' in text
    assert 'context = "main"' in text
    assert "mode = " not in text


def test_every_panel_action_id_is_declared_as_an_entry() -> None:
    """Plan §3 freezes the actionId list; a typo here breaks the panel silently."""
    root = Path(__file__).resolve().parents[1]
    source = (root / "__init__.py").read_text(encoding="utf-8")
    for entry_id in PANEL_ENTRY_IDS:
        assert f'id="{entry_id}"' in source, f"missing plugin_entry id: {entry_id}"


def test_default_config_sections_present_in_example() -> None:
    root = Path(__file__).resolve().parents[1]
    example = (root / "config.example.toml").read_text(encoding="utf-8")
    for section in ("[search]", "[net]", "[ui]", "[host]"):
        assert section in example
    for key in ("exa_api_key", "exa_tool", "exa_key_fallback_anonymous", "baidu_warmup",
                "duckduckgo_needs_proxy", "ssrf_allow_ranges", "onboarding_stage",
                "first_run_notice_sent", "takeover_search"):
        assert key in example, f"config.example.toml missing {key}"
    assert 'backend_chain = ["exa", "anysearch", "bing", "baidu"]' in example
