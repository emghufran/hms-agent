import asyncio
import argparse
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec


async def main(host: str, port: int):
    # Build MCP URL from host and port
    mcp_url = f"http://{host}:{port}/mcp"

    # Initialize MCP client and tool spec
    mcp_client = BasicMCPClient(mcp_url)
    mcp_tool = McpToolSpec(client=mcp_client)

    # Print available tools
    tools = await mcp_tool.to_tool_list_async()
    print("Available tools:")
    for tool in tools:
        print(f"{tool.metadata.name}: {tool.metadata.description}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP client")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8000, help="MCP server port")

    args = parser.parse_args()

    asyncio.run(main(args.host, args.port))
