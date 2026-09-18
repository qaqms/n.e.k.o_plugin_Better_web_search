# 更新记录

## 未发布

一轮"说的和做的对上"的修正，全部有离线单测兜底（202 → 226 个用例）。

### 修正

- **16 个配置项从来没生效过**：`plugin.toml` 在 `[host]` 段之后没有再开新段头，导致
  `max_content_chars`、`fetch_total_timeout_seconds`、`cache_ttl_seconds`、7 个
  `*_min_interval_seconds` 等一并落在 `[host]` 下，而代码只从 `[search]` 读——改这些值
  等于没改。现已归位，并新增 `tests/test_config_keys.py`：直接从 `__init__.py` 反推读取清单，
  双向断言"读的键必须声明在对应段、声明的键必须真被读"，两份 TOML 的键集也必须一致。
- **`[search] backend` 偏好后端**：`search()` 恒传 `"auto"`，`forced = backend or configured or
  "auto"` 永远在第一个值上短路，配置里的偏好后端从未参与执行，只是让上报的链路顺序看起来变了。
  现在提出 `_ordered_chain()` 由 startup / 面板上下文 / 执行路径共用；语义定为**配置=偏好**
  （提到链首、仍自动回退），**对话里显式指定的 backend=锁死**（不回退，避免张冠李戴的引用）。
- **`[search] max_results` 接线**：原本两份 TOML 都声明、代码从不读（真实默认是入口签名里的
  字面量 6）。现在不指定条数时用配置值，并按 1..15 收敛；入口 schema 去掉字面量默认，避免宿主
  替用户填回 6 而再次吞掉配置。
- **网络自检真的做直连/代理双测**：后端 `diagnose_network(with_proxy=true)` 一直是完整的，但面板
  恒传 `false` 且表格只有 4 列，`proxied` 那一列从未被渲染——README 承诺的"直连/代理双测"实际
  只有单测。面板现在按检测到的代理情况默认决定是否双测（可手动固定），表格加"走代理能不能用"列，
  未测显示"未测"而不是"用不了"。双测时探测数翻倍会顶穿 25 秒外层超时，因此把探测线程池按倍数放宽。
- `_providers._is_unresolved_redirect` 里的 `lstrip("www.")` 改为 `removeprefix("www.")`
  （与同文件 `_is_engine_results_page` 一致）。此处只做后缀匹配，**无行为差异**，属一致性修正。
- **"密钥没有写入成功：请确认宿主配置目录可写"是插件自己误判的**。宿主日志时间线显示：配置在
  3 毫秒内就落盘了（宿主明确记录 `file_writable=True / parent_writable=True`，磁盘上也能读到
  写进去的密钥），4.5 秒后插件才收到 `TransportError: Config persistence response timed out;
  final persistence status is unknown` —— 丢的是**回执**不是写入。同一台宿主上另一个插件
  （`tide_moments`）报的是同一句话，且该字符串只存在于宿主服务端，与本插件无关。
  `_persist` 现在在异常后**回读校验**：值确实写到了就当成功，只有回读不一致才报失败，文案也不再
  指向"目录权限"。真正该修的是宿主持久化回执通道（疑为 Windows Proactor 事件循环下
  `zmq add_reader` 缺陷，宿主日志里本轮出现 7 次该 RuntimeWarning）。
- **面板"复制网址"不再弹"插件界面控件错误"**。机制在宿主：`useClipboard()` 这个 hook 只检查
  `writeText` **是不是个函数**（被 Permissions-Policy 屏蔽时它仍然是函数，crbug.com/414348233），
  于是它 await → 捕到 DOMException → **顺手调 `reportHostedRuntimeError('clipboard.write')`**，
  面板框架就把这条渲染成"插件界面控件错误"。它本身是干净地返回 false 的，所以插件侧 try/catch
  **挡不住这个横幅**。改成自己直连 `navigator.clipboard.writeText`（失败静默）→ 再退到
  `document.execCommand("copy")`（不受该策略限制）→ 最后才用宿主 hook，此时失败是真的不可用，
  横幅才有信息量。新增静态用例锁住这个调用顺序。

