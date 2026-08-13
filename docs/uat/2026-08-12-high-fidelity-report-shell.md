# 新闻雷达高保真报告外壳 UAT

执行日期：2026-08-13（Asia/Shanghai）

验收对象：`web/dist/reports/2026-08-11-0800.html`，并以全部 7 份 checked report 为归档与确定性范围

批准基准：`docs/superpowers/specs/2026-08-12-high-fidelity-report-shell-design.md` 与 `layout-final-v3.html`

## 1. 产物身份与构建范围

- 构建根目录是 linked、非 submodule 的隔离 worktree；Git dir 位于主仓库 `.git/worktrees/news-radar-web`，common dir 为主仓库 `.git`。
- `git ls-files 'reports/*.md'` 与 worktree 中标准命名的 Markdown 集合相等，均为 7 份。受控的第 8 份未跟踪报告输入会被门禁拒绝。
- 正式构建命令产出 `7 reports (169 items)`；manifest 和 `web/dist/reports/*.html` 均精确包含 7 个预期报告页面。
- checked `web/dist` 与 fresh build 通过 byte-identical unittest；第二次临时构建后 `diff -qr` 返回 0 且无输出；源/生成 `app.css`、`app.js` 分别通过 `cmp`。因此 fresh-build 浏览器门禁代表 checked artifact，而不是仅代表另一份临时输出。
- `assert_public_tree_safe(web/dist)` 通过：没有私有路径、凭据、危险 URL scheme、symlink、私有文件名或合同外文件。
- 最后一次生成改动之后运行 `python3 -m unittest discover -s tests -v`：87 run / 87 passed / 0 failed / 0 errors / 0 skipped。独立的构建/安全子集为 39 run / 39 passed；跨 7 份解析模型检查 2,483 个可渲染值，缺失 0。

## 2. 内容完整性

Aug. 11 Markdown 解析模型与 checked HTML 的合同结果如下：

| 内容 | 结果 |
|---|---:|
| 核心方向 | 5 |
| 渲染新闻实例 | 25 |
| unique event | 24 |
| 其他重要新闻 | 12 |
| 待核验线索 | 5 |
| 主榜来源链接 | 44 |
| 报告窗口 | 6/6 非空完整渲染（另 1 份为空，不生成空节点） |
| 发布时段 | 25/25 |
| 关键信号/预期差 | 25/25 |
| 市场反馈 | 25/25 |
| 判断边界 | 25/25 |
| 热度变化 | 25/25 |

主题顺序、聚合分数、other-important 区块、24 个 unique event 的 25 个主题/其他实例、来源、5 条 pending、PBOC 与 NVIDIA 长链接均由 checked-artifact 回归测试验证。正文顺序保持“核心方向 01—05 → 其他重要新闻 → 待核验线索”，没有恢复旧索引或类别筛选器。

## 3. 桌面视觉 UAT（1440 × 900）

真实 headless Chrome 的计算样式与边界框：

| 项目 | 实测 | 基准 |
|---|---:|---:|
| body 背景 | `rgb(237, 241, 246)` | `#edf1f6` |
| shell | `980px`，左右 margin `230px`，padding `27px` | `980px / 27px` |
| card | `926px` | viewport − margin/padding |
| card 外观 | `2px solid rgb(202,211,225)`；`16px`；`rgba(30,40,60,.1) 0 16px 40px` | `#cad3e1 / 16px / 指定阴影` |
| sidebar | `76px`；padding `17px 9px`；`rgb(28,41,64)` | `76px / 17px 9px / #1c2940` |
| workspace 正文 | 左右 padding `28px` | `28px` |
| report title | `21px / 800` | `21px / 800` |
| theme title | `25px / 700` | `25px` |
| news title | `12px / 700` | `12px` |
| 字体栈 | `-apple-system, system-ui, Segoe UI, PingFang SC, sans-serif` | 系统中文字体栈，无 Inter |
| theme nav | gap `16px`；padding `12px 0`；横向 overflow auto | 单行导航 |
| 方向分隔 | `6px solid rgb(237,240,244)` | `6px #edf0f4` |
| 新闻栅格 | `30px 751px`；gap `9px`；padding `12px 0` | 两列 `30px + content` |

可见层级符合参考：灰色画布包围单一卡片，深蓝窄侧栏从卡片顶部贯穿报告；标题与截止时间底边对齐；主题导航、主题标题和浅色分隔带节奏清晰；新闻排名与正文形成稳定两列，详情和来源没有第三列或横向跳动。设计标注 `.note` / `.legend` 未进入正式页面。

