# A股短线新闻雷达操作手册

> **定位：** 本文件是项目的**单一权威操作手册**，用于 Codex 桌面客户端、Codex CLI 和新会话接手。新闻方法以当前项目规范为准，实际命令以仓库代码为准。
>
> **当前边界：** 仓库具备确定性的 Markdown 解析、HTML 构建、测试和可选发布能力；**当前没有自动生成新闻 Markdown 的程序**。Markdown 由采集、候选对账、事件化、评分、题材聚合和编辑流程生成。
>
> **安全边界：** 不读取、保存或输出密码、Cookie、Local Storage或浏览器历史。推送和发布需要单独明确授权；运行本手册的构建或测试不会启用自动任务。

## 1. 项目心智模型

完整数据流如下：

```text
来源发现与窗口清单
  -> evidence/ 证据、热度快照与失败记录
  -> 候选账本（每条必须有最终状态）
  -> 事件去重、热点权重、题材聚合
  -> reports/YYYY-MM-DD-HHMM-<slug>.md
  -> python3 -m web.build
  -> web/dist/ 静态 HTML
  -> 单元测试 + Chrome 布局验收
  -> 可选：market-news-site / GitHub Pages
```

这里有两条必须分开的流水线：

1. **内容生产流水线：** 新闻来源、时间、热度和语义判断会变化，由代理或人工完成并产出 Markdown。
2. **页面构建流水线：** 输入 Markdown 与固定模板后，`web.build` 确定性生成 HTML；模板、CSS 和 JS 不随每日报告重复编写。

关键目录：

| 路径 | 用途 |
|---|---|
| [`../reports/`](../reports/) | 每期 Markdown 报告，HTML 的内容源 |
| [`../evidence/`](../evidence/) | 来源快照、候选、热度基线、召回和验证证据 |
| [`../web/report_parser.py`](../web/report_parser.py) | Markdown 解析和结构校验 |
| [`../web/report_catalog.json`](../web/report_catalog.json) | 历史非标准命名报告的兼容目录 |
| [`../web/templates/report.html`](../web/templates/report.html) | 固定 HTML 模板 |
| [`../web/assets/`](../web/assets/) | 固定 CSS 和 JavaScript |
| [`../web/dist/`](../web/dist/) | 可部署静态站产物 |
| [`../tests/`](../tests/) | 报告、解析、构建、发布、安全和浏览器验收 |

方法与历史说明：

- [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md)：来源、时间窗口、热度、完整性和维护规则。
- [`2026-08-11-theme-aggregation-method-uat.md`](2026-08-11-theme-aggregation-method-uat.md)：当前题材聚合语法、反漏采控制和 UAT。
- [`../HANDOFF.md`](../HANDOFF.md)：项目历史交接和已知限制。
- [`uat/2026-08-12-high-fidelity-report-shell.md`](uat/2026-08-12-high-fidelity-report-shell.md)：当前高保真页面验收记录。

历史文档中的“未合并”“未发布”“不是 Git 仓库”等状态只代表记录当时，不应覆盖本手册和当前代码、Git 状态的现场检查结果。

## 2. 新环境或新会话准备

### 2.1 基础检查

```bash
cd /path/to/market_news
git branch --show-current
git status --short
python3 --version
node --version
```

迁移到另一台机器时，项目路径可以变化；直接使用本节相对命令。只有 [`../scripts/run_morning_site.sh`](../scripts/run_morning_site.sh) 当前固定写了两个本机绝对路径，迁移机器后应先把 `project_dir` 和 `site_repo` 改为新路径，并重新运行入口测试。

### 2.2 桌面客户端与 Codex CLI 的能力边界

- **Codex CLI：** 适合读取公开网页/API、处理本地文件、生成 Markdown、构建 HTML、运行测试和 Git 操作。
- **桌面客户端：** 当任务依赖微博、雪球、X、淘股吧等**已登录浏览器会话**，优先使用桌面客户端的 Chrome 控制；只读取页面可见内容。
- CLI 不能稳定继承桌面 Chrome 的登录态。登录渠道不可用时，应记录失败并继续公开来源，不要伪造互动量，也不要要求用户提供密码、Cookie、Local Storage或浏览器历史。
- 财联社、东方财富等动态页面如果 CLI 取不到正文，可使用桌面浏览器从站内入口点击；仍必须保存具体文章/电报直链和北京时间。

