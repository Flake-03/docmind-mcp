import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from ...config import Settings


class GitService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.docs_repository_dir
        self.env = os.environ | {
            "GIT_AUTHOR_NAME": settings.git_author_name,
            "GIT_AUTHOR_EMAIL": settings.git_author_email,
            "GIT_COMMITTER_NAME": settings.git_author_name,
            "GIT_COMMITTER_EMAIL": settings.git_author_email,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": str(Path(__file__).with_name("git_askpass.sh")),
            "GITHUB_TOKEN": settings.github_token,
        }
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(f"{self.root}.lock", timeout=120)

    @contextmanager
    def synced(self) -> Iterator[None]:
        with self.lock:
            self._checkout()
            self._run("reset", "--hard")
            self._run("clean", "-fd", "--", "projects")
            self._require_base_branch()
            self._run("switch", "--detach", f"origin/{self.settings.docs_base_branch}")
            yield

    def create_branch(self, branch: str) -> None:
        self._run("switch", "--force-create", branch)

    def commit_and_push(self, title: str, branch: str, paths: list[str]) -> str:
        self._run("add", "--", *paths)
        result = self._run("diff", "--cached", "--quiet", check=False)
        if result.returncode == 0:
            raise ValueError("documentation is unchanged")
        if result.returncode != 1:
            raise RuntimeError("git failed while checking changes")

        self._run("commit", "-m", title)
        commit = self._run("rev-parse", "HEAD").stdout.strip()
        self._run("push", "--set-upstream", "origin", branch)
        return commit

    def _checkout(self) -> None:
        if (self.root / ".git").is_dir():
            self._run("fetch", "--prune", "origin")
            return
        if self.root.exists() and any(self.root.iterdir()):
            raise RuntimeError(f"managed repository path is not empty: {self.root}")
        self._run("clone", self.settings.docs_repository_url, str(self.root), cwd=self.root.parent)

    def _require_base_branch(self) -> None:
        branch = self.settings.docs_base_branch
        result = self._run("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}", check=False)
        if result.returncode != 0:
            raise RuntimeError(f"documentation repository has no {branch!r} base branch")

    def _run(self, *args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            env=self.env,
            check=check,
            capture_output=True,
            text=True,
            timeout=120,
        )
