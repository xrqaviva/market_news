# 2026-07-30 A股新闻雷达1500证据表

> 自动化ID：`a-15-00`（本轮仅手动测试；08:00、12:00、15:00三个定时任务均保持暂停）
> 交易日：2026-07-30；下一交易日：2026-07-31。
> 事件窗口：2026-07-30 00:00—15:00；实际重试开始：16:10:33；登录热度保存：16:15—16:20。
> 官方日历证据：[上交所2026年休市安排](https://www.sse.com.cn/disclosure/dealinstruc/closed/)。

## 执行规则

- 三个sub-agent并行：海外/跨资产、国内/公司与A股收盘、登录渠道热度；只有热度组操作登录Chrome。
- 15:00后只核验15:00前事件及保存下一交易日08:00基线，不倒灌新事件，不把16:xx值冒充15:00。
- 排名只使用覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10；深度、可靠性、行情和个股映射不入分。
- “激增”必须为同一永久链接、同一平台、同一字段双时点，且合计至少+50%、绝对增加至少50；换帖、换榜不计算百分比。
- 不读取密码、Cookie、Local Storage、浏览器历史或私人内容；不提供交易建议。

## 五项评分验算

| 排名 | 事件 | 覆盖 | 变化 | 绝对热度 | 新鲜度 | 频次 | 总分 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | FOMC维持利率、三票主张加息 | 25 | 30 | 20 | 11 | 10 | 96 |
| 2 | 美军打击伊朗与能源风险 | 25 | 28 | 18 | 14 | 9 | 94 |
| 3 | 全球存储/科技链承压 | 25 | 28 | 20 | 11 | 9 | 93 |
| 4 | MLCC调价与A股分化 | 25 | 24 | 19 | 10 | 10 | 88 |
| 5 | Meta财报 | 20 | 22 | 17 | 15 | 8 | 82 |
| 6 | 微软财报/Azure | 20 | 21 | 17 | 15 | 8 | 81 |
| 7 | 兆易创新回购/增持 | 20 | 22 | 15 | 13 | 9 | 79 |
| 8 | 三星Q2业绩与亚洲反馈 | 20 | 18 | 15 | 15 | 10 | 78 |
| 9 | Kimi融资报道 | 20 | 18 | 14 | 14 | 9 | 75 |
| 10 | 锂库存社区帖 | 15 | 26 | 15 | 9 | 8 | 73 |
| 11 | 韩国稳市/杠杆ETF | 20 | 15 | 13 | 13 | 9 | 70 |
| 12 | Lam Research财报 | 15 | 15 | 13 | 14 | 8 | 65 |
| 13 | 九部门科技金融数据通知 | 15 | 14 | 12 | 13 | 8 | 62 |
| 14 | 永鼎股份激光芯片订单 | 15 | 13 | 11 | 13 | 7 | 59 |
| 15 | 行云科技算力合同 | 15 | 12 | 11 | 13 | 7 | 58 |
| 16 | 恒瑞医药长效胰岛素获批 | 15 | 11 | 10 | 13 | 7 | 56 |
| 17 | 天智航重大资产重组 | 15 | 11 | 10 | 12 | 7 | 55 |
| 18 | 高通财报与指引 | 15 | 12 | 10 | 10 | 7 | 54 |

## 事件证据与判断边界

### EVT-01｜FOMC｜96

- 时间链：02:00官方决议 → 10:00精确微博快照 → 13:09亚洲跨资产稿 → 16:15实际保存。
- 来源：[FOMC声明](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm)；[AP亚洲市场](https://apnews.com/article/stock-markets-rates-korea-ai-oil-99b5702d93a2b5c6e513fb952ccdcc92)；[微博原帖](https://weibo.com/1216826604/Rb1cNzbJ4)。
- 热度：10:00的15/176/6988（7179）→16:15的15/179/7700（7894），+10.0%，未达激增；后点不计入15:00评分。
- 边界：FOMC偏鹰是市场解读；收益率、美元、油价与股市同时受地缘和财报影响。

### EVT-02｜美军打击伊朗/油价｜94

- 时间链：10:00打击完成 → 10:45 Axios → 13:08—13:09 AP。
- 来源：[CENTCOM](https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4559495/us-strikes-irgc-targets-after-attempted-iranian-attacks/)；[Axios](https://www.axios.com/2026/07/29/us-airstrikes-iran-trump-resume)；[AP地区稿](https://apnews.com/article/iran-war-us-hormuz-strait-july-30-2026-8dc77ed6a65f389ea4af84635d2473bd)；[AP市场稿](https://apnews.com/article/stock-markets-rates-korea-ai-oil-99b5702d93a2b5c6e513fb952ccdcc92)。
- 热度：微博同帖07:51的778→16:19的1100，+41.4%，未激增；后点只作次日基线。
- 边界：官方单方声明不能独立确认全部战果；亚洲时段油价小涨不能全归于打击。

### EVT-03｜全球存储/科技链｜93

- 时间链：05:42隔夜收盘稿 → 10:00 A股早盘反馈 → 15:00成长指数/半导体收盘弱势 → 16:19保存互动。
- 来源：[财联社隔夜稿](https://www.cls.cn/detail/2440737)；[A股指数接口](https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000688&fields=f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18)；[行业跌幅接口](https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=30&po=0&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f12,f14,f2,f3,f4,f62,f104,f105,f128,f136,f140,f141)；[微博原帖](https://weibo.com/2868676035/Rb1gAyAPd)。
- 热度：07:51的49→16:19的100，+104.1%、绝对+51，满足低基数保护；只能称07:51→16:19激增。
- 边界：市场回撤与FOMC、估值、财报、中国竞争等多因素同期，不能单因果。

### EVT-04｜MLCC｜88

- 来源：[财联社调价报道](https://www.cls.cn/detail/2440280)；[微博原帖](https://weibo.com/2868676035/RaWuDotab)；[代表股收盘](https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.603986,0.000636,0.300648,1.603602,0.301398,1.688277&fields=f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18)。
- 热度：微博07:51的313→16:19的337，+7.7%；原财联社单篇由10:00第1退出16:17可见前13，原条目降温。
- 反馈：15:00风华+6.29%、鸿远+6.68%，三环-3.30%、火炬-4.93%；行业整体约-6.73%。
- 边界：调价函原件未取得；调价意向不等于全品类实际成交。

### EVT-05｜Meta｜82

- 来源：[Meta官方业绩](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx)；[财联社盘前早报](https://www.cls.cn/detail/2440772)。
- 反馈：盘后约-8%，截至15:00无常规盘确认；16:17只在打包早报中可确认，无法归因单一条目。
- 边界：费用、法律事项、资本开支与指引共同影响盘后价格。

### EVT-06｜微软｜81

- 来源：[微软官方业绩](https://www.microsoft.com/en-us/Investor/earnings/FY-2026-Q4/press-release-webcast)；[财联社详情](https://www.cls.cn/detail/2440762)。
- 热度：同链接NewsNow 10:00第8→16:17第3，上升5位，未达上升10位的榜位激增阈值；后点只作次日基线。
- 边界：RPO不等于当期收入，盘后约+8%也不是常规收盘。

### EVT-07｜兆易创新｜79

- 来源：[财联社详情](https://www.cls.cn/detail/2440582)；[早报复核](https://www.cls.cn/detail/2440772)；[收盘接口](https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.603986&fields=f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18)。
- 纠错：回购 **10亿—20亿元**，拟增持 **不少于10亿元**；不是1亿—2亿元/1亿元。
- 反馈：15:00 +1.94%、成交约354.84亿元；半导体行业同期约-7.16%。
- 边界：提议不等于董事会通过或实际实施，正式公告PDF本轮未取得。

### EVT-08｜三星Q2｜78

- 来源：[三星IR](https://www.samsung.com/global/ir/)；[官方演示PDF](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_2Q_conference_eng.pdf)；[AP公司稿](https://apnews.com/article/samsung-ai-profit-memory-chips-10c2c548a392988862d8c7bd3f6fae05)；[AP市场稿](https://apnews.com/article/stock-markets-rates-korea-ai-oil-99b5702d93a2b5c6e513fb952ccdcc92)。
- 反馈：韩国14:30收盘KOSPI-1.2%、三星-0.7%、SK海力士-5.6%；日本设备/存储股分化上涨。
- 边界：主要数字与此前预告大体一致；业绩、去杠杆、供给与竞争因素并存。

### EVT-09｜Kimi融资｜75

- 来源：[最早检索样本](https://weibo.com/3880172960/RaVVF5niZ)；[财联社微博](https://weibo.com/2868676035/RaW2ZetkX)；[每日经济新闻](https://weibo.com/1649173367/RaYkkez5s)。
- 热度：盘前最后精确值67→16:17的71，+6.0%；因10:00未重读，严格10:00趋势未知。
- 边界：媒体知情人士口径不能证明交割到账或供应链订单。

### EVT-10｜锂库存社区帖｜73

- 来源：[雪球原帖](https://xueqiu.com/6238316110/402667020)。
- 热度：07-29晚280→07-30 07:49的430（跨夜激增）→10:00的437→16:16的501；严格10:00→16:16仅+14.6%，未激增。
- 边界：社区互动不替代库存、现货或期货原始数据。

## 11—18证据索引

- 韩国稳市/杠杆ETF：[财联社](https://www.cls.cn/detail/2440253)；[雪球](https://xueqiu.com/1213759028/402735276)。
- Lam Research：[官方业绩PDF](https://investor.lamresearch.com/image/Jun_Q_2026_Earnings_PR.pdf)；[电话会公告](https://newsroom.lamresearch.com/2026-07-08-Lam-Research-Corporation-Announces-June-Quarter-Financial-Conference-Call)。
- 九部门科技金融数据、永鼎、行云、恒瑞、天智航：[财联社盘前早报](https://www.cls.cn/detail/2440772)；其中官方政策全文/公司公告PDF未取得，均保留“原文待核”。
- 高通：[官方业绩PDF](https://s204.q4cdn.com/645488518/files/doc_financials/2026/q3/FY2026-3rd-Quarter-Earnings-Release.pdf)；[电话会安排](https://investor.qualcomm.com/news-events/press-releases/news-details/2026/Qualcomm-Schedules-Third-Quarter-Fiscal-2026-Earnings-Release-and-Conference-Call/default.aspx)。
- 行云科技纠错：30.53亿元算力合同主体为 **行云科技300209**，不是星云股份300648；[收盘快照](https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=0.300209&fields=f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18)。

## A股15:00收盘锚点

| 指标 | 收盘 | 涨跌幅 | 时间 |
|---|---:|---:|---|
| 上证指数 | 3804.6926 | -0.62% | 15:30接口盘后更新时间 |
| 深证成指 | 13285.801 | -2.73% | 15:00:03 |
| 创业板指 | 3244.618 | -3.97% | 15:00:03 |
| 北证50 | 1049.072 | -1.43% | 15:30接口盘后更新时间 |
| 科创50 | 1588.41 | -5.38% | 15:00收盘快照 |

来源：[新浪公开指数行情](https://hq.sinajs.cn/list=sh000001,sz399001,sz399006,bj899050)；[东方财富指数接口](https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000688&fields=f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18)。

## 登录渠道与失败

- 微博、雪球、NewsNow成功；所有当前读数均标16:xx实际时间。
- X具体样本页仍只显示“Loading timeline”，未取得正文或互动，不计趋势与覆盖。
- NewsNow只保存当前可见范围；“榜外”不等于消失，也不虚构具体名次。
- 原始分工证据：[海外组](2026-07-30-1500-overseas-agent.md)、[国内组](2026-07-30-1500-domestic-agent.md)、[热度组](2026-07-30-1500-heat-agent.md)。
