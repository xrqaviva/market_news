# Task 5 report — deterministic HTML build

## Scope and decision record

- Intent: regenerate the public `web/dist/` site from the existing build entry point and lock the Aug. 11 themed-report artifact contract.
- Approved task brief: `.superpowers/sdd/2026-08-11-theme-aggregation/task-5-brief.md`; it explicitly assigns `tests/test_web_build.py`, generated `web/dist/**`, and a local-only commit.
- In scope: generated artifact test, deterministic rebuild, output safety/release checks. Out of scope: parser, build, templates, assets, and report source edits. No push, deploy, publish, or destructive cleanup.
- Test change: `test_checked_in_aug11_artifact_keeps_themed_news_contract` fails if a checked-in Aug. 11 output loses its six ordered theme totals, 25 unique indexed/DOM events, unique cross-theme instances, the selected exact source links, four unscored pending items, or latest archive/manifest navigation. The expected values are literals taken from the approved report contract, not computed by the renderer.

## RED → GREEN

- RED: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_build.WebBuildTest.test_checked_in_aug11_artifact_keeps_themed_news_contract -v`
  failed as expected: old `web/dist/reports/2026-08-11-0800.html` rendered no `theme-group` sections.
- Generation: `PYTHONDONTWRITEBYTECODE=1 python3 -m web.build --project-root . --output web/dist`
  built 7 reports / 170 items / 11 output files. No generated file was hand edited.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_build -v` — 26 passed.

## Fresh verification

- Full: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` — 77 passed, 0 failed/errors, after the final build.
- `node --check web/assets/app.js` — passed.
- `git diff --check` — passed.
- `assert_public_tree_safe(Path("web/dist"))` — passed.
- Determinism: a second identical build produced the same 11-file tree digest both times:
  `76778e73b8bfb149397c52d2068f708337a65536946baadececa38000fdf5855`.
- Privacy/security scan over `web/dist` for absolute local paths, `file:`, API keys, secrets, cookies, browser state, authorization/bearer/session/password text returned no matches.
- Local browser exercise: generated Aug. 11 page loaded with 6 theme groups; clicking the unique `产业` filter set `aria-pressed=true`, left 8 visible rows, and recorded no console errors.

## Artifact/history review and concern

- 07-31, 08-03, and 08-10 historical report content is unchanged after normalizing the expected shared archive insertion, shared instance-id attributes, and template whitespace.
- 07-29, 07-30 08:00, and 07-30 15:00 additionally refresh three headline strings from their currently committed Markdown sources (for example the MLCC and lithium-inventory headings). These are not shared-template/assets-only changes; `bc16916` introduced the current source reports while HEAD's generated output still had older headings. This has been raised to the task owner for disposition and is not silently waived here.
- Untracked source reports `reports/2026-08-03-0800-premarket-news-ranking.md` and `reports/2026-08-10-0800-premarket-news-ranking.md` were pre-existing user work and are excluded. This report is intentionally uncommitted.

### Disposition

- User explicitly approved the three 2026-07-29/30 historical title synchronizations. Markdown is the sole source of truth, so the complete generator rebuild is authorized to update the stale HTML copies. The prior concern is resolved.

## Git

- Commit `4013de5` (`test: lock generated themed report output`) contains only `tests/test_web_build.py` and `web/dist/**`. No push/deploy/publish has occurred.
