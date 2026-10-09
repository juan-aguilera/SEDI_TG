"""Chat web sobre el grafo GraphRAG.

Arrancar desde Pipeline_RAG, con un solo worker:

    uvicorn api.server:app --port 8000

La página queda en http://localhost:8000. Cada sesión es un thread_id del
grafo, persistido con SqliteSaver. El `app` que importa el notebook no se
toca: sigue compilado con MemorySaver.

`app` se construye al usarlo (no al importar este módulo) para no abrir
Neo4j hasta que uvicorn carga el ASGI app.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.sessions_store import (
    CHECKPOINTS_PATH,
    DEFAULT_TITLE,
    SessionsStore,
    title_from_question,
)

logger = logging.getLogger("uvicorn.error")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
REPO_ROOT = Path(__file__).resolve().parents[2]

_production_app: FastAPI | None = None


class RenameIn(BaseModel):
    title: str = Field(..., min_length=1)


class MessageIn(BaseModel):
    content: str


class AnswerOut(BaseModel):
    content: str
    route: str | None = None


def create_app(graph_app, sessions: SessionsStore, checkpointer) -> FastAPI:
    """Rutas de sesiones y la página estática. `graph_app` es el grafo compilado."""
    api = FastAPI(title="GraphRAG Chat")
    generation_lock = asyncio.Lock()
    graph_lock = threading.Lock()

    @api.get("/api/sessions")
    def list_sessions():
        return sessions.list_sessions()

    @api.post("/api/sessions")
    def create_session():
        return sessions.create()

    @api.patch("/api/sessions/{session_id}")
    def rename_session(session_id: str, body: RenameIn):
        updated = sessions.rename(session_id, body.title)
        if updated is None:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        return updated

    @api.delete("/api/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str):
        if not sessions.delete(session_id):
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        _drop_thread(checkpointer, graph_lock, session_id)

    @api.get("/api/sessions/{session_id}/messages")
    def list_messages(session_id: str):
        if sessions.get(session_id) is None:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        values = _read_state(graph_app, graph_lock, session_id)
        return messages_from_state(values)

    @api.post("/api/sessions/{session_id}/messages", response_model=AnswerOut)
    async def post_message(session_id: str, body: MessageIn):
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        question = body.content.strip()
        if not question:
            raise HTTPException(status_code=400, detail="El mensaje está vacío")

        # Un solo invoke a la vez: Azure y Neo4j no se pisan, y el lock de
        # asyncio suelta el event loop para que el resto de la API siga viva.
        async with generation_lock:
            try:
                result = await asyncio.to_thread(
                    _invoke, graph_app, graph_lock, session_id, question
                )
            except Exception as exc:
                logger.exception("Fallo al responder en la sesión %s", session_id)
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        if session["title"] == DEFAULT_TITLE:
            sessions.rename(session_id, title_from_question(question))
        else:
            sessions.touch(session_id)

        answer = result.get("answer") or ""
        if not isinstance(answer, str):
            answer = str(answer)
        route = result.get("route")
        if route is not None and not isinstance(route, str):
            route = str(route)
        return AnswerOut(content=answer, route=route)

    if WEB_DIR.is_dir():
        api.mount(
            "/",
            StaticFiles(directory=str(WEB_DIR), html=True),
            name="web",
        )
    return api


def messages_from_state(values: dict) -> list[dict]:
    """human/ai del checkpoint → {role, content}. La ruta solo va en el último asistente."""
    messages = []
    for raw in values.get("messages") or []:
        role = _message_role(raw)
        if role is None:
            continue
        messages.append({"role": role, "content": _message_content(raw)})
    route = values.get("route")
    if route and messages and messages[-1]["role"] == "assistant":
        messages[-1]["route"] = route
    return messages


def _invoke(graph_app, graph_lock: threading.Lock, session_id: str, question: str) -> dict:
    # Solo la pregunta. Reenviar documents pisaría el checkpoint.
    with graph_lock:
        return graph_app.invoke(
            {"question": question},
            config={"configurable": {"thread_id": session_id}},
        )


def _read_state(graph_app, graph_lock: threading.Lock, session_id: str) -> dict:
    with graph_lock:
        try:
            snapshot = graph_app.get_state(
                {"configurable": {"thread_id": session_id}}
            )
        except Exception:
            logger.exception("No se pudo leer el estado de la sesión %s", session_id)
            return {}
    values = getattr(snapshot, "values", None) or {}
    return values if isinstance(values, dict) else {}


def _drop_thread(checkpointer, graph_lock: threading.Lock, session_id: str) -> None:
    with graph_lock:
        delete_checkpoint_thread(checkpointer, session_id)


def delete_checkpoint_thread(checkpointer, thread_id: str) -> None:
    """Borra el thread del saver. Si aún no hay tablas, no hace nada."""
    deleter = getattr(checkpointer, "delete_thread", None)
    if callable(deleter):
        try:
            deleter(thread_id)
            return
        except Exception:
            logger.exception("delete_thread falló para %s; se intenta SQL", thread_id)
    conn = getattr(checkpointer, "conn", None)
    if conn is None:
        return
    try:
        for table in ("writes", "checkpoints"):
            conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,))
        conn.commit()
    except sqlite3.OperationalError:
        return


def _message_role(msg) -> str | None:
    if isinstance(msg, dict):
        raw = msg.get("type") or msg.get("role") or ""
    else:
        raw = getattr(msg, "type", None) or getattr(msg, "role", "") or ""
    raw = str(raw).lower()
    if raw in {"human", "user"}:
        return "user"
    if raw in {"ai", "assistant"}:
        return "assistant"
    return None


def _message_content(msg) -> str:
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = getattr(msg, "content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(part for part in parts if part)
    return str(content)


def build_production_app() -> FastAPI:
    """Grafo real + SQLite. Carga el .env de la raíz antes de importar las cadenas."""
    from dotenv import load_dotenv
    from langgraph.checkpoint.sqlite import SqliteSaver

    load_dotenv(REPO_ROOT / ".env")

    # El import abre Neo4j y lee las claves de Azure. Tiene que ir después del dotenv.
    from Graph.graph import build_app

    CHECKPOINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINTS_PATH), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph_app = build_app(checkpointer)
    sessions = SessionsStore()
    api = create_app(graph_app, sessions, checkpointer)
    api.state.checkpoint_conn = conn
    return api


def __getattr__(name: str):
    # uvicorn api.server:app entra por aquí. Importar el módulo no conecta a Neo4j.
    global _production_app
    if name == "app":
        if _production_app is None:
            _production_app = build_production_app()
        return _production_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
