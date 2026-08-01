"""Safety checks for files that are safe to publish as a static site."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class SecurityFinding:
    path: str
    rule: str
    excerpt: str


class PublicTreeUnsafe(RuntimeError):
    """Raised when a static public directory contains unsafe content."""


_PRIVATE_FILE_NAMES = {
    "findings.md",
    "progress.md",
    "task_plan.md",
    "handoff.md",
    ".git",
    ".superpowers",
    ".planning",
}
_CONTENT_RULES = (
    ("absolute-local-path", re.compile(r"/Users/")),
    ("local-file-url", re.compile(r"file://", re.IGNORECASE)),
    ("private-key", re.compile(r"BEGIN OPENSSH PRIVATE KEY")),
    ("credential-token", re.compile(r"ghp_", re.IGNORECASE)),
    ("credential-token", re.compile(r"github_pat_", re.IGNORECASE)),
    ("authorization-header", re.compile(r"Authorization:\s*Bearer", re.IGNORECASE)),
    ("cookie-header", re.compile(r"Cookie:", re.IGNORECASE)),
    ("local-storage", re.compile(r"Local Storage", re.IGNORECASE)),
    ("unsafe-url-scheme", re.compile(r"\b(?:javascript|data):", re.IGNORECASE)),
)


def _private_file_name(name: str) -> bool:
    lowered = name.lower()
    return (
        "evidence" in lowered
        or lowered in _PRIVATE_FILE_NAMES
        or lowered == ".env"
        or lowered.startswith(".env.")
    )


def _redact(match: re.Match) -> str:
    return "{}…".format(match.group(0)[:4])


def _find_content(root: Path, path: Path) -> list[SecurityFinding]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    findings = []
    for rule, pattern in _CONTENT_RULES:
        for match in pattern.finditer(text):
            findings.append(SecurityFinding(relative, rule, _redact(match)))
    return findings


def scan_public_tree(root: Path) -> list[SecurityFinding]:
    """Scan only regular files below resolved root; never follow symlinks."""
    resolved_root = root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise ValueError("public tree root must be a directory: {}".format(root))

    findings = []

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
            relative = path.relative_to(resolved_root).as_posix()
            if path.is_symlink():
                findings.append(SecurityFinding(relative, "symlink", "syml…"))
                continue
            if _private_file_name(path.name):
                findings.append(SecurityFinding(relative, "private-file-name", "{}…".format(path.name[:4])))
                continue
            if path.is_dir():
                visit(path)
            elif path.is_file():
                findings.extend(_find_content(resolved_root, path))

    visit(resolved_root)
    return findings


def assert_public_tree_safe(root: Path) -> None:
    findings = scan_public_tree(root)
    if findings:
        raise PublicTreeUnsafe("; ".join("{}:{}".format(f.path, f.rule) for f in findings))
