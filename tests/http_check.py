"""Call `add` on a running HTTP MCP server."""

import asyncio
import sys

from mcp import Client


async def main(url: str) -> None:
    """Connect to `url` and call the `add` tool."""
    async with Client(url) as client:
        result = await client.call_tool("add", {"a": 4, "b": 6})
        print("add(4, 6) =", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000/mcp"))
