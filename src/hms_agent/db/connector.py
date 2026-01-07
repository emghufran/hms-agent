import sqlite3
from typing import Optional

_DB_PATH: Optional[str] = None


def set_db_path(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


def get_connection() -> sqlite3.Connection:
    if _DB_PATH is None:
        raise RuntimeError("Database path not set")
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