### 2.3 新会话先读什么

任何新会话都应**先完整阅读**：

1. [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md)
2. [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md)
3. [`2026-08-11-theme-aggregation-method-uat.md`](2026-08-11-theme-aggregation-method-uat.md)
4. [`../HANDOFF.md`](../HANDOFF.md)
5. 最新一份 [`../reports/`](../reports/) Markdown
6. 最新相关 [`../evidence/`](../evidence/) 与 UAT 文件

开始前运行 `git status --short`。已有修改属于用户或其他会话，不能覆盖、重置或顺手提交。

## 3. 如何生成一份 Markdown 报告

### 3.1 选择报告时段与新闻窗口

新文件推荐统一命名：

```text
reports/YYYY-MM-DD-HHMM-<slug>.md
```

常用时段：

| `HHMM` | 页面标签 | 典型截点 |
|---|---|---|
| `0800` | 盘前 | A股开盘前实际采集截点 |
| `1200` | 午间 | 上午收盘后实际采集截点 |
| `1500` | 盘后 | A股收盘后实际采集截点 |

不要为了文件名伪造截点；报告正文必须写实际采集完成时间。普通交易日窗口从前一交易日 `00:00:00` 开始，到本期实际截点结束。周一从上周最后一个交易日 `00:00:00` 开始；节假日后首日从节前最后一个交易日 `00:00:00` 开始，覆盖中间所有自然日。交易日必须使用可靠交易所日历确认。

所有时间统一换算为**北京时间**，同时保留必要的原始时区信息。只有日期或无法确认时区时，明确写“来源页面未显示精确分钟/可靠时区”，不能补造分钟。

### 3.2 建立来源窗口与候选账本

至少覆盖以下来源层：

1. 官方、监管、交易所、公司公告与 IR。
2. 国内财经媒体和 7×24 快讯。
3. 财经社区、题材社区、公共热榜与登录渠道。
4. 海外主流媒体、科技媒体和产业垂直源。
5. 相关市场行情和发布后可观察反应。

早报和汇总稿只用于发现；其中每一个独立事实都要生成候选。事件身份使用：

```text
主体 + 动作 + 对象 + 发生时间 + 具体URL
```

实行**零静默丢弃**。每个来源条目的最终状态只能是：

- `ranked`
- `merged_into:<event_id>`
- `excluded:<明确原因>`
- `pending_verification`

同题材不等于同一事件；合并必须保留目标事件 ID，排除必须保留具体原因。若财联社、东方财富等多家核心媒体出现同一重要事实，交付前必须完成跨媒体覆盖对账。

### 3.2.1 强制采集源清单（2026-08-16 用户裁定：每次跑任务必须全跑，不许少源）

**每次采集任务（含增量）必须按以下 7 源全部采集**，缺一不可；任何源未采集=任务未完成（除非记录失败原因并如实标注，不允许静默跳过）：

| # | 源 | 通道 | 入口 | 登录要求 |
|---|---|---|---|---|
| 1 | 新浪 7×24 | API 回放 | `zhibo.sina.com.cn/api/zhibo/feed?page={n}&page_size=100&zhibo_id=152&tag_id=0&dire=f&dpc=1` | 无 |
| 2 | 东方财富 7×24 | `scripts/fetch_em7x24.py` | `np-listapi.eastmoney.com/comm/web/getNewsByColumns?client=web&biz=web_724&column=350&order=1&page_index={n}&page_size=100&req_trace={n}` | 无 |
| 3 | 财联社电报 | 浏览器 DOM | `https://www.cls.cn/telegraph` | 无 |
| 4 | 韭研公社 | 浏览器 DOM / curl SSR | `https://www.jiuyangongshe.com/` | 无 |
| 5 | 雪球 | 浏览器 DOM | `https://xueqiu.com/`（热股榜+时间线+热门话题） | 登录（用户已在 IAB 登录） |
| 6 | X | 浏览器 DOM | `https://x.com/home`（Home timeline） | 登录（用户已在 IAB 登录） |
| 7 | 微博热搜 | 浏览器 DOM | `https://s.weibo.com/top/summary` | 登录（用户已在 IAB 登录） |
| 8 | 淘股吧 | 浏览器 DOM | `https://www.taoguba.com.cn/`（题材分布+复盘帖+极速快讯） | 登录（用户已在 IAB 登录） |
| 9 | 东方财富人气榜 | 浏览器 DOM | `https://guba.eastmoney.com/rank/?tab=rank-7&type=7` | 无 |

