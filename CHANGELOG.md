# 更新记录

## v0.4.0（2026-09-19）

面板新增「最近一次搜索」卡：把只有日志知道的事实搬到用户眼前。

### 为什么要加这一张卡

2026-09-19 那轮真机排查里，"这次搜索到底走的 exa、还是退回匿名档了"**没法直接回答**：宿主不记插件的
工具返回体（`neko-electron-debug.log` 只有 `Dispatching UserPlugin: plugin_id=…, entry_id=search` 一行），
而我们自己也只在 `N.E.K.O_Plugin_better_web_search_<日期>.log` 里留一句
`search answered: backend=exa count=5 attempted=['exa']`。当时判定"19:41–19:44 的 5 次全部由 exa 在 2 秒内
答上"，靠的是日志 grep；换一个人问"我的密钥到底用上没"，就只能看 ready 行的 `exa_key=True` 加上"没有降级行"
这种反推。现在这件事在面板上是可见的：来源 / 条数 / 耗时 / 依次试过哪几路 / 当次要几条 / 什么时候。

### 怎么实现的

- `search` 入口拆成三段：`search()`（参数与 `max_results` 收敛，不变）、`_run_search()`（**原有的后端编排
  与回退逻辑一个字没动**，只是从 `search()` 里搬出来）、`_record_search()`（把这一次的形状化）。拆而不逐个
  补记录行，是因为失败出口有 6 个 `return Err(...)`，逐处加一遍迟早会漏一个。
- `_run_search` 连同 `attempted` 一起返回：一条结果都没有的情形最需要"走过哪几路"，而那条路径上没有 Ok
  载荷可以挂这个字段。
- 只存 `query_len`，**不存关键词本身**；`message` 也只存我们已经回给对话的那句，不新增任何没经过把关的
  字符串（异常原文可能带完整请求 URL，也就是带关键词——这条约束原本就写在 `search` 的注释里）。面板 context
  要过宿主，宿主会把状态与 context 原样写进日志。
- 从没搜过时 `last_search` 是 `{}`，面板用"有没有 `at`"判定有没有记录，而不是 `count == 0`：否则一台新机器
  会显示"0 条 / 没搜到"，看起来像刚刚失败了一次。
- 记录只在内存里，重启插件即清空。这张卡答的是"刚才那次"，不是历史统计。
- `attempted` 最多留 8 个名字，防着以后链路配长把 context 撑大。

### 「宿主内置『网络搜索』」那张卡补上推荐与代价

标题改成「宿主内置『网络搜索』（强烈推荐停用）」，下面写清三件事，全都有宿主源码行号背书：

- **为什么推荐停用**：两个搜索插件同时挂着时，这一轮用哪一个由模型挑，用户填的密钥、选的链路可能整轮没轮到。
- **停用会少掉什么**（这是本次新查的，之前 README 只含糊写过"几条路径"）：宿主里只有两处不经 LLM 工具、
  直接按 id 调用内置插件，`utils/web_scraper/window_context.py:404,521,761`（经
  `search_gateway.py:228`）与 `main_logic/topic/materials.py:73-101`。前者让主动聊天的「窗口」信息源拿不到
  资料并被丢掉（`main_logic/proactive_chat/sources.py:403-406` + `:481-487`，日志一行
  `信息源 [window] 获取失败`）；后者让主动话题的「找到了和某某有关的素材…」静默消失，而且
  `_safe_fetch`（`materials.py:244-251`）失败时**一行日志都不记**。B 站 / YouTube / Twitch 热搜、一起看、
  网页正文走各自的 httpx 通道，已确认不受影响。
- **不该承诺的事**：卡片没有写"停用之后她就会去搜"。决定搜不搜的是宿主自己的闸门
  `brain/task_executor.py:1958-1968`（`external_intent < 0.2` 且没有确定性信号 → 直接不派发任何插件，
  阈值在 `config/agent_settings.py:224`），插件碰不到；能写成文案的只有"一旦去搜，搜的就是这一路"。

