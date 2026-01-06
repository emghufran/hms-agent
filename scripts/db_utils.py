import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False, unique=True)
    bookings = relationship("Booking", back_populates="customer")

    def __repr__(self):
        return f"<Customer(name='{self.name}', phone_number='{self.phone_number}')>"

from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, UniqueConstraint

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)

    hotels = relationship("Hotel", back_populates="location")

    def __repr__(self):
        return f"<Location(name='{self.name}', address='{self.address}', city='{self.city}', country='{self.country}')>"

class Hotel(Base):
    __tablename__ = 'hotels'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))

    location = relationship("Location", back_populates="hotels")
    rooms = relationship("Room", back_populates="hotel")

    def __repr__(self):
        return f"<Hotel(name='{self.name}', location='{self.location.name if self.location else None}')>"

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    room_number = Column(String, nullable=False)
    room_type = Column(String, nullable=False)
    price_per_night = Column(Integer, nullable=False) # Storing in cents to avoid float issues
    capacity = Column(Integer, nullable=False)

    hotel = relationship("Hotel", back_populates="rooms")
    __table_args__ = (UniqueConstraint('hotel_id', 'room_number', name='_hotel_room_uc'),)

    def __repr__(self):
        return f"<Room(room_number='{self.room_number}', room_type='{self.room_type}')>"

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    room_id = Column(Integer, ForeignKey('rooms.id'))
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    status = Column(String, default="confirmed") # e.g., confirmed, cancelled, completed

    customer = relationship("Customer", back_populates="bookings")
    room = relationship("Room")

    def __repr__(self):
        return f"<Booking(id={self.id}, customer_id={self.customer_id}, room_id={self.room_id}, check_in={self.check_in_date}, check_out={self.check_out_date})>"

DATABASE_URL = "sqlite:///./bookings.db"

def create_database():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    print("Database and tables created successfully.")

if __name__ == "__main__":
    create_database()
