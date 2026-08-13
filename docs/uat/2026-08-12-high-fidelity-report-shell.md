# 新闻雷达高保真报告外壳 UAT

执行日期：2026-08-13（Asia/Shanghai）

Final fix 状态：`GREEN`。报告级说明、合并来源、题材热点分项和隐私路径修复后的真实浏览器门禁 exit 0；内容、确定性、安全、语法和完整 Python 套件亦已复验。

验收对象：`web/dist/reports/2026-08-11-0800.html`，并以全部 7 份 checked report 为归档与确定性范围

批准基准：`docs/superpowers/specs/2026-08-12-high-fidelity-report-shell-design.md` 与 `layout-final-v3.html`

## 1. 产物身份与构建范围

- 构建根目录是 linked、非 submodule 的隔离 worktree；Git dir 位于主仓库 `.git/worktrees/news-radar-web`，common dir 为主仓库 `.git`。
- `git ls-files 'reports/*.md'` 与 worktree 中标准命名的 Markdown 集合相等，均为 7 份。受控的第 8 份未跟踪报告输入会被门禁拒绝。
- 正式构建命令产出 `7 reports (169 items)`；manifest 和 `web/dist/reports/*.html` 均精确包含 7 个预期报告页面。
- checked `web/dist` 与 fresh build 通过 byte-identical unittest；第二次临时构建后 `diff -qr` 返回 0 且无输出；源/生成 `app.css`、`app.js` 分别通过 `cmp`。因此 fresh-build 浏览器门禁代表 checked artifact，而不是仅代表另一份临时输出。
- `assert_public_tree_safe(web/dist)` 通过：没有私有路径、凭据、危险 URL scheme、symlink、私有文件名或合同外文件。
- 最后一次生成改动之后运行 `python3 -m unittest discover -s tests -v`：104 run / 104 passed / 0 failed / 0 errors / 0 skipped。

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
| 题材热点构成 | 25/25 渲染实例，每实例恰好一次 |
| 报告级有标题说明 | 11/11，保持源顺序 |
| 顶部非 meta 口径 | 7/7 报告保留 |

Fix round 1 从原始 Markdown 新闻块开始做独立审计，而非从解析模型开始：

| 源级合同 | 结果 |
|---|---:|
| 7/29 `消息详情` → 核心摘要 | 35/35 非空并逐条进入 HTML |
| 7/29 `时间`、`监控区间`、`热度变化`、`变化判定`、`传播路径`、`当前原始热度`、`可靠性`、`尚未确认`、`可选A股附注` | 每类 35/35，标签和值各恰好一次，源顺序不变 |
| 旧版 `状态` | 55/55 恰好一次 |
| 旧格式 `热点权重分项` → `热点构成` | 85/85 恰好一次；空值 0 节点；特殊字符转义 |
| 8/11 题材 `#### 新闻` 热点分项 | 25/25 实例恰好一次；跨题材副本一致；空值与转义门禁通过 |
| 报告说明 | 11 个标题章节及其正文/HTTP(S) 链接完整；7 份顶部非 meta 披露完整；新闻后、pending 前 |
| 表格 + 内联来源 | 表格优先、按 URL 稳定去重；7/30 15:00 第 1 条 AP 独有链接可点击 |
| 报告窗口 | 6 个非空值各 1 节点；第 7 个空值 0 节点；特殊字符转义 |
| 模型总量 | 169 items；169 core；317 sources；109 unique-item breakdown；370 supplemental label/value pairs |
| 既有字段不回退 | signal 74、feedback 74、boundary 74、variables 50、heat change 89、release session 24 |

新闻块加粗标签审计的已识别集合包含：`热点权重`/分项、`状态`、`消息详情`、`核心信息`、`时间`、`监控区间`、`热度变化`、`变化判定`、`传播路径`、`当前原始热度`、`核验路径`、`可靠性`、`尚未确认`、`可选A股附注`、新格式信号/反馈/边界/变量/发布时段/关联题材。`核验路径` 继续以来源链接呈现；`即时市场定价为…` 保持在完整市场反馈中，显式定价字段仍单独解析。排除的加粗内容仅有数字强调（例如回购金额），它们不是字段标签；新闻块外评分方法、渠道说明和完整性边界不会进入新闻模型。未识别的新闻字段标签集合为空。

主题顺序、聚合分数、other-important 区块、24 个 unique event 的 25 个主题/其他实例、来源、5 条 pending、PBOC 与 NVIDIA 长链接均由 checked-artifact 回归测试验证。正文顺序保持“核心方向 01—05 → 其他重要新闻 → 报告说明 → 待核验线索”，没有恢复旧索引或类别筛选器。

## 3. 桌面视觉 UAT（1440 × 900；fix round 1 fresh）

以下是真实 headless Chrome 对 final fix 最终产物的计算样式与边界框。补齐说明和题材分项后，报告 card 高度自然增长至 `8648.21875px`，固定横向几何与视觉 token 不变。

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

所有已展开主题新闻的 title、summary、association、detail、source 共 138 个对齐测点都落在 `402px` 内容左线；另一个 source-only 报告的 45 个测点也无偏差。首条详情展开高度 `173.34375px`，关闭/展开/再关闭状态依次为 `0 → 173.34375 → 0`，`hidden` 与 `aria-expanded` 同步。

## 4. 移动视觉 UAT（390 × 844；fix round 1 fresh）

