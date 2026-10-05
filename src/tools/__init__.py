from fastmcp import FastMCP

from ..config import Settings
from ..services.documents import DocumentService
from ..services.projects import ProjectService
from .documents import create_document_tools
from .projects import create_project_tools


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    projects = ProjectService(settings.projects_root)
    documents = DocumentService(settings)

    mcp.add_provider(create_project_tools(projects))
    mcp.add_provider(create_document_tools(documents))
