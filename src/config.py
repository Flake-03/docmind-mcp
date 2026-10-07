from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    projects_root: Path
    docs_repository_url: str
    docs_repository_dir: Path
    docs_base_branch: str
    github_token: str
    git_author_name: str
    git_author_email: str


settings = Settings()
