import asyncio
import os
from datetime import date

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import ModelMessage

# MCP Server Configuration
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"

# Ollama Configuration
OLLAMA_BASE_URL = "http://localhost:11434/v1"  # Ollama OpenAI-compatible API
MODEL_NAME = "qwen2.5:14b"  # Upgraded from llama3.2 for better tool calling

# Set Ollama base URL environment variable (needs /v1 for OpenAI compatibility)
os.environ['OLLAMA_BASE_URL'] = OLLAMA_BASE_URL

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


async def get_agent() -> Agent:
    """Create and return configured PydanticAI agent with MCP tools."""
    # Connect to MCP server
    server = MCPServerStreamableHTTP(MCP_SERVER_URL)

    # Format system prompt with current date
    formatted_prompt = SYSTEM_PROMPT.format(current_date=date.today().isoformat())

    # Create agent with MCP toolset
    agent = Agent(
        f'ollama:{MODEL_NAME}',
        toolsets=[server],
        system_prompt=formatted_prompt,
        retries=2  # Handle occasional small model failures
    )

    return agent


async def handle_user_message(
    message_content: str,
    agent: Agent,
    message_history: list[ModelMessage],
    verbose: bool = False,
) -> str:
    """Handle a user message using the agent with conversation history.

    Args:
        message_content: The user's message text
        agent: The configured PydanticAI agent
        message_history: List of previous messages in the conversation
        verbose: If True, log tool calls and results

    Returns:
        The agent's response as a string
    """
    # Run agent with message history
    result = await agent.run(message_content, message_history=message_history)

    # Verbose logging - inspect new messages for tool calls
    if verbose:
        for msg in result.new_messages():
            # Check if this is a tool call or tool return
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    part_type = type(part).__name__
                    if part_type == 'ToolCallPart':
                        print(f"Calling tool {part.tool_name} with kwargs {part.args}")
                    elif part_type == 'ToolReturnPart':
                        print(f"Tool {part.tool_name} returned")

    # Update message history with new messages from this turn
    message_history.extend(result.new_messages())

    return str(result.output)


async def main():
    """Main entry point for the terminal agent."""
    # Get the agent
    agent = await get_agent()

    # Initialize message history
    message_history: list[ModelMessage] = []

    # Print available tools
    print("Hotel Booking Agent (PydanticAI + qwen2.5:14b)")
    print("=" * 50)
    print("\nEnter 'exit' to quit")

    # Main interaction loop
    while True:
        try:
            user_input = input("\nEnter your message: ")
            if user_input.lower() == "exit":
                break

            print(f"\nUser: {user_input}")
            response = await handle_user_message(
                user_input, agent, message_history, verbose=True
            )
            print(f"Agent: {response}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
