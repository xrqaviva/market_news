# 新闻雷达可用接口与来源清单（2026-08-14 沉淀）

**定位：** 本文件是数据采集接口的权威台账。每个接口标注：通道、URL 模式、可用字段、验证状态、限制与使用注意。新增/失效接口必须在此登记。采集规则见《全窗口遍历式发现方法》（docs/2026-08-13-full-window-discovery-method.md）。

## 1. 行情/数据 API

| 接口 | 通道 | URL 模式 | 可用字段 | 状态 | 限制与注意 |
|---|---|---|---|---|---|
| 新浪行情 API | curl/HTTP | `https://hq.sinajs.cn/list=sh000001,sz399001` | 指数/个股实时快照（开高低收、成交量额、时间） | ✅ 实测可用 | 必须带 `Referer: https://finance.sina.com.cn/`；返回 GBK 需转码；`sh`/`sz`/`hk` 前缀 |
| 财联社 API | HTTP | `https://api3.cls.cn/nodeapi/telegraphList?app=CailianpressWeb&os=web&sv=7.7.5&sign=...` | 电报 JSON | ⚠️ 存活但需签名 | 返回 `{"errno":50101,"msg":"小财正在加载中..."}`，sign 参数需客户端算法，未逆向，不采用 |
| 新浪 7×24 回放 API | curl/HTTP | `https://zhibo.sina.com.cn/api/zhibo/feed?page={n}&page_size=100&zhibo_id=152&tag_id=0&dire=f&dpc=1` | 全窗口快讯流：`create_time`（精确到秒）、`rich_text`、`ext.docurl`（**永久详情页直链**）、id | ✅ 2026-08-14 实测 | **主发现/核验通道**：page=1 最新、page 递增回看；`dire=f` 为向前翻页；2300条约23页；`ext` 为 **JSON 字符串需二次解析**；约 6% 条目无 docurl；详情页 `https://finance.sina.com.cn/7x24/YYYY-MM-DD/doc-xxx.shtml` 纯 HTML 可直接 curl；需 UA+Referer `https://finance.sina.com.cn/7x24/` |
| 东方财富推送 API | HTTP | `https://push2.eastmoney.com/...` | 行情推送 | 未实测 | 历史域名单中出现，未验证 |
| 东方财富 7×24 回放 API | curl/HTTP | `https://np-listapi.eastmoney.com/comm/web/getNewsByColumns?client=web&biz=web_724&column=350&order=1&needInteractData=0&page_index={n}&page_size=100&req_trace={n}` | 全窗口快讯流：`showTime`（精确到秒）、`title`、`summary`、`mediaName`（财联社/新京报/澎湃等）、`uniqueUrl`（**永久详情页直链**） | ✅ 2026-08-16 实测 | **第二发现源（与新浪 7×24 并集遍历）**：覆盖财联社电报与东财原创研报/行业文章，新浪常缺（例：SK海力士大连工厂、CRO跑赢CPO、SST固态变压器、张忆东观点）；需 UA+Referer `https://finance.eastmoney.com/7x24.html`；**必须带 `req_trace` 参数**否则返回 error；page 递增回看约 2 天（实测 500 条到 08-14 06:00）；抓取脚本：`scripts/fetch_em7x24.py --start "<窗口起点>" --out <evidence>.jsonl` |
| NewsNow 公共 JSON | HTTP | NewsNow 站内 JSON 接口 | 聚合榜位 | ❌ 历史失败 | 2026-07-29 起超时返回非 JSON，改走公共网页 |
| 巨潮资讯 cninfo | 浏览器 | `http://www.cninfo.com.cn/new/index` | 法定公告 | ✅ 浏览器可达 | 命令行 WebFetch 未验证 |

## 2. WebFetch 可用的文章/快讯源（无需浏览器）

