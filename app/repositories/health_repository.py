import sqlite3


def ping(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
