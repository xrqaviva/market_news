import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_morning_site.sh"
PROJECT_DIR = "/Users/aviva/Projects/market_news"
SITE_REPO = "/Users/aviva/Projects/market-news-site"


class MorningSiteEntrypointTest(unittest.TestCase):
    def _run_entrypoint(self, mode=None, publisher_exit=0):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            log = base / "python3.log"
            stub = base / "python3"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >> \"$MORNING_SITE_LOG\"\n"
                "if [[ \"$2\" == \"web.publish\" ]]; then\n"
                "  exit \"$MORNING_SITE_PUBLISHER_EXIT\"\n"
                "fi\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            environment = os.environ.copy()
            environment["MORNING_SITE_LOG"] = str(log)
            environment["MORNING_SITE_PUBLISHER_EXIT"] = str(publisher_exit)
            environment["PATH"] = "{}{}{}".format(base, os.pathsep, environment["PATH"])
            if mode is None:
                environment.pop("SITE_PUBLISH_MODE", None)
            else:
                environment["SITE_PUBLISH_MODE"] = mode
            completed = subprocess.run(
                [str(SCRIPT)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            return completed, calls

    def test_default_mode_builds_then_runs_dry_run_publisher(self):
        completed, calls = self._run_entrypoint()

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            [
                "-m web.build --project-root {} --output web/dist".format(PROJECT_DIR),
                "-m web.publish --dist web/dist --site-repo {}".format(SITE_REPO),
            ],
            calls,
        )

    def test_apply_mode_builds_then_runs_complete_publisher(self):
        completed, calls = self._run_entrypoint(mode="apply")

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            [
                "-m web.build --project-root {} --output web/dist".format(PROJECT_DIR),
                "-m web.publish --dist web/dist --site-repo {} --apply --commit --push".format(SITE_REPO),
            ],
            calls,
        )

    def test_invalid_mode_fails_without_calling_python(self):
        completed, calls = self._run_entrypoint(mode="aply")

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("SITE_PUBLISH_MODE", completed.stderr)
        self.assertEqual([], calls)

    def test_missing_site_repo_publisher_failure_follows_successful_build(self):
        completed, calls = self._run_entrypoint(publisher_exit=23)

        self.assertEqual(23, completed.returncode)
        self.assertEqual(
            [
                "-m web.build --project-root {} --output web/dist".format(PROJECT_DIR),
                "-m web.publish --dist web/dist --site-repo {}".format(SITE_REPO),
            ],
            calls,
        )

    def test_entrypoint_has_no_raw_git_publication(self):
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("git commit", script)
        self.assertNotIn("git push", script)