| 来源 | URL 模式 | 可用内容 | 提取注意 |
|---|---|---|---|
| 新浪财经 7×24 | API 直链（见第1节） | 全窗口快讯（时间戳+docurl 永久链接） | 优先 API；详情页纯 HTML 可 curl |
| 新浪财经 7×24 网页 | `https://finance.sina.com.cn/7x24/` | 最近约25分钟快讯（标题+时间） | 只作发现与对账；回放必须走 API |
| 财联社电报（完整流） | ✅ 浏览器 DOM 可读（无需登录） | 电报页 `https://www.cls.cn/telegraph` 为 Next.js，**DOM 快照直接渲染完整电报流**（时间+全文+阅读量+详情链接 `/detail/<id>`）；API `/api/csw` 实测 404、旧 `nodeapi/telegraphList` 已下线 | 2026-08-16 浏览器实测：未登录状态全文可读（12:08 至 08:53 完整流） | 每日遍历时浏览器打开该页读取 DOM；回放历史窗口需滚动加载（配合日期参数）；东财 7×24 已间接覆盖其精选 |
| 韭研公社 | ✅ 浏览器 DOM 可读（无需登录） | `https://www.jiuyangongshe.com/` 首页 DOM 直接渲染「最新热度/最新发布/最新互动」帖流：发帖人、时间、全文摘要、关联股票、文章链接 `/a/<id>`；含券商研报转载（方正/开源等）与题材挖掘 | 2026-08-16 浏览器实测：未登录可见完整帖流（长韭杯、锐捷网络研报、算电岛/特锐德、机器人 T 进展等） | 每日遍历时浏览器打开首页读取「最新热度」帖流；完整内容需点开 `/a/<id>` 详情 |
| 雪球 | 🟡 部分可读 | `https://xueqiu.com/` 未登录可见：指数行情、**热股榜**（1h/24h 热门股+涨跌幅）、热门基金；「热门话题/7x24/时间线」需登录（Loading 挂起） | 2026-08-16 浏览器实测：热股榜可读（儒意电影/茅台/长鑫科技/天孚通信等） | 每日遍历读热股榜（市场情绪/资金关注）；时间线等需用户在 IAB 登录后读取 |
| 微博热搜榜 | ✅ 浏览器 DOM 可读（用户已登录） | `https://s.weibo.com/top/summary` 热搜榜直接渲染：关键词+热度值+分类（热搜/文娱/社会/科技/生活/体育/ACG） | 2026-08-16 浏览器实测：已登录（仙人球嗷）、热搜榜+热度值完整可读（胖东来118万等） | 每日遍历读热搜榜（社会情绪/突发发现）+ 财经相关话题；热度值可用于双时点变化 |
| 淘股吧 | ✅ 浏览器 DOM 可读（用户已登录） | `https://www.taoguba.com.cn/`（跳转 tgb.cn）首页直接渲染：题材分布、淘股论坛帖（阅读数/时间/作者/链接`/a/<id>`）、极速快讯 `https://shuo.tgb.cn/newsFlash/`、复盘帖（题材梯队） | 2026-08-16 浏览器实测：已登录（avivaxrq）、题材分布+复盘帖可读 | 每日遍历读题材分布+复盘帖（短线情绪/题材梯队）+极速快讯 |
| 东方财富人气榜 | ✅ 浏览器 DOM 可读（无需登录） | `https://guba.eastmoney.com/rank/?tab=rank-7&type=7` 直接渲染：排名、排名较昨日变动、代码/名称、最新价、涨跌幅、新晋粉丝%/铁杆粉丝%（更新时间戳） | 2026-08-16 浏览器实测：未登录可读（金牛化工第5、亨通光电涨停等） | 每日遍历读人气榜（市场资金关注/情绪），榜位可用于双时点变化 |
| X（推特） | ✅ 浏览器可读（用户已登录） | `https://x.com/home` 用户会话已登录（@XrqXu44788），Home timeline 直接渲染 | 2026-08-16 浏览器实测：已登录、时间线可见 | 每日遍历读取 Home timeline（用户关注大V动态）；**只读页面可见内容，不读取/不输出任何凭据**；关注列表调整由用户操作 |
| 东方财富 7×24 回放（推荐） | `scripts/fetch_em7x24.py` | 全窗口快讯（showTime+summary+mediaName+uniqueUrl 永久链接） | 优先 API；每报告窗口与新浪 7×24 **并集遍历**，防止单源漏新闻 |
| 东方财富 7×24 | `https://finance.eastmoney.com/a/cywjh.html` | 头条/资讯精华/网友点击榜（标题+完整URL） | WebFetch 提示"标题 = URL"格式提取效果最好；文章 URL 形如 `/a/YYYYMMDD<数字>.html` |
| 第一财经 | `https://www.yicai.com/` | 头条新闻（标题+URL，如 `/news/103317713.html`） | 财经政策/公司稿覆盖好，双源首选 |
| 证券时报 | `https://www.stcn.com/` | 头条（标题+URL，如 `/article/detail/4074971.html`） | 监管/政策/公司稿 |
| 界面新闻 | `https://www.jiemian.com/` | 科技/财经早报（如 `/article/14919740.html`） | 科技/AI/公司稿覆盖好；有每日科技早报 |
| 中国证券报（中证网） | `https://www.cs.com.cn/` | 港股/政策稿（如 `/gppd/ggzx/.../detail_....html`） | 港股与政策 |
| 澎湃 | `https://www.thepaper.cn/` | 财经/社会稿（如 `/newsDetail_forward_....html`） | 补充覆盖 |
| 上证报 cnstock | `https://www.cnstock.com/` | 标题可见 | WebFetch 有时返回空，优先浏览器 |