**执行顺序：** API 双源（1-2）→ 浏览器源（3-9）→ 九路并集去重 → 全窗口遍历分析 → 报告。
**浏览器源原则：** 只读页面可见内容，不读取/不输出任何凭据；登录由用户在 IAB 完成；webview 故障时按台账 §10.5 规则重试或如实记录缺源。
**增量采集：** 截点后的增量窗口同样按此清单执行（周末低密度时浏览器源快照仍须取，不得省略）。

### 3.3 15分钟并行工作流

盘前任务的性能目标是**15分钟内尽量交付**，但全面性和准确性优先：超过15分钟时不中断，继续运行直至完整交付。

有可用并行代理时，将发现阶段拆成三条独立检索流：

1. **海外与宏观**：海外市场、央行、地缘、科技公司、财报及相应市场反应。
2. **国内与政策**：官方政策、监管、交易所、公司公告、国内媒体与产业事件。
3. **登录渠道与热度**：微博、雪球、X、淘股吧等登录渠道的原帖、互动字段和双时点快照。

主代理负责统一候选账本、去重、跨媒体覆盖对账、题材聚合和最终编辑。只对热点权重**前10条**增加更深的背景、预期差和市场反应核验；这个范围只限制深度，不限制新闻数量，不能停止来源发现或丢弃合格长尾新闻。

### 3.4 热点权重与热度变化

当前单条热点权重为：

```text
覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10 = 100
```

- 分数只衡量传播热度，不衡量真假。
- 可靠性、资金验证、公告确认、个股映射、市场反馈和深度判断均不参与排序。
- 变化分只比较同一永久 URL、同一字段的**双时点**北京时间快照；不同字段或不同帖子不能计算百分比。
- 没有旧基线时写“新出现”或“不可比”，可以参与本窗口比较，但不要伪造增速。
- 窗口外旧闻只有在本窗口重新传播或热度明显变化时纳入，并保留原始时间、再传播时间和比较口径。
- 标题只写事件事实，不写“高热”“激增”“双时点未达阈值”等方法判断。

### 3.5 题材聚合

- 题材由当期新闻动态生成，不使用固定每日清单。
- 一个题材至少两条不同事件，且必须有共同产业链、事件链或催化逻辑；不能用空泛词凑组。
- 一条新闻可以跨题材，每个成立题材获得该新闻完整分数，不拆分；重复副本必须字段一致并披露关联。
- 题材分是成员新闻分数之和；**题材分不是市场总分**，不同题材不能再次相加解释为全市场热度。
- 未成题材的合格新闻进入“其他重要新闻”，仍保留完整字段。
- 待核线索不进入主榜、不形成题材、不计分。
- 直接映射和板块代表分层展示，均不计分、不继承热度、不构成投资建议。

### 3.6 新闻字段与特殊事件

每条新闻至少保留：

- 连续排名、稳定事件 ID、事实标题和热点分。
- `热点构成`与核心信息。
- 传播渠道、北京时间、相关市场`发布时段`和**具体直链**。
- 关键信号/预期差、可观察`市场反馈`或不可得原因。
- `判断边界`、热度变化和关联题材。

时段按新闻对应市场判断：中国新闻标中国市场盘前/盘中/盘后，美国新闻标美国市场盘前/盘中/盘后，不以报告本身的盘前/盘后代替事件市场时段。

特殊事件还需补充：

