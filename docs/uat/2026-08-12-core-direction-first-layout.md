# 核心方向优先布局 UAT（2026-08-12）

## 批准范围与输入边界

- 批准设计：`docs/superpowers/specs/2026-08-12-core-direction-first-layout-design.md`，提交 `00d6a4d`。
- 批准计划：`docs/superpowers/plans/2026-08-12-core-direction-first-layout.md`，提交 `3c2a8a4`；行为测试计划提交 `32c1a53`。
- 实现基线：`f8c1003`、`a051d21`、`a9bbe31`；构建输入纠偏提交 `664f8ff`。
- `664f8ff` 明确限定：生成物只读取隔离工作树中 7 份受 Git 跟踪的报告 Markdown；主检出目录中未跟踪的历史候选稿不是本次构建输入。
- 首次按旧简报使用主检出目录的 adapter 后，完整套件出现 1 个确定性失败；诊断确认 3 份历史报告 Markdown 在主检出目录与工作树内容不同。该批生成物已整体丢弃，未进入交付范围；随后按 `664f8ff` 从隔离工作树重新生成。

## RED → GREEN 与构建结果

- 在重建前先更新 `test_checked_in_aug11_artifact_keeps_themed_news_contract`：保留 5 个题材名/总分、24 个事件 ID、实例 ID 唯一性、25 个发布时段、截点、关键来源、5 个待核项、manifest 最新 URL 和归档链接断言；把旧索引契约替换为无长索引、5 个连续核心方向、其他重要新闻/待核附录顺序、原生待核折叠契约。
- RED：`python3 -m unittest tests.test_web_build.WebBuildTest.test_checked_in_aug11_artifact_keeps_themed_news_contract -v` 运行 1 项、失败 1 项；旧 HTML 未匹配新的 `N条 · SCORE` 方向标题，属于预期的 stale artifact 失败。
- 最终构建命令：`python3 -m web.build --project-root /Users/aviva/Projects/market_news/.worktrees/news-radar-web --output /Users/aviva/Projects/market_news/.worktrees/news-radar-web/web/dist`。
- 构建结果：7 份报告、169 条新闻，最新 URL 为 `reports/2026-08-11-0800.html`。
- GREEN：同一聚焦测试运行 1 项、通过 1 项；最终完整套件运行 85 项、85 passed、0 failed、0 errors、0 skipped。

## 生成物、确定性与安全

- `cmp web/assets/app.js web/dist/assets/app.js` 与 `cmp web/assets/app.css web/dist/assets/app.css` 均退出 0。
- `node --check web/dist/assets/app.js` 与 `git diff --check` 均退出 0。
- 使用同一工作树根命令第二次生成到独立临时 `dist`，`diff -qr` 无输出：11 个公开文件逐字节一致。
- `web/dist/index.html` 与 `web/dist/reports.json` 在本次重建后无差异；manifest 仍指向最新 Aug. 11 报告。
- `assert_public_tree_safe(Path("web/dist"))` 通过。公开树为 11 个文件、8 个 HTML、0 个符号链接；未发现 `/Users/`、loopback URL、`localhost` 或 `file://` 残留。

## 桌面浏览器 UAT（1440 × 900）

- 只在 `127.0.0.1` 上提供静态预览；使用 in-app browser 实际打开生成后的 Aug. 11 页面。首次端口在重建后保留旧 CSS 缓存，因此所有最终布局数据均取自新端口的 cache-cold origin；未因此修改任何资源文件。
- 窄归档侧栏显示，实测宽 120px；6 个可见日期入口。点击当前日期后 fragment 正确，日期 `aria-expanded=true`，对应 slot 容器从 hidden 变为可见。
- 核心方向导航为单行，5 个链接顶边相同；5 个 href 均指向存在的题材容器。实际点击方向 03 后 fragment 正确且目标顶边为 0；无长索引、无“接下来的方向”、无 intensity/stat card。
- 核心方向依次为 `01` 至 `05`：`5条 · 420`、`2条 · 184`、`2条 · 166`、`2条 · 165`、`2条 · 161`；方向 05 后是“其他重要新闻”，待核附录是主区最后一项。
- 方向标题字号 32px；方向总计为 10px、灰色，新闻热度为 10px、灰色，视觉上均为次级信息。
- 25 个详情按钮对应 25 个唯一 `aria-controls` 目标且初始详情全部隐藏。实际打开第一个详情后仅该目标显示、第二个仍隐藏，展开区包含 3 个来源链接。
- 历史 Aug. 10 页存在 15 个 `data-detail-kind="sources-inline"` 条目；抽检 3 条均有直接可见来源、按钮数 0，不产生空详情按钮。
- 待核 `<details>` 初始关闭、含 5 项；鼠标实际点击可开，再次点击可关。
- 整个 cache-cold tab 会话控制台为 0 warnings、0 errors。

## 移动浏览器 UAT（390 × 844）

- 桌面归档 `display:none`；报告选择器 `display:block`、7 个选项。实际选择 Aug. 10 盘前后到达对应报告和 fragment，标题同步更新。
- 核心方向导航 `display:flex`、`white-space:nowrap`、`overflow-x:auto`；实测 `clientWidth=374`、`scrollWidth=652`。点击屏外方向 05 后导航 `scrollLeft=275.5`，fragment 正确且目标顶边为 0，证明导航可横向滚动。
- 页面 `document.documentElement.clientWidth=390`、`scrollWidth=390`，没有整页横向溢出。
- 方向标题未裁切，`scrollWidth == clientWidth`；标题与 `5条 · 420` 元数据矩形不重叠。
- 新闻行保持两列可读布局。实际打开方向 05 的第 2 条详情：详情 `clientWidth=319`、`scrollWidth=319`，来源链接均在 390px 视口内并自然换行；整页宽度仍为 390px。
- 待核附录仍默认关闭且含 5 项。

## 键盘控制说明与边界

- 页面使用原生可聚焦 `<summary>`（`tabIndex=0`）且没有脚本覆盖其 toggle；自动化语义契约也验证 `<details class="pending-details">` 默认无 `open`。
- 当前 in-app browser 的键盘注入链路不能激活普通原生 `<button>`：对已聚焦详情按钮执行 locator `press("Enter")`、DOM keyboard 及 CUA keyboard 后，`aria-expanded` 均保持 `false`。同一限制也出现在已聚焦 `<summary>` 的 Enter/Space；因此本执行者不把这些无状态变化冒充页面键盘失败或通过。

## 发布边界

- 本次只重建并验收受控静态树、更新 artifact 回归契约并保存 UAT 证据；没有读取浏览器 Cookie、Local Storage、密码、Token 或历史，也没有访问外部来源站点。
- 明确边界：**未合并、未推送、未部署、自动任务保持关闭**。