用词统一：面板全篇用「停用」，所以标题也写「强烈推荐停用」而不是「关闭」，避免同一张卡里两种说法。

后面又补了两段，因为"会少掉什么"如果不带上"少掉的那部分平时到底影响多大"，等于把选择权又丢回给用户猜：

- **影响面**（`panel.host.impact`）：主动聊天共 11 种信息源（`main_logic/proactive_chat/sources.py:104-459`：
  news / community / video / home / personal / music / vision / window / meme …），**只有 `window` 需要搜索**，
  而且它默认是关的（`main_logic/proactive_chat/contracts.py:50,77` `use_window_search: bool = False`）；
  主动话题的联网增强虽然默认开着（`main_logic/topic/pipeline.py:270`），但失败时话题照发 —— 宿主自己的注释写着
  "Any failure leaves the cheap keyword floor hint intact"（`pipeline.py:962-966`），只是开场白退成关键词提示。
- **取舍建议 + 开回来的坑**（`panel.host.tradeoff`）：这里要更正一条我们一度写错的事实 —— 停用期间那两条路径
  **不会**把空结果写进宿主缓存：`search_gateway.py` 里 `_store()` 全程只有一个调用点（`:460`），走的是"插件跑完了
  但确实没结果"那条；插件停着时 `_invoke_plugin` 直接抛异常（`:369-373`）给该后端上 **300 秒失败冷却**且不写缓存，
  冷却期内后续调用在 `:345-347` 判为 throttle 返回旧缓存或空。所以"刚把内置开回来那几分钟还是空的"的真正原因
  是**还在冷却里**，文案按这个写。

#### 后来把三行警告撤了（同一天）

看过影响面之后决定：不影响正常功能的东西不必在面板上占三行警告。`panel.host.lostTitle` / `lostWindow` /
`lostTopic` / `unaffected` 四个键删除，卡片从 8 块回到 5 块 —— 意图说明 → 推荐理由 → 闸门归因 →
**一句**「会少掉的只有两处宿主功能，都不关键…」→ 一句取舍建议（"开回来要等 5 分钟冷却"这个坑保留）。
细节没丢：`README.md` 的「接管范围的诚实说明」仍然逐条带 `file:line`，含那两条路径、同名覆盖为何被安装侧
409 挡死、以及上面那条冷却与缓存的准确关系。静态用例两边都锁 —— 这一句披露不许消失，那四行警告不许自己长回来。

### `keywords` 补齐到"停用内置之后也不许少搜"

排查"她为什么不搜就答"时顺出来的一条真实回归风险（不是理论）：

- 宿主在派发前有一道闸门 `brain/task_executor.py:1958-1968` —— `external_intent < 0.2`
  （阈值 `config/agent_settings.py:224`）**且没有任何确定性信号**时直接 `return None`，整轮不派发任何插件；
- 插件侧唯一的确定性信号是把自己的 `keywords` 当**正则**去 `re.search`
  （`brain/plugin_filter.py:114-124`，见 `task_executor.py:1881-1905`）；
- 内置那份 `plugin/plugins/web_search/plugin.toml:5` 里有 `查[一找]`，命中「查一下」「查找」；
  我们原来只有字面 `查一查`，**匹配不上「帮我查一下 X」**。停用内置之后内置那份不再参与，这一类说法就少了兜底，
  撞上低外部意图的一轮就是不搜、凭记忆答。

所以 `plugin.toml` 的 `keywords` 补了 `查[一找]`、`帮我查`、`百度`、`探し`、`찾아`、`искать`、`найти`，
并保留我们原有的 `联网/网页/web/fetch/busca`。唯一刻意不对齐的是 `AnySearch`（那是后端品牌名，不是用户会说的话）。
新增 `test_keyword_shortcut_covers_what_the_builtin_matched`：把内置那份抄成断言（CI 只检出本仓库，不能去读宿主树），
再用 6 句人话（含俄语、韩语）逐个跑宿主那套匹配语义，少一个模式或某句话匹配不上都会红。

