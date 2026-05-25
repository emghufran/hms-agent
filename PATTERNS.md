# HMS Agent - Patterns & Conventions

This document captures architectural patterns, coding conventions, and design decisions used throughout the HMS Agent codebase. Follow these patterns when adding new features or modifying existing code.

## Table of Contents
- [Architectural Patterns](#architectural-patterns)
- [Code Organization](#code-organization)
- [Database Patterns](#database-patterns)
- [Error Handling](#error-handling)
- [Validation & Type Safety](#validation--type-safety)
- [Naming Conventions](#naming-conventions)
- [Agent Behavior Patterns](#agent-behavior-patterns)
- [Testing Patterns](#testing-patterns)
- [Best Practices](#best-practices)

---

## Architectural Patterns

### Hub-and-Spoke Architecture

**Pattern**: Single source of truth (MCP Server) with multiple client interfaces
```
Voice Gateway (Web)  ──┐
Terminal Agent       ──┼──> MCP Server ──> Database
MCP Test Client      ──┘
```

**Why**:
- Separates business logic from interface concerns
- Allows adding new interfaces without duplicating logic
- Makes testing easier (test tools independently)

**When to use**:
- When adding new client types (WhatsApp, phone, mobile app)
- All clients should go through MCP server, never directly to DB

### MCP (Model Context Protocol) Pattern

**Pattern**: Expose tools via standardized protocol
```python
@mcp.tool()
def tool_name(param: Type) -> ReturnType:
    """
    Clear description of what this tool does.
    Include important constraints or requirements.
    """
    try:
        # Validate input (Pydantic handles this)
        # Execute logic
        return result
    except Exception as e:
        return {"error": str(e)}
```

**Key Principles**:
1. Each tool does ONE thing
2. Tools are stateless (no session data)
3. Tools return structured data (Pydantic models)
4. Errors are returned as JSON, not raised

**Example** (from [mcp_server.py:60-80](src/hms_agent/mcp_server.py:60-80)):
```python
@mcp.tool()
def search_rooms(hotel_id: int, check_in_date: str, check_out_date: str, min_capacity: int):
    """
    Search for available rooms in a specific hotel for a given date range and capacity.
    Returns a list of rooms with their ID, type, and nightly price.
    Note: Always confirm the room type and price with the user before booking.
    Dates must be in YYYY-MM-DD format.
    """
    try:
        data = SearchRoomsInput(...)
        rooms = get_available_rooms(data)
        return {"rooms": [room.model_dump() for room in rooms]}
    except Exception as e:
        return {"error": str(e), "rooms": []}
```

**Anti-patterns** (AVOID):
```python
# ❌ Stateful tool (stores data between calls)
@mcp.tool()
def remember_preference(user_id: int, preference: str):
    SESSION_DATA[user_id] = preference  # NO!

# ❌ Tool does multiple things
@mcp.tool()
def search_and_book_room(...):
    # Search + Book in one tool - violates single responsibility

# ❌ Raising exceptions instead of returning errors
@mcp.tool()
def bad_tool(...):
    if error:
        raise ValueError("error")  # Should return {"error": "..."}
```

---

## Code Organization

### Layer Separation

**Database Layer** (`src/hms_agent/db/`)
- `connector.py`: Connection management only
- `models.py`: Pydantic models only (no business logic)

**Tools Layer** (`src/hms_agent/tools/`)
- Each tool in separate file
- Imports from db layer only
- Pure functions (no state)

**Application Layer** (`src/hms_agent/`)
- `mcp_server.py`: MCP tool registration
- `agent.py`: Agent orchestration
- `voice_gateway.py`: Voice interface

**Scripts** (`scripts/`)
- Database utilities (schema, population)
- Not imported by application code

**Tests** (`src/hms_agent/tests/`)
- Integration tests
- Tool verification

**Pattern**:
```
Application Layer
    ↓ calls
MCP Server Layer
    ↓ calls
Tools Layer
    ↓ uses
Database Layer (models + connector)
    ↓ queries
SQLite Database
```

**Rule**: Lower layers never import from higher layers

---

## Database Patterns

### Connection Management

**Pattern**: Global DB path + connection factory
```python
# At application startup (mcp_server.py)
from db.connector import set_db_path
set_db_path(DB_PATH)

# In tool functions
from db.connector import get_connection

def tool_function(...):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Use connection
    finally:
        conn.close()  # Always close
```

**Why**:
- Single point of configuration
- No connection pooling needed (SQLite + single-process)
- Explicit cleanup prevents locks

**Anti-pattern**:
```python
# ❌ Hard-coded path in tool
def bad_tool():
    conn = sqlite3.connect("bookings.db")  # NO!
```

### Date Overlap Logic

**Pattern**: Detect booking conflicts using temporal logic
```sql
-- A booking conflicts if it overlaps with the requested dates
-- Overlap occurs when booking does NOT end before request starts
-- AND booking does NOT start after request ends

WHERE NOT (
    existing_checkout <= new_checkin
    OR existing_checkin >= new_checkout
)
```

**Used in**:
- [tools/rooms.py:17-24](src/hms_agent/tools/rooms.py:17-24) - Availability check
- [tools/bookings.py:12-23](src/hms_agent/tools/bookings.py:12-23) - Conflict prevention

**Visualization**:
```
Timeline:
    [--- Request ---]
[End] [Start]               Case 1: existing_checkout <= new_checkin (No overlap)
                [Start] [End]   Case 2: existing_checkin >= new_checkout (No overlap)
    [--- Overlap ---]       Case 3: Neither condition true (CONFLICT!)
```

**Implementation** (from [tools/rooms.py](src/hms_agent/tools/rooms.py)):
```python
cur.execute(
    """
    SELECT r.*
    FROM rooms r
    WHERE r.hotel_id = ?
      AND r.capacity >= ?
      AND r.id NOT IN (
        SELECT room_id FROM bookings
        WHERE status = 'confirmed'
          AND NOT (
            check_out_date <= ?      -- Request check-in
            OR check_in_date >= ?    -- Request check-out
          )
      )
    """,
    (hotel_id, min_capacity, check_in_date, check_out_date)
)
```

**When to use**: Any feature involving date ranges (reservations, availability, occupancy reports)

### Transaction Pattern

**Pattern**: Explicit transaction with rollback on error
```python
def create_booking(data: CreateBookingInput) -> BookingOutput:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Check constraints
        cur.execute("SELECT ...")
        if conflict:
            raise ValueError("User-facing error message")

        # 2. Perform mutation
        cur.execute("INSERT ...")

        # 3. Commit
        conn.commit()

        # 4. Return result
        return BookingOutput(...)
    except Exception:
        if conn:
            conn.rollback()  # Undo changes
        raise  # Re-raise for caller to handle
    finally:
        if conn:
            conn.close()  # Always cleanup
```

**When to use**: Any write operation (INSERT, UPDATE, DELETE)

**Why**:
- Ensures data consistency
- Prevents partial writes
- Clear error recovery path

---

## Error Handling

### Three-Tier Error Strategy

**Layer 1: Tool Functions** (tools/*.py)
```python
def tool_function(data: Input) -> Output:
    try:
        # Business logic
        return result
    except ValueError as e:
        # User errors (bad input, conflicts)
        raise  # Let MCP layer handle
    except Exception as e:
        # System errors (DB issues, etc)
        raise  # Let MCP layer handle
```

**Layer 2: MCP Server** (mcp_server.py)
```python
@mcp.tool()
def mcp_tool(...):
    try:
        result = tool_function(data)
        return result.model_dump()
    except ValueError as e:
        return {"error": str(e)}  # User-facing error
    except Exception as e:
        return {"error": f"Failed to ...: {str(e)}"}  # System error
```

**Layer 3: Agent** (agent.py)
```python
# In system prompt:
"""
CRITICAL RELIABILITY RULES:
- HARD HALT ON ERRORS: If a tool returns an 'error', report it and STOP.
  Do NOT guess a workaround.
"""
```

**Error Types**:
- `ValueError`: User errors (room unavailable, booking not found, invalid dates)
- `Exception`: System errors (DB connection failed, file I/O error)

**Example** (from [tools/bookings.py:25-26](src/hms_agent/tools/bookings.py:25-26)):
```python
if cur.fetchone():
    raise ValueError("Room is not available for selected dates")
```

**Anti-pattern**:
```python
# ❌ Silent failure
def bad_tool():
    try:
        result = risky_operation()
    except:
        return []  # Lost error information!

# ❌ Generic error message
except Exception:
    return {"error": "Something went wrong"}  # Not helpful!
```

---

## Validation & Type Safety

### Pydantic Input Validation

**Pattern**: Define input models with constraints
```python
from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated

DateStr = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
]

class CreateBookingInput(BaseModel):
    customer_id: int = Field(
        ...,  # Required
        gt=0,  # Greater than 0
        description="The ID of the customer. MUST be obtained from search_customers or create_customer_entry first.",
    )
    room_id: int = Field(..., gt=0, description="...")
    check_in_date: DateStr
    check_out_date: DateStr
```

**Benefits**:
- Automatic validation (no manual checks)
- Self-documenting (Field descriptions)
- Type safety (IDE autocomplete)
- Examples for docs/testing

**When to use**: Every MCP tool input/output

### Type Annotations

**Pattern**: Always annotate function signatures
```python
from typing import List

def get_available_rooms(data: SearchRoomsInput) -> List[RoomOutput]:
    ...
```

**Why**:
- Catches type errors early
- Enables IDE autocomplete
- Makes code self-documenting

**Rule**: All public functions must have type annotations

---

## Naming Conventions

### MCP Tool Names

**Pattern**: `<verb>_<noun>` format
- `search_*`: Read operations (queries)
- `create_*`: Write operations (inserts)
- `cancel_*`: Delete/update operations
- `get_*`: Retrieve single item
- `list_*`: Retrieve multiple items

**Examples**:
- ✅ `search_rooms(...)` - Query available rooms
- ✅ `create_reservation(...)` - Create booking
- ✅ `cancel_reservation(...)` - Cancel booking
- ❌ `rooms(...)` - Unclear action
- ❌ `book_room(...)` - Use `create_reservation`

### Python Functions & Variables

**Pattern**: snake_case for all Python code
```python
# Functions
def get_available_rooms(...): ...
def create_customer(...): ...

# Variables
check_in_date = "2026-01-01"
mcp_server_url = "http://localhost:8000/mcp"

# Constants
MCP_SERVER_URL = "http://localhost:8000/mcp"
DEFAULT_TIMEOUT = 120
```

### File Names

**Pattern**:
- Python files: `snake_case.py`
- Plural for collections: `bookings.py`, `customers.py`
- Singular for single purpose: `connector.py`, `agent.py`

### Database Tables

**Pattern**: Lowercase, plural
```sql
CREATE TABLE locations (...);
CREATE TABLE hotels (...);
CREATE TABLE bookings (...);
```

**Columns**: Lowercase, snake_case
```sql
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    check_in_date TEXT,
    check_out_date TEXT
);
```

---

## Agent Behavior Patterns

### Mandatory Workflow

**Pattern**: Enforce strict step-by-step flow in system prompt
```python
SYSTEM_PROMPT = """
### MANDATORY WORKFLOW (ORDER MATTERS)
1. **Identify Location**: Get available locations using `search_locations`.
2. **Find Hotel**: Use `search_hotels` (filtering by `location_id` if possible).
3. **Availability**: Use `search_rooms` with the `hotel_id`, dates, and capacity.
4. **Guest Profile (CRITICAL)**:
   - Search for customer using `search_customers`
   - If not found, use `create_customer_entry`
5. **Confirm Booking**: Call `create_reservation` with all required IDs.
"""
```

**Why**:
- Prevents agent from guessing IDs
- Ensures data consistency
- Provides better UX (user sees all steps)

**Example** (from [agent.py:18-27](src/hms_agent/agent.py:18-27))

### Reliability Rules

**Pattern**: Strict constraints to prevent hallucinations
```python
### CRITICAL RELIABILITY RULES
- **STRICT ID POLICY**: NEVER guess, assume, or invent numeric IDs.
  All IDs MUST come from tool outputs in the current session.
- **NO DATE INVENTION**: Strictly forbidden from assuming dates.
  YOU MUST ASK the user for them.
- **HARD HALT ON ERRORS**: If a tool returns 'error', report it and STOP.
- **NO HALLUCINATION**: Only use information returned by tools.
```

**Why**:
- Prevents booking wrong rooms
- Avoids data corruption
- Makes debugging easier

### Privacy Pattern

**Pattern**: Never reveal PII back to user
```python
# In agent.py system prompt:
"""
**PRIVACY RULE**: If a customer is found, NEVER repeat their phone number or ID
back to the user. Simply confirm "I've found your profile."
"""
```

**When to use**: Any tool that retrieves sensitive data

---

## Testing Patterns

### Integration Test Pattern

**Pattern**: Test complete workflow end-to-end
```python
async def test_booking_flow():
    # 1. Search for available room
    rooms = await client.call_tool("search_rooms", {...})
    assert len(rooms) > 0

    # 2. Create booking
    booking = await client.call_tool("create_reservation", {
        "room_id": rooms[0]["id"],
        ...
    })
    assert booking["status"] == "confirmed"

    # 3. Cancel booking
    result = await client.call_tool("cancel_reservation", {
        "booking_id": booking["booking_id"]
    })
    assert result["status"] == "cancelled"
```

**File**: [src/hms_agent/tests/test_mcp_server.py](src/hms_agent/tests/test_mcp_server.py)

**Why**: Tests the most important user journeys

### Tool Verification Pattern

**Pattern**: Verify each tool in isolation
```python
def test_search_rooms():
    data = SearchRoomsInput(
        hotel_id=1,
        check_in_date="2026-06-01",
        check_out_date="2026-06-05",
        min_capacity=2
    )
    rooms = get_available_rooms(data)
    assert isinstance(rooms, list)
    assert all(isinstance(r, RoomOutput) for r in rooms)
```

**File**: [src/hms_agent/tests/verify_tools.py](src/hms_agent/tests/verify_tools.py)

**Why**: Catches regressions in individual tools

---

## Best Practices

### 1. Always Use Pydantic Models

**DO**:
```python
@mcp.tool()
def search_rooms(hotel_id: int, check_in_date: str, ...):
    data = SearchRoomsInput(  # Validates input
        hotel_id=hotel_id,
        check_in_date=check_in_date,
        ...
    )
    rooms = get_available_rooms(data)
    return {"rooms": [room.model_dump() for room in rooms]}
```

**DON'T**:
```python
@mcp.tool()
def search_rooms(hotel_id, check_in_date, ...):
    # No validation - bad dates could reach SQL query
    return raw_sql_query(hotel_id, check_in_date)
```

### 2. Always Close Connections

**DO**:
```python
def tool_function():
    conn = get_connection()
    try:
        # Use connection
        return result
    finally:
        conn.close()  # Always executes
```

**DON'T**:
```python
def tool_function():
    conn = get_connection()
    result = conn.execute(...)
    conn.close()  # Skipped if execute() raises!
    return result
```

### 3. Provide Helpful Tool Descriptions

**DO**:
```python
@mcp.tool()
def search_customers(name: str | None = None, phone_number: str | None = None):
    """
    Lookup existing customers by name or phone number.
    Privacy Rule: Use this to confirm identity before booking, but never reveal
    existing details to the user.
    If no customer is found, use `create_customer_entry` to register the guest.
    """
```

**DON'T**:
```python
@mcp.tool()
def search_customers(name, phone):
    """Search customers."""  # Not helpful!
```

### 4. Return Structured Errors

**DO**:
```python
try:
    result = risky_operation()
    return result.model_dump()
except ValueError as e:
    return {"error": str(e)}  # Structured
except Exception as e:
    return {"error": f"Failed to create booking: {str(e)}"}
```

**DON'T**:
```python
try:
    result = risky_operation()
    return result
except Exception as e:
    return str(e)  # Not structured - breaks client parsing
```

### 5. Use Type Hints Everywhere

**DO**:
```python
def get_hotels(data: HotelsInput) -> List[HotelsOutput]:
    ...

async def handle_user_message(
    message: str,
    agent: FunctionAgent,
    context: Context,
    verbose: bool = False
) -> str:
    ...
```

**DON'T**:
```python
def get_hotels(data):  # What type is data?
    ...

async def handle_user_message(message, agent, context, verbose=False):
    ...
```

### 6. Validate at System Boundaries

**Pattern**: Validate external input, trust internal data
```python
# External input (from user/API)
@mcp.tool()
def search_rooms(...):
    data = SearchRoomsInput(...)  # ✅ Validate

# Internal function (from another module)
def get_available_rooms(data: SearchRoomsInput):
    # ❌ Don't re-validate - trust the type system
    rooms = query_database(...)
```

### 7. Keep Tools Stateless

**DO**:
```python
@mcp.tool()
def search_rooms(...):
    # All data from parameters
    return query_results
```

**DON'T**:
```python
CURRENT_USER = None  # ❌ Global state

@mcp.tool()
def search_rooms(...):
    # Uses global state - breaks with multiple clients
    user_id = CURRENT_USER
```

### 8. Document Complex Logic

**DO**:
```python
# Check for date overlap using De Morgan's law
# A booking conflicts if it does NOT end before request starts
# AND does NOT start after request ends
cur.execute("""
    WHERE NOT (
        check_out_date <= ?  -- Ends before request starts
        OR check_in_date >= ?  -- Starts after request ends
    )
""", (check_in, check_out))
```

**DON'T**:
```python
# Complex date logic with no explanation
cur.execute("WHERE NOT (check_out_date <= ? OR check_in_date >= ?)", (...))
```

### 9. Use Descriptive Variable Names

**DO**:
```python
mcp_server_url = "http://localhost:8000/mcp"
customer_search_results = search_customers(name="John")
available_rooms = get_available_rooms(data)
```

**DON'T**:
```python
url = "http://localhost:8000/mcp"
results = search(n="John")
r = get_rooms(d)
```

### 10. Follow Python Conventions

**DO**:
```python
# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 120

# Private functions
def _internal_helper():
    ...

# Public functions
def public_api():
    ...
```

**DON'T**:
```python
# ❌ Java-style naming
MaxRetries = 3
defaultTimeout = 120

# ❌ Unclear privacy
def helperFunction():
    ...
```

---

## Architecture Decision Records

### Why FastMCP?
- **Decision**: Use FastMCP for MCP server
- **Rationale**: Simple decorator-based API, built-in HTTP support
- **Alternative Considered**: Implement raw MCP protocol (too complex)

### Why Ollama + LlamaIndex?
- **Decision**: Use Ollama (llama3.2) with LlamaIndex
- **Rationale**: Local execution, no API costs, good for development
- **Alternative Considered**: OpenAI API (costs money), Groq (requires API key)
- **Future**: May switch to Groq for production (faster inference)

### Why SQLite?
- **Decision**: Use SQLite for persistence
- **Rationale**: Simple, no separate server, perfect for development/prototyping
- **Alternative Considered**: PostgreSQL (overkill for current needs)
- **Future**: May migrate to PostgreSQL for production (better concurrency)

### Why Faster-Whisper?
- **Decision**: Use Faster-Whisper for STT
- **Rationale**: Fast on CPU, good accuracy, open-source
- **Alternative Considered**: OpenAI Whisper API (costs money), Deepgram (requires API key)

### Why Piper-TTS?
- **Decision**: Use Piper for TTS
- **Rationale**: Local execution, natural voice, fast
- **Alternative Considered**: ElevenLabs (costs money), OpenAI TTS (costs money)

---

## Common Pitfalls to Avoid

### 1. Date Overlap Logic Errors
```python
# ❌ WRONG - This allows double-booking!
cur.execute("""
    WHERE check_out_date < ? AND check_in_date > ?
""", (check_in, check_out))

# ✅ CORRECT - Uses <= and >= with NOT
cur.execute("""
    WHERE NOT (
        check_out_date <= ? OR check_in_date >= ?
    )
""", (check_in, check_out))
```

### 2. Forgetting to Close Connections
```python
# ❌ WRONG - Connection leaks if error occurs
conn = get_connection()
result = conn.execute(...)
conn.close()
return result

# ✅ CORRECT - Always closes
conn = get_connection()
try:
    return conn.execute(...)
finally:
    conn.close()
```

### 3. Not Validating User Input
```python
# ❌ WRONG - SQL injection risk!
@mcp.tool()
def bad_search(hotel_name: str):
    conn = get_connection()
    cur.execute(f"SELECT * FROM hotels WHERE name = '{hotel_name}'")

# ✅ CORRECT - Parameterized query
@mcp.tool()
def good_search(hotel_name: str):
    data = HotelsInput(name=hotel_name)  # Validate
    conn = get_connection()
    cur.execute("SELECT * FROM hotels WHERE name = ?", (hotel_name,))
```

### 4. Returning Inconsistent Error Format
```python
# ❌ WRONG - Sometimes dict, sometimes string
@mcp.tool()
def inconsistent_tool(...):
    try:
        return {"result": ...}
    except Exception as e:
        return str(e)  # String!

# ✅ CORRECT - Always dict
@mcp.tool()
def consistent_tool(...):
    try:
        return {"result": ...}
    except Exception as e:
        return {"error": str(e)}  # Dict!
```

---

## When to Deviate from Patterns

These patterns are guidelines, not laws. Deviate when:

1. **Performance**: If a pattern causes significant performance issues
2. **External APIs**: If integrating with APIs that require different patterns
3. **Better Alternative**: If you find a clearly superior approach
4. **Prototyping**: For quick experiments (but refactor before committing)

**Important**: Document why you deviated (code comments + git commit message)

---

## References

- [CLAUDE.md](CLAUDE.md) - Architecture overview
- [CODEBASE_INDEX.md](CODEBASE_INDEX.md) - File reference
- [project_plan.md](project_plan.md) - Original design
- [FastMCP Docs](https://github.com/jlowin/fastmcp)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [Pydantic Docs](https://docs.pydantic.dev/)
