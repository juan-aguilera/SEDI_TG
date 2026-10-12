"""Títulos y orden de la barra lateral.

SqliteSaver guarda el estado del grafo (mensajes, documents, route) por
thread_id, pero no el nombre del chat ni la fecha para ordenar la lista.
Esta tabla vive en otro archivo para no mezclarse con el esquema del
checkpointer.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TITLE = "Nuevo chat"
TITLE_LIMIT = 60

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
CHAT_DATA_DIR = PIPELINE_ROOT / "chat_data"
SESSIONS_PATH = CHAT_DATA_DIR / "sessions.sqlite"
CHECKPOINTS_PATH = CHAT_DATA_DIR / "checkpoints.sqlite"


def title_from_question(text: str, limit: int = TITLE_LIMIT) -> str:
    """Primera pregunta del chat, en una línea y recortada."""
    compact = " ".join((text or "").split())
    if not compact:
        return DEFAULT_TITLE
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionsStore:
    def __init__(self, path: Path | str = SESSIONS_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def list_sessions(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, title: str = DEFAULT_TITLE) -> dict:
        session_id = str(uuid.uuid4())
        now = _now()
        stored_title = title.strip() or DEFAULT_TITLE
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, stored_title, now, now),
            )
            self._conn.commit()
        return {
            "id": session_id,
            "title": stored_title,
            "created_at": now,
            "updated_at": now,
        }

    def get(self, session_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def rename(self, session_id: str, title: str) -> dict | None:
        stored_title = title.strip()
        if not stored_title:
            stored_title = DEFAULT_TITLE
        return self._update(session_id, title=stored_title)

    def touch(self, session_id: str) -> dict | None:
        return self._update(session_id, title=None)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM sessions WHERE id = ?",
                (session_id,),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def _update(self, session_id: str, title: str | None) -> dict | None:
        now = _now()
        with self._lock:
            row = self._conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            stored_title = row["title"] if title is None else title
            self._conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (stored_title, now, session_id),
            )
            self._conn.commit()
        return {
            "id": session_id,
            "title": stored_title,
            "created_at": row["created_at"],
            "updated_at": now,
        }
