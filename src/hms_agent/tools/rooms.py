from typing import List
from db.connector import get_connection
from db.models import SearchRoomsInput, RoomOutput


def get_available_rooms(data: SearchRoomsInput) -> List[RoomOutput]:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

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
                    check_out_date <= ?
                    OR check_in_date >= ?
                  )
              )
            """,
            (
                data.hotel_id,
                data.min_capacity,
                data.check_in_date,
                data.check_out_date,
            ),
        )

        rows = cur.fetchall()

        return [
            RoomOutput(
                id=row["id"],
                room_number=row["room_number"],
                room_type=row["room_type"],
                price_per_night=row["price_per_night"],
                capacity=row["capacity"],
            )
            for row in rows
        ]
    finally:
        if conn:
            conn.close()