## 3. 浏览器专用源（ZCode 内置浏览器 iab）

| 来源 | 入口 | 可用字段 | 状态 |
|---|---|---|---|
| 财联社 cls.cn | 首页/电报/详情 `/detail/<id>` | 电报全窗口流、阅读/评论/分享原值、分钟时间 | ✅ 主发现流（全窗口遍历） |
| 东方财富资讯/股吧 | eastmoney.com / guba | 文章、评论、人气榜 | ✅ |
| 证券时报/上证报/一财/每经 | stcn/cnstock/yicai/nbd | 头条与文章 | ✅ |
| 同花顺财经 | 10jqka.com.cn | 资讯 | ✅（问财/热榜能力未验证） |
| 巨潮资讯 | cninfo.com.cn | 法定公告 | ✅ |
| 微博热搜榜 | `https://s.weibo.com/top/summary` | 50条热搜（榜位+热度值） | ✅ 无需登录 |
| 雪球 | xueqiu.com | 首页/热帖 | ✅ 公开页；互动需登录 |
| 淘股吧 | tgb.cn | 公开帖/热帖 | ✅ 公开页；互动需登录 |
| 韭研公社 | jiuyangongshe.com | 题材帖详情 | ✅ 公开 |
| NewsNow | newsnow.busiyi.world | 聚合热榜 | ✅ |
| 开盘啦 | kaipanla.com | 仅官网说明 | ⚠️ 实时情绪字段无公开入口 |

## 4. 登录渠道（互动热度原值）

| 平台 | 状态 | 可采字段 | 说明 |
|---|---|---|---|
| 微博 | ✅ 已登录 | 单帖转评赞、话题值、热搜榜位 | 登录态在 IAB 内由用户自行维护 |
| 雪球 | ✅ 已登录 | 讨论/赞/收藏/转发 | 同上 |
| X | ✅ 已登录 | 回复/转发/赞/浏览、趋势 | SPA 重载慢，逐条采集成本高 |
| 淘股吧 | ✅ 已登录 | 浏览/评论/加油 | 同上 |

登录态仅在本次 ZCode 进程内有效；每日启动按方法文档第9节核验。

## 5. 不可用或受限（有替代）

| 源 | 原因 | 替代 |
|---|---|---|
| Reuters / AP / Investing | 浏览器导航超时 | 财联社环球市场稿/美股收盘稿 |
| The Information / Wind / Choice / Datayes | 付费墙/付费授权 | 公开转载/公司IR |
| 开盘啦实时情绪字段 | App内 | 无 |

## 6. 使用注意（实操沉淀）

1. **WebFetch 提取技巧**：对文章列表页，提示词写明"列出标题及其完整URL，格式：标题 = URL"命中率最高；分关键词提问优于一次问全。**提取模型不稳定**：同一 URL 可能时通时挂（返回空或 403），失败后间隔重试 1-2 次，或换列表页入口。
2. **双源规则**：重要条目至少两个独立来源（不同平台）；同一平台多篇不算双源。当前待双源清单见当日报告"来源覆盖与核验缺口"。
3. **接口可用性随环境变化**：hq.sinajs.cn 已验证；浏览器 webview 偶发"guest not attached"，重试或等 5-10 秒即可恢复；**webview 故障高峰期（连续多次失败）应暂停浏览器任务，改用 WebFetch/API 通道**。
4. **新浪 7×24 无直链**：只作发现与对账，条目直链需回财联社/东财等取得。

