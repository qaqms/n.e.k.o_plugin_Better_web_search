# 更好的网络搜索 / Better Web Search

给 N.E.K.O 的免 API Key 联网搜索 + 网页正文阅读插件。**装好就能用，不需要注册任何服务、不需要填任何 Key。**

一个不需要任何 API Key 的联网搜索与网页正文阅读插件，开箱即用，失败自动切换后端。插件自带面板：首装猫娘会开口引导；面板里可一键填 Exa 免费密钥（可选）、一键停用宿主内置搜索、一键网络自检。

---

## 为什么它是免费的

大多数"免费搜索插件"其实是去爬搜索引擎的搜索结果页，这条路会被限流、会被反爬、而且在国内经常根本连不上。这个插件的主路径不是爬页面，而是走**别人公开免费的检索网关**：

下表为 mainland 直连实测（系统代理关闭、无环境代理，plan §0 同款环境）：

| 后端 | 要不要 Key | 原理 | 国内直连（实测） |
| --- | --- | --- | --- |
| `exa`（默认首选） | 不要（可选填自己的免费 Key） | Exa 的公共 MCP 端点 `mcp.exa.ai`，对方替所有匿名用户付钱 | ✅ 快路径约 1.0–1.8s，返回标题+链接+高亮片段 |
| `anysearch` | 不要（可选填） | AnySearch 的匿名档 | ✅ 1.2–5.0s |
| `bing` | 不要 | 抓结果页 | ✅ 约 0.6s，中英文都好，已进默认链路 |
| `baidu` | 不要 | 抓结果页 + BAIDUID 预热 | ❌ 直连裸请求回"百度安全验证"（HTTP 200 验证页），预热才有救，排链路末位 |
| `duckduckgo` | 不要 | 抓 `html.duckduckgo.com` 的结果页 | ❌ 直连 DNS 污染直接超时；**没检测到代理时根本不会进实际链路**（见 `duckduckgo_needs_proxy`） |
| `sogou` | 不要 | 抓结果页 | ❌ 实测无可解析结果，不进默认链路 |
| `searxng` | 不要 | **你自己的**实例，唯一真正不受别人限流的路 | 自己部署 |

`exa` 排第一不只是因为它免 Key：它给的是**带高亮的结果**，而不是搜索引擎那种一句被截断的预览。要看**整页正文**请接着用 `fetch`（它会先直连抓原文，失败才走 Exa 阅读器）。

> 如果你愿意拿延迟换更长的正文片段，可以把 `exa_tool` 显式改成 `advanced`（返回页正文、但实测 3.7–11.7s，会接近单后端 12s 超时）。默认**不**这么做。

### 想更稳？填一个 Exa 免费 Key（可选，不是必需）

- 注册地址 <https://dashboard.exa.ai/api-keys>，国内**直连可达**；登录只有 Google / Email 两种方式，国内建议走 **Email 注册**。
- 免费档 = 注册送 $20，之后**每月刷新 $10**；实测 `/search` 单价 $7/1k，≈ **1400 次/月 ≈ 47 次/天**。
- 不填 Key 照样能搜。填 Key 买到的是**额度确定性**，不是速度：实测 advanced 档 3.7–11.7s 会顶穿 12s 预算，所以 `exa_tool = "auto"` 恒用快路径（带不带 Key 都一样）。
- Key 无效 / 额度用尽：本次搜索**自动降级回匿名档**，不会因此搜不到；面板会提示"密钥无效，请到面板重新填写"。
- 安全：Key 只存在本插件配置里；日志、状态上报、面板回显一律最多出现 `exa****尾4位`（宿主日志不脱敏，所以我们连状态都不写明文）。

## 装完之后怎么用

对猫娘直接说"搜一下 XXX"就会走 `search`；想知道某条结果的具体内容时说"打开这个链接看看"就会走 `fetch`。两个入口都注册给了对话侧：

- **`search`** — 免 Key 搜索。参数 `query` / `max_results` / `backend`。返回 `summary`（含标题、摘要、链接），外加 `backend` 与 `attempted`（这一次实际走过哪几路）。
- **`fetch`** — 读取网页正文。参数 `url` / `max_chars` / `mode`。先本地直连抓正文（**URL 不会经过任何第三方**），失败再走远端阅读器。

