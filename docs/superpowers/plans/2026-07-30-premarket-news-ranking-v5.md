# 2026-07-30盘前新闻热榜V5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份截至2026-07-30盘前最新采集时点的A股纯新闻热榜，覆盖2026-07-29 00:00以来的全部可核消息及窗口内突然升温的旧闻。

**Architecture:** 先固定北京时间新闻窗口，再通过登录Chrome和公开原始来源收集候选与时间/热度快照。按事件去重、识别窗口内新闻与旧闻异动，按已确认的五项权重统一排序，最后生成方案A紧凑报告和逐项证据表。

**Tech Stack:** Markdown报告与证据表、已登录Chrome可见页面、公开官方/媒体链接、Python只读结构验收。

## Global Constraints

- 主新闻窗口为`2026-07-29 00:00:00 Asia/Shanghai`至最终采集截点。
- 海外时间先换算为`Asia/Shanghai`再纳入和排序；原时区保存在证据表。
- 窗口外旧闻只有在窗口内取得可核显著升温证据才进入统一主榜，标记“旧闻异动”。
- 排序只使用覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10；可靠性、资金验证、个股映射和公告确认不参与排序。
- 每条使用方案A：标题/分数/状态 → 核心信息 → 传播渠道×北京时间表 → 最多三行紧凑尾注。
- 核验链接直接嵌入表格“消息或热度”详情文字，不另设核验路径行。
- 不读取或输出密码、Cookie、Local Storage或浏览器历史。
- 不给出“一眼结论”或任何操作建议。
- 当前目录不是Git仓库；提交、推送、PR、部署均为N/A。

---

### Task 1: 固定时间窗口与验收基线

**Files:**
- Create: `evidence/2026-07-30-premarket-monitoring-snapshots.md`
- Modify: `task_plan.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-29-trading-window-compact-news-ranking-design.md`
- Produces: 报告窗口起点、截点、时区和候选证据模板。

- [x] **Step 1: 运行RED结构验收**

  Run: `python3 -c 'from pathlib import Path; p=Path("evidence/2026-07-30-premarket-monitoring-snapshots.md"); assert p.exists() and "2026-07-29 00:00:00" in p.read_text()'`

  Expected: FAIL because the evidence artifact does not yet exist.

- [x] **Step 2: 建立证据表头与时间口径**

  写明前一交易日`2026-07-29`、当前交易日`2026-07-30`、窗口起点`2026-07-29 00:00:00`、采集截点和`Asia/Shanghai`。

- [x] **Step 3: 运行GREEN窗口验收**

  Run the Step 1 command again.

  Expected: PASS with exit code 0.

### Task 2: 采集盘前候选与热度快照

**Files:**
- Modify: `evidence/2026-07-30-premarket-monitoring-snapshots.md`
- Modify: `findings.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: 已登录Chrome中的微博、雪球、X，以及公开财联社、NewsNow、东方财富、韭研等页面。
- Produces: 按事件ID去重的候选，每项包含北京时间传播节点、具体链接、原始热度和失败边界。

- [x] **Step 1: 采集媒体与官方候选**

  记录2026-07-29 00:00以来财联社/NewsNow/东方财富和官方源的具体新闻、北京时间及永久链接。

- [x] **Step 2: 采集登录社交与投资社区快照**

  对主要候选采集微博、雪球、X和可访问社区的具体帖子时间、永久链接、原始互动或榜位。

- [x] **Step 3: 识别旧闻异动和孤立快照**

  窗口外事件只在窗口内取得同口径显著变化时标记旧闻异动；单快照明确写趋势数据不足。

- [x] **Step 4: 验证候选完整性**

  Run: `python3 -c 'from pathlib import Path; s=Path("evidence/2026-07-30-premarket-monitoring-snapshots.md").read_text(); assert s.count("## EVT-") >= 20; assert "北京时间" in s and "具体链接" in s'`

  Expected: PASS with at least 20 evidence events unless the evidence file explicitly documents fewer qualifying candidates and all checked-source counts.

### Task 3: 生成方案A紧凑主榜

**Files:**
- Create: `reports/2026-07-30-premarket-news-ranking-v5.md`
- Modify: `evidence/2026-07-30-premarket-monitoring-snapshots.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: Task 2候选、时间链、热度快照和永久链接。
- Produces: 按热点权重降序的V5盘前主榜。