## 7. 反模式记录（2026-08-14 实测，勿重复踩坑）

| 通道 | 结果 | 结论 |
|---|---|---|
| 百度搜索 curl | 首查询成功，随后全部被反爬拦截（636字节拦截页） | 不可作为稳定接口；偶发可用 |
| DuckDuckGo HTML / Sogou / 360 / Bing | 全部 JS 墙或返回空 | 不可用 |
| 新浪新闻搜索 search.sina.com.cn | JS 渲染，curl/WebFetch 均空 | 不可用（浏览器可试） |
| 网易 F10 quotes.money.163.com | 502 | 不可用 |
| 必应（浏览器） | 站点搜索不返回过滤结果 | 不可用 |
| WebFetch 批量提取 | 命中率约 50%，时通时挂 | 可用但需重试与多轮 |
| 财联社站内/电报搜索（SPA） | 输入不生效 | 不可用，用全窗口遍历替代 |
| 财联社搜索页 /search?keyword= | 404（"页面找不到了"） | 不可用 |
| 一财搜索 /search?keys= | 常用关键词 0 结果（仅覆盖部分近期文章） | 不可用为通用通道；双源核验不依赖 |
| 东财搜索 so.eastmoney.com | WebFetch 返回空 | 不可用（浏览器可试） |
| 新浪7×24 部分快讯 | 无 docurl（约 6%） | 来源缺失时换同主题有 docurl 节点 |
| 财联社 webview 激活 | 偶发 "could not be restored for activation" | 用户手动切到目标页（前台）后重试可恢复；或转新浪 API |

## 8. 数据降级规则（用户裁定，2026-08-15 持久化）

**规则：** 接口无法获取数据时，先从**已接入的备用接口**取同品种数据（如 东财→腾讯→新浪→SMM→官方源）；仍不行则**寻找/接入新的可用接口**并登记到本台账与 daily_info 的 `config/instruments.json`；只有全部通道都失败时才允许展示空缺，并如实标注原因。**禁止"接口失败就展示为空"而不做降级尝试。**

**2026-08-15 实证（东财 IP 限流 24h 级）：**
- 美股/欧洲/期货：腾讯单源兜底 ✓（未展示空）
- 国际商品（布伦特/天然气/铂金/钯金）：腾讯 hf 源 ✓（周末日期回退修复）
- 小金属 11 项：SMM ✓（浏览器 UA 修复）
- 汇率：boc+ecb 多数同日期共识 ✓（滞后源不再拖垮）
- 美元指数：东财限流且腾讯/新浪无可用替代 → 唯一如实空缺，恢复后自动补
- 已实施的长期加固：东财请求加 Referer、curl 改浏览器 UA、接口台账持续登记新通道

**2026-08-17 实证（涨跌家数三连空根因）：** A 股非ST涨跌家数从 08-14 起连续四天空缺（08-14/15/16 全是 `—`）。非接口故障，而是三道核验闸门在盘前/盘后场景下过激冲突——本质与 08-15 行情品种的"盘前未来日期标记"同源，但 breadth 链 08-15 那一轮漏修，08-17 才补齐：

| 闸门 | 现象 | 修复 |
|---|---|---|
| 新浪 `hq.sinajs.cn` 标 08-17 | `_sina_market_date()` 严格核验失败，整个新浪源被拒 | `BreadthCollector._normalize_stamp` 静态方法：盘前/周末未来标记 ≤3 天 + 非交易时段 → 重标 expected |
| 东财 `push2delay` f124=08-17 | eastmoney 单源 5333 样本 → `_verify_single` 判 unexpected_market_date conflict → 全空 | collect 层 `replace(result, market_date=normalize(...))` |
| 双源代码集合差 6.8% / 涨跌计数差 20+ | 两源是独立全市场快照，覆盖与时点本就不同 → verify_breadth 判 eligible_code_set_mismatch / breadth_outside_tolerance → 全空 | verify_breadth 容差放宽：集合对称差 ≤10%、样本差 ≤2%、计数差容差 `max(20, 0.5%)`；duplicate_eligible_codes 从 conflict 删除（去重后的统计本身有效） |