`fetch` 带 SSRF 防护：`localhost`、`127.0.0.1`、`192.168.x.x`、`169.254.169.254`（云元数据地址）、`*.local`、以及解析到内网的域名、`javascript:` / `ftp:` 之类协议，全部拒绝。唯一例外是 `[net] ssrf_allow_ranges`（默认 `198.18.0.0/15`）：兼容 TUN + fake-ip 代理把外网域名解析成假 IP 的情况，且**只对域名解析结果放行**——直接把 IP 填进链接照样拒绝。

面板里还有：**「最近一次搜索」回看卡**（哪一路答的、几条、多久、依次试过哪几路——这些原本只在插件日志里，宿主不记插件的工具返回体，所以面板是唯一能看到的地方；只记关键词字数，不记内容，重启插件即清空）、接入教程（注册 → 粘贴 → 立即测试三步 + 「先体验」按钮）、「停用宿主内置网络搜索」双向开关（避免两个搜索插件抢活）、**「代理软件兼容」开关**（Clash/mihomo 的 TUN + fake-ip 模式下面板一键切，不需要你懂 CIDR）、网络自检（默认跟随检测到的代理决定是否**直连/代理双测**，也可手动固定；双测会把探测次数翻倍，结果表格里"走代理能不能用"单独一列，未测不等于用不了）。

> **接管范围的诚实说明**：面板那个开关只接管**对话侧的搜索工具**这一路。宿主自己还有几条不走 LLM 工具的路径
> （窗口上下文 `search_duckduckgo` / `search_baidu`、话题素材采集等）经 `utils/web_scraper/search_gateway.py`
> **硬编码**调用内置 `web_search` 插件；停用内置之后，那些路径会安静地返回空结果（`{"success": False,
> "results": []}`），**不会**改走本插件。要是你依赖那些功能，就别在这里停用内置，或者去宿主侧把它改成可插拔。

## 装到自己的 N.E.K.O 上

在 N.E.K.O 源码根目录构建，然后在 **插件中心 → 导入** 选这个包：

```bash
cd N.E.K.O
PYTHONDONTWRITEBYTECODE=1 uv run python -m plugin.neko_plugin_cli build "../plugins/better_web_search"
# 产物：N.E.K.O/plugin/neko_plugin_cli/target/better_web_search.neko-plugin
```

> **老名字 `free_web_search` 装过的话，先卸载再导入**：插件 id 换了，宿主**不会**把
> `plugins/free_web_search/config/` 搬过去（`registry.py:1461 _migrate_plugin_id` 只搬进程内的注册表
> 映射，不碰磁盘配置），所以 Exa 密钥、接管开关、引导进度都要重填。包里声明了
> `[plugin].previous_ids = ["free_web_search"]`，旧插件还在的时候导入会被直接拒绝并提示冲突
> （`install_plan.py:135-153`），这是故意的——两个都注册了 `search` 工具的插件同时活着比装不上更糟。

> **构建后花一秒自验包**（元数据在不在 = 面板能不能用；测试夹具不该在里面）：
>
> ```bash
> python -c "import zipfile,sys; n=zipfile.ZipFile(sys.argv[1]).namelist(); \
> print('files:', len(n)); \
> print('plugin.meta.json:', any('plugin.meta.json' in x for x in n) or '缺失！这份包不能让面板正常工作'); \
> print('tests/ leaked:', any('/tests/' in x for x in n) or 'no'); \
> print('quickstart.md:', any('docs/quickstart.md' in x for x in n) or '缺失！教程打不开')" \
> N.E.K.O/plugin/neko_plugin_cli/target/better_web_search.neko-plugin
> ```
>
> 干净的样子是 `files: 24`、`tests/ leaked: no`、`quickstart.md: True`。
>
> 实测过的坑：`neko-plugin` 这个命令入口（venv 里的 console script）可能解析到**另一份旧的宿主
> 检出**，那份 CLI 还没有 entry 元数据探测步骤，于是构建照样 `[OK]`、**不打任何警告**，但产物里没有
> `plugin.meta.json`。宿主只能退回"从 manifest 猜入口"，静态注册表拿到空集，面板每个按钮都回
> `UI action 'xxx' is not a plugin entry`（404，文案还骗人——它说的是"一个入口都没注册上"）。
> 用 `python -m plugin.neko_plugin_cli` 代替 `neko-plugin` 就能确定性地走当前这棵树（cwd 在哪儿都无所谓，
> 已实测两边都能出 meta）。

