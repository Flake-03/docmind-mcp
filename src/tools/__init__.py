from fastmcp import FastMCP

from ..config import Settings
from ..services.docs import DocsService
from ..services.source import SourceService
from .docs import create_docs_tools
from .source import create_source_tools


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    source = SourceService(settings.projects_root)
    docs = DocsService(settings)

    mcp.add_provider(create_source_tools(source))
    mcp.add_provider(create_docs_tools(docs))
