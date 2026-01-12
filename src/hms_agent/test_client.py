import asyncio
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings

llm = Ollama(model="llama3.2", request_timeout=120.0)
Settings.llm = llm


# System prompt for the agent
SYSTEM_PROMPT = """\
You are an AI assistant for hotel reservations. You have several tools at your disposal to perfrom the actions. Be as human as you can in conversations

Before you help a user, you need to work with tools to interact with hotel database.
Only reply with information from available tools. Do NOT generate any response that does not come from the available tools regarding locations, hotels, rooms availabilities etc.
If a tool call fails, inform the user about it. 

If you need certain information for a tool call, ask the user about what you need instead of calling the tool without the required parameters.
You have the following tools available: 
1. get_locations: This tool gives you a list of available locations in the system. This is necessary to get a list of hotels.
2. get_hotels: This tool gives a list of hotels that are available for a given location. If no location id is provided first call get_locations and only then call this tool.
3. search_rooms: This tool gives a list of rooms available for a hotel. You need to have a hotel id, check-in / check-out dates and capacity required. 
    You need to provide a hotel id. If you don't have one, ask the user appropriate questions to identify a hotel. Call appropriate tools like get_locations, and get_hotels.
4. 
"""


async def get_agent(tools: McpToolSpec):
    """Create and return a FunctionAgent with the given tools."""
    tools = await tools.to_tool_list_async()
    agent = FunctionAgent(
        name="Agent",
        description="An agent that can work with Our Database software.",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


async def handle_user_message(
    message_content: str,
    agent: FunctionAgent,
    agent_context: Context,
    verbose: bool = False,
):
    """Handle a user message using the agent."""
    handler = agent.run(message_content, ctx=agent_context)
    async for event in handler.stream_events():
        if verbose and type(event) is ToolCall:
            print(f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}")
        elif verbose and type(event) is ToolCallResult:
            print(f"Tool {event.tool_name} returned {event.tool_output}")

    response = await handler
    return str(response)


async def main():
    # Initialize MCP client and tool spec
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/mcp")
    mcp_tool = McpToolSpec(client=mcp_client)

    # Get the agent
    agent = await get_agent(mcp_tool)

    # Create the agent context
    agent_context = Context(agent)

    # Print available tools
    tools = await mcp_tool.to_tool_list_async()
    print("Available tools:")
    for tool in tools:
        print(f"{tool.metadata.name}: {tool.metadata.description}")

    # Main interaction loop
    print("\nEnter 'exit' to quit")
    while True:
        try:
            user_input = input("\nEnter your message: ")
            if user_input.lower() == "exit":
                break

            print(f"\nUser: {user_input}")
            response = await handle_user_message(
                user_input, agent, agent_context, verbose=True
            )
            print(f"Agent: {response}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
