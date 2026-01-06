# High-Level Architecture
You are essentially building a Hub-and-Spoke system. The "Hub" is the HMS (exposed via MCP), and the "Spokes" are your agents handling different modalities.

The Data Flow:

1. User: Interacts via WhatsApp (Text or Call).

2. Interface Layer: Twilio (or similar) handles the telephony and message routing.

3. Agent Layer:

    * Chat Agent: Processes text, handles context window, formats output for reading.

    * Voice Agent: Handles Speech-to-Text (STT), interruption logic, and Text-to-Speech (TTS).

4. Tooling Layer (MCP Client): Both agents connect to the same MCP Client.

5. Service Layer (MCP Server): A lightweight server that exposes the HMS functions (e.g., check_availability, create_booking).

6. Simulated HMS: A simple database (SQLite or PostgreSQL) representing rooms and guests.

# Component Breakdown
## The Simulated HMS & MCP Server
Instead of building a full frontend for the hotel, just build the backend logic and expose it.

* The Database: A simple SQL schema with tables for Rooms, Bookings, and Customers.

* The MCP Server: This is the core bridge. You will write a server (likely in Python or TypeScript) that implements the Model Context Protocol.

    * Tools to expose:

        * get_room_availability(start_date, end_date, room_type)

        * create_booking(customer_name, phone_number, room_id, dates)

        * cancel_booking(booking_id)

## The WhatsApp Chat Agent
This is the "text-based" receptionist.

* Tech Stack: Python (LangChain or LangGraph) + Twilio API for WhatsApp.

* Behavior: It needs to be precise. It should ask clarifying questions (e.g., "Do you need a sea view?").

* State Management: It must remember the user's name and dates throughout the conversation.

## The WhatsApp Voice Agent (The "Call" Agent)
This is the most complex part due to latency.

* Tech Stack: Twilio Voice + OpenAI Realtime API (or Deepgram for STT + ElevenLabs for TTS).

* Behavior: Needs to be concise. Voice output shouldn't read out a list of 10 room types; it should summarize (e.g., "I have a suite and a standard room available").

* Challenge: Handling "barge-in" (when the user interrupts the bot). The OpenAI Realtime API is currently the gold standard for this.

## Implementation Roadmap
### Phase 1: The "Brain" (HMS + MCP)

Build the simulated hotel system and the MCP server first.

1. Create a bookings.db (SQLite).

1. Write Python functions to query/update this DB.

1. Wrap these functions in an MCP Server.

1. Milestone: You can use an MCP debugger (like the Claude Desktop app or MCP Inspector) to "chat" with your database manually.

### Phase 2: The Text Agent
Connect the MCP server to a chatbot.

1. Set up a Twilio Sandbox for WhatsApp.

1. Create a LangGraph agent that uses the MCP client as a tool.

1. Implement the logic: Receive Webhook -> Agent Processes -> Agent Calls MCP -> Agent Replies.

1. Milestone: You can text the bot on WhatsApp and book a room.

### Phase 3: The Voice Agent
Add the voice layer.

1. Set up a Twilio Voice number.

1. Use a stream (WebSocket) to connect the call audio to the AI model.

1. Give the Voice Agent access to the same MCP client used in Phase 2.

1. Milestone: You can call the number, talk to the agent, and the booking appears in the same database as the text agent.

## Technical choices for different AI components:
* Logic: Llama 3.2 3B hosted on Groq (Blazing fast inference, crucial for voice).

* Voice: Deepgram (for both STT and TTS).

* Orchestrator: Python code on your laptop.