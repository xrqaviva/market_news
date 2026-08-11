# 2026-08-11 题材聚合真实浏览器 UAT

## 范围与边界

- 验证对象：已生成的 `web/dist`，最新入口为 `reports/2026-08-11-0800.html`。
- 本地预览：`python3 -m http.server 8765 --bind 127.0.0.1 --directory web/dist`；浏览器从 `http://127.0.0.1:8765/` 进入并由静态首页跳转到最新报告。未使用 `file://`，未绕过浏览器安全策略。
- 浏览器：Codex in-app browser，通过项目指定的 browser-client/Node js 控制面执行真实点击、选择与 DOM/控制台观察。
- 视口：默认桌面浏览器宽度 `1470`；窄屏覆盖 `390 × 844`。
- 未读取 Cookie、Local Storage、浏览器历史、密码、Token 或其他浏览器敏感状态；未逐个请求外部来源链接。
- 本任务只做本地预览、测试、只读检查与文档提交；未 push、deploy、publish、发送邮件或启用自动任务。

## 浏览器操作与结果

### 最新报告与归档层级

1. 打开 `http://127.0.0.1:8765/`，实际落点为 `http://127.0.0.1:8765/reports/2026-08-11-0800.html`，标题为 `2026-08-11 A股盘前新闻热榜（08:00 题材优先版）`。
2. 默认选中项为 `2026-08-11 · 盘前`。桌面侧栏有 6 个日期组，初始均为 `aria-expanded=false` 且 slot 容器为 `hidden`；最新日期内的当前报告为盘前。
3. 点击日期 `2026-07-30`，实际到达 `http://127.0.0.1:8765/reports/2026-07-30-1500.html#archive-2026-07-30`。只有 `2026-07-30` 日期组展开，显示盘前与盘后两个时段，盘后为 `aria-current=page`，移动报告选择器同步选中 `2026-07-30 · 盘后`。
4. 点击该日期组内的盘前，实际到达 `http://127.0.0.1:8765/reports/2026-07-30-0800.html#archive-2026-07-30`。同一日期组保持展开，盘前成为当前报告，移动选择器同步选中 `2026-07-30 · 盘前`。
5. 返回 `2026-08-11` 后，最新题材页重新加载 5 个题材组且盘前为当前报告。

日期点击使用浏览器导航等待器时有一次等待器超时，但页面已完成正确导航；随后以实际 URL、标题、展开日期、可见时段和当前项逐项复核。该现象是测试控制等待器问题，不是页面导航失败。

### 索引、题材与完整详情

- 单条新闻索引共 24 个链接，href 全部唯一，24 个目标元素全部存在。排名从01连续至24且分数非递增；目标事件 ID 与索引集合一致。
- 实际点击第1条下方的“中东局势 / 油气”题材徽章，URL fragment 变为 `#theme-ascii-theme-middle-east-oil`；对应题材容器存在且目标顶边约为视口 `0.05px`。DOM中28个题材徽章的href均能解析到存在的题材容器。
- 25个正文卡片实例均渲染“发布时段”；数据截止显示精确实际截点 `2026-08-11 08:30:39（北京时间，Asia/Shanghai）`。题材页不再显示旧类别筛选按钮，历史页仍保留。
- 五个题材按以下顺序显示，均有题材分、关联条数、核心催化、直接映射或板块代表及题材风险边界：

| 顺序 | 题材 | 总分 | 条数 | 直接映射 | 板块代表 |
|---:|---|---:|---:|---:|---:|
| 1 | AI算力 / 半导体 / 存储芯片 | 420 | 5 | 2 | 9 |
| 2 | 中东局势 / 油气 | 184 | 2 | 0 | 3 |
| 3 | 低空经济 / 航空AI | 166 | 2 | 0 | 3 |
| 4 | A股回购 / 资本运作 | 165 | 2 | 5 | 0 |
| 5 | 人形机器人 / 具身智能 | 161 | 2 | 0 | 6 |

- 页面同时显示跨题材重复计分披露。主内容为五个题材组，原“并购重组”不再显示；其三条非低空新闻移入其他重要新闻，Archer收购仍保留在低空经济。待核验附录在其后，含豆包争议在内共5条且不带分数。

### 来源 URL 精确集合

- 使用生产解析器 `web.report_parser.parse_report` 解析 `reports/2026-08-11-0800-premarket-news-ranking.md`，从 24 个 canonical 主榜事件和 5 个 pending 项得到 32 个唯一来源 URL。
- 在真实浏览器 DOM 中读取 `[data-component='sources'] a` 与 `[data-component='pending-sources'] a` 的 href：53 次出现、32 个唯一 URL。
- 两个排序去重集合精确相等：missing `[]`、extra `[]`；32 个 URL 全部为 `http://` 或 `https://`。跨题材副本带来的重复出现未被误判为额外来源。
- 本检查只证明页面 href 与 Markdown 解析结果逐字相同，不代表对 32 个外部站点逐个发起网络请求或重新验证第三方可用性。

### 重复实例与 source-only 行

