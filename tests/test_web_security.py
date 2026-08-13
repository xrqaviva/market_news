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

    def test_accepts_only_the_empty_data_favicon_sentinel(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<link rel="icon" href="data:,">', encoding="utf-8"
            )
            self.assertEqual([], scan_public_tree(root))

            (root / "index.html").write_text(
                '<link rel="icon" href="data:,secret">', encoding="utf-8"
            )
            findings = scan_public_tree(root)
            self.assertTrue(any(item.rule == "unsafe-url-scheme" for item in findings))

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

    def test_rejects_utf16_content_that_contains_an_unsafe_url(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_bytes(
                '<a href="javascript:alert(1)">unsafe</a>'.encode("utf-16")
            )

            findings = scan_public_tree(root)

            self.assertTrue(any(item.rule == "unsupported-file-encoding" for item in findings))
            with self.assertRaises(PublicTreeUnsafe):
                assert_public_tree_safe(root)

    def test_rejects_files_outside_the_public_build_contract(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("safe", encoding="utf-8")
            (root / "unexpected.html").write_text("safe", encoding="utf-8")

            findings = scan_public_tree(root)

            self.assertTrue(any(item.rule == "unexpected-public-file" for item in findings))

    def test_rejects_a_symlink_used_as_the_public_root(self):
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            real_root = parent / "real"
            real_root.mkdir()
            (real_root / "index.html").write_text("safe", encoding="utf-8")
            linked_root = parent / "linked"
            linked_root.symlink_to(real_root, target_is_directory=True)

            findings = scan_public_tree(linked_root)

            self.assertTrue(any(item.rule == "symlink" for item in findings))
