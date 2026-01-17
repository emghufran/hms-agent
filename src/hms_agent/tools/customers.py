from db.connector import get_connection
from db.models import CustomerSearchInput, CustomerCreateInput, CustomerOutput


def get_customer(data: CustomerSearchInput) -> list[CustomerOutput]:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = "SELECT id, name, phone_number FROM customers WHERE 1=1"
        params = []

        if data.name:
            query += " AND name LIKE ?"
            params.append(f"%{data.name}%")

        if data.phone_number:
            query += " AND phone_number = ?"
            params.append(data.phone_number)

        cur.execute(query, params)
        rows = cur.fetchall()

        return [
            CustomerOutput(
                id=row["id"],
                name=row["name"],
                phone_number=row["phone_number"],
            )
            for row in rows
        ]
    finally:
        if conn:
            conn.close()


def create_customer(data: CustomerCreateInput) -> CustomerOutput:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO customers (name, phone_number)
            VALUES (?, ?)
            """,
            (data.name, data.phone_number),
        )

        conn.commit()
        customer_id = cur.lastrowid

        return CustomerOutput(
            id=customer_id,
            name=data.name,
            phone_number=data.phone_number,
        )
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
