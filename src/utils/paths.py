import fnmatch
import re
from pathlib import Path

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
IGNORED_PARTS = {
    ".git",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "lib",
    "node_modules",
    "target",
    "vendor",
}


def validate_project_id(project_id: str) -> None:
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("invalid project_id")


def is_ignored_name(name: str) -> bool:
    return name in IGNORED_PARTS or name.startswith(".env")


def is_ignored_path(path: Path) -> bool:
    return any(is_ignored_name(part) for part in path.parts)


def is_text_file(path: Path) -> bool:
    try:
        with path.open("rb") as file:
            sample = file.read(8_192)
        sample.decode("utf-8")
        return b"\0" not in sample
    except (OSError, UnicodeDecodeError):
        return False


def matches_glob(path: str, pattern: str) -> bool:
    return (
        pattern in {"*", "**/*"}
        or fnmatch.fnmatch(path, pattern)
        or (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))
    )


def safe_path(root: Path, relative_path: str | Path, *, exists: bool = True) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path must stay inside its configured root")

    root = root.resolve(strict=True)
    candidate = root
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError("symlink paths are not allowed")

    try:
        candidate = candidate.resolve(strict=exists)
    except FileNotFoundError as error:
        raise ValueError("path does not exist") from error
    if not candidate.is_relative_to(root):
        raise ValueError("path resolves outside its configured root")
    return candidate


def document_path(project_id: str, relative_path: str) -> Path:
    validate_project_id(project_id)
    path = Path(relative_path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.suffix.lower() != ".md"
        or any(part.startswith(".") for part in path.parts)
    ):
        raise ValueError("document path must be a visible relative .md path")
    return Path("projects") / project_id / path
