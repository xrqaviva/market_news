# Findings — Task 3 Fix Round 1

- Parent review reports 35/35 July 29 summaries empty and 85/85 parsed nonempty score breakdowns unrendered.
- Current branch HEAD before the fix round is `85b4834`.
- Existing tracked tree is clean; only private/unrelated untracked `.superpowers/` and `task-5-report.md` are present before planning files.
- Pre-change full baseline: 87 run / 87 passed / 0 failed / 0 errors / 0 skipped.
- Root cause: `_make_top_item` only mapped `核心信息` and newer labels. July 29 uses `消息详情` plus labeled bullet fields; July 30 uses `市场反馈` and `后续关键变量` aliases. `score_breakdown` was already modeled but absent from `_news_item` rendering.
- Source label audit inside news blocks found the legacy field families plus 55 `状态` values. `核验路径` was already preserved as source links; inline `即时市场定价为…` remains visible within rendered feedback. Bold numeric emphasis such as `10亿—20亿元` is content, not a field label.
- Pre-fix model counts: 169 items, 316 sources, 134 nonempty core, 85 score breakdown, 74 signal, 54 feedback, 74 boundary, 30 variables, 89 heat change, 24 release session.
- Intended post-fix counts: 169 core, 316 sources unchanged, 85 breakdown, 74 signal, 74 feedback, 74 boundary, 50 variables, 89 heat change, 24 release session; 35 July 29 items each retain ten labeled supplemental fields including status.
- Final review found 11 non-news H2 explanation sections excluded from the model, seven top disclosure blocks only partially represented as metadata, table sources suppressing unique inline links, and 25 themed news instances with hard-coded empty score breakdowns.
- Explanation-section titles are: 渠道状态与本轮增量, 完整性边界, 覆盖边界, 7月31日08:00比较基线, 覆盖与安全边界, 来源覆盖与限制 (three reports), 盘前待补节点, 08:00正式版待补节点, 来源覆盖与核验缺口.
- The fixed template already orders `THEME_CONTENT`, `NEWS_ITEMS`, then `PENDING_ITEMS`; report notes can be composed into the final replacement without changing the template.
- TDD evidence: Important 1 failed with 35 core = 0 and 20 legacy feedback = 0, then focused 4/4 green. Important 2 failed both actual-85 and synthetic escape/empty tests, then 2/2 green. Window component contract failed six actual subtests plus synthetic escape, then 2/2 green. Status/model-regression tests failed for 55 absent statuses and heat count 54 vs 89, then green.
