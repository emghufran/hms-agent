from db.connector import get_connection
from db.models import HotelsOutput


def get_hotels(location: int) -> list[HotelsOutput]:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT h.*
            FROM hotels h
            WHERE location_id = ?
            """,
            (location),
        )

        rows = cur.fetchall()

        return [
            HotelsOutput(
                id=row["id"],
                name=row["name"],
            )
            for row in rows
        ]
    finally:
        if conn:
            conn.close()