import uvicorn
from fastmcp import FastMCP

from .config import Settings
from .tools import register_tools

settings = Settings()
mcp = FastMCP("Project Documentation", mask_error_details=True)
register_tools(mcp, settings)
app = mcp.http_app(stateless_http=True)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)
