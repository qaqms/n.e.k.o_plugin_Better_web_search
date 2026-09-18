import fnmatch
import json
import re
import tomllib
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
    "set_ssrf_guard",
]

_ROOT = Path(__file__).resolve().parents[1]


def _read_toml(name: str) -> dict:
    with (_ROOT / name).open("rb") as stream:
        return tomllib.load(stream)


def _host_rule_matches(rel_path: str, pattern: str) -> bool:
    """The host's own pattern semantics (neko_plugin_cli/core/build_rules.py:153-158).

    A pattern without "/" is matched against the *file name*, so ["tests",
    "docs/plan-*.md"] and ["*.pyc"] all describe real host behaviour here
    instead of a guess at it.
    """
    if fnmatch.fnmatchcase(rel_path, pattern):
        return True
    return "/" not in pattern and fnmatch.fnmatchcase(Path(rel_path).name, pattern)


def _excluded_from_package(rel_path: str, rules: dict) -> bool:
    parts = Path(rel_path).parts
    for dir_pattern in rules.get("exclude_dirs", []):
        if any(_host_rule_matches("/".join(parts[: i + 1]), dir_pattern) for i in range(len(parts) - 1)):
            return True
    for pattern in list(rules.get("exclude", [])) + list(rules.get("exclude_files", [])):
        if _host_rule_matches(rel_path, pattern):
            return True
    return False


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
    """The built-in-search control must mirror the stored intent, never live state.

    It was briefly `checked={hostKnown && !hostRunning}`: because the badge then
    decided the switch position, a second click meant to "confirm the stop" sent
    enabled=true and started the built-in back up (seen on a Steam install at
    22:46:06 -> process started 22:46:07). The switch now reads [host].takeover_search,
    and a mismatch between intent and reality gets its own warning + retry button.
    """
    root = Path(__file__).resolve().parents[1]
    tsx = (root / "ui" / "panel.tsx").read_text(encoding="utf-8")
    body = tsx.split("function renderHostCard", 1)[1].split("\n  function ", 1)[0]
    assert "checked={takeover}" in body
    assert "toggleHostSearch(!value)" in body
    assert "!hostRunning}" not in body
    assert "panel.host.mismatch" in body and "panel.actions.retryStop" in body
    assert "正在运行" not in _load_locale("zh-CN")["panel.host.label"]
    assert "is running" not in _load_locale("en")["panel.host.label"]


def test_plugin_manifest_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "plugin.toml"
    assert manifest.is_file()
    text = manifest.read_text(encoding="utf-8")
    assert 'id = "better_web_search"' in text
    assert 'entry = "plugin.plugins.better_web_search:BetterWebSearchPlugin"' in text
    # The old id is declared so the importer refuses to install this side by side
    # with a live free_web_search (two plugins would both register `search`).
    assert 'previous_ids = ["free_web_search"]' in text


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


def test_name_is_the_same_everywhere() -> None:
    """The v0.3.0 rename (free_web_search -> better_web_search) left no stragglers.

    Three separate surfaces can disagree after a rename and each one is invisible
    from the others: the plugin center renders the *i18n* `plugin.name`
    (query_service.py:211-222 overrides the TOML value), Market renders the TOML
    value, and the runtime renders strings baked into `__init__.py` and the panel.
    So scan the runtime set for the old identifiers and pin the display name to
    the manifest name.
    """
    manifest = _read_toml("plugin.toml")["plugin"]
    plugin_id, entry, shown = manifest["id"], manifest["entry"], manifest["name"]

    assert _read_toml("pyproject.toml")["project"]["name"] == plugin_id
    module_name, class_name = entry.split(":")
    assert module_name == f"plugin.plugins.{plugin_id}"
    source = (_ROOT / "__init__.py").read_text(encoding="utf-8")
    assert f"class {class_name}(NekoPluginBase):" in source, f"entry names {class_name}"

    for locale in ("zh-CN", "en"):
        catalog = _load_locale(locale)
        assert catalog["plugin.name"] == catalog["panel.title"], f"{locale}: two titles"
    assert _load_locale("zh-CN")["plugin.name"] == shown, "manifest name != displayed name"

    for rel in ("__init__.py", "ui/panel.tsx", "docs/quickstart.md", "config.example.toml",
                "i18n/zh-CN.json", "i18n/en.json",
                # The market CI templates take the id as a workflow input, and a
                # stale one there fails only on GitHub, long after every local gate.
                ".github/workflows/verify.yml", ".github/workflows/release.yml",
                *[p.name for p in _ROOT.glob("_*.py")]):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        for stale in ("free_web_search", "FreeWebSearch", "FREE_WEB_SEARCH", "免费联网搜索"):
            assert stale not in text, f"{rel} still says {stale!r}"


def test_release_version_is_stated_once() -> None:
    """plugin.toml and pyproject.toml must agree on the version.

    Nothing else catches this: neko-plugin only compares the *git tag* against
    plugin.toml (release_cmd.py:237-239), so a pyproject left at the previous
    number is silent here but wrong in every pip-based view of this repo.
    """
    plugin_version = _read_toml("plugin.toml")["plugin"]["version"]
    project_version = _read_toml("pyproject.toml")["project"]["version"]
    assert plugin_version == project_version, (
        f"plugin.toml={plugin_version} but pyproject.toml={project_version}"
    )
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    first_heading = next((line for line in changelog.splitlines()
                          if line.startswith("## ")), "")
    assert first_heading.startswith("## v"), (
        f"the release on top of the changelog is not versioned: {first_heading!r}"
    )


def test_packaging_excludes_dev_payload_but_keeps_ui_files() -> None:
    """The distributed package carries the panel and the guide, nothing else.

    v0.2.0 shipped 41 files / 484 KB, of which 135 KB was scraped
    bing/baidu/duckduckgo HTML (tests/fixtures) and 18 KB an internal
    construction plan -- both are inputs to this repo's own tests, and the
    fixtures are other people's pages. The rules live in pyproject.toml and are
    applied at the staging copy (build.py:253,342), which is exactly why a
    declared UI entry that happens to sit under an excluded path would still
    fail *here* rather than on the user's panel.
    """
    rules = _read_toml("pyproject.toml").get("tool", {}).get("neko", {}).get("build", {})
    ui = _read_toml("plugin.toml")["plugin"]["ui"]
    declared = [panel["entry"] for panel in ui.get("panel", [])]
    declared += [guide["entry"] for guide in ui.get("guide", [])]
    assert declared, "manifest declares no UI files"

    for rel_path in declared:
        assert (_ROOT / rel_path).is_file(), f"manifest declares missing {rel_path}"
        assert not _excluded_from_package(rel_path, rules), f"{rel_path} must ship"

    assert _excluded_from_package("tests/fixtures/bing_html.html", rules)
    assert _excluded_from_package("docs/plan-v0.2.md", rules)
    assert _excluded_from_package("x/__pycache__/y.pyc", rules)