### 开发闭环

- 独立检出本仓库时 `pytest tests` 会 202 个用例全量 CollectError：仓库根目录就是插件包
  （有 `__init__.py`），pytest 会为 rootdir 到用例之间的每层目录建 Package 节点并去 import 它。
  新增 `tests/pytest.ini` 把 rootdir 收进 `tests/`（与宿主 `plugin/tests/pytest.ini` 同一约定），
  README 的命令相应更新。
- `diagnose_network` 入口原本零覆盖（`_diagnose.py` 有 33 个纯逻辑测试，但入口侧的双测参数、
  探测集合与线程池都没测到），补 3 个用例。
- `ui/` 没有测试框架，新增静态校验：`panel.tsx` 里每个 `t("…")` 文案键必须同时存在于
  `i18n/zh-CN.json` 与 `en.json`，且两份语言的键集一致。

### 打包

- **`neko-plugin` 命令入口可能解析到另一份旧宿主检出**（本机实测：`F:\ai\N.E.K.O`），那份 CLI 还没有
  entry 元数据探测步骤，于是 `build` 照样打 `[OK]`、**不给任何警告**，产物里却没有 `plugin.meta.json`。
  宿主只能退回"从 manifest 猜入口"，静态注册表得到空集；此后面板每个按钮都回
  `UI action 'xxx' is not a plugin entry`（404）。该文案由宿主
  `plugin/server/application/plugins/ui_query_service.py` 的 `if not entry_ids` 分支产生，
  它判断的是"整个集合为空"，却按"你点的那个 id 不存在"的口气说话。
  改用 `python -m plugin.neko_plugin_cli` 构建（与 cwd 无关，两边实测都能出 meta），
  README 补了一行包内自验命令。

### 面板（实机反馈）

- **密钥配好了却还反复弹新手引导 / 一直显示"现在用的是免费额度…去配置密钥"**。两处叠加：
  `refreshContext("done")` 先设乐观 `localStage` 又在同一函数末尾把它清空，而 `saveKey()`
  **从来没写过** `[ui].onboarding_stage`（只有「先体验」会写 `trial`）——所以配置里永远停在
  `trial`/空值，`stageOf` 又把未知值一律映射成引导首屏。现在密钥**校验通过**时由服务端落
  `onboarding_stage = "done"`（保存和"测试密钥"两条路都会），试用卡额外要求"确实没有已存密钥"
  才显示，这样旧安装在下次打开就直接恢复正常。
- **"我明明关了它还显示『内置「网络搜索」正在运行』"是文案 bug，不是状态读错**。那句是开关的
  **静态标签**（`panel.host.label`），跟状态无关，关掉之后照样整句挂着，看起来像没生效。开关现在
  表达意图（开=已交给本插件，`checked={hostKnown && !hostRunning}`），只有右边徽章声明状态。
  顺带把实测到的真相记下来：宿主 `plugin/core/status.py` 的 `main_process_synthetic` **不是**永远
  `stopped`——它会按 `host.is_alive()` 覆盖成 `running`/`crashed`；本机那次是因为内置 `web_search`
  在 21:24:47 随重新导入真的自启、21:25:17 才被停，那几秒显示"在跑"是**正确**的。
- **网络自检说清楚自己在测什么**。表格原先只有"搜索来源"一列，用户无法判断测的是宿主、是 Exa
  密钥、还是匿名档。自检卡现在固定三行说明：探测的是本插件自己的通道（列出实际链路）、exa 那一行
  用的是你的密钥（掩码尾号）还是公共匿名档、以及宿主内置搜索在/不在都**与本自检无关**。
  "消耗 1 次额度"的旧文案也不准了，改成"每来源一次、开双测两次"。

## v0.2.0

面向"发行给别人用"的一次加固：默认配置不再依赖作者开发机上的本地代理，并把"能不能用"这件事
变成用户自己看得懂、点得动的东西。

### 新增

