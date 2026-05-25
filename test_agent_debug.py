import asyncio
from src.hms_agent.agent import get_agent

async def test():
    try:
        print("Testing PydanticAI agent...")
        agent = await get_agent()

        # Test with a simple query
        result = await agent.run("Show me available locations")

        print(f"\nResult type: {type(result)}")
        print(f"Result attributes: {dir(result)}")
        print(f"\nOutput: {result.output}")

        # Try to get new messages
        if hasattr(result, 'new_messages'):
            if callable(result.new_messages):
                msgs = result.new_messages()
                print(f"\nNew messages (via method): {msgs}")
            else:
                print(f"\nNew messages (attribute): {result.new_messages}")

        print("\n✅ Agent test successful!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
