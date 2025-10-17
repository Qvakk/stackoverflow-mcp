"""Main entry point for Stack Overflow MCP server."""

import asyncio

from stackoverflow_mcp.server import StackOverflowMCPServer


async def main() -> None:
    """Run the Stack Overflow MCP server."""
    server = StackOverflowMCPServer()
    try:
        await server.run()
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