Windows PowerShell 下这样带环境变量：

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
uv run python -m plugin.neko_plugin_cli build "../plugins/better_web_search"
```

> 本仓库独立检出在别处时（例如与 `N.E.K.O` 同级、目录名保留自旧仓库名的
> `n.e.k.o_plugin_Better_web_search`），把路径参数换成那个目录名即可，"在宿主根目录执行"这一条不能变。

> **为什么要加 `PYTHONDONTWRITEBYTECODE=1`**：`neko-plugin build` 会 import 插件来探测它的 entry 元数据，
> 而探测用的是**暂存目录里的那份副本**（构建日志里能看到它在 `%TEMP%\neko_build_<插件 id>\payload\plugins\…`
> 下读 `plugin.toml`），于是这一步写出的 `__pycache__/*.pyc` 落在暂存树里，最终跟着分发包一起被 zip。
> 实测不带这个环境变量：包里多 8 个 `.pyc`、159 KB 变 290 KB，而**源码目录的 `__pycache__` mtime 一个都没变**
> ——所以"先清理源码目录再构建"是无效动作，字节码压根不是写在源码目录里的。
> `[tool.neko.build] exclude_dirs` 只在复制到暂存树那一步生效（`plugin/neko_plugin_cli/core/build.py:342`），
> `export_package` 压缩时不再重套规则，因此对这条泄漏**无效**。上游的修法是构建时设
> `sys.dont_write_bytecode = True`，以及让压缩步骤复用 `build_rules.should_skip_path()`。
> 同理，本插件的分发包排除（`tests/` 与内部施工单 `docs/plan-*.md` 不进包）也是靠 `[tool.neko.build]`
> 生效的：包里只有 24 个文件，`docs/quickstart.md` 因为在 manifest 里被声明为教程 entry 所以必须留。

本插件**零第三方依赖**（只用 Python 标准库），所以没有 `vendor/`，包很小，也不会因为宿主依赖版本变动而坏掉。

## 配置

复制 `config.example.toml` 到插件配置里按需修改。最常碰的几项：

```toml
[search]
backend = "auto"
backend_chain = ["exa", "anysearch", "bing", "baidu"]   # 按直连实测排序；ddg 只有在检测到代理时才会被真正使用

# 代理：这是"搜索突然不能用"的头号原因
proxy = "auto"              # auto=跟随系统/环境变量，off=不用，on=全走，或直接填 http://127.0.0.1:7890
proxy_url = ""              # 显式代理；填了就等效"有代理"，duckduckgo 会回到链路里
duckduckgo_proxy = "proxy"  # DDG 在国内直连不通，默认强制走代理
bing_proxy = "direct"       # 百度/必应/搜狗保持直连，不要白白绕代理

# Exa 密钥（可选升级）：更推荐直接在插件面板里填并一键测试
exa_api_key = ""            # https://dashboard.exa.ai/api-keys 邮箱注册，每月 $10 免费额度
exa_tool = "auto"           # auto 恒用快路径（advanced 实测会顶穿 12s 预算，仅显式选择时才用）
exa_key_fallback_anonymous = true   # 坏 key / 超额自动降级匿名，搜索不断流
baidu_warmup = true         # 先领 BAIDUID cookie 再搜，否则基本必撞"百度安全验证"
duckduckgo_needs_proxy = true        # 无代理时 ddg 不进 effective chain

# 可选增强（留空照样能用）
anysearch_api_key = ""      # 填了限额更高，不填走匿名档
searxng_base_url = ""       # 自建实例，例如 http://127.0.0.1:8888

[net]
ssrf_allow_ranges = ["198.18.0.0/15"]   # TUN+fake-ip 兼容，只对域名解析结果放行

[host]
takeover_search = false     # 在面板切"停用内置搜索"时自动置 true；启动时重申，失败不影响启动
```

排查建议：如果搜索没结果，优先点面板里的**网络自检**（直连/代理双测 + 推荐链路 + 中文结论）；或看 `startup` 返回里的 `chain`（用户配置的）与 `effective_chain`（实际会用的，代理感知裁剪后）和 `system_proxy_detected`；再单独指定 `backend` 逐个试。想彻底不依赖第三方服务，就自建一个 SearXNG 并把 `backend_chain` 改成 `["searxng"]`。

## 开发

当前目录既是插件源码，也是它自己的 Git 仓库。发版到插件市场时，GitHub 仓库名必须是：

```text
n.e.k.o_plugin_better_web_search
```

> 比对是 `casefold()` 的（`release_cmd.py:231`），所以现在这个写作
> `n.e.k.o_plugin_Better_web_search` 的仓库名**直接满足要求**，不需要去 GitHub 改名。
> 这条是插件 id 从 `free_web_search` 改成 `better_web_search` 的附带收益之一。

在本仓库根目录（`neko-plugin` 换成 `python -m plugin.neko_plugin_cli` 的原因见上文那条坑注）：

```bash
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uv run --project "../../N.E.K.O" python -m plugin.neko_plugin_cli check .
# 含 lint + 测试 + 构建 + 包校验；带 NO-BYTECODE 才能得到干净的包
PYTHONDONTWRITEBYTECODE=1 uv run --project "../../N.E.K.O" python -m plugin.neko_plugin_cli check -r .
```

单元测试是**离线**的（`tests/fixtures/` 里是真实响应结构，不联网）：

```bash
uv run --project "../../N.E.K.O" python -m pytest -c tests/pytest.ini tests -q
```

> `-c tests/pytest.ini` 不能省：本仓库根目录就是插件包（有 `__init__.py`），pytest 8/9 会为 rootdir 到用例之间的每层目录建 Package 节点并去 import 根 `__init__.py`，而插件独立检出时它无法作为包被导入，202 个用例会在 setup 阶段全量 CollectError。把 rootdir 收进 `tests/` 就没这个节点（与宿主 `plugin/tests/pytest.ini` 同一约定）。

结构：

```text
__init__.py      插件主体：四段配置、后端编排与代理感知裁剪、回退、对话入口、最近一次搜索记录、面板 entry、首启引导
_providers.py    exa / anysearch / bing / baidu / duckduckgo / searxng + 正文抓取（exa 支持密钥）
_parsing.py      零依赖 HTML 解析（结果卡片打分 + 正文线性化 + GBK 容错解码）
_net.py          标准库 HTTP + 代理策略
_resilience.py   缓存、并发合并、限流、失败退避（含 ApiKeyRejected / QuotaExhausted 错误）
_guard.py        fetch 的 SSRF 防护（allow_ranges 只对域名解析结果生效）
_host.py         宿主内置 web_search 的状态读取与双向开关（只走宿主公开回环 API）
_diagnose.py     网络自检编排（纯逻辑，probe 闭包由 __init__.py 注入）
ui/panel.tsx     面板（引导三步 / 密钥管理 / 最近一次搜索回看 / 内置搜索开关 / 自检按钮）
docs/quickstart.md  接入教程
tests/           离线用例 + 真实响应夹具（**不进分发包**，见 pyproject 的 [tool.neko.build]）
docs/plan-*.md   施工单，内部文档（**不进分发包**）
```

面板 entry（actionId，全部对宿主 30s 看门狗留了预算）：`panel_context`、`save_exa_key`、`clear_exa_key`、`test_exa_key`、`set_host_search`、`get_host_search`、`set_onboarding`、`show_guide`、`diagnose_network`、`set_ssrf_guard`。

## 发布到 Market

```bash
uv run --project "../../N.E.K.O" python -m plugin.neko_plugin_cli publish .
```

先在 [Market 投稿页](https://market.project-neko.cn/#/upload) 用 GitHub 仓库地址提交一次审核，通过后这条命令会打 tag、等 GitHub Release、再通知 Market。`.github/workflows/release.yml` 会构建并上传 `better_web_search.neko-plugin`，Market 独立校验该 Release 后才上架。

发布前两条会**直接报 error** 的硬条件（`plugin/neko_plugin_cli/commands/release_cmd.py`）：

| 条件 | 代码位置 | 本仓库现状 |
| --- | --- | --- |
| git origin 的仓库名必须是 `n.e.k.o_plugin_<插件 id>` | `release_cmd.py:230-232`（`casefold()` 比对） | ✅ id 改成 `better_web_search` 后，现有的 `n.e.k.o_plugin_Better_web_search` 就满足了 |
| tag 去掉 `v` 前缀后必须等于 `plugin.toml` 的 `version` | `release_cmd.py:237-239` | ✅ 发 `v0.3.0`；`tests/test_smoke.py::test_release_version_is_stated_once` 保证 `plugin.toml` 与 `pyproject.toml` 不打架 |

> 剩下没做的只有"打 tag + 投稿 Market"这一步：本仓库至今**零 tag**（v0.2.0/v0.2.1 都没打过），
> 所以 Market 上至今没有这个插件。

## Entry

```toml
entry = "plugin.plugins.better_web_search:BetterWebSearchPlugin"
```

插件被安装到用户目录后，宿主会把 `plugin.plugins.*` 前缀改写成 `plugins.*` 再加载，因此开发时（挂在 N.E.K.O 源码树里）和安装后（在用户插件目录）用同一个 entry 字符串即可。
