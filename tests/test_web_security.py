from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.security import PublicTreeUnsafe, assert_public_tree_safe, scan_public_tree


class WebSecurityTest(unittest.TestCase):
    def test_rejects_private_names_and_absolute_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("/Users/aviva/Projects/market_news", encoding="utf-8")
            findings = scan_public_tree(root)
            self.assertTrue(any(item.rule == "absolute-local-path" for item in findings))
            with self.assertRaises(PublicTreeUnsafe):
                assert_public_tree_safe(root)

    def test_accepts_public_report_and_https_links(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<a href="https://apnews.com/article/example">AP</a>', encoding="utf-8"
            )
            self.assertEqual([], scan_public_tree(root))

    def test_rejects_private_file_names_and_symlinks(self):
        private_names = (
            "evidence.txt", "findings.md", "progress.md", "task_plan.md", "HANDOFF.md",
            ".env", ".git", ".superpowers", ".planning",
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in private_names:
                (root / name).write_text("public-looking content", encoding="utf-8")
            target = root / "safe.txt"
            target.write_text("safe", encoding="utf-8")
            (root / "linked.txt").symlink_to(target)

            rules = {finding.rule for finding in scan_public_tree(root)}

            self.assertIn("private-file-name", rules)
            self.assertIn("symlink", rules)

    def test_rejects_secret_tokens_and_unsafe_url_schemes_without_echoing_them(self):
        tokens = (
            "/Users/aviva/private", "file:///private/secret", "BEGIN OPENSSH PRIVATE KEY",
            "ghp_0123456789", "github_pat_0123456789", "Authorization: Bearer token",
            "Cookie: session=secret", "Local Storage", "javascript:alert(1)", "data:text/plain,secret",
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("\n".join(tokens), encoding="utf-8")

            findings = scan_public_tree(root)

            self.assertEqual(len(tokens), len(findings))
            self.assertTrue(all("…" in finding.excerpt for finding in findings))
            self.assertTrue(all("0123456789" not in finding.excerpt for finding in findings))
