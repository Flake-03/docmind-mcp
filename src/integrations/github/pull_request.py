import httpx

from ...config import Settings


def create_pull_request(settings: Settings, title: str, body: str, branch: str) -> str:
    repo = settings.docs_repository_url.removeprefix("https://github.com/").removesuffix(".git")
    response = httpx.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "title": title,
            "body": body,
            "head": branch,
            "base": settings.docs_base_branch,
        },
        timeout=30,
    )
    response.raise_for_status()

    url = response.json().get("html_url")
    if not isinstance(url, str) or not url:
        raise RuntimeError("GitHub response did not contain html_url")
    return url
