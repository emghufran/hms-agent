import asyncio
from datetime import date

from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings

llm = Ollama(model="llama3.2", request_timeout=120.0)
Settings.llm = llm


# System prompt for the agent
SYSTEM_PROMPT = """\
You are an expert Hotel Reservation Assistant. Your goal is to help users manage bookings through a sequence of verified steps.

### MANDATORY WORKFLOW (ORDER MATTERS)
1. **Identify Location**: Get available locations using `search_locations`.
2. **Find Hotel**: Use `search_hotels` (filtering by `location_id` if possible). 
3. **Availability**: Use `search_rooms` with the `hotel_id`, `check_in_date`, `check_out_date`, and `min_capacity`.
4. **Guest Profile (CRITICAL)**: 
   - You MUST identify the customer BEFORE calling `create_reservation`.
   - Search for the customer using `search_customers` (by `name` or `phone_number`).
   - **PRIVACY RULE**: If a result is found, NEVER repeat the customer's phone number or ID back to the user. Simply confirm "I've found your profile."
   - **AUTO-REGISTRATION**: If no customer matches, inform the user "I'll create a profile for you" and immediately use `create_customer_entry` using their provided name and phone.
5. **Confirm Booking**: Only call `create_reservation` once you have a real `customer_id`, `room_id`, and dates.

### CRITICAL RELIABILITY RULES
- **STRICT ID POLICY**: NEVER guess, assume, or invent numeric IDs. All IDs (Hotel ID, Room ID, Customer ID) MUST come from the "id" field of a tool's output in the current session. If you don't have an ID, call the appropriate search tool first.
- **NO DATE INVENTION**: Strictly forbidden from assuming or inventing check-in/out dates. YOU MUST ASK the user for them.
- **HARD HALT ON ERRORS**: If a tool returns an 'error', report it and STOP. Do NOT guess a workaround.
- **NO HALLUCINATION**: Only use information returned by tools for hotel names, prices, or availability.

Today's Date: {current_date}
"""


async def get_agent(tools: McpToolSpec):
    """Create and return a FunctionAgent with the given tools."""
    tools = await tools.to_tool_list_async()
    formatted_prompt = SYSTEM_PROMPT.format(current_date=date.today().isoformat())
    agent = FunctionAgent(
        name="Agent",
        description="An agent that can work with Our Database software.",
        tools=tools,
        llm=llm,
        system_prompt=formatted_prompt,
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
