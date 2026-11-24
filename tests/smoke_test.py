"""Smoke-test the demo MCP server over stdio.

Run with: uv run --with "mcp>=2.0.0" tests/smoke_test.py <path-to-server.py>
"""

import asyncio
import sys

from mcp import Client, StdioServerParameters


async def main(server_path: str) -> None:
    """Start the server, list its tools, and call `add`."""
    params = StdioServerParameters(
        command="uv", args=["run", server_path, "--transport", "stdio"]
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools.tools)
        assert names == ["add", "get-energy-prices", "get-todos"], names

        result = await client.call_tool("add", {"a": 2, "b": 3})
        text = result.content[0].text
        assert text == "5.0", text
    print("PASS: tools =", names, "| add(2, 3) =", text)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
