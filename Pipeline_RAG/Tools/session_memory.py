# Pipeline_RAG/Tools/session_memory.py
import json
from typing import Any


_KEEP_KEYS = (
    "model_id",
    "node_id",
    "repo_id",
    "repo_name",
    "username",
    "name",
    "author",
    "dataset_id",
    "space_id",
    "title",
    "pipeline_tag",
    "downloads",
    "likes",
    "label",
)

_DROP_KEYS = {
    "tags",
    "spaces",
    "embedding",
    "config",
    "description",
    "abstract",
    "readme",
}


def recent_messages(messages, n: int = 8) -> list:
    """Últimos N mensajes del historial. Lista vacía si aún no hay sesión."""
    if not messages:
        return []
    return list(messages[-n:])


def messages_as_text(messages) -> str:
    """Serializa rol + contenido para prompts con {chat_history} string."""
    if not messages:
        return ""
    lines = []
    for msg in messages:
        role = _message_role(msg)
        content = _message_content(msg)
        if content == "":
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def documents_digest(documents, max_chars: int = 3000) -> str:
    """JSON compacto de ids / nombres / conteos, numerado 1-based."""
    if not documents:
        return ""
    compact = _compact(documents)
    text = json.dumps(compact, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return text
    return text[: max_chars].rstrip() + "…"


def _message_role(msg) -> str:
    if isinstance(msg, dict):
        return str(msg.get("role") or msg.get("type") or "unknown")
    msg_type = getattr(msg, "type", None)
    if msg_type:
        return str(msg_type)
    return type(msg).__name__


def _message_content(msg) -> str:
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = getattr(msg, "content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str)


def _compact(value: Any) -> Any:
    # GraphCypherQAChain return_direct=True: {"query": "...", "result": [filas]}
    if isinstance(value, dict) and "result" in value:
        rows = value.get("result")
        digest = {"n": len(rows) if isinstance(rows, list) else 0}
        if value.get("query"):
            digest["query"] = str(value["query"])
        digest["result"] = _compact(rows) if rows is not None else []
        return digest

    if isinstance(value, list):
        compacted_rows = [_compact_row(item) for item in value]
        return [
            {"rank": i, **row} if isinstance(row, dict) else {"rank": i, "value": row}
            for i, row in enumerate(compacted_rows, start=1)
        ]

    if isinstance(value, dict):
        return _compact_row(value)

    return value


def _compact_row(row: Any) -> Any:
    if not isinstance(row, dict):
        return row

    compact = {}
    for key, val in row.items():
        if _should_drop(key) or val is None:
            continue
        if _is_keep_key(key) or _looks_like_count(key, val):
            compact[key] = val
    if not compact:
        for key, val in row.items():
            if _should_drop(key) or val is None:
                continue
            compact[key] = val
            if len(compact) >= 4:
                break
    return compact


def _should_drop(key: str) -> bool:
    short = key.split(".")[-1].lower()
    return short in _DROP_KEYS


def _is_keep_key(key: str) -> bool:
    short = key.split(".")[-1]
    return short in _KEEP_KEYS or short.endswith("_id")


def _looks_like_count(key: str, val) -> bool:
    short = key.split(".")[-1].lower()
    if short.startswith("count") or short in {"n", "total"}:
        return True
    return isinstance(val, (int, float)) and short in {"downloads", "likes", "followers"}