- [x] **Step 1: 运行RED报告验收**

  Run: `python3 -c 'from pathlib import Path; p=Path("reports/2026-07-30-premarket-news-ranking-v5.md"); assert p.exists() and "| 传播渠道 | 北京时间 | 消息或热度 |" in p.read_text()'`

  Expected: FAIL because the report artifact does not yet exist.

- [x] **Step 2: 按方案A生成每条新闻**

  每条依次为标题/分数/状态、一至两句核心信息、传播渠道×北京时间表、热度/传播/边界紧凑尾注。

- [x] **Step 3: 嵌入可点击核验详情**

  所有具体文章、帖子、公告或榜单链接都放在表格第三列的相应详情文字中，报告不出现独立“核验路径”字段。

- [x] **Step 4: 计分并排序**

  验证每条总分等于五项分数之和，主榜按总分降序，同分按变化分和最近时间处理。

- [x] **Step 5: 运行GREEN报告验收**

  Run the Step 1 command again.

  Expected: PASS with exit code 0.

### Task 4: 独立审阅与最终验证

**Files:**
- Modify: `reports/2026-07-30-premarket-news-ranking-v5.md`
- Modify: `evidence/2026-07-30-premarket-monitoring-snapshots.md`
- Modify: `task_plan.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: 完整报告和证据表。
- Produces: 时间窗口、交易日、链接、计分、旧闻异动和紧凑结构的审阅结果。

- [x] **Step 1: 运行完整结构与语义验收**

  检查条目数、时间窗口、北京时间、总分加总/降序、表格字段、详情内链接、无独立核验行和禁用措辞。

- [x] **Step 2: 执行金融内容独立只读审阅**

  审阅重点为时间换算、首发/首次发现区分、热度证据、窗口外旧闻纳入和链接可回溯性。

- [x] **Step 3: 复现并修正阻断发现**

  对每个阻断发现建立定向失败断言，修正后重跑该断言和完整验收。

- [x] **Step 4: 记录最终结果与边界**

  记录通过/失败数、条目和链接总数、未取得渠道、无法验证的时间/热度字段，不把环境失败写成内容为空。

## Test Matrix

- Unit: N/A，本轮无可执行业务函数；以单文件结构/语义断言覆盖时间窗口和版式。
- Integration: 报告与证据表的事件、时间、分数和链接对齐；预期RED为文件不存在，GREEN为逐项完全对齐。
- UI: N/A，交付物为Markdown，不改动可执行网页；紧凑版式以Markdown渲染结构和可点击链接验收。
- Security/privacy: 只读取页面可见内容，不读取密码、Cookie、Local Storage或历史；报告不包含登录证据或私有标识。
- Generated artifacts: `evidence/2026-07-30-premarket-monitoring-snapshots.md` → `reports/2026-07-30-premarket-news-ranking-v5.md`；以Python只读断言验证完整性和旧输出不误用。
- Build/compile/lint: N/A，无代码或构建产物；使用Markdown结构、链接、分数和禁用措辞验收。
- Full baseline: 当前不存在2026-07-30报告与证据文件，RED断言为合理基线；无仓库全量测试套件，因此全套以报告+证据完整验收代替。

## Authority and Preservation

- 仅修改本计划列出的报告、证据和项目记录；不覆盖用户其他文件或既有报告。
- 用户已明确授权生成今日盘前报告。
- 不实施定时任务、推送、对外发布或任何交易操作。
