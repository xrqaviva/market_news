import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from web.publish import PublishBoundaryError, publish_site, sync_dist


ROOT = Path(__file__).resolve().parents[1]


class WebPublishTest(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def _init_repo(self, repo: Path, branch: str = "main") -> None:
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", branch, str(repo)],
            check=True,
            capture_output=True,
            text=True,
        )
        self._git(repo, "config", "user.name", "Publisher Test")
        self._git(repo, "config", "user.email", "publisher@example.invalid")

    def _write_publishable_dist(self, dist: Path, marker: str = "safe") -> None:
        dist.mkdir()
        (dist / "reports").mkdir()
        (dist / "index.html").write_text(marker, encoding="utf-8")
        (dist / "reports" / "2026-07-31-0800.html").write_text(marker, encoding="utf-8")
        (dist / "reports.json").write_text(
            json.dumps(
                {
                    "reports": [
                        {
                            "date": "2026-07-31",
                            "slot": "0800",
                            "url": "reports/2026-07-31-0800.html",
                        }
                    ],
                    "latest": "reports/2026-07-31-0800.html",
                }
            ),
            encoding="utf-8",
        )

    def test_dry_run_does_not_modify_site_repo(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            self._init_repo(repo)

            result = sync_dist(dist, repo, dry_run=True)

            self.assertEqual(["index.html"], result.changed_paths)
            self.assertFalse(result.applied)
            self.assertFalse((repo / "index.html").exists())

    def test_rejects_wrong_repository_directory_name(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "wrong-name"
            dist.mkdir()
            repo.mkdir()

            with self.assertRaises(PublishBoundaryError):
                sync_dist(dist, repo, dry_run=False)

    def test_rejects_symlinked_repository_and_wrong_origin_without_leaking_url(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            real_repo = base / "real-site"
            self._init_repo(real_repo)
            linked_repo = base / "market-news-site"
            linked_repo.symlink_to(real_repo, target_is_directory=True)

            with self.assertRaises(PublishBoundaryError):
                sync_dist(dist, linked_repo)

            linked_repo.unlink()
            repo = base / "market-news-site"
            self._init_repo(repo)
            secret_url = "https://token@example.invalid/wrong-site.git"
            self._git(repo, "remote", "add", "origin", secret_url)

            with self.assertRaises(PublishBoundaryError) as raised:
                sync_dist(dist, repo)
            self.assertNotIn("token", str(raised.exception))
            self.assertNotIn(secret_url, str(raised.exception))

    def test_rejects_nonempty_untracked_file_before_apply(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir()
            (dist / "index.html").write_text("new", encoding="utf-8")
            self._init_repo(repo)
            (repo / "notes.txt").write_text("keep me", encoding="utf-8")

            with self.assertRaises(PublishBoundaryError):
                sync_dist(dist, repo, dry_run=False)

            self.assertEqual("keep me", (repo / "notes.txt").read_text(encoding="utf-8"))
            self.assertFalse((repo / "index.html").exists())

    def test_apply_copies_exact_dist_tree_and_removes_stale_tracked_assets(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir()
            (dist / "index.html").write_text("new", encoding="utf-8")
            self._init_repo(repo)
            (repo / "index.html").write_text("old", encoding="utf-8")
            (repo / "stale.html").write_text("stale", encoding="utf-8")
            self._git(repo, "add", "index.html", "stale.html")
            self._git(repo, "commit", "-m", "seed")

            result = sync_dist(dist, repo, dry_run=False)

            self.assertEqual(["index.html", "stale.html"], result.changed_paths)
            self.assertTrue(result.applied)
            self.assertEqual("new", (repo / "index.html").read_text(encoding="utf-8"))
            self.assertFalse((repo / "stale.html").exists())
            self.assertEqual(["index.html", "stale.html"], sorted(
                line[3:] for line in self._git(repo, "status", "--porcelain").stdout.splitlines()
            ))

    def test_commit_and_push_require_ordered_apply_flags(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            self._init_repo(repo)

            with self.assertRaises(PublishBoundaryError):
                publish_site(dist, repo, commit=True)
            with self.assertRaises(PublishBoundaryError):
                publish_site(dist, repo, push=True)
            with self.assertRaises(PublishBoundaryError):
                publish_site(dist, repo, apply=True, push=True)

            self.assertFalse((repo / "index.html").exists())

    def test_apply_commit_and_push_to_local_bare_remote(self):
        """The only push exercised by tests targets a temporary local bare remote."""
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            remote = base / "market-news-site.git"
            self._write_publishable_dist(dist)
            self._init_repo(repo)
            subprocess.run(
                ["git", "init", "--bare", str(remote)],
                check=True,
                capture_output=True,
                text=True,
            )
            self._git(repo, "remote", "add", "origin", str(remote))

            result = publish_site(dist, repo, apply=True, commit=True, push=True)

            self.assertTrue(result.applied)
            self.assertTrue(result.pushed)
            self.assertEqual(40, len(result.commit_sha))
            self.assertEqual("", self._git(repo, "status", "--porcelain").stdout)
            self.assertEqual(
                "publish: 2026-07-31 0800 news radar",
                self._git(repo, "log", "-1", "--format=%s").stdout.strip(),
            )
            remote_sha = subprocess.run(
                ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(result.commit_sha, remote_sha)

    def test_cli_defaults_to_dry_run(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            self._init_repo(repo)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "web.publish",
                    "--dist",
                    str(dist),
                    "--site-repo",
                    str(repo),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn('"applied": false', completed.stdout)
            self.assertIn('"changed_paths": [', completed.stdout)
            self.assertFalse((repo / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
