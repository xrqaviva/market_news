# 报告归档树 UAT 记录（2026-08-09）

## 范围与环境

- 验证对象：由主工作区 `reports/` 完整目录重建的 `web/dist` 静态站点。
- 源分支：`codex/news-radar-web`，Task 3 基线 `831732d36962fdacb8a13207576b07cf97141f69`。
- 本地预览：仅监听 `127.0.0.1`；浏览器桌面视口 1280 × 900，移动视口 390 × 844。
- Task 2 延期项：fragment 折叠与移动下拉缺少自动 DOM harness；本记录用真实生成页浏览器交互覆盖。

## 重建与静态产物

- 按 Task 3 简报中的 source-assets adapter 原子重建成功。
- `BuildResult`：6 份报告、145 条新闻，最新 URL 为 `reports/2026-08-10-0800.html`。
- `web/assets/app.js` 与 `web/dist/assets/app.js` 逐字节一致；CSS 同样一致。
- `node --check web/dist/assets/app.js` 与 `git diff --check` 均退出 0。

## 桌面浏览器验收

1. 打开最新报告时共有 5 个日期组，全部 `aria-expanded=false` 且 5 个 slot list 均为 `hidden`；可见子报告链接为 0。
2. 侧栏实测宽 120px；5 个日期链接的 `scrollWidth` 与 `clientWidth` 均为 104px，无日期裁切。
3. 点击 `2026-07-30` 后到达 `2026-07-30-1500.html#archive-2026-07-30`；只有该组展开，只显示“盘前/盘后”，其中“盘后”为 `aria-current=page`。
4. 点击“盘前”后到达 `2026-07-30-0800.html#archive-2026-07-30`；仍只有同一日期组展开，“盘前”成为当前报告。
5. 类别筛选实测使当前报告可见条目从 20 条降至 2 条；恢复“全部”后，Top 1 的“展开详情”可切换为 `aria-expanded=true` / “收起详情”，详细来源与分析正文显示。

## 移动浏览器验收

1. 390 × 844 下桌面侧栏隐藏，报告下拉可见（实测宽 164.5px）。
2. 下拉 6 个选项精确等于 6 份报告链接，只含真实报告，不含 5 个日期控制项。
3. 在下拉中选择 `2026-07-30 · 盘后` 后到达精确 fragment URL，选中项正确，且仅 `2026-07-30` 组保持展开。

## 运行时与回归

- 浏览器控制台：0 条 warning，0 条 error。
- 最后一个生成变更后的新鲜完整套件：54 passed、0 failed、0 errors、0 skipped；最终 `cmp` × 2、JS syntax、`git diff --check`、6 manifest reports = 6 report pages 均通过。
- `scan_public_tree` 为 0 findings，`assert_public_tree_safe` 通过；公开树共 10 个文件、7 个 HTML（其中 6 个报告页）、0 个符号链接，未发现本地路径/URL、凭据标记或不安全 URL scheme。
- 最终安全扫描与完整回归已刷新；公开站点验证在下节记录。

## 独立只读复核

- Reviewer：内部只读 reviewer `/root/archive_task2_review`（未修改文件）。
- 批准需求映射、六页生成兼容性、fragment 状态、移动下拉来源、隐私/安全和测试覆盖均通过静态复核；无代码或生成物 blocking/major finding。
- Task 2 deferred minor（缺少自动 DOM harness）由上述真实浏览器桌面/移动操作覆盖，最终处置为非阻断；后续仍可增补自动 DOM 回归测试。
- reviewer 首轮结论为“尚不可发布”，唯一原因是当时本节与发布门禁尚未写完、Task 3 产物尚未提交；不是实现缺陷。完成下节全部门禁后可发布。

## 发布验证

待记录：dry-run、源分支提交/推送、公开站点提交/推送、Pages build、HTTP 首页/最新报告和归档 contract。
