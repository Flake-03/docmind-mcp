from collections.abc import Iterator
from pathlib import Path

from ..schemas.common import GlobPattern, LineNumber, ProjectId, RelativePath, SearchQuery
from ..schemas.source import FileEntry, SearchMatch
from ..utils.paths import (
    PROJECT_ID_PATTERN,
    is_ignored_name,
    is_ignored_path,
    is_text_file,
    matches_glob,
    safe_path,
    validate_project_id,
)

MAX_FILES = 2_000
MAX_FILE_BYTES = 512_000
MAX_MATCHES = 50


class SourceService:
    def __init__(self, projects_root: Path) -> None:
        self._projects_root = projects_root

    def list_projects(self) -> list[str]:
        """List project IDs available below PROJECTS_ROOT."""
        if not self._projects_root.is_dir():
            raise ValueError("PROJECTS_ROOT does not exist")
        return sorted(
            path.name
            for path in self._projects_root.iterdir()
            if path.is_dir() and not path.is_symlink() and PROJECT_ID_PATTERN.fullmatch(path.name)
        )

    def list_project_files(self, project_id: ProjectId, pattern: GlobPattern = "**/*") -> list[FileEntry]:
        """List readable text files in a project, optionally filtered by glob."""
        entries: list[FileEntry] = []
        for relative_path, source_file in self._text_files(project_id, pattern):
            entries.append(FileEntry(path=relative_path, size_bytes=source_file.stat().st_size))
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

        project_root = self._project_root(project_id)
        file_path = safe_path(project_root, path)
        relative_path = file_path.relative_to(project_root)
        if is_ignored_path(relative_path) or not file_path.is_file():
            raise ValueError("file is not readable")
        if file_path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("file is too large")
        if not is_text_file(file_path):
            raise ValueError("file is not valid UTF-8 text")

        lines = file_path.read_text(encoding="utf-8").splitlines()
        selected = lines[start_line - 1 : end_line]
        return "\n".join(f"{number}: {line}" for number, line in enumerate(selected, start=start_line))

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
        for relative_path, source_file in self._text_files(project_id, pattern):
            for line_number, line in enumerate(source_file.read_text(encoding="utf-8").splitlines(), start=1):
                if needle in line.casefold():
                    matches.append(SearchMatch(path=relative_path, line=line_number, text=line[:500]))
                    if len(matches) >= MAX_MATCHES:
                        return matches
        return matches

    def _project_root(self, project_id: str) -> Path:
        validate_project_id(project_id)
        project_root = safe_path(self._projects_root, project_id)
        if not project_root.is_dir():
            raise ValueError(f"project_id {project_id!r} is not a directory")
        return project_root

    def _text_files(self, project_id: str, pattern: str) -> Iterator[tuple[str, Path]]:
        project_root = self._project_root(project_id)
        for directory, dirnames, filenames in project_root.walk():
            dirnames[:] = sorted(
                name for name in dirnames if not is_ignored_name(name) and not (directory / name).is_symlink()
            )
            for name in sorted(filenames):
                source_file = directory / name
                relative_path = source_file.relative_to(project_root)
                relative_path_text = relative_path.as_posix()
                if source_file.is_symlink() or is_ignored_path(relative_path):
                    continue
                if not matches_glob(relative_path_text, pattern):
                    continue
                if source_file.stat().st_size > MAX_FILE_BYTES or not is_text_file(source_file):
                    continue
                yield relative_path_text, source_file