- 第 5 条在 `AI算力 / 半导体 / 存储芯片` 与 `A股回购 / 资本运作` 中各有一个唯一实例，是本轮唯一跨题材事件。
- 对第 5 条执行：打开第一个实例、核对第二个仍收起，再打开第二个、关闭第一个。每一步中另一个实例的 `aria-expanded` 和详情 `hidden` 状态保持独立；展开详情内可见“发布时段”。
- 历史页 `2026-07-30-1500.html#archive-2026-07-30` 有 8 个 `data-detail-kind="sources-inline"` 卡片；这8个卡片自身的 `.news-toggle` 数为0且8处来源均直接可见。页面上另有10个分析型卡片按钮，它们不属于此断言的统计口径。

### 历史页面交互

- 在 `2026-07-30-1500.html#archive-2026-07-30` 点击唯一的“财报”筛选按钮：18条中仅7条可见，可见类别集合只有 `财报`，该按钮为 `aria-pressed=true`。
- 历史无题材页面保持平铺单条列表，归档、筛选、详情开合与 source-only 契约均可交互。

### 桌面与窄屏布局

- 默认桌面浏览器宽度1470时，最新页的 `documentElement.clientWidth` 与 `scrollWidth` 均为1470，无水平溢出。
- 窄屏 `390 × 844`：桌面侧栏 `display:none`，移动报告控制 `display:flex`，选择器实测宽 `164.5px`；主区 left/right/width 为 `0/390/390px`，页面 `clientWidth=scrollWidth=390`，没有可见元素越过视口边界。
- 窄屏下拉实际选择 `2026-08-03 · 盘前` 后到达 `http://127.0.0.1:8765/reports/2026-08-03-0800.html#archive-2026-08-03`，选中项和展开日期均正确，随后通过同一下拉返回最新报告。

### 运行时

- 本次单个浏览器 tab 跨最新页和历史页完成全部导航与交互。
- 跨整个 tab 会话读取 console：0 warning、0 error。
- 最新页 DOM 重复 ID：0；24个canonical事件生成25个增强新闻实例，对应25个独立详情容器，仅 `evt-20260811-005` 重复。

## Fresh final verification

### Root

```text
cd /Users/aviva/Projects/market_news
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

结果：45 tests，0 failures，0 errors，0 skipped，退出 0。

```text
git diff --check
```

结果：退出 0，无输出。

### Web worktree

```text
cd /Users/aviva/Projects/market_news/.worktrees/news-radar-web
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

结果：85 tests，0 failures，0 errors，0 skipped，退出 0。

```text
git diff --check
```

结果：退出 0，无输出。

### 产物、覆盖与安全

- `assert_public_tree_safe(Path("web/dist"))` 通过；扫描为 0 findings、11 个文件、8 个 HTML、0 符号链接。
- `cmp reports/2026-08-11-0800-premarket-news-ranking.md .worktrees/news-radar-web/reports/2026-08-11-0800-premarket-news-ranking.md` 退出 0，root 与 worktree 报告逐字节一致。
- 解析器独立统计：索引24次/24个唯一事件且每个一次；正文25次/24个唯一事件且每个至少一次；只有 `evt-20260811-005` 因跨题材出现两次，索引与正文事件集合相等。
- 五题材顺序、总分和条数精确为 `420/5, 184/2, 166/2, 165/2, 161/2`。
- 待核验项目为5个；Markdown 待核段和 HTML 待核 section 均不匹配 `热点权重`、`n/100` 或 `n分`。豆包项明确披露09:39:51知乎用户问题晚于08:30:39实际截点，不作为截点前证据。
- 两次临时构建与checked-in `web/dist` 的11个文件逐字节一致，组合SHA-256为`50e2d15f7c07e94465d7cc3711df5bbad4ff1063222372492a9b7f3bc2adacbc`。
- 自动化状态只读能力限制：本会话没有可调用的 `automation_update`/automation 查询工具；`crontab -l` 返回 `no crontab for aviva`。因此不能把 Codex app 中 `a-08-00`、`a-12-00`、`a-15-00` 的实时状态宣称为独立复核通过。现有权威文档仍记录三项暂停，本任务没有调用任何启停接口。
- 本任务未执行 push、deploy、email、publication、GitHub Pages 或外部站点发布；输出保持本地。

## 证据入口与后续边界

- Markdown：`reports/2026-08-11-0800-premarket-news-ranking.md`
- 生成 HTML：`web/dist/reports/2026-08-11-0800.html`
- 设计：`docs/superpowers/specs/2026-08-11-theme-aggregation-design.md`
- 实施计划：`docs/superpowers/plans/2026-08-11-theme-aggregation.md`
- 方法/UAT 台账（root）：`docs/2026-08-11-theme-aggregation-method-uat.md`
- 本 UAT：`docs/uat/2026-08-11-theme-aggregation.md`

退化来源与映射边界沿用报告披露：AmazingData 认证不可用且未读取认证值；分钟或原始确认未取得的来源保持降级描述；未核代码或映射被省略，板块代表不继承新闻或题材分。独立整分支审查由 controller 另行执行，不在本执行记录中冒充已完成。任何 preview、提交整合、push 或 GitHub Pages 部署均需下一次独立授权。
