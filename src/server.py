import uvicorn
from fastmcp import FastMCP

from .config import settings
from .tools import register_tools

mcp = FastMCP("DocMind")

register_tools(mcp, settings)
app = mcp.http_app(stateless_http=True)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