**教训统一记入**：`verification.py` 与 `breadth_collect.py` 的 `_normalize_stamp` 是同一个根因的镜像修复。任何"盘前/周末日期标记"的场景必须走统一规则；后续若发现同类 bug（例如商品源快照日期标记），复用此模式而非重新发明。**用户原话："这个不是持久化了吗？为什么还会犯错"——根因是 breadth 这条链的持久化遗漏。** 复盘后已纳入台账，确保下次同类问题一眼可查。

### 8.1 避坑流程（2026-08-17 用户裁定持久化）

**用户原话**："这些问题全部都持久化下来，把如何避坑也记录下来，确保下一次任务没问题"。本节为下次接到类似任务时的**强制自检清单**，每条都对应一次真实失败模式。

### 8.2 报告生成提速（2026-08-18 用户裁定：不能折损数据质量")

**用户原话**："你现在跑一次太慢了，需要提升效率……可以考虑技术手段，例如优化代码、并行跑等，注意不是要折损数据质量（例如少采集等）。"

**耗时实测（08-18 全流程）：**

| 阶段 | 原耗时 | 优化后 | 手段 |
|---|---|---|---|
| 新浪 7×24 翻页 | ~40-60s（串行+间隔） | **~5s（两天窗口 2315 条）** | `scripts/fetch_api_sources.py` 8 线程并发翻页，不损条数 |
| 东财 7×24 | ~30s | **~5s（700 条）** | 复用 `fetch_em7x24.py`（本身已较快） |
| 主题候选账本分析 | 人工多次手工扫描 | **0.13s** | `scripts/scan_evidence.py` 词带扫描，输出时间+来源+LINK 标记 |
| 报告生成（数据编制） | 大量时间（引号 bug 反复） | **minutes** | `data/reports/<日期>.json` JSON 数据层 + `scripts/gen_report.py` 自动匹配来源/套契约 |
| 浏览器 7 源采集 | ~60-75s | 串行下限（无法并行） | IAB webview 单例 + Browser Use 为 main-agent-only，**subagent 不能开浏览器** |

**新流程（下次跑）：**
1. `python3 scripts/fetch_api_sources.py --start "YYYY-MM-DD 00:00" --out-dir evidence` → 并发抓新浪+东财
2. 主代理浏览器串行采 7 源（韭研/人气榜/微博/X/淘股吧/财联社/雪球），evidence 落盘
3. `python3 scripts/scan_evidence.py --sina "...窗口..." --em "...窗口..." --with-link-only` → 候选账本（LINK 列即带 docurl 的来源，直接规避"needs source link"）
4. 填 `data/reports/<日期>.json`（NEW/OLD/THEMES + pending/coverage，字段天然无引号地狱）
5. `python3 scripts/gen_report.py --data data/reports/<日期>.json --sina ... --em ... --out reports/<日期>-0800-news-ranking-preview.md` → 自动生成 + 校验
6. 构建 dist / 测试 / 部署（现有流程）

**浏览器源为何不能 subagent 并行**：Browser Use 技能声明 main-agent-only，subagent 无法加载；且 IAB webview 单例（批量 tabs.new 会触发 "guest not attached"）。7 个浏览器源只能由主代理串行，每个约 12-18s 是环境下限。**这不属数据质量折损**——只是无法压缩传输/渲染等待。

**JSON 数据层要点**：`data/reports/<日期>.json` 用 `evt_prefix`（如 "evt-20260818"）+ THEMES 成员编号自动映射完整 id；`other_news`/`pending`/`coverage` 可选字段控制报告尾段；生成器在输出前用 `("sina"|"em", time, url, text)` 结构自动建来源表，缺 LINK 会 `sys.exit(2)` 提前暴露。**不再需要手写 41 条 Python 元组。**


#### A. 数据/接口层