#### 当晚 22:45 的一次真实"没搜"，把这份列表又推宽了一轮

用户实录：「你仔细帮查查然后总结一下给我」→ 她回「本喵这就去仔细查…」，但**一次搜索都没发生**。
插件日志里那段时间没有任何 `TRIGGER entry='search'`；宿主日志给出了原因（对齐到毫秒）：

```
22:44:33.397  [TaskExecutor] Dispatching UserPlugin: better_web_search / search   ← 上一轮是好的
22:45:07.504  [AgentGate] skip assessment: external_intent=0.00 < 0.20, no deterministic signal
22:46:04.590  [TaskExecutor] Dispatching UserPlugin: better_web_search / search   ← 被质问之后才搜
```

三条结论：

- **那句承诺是宿主提示词要求说的**：`config/prompts/prompts_sys.py:170-172` 让模型在被要求执行操作时
  "只能简短说明会尝试处理"，而对话模型手里**没有**任何搜索工具（只有 `recall_memory`；插件入口靠 analyzer
  那条链路，不是 `@llm_tool`），所以"我去查"和"真去查"本来就是两条互不知道的路。
- 刹车的是 `external_intent=0.00` + 没有确定性信号。确定性信号只有插件 `keywords` 这一处能左右，
  而「查查」——内置的 `查[一找]` 和我们的旧写法**都**匹配不上。
- 于是把这轮补成带否后视的一条正则：`(?<![调检侦考审警探追巡])查(?:[一下询找看]|查|资料|了)`，
  外加 `搜(?:[一下]|一搜|搜)` 和 `look\s?up`。14 句人话全命中（含用户那句原话、검색해줘、調べたい），
  8 句闲聊零误命中，且顺带**消掉了内置会犯的**"检查一下身体/调查一下/审查一下"三类误伤。

**为什么到此为止、不加裸 `查|搜`**：命中不只是"多跑一次评估"。`task_executor.py:1503` 会把命中的插件
强推进 Stage-2 候选，`:1525` 在提示里把它标成 `[KEYWORD MATCH]`，而 `config/prompts/prompts_agent.py:370,414,458`
要求模型优先选打了标的插件 —— 误命中会变成一次真搜索，还会占用引擎冷却（`baidu_min_interval` 10s、
`cooldown_seconds` 60s 这类），把后面真正该搜的那轮挡在门外。这条边界写成用例里的两份清单。
`test_keyword_shortcut_covers_what_the_builtin_matched` 同时断言"内置能命中的真查语句我们一句都不能少"，
并把三处刻意收窄单独记账，免得以后有人拿"对齐内置"当理由把守卫删了。

### 面板重排：一屏 2764 字 → 分三区 + 折叠

用户反馈"全是文字，乱糟糟"。量出来的确实现实：129 条文案、2764 个中文字符平铺在一张滚动页上，
其中我刚加的内置搜索卡一张就 687 字。还有个视觉放大器：**kit 里的 `<Tip>` 不是灰字注释，是带琥珀色
边框的提示盒**（`ui-kit/styles.css` `.neko-tip`），而我们在卡片里一张塞了 2–4 个。

- `renderHome` 改成 `Tabs` 三区：**状态**（最近一次搜索 + 当前链路）/ **设置**（密钥 + 内置搜索开关 +
  代理兼容）/ **诊断**（网络自检）。`Tabs` 的 `items[].content` 只有当前区会挂载，所以另外两区的文字
  根本不进 DOM。
- 解释性长句一律进默认收起的 `Accordion`（`open={false}`）：为什么推荐停用、停用会少掉什么、这次搜索
  走过哪几路、为什么少了某个来源、虚拟地址放行是干什么的、自检测的是什么、额度怎么算。
- 全篇 `<Tip>` 清零（`grep` 断言钉住），"免费额度"那张单独的卡收进密钥卡的一条 `Alert`，少一张卡。
- 新组件不是没代价：`Tabs`/`Accordion` 的展开状态存在 kit 的模块级 `Map`（`useLocalState`），
  **面板 iframe 一重载就回到默认**，不会记住用户展开过什么；宿主自带的三个面板（mcp_adapter /
  lifekit / netease_music）也都没用过这两个组件，所以观感是新 territory。
