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
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS critical_events_logs
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                type TEXT NOT NULL,           -- na razie przewidziane 'warning' i 'critical'
                description TEXT NOT NULL
            )
        """)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video_env
            (
                video_id TEXT PRIMARY KEY,
                env_mult REAL NOT NULL DEFAULT 1.0
            )
        """)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS frame_annotations
            (
                video_id       TEXT    NOT NULL,
                frame_id       INTEGER NOT NULL,
                vehicle_action TEXT,
                traffic_light  TEXT,
                ped_crossing   INTEGER NOT NULL DEFAULT 0,
                ped_sign       INTEGER NOT NULL DEFAULT 0,
                stop_sign      INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (video_id, frame_id)
            )
        """)