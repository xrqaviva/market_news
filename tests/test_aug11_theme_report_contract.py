import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/2026-08-11-0800-premarket-news-ranking.md"
WORKTREE_REPORT = (
    ROOT
    / ".worktrees/news-radar-web/reports/2026-08-11-0800-premarket-news-ranking.md"
)

EXPECTED_RANKED_NEWS = (
    (1, "霍尔木兹重开条件继续发酵，布油收涨5%", 96),
    (2, "宇树科技网上发行中签率为0.0181%", 94),
    (3, "苹果新品爆料两词条进入微博热榜前20", 92),
    (4, "央行发布“十五五”改革发展规划并配套9份行动方案", 90),
    (5, "江波龙半年净利同比71528.66%，经营现金流净额为-31.51亿元", 89),
    (6, "英伟达联合六家机构拟动员超过5000亿美元AI基础设施资本", 89),
    (7, "特朗普要求伊朗赔偿美国死伤者及伊朗抗议者家庭", 88),
    (8, "甘李药业授权博凡格鲁肽欧洲39国商业化权益", 88),
    (9, "9月加息隐含概率回升至约52%，10年美债收益率升至4.70%", 87),
    (10, "Archer拟收购波音三项业务，波音将入股合作", 86),
    (11, "豆包回应推荐酒店抽取12%佣金争议", 86),
    (12, "煤炭工业“十五五”规划量化智能化目标", 85),
    (13, "Intel拟发行150亿美元普通股", 83),
    (14, "阿里云称大型AIDC交付周期压至100天", 82),
    (15, "Archer发布航空AI基础模型ZEE", 80),
    (16, "Teledyne拟现金收购Varex Imaging", 80),
    (17, "25Ah金属锂一次电池实现超过750Wh/kg低倍率能量密度", 79),
    (18, "爱丽家居连续11个交易日涨停后停牌核查", 78),
    (19, "伯克希尔Q2三年来首次净买入股票的讨论再上热榜", 78),
    (20, "芯联集成半年营收45.62亿元、净利2.78亿元扭亏", 77),
    (21, "兆驰股份等多家公司集中披露回购计划", 76),
    (22, "MarineMax获约15亿美元现金收购", 72),
    (23, "日本央行发布7月会议意见摘要", 70),
    (24, "建设机械拟收购蒲城清洁能源100%股权并停牌", 68),
    (25, "天津提出到2028年智能机器人核心产业产值突破200亿元", 67),
)

EXPECTED_THEMES = (
    ("theme-ai-compute-memory", "AI算力 / 半导体 / 存储芯片", (5, 6, 13, 14, 20), 420),
    ("theme-ma", "并购重组", (10, 16, 22, 24), 306),
    ("theme-middle-east-oil", "中东局势 / 油气", (1, 7), 184),
    ("theme-low-altitude-aviation-ai", "低空经济 / 航空AI", (10, 15), 166),
    ("theme-a-share-buyback-capital", "A股回购 / 资本运作", (5, 21), 165),
    ("theme-humanoid-embodied-ai", "人形机器人 / 具身智能", (2, 25), 161),
)

