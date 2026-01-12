from db.connector import get_connection
from db.models import HotelsInput
from db.models import HotelsOutput


def get_hotels(data: HotelsInput) -> list[HotelsOutput]:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT h.*
            FROM hotels h
            WHERE h.location_id = ?
            """,
            (data.location_id,),
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