- 可见文案 2764 → 1375 字，最长单条 128 → 51（`panel.host.mismatch` 是被新加的预算用例抓出来的，
  压短的同时保留了"点重新停用、别再拨开关"和原因）。
- **顺带发现：面板是可以真类型检查的**，不必装宿主 `frontend/node_modules` —— 临时 `npm i typescript`，
  照抄宿主 `plugin/sdk/hosted-ui/tsconfig.json` 的 compilerOptions 指到它自带的 `.d.ts` 上就能跑，
  本次 `tsc` 干净通过（含 `noUnusedLocals`，它正好抓出了没人用的 `Tip` import）。命令记在 README。

### 用例

232 → 242。新增：成功记录（来源/条数/回退链/耗时/时刻）、失败记录用的就是对话看到的那句文案、空结果保留
走过的链路、关键词过短**不**覆盖上一次记录、context 与记录里都 grep 不到关键词本身；面板侧四条静态用例
（`ui/` 没有渲染测试，只能锁源码形状）：回看卡判据是 `at` 而不是 `count`、内置搜索卡必须同时带着
"推荐停用"与"停用会少掉什么"这两块文案且不许出现"每次都会搜"这类承诺、三区版式与 `<Tip>` 清零、
以及那条可见文案字数预算。再加一条关键词兜底对齐用例。


## v0.3.0（2026-09-19）

改名：**免费联网搜索 / `free_web_search`** → **更好的网络搜索 / `better_web_search`**。功能、配置项、
面板行为一个字没动；"不需要任何 API Key"仍然是首要卖点，只是不再写进名字里。

### 改名波及的面

- 插件 id、`entry`（`plugin.plugins.better_web_search:BetterWebSearchPlugin`）、类名
  `FreeWebSearchPlugin` → `BetterWebSearchPlugin`、面板默认导出组件名、错误码前缀
  `FREE_WEB_SEARCH_*` → `BETTER_WEB_SEARCH_*`、`pyproject.toml` 的项目名、首启话术里自称的名字、
  `search` 入口喂给模型的 `name`、ready 日志前缀、`push_message` 的 `source`，以及
  `.github/workflows/{verify,release}.yml` 里当参数写死的 `plugin-id:`（这条最容易漏——它本地全绿，
  只在 GitHub 上才炸）。
- **插件中心显示的名字来自 i18n，不是 `plugin.toml`**：宿主
  `plugin/server/application/plugins/query_service.py:211-222` 用 `plugin.name` 这个 i18n 键**覆盖**
  `[plugin].name`（TOML 只在缺键时兜底）。所以真正看得见的名字改的是 `i18n/zh-CN.json` 与
  `i18n/en.json` 的 `plugin.name` + `panel.title`，TOML 那份只是 Market 侧的兜底。
- 附带收益：Market 要求的仓库名是 `n.e.k.o_plugin_<id>`，而比对是 `casefold()`
  （`release_cmd.py:231`），所以 GitHub 上现有的 `n.e.k.o_plugin_Better_web_search` **直接就过了**，
  不用再去改仓库名——这是 v0.2.1 时记下的那条发布阻塞的直接解除。

### 装过旧版的要注意（真实代价）

- **配置不会跟着搬**：宿主没有"改 id 就迁移数据"这回事。`plugin/core/registry.py:1461`
  的 `_migrate_plugin_id` 只搬进程内的注册表映射（hosts / event handlers / entry 方法表），
  磁盘上的 `plugins/free_web_search/config/plugin.toml` 原封不动，新 id 从空白配置开始 ⇒
  **Exa 密钥、`[host].takeover_search` 意图、引导进度都要重填一次**。
- **必须先卸载旧插件**：包里声明了 `[plugin].previous_ids = ["free_web_search"]`，旧插件还装着时
  导入会被直接判为 `reason=legacy_plugin_present` 并弹冲突提示（`install_plan.py:135-153` →
  前端 `usePluginPackageInstaller.ts:88-101`）。这是故意的：新旧两份都注册 `search` 工具同时活着，
  比装不上更糟。
