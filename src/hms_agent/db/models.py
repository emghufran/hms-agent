from pydantic import BaseModel, Field, StringConstraints
from typing import Literal
from typing_extensions import Annotated

DateStr = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
]


class HotelsInput(BaseModel):
    location_id: int | None = Field(
        None,
        gt=0,
        description="Optional ID of the location to filter hotels. If omitted, all hotels are returned.",
        examples=[1, 5],
    )


class HotelsOutput(BaseModel):
    id: int = Field(..., gt=0)
    name: str


class LocationsOutput(BaseModel):
    id: int = Field(..., gt=0, description="Unique identifier for the location")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")


class SearchRoomsInput(BaseModel):
    hotel_id: int = Field(
        ...,
        gt=0,
        description="The unique ID of the hotel to check for rooms.",
        examples=[12],
    )
    check_in_date: DateStr = Field(
        ..., description="Check-in date in YYYY-MM-DD format.", examples=["2026-06-15"]
    )
    check_out_date: DateStr = Field(
        ...,
        description="Check-out date in YYYY-MM-DD format. Must be after check-in.",
        examples=["2026-06-20"],
    )
    min_capacity: int = Field(
        ...,
        gt=0,
        description="Minimum number of guests the room must accommodate.",
        examples=[2],
    )


class RoomOutput(BaseModel):
    id: int
    room_number: str
    room_type: str
    price_per_night: int
    capacity: int


class CreateBookingInput(BaseModel):
    customer_id: int = Field(
        ...,
        gt=0,
        description="The ID of the customer. MUST be obtained from search_customers or create_customer_entry first.",
    )
    room_id: int = Field(
        ...,
        gt=0,
        description="The ID of the room. MUST be obtained from search_rooms first.",
    )
    check_in_date: DateStr
    check_out_date: DateStr


class BookingOutput(BaseModel):
    booking_id: int
    status: Literal["confirmed"]


class CancelBookingInput(BaseModel):
    booking_id: int = Field(
        ...,
        gt=0,
        description="The ID of the booking to cancel. MUST be obtained from search_bookings first.",
    )


class CustomerSearchInput(BaseModel):
    name: str | None = Field(
        None, description="Full name of the customer to search for."
    )
    phone_number: str | None = Field(
        None, description="Exact phone number of the customer."
    )


class CustomerCreateInput(BaseModel):
    name: str = Field(..., min_length=1, description="Full name of the new customer.")
    phone_number: str = Field(
        ..., min_length=5, description="Contact phone number for the new customer."
    )


class CustomerOutput(BaseModel):
    id: int
    name: str
    phone_number: str
