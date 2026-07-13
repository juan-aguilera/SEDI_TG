"""
generate_embeddings.py
─────────────────────────────────────────────────────────────────────
Etapa 1 del pipeline de embeddings para el grafo de conocimiento de HFH.
 
Flujo:
  1. Extrae nodos de Neo4j por lotes (paginado con SKIP/LIMIT).
  2. Construye un texto representativo por nodo.
  3. Llama a Azure OpenAI (text-embedding-3-small) en batches con reintentos.
  4. Persiste los vectores en parquet (CHECKPOINT reanudable).
 
Despues de esto, usa load_to_neo4j.py para escribir los vectores al grafo.
 
Uso:
    python generate_embeddings.py --label Model
    python generate_embeddings.py --label all
─────────────────────────────────────────────────────────────────────
"""
import os
import time
import argparse
from pathlib import Path
 
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from neo4j import GraphDatabase
from openai import AzureOpenAI
from openai import RateLimitError, APIConnectionError, APITimeoutError, InternalServerError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
 
load_dotenv()
 
# ════════════════════════════════════════════════════════════════════
# CONFIGURACION DE NODOS
# ────────────────────────────────────────────────────────────────────
# AJUSTA AQUI los nombres reales de las propiedades de cada nodo en TU grafo.
#   - id_key   : propiedad que identifica univocamente al nodo (tu indice).
#   - text_props: lista de propiedades de texto a concatenar.
#   - prefix   : etiqueta legible que se antepone al texto (ayuda al modelo).
# Si una propiedad no existe en un nodo, simplemente se omite (Cypher devuelve null).
# ════════════════════════════════════════════════════════════════════
NODE_CONFIG = {
    "Model": {
        "id_key": "model_id",
        "text_props": ["model_id", "pipeline_tag", "tags", "description"],
        "prefix": "modelo de machine learning",
    },
    "Dataset": {
        "id_key": "dataset_id",
        "text_props": ["dataset_id", "citation", "description"],
        "prefix": "dataset",
    },
    "Space": {
        "id_key": "space_id",
        "text_props": ["space_id", "sdk", "hardware"],
        "prefix": "space",
    },
    "Repository": {
        "id_key": "id",
        "text_props": ["id","name","card_data"],
        "prefix": "repository",
    },
    "Author": {
        "id_key": "username",
        "text_props": ["username", "fullname"],
        "prefix": "author",
    },
    "Tag": {
        "id_key": "name",
        "text_props": ["name"],
        "prefix": "tag",
    },
}
 
# ── Parametros operativos ───────────────────────────────────────────
FETCH_PAGE_SIZE = 5000      # cuantos nodos traer de Neo4j por consulta
EMBED_BATCH_SIZE = 16       # cuantos textos mandar a Azure por request (bajo por el tier S0)
MAX_CHARS = 8000            # truncado defensivo por texto (evita pasar el limite de tokens)
THROTTLE_SECONDS = 1.0      # pausa entre requests para no saturar el rate limit por minuto
OUTPUT_DIR = Path("embeddings_out")
OUTPUT_DIR.mkdir(exist_ok=True)
 
# ── Clientes ────────────────────────────────────────────────────────
azure_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
EMBED_DEPLOYMENT = os.environ["AZURE_EMBEDDING_DEPLOYMENT"]
 
neo4j_driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)
NEO4J_DB = os.environ.get("NEO4J_DATABASE", "neo4j")
 
 
# ════════════════════════════════════════════════════════════════════
# 1. CONSTRUCCION DEL TEXTO POR NODO
# ════════════════════════════════════════════════════════════════════
def build_text(record: dict, cfg: dict) -> str:
    """Concatena las propiedades de texto en una frase coherente."""
    parts = [cfg["prefix"]]
    for prop in cfg["text_props"]:
        val = record.get(prop)
        if val is None:
            continue
        val = str(val).strip()
        if val and val.lower() != "none":
            parts.append(f"{prop}: {val}")
    text = " | ".join(parts)
    return text[:MAX_CHARS]
 
 
# ════════════════════════════════════════════════════════════════════
# 2. EXTRACCION DE NODOS DESDE NEO4J (paginada)
# ════════════════════════════════════════════════════════════════════
def count_nodes(label: str) -> int:
    with neo4j_driver.session(database=NEO4J_DB) as session:
        res = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c")
        return res.single()["c"]
 
 
def fetch_nodes(label: str, cfg: dict, skip: int, limit: int):
    """Trae un lote de nodos con su id y propiedades de texto."""
    props = set([cfg["id_key"]] + cfg["text_props"])
    return_clause = ", ".join(f"n.`{p}` AS `{p}`" for p in props)
    # elementId() es estable dentro de la BD y sirve como llave de escritura posterior
    query = (
        f"MATCH (n:`{label}`) "
        f"RETURN elementId(n) AS _eid, {return_clause} "
        f"ORDER BY _eid SKIP $skip LIMIT $limit"
    )
    with neo4j_driver.session(database=NEO4J_DB) as session:
        result = session.run(query, skip=skip, limit=limit)
        return [dict(r) for r in result]
 
 