- **带明确日期的未来事件（2026-08-17 机制化）：** 当新闻明确提到未来日历事件（IPO 发行/聆讯、限售解禁日、停牌起始日、会议/决议日、数据发布日等）时，详情卡必须输出 `**事件日期：** <YYYY-MM-DD>（依据：<来源与原文>）` 字段——精确日或区间，`YYYY-MM-DD` 必须可被机器解析；日期未披露就写 `未取得（原因）`，绝不补造（P7）。带确定日期的条目可被下游事件日历机械并入。
- 新发财报：盘后或财报后首个可交易时段的价格反应、北京时间和来源；短线价格不等于长期认可，也不证明单一因果。
- IPO：询价日、`申购日`、证券代码；`上市日`未披露就明确写未披露，申购日不能写成上市日。
- 政策：写清主管部门、领域和已公开配套方案，未取得方案名称时不补造。
- 财务数字：同时展示显著增长、现金流或一次性因素等重要反差信息，避免只摘最亮眼数字。

**不收录（2026-08-16 用户裁定）：** A 股个股的涨跌结果本身不收录——涨停/跌停、龙虎榜、游资买入、资金流向、连板等盘面数据是"结果"而非"事件"，不单独成条。有实质事件的（分红、回购、业绩、公告、停牌核查等）以事件形式收录，标题写事件本身，不以涨跌表现为卖点；其他条目的"带时间市场反馈"里可保留盘面描述作为反馈。美股/板块/大盘的涨跌作为市场反馈照常保留。

**不合并（2026-08-16 用户裁定）：** 重要的机构评级/目标价行动（如大行上调个股评级或目标价）是独立利好事件，不与同板块的其他新闻合并成一条；即使与板块行情同时发生，也要独立成条，避免重要个股利好被合并条目稀释（例：NewStreet 上调美光至"买入"、目标价 1250 美元独立成条，不并入"存储板块大涨"条目）。

### 3.7 可直接复制的 Markdown 骨架

```markdown
# YYYY-MM-DD A股盘前新闻热榜

> **新闻窗口：** <前一交易日00:00:00>—<实际截点>（北京时间，Asia/Shanghai）。
> **实际截点：** <实际时间>（北京时间，Asia/Shanghai）。
> **排序口径：** 热点权重＝覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10。
> **时间口径：** 全部换算为北京时间；分钟不可得时明确说明。

## 单条新闻热榜索引

| 排名 | 事件ID | 新闻标题 | 热点分 | 关联题材 | 跳转锚点 |
|---:|---|---|---:|---|---|
| 1 | evt-YYYYMMDD-001 | <事实标题> | 80 | theme-example | [查看](#evt-YYYYMMDD-001) |

## 题材主线

### 主线1：<题材名>｜150分｜关联新闻2条

**题材ID：** theme-example
**核心催化：** <共同催化>
**题材风险边界：** <边界>

#### 新闻：1｜evt-YYYYMMDD-001｜<事实标题>｜80/100

**热点权重：80/100**（覆盖20 + 变化20 + 绝对热度16 + 新鲜度14 + 频次10）
**核心信息：** <核心事实>

| 传播渠道 | 北京时间 | 时段与信息 |
|---|---:|---|
| 官方/媒体 | MM-DD HH:MM | [具体原文](https://example.com/article) |

**关键信号/预期差：** <信息增量>
**带时间市场反馈：** <市场反应或不可得原因>
**判断边界：** <不能由现有证据推出什么>
**热度变化：** <双时点变化、新出现或不可比>
**发布时段：** <中国/美国市场盘前、盘中或盘后>。
**事件日期：** <仅当新闻明确提到未来日历事件时：YYYY-MM-DD（依据：<来源与原文>）；否则整行省略>
**关联题材：** theme-example

## 其他重要新闻

<!-- 使用与题材内新闻相同的完整字段。 -->

## 待核验线索

### <线索标题>
**已知事实：** <已知内容>
**待核原因：** <缺口>
[具体线索](https://example.com/pending)
```

完整语法、跨题材副本和负例以 [`2026-08-11-theme-aggregation-method-uat.md`](2026-08-11-theme-aggregation-method-uat.md) 为准。当前解析器最低可解析不等于可发布；上述发布字段不得因解析器未强制而省略。

## 4. 如何从 Markdown 生成 HTML

### 4.1 新报告如何被发现

