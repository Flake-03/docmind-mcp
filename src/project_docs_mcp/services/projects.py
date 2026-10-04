import fnmatch
from collections.abc import Iterator
from pathlib import Path

from ..schemas.common import GlobPattern, LineNumber, ProjectId, RelativePath, SearchQuery
from ..schemas.projects import FileEntry, SearchMatch
from .paths import (
    IGNORED_PARTS,
    PROJECT_ID_PATTERN,
    safe_path,
    validate_project_id,
)

MAX_FILES = 2_000
MAX_FILE_BYTES = 512_000
MAX_MATCHES = 50


class ProjectService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_projects(self) -> list[str]:
        """List project IDs available below PROJECTS_ROOT."""
        if not self.root.is_dir():
            raise ValueError("PROJECTS_ROOT does not exist")
        return sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_dir()
            and not path.is_symlink()
            and PROJECT_ID_PATTERN.fullmatch(path.name)
        )

    def list_project_files(
        self, project_id: ProjectId, pattern: GlobPattern = "**/*"
    ) -> list[FileEntry]:
        """List readable text files in a project, optionally filtered by glob."""
        entries: list[FileEntry] = []
        for relative, path in self._text_files(project_id, pattern):
            entries.append(FileEntry(path=relative, size_bytes=path.stat().st_size))
            if len(entries) >= MAX_FILES:
                break
        return entries

    def read_project_file(
        self,
        project_id: ProjectId,
        path: RelativePath,
        start_line: LineNumber = 1,
        end_line: LineNumber = 400,
    ) -> str:
        """Read up to 500 numbered lines from a project-relative text file."""
        if start_line < 1 or end_line < start_line or end_line - start_line > 499:
            raise ValueError("line range must contain 1 to 500 lines")

        project = self._project_root(project_id)
        candidate = safe_path(project, path)
        relative = candidate.relative_to(project)
        if self._ignored(relative) or not candidate.is_file():
            raise ValueError("file is not readable")
        if candidate.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("file is too large")
        if not self._is_text(candidate):
            raise ValueError("file is not valid UTF-8 text")

        lines = candidate.read_text(encoding="utf-8").splitlines()
        selected = lines[start_line - 1 : end_line]
        return "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(selected, start=start_line)
        )

    def search_project_text(
        self,
        project_id: ProjectId,
        query: SearchQuery,
        pattern: GlobPattern = "**/*",
    ) -> list[SearchMatch]:
        """Find a case-insensitive literal string in project text files."""
        needle = query.strip().casefold()
        if not needle:
            raise ValueError("query must not be blank")

        matches: list[SearchMatch] = []
        for relative, path in self._text_files(project_id, pattern):
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if needle in line.casefold():
                    matches.append(
                        SearchMatch(path=relative, line=line_number, text=line[:500])
                    )
                    if len(matches) >= MAX_MATCHES:
                        return matches
        return matches

    def _project_root(self, project_id: str) -> Path:
        validate_project_id(project_id)
        project = safe_path(self.root, project_id)
        if not project.is_dir():
            raise ValueError(f"project_id {project_id!r} is not a directory")
        return project

    def _text_files(
        self, project_id: str, pattern: str
    ) -> Iterator[tuple[str, Path]]:
        project = self._project_root(project_id)
        for directory, dirnames, filenames in project.walk():
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in IGNORED_PARTS
                and not name.startswith(".env")
                and not (directory / name).is_symlink()
            )
            for name in sorted(filenames):
                path = directory / name
                relative = path.relative_to(project)
                relative_text = relative.as_posix()
                if self._ignored(relative) or path.is_symlink():
                    continue
                if (
                    pattern not in {"*", "**/*"}
                    and not fnmatch.fnmatch(relative_text, pattern)
                    and not (
                        pattern.startswith("**/")
                        and fnmatch.fnmatch(relative_text, pattern[3:])
                    )
                ):
                    continue
                if path.stat().st_size > MAX_FILE_BYTES or not self._is_text(path):
                    continue
                yield relative_text, path

    @staticmethod
    def _ignored(relative: Path) -> bool:
        return any(
            part in IGNORED_PARTS or part.startswith(".env") for part in relative.parts
        )

    @staticmethod
    def _is_text(path: Path) -> bool:
        try:
            with path.open("rb") as file:
                sample = file.read(8_192)
            sample.decode("utf-8")
            return b"\0" not in sample
        except (OSError, UnicodeDecodeError):
            return False
