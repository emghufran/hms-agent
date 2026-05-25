# HMS Agent - Codebase Index

Complete reference of all files in the project with descriptions and key functions.

## Table of Contents
- [Root Configuration Files](#root-configuration-files)
- [Source Code](#source-code)
  - [Main Application Files](#main-application-files)
  - [Database Layer](#database-layer)
  - [Tools Layer](#tools-layer)
  - [Tests](#tests)
  - [Web UI](#web-ui)
- [Scripts](#scripts)
- [Database](#database)
- [Documentation](#documentation)

---

## Root Configuration Files

### [pyproject.toml](pyproject.toml)
**Purpose**: Python project configuration and dependency management
**Key Contents**:
- Project metadata (name, version, authors)
- Dependencies with exact versions
- Python version requirement: 3.13.2
- Build system: hatchling
- Dev dependencies: ruff, pytest
- Test configuration

**Important Dependencies**:
- `fastmcp>=2.14.2` - MCP server framework
- `llama-index>=0.14.12` - Agent orchestration
- `llama-index-llms-ollama>=0.9.1` - Ollama integration
- `faster-whisper>=1.2.1` - Speech-to-text
- `piper-tts>=1.3.0` - Text-to-speech
- `fastapi>=0.128.0` - Web framework
- `SQLAlchemy==2.0.45` - ORM (though raw SQL is used)

### [README.md](README.md)
**Purpose**: User-facing documentation
**Contents**:
- Database setup instructions
- How to run each component
- Testing commands
- Quick start guide

### [project_plan.md](project_plan.md)
**Purpose**: Original architecture and implementation plan
**Contents**:
- High-level architecture explanation (Hub-and-Spoke)
- Component breakdown
- Implementation roadmap (3 phases)
- Technical choices and rationale

### [.gitignore](.gitignore)
**Purpose**: Git exclusions
**Excludes**:
- `__pycache__/`, `*.pyc`
- `.venv/`
- `bookings.db` (local database)
- `.ruff_cache/`

### [uv.lock](uv.lock)
**Purpose**: Locked dependency versions (managed by uv package manager)

---

## Source Code

### Main Application Files

#### [src/hms_agent/__init__.py](src/hms_agent/__init__.py)
**Purpose**: Package initialization (currently empty)

#### [src/hms_agent/mcp_server.py](src/hms_agent/mcp_server.py) ⭐
**Purpose**: FastMCP server exposing hotel management tools via HTTP
**Lines**: 152
**Run**: `uvicorn mcp_server:app --host 0.0.0.0 --port 8000 --app-dir src/hms_agent`

**Exports**:
- `app` - FastAPI application instance

**MCP Tools** (8 total):
1. `search_locations()` → List all locations
2. `search_hotels(location_id?)` → List hotels (optionally filtered)
3. `search_rooms(hotel_id, check_in, check_out, min_capacity)` → Find available rooms
4. `create_reservation(customer_id, room_id, check_in, check_out)` → Book room
5. `cancel_reservation(booking_id)` → Cancel booking
6. `search_customers(name?, phone_number?)` → Find customers
7. `create_customer_entry(name, phone_number)` → Register new customer

**Key Details**:
- Endpoint: `/mcp` (HTTP-based MCP protocol)
- Database path: `../../bookings.db` (relative to this file)
- All tools return JSON with error handling
- Tools use Pydantic models for validation

**Dependencies**:
```python
from fastmcp import FastMCP
from db.models import *  # All Pydantic models
from db.connector import set_db_path
from tools import *  # All tool implementations
```

---

#### [src/hms_agent/agent.py](src/hms_agent/agent.py) ⭐
**Purpose**: LlamaIndex FunctionAgent with hotel booking workflow
**Lines**: 111
**Run**: `uv run src/hms_agent/agent.py`

**Key Functions**:
- `get_agent(tools: McpToolSpec)` → Create FunctionAgent with system prompt
- `handle_user_message(message, agent, context, verbose)` → Process user input through agent
- `main()` → CLI interaction loop

**System Prompt** (lines 15-36):
- Mandatory workflow: Location → Hotel → Rooms → Customer → Booking
- Critical reliability rules:
  - STRICT ID POLICY: Never guess IDs
  - NO DATE INVENTION: Must ask user
  - HARD HALT ON ERRORS: No workarounds
  - PRIVACY RULE: Never reveal customer phone/ID

**Configuration**:
- LLM: Ollama llama3.2
- Request timeout: 120s
- MCP Server: http://127.0.0.1:8000/mcp

**Event Types**:
- `ToolCall` - When agent calls a tool
- `ToolCallResult` - Tool execution result
- Final response from agent

---

#### [src/hms_agent/voice_gateway.py](src/hms_agent/voice_gateway.py) ⭐
**Purpose**: WebSocket server for conversational voice interface
**Lines**: 206
**Run**: `uv run src/hms_agent/voice_gateway.py` → http://localhost:8001

**Key Functions**:
- `ensure_models()` → Download Piper TTS models from HuggingFace
- `synthesize_speech(text)` → Convert text to WAV audio
- `websocket_endpoint(websocket)` → Handle WebSocket connections
- `get()` → Serve HTML UI
- `lifespan(app)` → Startup/shutdown hooks

**WebSocket Protocol**:
- Endpoint: `/ws/chat`
- Accepts: Int16 PCM audio chunks OR text messages
- Returns: JSON messages + binary audio

**Message Types**:
```json
// Client → Server
{"type": "end_audio"}  // Trigger transcription
"<text message>"       // Direct text input

// Server → Client
{"type": "transcription", "content": "..."}
{"type": "text", "content": "..."}
<binary audio data>  // WAV file bytes
```

**Audio Processing**:
1. Accumulate Int16 PCM chunks in buffer
2. On `end_audio`: Transcribe with Whisper
3. Process through agent
4. Synthesize response with Piper
5. Send text + audio back

**Models**:
- STT: Faster-Whisper "base" (CPU, int8)
- TTS: Piper en_US-lessac-medium
- Model storage: `src/hms_agent/models/`

**Configuration**:
- Port: 8001
- MCP Server URL: http://127.0.0.1:8000/mcp
- Static files: `src/hms_agent/web/`

---

#### [src/hms_agent/mcp_client.py](src/hms_agent/mcp_client.py)
**Purpose**: Basic MCP client for testing tool connectivity
**Lines**: ~50 (estimated)
**Run**: `uv run src/hms_agent/mcp_client.py --host 127.0.0.1 --port 8000`

**Usage**: Minimal client to verify MCP server is responding correctly

---

### Database Layer

#### [src/hms_agent/db/connector.py](src/hms_agent/db/connector.py)
**Purpose**: Database connection management
**Lines**: 18

**Functions**:
- `set_db_path(path: str)` → Configure global DB path
- `get_connection()` → Return SQLite connection with Row factory

**Pattern**:
```python
# In mcp_server.py
set_db_path("/path/to/bookings.db")

# In tool functions
conn = get_connection()
try:
    # Use connection
finally:
    conn.close()
```

**Key Detail**: Uses `sqlite3.Row` factory for dict-like row access

---

#### [src/hms_agent/db/models.py](src/hms_agent/db/models.py) ⭐
**Purpose**: Pydantic models for all MCP tool inputs/outputs
**Lines**: 110

**Custom Types**:
- `DateStr` - Annotated string with regex `^\d{4}-\d{2}-\d{2}$`

**Input Models**:
- `HotelsInput(location_id?)` - For search_hotels
- `SearchRoomsInput(hotel_id, check_in, check_out, min_capacity)` - For search_rooms
- `CreateBookingInput(customer_id, room_id, check_in, check_out)` - For create_reservation
- `CancelBookingInput(booking_id)` - For cancel_reservation
- `CustomerSearchInput(name?, phone_number?)` - For search_customers
- `CustomerCreateInput(name, phone_number)` - For create_customer_entry

**Output Models**:
- `LocationsOutput(id, city, country)`
- `HotelsOutput(id, name)`
- `RoomOutput(id, room_number, room_type, price_per_night, capacity)`
- `BookingOutput(booking_id, status: Literal["confirmed"])`
- `CustomerOutput(id, name, phone_number)`

**Validation**:
- All IDs: `gt=0` (greater than 0)
- Dates: Regex pattern validation
- Strings: `min_length` constraints
- Examples provided for documentation

---

### Tools Layer

All tools follow this pattern:
```python
def tool_function(data: InputModel) -> List[OutputModel]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SQL QUERY", params)
        rows = cur.fetchall()
        return [OutputModel(**row) for row in rows]
    finally:
        conn.close()
```

#### [src/hms_agent/tools/locations.py](src/hms_agent/tools/locations.py)
**Purpose**: Query available locations
**Lines**: ~30 (estimated)

**Function**:
- `get_locations()` → List[LocationsOutput]

**SQL**:
```sql
SELECT id, city, country FROM locations
```

---

#### [src/hms_agent/tools/hotels.py](src/hms_agent/tools/hotels.py)
**Purpose**: Query hotels with optional location filter
**Lines**: ~40 (estimated)

**Function**:
- `get_hotels(data: HotelsInput)` → List[HotelsOutput]

**SQL**:
```sql
-- If location_id provided:
SELECT id, name FROM hotels WHERE location_id = ?

-- Otherwise:
SELECT id, name FROM hotels
```

---

#### [src/hms_agent/tools/rooms.py](src/hms_agent/tools/rooms.py) ⭐
**Purpose**: Find available rooms with complex date logic
**Lines**: 50

**Function**:
- `get_available_rooms(data: SearchRoomsInput)` → List[RoomOutput]

**SQL** (critical date overlap logic):
```sql
SELECT r.*
FROM rooms r
WHERE r.hotel_id = ?
  AND r.capacity >= ?
  AND r.id NOT IN (
    SELECT room_id FROM bookings
    WHERE status = 'confirmed'
      AND NOT (
        check_out_date <= ?      -- New check-in
        OR check_in_date >= ?    -- New check-out
      )
  )
```

**Logic**: A room is unavailable if there exists a booking that overlaps with the requested dates. The overlap check uses De Morgan's law.

---

#### [src/hms_agent/tools/customers.py](src/hms_agent/tools/customers.py)
**Purpose**: Customer search and creation
**Lines**: ~60 (estimated)

**Functions**:
- `get_customer(data: CustomerSearchInput)` → List[CustomerOutput]
- `create_customer(data: CustomerCreateInput)` → CustomerOutput

**Search SQL**:
```sql
-- Builds dynamic WHERE clause based on provided filters
SELECT id, name, phone_number FROM customers
WHERE name LIKE ? OR phone_number = ?
```

**Create SQL**:
```sql
INSERT INTO customers (name, phone_number, created_at)
VALUES (?, ?, datetime('now'))
```

---

#### [src/hms_agent/tools/bookings.py](src/hms_agent/tools/bookings.py) ⭐
**Purpose**: Booking creation and cancellation with conflict detection
**Lines**: 83

**Functions**:
- `create_booking(data: CreateBookingInput)` → BookingOutput
- `cancel_booking(data: CancelBookingInput)` → None

**Create Logic**:
1. Check for date conflicts (same logic as rooms.py)
2. If conflict exists: raise ValueError
3. Insert booking with status='confirmed'
4. Return booking_id

**Create SQL**:
```sql
-- 1. Conflict check
SELECT 1 FROM bookings
WHERE room_id = ?
  AND status = 'confirmed'
  AND NOT (
    check_out_date <= ?
    OR check_in_date >= ?
  )

-- 2. Insert if no conflict
INSERT INTO bookings (customer_id, room_id, check_in_date, check_out_date, status)
VALUES (?, ?, ?, ?, 'confirmed')
```

**Cancel SQL**:
```sql
UPDATE bookings
SET status = 'cancelled'
WHERE id = ?
```

**Error Handling**:
- Uses try/except with rollback
- Raises ValueError for user errors
- Generic Exception for system errors

---

### Tests

#### [src/hms_agent/tests/test_mcp_server.py](src/hms_agent/tests/test_mcp_server.py)
**Purpose**: Integration test for complete booking flow
**Run**: `uv run src/hms_agent/tests/test_mcp_server.py`

**Test Flow**:
1. Check room availability
2. Create a booking
3. Cancel the booking
4. Verify all steps succeeded

**Requirements**: MCP server must be running on port 8000

---

#### [src/hms_agent/tests/verify_tools.py](src/hms_agent/tests/verify_tools.py)
**Purpose**: Tool verification and data consistency checks
**Run**: `uv run src/hms_agent/tests/verify_tools.py`

**Checks**:
- Each tool returns expected data format
- Database constraints are enforced
- Date validation works correctly

---

### Web UI

#### [src/hms_agent/web/script.js](src/hms_agent/web/script.js)
**Purpose**: Frontend JavaScript for voice interface
**Lines**: ~200 (estimated)

**Key Functions**:
- WebSocket connection management
- Audio recording from microphone
- Audio playback from server
- Chat message rendering
- Microphone button toggle

**WebSocket Events**:
```javascript
ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    // Audio response - play it
  } else {
    // JSON message - display in chat
  }
}
```

**Audio Capture**:
- Uses MediaRecorder API
- Records in PCM format
- Sends Int16 chunks to server
- Signals end with `{"type": "end_audio"}`

---

#### [src/hms_agent/web/style.css](src/hms_agent/web/style.css)
**Purpose**: UI styling for voice interface
**Lines**: ~150 (estimated)

**Design**:
- Clean chat interface
- Microphone button with visual feedback
- Status indicator dot
- Responsive layout
- Message bubbles (user vs assistant)

---

## Scripts

#### [scripts/db_utils.py](scripts/db_utils.py)
**Purpose**: Database schema creation and initialization
**Run**: `uv run scripts/db_utils.py`

**Creates Tables**:
- `locations(id, city, country)`
- `hotels(id, name, location_id)`
- `rooms(id, hotel_id, room_number, room_type, price_per_night, capacity)`
- `customers(id, name, phone_number, created_at)`
- `bookings(id, customer_id, room_id, check_in_date, check_out_date, status)`

**Foreign Keys**:
- hotels.location_id → locations.id
- rooms.hotel_id → hotels.id
- bookings.customer_id → customers.id
- bookings.room_id → rooms.id

**Indexes**:
- bookings(room_id, check_in_date, check_out_date) - For fast availability checks
- customers(phone_number) - For customer lookup

---

#### [scripts/populate_db.py](scripts/populate_db.py)
**Purpose**: Generate test data using Faker
**Run**:
```bash
# Hotels and rooms
uv run scripts/populate_db.py populate-hotels --num-locations 5 --num-hotels-per-location 2 --num-rooms-per-hotel 20

# Bookings
uv run scripts/populate_db.py populate-bookings --start-date 2026-01-01 --end-date 2026-12-31 --num-customers 100 --num-bookings 500
```

**Subcommands**:
- `populate-hotels` - Create locations, hotels, and rooms
- `populate-bookings` - Create customers and bookings

**Data Generation**:
- Uses Faker for realistic names, cities, countries, phone numbers
- Random room types: Standard, Deluxe, Suite, Family, Presidential
- Random prices: 50-500 per night
- Random capacities: 1-6 people
- Booking dates within specified range
- Avoids creating conflicting bookings

---

## Database

### [bookings.db](bookings.db)
**Purpose**: SQLite database file (not checked into git)
**Size**: ~85KB (with test data)
**Location**: Project root

**Schema Version**: See [scripts/db_utils.py](scripts/db_utils.py)

**Tables**: 5 (locations, hotels, rooms, customers, bookings)

**Access**:
```bash
sqlite3 bookings.db
.tables
.schema bookings
SELECT * FROM hotels LIMIT 10;
```

---

## Documentation

### [CLAUDE.md](CLAUDE.md) ⭐ (This File)
**Purpose**: AI assistant guide to the codebase
**Contents**:
- Project overview
- Architecture diagrams
- Quick start commands
- Component explanations
- Common tasks
- Troubleshooting

### [CODEBASE_INDEX.md](CODEBASE_INDEX.md) ⭐ (You Are Here)
**Purpose**: Complete file reference
**Contents**:
- Every file documented
- Key functions listed
- Line counts and purposes
- SQL queries explained

### [project_plan.md](project_plan.md)
**Purpose**: Original design document
**Contents**:
- Architecture rationale
- Implementation phases
- Future roadmap

---

## Directory Structure Summary

```
hms-agent/
├── .git/                    # Git repository
├── .github/                 # GitHub configuration
├── .venv/                   # Virtual environment (not committed)
├── scripts/                 # Database utilities
│   ├── db_utils.py         # Schema creation
│   └── populate_db.py      # Test data generation
├── src/
│   └── hms_agent/          # Main package
│       ├── __init__.py
│       ├── agent.py        # Terminal agent (LlamaIndex)
│       ├── mcp_server.py   # MCP server (FastMCP)
│       ├── mcp_client.py   # Test client
│       ├── voice_gateway.py # Voice WebSocket server
│       ├── db/             # Database layer
│       │   ├── connector.py
│       │   └── models.py
│       ├── tools/          # MCP tool implementations
│       │   ├── bookings.py
│       │   ├── customers.py
│       │   ├── hotels.py
│       │   ├── locations.py
│       │   └── rooms.py
│       ├── tests/          # Test files
│       │   ├── test_mcp_server.py
│       │   └── verify_tools.py
│       ├── web/            # Frontend assets
│       │   ├── script.js
│       │   └── style.css
│       └── models/         # Downloaded AI models
│           └── en_US-lessac-medium.onnx*
├── bookings.db             # SQLite database (gitignored)
├── pyproject.toml          # Project config
├── uv.lock                 # Locked dependencies
├── README.md               # User documentation
├── project_plan.md         # Design document
├── CLAUDE.md               # AI assistant guide
└── CODEBASE_INDEX.md       # This file
```

---

## File Count Summary

| Category | Count | Files |
|----------|-------|-------|
| **Core Application** | 4 | mcp_server.py, agent.py, voice_gateway.py, mcp_client.py |
| **Database Layer** | 2 | connector.py, models.py |
| **Tools** | 5 | bookings.py, customers.py, hotels.py, locations.py, rooms.py |
| **Tests** | 2 | test_mcp_server.py, verify_tools.py |
| **Scripts** | 2 | db_utils.py, populate_db.py |
| **Web UI** | 2 | script.js, style.css |
| **Config** | 2 | pyproject.toml, .gitignore |
| **Documentation** | 4 | README.md, CLAUDE.md, CODEBASE_INDEX.md, project_plan.md |
| **Total** | 23 | (excluding auto-generated files) |

---

## Lines of Code (Estimated)

| Component | Lines |
|-----------|-------|
| mcp_server.py | 152 |
| agent.py | 111 |
| voice_gateway.py | 206 |
| db/models.py | 110 |
| tools/bookings.py | 83 |
| tools/rooms.py | 50 |
| Other tools | ~150 |
| Scripts | ~300 |
| Tests | ~200 |
| Web UI | ~350 |
| **Total** | ~1,712 |

---

## Key Entry Points

| Interface | Entry Point | Port |
|-----------|-------------|------|
| **MCP Server** | [src/hms_agent/mcp_server.py](src/hms_agent/mcp_server.py) | 8000 |
| **Voice Web UI** | [src/hms_agent/voice_gateway.py](src/hms_agent/voice_gateway.py) | 8001 |
| **Terminal Agent** | [src/hms_agent/agent.py](src/hms_agent/agent.py) | - |
| **MCP Test Client** | [src/hms_agent/mcp_client.py](src/hms_agent/mcp_client.py) | - |

---

## Most Important Files to Understand

For developers new to the codebase, start with these files in order:

1. **[CLAUDE.md](CLAUDE.md)** - Overview and architecture
2. **[db/models.py](src/hms_agent/db/models.py)** - Data structures
3. **[mcp_server.py](src/hms_agent/mcp_server.py)** - API layer
4. **[agent.py](src/hms_agent/agent.py)** - Business logic and workflow
5. **[tools/rooms.py](src/hms_agent/tools/rooms.py)** - Complex availability logic
6. **[tools/bookings.py](src/hms_agent/tools/bookings.py)** - Critical booking logic
7. **[voice_gateway.py](src/hms_agent/voice_gateway.py)** - Voice interface (optional)

---

## Dependencies Between Files

```
mcp_server.py
├── db/models.py (all models)
├── db/connector.py (set_db_path)
├── tools/locations.py (get_locations)
├── tools/hotels.py (get_hotels)
├── tools/rooms.py (get_available_rooms)
├── tools/customers.py (get_customer, create_customer)
└── tools/bookings.py (create_booking, cancel_booking)

agent.py
└── (connects to mcp_server.py via HTTP)

voice_gateway.py
├── agent.py (get_agent, handle_user_message)
└── (connects to mcp_server.py via HTTP)

All tools/*
├── db/connector.py (get_connection)
└── db/models.py (specific models)
```

---

## Recent Changes (from Git History)

- `69712fa` - Adding voice support
- `af41c0a` - Fix linting and formatting
- `4bc3b8d` - Updated tools and the agent
- `c02c6ba` - Code refactoring
- `bc0aa0f` - Adding new tools

**Current Branch**: `feat-conversational-voice`
**Main Branch**: `main`

---

## What's Missing / Not Yet Implemented

Based on [project_plan.md](project_plan.md), these features are planned but not yet implemented:

1. **WhatsApp Integration** (Twilio Text API)
2. **Phone Call Support** (Twilio Voice + WebSocket)
3. **Advanced Interruption Handling** (OpenAI Realtime API)
4. **Production LLM** (Groq for faster inference)
5. **Booking Modifications** (only create/cancel currently)
6. **User Authentication**
7. **Multi-tenancy** (all bookings in one DB)
8. **Payment Processing**
9. **Email Confirmations**
10. **Admin Dashboard**

---

This index should be updated whenever:
- New files are added
- Significant refactoring occurs
- New features are implemented
- API changes are made
