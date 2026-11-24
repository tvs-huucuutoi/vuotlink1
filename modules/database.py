import json
import os
import sqlite3
from datetime import datetime, timezone

def db_path():
    return os.getenv("DB_PATH", "/tmp/linkcode_tool.sqlite3")

def _connect():
    conn = sqlite3.connect(db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    path = db_path()
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                input_value TEXT NOT NULL,
                final_url TEXT,
                status INTEGER,
                title TEXT,
                codes_json TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at DESC)")

def save_result(kind, input_value, result):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO history(created_at,kind,input_value,final_url,status,title,codes_json) VALUES(?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), kind, input_value,
             result.get("final_url", ""), result.get("status"), result.get("title", ""),
             json.dumps(result.get("codes", []), ensure_ascii=False))
        )

def _row(row):
    return {
        "id": row["id"], "created_at": row["created_at"], "kind": row["kind"],
        "input_value": row["input_value"], "final_url": row["final_url"] or "",
        "status": row["status"], "title": row["title"] or "",
        "codes": json.loads(row["codes_json"] or "[]")
    }

def list_history(query="", limit=50):
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM history
               WHERE input_value LIKE ? OR final_url LIKE ? OR title LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        ).fetchall()
    return [_row(r) for r in rows]

def get_history():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 5000").fetchall()
    return [_row(r) for r in rows]

def delete_history(item_id=None):
    with _connect() as conn:
        if item_id is None:
            conn.execute("DELETE FROM history")
            return True
        cur = conn.execute("DELETE FROM history WHERE id=?", (item_id,))
        return cur.rowcount > 0