- shell 外边距 `12px`；topbar margin 与正文 padding 均为 `18px`；card 仍为 `16px` 圆角。
- desktop sidebar 的计算 display 为 `none`，移动报告选择器为 `flex`。
- 主题标题为 `21px`。主题导航 `523px > 326px`，确有横向滚动空间；第五主题锚点点击后 target top 为 `-0.0625px`（亚像素舍入，视口顶部对齐）。
- document `scrollWidth/clientWidth = 390/390`，无页面级横向溢出；完整详情保持可读，没有因移动布局删除字段。
- 报告说明 `scrollWidth/clientWidth = 326/326`，左右边界 `32px/358px`，无局部横向溢出。
- 移动端默认与点击后都恰有一个 `aria-current="location"` 导航项。

## 5. 交互、打印、对比度与运行时（fix round 1 fresh）

- 主题锚点：桌面第三主题、direct-hash 第五主题、移动第五主题均到达对应 ID；普通点击更新唯一 current。取消、非主键、Ctrl/Meta/Shift/Alt 点击不会错误改变 current/hash。
- 新闻 disclosure：关闭、展开、再关闭的 `hidden`、`aria-expanded`、高度生命周期一致。
- 归档：点击 2026-08-11 后 hash、expanded 和 slots 可见性同步；选择 2026-08-10 后前一日期收起、目标日期展开。
- pending disclosure：屏幕态可展开，打印前后生命周期被真实触发；`beforeprint`/print 中 25/25 新闻详情、5/5 pending 及 1/1 报告说明章节均可见，`afterprint` 恢复原先 closed 状态。
- 报告说明视觉/安全：标题 `14px`、章节标题 `10px`、正文 `8px`；真实含链接报告取得 1 个 HTTP(S) 链接、危险协议 0；顺序为 other-important 后、pending 前。
- 动态对比度：展开 archive、全部 news disclosure 与 pending 后扫描 660 个可见、直接文本、字号小于 18px 的节点，其中报告说明 15 个；最低 `4.6245761308799:1`，低于 4.5 的节点为 0。受控 alpha mutant 为 `1.4940333112803392:1`，证明扫描器能发现真实问题并正确合成半透明背景。
- 可访问性偏差：参考页的 eyebrow、cutoff、rank 等灰色 token 低于小字号 `4.5:1` 门槛；生产页统一使用较深的 `--muted: #657287`。这是为对比度门禁保留的有意覆盖，其他几何和层级 token 仍按参考实现。
- browser console warnings/errors：0。

## 6. 环境边界与处置

- 沙箱内直接启动 Chrome 首次在 DevTools 端口等待 10 秒后超时；同一规定命令用已限定的 headless-Chrome 权限重跑后通过。该次超时记录为环境失败，不是产品测试结果。
- in-app Browser 的 URL 安全策略拒绝打开本地 `file://` 参考页；未绕过。正式 UAT 证据来自已获权限的本地 headless Chrome、真实 DOM/计算样式、交互、打印和 console 检查。
- headless Chrome profile、临时 fresh dist 与 determinism 临时目录均在门禁结束后删除；没有截图、profile、server state 或本地临时产物进入仓库。
- Fix round 1 重建后，精确命令 `node tests/report_layout_browser.mjs` 通过已有的受限 headless-Chrome 权限请求执行，但自动审批在进程启动前以账户使用额度拒绝；主控重复同一精确请求也得到相同结果。遵守安全策略，没有改用其他命令、浏览器或间接通道绕过。该结果是未解决环境阻断，不是产品 PASS/FAIL。
- 用户随后明确批准该浏览器门禁；最终 parser 边界修复和正式重建后重新运行同一精确命令，exit 0。7 tracked/disk/manifest/HTML 集合一致；desktop `980/27/926/76/28`，card 四边 `2px solid`、`16px`；common-left 138 与 source-only 45 均 0 违规；print 25/25 news 与 5/5 pending；contrast 595 nodes、minimum `4.6245761308799`、controlled mutant `1.4940333112803392`；mobile `390/390` 无溢出、`12/18`、nav `523>326`；archive/theme current/disclosure 全过；console problems 0。
- Final fix 浏览器重跑先在沙箱内 Chrome 启动超时，随后按既有精确权限运行成功。除上述固定几何外，报告说明顺序/字号/协议门禁通过，print 1/1、contrast note nodes 15、mobile notes `326/326`、console problems 0。

## 7. 独立审查处置

- 初审发现 Task 1 的新 header 未渲染 `ReportMeta.window`：模型审计中 6 份非空报告窗口均不在 HTML。该阻断项先由一个覆盖全部 6 个精确值的回归测试稳定复现为 6 个 subtest 失败。
- 经任务所有者扩大 `web/build.py` 范围后，仅在 header 的次级元数据区增加经过 HTML 转义的 `报告窗口 · …` 行；没有修改模板、CSS 或 JavaScript 源文件。聚焦测试转绿，重建 7 份产物后，真实浏览器仍保持 report title 与 cutoff 底边完全对齐（差值 `0px`）。
- 初审还指出直接视觉比较、最终 full-suite 精确计数、本机绝对路径和可访问性颜色偏差的证据不足；本记录已分别补充或清理。最终只读复审确认 Critical / Important / Minor 均为 0，结论为 Ready。
- Fix round 1 的后续审查发现旧格式正文和已解析热点分项仍有丢失；上述源级合同已按独立 RED → GREEN 修复。当前修复 diff 可进行只读代码复审，但在真实浏览器门禁恢复前不得提交完成。
- Fix round 1 只读复审还发现末条新闻 block 会延伸到后续 `##` 说明区，导致说明链接可能污染来源。Synthetic 测试先稳定复现 2 个来源而非 1 个；`_top_sections` 统一截到下一任意二级标题后聚焦 3/3 通过，当前 316 来源计数不变。

结论：Final fix 的内容、模型、生成确定性、语法、安全、Python 完整套件及 desktop/mobile/disclosure/archive/print/contrast/console 浏览器门禁全部通过；本任务不发布该产物。
