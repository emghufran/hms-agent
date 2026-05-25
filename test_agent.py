import asyncio
from src.hms_agent.agent import get_agent, handle_user_message

async def test():
    try:
        print("Testing PydanticAI agent...")
        agent = await get_agent()
        message_history = []

        # Test with a simple query
        response = await handle_user_message(
            "Show me available locations",
            agent,
            message_history,
            verbose=True
        )

        print(f"\nAgent Response: {response}")
        print("\n✅ Agent test successful!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
