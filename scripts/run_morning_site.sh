#!/usr/bin/env bash
set -euo pipefail

project_dir="/Users/aviva/Projects/market_news"
site_repo="/Users/aviva/Projects/market-news-site"
publish_mode="${SITE_PUBLISH_MODE:-dry-run}"

case "$publish_mode" in
  dry-run|apply)
    ;;
  *)
    printf 'invalid SITE_PUBLISH_MODE: %s (expected dry-run or apply)\n' "$publish_mode" >&2
    exit 2
    ;;
esac

cd "$project_dir"
python3 -m web.build --project-root "$project_dir" --output web/dist

if [[ "$publish_mode" == "apply" ]]; then
  python3 -m web.publish --dist web/dist --site-repo "$site_repo" --apply --commit --push
else
  python3 -m web.publish --dist web/dist --site-repo "$site_repo"
fi