1. **任何"未来日期标记"问题，必须先复用 `_normalize_stamp` 模式，不要重新发明规则**。盘前/周末/节假日所有源都可能在快照日期上"撒谎"——价格是上一交易日的，日期标当天。**自检**：列出该品种的全部源，逐个调用看 `market_date`；凡超出 expected_date 且 ≤3 天的，配合 as_of 在非交易时段 → 一律归一化。
2. **核验规则的容差要紧贴"接口实现差异"和"数据错误"的边界**。不能因为"两源对不上"就一刀切 conflict——独立全市场快照本来就 6.8% 代码集不同、~20 计数不同。**自检**：所有 verify_* 函数先问"两个值差异来自接口实现还是来自数据错误"——前者放宽容差，后者保留闸门。
3. **双源数字超容差时，落回单源 + 如实披露冲突原因**，而不是整段判 conflict 全空。**自检**：每个 conflict reason 都有对应降级路径（单源 + 披露 / 取较大样本 + reason）。
4. **品类边界跨越时，必须重检**：08-15 修行情品种时，breadth 是同源问题但不同代码链——任何"全接口问题修复"必须**遍历所有调用栈**（market.py / breadth_collect.py / news_collect.py 等），不能只补一处。
5. **接口台账不能"光记录不核验"**：每个 fallback 链路要在 force run 里实际走通，证据落到 `evidence/cron-runs.jsonl`，否则就是纸面持久化。

#### B. 渲染/UI 层

6. **`overflow:auto / hidden` 容器会裁剪绝对定位子元素（含 `::before`）**。要扩展背景到容器外，要么换 `position:fixed` 让元素脱离文档流，要么把扩展内容移到外层。**自检**：任何"伪元素延伸超出父级"的设计都要先验证父级 overflow。
7. **页面布局调整要同步测试契约**：sticky → fixed 改变 `position` / `top` / `height` / `padding` 等可计算属性时，layout 测试断言必须同步更新（`tests/report_layout_browser.mjs`）。
8. **fixed 元素脱离文档流后，需要手动给主列让位**（`page-shell padding-left: 76px`），否则会盖住内容。
9. **mobile 端 `display:none` 的元素，desktop 端改了定位后要再确认 mobile 不受影响**——layout 测试的 mobile 分支就是为此存在。

#### C. 报告层

10. **stock_groups / synthetic 指数等"特殊段"在 fusion/外引构建时易遗漏**：fusion.py 只处理了行情品种，没处理 stock_groups——任何新增段落必须从"晨报里有没有"反推"市场新闻里要不要显示"。
11. **数据日期不动 ≠ 数据没刷新**：盘后或周末源数据就是上一交易日收盘，这是预期而非 bug。**自检**：用 as_of 判断"是不是今天本就没有新数据"，不要急着改 expected。

#### D. 通用

12. **用户提"白底/留白"先看图确认是哪一侧/哪种留白**：上下、左右、内 padding、外 page-shell、卡片内——四种场景修法完全不同。截图比描述准。
13. **修改后必须真正部署并截图验证**：layout test PASS 不等于用户看到的视觉对——Chrome headless 与 IAB、CSS 子像素渲染差异都会掩盖问题。重要变更发部署后再让用户看。
14. **每次修复后必须回答"下一个同类问题会不会再犯"**：把根因（不是症状）写入 docs/，并让新规则对**所有调用点**生效。否则就是同一根因的不同症状轮替出现。

## 9. 空值清零审查（用户裁定，2026-08-15 复盘固化）

**教训复盘（美元指数案例）：** 东财限流导致美元指数空缺时，曾以"周一自动恢复"作为交付状态——这违反用户"取不到就换源"的明确要求。根因：①把解释原因当解决问题；②对候选源（新浪 DINIW，项目内置解析器）因周末日期标记草率判定不可用，未应用已有日期修正手段；③缺少空值穷尽审查。

**强制流程（每个空缺条目）：**
1. 先列全部已接入备用源并逐个实测（东财→腾讯→新浪→SMM→官方源）；
2. 再列候选新源（项目内置解析器：sina_diniw/stooq/yahoo/investing）并验证；
3. 遇到"日期错位/周末标记"类问题，先应用已有修正（周末回退、多数同日期共识、同日去重）再判源不可用；
4. 可行即接入并登记；全部失败才允许空缺，附"已尝试源+失败原因"证据；
5. **"等数据源恢复"不是交付状态**——要么今天有值，要么证明已穷尽。

## 10. 图片识别能力（vision skill，2026-08-15 接入）

**能力：** 当前模型为纯文本（无原生识图）。用户粘贴/分享图片（本地路径或网络 URL）时，用外部视觉模型识别。已实测可用（modelscope 通道）。