# ════════════════════════════════════════════════════════════════════
# 3. LLAMADA A AZURE OPENAI (con reintentos y backoff)
# ════════════════════════════════════════════════════════════════════
@retry(
    # espera hasta 90s entre intentos (Azure pide ~60s tras un 429)
    wait=wait_exponential(multiplier=2, min=5, max=90),
    stop=stop_after_attempt(12),
    # solo reintenta ante errores transitorios (rate limit, conexion, timeout, 5xx)
    retry=retry_if_exception_type(
        (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
    ),
    reraise=True,
)
def embed_batch(texts: list[str]) -> list[list[float]]:
    """Genera embeddings para un batch. Reintenta ante rate limit / errores transitorios."""
    # text-embedding-3 no acepta strings vacios -> sustituye por un placeholder
    safe = [t if t.strip() else "sin informacion" for t in texts]
    resp = azure_client.embeddings.create(model=EMBED_DEPLOYMENT, input=safe)
    time.sleep(THROTTLE_SECONDS)  # throttle: no dispares el siguiente request de inmediato
    return [d.embedding for d in resp.data]
 
 
# ════════════════════════════════════════════════════════════════════
# 4. PROCESAMIENTO DE UNA ETIQUETA COMPLETA (con checkpoint)
# ════════════════════════════════════════════════════════════════════
def process_label(label: str):
    cfg = NODE_CONFIG[label]
    out_path = OUTPUT_DIR / f"embeddings_{label}.parquet"
 
    # ── Reanudacion: si ya existe parquet, saltamos los ids ya hechos ──
    done_eids = set()
    if out_path.exists():
        existing = pd.read_parquet(out_path, columns=["_eid"])
        done_eids = set(existing["_eid"].tolist())
        print(f"[{label}] checkpoint encontrado: {len(done_eids):,} nodos ya procesados.")
 
    total = count_nodes(label)
    print(f"[{label}] total de nodos: {total:,}")
 
    buffer_rows = []          # acumula filas antes de volcarlas a disco
    pbar = tqdm(total=total, desc=label, unit="nodo")
    pbar.update(len(done_eids))
 
    skip = 0
    while skip < total:
        page = fetch_nodes(label, cfg, skip, FETCH_PAGE_SIZE)
        skip += FETCH_PAGE_SIZE
        if not page:
            break
 
        # filtra los ya procesados
        page = [r for r in page if r["_eid"] not in done_eids]
        if not page:
            continue
 
        # construye textos
        for r in page:
            r["_text"] = build_text(r, cfg)
 
        # embebe en sub-batches
        for i in range(0, len(page), EMBED_BATCH_SIZE):
            chunk = page[i : i + EMBED_BATCH_SIZE]
            vectors = embed_batch([r["_text"] for r in chunk])
            for r, vec in zip(chunk, vectors):
                buffer_rows.append({
                    "_eid": r["_eid"],
                    "node_id": r.get(cfg["id_key"]),
                    "label": label,
                    "text": r["_text"],
                    "embedding": np.asarray(vec, dtype=np.float32),
                })
            pbar.update(len(chunk))
 
        # ── volcado periodico a disco (checkpoint) ──
        if len(buffer_rows) >= 20000:
            _flush(buffer_rows, out_path)
            buffer_rows = []
 
    if buffer_rows:
        _flush(buffer_rows, out_path)
 
    pbar.close()
    print(f"[{label}] LISTO -> {out_path}")
 
 
def _flush(rows: list[dict], out_path: Path):
    """Anexa filas al parquet existente (append-safe)."""
    df_new = pd.DataFrame(rows)
    if out_path.exists():
        df_old = pd.read_parquet(out_path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_parquet(out_path, index=False)
 
 
# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--label",
        required=True,
        help="Etiqueta a procesar (Model, Dataset, Space, Repository, Author, Tag) o 'all'.",
    )
    args = parser.parse_args()
 
    if args.label == "all":
        labels = list(NODE_CONFIG.keys())
    else:
        if args.label not in NODE_CONFIG:
            raise SystemExit(f"Etiqueta desconocida. Opciones: {list(NODE_CONFIG)} o 'all'.")
        labels = [args.label]
 
    start = time.time()
    for lbl in labels:
        process_label(lbl)
    print(f"\nTiempo total: {(time.time() - start) / 60:.1f} min")
    neo4j_driver.close()
 
 
if __name__ == "__main__":
    main()
 