推荐的 `YYYY-MM-DD-HHMM-<slug>.md` 会被解析器自动发现，无需修改目录。历史文件若不符合这个规则，必须显式加入 [`../web/report_catalog.json`](../web/report_catalog.json)，包括唯一 `report_id`、路径、日期、四位时段和标签。

不要把草稿命名成标准格式后留在 `reports/`；标准命名意味着它会进入网站归档。草稿应放在规划/证据目录，或使用不匹配标准规则的临时名称。

### 4.2 构建命令

在项目根目录运行：

```bash
python3 -m web.build --project-root . --output web/dist
```

成功输出类似：

```text
built <报告数> reports (<新闻数> items) in .../web/dist
```

构建器会：

1. 解析目录与标准命名报告。
2. 校验排名、题材成员、分数、副本和 HTTP(S) 来源等结构。
3. 使用固定模板、CSS 和 JS 生成每期 HTML。
4. 生成 `web/dist/reports.json` 和跳转到最新报告的 `web/dist/index.html`。
5. 执行公开树安全检查。
6. 全部成功后原子替换 `web/dist`；失败时不以半成品覆盖现有站点。

MD 生成好后，HTML 构建通常很快；耗时核心仍是新闻采集、核验、时间换算、候选对账和 Markdown 编辑。

### 4.3 本地查看

直接打开：

```text
web/dist/index.html
```

或仅在本机启动预览：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory web/dist
```

然后访问 `http://127.0.0.1:8765/`。该地址只在本机有效，不是公网链接。隔离工作树被删除后，原 `.worktrees/...` 文件地址会失效；应改用主仓库 `web/dist/...`。

## 5. 交付前验证

### 5.1 内容验收

逐项确认：

- 交易日、新闻窗口、实际截点和北京时间正确。
- 排名从 1 连续、热点分非递增、五项之和等于总分。
- 标题只描述事件；Top 10 和长尾新闻都保留规定字段。
- 每条至少有一个安全、具体、可点击的 HTTP(S) 来源。
- 题材至少两条且语义成立；题材总分与成员和一致。
- 候选账本无未处置条目，待核不计分。
- 财报、IPO、政策和旧闻异动满足特殊字段要求。
- 没有操作建议、买卖信号、伪造分钟或伪造互动数据。

### 5.1.1 来源齐全性验收（强制）

交付前逐项核对 3.2.1 强制清单：**9 个源每个都要有采集动作或失败记录**（evidence 文件、DOM 快照、或失败原因标注）。缺源即验收不通过，须补齐后再交付；不得以"该源本轮无新增"为由跳过采集动作。

### 5.2 自动测试

完整 Python 回归：

```bash
python3 -m unittest discover -s tests -v
```

真实 Chrome 布局、交互、移动端、打印和对比度验收：

```bash
node tests/report_layout_browser.mjs
```

代码与差异检查：

```bash
node --check web/assets/app.js
node --check tests/report_layout_browser.mjs
git diff --check
```

浏览器脚本需要本机 Chrome/Chromium；找不到时可设置 `CHROME_PATH`。环境失败不是通过，必须修复环境或明确记录未完成。

若只改了一期报告，先运行对应报告契约作为快速反馈，再运行完整回归。例如当前题材版：

```bash
python3 -m unittest tests.test_aug11_report_contract tests.test_aug11_theme_report_contract -v
```

最终结论只能引用最后一次内容/模板变更后的新鲜验证结果。

## 6. 可选发布到 GitHub Pages

静态站不需要 VPS。当前发布目标约定为本机兄弟仓库 `market-news-site`，由 GitHub Pages 托管。发布前必须确认目标仓库路径、远端、分支和工作区状态正确。

### 6.1 默认只检查，不发布

```bash
scripts/run_morning_site.sh
```

这是**默认 dry-run**：先重建 `web/dist`，再计算与站点仓库的差异；不复制、不提交、不 push。

等价的直接命令：

```bash
python3 -m web.publish --dist web/dist --site-repo ../market-news-site
```

### 6.2 显式发布

只有用户单独授权发布后才运行：

```bash
SITE_PUBLISH_MODE=apply scripts/run_morning_site.sh
```