- **Exa 免费密钥（可选）**：`[search] exa_api_key` + `exa_tool`。注册地址
  <https://dashboard.exa.ai/api-keys> 国内直连可达；免费档 = 注册送 $20、之后每月刷新 $10，
  实测 `/search` 单价 $7/1k ⇒ 约 1400 次/月。**不填照样能用**。
  密钥只走 `x-api-key` 请求头，绝不进 URL / 日志 / 状态上报 / 面板回显（一律 `exa****尾4位`）。
- **插件面板 + 新手引导**（`ui/panel.tsx`）：装完打开面板即三步引导（注册 → 粘贴密钥 → 立即测试），
  含「先体验」按钮（跳过注册直接用免费额度）；之后可在面板里管理密钥（测试 / 替换 / 删除 / 重新引导）。
  首次启动会让猫娘主动开口提示去面板（只提示一次）。
- **停用宿主内置"网络搜索"**：面板里的双向开关，只走宿主公开的回环管理 API
  （`GET /plugin/status`、`POST /plugin/{id}/stop|start`），且目标插件 id 硬编码白名单，
  不接受任意 id。`[host] takeover_search` 记录用户意图并在启动时重申。
- **网络自检 `diagnose_network`**：直连/代理双测每个后端，区分"网络不通 / 被反爬挡 / 额度用尽 /
  密钥无效 / 解析不出结果"，返回中文结论与推荐链路。会消耗少量额度，只在用户主动点时跑。
- **代理软件兼容开关**：面板一键切 `[net] ssrf_allow_ranges`（默认放行 `198.18.0.0/15`），
  解决 Clash/mihomo **TUN + fake-ip** 模式下 `fetch` 对所有公网网址报"域名解析到了本地/内网地址"
  而完全不可用的问题。放行**只对域名解析结果生效**，字面内网 IP、`169.254.169.254`、
  `*.local`、`localhost` 等照旧拒绝。
- **坏密钥 / 额度耗尽的明确提示 + 自动回落**：`ApiKeyRejectedError` / `QuotaExhaustedError`
  分开分类，本次搜索自动降级回匿名档，不再静默跳过后端让人误以为"搜索坏了"。
- **百度 BAIDUID 预热**：裸请求必中"百度安全验证"页，先访问首页领 cookie 再搜。

### 变更

- 默认后端链路 → `exa → anysearch → bing → baidu`（实测直连可用性排序）。
- `duckduckgo` 移出默认链路：仅在检测到系统/环境/显式代理时才进实际链路（`duckduckgo_needs_proxy`）。
- `exa_tool = "auto"` 恒用快路径 `web_search_exa`。原计划"有密钥用 advanced"被实测推翻：
  advanced 3.7–11.7s 的抖动来自它自己抓页面、与是否带密钥无关，会顶穿单后端 12s 预算。

### 修复

- **单位不一致**：自检结果字段 `ms` 里装的是秒，面板按毫秒渲染（1.2 秒会显示成"1 ms"）。统一到毫秒。
- **百度被自己的过滤规则误杀**：`baidu.com/link?url=` 是真实 `302` 跳转（可正常跟随），
  却一律按"打不开的壳"丢弃，导致解析出 8 条高分结果仍报"未返回可解析结果"。JS 壳页仍由
  `_check_block` 单独判定，两者不再混为一谈。
- **坏密钥被误报成"没有结果"**：Exa MCP 对无效密钥返回 `HTTP 200` + `result.isError`，
  而旧代码只看 JSON-RPC 层的 `error`，永远看不到它。
- `_mcp_error` 的错误文案匹配改为带边界的数字匹配，避免服务端文案里出现 `1401` 之类数字时被误判成
  "你的密钥无效"（那会把用户推去重新注册，而不是让他重试）。

### 工程

- 门禁：`pytest 202 passed`、`ruff@0.12.4 All checks passed`、`neko-plugin check 0 error`；
  真机（ mainland 直连、代理关闭）行为验收 19/19。
- 仍然**零第三方依赖**（只用标准库），分发包无 `vendor/`。
