import sqlite3
import os

FLASH_DIR = os.path.join(os.path.expanduser("~"), ".flash")
DB_PATH   = os.path.join(FLASH_DIR, "enumtool.db")

os.makedirs(FLASH_DIR, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subdomains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER NOT NULL,
            host TEXT UNIQUE NOT NULL,
            discovered_at TEXT NOT NULL,
            has_webapp INTEGER DEFAULT 0,
            webapp_scheme TEXT DEFAULT '',
            webapp_status INTEGER DEFAULT 0,
            FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
        )
    """)

    for col, definition in [
        ("has_webapp", "INTEGER DEFAULT 0"),
        ("webapp_scheme", "TEXT DEFAULT ''"),
        ("webapp_status", "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE subdomains ADD COLUMN {col} {definition}")
        except Exception:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dirsearch_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            command TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dirsearch_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            content_length INTEGER DEFAULT 0,
            redirect TEXT DEFAULT '',
            scanned_at TEXT NOT NULL,
            FOREIGN KEY (scan_id) REFERENCES dirsearch_scans(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
