from fastmcp.server.providers import LocalProvider
from mcp.types import ToolAnnotations

from ..services.projects import ProjectService

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)


def create_project_tools(service: ProjectService) -> LocalProvider:
    tools = LocalProvider()
    for function in (
        service.list_projects,
        service.list_project_files,
        service.read_project_file,
        service.search_project_text,
    ):
        tools.tool(annotations=READ_ONLY)(function)
    return tools
