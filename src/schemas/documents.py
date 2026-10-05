from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from .projects import SearchMatch

PullRequestTitle = Annotated[str, Field(min_length=1, max_length=120)]
PullRequestBody = Annotated[str, Field(max_length=10_000)]


class DocumentMatch(SearchMatch):
    project_id: str


class DocumentChange(BaseModel):
    path: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def markdown_only(cls, value: str) -> str:
        if not value.lower().endswith(".md"):
            raise ValueError("document path must end in .md")
        return value


class PublishResult(BaseModel):
    branch: str
    commit: str
    pull_request_url: str
    changed_files: list[str]
