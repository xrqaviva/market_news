# A股短线纯新闻热榜 V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份不少于30条、按当前热度与监控区间变化共同排序、逐条提供具体核验路径的A股短线纯新闻热榜V4。

**Architecture:** 先建立候选与监控快照证据表，把V3同口径早期值作为基线，并从登录Chrome和公开网页取得终点值与新增候选。随后按事件去重，以“覆盖25＋变化30＋绝对热度20＋新鲜度15＋频次10”计分，最后从证据表生成Markdown报告并运行结构、分值、时间、变化状态、链接与禁用措辞验证。

**Tech Stack:** Markdown、Chrome登录会话、公开网页、Python 3只读验证脚本、`rg`。

## Global Constraints

- 主榜以30条为起点，不设硬上限；达到设计门槛的消息不得因条数截断。
- 热度变化占30分，为主榜最高单项权重。
- 只有双时点同口径数据才能标记升温、降温或激增；低基数激增必须通过绝对增量保护。
- 上一窗口已成功覆盖但未发现的消息按“未发现 → 当前值”标记新出现，相对增幅为不适用；上一窗口采集失败不得判新出现。
- 可靠性、资金验证、个股映射和公告确认不参与排序，缺失不影响入榜。
- 每条必须展示消息详情、时间、监控区间、热度变化、变化判定、传播路径、终点热度与具体核验路径。
- 旧闻必须同时展示原始发布时间和本轮再升温/再次发现时间。
- 不读取或输出密码、Cookie、Local Storage、浏览器历史或其他敏感会话数据。
- 不实现自动调度、数据库、推送或长期历史曲线。
- 当前目录不是Git仓库；不执行提交、推送、PR、发布或部署。

---

## Discovery and delivery gates

- Repository root: `/Users/aviva/Projects/market_news`。
- Repository state: `git status --short --branch`于2026-07-29 17:28 CST返回“not a git repository”；无分支、HEAD、upstream、staged或commit门槛可执行。
- Instructions: 未发现`AGENTS.md`；受根级系统/开发者指令、V4设计及现有`HANDOFF.md`约束。
- Existing artifacts: V2、V3、短线雷达报告、设计、交接、计划、发现与进度Markdown文件。
- Existing test harness: 无软件测试、构建、编译、lint或UI应用；本任务交付物是Markdown研究报告。
- Pre-change full baseline: 2026-07-29 17:28 CST运行V3只读验证，17条/17分值/17时间字段、43链接、分值降序、0个韭研首页链接、0个完整建议措辞，退出0。
- Preservation: 不改写V2、V3和用户既有材料；V4另建文件，证据另建文件，仅追加更新计划/发现/进度。
- Authorization stops: 不购买会员、不绕过登录/验证码/安全策略，不进行外部发帖、评论、点赞、消息发送或任何Git/发布动作。

## Test matrix

- Unit: N/A；没有生产函数或可独立调用的软件单元。用报告结构断言替代。
- Integration: 证据表到V4报告的逐条映射；Python检查每个条目包含规定字段，分值和为100制总分，至少30条且按规则降序。
- UI: N/A；不改网页或应用UI。Chrome仅用于读取用户已授权的可见页面状态，不操作账户内容。
- Security/privacy: 检查报告与证据不包含Cookie、Token、Local Storage、密码、个人浏览历史或本地私密配置；只保存公开内容字段和永久链接。
- Generated artifact: `evidence/2026-07-29-v4-monitoring-snapshots.md` → `reports/2026-07-29-pure-news-hot-ranking-v4.md`；通过条目数量、字段、分值、排序、链接、时间和趋势证据验证。
- Build/compile/lint: N/A；纯Markdown无构建系统。运行Markdown结构与空白检查、URL形态检查和禁用措辞扫描。
- Independent review: 该报告涉及金融资讯排序且用户可能据此投入注意力，完成草稿后使用可用的内部只读审阅能力检查数据映射、分值和过度推断；不授权外部人员或系统协调。

### Task 1: 建立V4候选与快照证据表

