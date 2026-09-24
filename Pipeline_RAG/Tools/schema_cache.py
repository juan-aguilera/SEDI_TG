from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema_cache.txt"

def load_or_fetch_schema(graph, refresh: bool = False) -> str:
    """Lee el schema cacheado; si no existe (o refresh=True), lo pide a Neo4j y lo escribe."""
    if SCHEMA_PATH.exists() and not refresh:
        return SCHEMA_PATH.read_text(encoding="utf-8")
    text = graph.get_schema
    SCHEMA_PATH.write_text(text, encoding="utf-8")
    return text