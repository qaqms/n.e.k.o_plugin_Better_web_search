# 免费联网搜索 / Free Web Search

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

- **`search`** — 免 Key 搜索。参数 `query` / `max_results` / `backend`。返回 `summary`（含标题、摘要、链接）。
- **`fetch`** — 读取网页正文。参数 `url` / `max_chars` / `mode`。先本地直连抓正文（**URL 不会经过任何第三方**），失败再走远端阅读器。

`fetch` 带 SSRF 防护：`localhost`、`127.0.0.1`、`192.168.x.x`、`169.254.169.254`（云元数据地址）、`*.local`、以及解析到内网的域名、`javascript:` / `ftp:` 之类协议，全部拒绝。唯一例外是 `[net] ssrf_allow_ranges`（默认 `198.18.0.0/15`）：兼容 TUN + fake-ip 代理把外网域名解析成假 IP 的情况，且**只对域名解析结果放行**——直接把 IP 填进链接照样拒绝。

面板里还有：接入教程（注册 → 粘贴 → 立即测试三步 + 「先体验」按钮）、「停用宿主内置网络搜索」双向开关（避免两个搜索插件抢活）、**「代理软件兼容」开关**（Clash/mihomo 的 TUN + fake-ip 模式下面板一键切，不需要你懂 CIDR）、网络自检（直连/代理双测，给出推荐链路）。

## 装到自己的 N.E.K.O 上

在 N.E.K.O 源码根目录构建，然后在 **插件中心 → 导入** 选这个包：

```bash
cd N.E.K.O
PYTHONDONTWRITEBYTECODE=1 uv run neko-plugin build "../plugins/free_web_search"
# 产物：N.E.K.O/plugin/neko_plugin_cli/target/free_web_search.neko-plugin
```

Windows PowerShell 下这样带环境变量：

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
uv run neko-plugin build "../plugins/free_web_search"
```

> **为什么要加 `PYTHONDONTWRITEBYTECODE=1`**：`neko-plugin build` 会 import 插件来探测它的 entry 元数据，这一步在源码目录生成 `__pycache__/*.pyc`，而这些字节码会跟着进最终的分发包（实测约 22 KB→53 KB 的差距全在这里）。因为探测发生在打包之前，**先清理源码目录再构建是没用的**，字节码会被重新生成。插件的 `pyproject.toml` 里已声明 `[tool.neko.build] exclude_dirs`，但压缩步骤不读该规则，所以只能靠这个环境变量绕过。这是 `neko_plugin_cli` 的通病，所有插件都会碰到；上游的修法是构建时设 `sys.dont_write_bytecode = True`，以及让压缩步骤复用 `build_rules.should_skip_path()`。

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
n.e.k.o_plugin_free_web_search
```

在本仓库根目录：

```bash
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uv run --project "../../N.E.K.O" neko-plugin check .
# 含 lint + 测试 + 构建 + 包校验；带 NO-BYTECODE 才能得到干净的包
PYTHONDONTWRITEBYTECODE=1 uv run --project "../../N.E.K.O" neko-plugin check -r .
```

单元测试是**离线**的（`tests/fixtures/` 里是真实响应结构，不联网）：

```bash
uv run --project "../../N.E.K.O" python -m pytest tests -q
```

结构：

```text
__init__.py      插件主体：四段配置、后端编排与代理感知裁剪、回退、对话入口、面板 entry、首启引导
_providers.py    exa / anysearch / bing / baidu / duckduckgo / searxng + 正文抓取（exa 支持密钥）
_parsing.py      零依赖 HTML 解析（结果卡片打分 + 正文线性化 + GBK 容错解码）
_net.py          标准库 HTTP + 代理策略
_resilience.py   缓存、并发合并、限流、失败退避（含 ApiKeyRejected / QuotaExhausted 错误）
_guard.py        fetch 的 SSRF 防护（allow_ranges 只对域名解析结果生效）
_host.py         宿主内置 web_search 的状态读取与双向开关（只走宿主公开回环 API）
_diagnose.py     网络自检编排（纯逻辑，probe 闭包由 __init__.py 注入）
ui/panel.tsx     面板（引导三步 / 密钥管理 / 内置搜索开关 / 自检按钮）
docs/quickstart.md  接入教程
```

面板 entry（actionId，全部对宿主 30s 看门狗留了预算）：`panel_context`、`save_exa_key`、`clear_exa_key`、`test_exa_key`、`set_host_search`、`get_host_search`、`set_onboarding`、`show_guide`、`diagnose_network`、`set_ssrf_guard`。

## 发布到 Market

```bash
uv run --project "../../N.E.K.O" neko-plugin publish .
```

先在 [Market 投稿页](https://market.project-neko.cn/#/upload) 用 GitHub 仓库地址提交一次审核，通过后这条命令会打 tag、等 GitHub Release、再通知 Market。`.github/workflows/release.yml` 会构建并上传 `free_web_search.neko-plugin`，Market 独立校验该 Release 后才上架。

## Entry

```toml
entry = "plugin.plugins.free_web_search:FreeWebSearchPlugin"
```

插件被安装到用户目录后，宿主会把 `plugin.plugins.*` 前缀改写成 `plugins.*` 再加载，因此开发时（挂在 N.E.K.O 源码树里）和安装后（在用户插件目录）用同一个 entry 字符串即可。
