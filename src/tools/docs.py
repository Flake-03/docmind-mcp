from fastmcp.server.providers import LocalProvider
from mcp.types import ToolAnnotations

from ..services.docs import DocsService

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True)
WRITE = ToolAnnotations(destructive_hint=False)


def create_docs_tools(service: DocsService) -> LocalProvider:
    provider = LocalProvider()
    for function in (service.search_documents, service.read_document):
        provider.tool(annotations=READ_ONLY)(function)
    provider.tool(annotations=WRITE)(service.publish_documents)
    return provider