**用法：**
```bash
node "/Users/aviva/Documents/AI/Skills/vision/vision.js" "<图片绝对路径>" "这是一张截图。请用中文识别并完整提取图中所有可见文字…"
node "/Users/aviva/Documents/AI/Skills/vision/vision.js" --url "<图片URL>" "请描述这张图片"
```
- 截图优先：提取全部文字（报错/数字/按钮/标题），按左上→右下描述布局
- 多服务自动切换（providers.json）；配置与凭据在 vision.js 同目录，**不读取/不输出凭据**
- 触发：用户发图片、"Saved attachments:" 列表、要求看截图/识别图

**2026-08-15 实测：** 成功识别用户此前发的"美元指数/汇率全空"截图，文字与布局完整提取。

## 10.5 浏览器源遍历（2026-08-16 实测接入）

**背景：** 新浪 7×24 与东财 7×24 是 API 源，但财联社完整电报、韭研公社、雪球热股、X 时间线等无法 API 抓取。浏览器（IAB）DOM 读取补齐这些盲区。

**每日遍历顺序（报告窗口内）：**
1. `scripts/fetch_em7x24.py` 抓东财 7×24 → evidence JSONL
2. 新浪 7×24 API 抓取（现有脚本）→ evidence JSONL
3. 浏览器打开以下页面读取 DOM（只读内容，不碰凭据）：
   - 财联社电报 `https://www.cls.cn/telegraph`（完整电报流，无需登录）
   - 韭研公社 `https://www.jiuyangongshe.com/`（最新热度帖流，无需登录）
   - 雪球 `https://xueqiu.com/`（热股榜+登录后时间线/热门话题）
   - X `https://x.com/home`（用户已登录时读 Home timeline）
   - 微博热搜 `https://s.weibo.com/top/summary`（热搜榜+热度值，用户已登录）
   - 淘股吧 `https://www.taoguba.com.cn/`（题材分布+复盘帖+极速快讯，用户已登录）
   - 东财人气榜 `https://guba.eastmoney.com/rank/?tab=rank-7&type=7`（榜位+排名变动+粉丝占比，无需登录）
4. 七路并集去重后进入全窗口遍历分析

**注意：** 浏览器读取依赖会话（X 需登录态），登录由用户在 IAB 完成；我仅验证页面可见状态与读取内容。

## 11. 公开访问（GitHub Pages，2026-08-15 启用）

**站点：** https://xrqaviva.github.io/market_news/（公开仓库 xrqaviva/market_news，用户已授权发布）

**机制：** `.github/workflows/pages.yml` —— push 到 main 时，Actions 把已提交的 `web/dist/`（本地每日自动化构建产物）上传到 GitHub Pages。CI 不重新构建（fusion 依赖 daily_info 晨报产出，仅本地可构建）。

**发布流程：** 每日自动化构建 dist → 提交 → `git push origin main` → Actions 自动部署（已验证：首页/融合页/报告页均 200）。

**注意：** 仓库为公开（全部代码/文档/历史公开）；报告内容本身为公开市场信息，无凭据。发布任何新内容前确认不含敏感信息。

## 12. 公共区域规则（用户裁定，2026-08-16 持久化）

**架构（2026-08-16 用户裁定重构）：唯一页面 = 报告页，每页都是融合页**
- **index.html 只是指针**：`<meta refresh>` 指向最新报告页（reports/<latest>.html），不承载任何 UI
- **每个报告页本身就是融合页**：顶部「外围/新闻」tab 切换两个 pane——外围 pane = daily_info 晨报内容（按报告日期取 daily_info runs，无则用最新晨报），新闻 pane = market_news 报告内容
- **左侧栏（公共）**：品牌「新闻速递」+ 日历日期筛选器（antd 式月历弹层，仅可选有报告的日期，选择跳转该日最后报告）+ 日期归档
- **顶栏（公共）**：标题（MMDD盘前/盘后新闻速递）+ 右上角「外围/新闻」切换按钮
- **不再有独立的 fusion.html**（旧融合页废弃）；融合逻辑在 web/build.py（_brief_pane）+ web/fusion.py（变换函数复用）+ 模板 report.html
- 标题统一：`MMDD盘前/盘后新闻速递`（0800=盘前，其余=盘后）

**改动纪律：** 唯一模板（web/templates/report.html）+ 唯一构建（web/build.py）——公共区域一次改到位，不存在第二套页面需要同步；浏览器验证（含 tab 切换、日历跳转、外围/新闻内容）后再交付。
