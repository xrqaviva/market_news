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
    ("absolute-local-path", re.compile(rb"/Users/")),
    ("local-file-url", re.compile(rb"file://", re.IGNORECASE)),
    ("private-key", re.compile(rb"BEGIN OPENSSH PRIVATE KEY")),
    ("credential-token", re.compile(rb"ghp_", re.IGNORECASE)),
    ("credential-token", re.compile(rb"github_pat_", re.IGNORECASE)),
    ("authorization-header", re.compile(rb"Authorization:\s*Bearer", re.IGNORECASE)),
    ("cookie-header", re.compile(rb"Cookie:", re.IGNORECASE)),
    ("local-storage", re.compile(rb"Local Storage", re.IGNORECASE)),
    ("unsafe-url-scheme", re.compile(rb"\b(?:javascript|data):", re.IGNORECASE)),
)


def _private_file_name(name: str) -> bool:
    lowered = name.lower()
    return (
        "evidence" in lowered
        or lowered in _PRIVATE_FILE_NAMES
        or lowered == ".env"
        or lowered.startswith(".env.")
    )


def _redact(match: re.Match[bytes]) -> str:
    return "{}…".format(match.group(0)[:4].decode("ascii", errors="replace"))


def _find_content(root: Path, path: Path) -> list[SecurityFinding]:
    content = path.read_bytes()
    relative = path.relative_to(root).as_posix()
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return [SecurityFinding(relative, "unsupported-file-encoding", "bina…")]
    scannable_content = content.replace(b'<link rel="icon" href="data:,">', b"")
    findings = []
    for rule, pattern in _CONTENT_RULES:
        for match in pattern.finditer(scannable_content):
            findings.append(SecurityFinding(relative, rule, _redact(match)))
    return findings


def _allowed_public_path(relative: str, is_directory: bool) -> bool:
    if is_directory:
        return relative in {"assets", "reports"}
    return (
        relative in {"index.html", "reports.json", "assets/app.css", "assets/app.js"}
        or re.fullmatch(r"reports/[^/]+\.html", relative) is not None
    )


def scan_public_tree(root: Path) -> list[SecurityFinding]:
    """Scan only regular files below resolved root; never follow symlinks."""
    unresolved_root = root.expanduser()
    if unresolved_root.is_symlink():
        return [SecurityFinding(".", "symlink", "syml…")]
    resolved_root = unresolved_root.resolve()
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
                if not _allowed_public_path(relative, is_directory=True):
                    findings.append(SecurityFinding(relative, "unexpected-public-file", "path…"))
                    continue
                visit(path)
            elif path.is_file():
                if not _allowed_public_path(relative, is_directory=False):
                    findings.append(SecurityFinding(relative, "unexpected-public-file", "path…"))
                    continue
                findings.extend(_find_content(resolved_root, path))

    visit(resolved_root)
    return findings


def assert_public_tree_safe(root: Path) -> None:
    findings = scan_public_tree(root)
    if findings:
        raise PublicTreeUnsafe("; ".join("{}:{}".format(f.path, f.rule) for f in findings))