同一 `1440 × 900` 视口下分别截取批准参考和生成报告，并检查并排图；再将参考图向上裁去其设计说明区后，以 50% 透明度叠加生成图。卡片左右边界、圆角、阴影、侧栏宽度、workspace 左边线、header 分隔线和主题导航分隔线重合；标题、主题和 story 的视觉层级一致。参考页使用示意摘要而生产页保留完整 Markdown，所以生产页在 header 高度、单个主题内容密度和纵向位置上按内容自然增长，不要求逐像素重合。截图与叠加图仅保存在临时目录，检查后不进入仓库。

所有已展开主题新闻的 title、summary、association、detail、source 共 138 个对齐测点都落在 `402px` 内容左线；另一个 source-only 报告的 45 个测点也无偏差。首条详情展开高度 `152.953125px`，关闭/展开/再关闭状态依次为 `0 → 152.953125 → 0`，`hidden` 与 `aria-expanded` 同步。

## 4. 移动视觉 UAT（390 × 844）

- shell 外边距 `12px`；topbar margin 与正文 padding 均为 `18px`；card 仍为 `16px` 圆角。
- desktop sidebar 的计算 display 为 `none`，移动报告选择器为 `flex`。
- 主题标题为 `21px`。主题导航 `523px > 326px`，确有横向滚动空间；第五主题锚点点击后 target top 为 `-0.0625px`（亚像素舍入，视口顶部对齐）。
- document `scrollWidth/clientWidth = 390/390`，无页面级横向溢出；完整详情保持可读，没有因移动布局删除字段。
- 移动端默认与点击后都恰有一个 `aria-current="location"` 导航项。

## 5. 交互、打印、对比度与运行时

- 主题锚点：桌面第三主题、direct-hash 第五主题、移动第五主题均到达对应 ID；普通点击更新唯一 current。取消、非主键、Ctrl/Meta/Shift/Alt 点击不会错误改变 current/hash。
- 新闻 disclosure：关闭、展开、再关闭的 `hidden`、`aria-expanded`、高度生命周期一致。
- 归档：点击 2026-08-11 后 hash、expanded 和 slots 可见性同步；选择 2026-08-10 后前一日期收起、目标日期展开。
- pending disclosure：屏幕态可展开，打印前后生命周期被真实触发；`beforeprint`/print 中 25/25 新闻详情与 5/5 pending 均可见，`afterprint` 恢复原先 closed 状态。
- 动态对比度：展开 archive、全部 news disclosure 与 pending 后扫描 595 个可见、直接文本、字号小于 18px 的节点，最低 `4.6245761308799:1`，低于 4.5 的节点为 0。受控 alpha mutant 为 `1.4940333112803392:1`，证明扫描器能发现真实问题并正确合成半透明背景。
- 可访问性偏差：参考页的 eyebrow、cutoff、rank 等灰色 token 低于小字号 `4.5:1` 门槛；生产页统一使用较深的 `--muted: #657287`。这是为对比度门禁保留的有意覆盖，其他几何和层级 token 仍按参考实现。
- browser console warnings/errors：0。

## 6. 环境边界与处置

- 沙箱内直接启动 Chrome 首次在 DevTools 端口等待 10 秒后超时；同一规定命令用已限定的 headless-Chrome 权限重跑后通过。该次超时记录为环境失败，不是产品测试结果。
- in-app Browser 的 URL 安全策略拒绝打开本地 `file://` 参考页；未绕过。正式 UAT 证据来自已获权限的本地 headless Chrome、真实 DOM/计算样式、交互、打印和 console 检查。
- headless Chrome profile、临时 fresh dist 与 determinism 临时目录均在门禁结束后删除；没有截图、profile、server state 或本地临时产物进入仓库。

## 7. 独立审查处置

- 初审发现 Task 1 的新 header 未渲染 `ReportMeta.window`：模型审计中 6 份非空报告窗口均不在 HTML。该阻断项先由一个覆盖全部 6 个精确值的回归测试稳定复现为 6 个 subtest 失败。
- 经任务所有者扩大 `web/build.py` 范围后，仅在 header 的次级元数据区增加经过 HTML 转义的 `报告窗口 · …` 行；没有修改模板、CSS 或 JavaScript 源文件。聚焦测试转绿，重建 7 份产物后，真实浏览器仍保持 report title 与 cutoff 底边完全对齐（差值 `0px`）。
- 初审还指出直接视觉比较、最终 full-suite 精确计数、本机绝对路径和可访问性颜色偏差的证据不足；本记录已分别补充或清理。最终只读复审确认 Critical / Important / Minor 均为 0，结论为 Ready。

结论：高保真外壳、完整内容、桌面/移动布局、归档与 disclosure、打印、对比度、运行时及公共产物安全门禁通过；本任务不发布该产物。
