from typing import Annotated

from pydantic import Field

ProjectId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")]
RelativePath = Annotated[str, Field(min_length=1, max_length=500)]
SearchQuery = Annotated[str, Field(min_length=1, max_length=200)]
GlobPattern = Annotated[str, Field(min_length=1, max_length=200)]
LineNumber = Annotated[int, Field(ge=1)]
