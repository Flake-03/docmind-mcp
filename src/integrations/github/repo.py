import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from ...config import Settings


class DocsRepo:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.repo_dir = settings.docs_repository_dir
        self._env = os.environ | {
            "GIT_AUTHOR_NAME": settings.git_author_name,
            "GIT_AUTHOR_EMAIL": settings.git_author_email,
            "GIT_COMMITTER_NAME": settings.git_author_name,
            "GIT_COMMITTER_EMAIL": settings.git_author_email,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": str(Path(__file__).with_name("git_askpass.sh")),
            "GITHUB_TOKEN": settings.github_token,
        }
        self.repo_dir.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(f"{self.repo_dir}.lock", timeout=120)

    @contextmanager
    def synced(self) -> Iterator[None]:
        with self._lock:
            self._prepare()
            self._run("reset", "--hard")
            self._run("clean", "-fd", "--", "projects")
            self._require_base_branch()
            self._run("switch", "--detach", f"origin/{self._settings.docs_base_branch}")
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

    def _prepare(self) -> None:
        if (self.repo_dir / ".git").is_dir():
            self._run("fetch", "--prune", "origin")
            return
        if self.repo_dir.exists() and any(self.repo_dir.iterdir()):
            raise RuntimeError(f"managed repository path is not empty: {self.repo_dir}")
        self._run("clone", self._settings.docs_repository_url, str(self.repo_dir), cwd=self.repo_dir.parent)

    def _require_base_branch(self) -> None:
        branch = self._settings.docs_base_branch
        result = self._run("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}", check=False)
        if result.returncode != 0:
            raise RuntimeError(f"documentation repository has no {branch!r} base branch")

    def _run(self, *args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo_dir,
            env=self._env,
            check=check,
            capture_output=True,
            text=True,
            timeout=120,
        )
