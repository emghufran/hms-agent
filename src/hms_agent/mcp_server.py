from fastmcp import FastMCP
from db.models import (
    HotelsInput,
    SearchRoomsInput,
    CreateBookingInput,
    CancelBookingInput,
)
from db.connector import set_db_path

from tools.locations import get_locations
from tools.hotels import get_hotels
from tools.rooms import get_available_rooms
from tools.bookings import create_booking, cancel_booking
from pathlib import Path

# Get the path relative to main.py
BASE_DIR = Path(__file__).resolve().parent  # src/hms_agent
DB_PATH = (
    BASE_DIR.parent.parent / "bookings.db"
)  # goes two folder up from hms_agent to the root of repo

# Set database path before creating the server
set_db_path(DB_PATH)

mcp = FastMCP("HMS MCP Server")


@mcp.tool()
def search_hotels(input: HotelsInput):
    """
    List available hotels for a given location available in the system.
    Id of location can be obtained from search_locations tool.
    Args:
        input (HotelsInput): Input parameters for the hotel query.

    Schema:
        - location_id: Integer field (required)
          Must be a positive integer greater than 0.
    Returns:
        HotelsOutput: The result of the hotel retrieval operation.
    """

    try:
        hotels = get_hotels(input)
        return {"hotels": [hotel.model_dump() for hotel in hotels]}
    except Exception as e:
        return {"error": str(e), "hotels": []}


@mcp.tool()
def search_locations():
    """
    List available hotel locations in the system.

    Returns:
        LocationsOutput: The result of the locations retrieval operation.
        Which can be used by hotel search tool
    """
    try:
        locations = get_locations()
        return {"locations": [location.model_dump() for location in locations]}
    except Exception as e:
        return {"error": str(e), "locations": []}


@mcp.tool()
def search_rooms(input: SearchRoomsInput):
    """Search for available rooms based on dates and capacity"""
    try:
        rooms = get_available_rooms(input)
        return {"rooms": [room.model_dump() for room in rooms]}
    except Exception as e:
        return {"error": str(e), "rooms": []}


@mcp.tool()
def create_reservation(input: CreateBookingInput):
    """Create a new hotel reservation"""
    try:
        result = create_booking(input)
        return result.model_dump()
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to create booking: {str(e)}"}


@mcp.tool()
def cancel_reservation(input: CancelBookingInput):
    """Cancel an existing reservation"""
    try:
        cancel_booking(input)
        return {"status": "cancelled", "booking_id": input.booking_id}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to cancel booking: {str(e)}"}


# Create the HTTP app - the endpoint will be at /mcp
app = mcp.http_app()
