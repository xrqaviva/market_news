# Task 3 Fix Round 1 Plan

## Goal

Restore every approved Markdown-derived legacy news field and parsed score breakdown to deterministic HTML without changing the Task 1/2 shell, CSS, or JavaScript behavior.

## Authority and constraints

- Approved: `web/report_parser.py`, necessary `web/report_model.py`, `web/build.py`, `tests/test_web_parser.py`, `tests/test_web_build.py`, seven generated report HTML files, UAT, and the untracked Task 3 report.
- Do not touch production template/CSS/JS source unless separately authorized; current scope says preserve them.
- Preserve existing untracked `.superpowers/` and `task-5-report.md`; exclude planning files and all temporary artifacts from commits.
- Local fix commit is authorized after all gates and independent review. No push, merge, PR, deploy, publish, or automation.

## Design

- Extend `NewsItem` only if independent typed fields are necessary to preserve old labels without conflation.
- Map legacy `消息详情` to `core`.
- Preserve `时间`, `监控区间`, `传播路径`, and `尚未确认` as distinct compact detail fields, rendered in Markdown order with explicit labels.
- Render nonempty `score_breakdown` exactly once in the expanded/auxiliary detail area under label `热点构成`; omit it when empty.
- Strengthen window behavior to assert six known nonempty values exactly once, the seventh empty report has zero window nodes, and synthetic special characters escape correctly.
- Source-level audit starts from Markdown labels and proves expected source fields reach HTML; model-only audit is supplementary.

## Test matrix

- Parser unit RED/GREEN: actual 7/29 fixture has 35 nonempty summaries; all legacy compact detail fields remain independently available and ordered; non-news labels are excluded.
- Renderer/build RED/GREEN: 35/35 summaries and all new legacy detail fields appear; 85/85 nonempty breakdowns appear exactly once; empty breakdown omitted; special breakdown escaped.
- Window RED/GREEN: six nonempty exactly once; empty report zero; synthetic special value escaped.
- Generated artifacts: rebuild exactly seven tracked reports; checked/fresh byte equivalence; second build diff zero; source/dist asset equality.
- UI: real headless Chrome desktop/mobile/interactions/print/contrast/console after final generated change.
- Security/privacy: build/security tests, public-tree safety, staged secret/path scan.
- Final: full `unittest discover`, exact counts, independent read-only review, exact staged patch, authorized local commit.

## Phases

1. [complete] Discovery, baseline, Markdown label audit, root-cause trace.
2. [complete] Important 1 TDD: legacy summary and distinct detail fields.
3. [complete] Important 2 TDD: score breakdown rendering.
4. [complete] Minor TDD: window count/empty/escape hardening.
5. [complete] Rebuild, source-level audit, UAT/report update.
6. [complete] Fresh browser/artifact/security/full-suite verification.
7. [complete] Independent review, exact staging, and authorized local commit.

## Final fix wave

- [complete] Audit the 11 report-level explanation sections, seven top disclosures, merged source coverage, themed score breakdowns, and tracked feature-document paths.
- [complete] RED/GREEN: ordered typed report notes, safe compact rendering, exact placement before pending items.
- [complete] RED/GREEN: table-plus-inline source merge with stable URL deduplication and unsafe-scheme rejection.
- [complete] RED/GREEN: all 25 August 11 themed news instances retain and render score breakdowns.
- [complete] Rebuild seven reports; strengthen browser completeness, ordering, mobile, print, link-safety, and contrast gates.
- [complete] Deterministic/full/security/source audits, UAT/report, independent review, exact-stage, and commit.

## Errors

- Initial skill paths referenced 6.2.0 but installed files are at 6.3.0; located and read the current version before proceeding.
- First attempt to create `/private/tmp/task3_label_audit.py` was rejected by automatic approval review due a usage-limit message. Did not retry or work around the write; used a materially safer read-only `awk` audit instead.
- First label-audit command redirected to `/dev/stdout`, which the sandbox rejected. Removed the unnecessary redirection and reran successfully.
- First status test regex recognized ASCII `|` only, while source uses full-width `｜`; corrected the test fixture regex and reran to obtain the intended product RED.
- One multi-file patch had an incorrect context boundary and applied nothing; split it into correct file contexts before applying.
