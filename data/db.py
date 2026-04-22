import sqlite3

class Db:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.conn is None:
                return
            if exc_val is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.close()

    def open(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.row_factory = lambda cursor, row: {
                col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None


def init_db(db_path):
    with sqlite3.connect(db_path) as conn:
        c = conn.execute("PRAGMA foreign_keys = ON")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS critical_events_logs
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                type TEXT NOT NULL,           -- na razie przewidziane 'warning' i 'critical'
                description TEXT NOT NULL
            )
        """)