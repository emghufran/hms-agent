# HMS Agent - AI Assistant Guide

## Project Overview

HMS Agent is a **multi-agent hotel management system** that enables hotel bookings through multiple interfaces:
- Web-based conversational voice interface (STT + TTS)
- Terminal-based agent with full reasoning capabilities
- MCP (Model Context Protocol) server exposing hotel management tools

**Key Technologies:**
- Python 3.13.2
- FastMCP for MCP server implementation
- **PydanticAI with Ollama (qwen2.5:14b)** for agent orchestration
- Faster-Whisper for speech-to-text
- Piper-TTS for text-to-speech
- SQLite for data persistence
- FastAPI for web services

## Architecture

This is a **Hub-and-Spoke** architecture:
- **Hub**: HMS database and MCP server (exposes tools)
- **Spokes**: Multiple agent clients (terminal agent, voice gateway)

```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Voice Gateway│  │ Terminal     │  │ MCP Client   │ │
│  │ (Web UI)     │  │ Agent        │  │ (Test)       │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │   MCP Server    │
                    │ (Port 8000)     │
                    │ /mcp endpoint   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Tool Layer     │
                    │ - Locations     │
                    │ - Hotels        │
                    │ - Rooms         │
                    │ - Customers     │
                    │ - Bookings      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   SQLite DB     │
                    │  bookings.db    │
                    └─────────────────┘
```

## Quick Start Commands

### 1. Database Setup
```bash
# Initialize database schema
uv run scripts/db_utils.py

# Populate with test data
uv run scripts/populate_db.py populate-hotels --num-locations 5 --num-hotels-per-location 2 --num-rooms-per-hotel 20
uv run scripts/populate_db.py populate-bookings --start-date 2026-01-01 --end-date 2026-12-31 --num-customers 100 --num-bookings 500
```

### 2. Running the System

**MCP Server** (required for all clients):
```bash
uv run uvicorn mcp_server:app --host 0.0.0.0 --port 8000 --reload --app-dir src/hms_agent
```

**Voice Gateway** (web UI with STT/TTS):
```bash
uv run src/hms_agent/voice_gateway.py
# Access at http://localhost:8001
```

**Terminal Agent** (CLI with full reasoning):
```bash
uv run src/hms_agent/agent.py
```

**Basic MCP Client** (testing):
```bash
uv run src/hms_agent/mcp_client.py --host 127.0.0.1 --port 8000
```

### 3. Testing
```bash
# Integration tests
uv run src/hms_agent/tests/test_mcp_server.py

# Tool verification
uv run src/hms_agent/tests/verify_tools.py
```

## Core Components

### 1. MCP Server ([src/hms_agent/mcp_server.py](src/hms_agent/mcp_server.py))
FastMCP server exposing 8 tools:
- `search_locations()` - List all available locations (cities/countries)
- `search_hotels(location_id?)` - List hotels, optionally filtered by location
- `search_rooms(hotel_id, check_in, check_out, min_capacity)` - Find available rooms
- `create_reservation(customer_id, room_id, check_in, check_out)` - Create booking
- `cancel_reservation(booking_id)` - Cancel existing booking
- `search_customers(name?, phone_number?)` - Lookup existing customers
- `create_customer_entry(name, phone_number)` - Register new customer

**Endpoint**: `http://localhost:8000/mcp` (HTTP-based MCP protocol)

### 2. Agent ([src/hms_agent/agent.py](src/hms_agent/agent.py))
**PydanticAI Agent** with strict booking workflow and qwen2.5:14b model:
1. Identify location → Find hotel → Check availability
2. **Customer identification** (search → create if not found)
3. Confirm booking

**Technical Stack**:
- Framework: PydanticAI 1.60.0
- Model: Ollama qwen2.5:14b (upgraded from llama3.2)
- MCP Integration: MCPServerStreamableHTTP
- State Management: Explicit message_history list

**Critical Rules**:
- NEVER guess/assume IDs (must come from tool outputs)
- NEVER invent dates (must ask user)
- HARD HALT on errors
- Privacy rule: Never reveal customer phone/ID back to user

