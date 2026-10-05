from fastmcp.server.providers import LocalProvider
from mcp.types import ToolAnnotations

from ..services.documents import DocumentService

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True)
WRITE = ToolAnnotations(destructive_hint=False)


def create_document_tools(service: DocumentService) -> LocalProvider:
    tools = LocalProvider()
    for function in (service.search_documents, service.read_document):
        tools.tool(annotations=READ_ONLY)(function)
    tools.tool(annotations=WRITE)(service.publish_documents)
    return tools