- 日志文件名会跟着 id 变成 `N.E.K.O_Plugin_better_web_search_<日期>.log`；老的
  `..._free_web_search_...` 那份是历史，不用管。
- 内置搜索的停用状态存在宿主的 `plugin_runtime_overrides.json` 里、按内置插件自己的 id 记账，
  所以换名**不会**把内置 `web_search` 悄悄启回来；新插件启动时会按重填后的 `[host].takeover_search`
  重申一次。

### 用例

新增 `test_name_is_the_same_everywhere`（231 → 232）：id、`entry` 里的类名、`pyproject.toml` 项目名、
i18n 显示名、TOML `name` 五者互相对齐，并把运行期会碰到的文件（`__init__.py`、`_*.py`、
`ui/panel.tsx`、两份 i18n、`docs/quickstart.md`、两份 workflow）整体扫一遍——出现任何旧标识符就失败。

选在这时候改 id 的理由：本仓库至今零 tag、从未上过 Market，除了用户自己机器上的导入记录没有任何
历史包袱；发布之后再改就要永久背着 `previous_ids` 和别人的配置了。

## v0.2.1（2026-09-19）

一轮"说的和做的对上"的修正：把配置项、自检、开关语义、面板文案与真实行为重新对齐，并顺手把
分发包里不该出现的东西拿掉。全部有离线单测兜底（202 → 231 个用例）。


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

### 面板响应与开关语义（第二轮实机反馈）

- **先认一个回归**：上一版把开关改成 `checked={hostKnown && !hostRunning}`（位置跟随实时状态）是
  设计错误。因为位置由状态决定，用户"再点一下确认停用"时发出去的是 `enabled=true` ——
  **把内置搜索又启动了**。实机日志正是这样：22:43:36 / 22:43:57 / 22:45:56 / 22:46:06 四次
  `set_host_search`，紧接 22:46:07 内置 `web_search` 进程 Started，宿主
  `plugin_runtime_overrides.json` 也从 `enabled:false` 回到 `true`。现在开关只反映
  `[host].takeover_search`（用户意图，点下去就落盘，绝不因读取失败而回弹），实际运行状态只由徽章表达。
- **意图与实况不一致时不再靠用户瞎试**：徽章显示还在跑而你已经选择接管时，卡片给出黄色提示 +
  「重新停用」按钮，并把上次失败原因（`takeover_error`）显示出来，而不是只写进日志。
- **开关不再卡住**：`panel_context` 现在带 20 秒的主机状态缓存 —— 面板每个动作结束都会刷新上下文，
  以前每次都付一次回环读（2.5 秒封顶）。失败的读取**不进**缓存（否则错误会变成"真相"）；
  切换开关会强制失效缓存，所以刷新时一定拿到实况。「重新检查」按钮仍走实时读并顺手回填缓存。
- **写入超时 4s → 8s**：实机看到宿主在 `ready:` 之后 4–5 秒才回 `PLUGIN_NOT_RUNNING`，
  4 秒预算必然超时并被报成"未能连接宿主管理接口"，正是诱导用户重复点击的原因。
- `_persist` 在"丢回执"路径上不再连做两次 `config.dump`（回读校验本身就 reload 过），省掉一个 5 秒往返。
- `search` 成功时记一行 `search answered: backend=… count=… attempted=[…]`。宿主不记工具返回，
  以前事后无法回答"这次到底是哪个后端答的、我的 key 用上没有"。
- README 增加**接管范围的诚实说明**：宿主的窗口上下文 / 话题素材等路径
  （`utils/web_scraper/search_gateway.py`）硬编码调用内置 `web_search`，停用内置后它们只是安静地
  返回空结果，**不会**改走本插件。

### 打包

