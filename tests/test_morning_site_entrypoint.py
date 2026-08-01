from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MorningSiteEntrypointTest(unittest.TestCase):
    def test_entrypoint_builds_before_optional_publish(self):
        script = (ROOT / "scripts/run_morning_site.sh").read_text(encoding="utf-8")
        build_at = script.index("python3 -m web.build")
        publish_at = script.index("python3 -m web.publish")
        self.assertLess(build_at, publish_at)
        self.assertIn('SITE_PUBLISH_MODE:-dry-run', script)
        self.assertIn("--apply --commit --push", script)
        self.assertNotIn("git push", script)
