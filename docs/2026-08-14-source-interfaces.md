# 新闻雷达可用接口与来源清单（2026-08-14 沉淀）

**定位：** 本文件是数据采集接口的权威台账。每个接口标注：通道、URL 模式、可用字段、验证状态、限制与使用注意。新增/失效接口必须在此登记。采集规则见《全窗口遍历式发现方法》（docs/2026-08-13-full-window-discovery-method.md）。

## 1. 行情/数据 API

| 接口 | 通道 | URL 模式 | 可用字段 | 状态 | 限制与注意 |
|---|---|---|---|---|---|
| 新浪行情 API | curl/HTTP | `https://hq.sinajs.cn/list=sh000001,sz399001` | 指数/个股实时快照（开高低收、成交量额、时间） | ✅ 实测可用 | 必须带 `Referer: https://finance.sina.com.cn/`；返回 GBK 需转码；`sh`/`sz`/`hk` 前缀 |
| 财联社 API | HTTP | `https://api3.cls.cn/nodeapi/telegraphList?app=CailianpressWeb&os=web&sv=7.7.5&sign=...` | 电报 JSON | ⚠️ 存活但需签名 | 返回 `{"errno":50101,"msg":"小财正在加载中..."}`，sign 参数需客户端算法，未逆向，不采用 |
| 新浪 7×24 回放 API | curl/HTTP | `https://zhibo.sina.com.cn/api/zhibo/feed?page={n}&page_size=100&zhibo_id=152&tag_id=0&dire=f&dpc=1` | 全窗口快讯流：`create_time`（精确到秒）、`rich_text`、`ext.docurl`（**永久详情页直链**）、id | ✅ 2026-08-14 实测 | **主发现/核验通道**：page=1 最新、page 递增回看；`dire=f` 为向前翻页；2300条约23页；`ext` 为 **JSON 字符串需二次解析**；约 6% 条目无 docurl；详情页 `https://finance.sina.com.cn/7x24/YYYY-MM-DD/doc-xxx.shtml` 纯 HTML 可直接 curl；需 UA+Referer `https://finance.sina.com.cn/7x24/` |
| 东方财富推送 API | HTTP | `https://push2.eastmoney.com/...` | 行情推送 | 未实测 | 历史域名单中出现，未验证 |
| NewsNow 公共 JSON | HTTP | NewsNow 站内 JSON 接口 | 聚合榜位 | ❌ 历史失败 | 2026-07-29 起超时返回非 JSON，改走公共网页 |
| 巨潮资讯 cninfo | 浏览器 | `http://www.cninfo.com.cn/new/index` | 法定公告 | ✅ 浏览器可达 | 命令行 WebFetch 未验证 |

## 2. WebFetch 可用的文章/快讯源（无需浏览器）

| 来源 | URL 模式 | 可用内容 | 提取注意 |
|---|---|---|---|
| 新浪财经 7×24 | API 直链（见第1节） | 全窗口快讯（时间戳+docurl 永久链接） | 优先 API；详情页纯 HTML 可 curl |
| 新浪财经 7×24 网页 | `https://finance.sina.com.cn/7x24/` | 最近约25分钟快讯（标题+时间） | 只作发现与对账；回放必须走 API |
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
