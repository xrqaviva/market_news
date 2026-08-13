# A股短线纯新闻热榜测试报告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份信息尽可能完整、纯新闻、按消息热度降序排列的 2026-07-29 A股短线测试报告。

**Architecture:** 从公开热榜、财经媒体、题材社区、产业媒体和官方页面补抓候选消息，将同一事件合并为事件卡片，再按独立于可靠性的消息热度模型排序。资金、个股和公告只作为可选字段，报告末尾仅列覆盖范围与采集失败。

**Tech Stack:** Markdown、公开网页/API、shell 结构校验。

## Global Constraints

- 不使用另外两个项目的新闻结果。
- 正文不得包含“一眼结论”、操作建议或按事后验证筛选新闻。
- 所有新闻使用统一榜单并按热点权重降序排列。
- 缺少资金验证、个股映射或公告确认不得影响入榜和排序。
- 精确互动量不可得时必须标明，不得虚构。
- 不提交、不推送、不部署。

---

### Task 1: 补抓并合并候选新闻

**Files:**
- Read: `reports/2026-07-29-shortline-news-radar-test.md`
- Create: `reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

**Interfaces:**
- Consumes: 公开来源的标题、时间、路径、热度字段与可靠性状态
- Produces: 去重后的统一新闻事件列表

- [ ] **Step 1: 验证目标报告尚不存在（RED）**

Run: `test -f reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

Expected: exit 1。

- [ ] **Step 2: 补抓通用热榜、财经媒体、题材社区、产业媒体和公告候选**

记录每类成功与失败来源，保存可点击原始路径及原始互动字段。

- [ ] **Step 3: 按事件去重**

同一事件只保留一条新闻卡片；首发、转述和社区路径全部保留在该卡片内。

### Task 2: 计算热度并生成统一榜单

**Files:**
- Create: `reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

**Interfaces:**
- Consumes: Task 1 事件列表
- Produces: 按权重降序的 Markdown 新闻榜

- [ ] **Step 1: 为每条新闻填写五项热度构成**

使用 `覆盖30 + 增速25 + 平台热度25 + 新鲜度15 + 持续频次5`，没有精确量时标记估算依据。

- [ ] **Step 2: 生成报告**

每条卡片填写内容、时间、传播路径、原始热度、可靠性、待确认点和可选验证字段。

- [ ] **Step 3: 验证报告存在（GREEN）**

Run: `test -s reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

Expected: exit 0。

### Task 3: 结构与完整性验证

**Files:**
- Verify: `reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

**Interfaces:**
- Consumes: Task 2 报告
- Produces: 可交付的结构验证证据

- [ ] **Step 1: 禁止章节校验**

Run: `! rg -n '一眼结论|操作建议|下一次盘中需要盯什么|午间新出现的小作文观察池' reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

Expected: exit 0，无匹配。

- [ ] **Step 2: 必需字段校验**

Run: `rg -n '热点权重|首次发现|传播路径|原始热度|可靠性|尚未确认|采集覆盖' reports/2026-07-29-pure-news-hot-ranking-test-v2.md`

Expected: 每类字段至少出现一次。

- [ ] **Step 3: 排序校验**

抽取所有“热点权重”数值，验证相邻值非递增。

- [ ] **Step 4: 链接与缺失量校验**

检查每条新闻至少有一个核验链接；无法取得互动量的条目明确写“不可得”或“暂未取得”。

- [ ] **Step 5: 完整范围校验**

确认正文覆盖媒体确认消息、社区小作文、产业消息、公告/政策消息，并在末尾列出成功与失败渠道。

## Test Matrix

- Unit：N/A，本轮无生产代码，仅生成 Markdown 报告。
- Integration：公开来源到报告路径人工核验；无自动采集系统。
- UI：N/A，不修改网页或应用界面。
- Security/privacy：只使用公开网页，不写入密钥、登录态或其他项目私有新闻结果。
- Artifact：结构、排序、链接、禁用章节与覆盖范围检查。
- Full suite：N/A，当前工作区无代码、测试框架及 Git 仓库；以完整报告验证命令替代。
