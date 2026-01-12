from db.connector import get_connection
from db.models import LocationsOutput


def get_locations() -> list[LocationsOutput]:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT l.*
            FROM locations l
            """
        )

        rows = cur.fetchall()

        return [
            LocationsOutput(
                id=row["id"],
                city=row["city"],
                country=row["country"],
            )
            for row in rows
        ]
    finally:
        if conn:
            conn.close()