- **`neko-plugin` 命令入口可能解析到另一份旧宿主检出**（本机实测：`F:\ai\N.E.K.O`），那份 CLI 还没有
  entry 元数据探测步骤，于是 `build` 照样打 `[OK]`、**不给任何警告**，产物里却没有 `plugin.meta.json`。
  宿主只能退回"从 manifest 猜入口"，静态注册表得到空集；此后面板每个按钮都回
  `UI action 'xxx' is not a plugin entry`（404）。该文案由宿主
  `plugin/server/application/plugins/ui_query_service.py` 的 `if not entry_ids` 分支产生，
  它判断的是"整个集合为空"，却按"你点的那个 id 不存在"的口气说话。
  改用 `python -m plugin.neko_plugin_cli` 构建（与 cwd 无关，两边实测都能出 meta），
  README 补了一行包内自验命令。
- **分发包瘦身：41 个文件 / 484 KB → 24 个 / 332 KB（压缩后 159 KB → 109 KB）**。v0.2.0 的包里
  有 16 个文件、135 KB 是 `tests/fixtures/` 下 Bing/百度/DuckDuckGo 的**真实抓取页面**，另有
  18 KB 的 `docs/plan-v0.2.md` 内部施工单——两者都是本仓库自测的输入，不是运行期需要的东西。
  宿主默认排除表（`neko_plugin_cli/core/build_rules.py:18-39`）不含 `tests/`、`docs/`，所以在
  `pyproject.toml` 的 `[tool.neko.build]` 里补了 `exclude_dirs = ["tests"]` 与
  `exclude = ["docs/plan-*.md"]`。`docs/quickstart.md` **必须**留下（`[[plugin.ui.guide]]`
  的 entry 指着它），新用例 `test_packaging_excludes_dev_payload_but_keeps_ui_files` 就是把
  manifest 声明的 UI 文件逐个拿去套宿主自己的匹配语义来兜这条底。`tests/` 仍留在 git 仓库里
  （宿主 `validate_cmd.py:112` 在 `--strict` 下要求 `tests/test_smoke.py` 存在），只是不再进包。
- **上一版 README 关于 `__pycache__` 的归因是错的，结论对**。实测：不带
  `PYTHONDONTWRITEBYTECODE=1` 构建，源码树 `__pycache__/` 里每个文件的 mtime 都不变，包里却
  实实在在多出 8 个 `.pyc`（159 KB → 290 KB）。真正的机制是排除规则只在**复制到暂存树**那一步
  生效（`core/build.py:342`），随后 entry 探测 import 的是**暂存副本**（构建日志里的
  `%TEMP%\neko_build_<id>\payload\plugins\…\plugin.toml` 就是它），字节码写在暂存树里，而
  `export_package` 直接把暂存树 zip 掉、不再套一遍规则。所以"`exclude_dirs` 写 `__pycache__`"
  挡不住，只有那个环境变量挡得住；清理源码目录也没用，因为根本不在源码目录。
- **Market 发布有两个硬前置**（读代码确认，本机 origin 目前过不了第一条）：仓库名必须是
  `n.e.k.o_plugin_<plugin_id>`，否则 `release_cmd.py:230-232` 直接报 error；tag 必须等于
  `plugin.toml` 的 `version`（`release_cmd.py:237-239`）。本仓库现在的 origin 是
  `…/n.e.k.o_plugin_Better_web_search`，所以**打 tag 触发的 release 工作流会被名字这条拦住**；
  改名不在本次改动范围内（要改的是 GitHub 上的仓库名，改完 `git remote set-url` 即可）。
- 新增 `test_release_version_is_stated_once`：`plugin.toml` 与 `pyproject.toml` 的版本号必须一致，
  且 CHANGELOG 顶端那一节必须是已定版的版本号（不许带着"未发布"发版）。宿主侧没有任何一处比对
  这两个文件，只有 tag 与 `plugin.toml` 相比对。
- `PANEL_ENTRY_IDS` 一直漏记 `set_ssrf_guard`（它有行为用例，但没有"面板调的 id 必须在
  `__init__.py` 里声明成 entry"这条保护），补进列表。

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
