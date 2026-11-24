# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=2.0.0",
#     "fastapi>=0.141.0",
#     "uvicorn>=0.52.0",
#     "httpx>=0.28.0",
# ]
# ///
"""Demo MCP server with two transports.

Run over stdio (for Claude Code):  uv run server.py --transport stdio
Run over HTTP (for remote use):    uv run server.py --transport http --port 3000
"""

import argparse
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from mcp.server import MCPServer

mcp_server = MCPServer(name="Demo", version="1.0.0")


@mcp_server.tool(name="add")
def add(a: float, b: float) -> str:
    """Add two numbers."""
    return str(a + b)


@mcp_server.tool(name="get-energy-prices")
async def get_energy_prices() -> str:
    """Fetch tomorrow's energy prices."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.awattar.de/v1/marketdata")
        data = response.json()
    return f"Energy prices for tomorrow: {data}"


@mcp_server.tool(name="get-todos")
async def get_todos() -> str:
    """Fetch a public todo list."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/todos")
        data = response.json()
    return f"Todos: {data}"


@mcp_server.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Return a greeting for `name`."""
    return f"Hello, {name}!"


def build_http_app() -> FastAPI:
    """Return a FastAPI app that serves the MCP endpoint at /mcp."""
    mcp_app = mcp_server.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(lifespan=lifespan)
    app.mount("/", mcp_app)
    return app


def main() -> None:
    """Parse arguments and start the server on the chosen transport."""
    parser = argparse.ArgumentParser(description="Demo MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    if args.transport == "stdio":
        # Never print() to stdout here: stdout carries the MCP protocol.
        mcp_server.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(build_http_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
