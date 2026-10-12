"""Chat web sobre el grafo GraphRAG.

Desde Pipeline_RAG:

    python run_chat.py

La página queda en http://127.0.0.1:8000 y en http://localhost:8000.
Cada sesión es un thread_id, persistido con SqliteSaver. El `app` que
importa el notebook no se toca: sigue compilado con MemorySaver.

La página se sirve enseguida. Neo4j y Azure se abren en la primera
pregunta; si eso falla, el chat muestra el error en vez de dejar el
navegador en blanco.
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
        try:
            values = _read_state(graph_app, graph_lock, session_id)
        except Exception as exc:
            logger.exception("No se pudo leer la sesión %s", session_id)
            raise HTTPException(status_code=500, detail=graph_failure_message(exc)) from exc
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
                raise HTTPException(status_code=500, detail=graph_failure_message(exc)) from exc

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
        snapshot = graph_app.get_state({"configurable": {"thread_id": session_id}})
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


def graph_failure_message(exc: BaseException) -> str:
    """Texto para el chat cuando Neo4j, Azure o el .env impiden responder."""
    return (
        "No se pudo usar el grafo. Revisa que Neo4j esté encendido y que el archivo "
        ".env de la raíz del proyecto tenga NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD "
        f"y las claves AZURE_. Detalle: {exc}"
    )


class _LazyGraph:
    """No importa el grafo hasta la primera pregunta, para que el puerto abra ya."""

    def __init__(self, loader):
        self._loader = loader
        self._graph = None
        self._lock = threading.Lock()

    def _get(self):
        if self._graph is not None:
            return self._graph
        with self._lock:
            if self._graph is None:
                self._graph = self._loader()
            return self._graph

    def invoke(self, *args, **kwargs):
        return self._get().invoke(*args, **kwargs)

    def get_state(self, *args, **kwargs):
        return self._get().get_state(*args, **kwargs)


def _open_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver

    CHECKPOINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINTS_PATH), check_same_thread=False)
    return SqliteSaver(conn), conn


def _load_graph(checkpointer):
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    logger.info("Conectando con Neo4j y Azure. La primera pregunta puede tardar.")
    # Este import abre Neo4j. Va después del .env y nunca al arrancar el puerto.
    from Graph.graph import build_app

    graph_app = build_app(checkpointer)
    logger.info("Grafo listo.")
    return graph_app


_checkpointer, _checkpoint_conn = _open_checkpointer()
app = create_app(_LazyGraph(lambda: _load_graph(_checkpointer)), SessionsStore(), _checkpointer)
app.state.checkpoint_conn = _checkpoint_conn
