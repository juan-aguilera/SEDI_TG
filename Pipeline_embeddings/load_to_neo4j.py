"""
load_to_neo4j.py
─────────────────────────────────────────────────────────────────────
Etapa 2: escribe los embeddings (parquet) de vuelta a Neo4j como la
propiedad `embedding`, y crea un VECTOR INDEX para busqueda por similitud.

Uso:
    python load_to_neo4j.py --label Model
    python load_to_neo4j.py --label all
─────────────────────────────────────────────────────────────────────
"""
import os
import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from neo4j import GraphDatabase

load_dotenv()

OUTPUT_DIR = Path("embeddings_out")
WRITE_BATCH = 1000   # nodos por transaccion
EMBED_DIM = 1536     # dimension de text-embedding-3-small

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)
NEO4J_DB = os.environ.get("NEO4J_DATABASE", "neo4j")


def write_embeddings(label: str):
    path = OUTPUT_DIR / f"embeddings_{label}.parquet"
    if not path.exists():
        print(f"[{label}] no hay parquet, se omite.")
        return

    df = pd.read_parquet(path)
    print(f"[{label}] escribiendo {len(df):,} embeddings...")

    # UNWIND por lotes: rapido y transaccional
    query = """
    UNWIND $rows AS row
    MATCH (n) WHERE elementId(n) = row.eid
    CALL db.create.setNodeVectorProperty(n, 'embedding', row.vec)
    """
    rows = [
        {"eid": r["_eid"], "vec": [float(x) for x in r["embedding"]]}
        for _, r in df.iterrows()
    ]

    with driver.session(database=NEO4J_DB) as session:
        for i in tqdm(range(0, len(rows), WRITE_BATCH), desc=f"write {label}"):
            batch = rows[i : i + WRITE_BATCH]
            session.run(query, rows=batch)
    print(f"[{label}] OK.")


def create_vector_index(label: str):
    """Crea un vector index por etiqueta para busqueda por coseno."""
    idx_name = f"vec_{label.lower()}_embedding"
    query = f"""
    CREATE VECTOR INDEX `{idx_name}` IF NOT EXISTS
    FOR (n:`{label}`) ON (n.embedding)
    OPTIONS {{ indexConfig: {{
        `vector.dimensions`: {EMBED_DIM},
        `vector.similarity_function`: 'cosine'
    }} }}
    """
    with driver.session(database=NEO4J_DB) as session:
        session.run(query)
    print(f"[{label}] vector index '{idx_name}' creado/verificado.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    labels = (
        [p.stem.replace("embeddings_", "") for p in OUTPUT_DIR.glob("embeddings_*.parquet")]
        if args.label == "all"
        else [args.label]
    )

    for lbl in labels:
        write_embeddings(lbl)
        create_vector_index(lbl)

    driver.close()


if __name__ == "__main__":
    main()
