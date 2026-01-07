import typer
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random

from db_utils import Location, Hotel, Room, Customer, Booking

app = typer.Typer()
fake = Faker()

# Database setup
DATABASE_URL = "sqlite:///./bookings.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


LOCATION_DATA = {
    "USA": ["New York", "Los Angeles", "Chicago"],
    "UK": ["London", "Manchester", "Edinburgh"],
    "France": ["Paris", "Marseille", "Lyon"],
    "Germany": ["Berlin", "Hamburg", "Munich"],
    "Japan": ["Tokyo", "Osaka", "Kyoto"],
}

ROOM_CAPACITY = {
    "Single": 1,
    "Double": 2,
    "Suite": 4,
}


@app.command()
def populate_hotels(
    num_locations: int = typer.Option(5, help="Number of locations to create"),
    num_hotels_per_location: int = typer.Option(
        2, help="Number of hotels per location"
    ),
    num_rooms_per_hotel: int = typer.Option(20, help="Number of rooms per hotel"),
):
    """
    Populates the database with locations, hotels, and rooms.
    """
    db = next(get_db())

    # Create Locations
    for _ in range(num_locations):
        country = random.choice(list(LOCATION_DATA.keys()))
        city = random.choice(LOCATION_DATA[country])
        location = Location(
            name=fake.unique.company(),
            address=fake.address(),
            city=city,
            country=country,
        )
        db.add(location)
    db.commit()
    print(f"Created {num_locations} locations.")

    # Create Hotels
    locations = db.query(Location).all()
    for location in locations:
        for _ in range(num_hotels_per_location):
            hotel = Hotel(name=fake.company(), location=location)
            db.add(hotel)
    db.commit()
    print(f"Created {num_hotels_per_location * len(locations)} hotels.")

    # Create Rooms
    hotels = db.query(Hotel).all()
    room_types = list(ROOM_CAPACITY.keys())
    for hotel in hotels:
        for i in range(num_rooms_per_hotel):
            room_type = random.choice(room_types)
            capacity = ROOM_CAPACITY[room_type]
            room = Room(
                hotel=hotel,
                room_number=f"{i + 1}",
                room_type=room_type,
                price_per_night=random.randint(50, 500) * 100,  # In cents
                capacity=capacity,
            )
            db.add(room)
    db.commit()
    print(f"Created {num_rooms_per_hotel * len(hotels)} rooms.")
    print("Hotel and room population complete.")


@app.command()
def populate_bookings(
    start_date: datetime = typer.Option(
        ..., help="Start date for bookings in YYYY-MM-DD format"
    ),
    end_date: datetime = typer.Option(
        ..., help="End date for bookings in YYYY-MM-DD format"
    ),
    num_customers: int = typer.Option(100, help="Number of customers to create"),
    num_bookings: int = typer.Option(500, help="Number of bookings to create"),
):
    """
    Populates the database with customers and bookings.
    """
    db = next(get_db())

    # Create Customers
    for _ in range(num_customers):
        customer = Customer(name=fake.name(), phone_number=fake.unique.phone_number())
        db.add(customer)
    db.commit()
    print(f"Created {num_customers} customers.")

    # Create Bookings
    rooms = db.query(Room).all()
    if not rooms:
        print("No rooms found. Please populate hotels first.")
        return

    customers = db.query(Customer).all()
    created_bookings = 0
    for _ in range(num_bookings):
        room = random.choice(rooms)
        customer = random.choice(customers)
        check_in_date = fake.date_between(start_date=start_date, end_date=end_date)
        check_out_date = check_in_date + timedelta(days=random.randint(1, 10))

        # Check for overlapping bookings
        existing_booking = (
            db.query(Booking)
            .filter(
                Booking.room_id == room.id,
                Booking.check_in_date < check_out_date,
                Booking.check_out_date > check_in_date,
            )
            .first()
        )

        if not existing_booking:
            booking = Booking(
                room=room,
                customer=customer,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
            )
            db.add(booking)
            created_bookings += 1

    db.commit()
    print(f"Created {created_bookings} bookings.")
    print("Booking population complete.")


if __name__ == "__main__":
    app()