EXPECTED_SOURCE_ROWS = {
    1: (("AP中东更新", "08-10 18:48", "https://apnews.com/article/iran-us-strait-hormuz-august-10-2026-0bdaae8f1d7b781918e76dca4317c897"), ("X固定帖", "08-09 00:24→08-11 08:28", "https://x.com/HormuzReport/status/2086126445051687039"), ("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308")),
    2: (("财经媒体", "08-10 20:00", "https://www.cls.cn/detail/2450388"), ("微博固定帖", "08-09 07:50→08-11 08:27", "https://weibo.com/1896820725/Rcy5YaEEe"), ("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678")),
    3: (("微博热榜", "08-11 08:19", "https://hotflashnews.com/platform/weibo"), ("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308")),
    4: (("中国人民银行", "08-10 18:20:36", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026081018132329141/index.html"), ("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678")),
    5: (("财经媒体详稿", "08-10 20:34", "https://www.cls.cn/detail/2450426"), ("半年现金流量表", "08-10，分钟未取得", "https://money.finance.sina.com.cn/corp/go.php/vFD_CashFlow/stockid/301308/ctrl/2026/displaytype/4.phtml"), ("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678")),
    6: (("Axios", "08-11 04:48:55", "https://www.axios.com/2026/08/10/nvidia-financing-ai-goldman-sachs-blackrock"), ("NVIDIA Newsroom", "08-11，精确分钟随官网", "https://nvidianews.nvidia.com/news/nvidia-partners-with-apollo-blackrock-blackstone-brookfield-goldman-sachs-and-kkr-to-establish-ai-compute-infrastructure-financing-platforms-to-mobilize-over-500-billion-of-third-party-capital")),
    7: (("AP", "08-10 18:48:53", "https://apnews.com/article/iran-us-strait-hormuz-august-10-2026-0bdaae8f1d7b781918e76dca4317c897"), ("微博热榜", "08-11 08:19", "https://hotflashnews.com/platform/weibo")),
    8: (("财经媒体详稿", "08-10 22:33", "https://www.cls.cn/detail/2450535"), ("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678")),
    9: (("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308"),),
    10: (("Archer IR", "08-11 05:00", "https://investors.archer.com/news/news-details/2026/Archer-Announces-Second-Quarter-2026-Results-Announces-Deal-with-Boeing-to-Shape-Physical-AI-Future-of-Aerospace-and-Defense/"),),
    11: (("百度实时榜", "08-11 08:01:31", "https://hotflashnews.com/platform/baidu"), ("百度日归档", "08-11，动态记录", "https://hotflashnews.com/archive/2026-08-11")),
    12: (("国家发改委", "08-10，分钟未取得", "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202608/t20260810_1406952.html"), ("国家发改委", "08-10，分钟未取得", "https://www.ndrc.gov.cn/xxgk/jd/jd/202608/t20260810_1406951.html"), ("财联社产业稿", "08-11 07:49", "https://www.cls.cn/detail/2450690")),
    13: (("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308"),),
    14: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"), ("财联社港股早报", "08-11 07:09", "https://www.cls.cn/detail/2450674")),
    15: (("Archer IR", "08-11 05:00", "https://investors.archer.com/news/news-details/2026/Archer-Announces-Second-Quarter-2026-Results-Announces-Deal-with-Boeing-to-Shape-Physical-AI-Future-of-Aerospace-and-Defense/"),),
    16: (("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308"),),
    17: (("科技日报转述/财联社", "08-10，分钟未取得→08-11 07:41", "https://www.cls.cn/detail/2450694"),),
    18: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"), ("上交所停复牌信息", "08-11盘前", "https://www.sse.com.cn/disclosure/dealinstruc/suspension/")),
    19: (("AP原始事件", "08-08 21:29", "https://apnews.com/article/e36ed92787eef9c9c67502501b345174"), ("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308"), ("知乎热榜", "08-11 08:19", "https://hotflashnews.com/platform/zhihu")),
    20: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"),),
    21: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"),),
    22: (("AP市场", "08-11 04:00", "https://apnews.com/article/stocks-markets-rates-iran-ai-adb7b918b15206e38d7899d482422308"),),
    23: (("日本央行", "08-10 07:50", "https://www.boj.or.jp/en/about/calendar/index.htm"), ("日本央行", "08-10 07:50", "https://www.boj.or.jp/en/mopo/mpmsche_minu/")),
    24: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"),),
    25: (("财联社早报", "08-11 07:00", "https://www.cls.cn/detail/2450678"),),
}

EXPECTED_DIRECT_MAPPINGS = {
    "theme-ai-compute-memory": (("江波龙", "301308"), ("芯联集成", "688469")),
    "theme-ma": (("建设机械", "600984"),),
    "theme-a-share-buyback-capital": (("江波龙", "301308"), ("兆驰股份", "002429"), ("国联民生", "601456"), ("永茂泰", "605208"), ("威迈斯", "688612")),
}

EXPECTED_SECTOR_REPRESENTATIVES = {
    "theme-ai-compute-memory": (("浪潮信息", "000977"), ("中科曙光", "603019"), ("海光信息", "688041"), ("中际旭创", "300308"), ("天孚通信", "300394"), ("北方华创", "002371"), ("中微公司", "688012"), ("兆易创新", "603986"), ("佰维存储", "688525")),
    "theme-middle-east-oil": (("中国石油", "601857"), ("中国海油", "600938"), ("中远海能", "600026")),
    "theme-low-altitude-aviation-ai": (("万丰奥威", "002085"), ("中信海直", "000099"), ("宗申动力", "001696")),
    "theme-humanoid-embodied-ai": (("绿的谐波", "688017"), ("双环传动", "002472"), ("鸣志电器", "603728"), ("柯力传感", "603662"), ("埃斯顿", "002747"), ("拓普集团", "601689")),
}


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not match:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


def _field(block: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}：\*\*\s*(.*)$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _news_blocks(text: str):
    headings = list(re.finditer(
        r"^#### 新闻：(\d+)｜(evt-\d{8}-\d{3})｜(.+?)｜(\d+)/100\s*$",
        text,
        re.MULTILINE,
    ))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end():end]
        sources = []
        for line in block.splitlines():
            if not line.startswith("|"):
                continue
            columns = [column.strip() for column in line.strip().strip("|").split("|")]
            if len(columns) < 3 or columns[0] == "传播渠道" or set("".join(columns)) <= {"-", ":"}:
                continue
            for url in re.findall(r"\[[^]]+]\((https?://[^)]+)\)", "|".join(columns[2:])):
                sources.append((columns[0], columns[1], url))
        yield {
            "rank": int(heading.group(1)),
            "event_id": heading.group(2),
            "title": heading.group(3),
            "score": int(heading.group(4)),
            "block": block.strip(),
            "core": _field(block, "核心信息"),
            "session": _field(block, "发布时段"),
            "theme_ids": tuple(filter(None, re.split(r"[、，,]", re.sub(r"（.*", "", _field(block, "关联题材"))))),
            "sources": tuple(sources),
        }


def _mappings(block: str, label: str):
    match = re.search(
        rf"^\*\*{re.escape(label)}：\*\*\s*$\n(.*?)(?=^\*\*[^\n]+：\*\*|^#### 新闻:|\Z)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ()
    return tuple(
        (name.strip(), ticker, evidence.strip())
        for name, ticker, evidence in re.findall(
            r"^-\s+(.+?)（(\d{6})）：\s*(.+)$", match.group(1), re.MULTILINE
        )
    )


def _parse_report(text: str):
    index_rows = []
    try:
        index_section = _section(text, "单条新闻热榜索引")
        themed = _section(text, "题材主线")
        other_section = _section(text, "其他重要新闻")
    except AssertionError:
        return (), (), ()
    for line in index_section.splitlines():
        match = re.match(
            r"^\|\s*(\d+)\s*\|\s*(evt-\d{8}-\d{3})\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|",
            line,
        )
        if match:
            index_rows.append((int(match.group(1)), match.group(2), match.group(3), int(match.group(4)), match.group(5)))

    themes = []
    headings = list(re.finditer(
        r"^### 主线\d+：(.+?)｜(\d+)分｜关联新闻(\d+)条\s*$", themed, re.MULTILINE
    ))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(themed)
        block = themed[heading.end():end]
        themes.append({
            "name": heading.group(1),
            "total": int(heading.group(2)),
            "declared_count": int(heading.group(3)),
            "theme_id": _field(block, "题材ID"),
            "catalyst": _field(block, "核心催化"),
            "risk": _field(block, "题材风险边界"),
            "direct": _mappings(block, "直接映射"),
            "representatives": _mappings(block, "板块代表"),
            "items": tuple(_news_blocks(block)),
        })
    return index_rows, themes, tuple(_news_blocks(other_section))


class Aug11ThemeReportContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")
        cls.index, cls.themes, cls.other = _parse_report(cls.text)

    def test_has_exactly_25_unique_ranked_events_with_unchanged_titles_and_scores(self) -> None:
        actual = tuple((rank, title, score) for rank, _event_id, title, score, _themes in self.index)
        self.assertEqual(EXPECTED_RANKED_NEWS, actual)
        self.assertEqual(
            tuple(f"evt-20260811-{rank:03d}" for rank in range(1, 26)),
            tuple(event_id for _rank, event_id, _title, _score, _themes in self.index),
        )

    def test_six_themes_have_exact_memberships_totals_and_cross_theme_contributions(self) -> None:
        actual = tuple(
            (theme["theme_id"], theme["name"], tuple(item["rank"] for item in theme["items"]), theme["total"])
            for theme in self.themes
        )
        self.assertEqual(EXPECTED_THEMES, actual)
        for theme in self.themes:
            self.assertEqual(theme["declared_count"], len(theme["items"]))
            self.assertEqual(theme["total"], sum(item["score"] for item in theme["items"]))
            self.assertTrue(theme["catalyst"])
            self.assertTrue(theme["risk"])
        contributions = {
            item["event_id"]: item["score"]
            for theme in self.themes
            for item in theme["items"]
            if item["rank"] in (5, 10)
        }
        self.assertEqual({"evt-20260811-005": 89, "evt-20260811-010": 86}, contributions)

    def test_every_complete_news_card_preserves_sources_details_and_session_semantics(self) -> None:
        copies = {}
        for item in (member for theme in self.themes for member in theme["items"]):
            copies.setdefault(item["rank"], []).append(item)
        for item in self.other:
            copies.setdefault(item["rank"], []).append(item)
        self.assertEqual(set(range(1, 26)), set(copies))
        for rank, expected_sources in EXPECTED_SOURCE_ROWS.items():
            with self.subTest(rank=rank):
                item = copies[rank][0]
                self.assertTrue(item["core"])
                self.assertRegex(item["session"], r"市场(?:盘前|盘中|盘后|收盘)")
                self.assertEqual(expected_sources, item["sources"])
                score_line = re.search(r"^\*\*热点权重：(\d+)/100\*\*（(.+)）$", item["block"], re.MULTILINE)
                self.assertIsNotNone(score_line)
                self.assertEqual(item["score"], int(score_line.group(1)))
                self.assertEqual(item["score"], sum(map(int, re.findall(r"\d+", score_line.group(2)))))
        for rank in (1, 2, 3, 6, 7, 11):
            self.assertTrue(_field(copies[rank][0]["block"], "热度变化"))
        for rank in (1, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20, 22, 23):
            self.assertTrue(_field(copies[rank][0]["block"], "带时间市场反馈"))
        self.assertIn("题材分不能再次相加", self.text)

    def test_cross_theme_rank_5_and_10_copies_are_byte_identical(self) -> None:
        for rank in (5, 10):
            copies = [item for theme in self.themes for item in theme["items"] if item["rank"] == rank]
            self.assertEqual(2, len(copies))
            self.assertEqual(copies[0], copies[1])

    def test_all_other_qualified_news_occur_exactly_once(self) -> None:
        self.assertEqual((3, 4, 8, 9, 11, 12, 17, 18, 19, 23), tuple(item["rank"] for item in self.other))
        themed_ranks = {item["rank"] for theme in self.themes for item in theme["items"]}
        self.assertFalse(themed_ranks.intersection(item["rank"] for item in self.other))

    def test_pending_appendix_has_exactly_four_unscored_items(self) -> None:
        pending = _section(self.text, "待核验线索（不参与主榜计分）")
        self.assertEqual(
            ("韩国半导体投资覆盖材料、零部件与设备", "马斯克与自由电子激光EUV光源", "英伟达拟向Lancium投资最高30亿美元", "天津机器人会议"),
            tuple(re.findall(r"^### (.+)$", pending, re.MULTILINE)),
        )
        self.assertNotRegex(pending, r"热点权重|/100")
        self.assertEqual(4, len(re.findall(r"^[-*] \*\*待核原因：\*\*", pending, re.MULTILINE)))

    def test_a_share_mappings_are_conservative_and_do_not_inherit_scores(self) -> None:
        by_id = {theme["theme_id"]: theme for theme in self.themes}
        self.assertEqual(
            set(EXPECTED_DIRECT_MAPPINGS) | set(EXPECTED_SECTOR_REPRESENTATIVES),
            set(by_id) & (set(EXPECTED_DIRECT_MAPPINGS) | set(EXPECTED_SECTOR_REPRESENTATIVES)),
        )
        actual_direct = {
            theme_id: tuple((name, ticker) for name, ticker, _evidence in by_id[theme_id]["direct"])
            for theme_id in EXPECTED_DIRECT_MAPPINGS
        }
        actual_representatives = {
            theme_id: tuple((name, ticker) for name, ticker, _evidence in by_id[theme_id]["representatives"])
            for theme_id in EXPECTED_SECTOR_REPRESENTATIVES
        }
        self.assertEqual(EXPECTED_DIRECT_MAPPINGS, actual_direct)
        self.assertEqual(EXPECTED_SECTOR_REPRESENTATIVES, actual_representatives)
        for theme in self.themes:
            for _name, _ticker, evidence in theme["direct"] + theme["representatives"]:
                self.assertTrue(evidence)
        for theme_id in EXPECTED_SECTOR_REPRESENTATIVES:
            for _name, _ticker, evidence in by_id[theme_id]["representatives"]:
                self.assertIn("本轮新闻未确认新增订单或直接受益", evidence)
        self.assertIn("板块代表不继承新闻或题材分数，也不构成投资建议", self.text)
        self.assertIn("AmazingData认证不可用", self.text)

    def test_root_and_worktree_reports_are_byte_identical(self) -> None:
        self.assertEqual(REPORT.read_bytes(), WORKTREE_REPORT.read_bytes())


if __name__ == "__main__":
    unittest.main()