该模式会调用安全发布器的 `--apply --commit --push`，因此同时产生外部状态变化。推送和发布需要单独明确授权，不能因为用户只要求“生成报告”就执行。

发布后应检查：

```bash
git -C ../market-news-site status --short
git -C ../market-news-site log -1 --oneline
git -C ../market-news-site rev-parse HEAD
git -C ../market-news-site rev-parse '@{upstream}'
```

确认本地 HEAD 与上游一致，并从公网链接抽查最新报告、历史归档和具体来源。

## 7. 自动任务边界

- 现有历史记录标记早间、午间和盘后自动任务为暂停；是否仍暂停应使用当前产品的自动任务只读接口重新确认，不能只凭旧文档断言运行时状态。
- `web.build`、`web.publish` 和 `scripts/run_morning_site.sh` 都不会创建、启用或恢复自动任务。
- Codex CLI 如果没有自动任务管理能力，只运行手动命令并记录实际时间；不要通过未审计的 cron/launchd 替代既有产品自动任务。
- 任何启用、停用、改时或删除自动任务都需要用户明确授权；生成 MD/HTML 本身不会启用自动任务。

## 8. 常见故障

### 新 Markdown 没进入网页

检查文件名是否满足 `YYYY-MM-DD-HHMM-<slug>.md`。历史非标准文件需加入 `web/report_catalog.json`。不要通过复制 HTML 绕过解析器。

### 构建报排名、题材或来源错误

按错误回到 Markdown 修复：排名必须连续且分数非递增；题材成员至少两条、总分等于成员和；索引、题材和其他新闻集合必须一致；每条排名新闻至少一个 HTTP(S) 具体直链。

### 登录来源取不到数据

记录渠道、尝试时间和失败原因，使用公开媒体/官方源继续；互动字段写“未取得”。需要登录态时切换桌面客户端，不读取凭据，不要伪造或用不同字段替代。

### 页面地址突然失效

`localhost` 依赖预览服务，`file://.../.worktrees/...` 依赖隔离工作树。优先重新构建并打开主仓库 `web/dist/index.html`。

### HTML 与 Markdown 内容不一致

重新运行构建和 `test_checked_in_dist_is_byte_identical_to_a_fresh_build` 所在的完整测试。禁止手工只改 `web/dist/*.html`；根因应在 Markdown、parser、模板或构建器中修复。

### 发布器拒绝目标仓库

不要关闭安全检查。核对目标目录名、远端、分支、未提交/未跟踪文件和 `web/dist` 安全扫描；在 dry-run 通过前不能 apply。

## 8.5 每日盘前采集固化流程（2026-08-18 用户裁定：确保之后都会采集、不遗漏）

**这是每次盘前报告必须完整执行的采集顺序。各环节是否完成由 `scripts/daily_scrum.py` 核查，缺一不可；[MISS] 项必须补齐才能发布报告。**

```
步骤 0  登录态/浏览器核验（如使用浏览器源）
步骤 1  API 源（并发，约10s）
        python3 scripts/fetch_api_sources.py --start "<YYYY-MM-DD 00:00>" --out-dir evidence
步骤 2  浏览器源（IAB 串行）：韭研公社 / 东财人气榜 / 微博热搜 / 淘股吧 / 财联社电报 / 雪球
        → evidence/<key>-<MMDD>.txt  （key 见 daily_scrum.py 第2节清单）
步骤 3  X 大V扫描（WebFetch 通道，不依赖 IAB，priority 顺序执行）
        for handle in config/x-influencers.json#priority:
          WebFetch "https://x.com/<handle>" → 提取最近5条帖文
          python3 scripts/save_x_scan.py --handle <handle> --date <date> --text <结果>
        + X Home timeline（如有浏览器会话）→ evidence/x-timeline-<MMDD>.txt
步骤 4  次日素材衔接：读 data/next-day-leads/<今日>.md（昨日生成）并入候选账本
步骤 5  完整性核查（必须全绿才继续）
        python3 scripts/daily_scrum.py --date <YYYY-MM-DD>
步骤 6  分析：python3 scripts/scan_evidence.py --sina ... --em ... --with-link-only
                        （候选账本 + [BBG]/[RT]/LINK 标记）
步骤 7  填数据层 data/reports/<date>.json → python3 scripts/gen_report.py --data ... --out ...
步骤 8  构建/测试/部署（现有流程）
```

