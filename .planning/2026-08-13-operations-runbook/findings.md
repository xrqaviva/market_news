# 操作手册盘点发现

## 权威边界

- 仓库已有确定性 `Markdown -> HTML` 构建器：`python3 -m web.build --project-root <root> --output <root>/web/dist`。
- 当前没有自动生成新闻 Markdown 的程序；MD 由采集、去重、热度评分、题材聚合和编辑流程生成。
- 生产解析器通过 `web/report_catalog.json` 读取旧命名报告，并自动发现 `YYYY-MM-DD-HHMM-*.md` 标准命名报告。
- 报告汇总和题材方法以 `docs/PROJECT_GUIDE.md` 与 `docs/2026-08-11-theme-aggregation-method-uat.md` 为参考，但操作命令必须以当前脚本为准。
- `scripts/run_morning_site.sh` 先构建 HTML，默认 `SITE_PUBLISH_MODE=dry-run`；只有显式 `apply` 才进入提交和 push 路径。
- 真实布局验收入口为 `node tests/report_layout_browser.mjs`；完整 Python 回归为 `python3 -m unittest discover -s tests -v`。

## 保留边界

- 主工作区已有 `docs/PROJECT_GUIDE.md`、一份历史设计文档与 `tests/test_project_guide.py` 未提交修改，本轮不改动。
