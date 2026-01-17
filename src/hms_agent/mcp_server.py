from fastmcp import FastMCP
from db.models import (
    HotelsInput,
    SearchRoomsInput,
    CreateBookingInput,
    CancelBookingInput,
    CustomerSearchInput,
    CustomerCreateInput,
)
from db.connector import set_db_path

from tools.locations import get_locations
from tools.hotels import get_hotels
from tools.rooms import get_available_rooms
from tools.bookings import create_booking, cancel_booking
from tools.customers import get_customer, create_customer
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
def search_hotels(location_id: int | None = None):
    """
    Explore and list all available hotels.
    Use `location_id` to narrow down results to a specific city.
    Returns a list of hotels including their IDs and names.
    Important: Always show the user the hotel names, but use IDs for subsequent bookings.
    """
    try:
        data = HotelsInput(location_id=location_id)
        hotels = get_hotels(data)
        return {"hotels": [hotel.model_dump() for hotel in hotels]}
    except Exception as e:
        return {"error": str(e), "hotels": []}


@mcp.tool()
def search_locations():
    """
    Find and list available geographic locations (cities/countries) where we have hotels.
    Each location has a unique ID which is required by the `search_hotels` tool.
    """
    try:
        locations = get_locations()
        return {"locations": [location.model_dump() for location in locations]}
    except Exception as e:
        return {"error": str(e), "locations": []}


@mcp.tool()
def search_rooms(hotel_id: int, check_in_date: str, check_out_date: str, min_capacity: int):
    """
    Search for available rooms in a specific hotel for a given date range and capacity.
    Returns a list of rooms with their ID, type, and nightly price.
    Note: Always confirm the room type and price with the user before booking.
    Dates must be in YYYY-MM-DD format.
    """
    try:
        data = SearchRoomsInput(
            hotel_id=hotel_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            min_capacity=min_capacity
        )
        rooms = get_available_rooms(data)
        return {"rooms": [room.model_dump() for room in rooms]}
    except Exception as e:
        return {"error": str(e), "rooms": []}


@mcp.tool()
def create_reservation(customer_id: int, room_id: int, check_in_date: str, check_out_date: str):
    """
    Finalize and create a hotel booking.
    Requires a valid customer ID, room ID, and dates (YYYY-MM-DD).
    On success, returns the confirm status and a unique booking reference ID.
    """
    try:
        data = CreateBookingInput(
            customer_id=customer_id,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )
        result = create_booking(data)
        return result.model_dump()
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to create booking: {str(e)}"}


@mcp.tool()
def cancel_reservation(booking_id: int):
    """Cancel an existing reservation using the booking ID."""
    try:
        data = CancelBookingInput(booking_id=booking_id)
        cancel_booking(data)
        return {"status": "cancelled", "booking_id": booking_id}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to cancel booking: {str(e)}"}


@mcp.tool()
def search_customers(name: str | None = None, phone_number: str | None = None):
    """
    Lookup existing customers by name or phone number.
    Privacy Rule: Use this to confirm identity before booking, but never reveal existing details to the user.
    If no customer is found, use `create_customer_entry` to register the guest.
    """
    try:
        data = CustomerSearchInput(name=name, phone_number=phone_number)
        customers = get_customer(data)
        return {"customers": [customer.model_dump() for customer in customers]}
    except Exception as e:
        return {"error": str(e), "customers": []}


@mcp.tool()
def create_customer_entry(name: str, phone_number: str):
    """
    Register a new customer profile in the database.
    Should be called if `search_customers` returns no results for a new guest.
    Returns the new customer ID.
    """
    try:
        data = CustomerCreateInput(name=name, phone_number=phone_number)
        result = create_customer(data)
        return result.model_dump()
    except Exception as e:
        return {"error": f"Failed to create customer: {str(e)}"}


# Create the HTTP app - the endpoint will be at /mcp
app = mcp.http_app()