**关键脚本（已固化）**：
- `scripts/fetch_api_sources.py`：并发抓新浪7×24+东财7×24（此前手写串行提速 ~7x）
- `scripts/scan_evidence.py`：主题词带扫描，输出候选账本，标 [LINK]/[BBG]/[RT]
- `scripts/daily_scrum.py`：每日采集完整性核查（API/浏览器/X大V/timeline/报告），[MISS] 即退出非零
- `scripts/save_x_scan.py`：把 WebFetch 返回落盘为 evidence/x-<handle>-<date>.txt（统一命名）
- `scripts/gen_report.py`：读 JSON 数据层生成符合解析器契约的报告（沿用 8.2）
- `config/x-influencers.json`：X 大V清单（priority/deprecated/pending_verification）

**不遗漏保证**：`daily_scrum.py` 在每天采集后强制执行（步骤5），X 大V文件名统一 `x-<handle>-<MMDD>.txt`（save_x_scan 保证），漏任何源都会 [MISS] 阻止进入生成。次日素材（next-day-leads）在步骤4读取，从数据上杜绝"上一天发现、次日忘用"。

**X 大V通道说明**：X 公开主页由 WebFetch 工具提取（curl 无 SSR 数据，无法脚本化直抓）；主代理对每个 handle 依次调用 WebFetch 后用 save_x_scan 落盘。若某个 handle 超时（WebFetch 不稳定），记入当日缺口并在次日重试，**不跳过不省略**。



### 9.1 Codex CLI

```text
继续 A股短线新闻雷达项目，工作目录为当前 market_news 仓库。

请先完整阅读：
1. docs/OPERATIONS_RUNBOOK.md
2. docs/PROJECT_GUIDE.md
3. docs/2026-08-11-theme-aggregation-method-uat.md
4. HANDOFF.md
5. 最新 reports/*.md
6. 对应 evidence/ 与 docs/uat/ 记录

先运行 git status --short，保留已有修改。按操作手册生成本期 Markdown，再运行：
python3 -m web.build --project-root . --output web/dist
python3 -m unittest discover -s tests -v
node tests/report_layout_browser.mjs

所有时间统一为北京时间；执行零静默丢弃候选对账；标题只写事件事实；保留具体直链、市场时段、可观察反应与判断边界。CLI无法取得登录渠道时明确记录失败，不读取或要求密码、Cookie、Local Storage或浏览器历史。不要推送、发布或启用自动任务，除非我另行明确授权。
```

### 9.2 桌面客户端（需要登录渠道）

```text
@Chrome 继续 A股短线新闻雷达项目，工作目录为当前 market_news 仓库。

先完整阅读 docs/OPERATIONS_RUNBOOK.md、docs/PROJECT_GUIDE.md、docs/2026-08-11-theme-aggregation-method-uat.md、HANDOFF.md、最新报告与证据。

使用当前已登录浏览器会话补充微博、雪球、X、淘股吧等页面可见时间与热度字段；不要读取或输出密码、Cookie、Local Storage或浏览器历史。公开来源与登录来源统一进入候选账本，完成零静默丢弃对账后生成本期 Markdown，再构建 HTML 和执行完整验证。不要推送、发布或启用自动任务，除非我另行明确授权。
```

## 10. 每期最短操作清单

1. `git status --short`，确认并保护已有修改。
2. 用交易所日历确定窗口和实际截点。
3. 建来源窗口、证据文件、热度基线和候选账本。
4. 完成事件身份、跨媒体对账和四状态处置。
5. 计算单条热点权重，按事实标题排序。
6. 动态生成题材，补齐全部新闻字段和待核附录。
7. 保存为 `reports/YYYY-MM-DD-HHMM-<slug>.md`。
8. 运行 `python3 -m web.build --project-root . --output web/dist`。
9. 运行完整单元测试和 `node tests/report_layout_browser.mjs`。
10. 用户只要求本地报告时到此停止；发布、推送、自动任务分别重新取得授权。
