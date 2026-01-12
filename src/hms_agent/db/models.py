from pydantic import BaseModel, Field, StringConstraints
from typing import Literal
from typing_extensions import Annotated

DateStr = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
]


class HotelsOutput(BaseModel):
    id: int = Field(..., gt=0)
    name: str


class LocationsOutput(BaseModel):
    id: int = Field(..., gt=0)
    city: str 
    country: str


class SearchRoomsInput(BaseModel):
    hotel_id: int = Field(..., gt=0)
    check_in_date: DateStr
    check_out_date: DateStr
    min_capacity: int = Field(..., gt=0)


class RoomOutput(BaseModel):
    id: int
    room_number: str
    room_type: str
    price_per_night: int
    capacity: int


class CreateBookingInput(BaseModel):
    customer_id: int = Field(..., gt=0)
    room_id: int = Field(..., gt=0)
    check_in_date: DateStr
    check_out_date: DateStr


class BookingOutput(BaseModel):
    booking_id: int
    status: Literal["confirmed"]


class CancelBookingInput(BaseModel):
    booking_id: int = Field(..., gt=0)
