# HMS Agent

A multi-agent hotel management system for managing bookings via WhatsApp, calls, and a web-based voice interface.

## Database Setup and Population

This project uses SQLite for its database. The schema includes tables for Locations, Hotels, Rooms, Customers, and Bookings.

### 1. Initialize the Database
```bash
uv run scripts/db_utils.py
```

### 2. Populate Hotels and Rooms
```bash
uv run scripts/populate_db.py populate-hotels --num-locations 5 --num-hotels-per-location 2 --num-rooms-per-hotel 20
```

### 3. Populate Bookings
```bash
uv run scripts/populate_db.py populate-bookings --start-date 2026-01-01 --end-date 2026-12-31 --num-customers 100 --num-bookings 500
```

---

## 🎙️ Conversational Voice Interface (Web)

The core feature is a local-first conversational web interface with real-time speech-to-text and text-to-speech.

### 1. Run the MCP Server
```bash
uv run uvicorn mcp_server:app --host 0.0.0.0 --port 8000 --reload --app-dir src/hms_agent
```

### 2. Run the Voice Gateway
```bash
uv run src/hms_agent/voice_gateway.py
```

### 3. Access the Web UI
Open **[http://localhost:8001](http://localhost:8001)** in your browser.

---

## 🤖 Terminal Agents and Clients

You can also interact with the system directly through terminal-based clients.

### Terminal Agent (Full Reasoning)
The full agent with the complete booking lifecycle and reliability rules.
**Powered by PydanticAI + qwen2.5:14b for better tool calling:**
```bash
uv run src/hms_agent/agent.py
```

### Basic MCP Client
A simpler client for testing MCP tool connectivity:
```bash
uv run src/hms_agent/mcp_client.py --host 127.0.0.1 --port 8000
```

---

## ✅ Testing and Verification

### Automated Integration Test
A comprehensive test script that checks room availability, creates a booking, and cancels it via the MCP server:
```bash
uv run src/hms_agent/tests/test_mcp_server.py
```

### Tool Verification
Verify specific tool logic and data consistency:
```bash
uv run src/hms_agent/tests/verify_tools.py
```

---

## 📚 Documentation

For developers working on this codebase:

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive guide for AI assistants and developers. Start here for architecture overview, quick start, and common tasks.
- **[CODEBASE_INDEX.md](CODEBASE_INDEX.md)** - Complete file reference with descriptions of every module, function, and component.
- **[PATTERNS.md](PATTERNS.md)** - Architectural patterns, coding conventions, and best practices to maintain consistency.
- **[project_plan.md](project_plan.md)** - Original design document with implementation roadmap and technical choices.