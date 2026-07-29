import sqlite3

DB_FILE = "tasks.db"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    count = cursor.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    if count == 0:
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy milk", 0),
                ("Read FastAPI docs", 1),
                ("Build the Task API", 0),
            ],
        )

    conn.commit()
    conn.close()