**Files:**
- Create: `evidence/2026-07-29-v4-monitoring-snapshots.md`
- Read: `reports/2026-07-29-pure-news-hot-ranking-v3.md`
- Read: `findings.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: V3的17条基线快照、V4设计的“激增/新出现/暂无趋势数据”规则。
- Produces: 至少35个候选的规范化证据记录；每个记录包含`event_id`、标题、事实摘要、首次发布时间、首次发现时间、监控起止、逐平台起止字段、变化状态、永久链接、可靠性与未确认项。

- [ ] **Step 1: 写入失败验收并观察RED**

运行：

```bash
python3 -c 'from pathlib import Path; p=Path("evidence/2026-07-29-v4-monitoring-snapshots.md"); assert p.exists(); assert p.read_text().count("## EVT-") >= 35'
```

预期：FAIL，因为证据文件尚不存在。

- [ ] **Step 2: 从V3抽取17条基线**

逐条记录V3已有采集时间、原始热度和永久链接；禁止把没有采集时间的值补写为同时点快照。液冷旧帖记录原帖时间2026-04-10 06:22:16和本轮发现时间2026-07-29 08:15。

- [ ] **Step 3: 补充至少18个新候选**

检查财联社公开电报、NewsNow、东方财富人气榜、微博、雪球、X、韭研公社及公开媒体/官方源，保存本轮实际检查过的来源、关键词和时间。候选不足35时继续检查V2遗漏事件、当日公告/业绩、产业涨价、海外科技、政策与消费事件，直到达到35个可核验候选。

- [ ] **Step 4: 保存终点快照和变化判定**

对可重访字段记录终点值；双时点计算绝对变化和同口径相对变化；已覆盖但此前未发现的记“新出现”；无法证明此前覆盖的记“暂无趋势数据”。每个激增结论写明命中的门槛。

- [ ] **Step 5: 运行证据完整性GREEN检查**

运行：

```bash
python3 -c 'from pathlib import Path; import re; s=Path("evidence/2026-07-29-v4-monitoring-snapshots.md").read_text(); ids=re.findall(r"^## (EVT-[0-9]{3})",s,re.M); assert len(ids)>=35; assert len(ids)==len(set(ids)); assert s.count("**变化判定：**")>=35; assert s.count("**核验路径：**")>=35'
```

预期：PASS，至少35个唯一候选，均有变化判定和核验路径。

### Task 2: 计算变化分与统一热点权重

**Files:**
- Modify: `evidence/2026-07-29-v4-monitoring-snapshots.md`
- Read: `docs/superpowers/specs/2026-07-29-pure-news-hot-ranking-v4-design.md`
- Modify: `findings.md`

**Interfaces:**
- Consumes: Task 1的候选、快照和变化状态。
- Produces: 每个候选的五项分值、总分、排序资格和未入榜理由；供Task 3直接排序。

- [ ] **Step 1: 写入分值完整性失败检查并观察RED**

运行：

```bash
python3 -c 'from pathlib import Path; import re; s=Path("evidence/2026-07-29-v4-monitoring-snapshots.md").read_text(); ids=re.findall(r"^## EVT-[0-9]{3}",s,re.M); scores=re.findall(r"\*\*评分：\*\* 覆盖([0-9]+) \+ 变化([0-9]+) \+ 绝对热度([0-9]+) \+ 新鲜度([0-9]+) \+ 频次([0-9]+) = ([0-9]+)",s); assert len(scores)==len(ids)'
```

预期：FAIL，因为候选尚未全部评分。

- [ ] **Step 2: 按设计逐项评分**

覆盖分上限25、变化分上限30、绝对热度上限20、新鲜度上限15、频次上限10。新出现按7—20分；孤立单快照变化分为0；激增必须满足双时点和绝对增量保护。

- [ ] **Step 3: 标记主榜资格**

优先选取总分前30条；第31条以后若满足设计中的任一扩展门槛继续入榜。未入榜候选保留在证据表并写明未达到哪项门槛，防止静默遗漏。

- [ ] **Step 4: 运行分值与边界GREEN检查**

运行：

```bash
python3 -c 'from pathlib import Path; import re; s=Path("evidence/2026-07-29-v4-monitoring-snapshots.md").read_text(); rows=[tuple(map(int,x)) for x in re.findall(r"\*\*评分：\*\* 覆盖([0-9]+) \+ 变化([0-9]+) \+ 绝对热度([0-9]+) \+ 新鲜度([0-9]+) \+ 频次([0-9]+) = ([0-9]+)",s)]; assert len(rows)>=35; assert all(a<=25 and b<=30 and c<=20 and d<=15 and e<=10 and a+b+c+d+e==t for a,b,c,d,e,t in rows)'
```

预期：PASS，所有候选分值边界正确且总分可复算。

### Task 3: 生成不少于30条的V4报告

**Files:**
- Create: `reports/2026-07-29-pure-news-hot-ranking-v4.md`
- Read: `evidence/2026-07-29-v4-monitoring-snapshots.md`
- Modify: `HANDOFF.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: Task 2已评分并标记资格的候选。
- Produces: 按总分、变化分、最近更新时间排序的V4主榜及渠道覆盖/失败清单。

- [ ] **Step 1: 写入报告结构失败检查并观察RED**

运行：

```bash
python3 -c 'from pathlib import Path; import re; p=Path("reports/2026-07-29-pure-news-hot-ranking-v4.md"); assert p.exists(); s=p.read_text(); assert len(re.findall(r"^## [0-9]+\.",s,re.M))>=30'
```

预期：FAIL，因为V4尚不存在。

- [ ] **Step 2: 生成主榜头部口径说明**

写明报告截止时间、时区、五项分值、30条起步但不设上限、新出现与激增规则、跨平台数字不可直接相加、互动数动态变化及完整性边界。

