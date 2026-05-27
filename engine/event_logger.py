import sqlite3
from datetime import datetime, timezone

LOGGABLE_RISKS = frozenset({"medium", "high", "critical"})


def should_log_state(previous_risk, current_risk):
    if current_risk not in LOGGABLE_RISKS:
        return False
    if previous_risk is None:
        return True
    return previous_risk != current_risk


def insert_log(db_path, event_type, description):
    timestamp_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "INSERT INTO critical_events_logs (date, type, description) VALUES (?, ?, ?)",
            (timestamp_utc, event_type, description),
        )
        log_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, date, type, description FROM critical_events_logs WHERE id = ?",
            (log_id,),
        ).fetchone()
    return dict(row)
