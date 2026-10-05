from pydantic import BaseModel


class FileEntry(BaseModel):
    path: str
    size_bytes: int


class SearchMatch(BaseModel):
    path: str
    line: int
    text: str
