import re

# After the first RETURN, these clauses are still part of the same Cypher statement.
_ALLOWED_AFTER_RETURN = re.compile(
    r"^\s*(ORDER\s+BY|SKIP|LIMIT)\b",
    re.IGNORECASE,
)

# A new reading clause / statement after RETURN is what triggers Neo4j 42I38.
_NEXT_STATEMENT = re.compile(
    r"(?:^|(?<=\s))(?:OPTIONAL\s+MATCH|MATCH|WITH|UNWIND|CALL|CREATE|MERGE|RETURN|FOREACH)\b",
    re.IGNORECASE,
)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:cypher)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip().strip("`").strip()


def clip_to_single_statement(query) -> str:
    """Keep the first Cypher statement: first RETURN plus trailing ORDER BY / SKIP / LIMIT.

    GraphCypherQAChain sends the LLM output to Neo4j as-is. Models sometimes concatenate
    a second MATCH/RETURN (or extra prose), which Neo4j rejects with 42I38.
    """
    if not query:
        return ""

    text = _strip_markdown_fence(str(query))
    if ";" in text:
        text = text.split(";", 1)[0].strip()

    return_match = re.search(r"\bRETURN\b", text, flags=re.IGNORECASE)
    if not return_match:
        return text

    head = text[: return_match.end()]
    rest = text[return_match.end() :]

    next_stmt = _NEXT_STATEMENT.search(rest)
    if next_stmt:
        rest = rest[: next_stmt.start()]

    clipped = (head + rest).strip()
    clipped = re.sub(r"[,]\s*$", "", clipped)
    return clipped.rstrip()
