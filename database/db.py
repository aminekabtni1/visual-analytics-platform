"""Database helpers — SQLite by default, Postgres via DATABASE_URL if set."""
import os
import sqlite3
import pathlib

DEFAULT_DB = pathlib.Path(__file__).parent.parent / "data" / "market_basket.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"

def get_db_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DB_PATH", str(DEFAULT_DB)))

def get_connection(db_path: str | pathlib.Path | None = None):
    path = pathlib.Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str | pathlib.Path | None = None):
    conn = get_connection(db_path)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {get_db_path()}")
