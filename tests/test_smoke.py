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
