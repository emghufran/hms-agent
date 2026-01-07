# HMS Agent

A multi-agent hotel management system for managing bookings via WhatsApp and calls.

## Database Setup and Population

This project uses SQLite for its database. The schema includes tables for Locations, Hotels, Rooms, Customers, and Bookings.

### 1. Initialize the Database

To create the `bookings.db` file and set up the necessary tables, run the database utility script:

```bash
source .venv/bin/activate
python scripts/db_utils.py
```

### 2. Populate Hotels and Rooms

To add initial data for locations, hotels, and rooms, use the `populate-hotels` command. You can optionally specify the number of locations, hotels per location, and rooms per hotel.

```bash
source .venv/bin/activate
python scripts/populate_db.py populate-hotels --num-locations 5 --num-hotels-per-location 2 --num-rooms-per-hotel 20
```

### 3. Populate Bookings

To add customers and bookings, use the `populate-bookings` command. This script will ensure that no overlapping bookings are created for the same room. You must provide a start and end date for the booking period.

```bash
source .venv/bin/activate
python scripts/populate_db.py populate-bookings --start-date YYYY-MM-DD --end-date YYYY-MM-DD --num-customers 100 --num-bookings 500
```
Replace `YYYY-MM-DD` with your desired date range.


## Booking managment using MCP server
After initializing the database (`bookings.db`) and polpulating the hotels and rooms, bookings can also be managed by MCP server.

### 1. Run MCP server
To manage the bookings using MCP server you first need to start the MCP server using follwoing commands.

```bash
uv run uvicorn mcp_server:app --host 0.0.0.0 --port 8000 --reload --app-dir src/hms_agent
```

### 2. Run MCP client
A basic agent based client using Ollma. Currently only capable of listing tools (to be updated soon).

```bash
uv run ./src/hms_agent/mcp_client.py --host 127.0.0.1 --port 8000
```

### 2. Test MCP server
The booking functionality can be tested using a test script that check room availbility, books a room and then cancels the booking. Use following commands to test these fuctionalities using MCP.

```bash
uv run ./src/hms_agent/tests/test_mcp_server.py
```