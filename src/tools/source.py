from fastmcp.server.providers import LocalProvider
from mcp.types import ToolAnnotations

from ..services.source import SourceService

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def create_source_tools(service: SourceService) -> LocalProvider:
    provider = LocalProvider()
    for function in (
        service.list_projects,
        service.list_project_files,
        service.read_project_file,
        service.search_project_text,
    ):
        provider.tool(annotations=READ_ONLY)(function)
    return provider