### 3. Voice Gateway ([src/hms_agent/voice_gateway.py](src/hms_agent/voice_gateway.py))
FastAPI + WebSocket server for voice interaction:
- STT: Faster-Whisper (base model, CPU, int8)
- TTS: Piper (en_US-lessac-medium)
- WebSocket endpoint: `/ws/chat`
- Serves static UI at `/` (port 8001)
- Integrates with same agent as terminal version

**Audio Flow**:
1. Client sends Int16 PCM chunks via WebSocket
2. Accumulates until `end_audio` message
3. Transcribes with Whisper
4. Processes through agent
5. Synthesizes response with Piper
6. Returns both text and audio

### 4. Database Layer

**Connector** ([src/hms_agent/db/connector.py](src/hms_agent/db/connector.py)):
- Global DB path configuration
- SQLite connection factory with Row factory

**Models** ([src/hms_agent/db/models.py](src/hms_agent/db/models.py)):
- Pydantic models for all tool inputs/outputs
- Custom `DateStr` type with regex validation (YYYY-MM-DD)

**Schema** (managed by [scripts/db_utils.py](scripts/db_utils.py)):
- `locations` (city, country)
- `hotels` (name, location_id)
- `rooms` (hotel_id, room_number, room_type, price_per_night, capacity)
- `customers` (name, phone_number, created_at)
- `bookings` (customer_id, room_id, check_in_date, check_out_date, status)

### 5. Tools Layer ([src/hms_agent/tools/](src/hms_agent/tools/))
Each tool module handles specific domain:
- **locations.py**: Query locations
- **hotels.py**: Query hotels with optional filtering
- **rooms.py**: Complex availability check using date overlap logic
- **customers.py**: Search and create customer profiles
- **bookings.py**: Create/cancel bookings with conflict detection

**Pattern**: All tools follow:
```python
def tool_function(data: InputModel) -> List[OutputModel]:
    conn = get_connection()
    try:
        # SQL query
        # Map to Pydantic models
        return results
    finally:
        conn.close()
```

## Database Schema Details

### Date Overlap Logic (Critical for Availability)
Used in [rooms.py](src/hms_agent/tools/rooms.py:17-24) and [bookings.py](src/hms_agent/tools/bookings.py:12-23):

```sql
-- Room is NOT available if there exists a booking where:
NOT (check_out_date <= new_check_in OR check_in_date >= new_check_out)

-- Inverse: Room IS available when:
check_out_date <= new_check_in OR check_in_date >= new_check_out
```

This prevents double-booking by checking for any temporal overlap.

## Key Patterns & Conventions

### 1. Tool Naming Convention
MCP tools use descriptive names with prefixes:
- `search_*`: Query operations (read-only)
- `create_*`: Insert operations
- `cancel_*`: Delete/update operations

### 2. ID Requirement Pattern
All IDs must be obtained from previous tool outputs:
- Customer ID: from `search_customers` or `create_customer_entry`
- Room ID: from `search_rooms`
- Hotel ID: from `search_hotels`
- Location ID: from `search_locations`

Agent enforces this in system prompt (see [agent.py:30-31](src/hms_agent/agent.py:30-31))

### 3. Date Format
All dates: `YYYY-MM-DD` (enforced by `DateStr` type in models.py)

### 4. Error Handling
- Tools return `{"error": str}` on failure
- Agent MUST halt on error (no guessing workarounds)
- Database operations use try/finally for cleanup

### 5. Privacy Rule
Agent never reveals existing customer phone numbers or IDs to users (see [agent.py:25](src/hms_agent/agent.py:25))

## Development Workflow

### Adding a New Tool
1. Define Pydantic models in [db/models.py](src/hms_agent/db/models.py)
2. Implement tool function in [tools/](src/hms_agent/tools/)
3. Add MCP decorator in [mcp_server.py](src/hms_agent/mcp_server.py)
4. Update agent system prompt if workflow changes

### Modifying Database Schema
1. Update schema in [scripts/db_utils.py](scripts/db_utils.py)
2. Delete existing `bookings.db`
3. Re-run initialization scripts
4. Update Pydantic models if needed

### Testing Voice Interface
1. Ensure MCP server is running (port 8000)
2. Start voice gateway (port 8001)
3. Open browser to http://localhost:8001
4. Grant microphone permissions
5. Use 🎤 button or type messages

## Important Files

