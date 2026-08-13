# Findings & Decisions

## Requirements
- Gate on a reliable A-share trading calendar; skip entirely if closed.
- Window is 2026-07-29 00:00 through the actual report cutoff, Asia/Shanghai; highlight 08:00—12:00 heat and new information.
- Heat changes and old-news re-heating participate in the same ranking; rank only by coverage 25 + change 30 + absolute heat 20 + freshness 15 + frequency 10.
- Top 10 require expectation delta/key signal, timestamped market feedback, judgment boundary, and next variables; ranks 11+ stay compact.
- Every concrete source must be directly clickable; no homepage substitutions for item-level evidence.
- At most three sub-agents; only one may control logged-in Chrome; never access passwords, cookies, local storage, or browser history.
- Create new date+1200 report/evidence files; do not overwrite historical reports; no trading advice.

## Research Findings
- Official SSE 2026 holiday schedule does not list July 30 as a closure; 2026-07-30 is a Thursday.
- Sina index endpoint returned dated A-share snapshots on 2026-07-30 at 11:34—11:35 for Shanghai, Shenzhen, and Beijing indices, confirming a live trading session.
- Previous trading day is 2026-07-29; V6 evidence at 10:00 provides item-level morning baseline and comparable heat snapshots for several candidates.
- Actual orchestration began after 12:54 because this automation invocation arrived late. The report must disclose the delay; 08:00—12:00 comparisons must exclude later evidence.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Preserve noon focus window separately from actual completion time | Prevents post-noon data from being presented as if observed by 12:00 |
| Use V6 exact-field snapshots as comparison baseline | Heat labels require same-platform, same-field comparability |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| AmazingData helper module unavailable | Use official exchange calendar plus dated live quotes; record the runtime limitation |
| Automation triggered after noon | Keep 1200 identity, disclose actual run times, and limit the focal comparison to 08:00—12:00 |

## Resources
- https://www.sse.com.cn/disclosure/dealinstruc/closed/
- https://hq.sinajs.cn/list=sh000001,sz399001,bj899050
- /Users/aviva/Projects/market_news/evidence/2026-07-30-premarket-depth-v6-snapshots.md
