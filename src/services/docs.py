from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ..config import Settings
from ..integrations.github.pull_request import create_pull_request
from ..integrations.github.repo import DocsRepo
from ..schemas.common import ProjectId, RelativePath, SearchQuery
from ..schemas.docs import (
    DocumentChange,
    DocumentMatch,
    PublishResult,
    PullRequestBody,
    PullRequestTitle,
)
from ..utils.paths import doc_path, safe_path, validate_project_id

MAX_FILE_BYTES = 512_000
MAX_MATCHES = 50
MAX_PUBLISH_FILES = 8
MAX_PUBLISH_BYTES = 250_000


class DocsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repo = DocsRepo(settings)

    def read_document(self, project_id: ProjectId, path: RelativePath) -> str:
        """Read one merged Markdown document."""
        with self._repo.synced():
            relative_path = doc_path(project_id, path)
            doc = safe_path(self._repo.repo_dir, relative_path)
            if not doc.is_file():
                raise ValueError("document does not exist")
            if doc.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("document is too large")
            return doc.read_text(encoding="utf-8")

    def search_documents(self, query: SearchQuery, project_id: ProjectId | None = None) -> list[DocumentMatch]:
        """Search merged Markdown documentation."""
        needle = query.strip().casefold()
        if not needle:
            raise ValueError("query must not be blank")

        with self._repo.synced():
            projects_dir = self._repo.repo_dir / "projects"
            search_root = projects_dir
            if project_id is not None:
                validate_project_id(project_id)
                search_root /= project_id
            if not search_root.exists():
                return []

            matches: list[DocumentMatch] = []
            for doc in sorted(search_root.rglob("*.md")):
                if doc.is_symlink() or not doc.is_file() or doc.stat().st_size > MAX_FILE_BYTES:
                    continue

                matched_project_id, *document_parts = doc.relative_to(projects_dir).parts
                relative_path = Path(*document_parts).as_posix()
                for line_number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
                    if needle in line.casefold():
                        matches.append(
                            DocumentMatch(
                                project_id=matched_project_id,
                                path=relative_path,
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

        with self._repo.synced():
            branch = self._new_branch(project_id)
            self._repo.create_branch(branch)

            changed_paths: list[str] = []
            for change in changes:
                relative_path = doc_path(project_id, change.path)
                doc = safe_path(self._repo.repo_dir, relative_path, exists=False)
                doc.parent.mkdir(parents=True, exist_ok=True)
                doc.write_text(change.content.rstrip() + "\n", encoding="utf-8")
                changed_paths.append(relative_path.as_posix())

            commit = self._repo.commit_and_push(title, branch, changed_paths)
            pull_request_url = create_pull_request(self._settings, title, body, branch)
            return PublishResult(
                branch=branch,
                commit=commit,
                pull_request_url=pull_request_url,
                changed_files=sorted(changed_paths),
            )

    @staticmethod
    def _validate_publish(title: str, body: str, changes: list[DocumentChange]) -> None:
        if not title.strip() or len(title) > 120:
            raise ValueError("title must contain 1 to 120 characters")
        if len(body) > 10_000:
            raise ValueError("pull request body exceeds 10,000 characters")
        if not changes or len(changes) > MAX_PUBLISH_FILES:
            raise ValueError(f"changes must contain 1 to {MAX_PUBLISH_FILES} files")
        if sum(len(change.content.encode("utf-8")) for change in changes) > MAX_PUBLISH_BYTES:
            raise ValueError("documentation changes are too large")
        if len({change.path for change in changes}) != len(changes):
            raise ValueError("changes contain duplicate document paths")

    @staticmethod
    def _new_branch(project_id: str) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return f"docs/{project_id}/{timestamp}-{uuid4().hex[:8]}"
