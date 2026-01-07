from db.connector import get_connection
from db.models import CreateBookingInput, BookingOutput, CancelBookingInput


def create_booking(data: CreateBookingInput) -> BookingOutput:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Availability check (date overlap)
        cur.execute(
            """
            SELECT 1 FROM bookings
            WHERE room_id = ?
              AND status = 'confirmed'
              AND NOT (
                check_out_date <= ?
                OR check_in_date >= ?
              )
            """,
            (data.room_id, data.check_in_date, data.check_out_date),
        )

        if cur.fetchone():
            raise ValueError("Room is not available for selected dates")

        cur.execute(
            """
            INSERT INTO bookings (customer_id, room_id, check_in_date, check_out_date, status)
            VALUES (?, ?, ?, ?, 'confirmed')
            """,
            (
                data.customer_id,
                data.room_id,
                data.check_in_date,
                data.check_out_date,
            ),
        )

        conn.commit()
        booking_id = cur.lastrowid

        return BookingOutput(
            booking_id=booking_id,
            status="confirmed",
        )
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def cancel_booking(data: CancelBookingInput) -> None:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE bookings
            SET status = 'cancelled'
            WHERE id = ?
            """,
            (data.booking_id,),
        )

        if cur.rowcount == 0:
            raise ValueError("Booking not found")

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