| File | Purpose | Lines |
|------|---------|-------|
| [mcp_server.py](src/hms_agent/mcp_server.py) | MCP server with 8 tools | 152 |
| [agent.py](src/hms_agent/agent.py) | LlamaIndex agent with strict workflow | 111 |
| [voice_gateway.py](src/hms_agent/voice_gateway.py) | WebSocket + STT/TTS server | 206 |
| [db/models.py](src/hms_agent/db/models.py) | Pydantic models for all I/O | 110 |
| [tools/bookings.py](src/hms_agent/tools/bookings.py) | Booking creation with conflict check | 83 |
| [tools/rooms.py](src/hms_agent/tools/rooms.py) | Availability search with date logic | 50 |
| [scripts/db_utils.py](scripts/db_utils.py) | Schema creation | - |
| [scripts/populate_db.py](scripts/populate_db.py) | Test data generation | - |

## Common Tasks

### How to: Debug Tool Execution
```bash
# Use verbose mode in agent
uv run src/hms_agent/agent.py
# Tool calls and responses are printed to console
```

### How to: Test MCP Tools Directly
```bash
# Use MCP client
uv run src/hms_agent/mcp_client.py --host 127.0.0.1 --port 8000
# Then call tools manually
```

### How to: Check Database Contents
```bash
sqlite3 bookings.db
.tables
SELECT * FROM locations;
SELECT * FROM hotels WHERE location_id = 1;
SELECT * FROM bookings WHERE status = 'confirmed';
```

### How to: Reset Database
```bash
rm bookings.db
uv run scripts/db_utils.py
uv run scripts/populate_db.py populate-hotels --num-locations 5 --num-hotels-per-location 2 --num-rooms-per-hotel 20
```

## Known Limitations

1. **Voice models are CPU-based**: Whisper base model + Piper TTS run on CPU (no GPU optimization yet)
2. **No authentication**: MCP server and voice gateway have no auth layer
3. **Single database**: All data in one SQLite file (no sharding/replication)
4. **No booking modifications**: Can only create or cancel, not modify existing bookings
5. **Voice UI is basic**: No interruption handling, simple chat interface
6. **Local LLM required**: Needs Ollama with llama3.2 model installed

## Future Enhancements (from project_plan.md)

### Planned Features
- **WhatsApp integration**: Twilio for text-based bookings
- **Phone call support**: Twilio Voice + WebSocket streaming
- **Advanced voice**: OpenAI Realtime API or Deepgram for better interruption handling
- **Production LLM**: Consider Groq for faster inference

### Architecture Goals
- All agents (web, WhatsApp, voice calls) use same MCP server
- Unified booking flow regardless of input modality
- State management across conversation turns

## Troubleshooting

### MCP Server Won't Start
- Check port 8000 is not in use: `lsof -i :8000`
- Verify database exists: `ls -l bookings.db`
- Check database path in mcp_server.py

### Voice Gateway Issues
- Ensure MCP server is running first
- Check Piper models downloaded: `ls src/hms_agent/models/`
- Check WebSocket connection in browser console
- Verify microphone permissions

### Agent Not Using Tools
- Check Ollama is running: `ollama list`
- Verify llama3.2 model installed: `ollama pull llama3.2`
- Check MCP server URL in agent.py (default: http://127.0.0.1:8000/mcp)

### Database Conflicts
- Ensure only one MCP server instance running
- Check for stale connections: restart MCP server
- Verify database not locked: close any open SQLite connections

## Code Style & Quality

### Current Setup
- Formatter: Ruff (configured in pyproject.toml)
- Python version: 3.13.2 (strict)
- Package manager: uv
- Testing: pytest (test files in src/hms_agent/tests/)

### Running Checks
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run tests
uv run pytest
```

## When Working on This Codebase

### Before Making Changes
1. Read relevant tool documentation in docstrings
2. Check agent system prompt for workflow constraints
3. Verify database schema matches your assumptions
4. Test with minimal data first

### After Making Changes
1. Run format/lint: `uv run ruff format . && uv run ruff check .`
2. Test MCP server: `uv run src/hms_agent/tests/test_mcp_server.py`
3. Test manually with agent: `uv run src/hms_agent/agent.py`
4. Verify voice gateway still works if you changed core logic

### Debugging Tips
- Enable verbose mode in agent to see tool calls
- Check MCP server logs for tool errors
- Use SQLite CLI to inspect database state
- Test tools in isolation before integration