- [ ] **Step 3: 为每个入榜事件写完整字段**

每条严格包含：消息详情、时间、监控区间、热度变化、变化判定、传播路径、当前原始热度、具体核验路径、可靠性、尚未确认、可选A股附注。多个平台变化用紧凑表格或分号分隔，始终携带快照时间。

- [ ] **Step 4: 写渠道状态与未入榜候选说明**

报告末尾列成功来源、失败来源、单快照数量、激增数量、新出现数量、未入榜候选数量及门槛原因；不得写市场结论或操作建议。

- [ ] **Step 5: 运行报告结构GREEN检查**

运行：

```bash
python3 -c 'from pathlib import Path; import re; s=Path("reports/2026-07-29-pure-news-hot-ranking-v4.md").read_text(); n=len(re.findall(r"^## [0-9]+\.",s,re.M)); required=["消息详情","时间","监控区间","热度变化","变化判定","传播路径","当前原始热度","核验路径","可靠性","尚未确认","可选A股附注"]; print({"items":n,**{k:s.count("**"+k+"：**") for k in required}}); assert n>=30; assert all(s.count("**"+k+"：**")==n for k in required)'
```

预期：PASS，每个主榜条目均包含11个规定字段。

### Task 4: 审阅并最终验证V4

**Files:**
- Review: `evidence/2026-07-29-v4-monitoring-snapshots.md`
- Review: `reports/2026-07-29-pure-news-hot-ranking-v4.md`
- Review: `docs/superpowers/specs/2026-07-29-pure-news-hot-ranking-v4-design.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: Task 3的V4报告与全部证据。
- Produces: 完整审阅记录、修正后的最终报告和新鲜验证证据。

- [ ] **Step 1: 执行独立只读审阅**

审查重点：30条以上是否遗漏达到门槛的候选；每个激增是否有双时点同口径证据；每个新出现是否有前序覆盖证明；时间是否混淆发布时间与发现时间；分值是否过度依赖可靠性或资金；链接是否为具体内容。

- [ ] **Step 2: 对阻断问题建立失败复现并修正**

每个阻断问题先用最小`rg`或Python断言复现失败，再修改证据或报告，随后重跑对应断言。无法证实的数据降级为“暂无趋势数据”或删除具体数字，不以估算掩盖缺口。

- [ ] **Step 3: 运行最终完整验证**

运行：

```bash
python3 -c 'from pathlib import Path; import re; s=Path("reports/2026-07-29-pure-news-hot-ranking-v4.md").read_text(); n=len(re.findall(r"^## [0-9]+\.",s,re.M)); score_rows=[tuple(map(int,x)) for x in re.findall(r"热点权重：([0-9]+)/100.*?覆盖([0-9]+) \+ 变化([0-9]+) \+ 绝对热度([0-9]+) \+ 新鲜度([0-9]+) \+ 频次([0-9]+)",s)]; totals=[r[0] for r in score_rows]; required=["消息详情","时间","监控区间","热度变化","变化判定","传播路径","当前原始热度","核验路径","可靠性","尚未确认","可选A股附注"]; urls=re.findall(r"https?://[^)\s]+",s); bad=re.findall(r"一眼结论|操作建议|建议买入|建议卖出|读取Cookie|Local Storage",s); print({"items":n,"score_rows":len(score_rows),"descending":totals==sorted(totals,reverse=True),"links":len(urls),"bad":bad}); assert n>=30 and len(score_rows)==n; assert all(t==a+b+c+d+e for t,a,b,c,d,e in score_rows); assert totals==sorted(totals,reverse=True); assert all(s.count("**"+k+"：**")==n for k in required); assert not bad; assert "https://www.jiuyangongshe.com/)" not in s'
```

预期：PASS；条目不少于30、分值可复算且降序、字段完整、无首页替代具体韭研帖、无操作建议或敏感数据措辞。

- [ ] **Step 4: 检查文件范围与交付状态**

运行`find`和`rg`确认只新增V4设计、V4计划、证据表和V4报告，并仅更新计划/发现/进度/交接；临时截图、浏览器数据、凭据和私密配置不进入工作目录。记录当前目录非Git仓库，因此commit、push、PR、merge、deploy和publish均未执行。

## Release readiness

- Intended inclusions: V4设计、实施计划、监控证据、V4报告，以及任务/发现/进度/交接的必要增量。
- Explicit exclusions: V2/V3覆写、浏览器会话数据、Cookie/Token/密码、验证码、会员内容、临时截图、自动化代码、数据库、推送配置、外部消息与任何Git动作。
- Final artifact: `reports/2026-07-29-pure-news-hot-ranking-v4.md`。
- Completion is blocked if少于30条、任一激增缺双时点、任一新出现缺前序覆盖证明、规定字段缺失、分值不可复算/非降序、具体核验链接缺失，或最终完整验证非零退出。
