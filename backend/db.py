"""SQLite job log. Every processing request is recorded so statistics are real."""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,              -- restoration | asset_recovery | ui_reconstruction
    status TEXT NOT NULL,            -- success | failed
    filename TEXT,
    created_at REAL NOT NULL,
    duration REAL,
    assets_count INTEGER DEFAULT 0,
    error TEXT,
    meta TEXT
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init() -> None:
    with _lock, _conn() as con:
        con.executescript(SCHEMA)


def record(job_id, kind, status, filename, duration=None, assets_count=0, error=None, meta=None):
    with _lock, _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
            (job_id, kind, status, filename, time.time(), duration, assets_count, error,
             json.dumps(meta or {})),
        )


def stats() -> dict:
    with _conn() as con:
        rows = con.execute(
            "SELECT kind, status, COUNT(*) n, COALESCE(SUM(assets_count),0) a, AVG(duration) d "
            "FROM jobs GROUP BY kind, status"
        ).fetchall()
    out = {"total_jobs": 0, "by_kind": {}}
    for r in rows:
        k = out["by_kind"].setdefault(r["kind"], {"success": 0, "failed": 0, "assets": 0, "avg_duration": None})
        k[r["status"]] = r["n"]
        k["assets"] += r["a"]
        if r["status"] == "success" and r["d"] is not None:
            k["avg_duration"] = round(r["d"], 1)
        out["total_jobs"] += r["n"]
    return out


def history(limit: int = 50) -> list:
    with _conn() as con:
        rows = con.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["meta"] = json.loads(d["meta"] or "{}")
        result.append(d)
    return result
