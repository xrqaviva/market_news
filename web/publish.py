"""Dry-run-first publisher for the standalone public news-radar repository."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Iterable, Optional

from web.security import assert_public_tree_safe


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SITE_REPO_NAME = "market-news-site"


@dataclass(frozen=True)
class PublishResult:
    site_repo: Path
    changed_paths: list
    applied: bool
    commit_sha: str = ""
    pushed: bool = False


class PublishBoundaryError(RuntimeError):
    """Raised when publication would cross a repository or Git boundary."""


def _git(site_repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(site_repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _checked_git(site_repo: Path, operation: str, *args: str) -> subprocess.CompletedProcess:
    completed = _git(site_repo, *args)
    if completed.returncode != 0:
        raise PublishBoundaryError("git {} failed".format(operation))
    return completed


def _worktree_files(site_repo: Path) -> dict:
    files = {}

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
            if directory == site_repo and path.name == ".git":
                continue
            relative = path.relative_to(site_repo).as_posix()
            if path.is_symlink():
                raise PublishBoundaryError("site repository must not contain symlinks")
            if path.is_dir():
                visit(path)
            elif path.is_file():
                files[relative] = path
            else:
                raise PublishBoundaryError("site repository contains an unsupported entry")

    visit(site_repo)
    return files


def _tracked_paths(site_repo: Path) -> set:
    completed = _checked_git(site_repo, "tracked-file inspection", "ls-files", "-z")
    return {path for path in completed.stdout.split("\0") if path}


def validate_site_repo(site_repo: Path, expected_name: str = _DEFAULT_SITE_REPO_NAME) -> None:
    """Require a standalone, named Git repository with a matching origin."""
    unresolved = site_repo.expanduser()
    if unresolved.is_symlink():
        raise PublishBoundaryError("site repository must not be a symlink")
    resolved = unresolved.resolve()
    if resolved in {Path("/").resolve(), Path.home().resolve(), _PROJECT_ROOT.resolve()}:
        raise PublishBoundaryError("site repository points at a protected directory")
    if resolved.name != expected_name or not resolved.is_dir():
        raise PublishBoundaryError("site repository has the wrong directory name")
    git_directory = resolved / ".git"
    if git_directory.is_symlink() or not git_directory.is_dir():
        raise PublishBoundaryError("site repository must contain its own .git directory")

    top_level = _checked_git(resolved, "repository validation", "rev-parse", "--show-toplevel")
    if Path(top_level.stdout.strip()).resolve() != resolved:
        raise PublishBoundaryError("site repository is not a standalone Git worktree")
    _worktree_files(resolved)

    remotes = _checked_git(resolved, "remote inspection", "remote").stdout.split()
    origin = _git(resolved, "config", "--get", "remote.origin.url")
    if origin.returncode != 0:
        if remotes:
            raise PublishBoundaryError("site repository remotes must use origin")
        return
    origin_url = origin.stdout.strip()
    allowed_endings = ("/{}.git".format(expected_name), ":{}.git".format(expected_name))
    if "\n" in origin_url or "\r" in origin_url or not origin_url.endswith(allowed_endings):
        raise PublishBoundaryError("origin does not target the expected site repository")


def _validate_dist(dist_dir: Path, site_repo: Path) -> Path:
    unresolved = dist_dir.expanduser()
    if unresolved.is_symlink():
        raise PublishBoundaryError("dist directory must not be a symlink")
    resolved = unresolved.resolve()
    if resolved.name != "dist" or not resolved.is_dir():
        raise PublishBoundaryError("publication input must be a directory named dist")
    if resolved == site_repo:
        raise PublishBoundaryError("dist and site repository must be different directories")
    assert_public_tree_safe(resolved)
    return resolved


def _dist_files(dist_dir: Path) -> dict:
    return {
        path.relative_to(dist_dir).as_posix(): path
        for path in sorted(dist_dir.rglob("*"))
        if path.is_file()
    }


def _same_public_file(source: Path, destination: Path) -> bool:
    if not destination.is_file():
        return False
    if source.read_bytes() != destination.read_bytes():
        return False
    return bool(source.stat().st_mode & 0o111) == bool(destination.stat().st_mode & 0o111)


def _remove_empty_worktree_directories(site_repo: Path) -> None:
    directories = [
        path
        for path in site_repo.rglob("*")
        if path.is_dir() and ".git" not in path.relative_to(site_repo).parts
    ]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass


def sync_dist(dist_dir: Path, site_repo: Path, dry_run: bool = True) -> PublishResult:
    """Compare exact public trees and optionally apply the safe dist tree."""
    validate_site_repo(site_repo)
    resolved_repo = site_repo.expanduser().resolve()
    resolved_dist = _validate_dist(dist_dir, resolved_repo)
    source_files = _dist_files(resolved_dist)
    destination_files = _worktree_files(resolved_repo)
    tracked_paths = _tracked_paths(resolved_repo)

    for relative, path in destination_files.items():
        if relative not in tracked_paths and path.stat().st_size:
            raise PublishBoundaryError("site repository contains a nonempty untracked file")

    changed = {
        relative
        for relative, source in source_files.items()
        if not _same_public_file(source, resolved_repo / relative)
    }
    changed.update(relative for relative in destination_files if relative not in source_files)
    changed.update(relative for relative in tracked_paths if relative not in source_files)
    changed_paths = sorted(changed)

    if dry_run:
        return PublishResult(resolved_repo, changed_paths, applied=False)

    for relative, path in destination_files.items():
        if relative not in source_files or not (resolved_repo / relative).is_file():
            path.unlink()
    _remove_empty_worktree_directories(resolved_repo)

    for relative, source in source_files.items():
        destination = resolved_repo / relative
        if destination.exists() and destination.is_dir():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not _same_public_file(source, destination):
            shutil.copy2(source, destination)

    return PublishResult(resolved_repo, changed_paths, applied=True)


def _require_clean_index(site_repo: Path) -> None:
    completed = _git(site_repo, "diff", "--cached", "--quiet", "--")
    if completed.returncode not in {0, 1}:
        raise PublishBoundaryError("git index inspection failed")
    if completed.returncode == 1:
        raise PublishBoundaryError("site repository index must be clean before publication")


def _scan_applied_public_tree(site_repo: Path) -> None:
    with TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "dist"
        snapshot.mkdir()
        for relative, source in _worktree_files(site_repo).items():
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        assert_public_tree_safe(snapshot)


def _commit_message(dist_dir: Path) -> str:
    manifest_path = dist_dir / "reports.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        reports = manifest["reports"]
        latest_url = manifest["latest"]
        latest = next(report for report in reports if report.get("url") == latest_url)
        report_date = latest["date"]
        slot = latest["slot"]
    except (FileNotFoundError, KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError):
        raise PublishBoundaryError("reports manifest cannot provide a deterministic commit message")
    if not isinstance(report_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_date):
        raise PublishBoundaryError("reports manifest has an invalid latest date")
    if not isinstance(slot, str) or not re.fullmatch(r"\d{4}", slot):
        raise PublishBoundaryError("reports manifest has an invalid latest slot")
    return "publish: {} {} news radar".format(report_date, slot)


def _stage_and_commit(dist_dir: Path, result: PublishResult) -> str:
    site_repo = result.site_repo
    _scan_applied_public_tree(site_repo)
    _checked_git(site_repo, "staging", "add", "-A", "--", ".")
    _checked_git(site_repo, "staged diff check", "diff", "--cached", "--check")
    staged = _checked_git(
        site_repo,
        "staged scope inspection",
        "diff",
        "--cached",
        "--name-only",
        "-z",
        "--diff-filter=ACDMRTUXB",
    )
    staged_paths = {path for path in staged.stdout.split("\0") if path}
    if not staged_paths:
        raise PublishBoundaryError("refusing an empty publication commit")
    if not staged_paths.issubset(set(result.changed_paths)):
        raise PublishBoundaryError("git index contains out-of-scope paths")
    message = _commit_message(dist_dir)
    _checked_git(site_repo, "commit", "commit", "-m", message)
    return _checked_git(site_repo, "commit verification", "rev-parse", "HEAD").stdout.strip()


def _push_checked_out_branch(site_repo: Path) -> None:
    validate_site_repo(site_repo)
    branch = _checked_git(
        site_repo, "branch inspection", "symbolic-ref", "--quiet", "--short", "HEAD"
    ).stdout.strip()
    if not branch or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or branch.startswith("-"):
        raise PublishBoundaryError("site repository must have a safe checked-out branch")
    _checked_git(
        site_repo,
        "push",
        "push",
        "origin",
        "HEAD:refs/heads/{}".format(branch),
    )


def publish_site(
    dist_dir: Path,
    site_repo: Path,
    apply: bool = False,
    commit: bool = False,
    push: bool = False,
) -> PublishResult:
    """Run validated sync, deterministic commit, and ordinary push stages."""
    if commit and not apply:
        raise PublishBoundaryError("--commit requires --apply")
    if push and (not apply or not commit):
        raise PublishBoundaryError("--push requires --apply and --commit")

    resolved_repo = site_repo.expanduser().resolve()
    if commit:
        validate_site_repo(site_repo)
        _require_clean_index(resolved_repo)
    result = sync_dist(dist_dir, site_repo, dry_run=not apply)
    if not commit:
        return result

    resolved_dist = dist_dir.expanduser().resolve()
    commit_sha = _stage_and_commit(resolved_dist, result)
    if push:
        _push_checked_out_branch(result.site_repo)
    return PublishResult(
        site_repo=result.site_repo,
        changed_paths=result.changed_paths,
        applied=True,
        commit_sha=commit_sha,
        pushed=push,
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a safe news-radar static site")
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--site-repo", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = publish_site(
            args.dist,
            args.site_repo,
            apply=args.apply,
            commit=args.commit,
            push=args.push,
        )
    except Exception as error:
        print("publish failed: {}".format(error), file=sys.stderr)
        return 1
    print(json.dumps(
        {
            "site_repo": str(result.site_repo),
            "changed_paths": result.changed_paths,
            "applied": result.applied,
            "commit_sha": result.commit_sha,
            "pushed": result.pushed,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
