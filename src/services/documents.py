import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ..clients.github import create_pull_request
from ..config import Settings
from ..schemas.common import ProjectId, RelativePath, SearchQuery
from ..schemas.documents import (
    DocumentChange,
    DocumentMatch,
    PublishResult,
    PullRequestBody,
    PullRequestTitle,
)
from .git import GitService
from .paths import (
    document_path,
    safe_path,
    validate_project_id,
)

MAX_FILE_BYTES = 512_000
MAX_MATCHES = 50
MAX_PUBLISH_FILES = 8
MAX_PUBLISH_BYTES = 250_000


class DocumentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.git = GitService(settings)

    def read_document(self, project_id: ProjectId, path: RelativePath) -> str:
        """Read one merged Markdown document."""
        with self.git.synced():
            relative = document_path(project_id, path)
            candidate = safe_path(self.git.root, relative)
            if not candidate.is_file():
                raise ValueError("document does not exist")
            if candidate.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("document is too large")
            return candidate.read_text(encoding="utf-8")

    def search_documents(
        self, query: SearchQuery, project_id: ProjectId | None = None
    ) -> list[DocumentMatch]:
        """Search merged Markdown documentation."""
        needle = query.strip().casefold()
        if not needle:
            raise ValueError("query must not be blank")

        with self.git.synced():
            projects_root = self.git.root / "projects"
            search_root = projects_root
            if project_id is not None:
                validate_project_id(project_id)
                search_root /= project_id
            if not search_root.exists():
                return []

            matches: list[DocumentMatch] = []
            for path in sorted(search_root.rglob("*.md")):
                if path.is_symlink() or not path.is_file():
                    continue
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue

                relative = path.relative_to(projects_root)
                match_project, *document_parts = relative.parts
                document = Path(*document_parts).as_posix()
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    if needle in line.casefold():
                        matches.append(
                            DocumentMatch(
                                project_id=match_project,
                                path=document,
                                line=line_number,
                                text=line[:500],
                            )
                        )
                        if len(matches) >= MAX_MATCHES:
                            return matches
            return matches

    def publish_documents(
        self,
        project_id: ProjectId,
        title: PullRequestTitle,
        body: PullRequestBody,
        changes: list[DocumentChange],
    ) -> PublishResult:
        """Commit Markdown replacements and open a pull request."""
        validate_project_id(project_id)
        self._validate_publish(title, body, changes)

        with self.git.synced():
            branch = self._new_branch(project_id)
            self.git.create_branch(branch)

            changed_paths: list[str] = []
            for change in changes:
                relative = document_path(project_id, change.path)
                destination = safe_path(self.git.root, relative, exists=False)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    change.content.rstrip() + "\n", encoding="utf-8"
                )
                changed_paths.append(relative.as_posix())

            commit = self.git.commit_and_push(title, branch, changed_paths)
            pull_request_url = create_pull_request(
                self.settings,
                title,
                body,
                branch,
            )
            return PublishResult(
                branch=branch,
                commit=commit,
                pull_request_url=pull_request_url,
                changed_files=sorted(changed_paths),
            )

    def _validate_publish(
        self, title: str, body: str, changes: list[DocumentChange]
    ) -> None:
        if not title.strip() or len(title) > 120:
            raise ValueError("title must contain 1 to 120 characters")
        if len(body) > 10_000:
            raise ValueError("pull request body exceeds 10,000 characters")
        if not changes or len(changes) > MAX_PUBLISH_FILES:
            raise ValueError(f"changes must contain 1 to {MAX_PUBLISH_FILES} files")
        if (
            sum(len(change.content.encode("utf-8")) for change in changes)
            > MAX_PUBLISH_BYTES
        ):
            raise ValueError("documentation changes are too large")
        paths = [change.path for change in changes]
        if len(paths) != len(set(paths)):
            raise ValueError("changes contain duplicate document paths")

    @staticmethod
    def _new_branch(project_id: str) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        safe_id = re.sub(r"[^A-Za-z0-9._-]", "-", project_id)
        return f"docs/{safe_id}/{timestamp}-{uuid4().hex[:8]}"
