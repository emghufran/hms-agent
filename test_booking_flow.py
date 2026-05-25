import asyncio
from src.hms_agent.agent import get_agent, handle_user_message

async def test_booking_flow():
    """Test a complete booking workflow."""
    try:
        print("=" * 60)
        print("Testing Complete Booking Workflow")
        print("=" * 60)

        agent = await get_agent()
        message_history = []

        # Step 1: Ask for locations
        print("\n[STEP 1] User: Show me available locations in English")
        response = await handle_user_message(
            "Please respond in English only. Show me available locations",
            agent,
            message_history,
            verbose=True
        )
        print(f"Agent: {response}\n")

        # Step 2: Ask for hotels
        print("[STEP 2] User: Show me hotels in Paris")
        response = await handle_user_message(
            "Show me hotels in Paris",
            agent,
            message_history,
            verbose=True
        )
        print(f"Agent: {response}\n")

        print("\n" + "=" * 60)
        print("✅ Booking workflow test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_booking_flow())
