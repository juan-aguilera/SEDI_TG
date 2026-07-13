
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
import os                                  # Acceso a variables de entorno (credenciales de Neo4j)
import argparse                            # Lectura de argumentos de linea de comandos (--label)
from pathlib import Path                   # Manejo de rutas de archivos de forma multiplataforma

import pandas as pd                        # Lectura de los archivos .parquet con los embeddings
from dotenv import load_dotenv             # Carga variables desde un archivo .env
from tqdm import tqdm                      # Barra de progreso para los lotes de escritura
from neo4j import GraphDatabase            # Cliente oficial para conectarse a Neo4j

load_dotenv()                              # Lee el archivo .env y expone sus variables en os.environ

OUTPUT_DIR = Path("embeddings_out")        # Carpeta donde estan los parquet generados en la Etapa 1
WRITE_BATCH = 1000   # nodos por transaccion   # Cuantos nodos se escriben por cada transaccion (lote)
EMBED_DIM = 1536     # dimension de text-embedding-3-small   # Dimension del vector de embedding

driver = GraphDatabase.driver(             # Crea el driver (conexion) hacia la base de datos Neo4j
    os.environ["NEO4J_URI"],               # URI del servidor Neo4j (ej: neo4j+s://xxx.databases.neo4j.io)
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),  # Usuario y contrasena para autenticar
)
NEO4J_DB = os.environ.get("NEO4J_DATABASE", "neo4j")   # Nombre de la BD; usa "neo4j" si no esta definida


def write_embeddings(label: str):          # Funcion que escribe los embeddings de una etiqueta en Neo4j
    path = OUTPUT_DIR / f"embeddings_{label}.parquet"  # Construye la ruta del parquet de esa etiqueta
    if not path.exists():                  # Si no existe el archivo para esa etiqueta...
        print(f"[{label}] no hay parquet, se omite.")  # ...avisa que se salta
        return                             # ...y termina la funcion sin hacer nada

    df = pd.read_parquet(path)             # Carga el parquet en un DataFrame de pandas
    print(f"[{label}] escribiendo {len(df):,} embeddings...")  # Informa cuantos embeddings se escribiran

    # UNWIND por lotes: rapido y transaccional
    query = """
    UNWIND $rows AS row
    MATCH (n) WHERE elementId(n) = row.eid
    CALL db.create.setNodeVectorProperty(n, 'embedding', row.vec)
    """                                    # Consulta Cypher: por cada fila del lote, ubica el nodo por su
                                           # elementId y le asigna el vector en la propiedad 'embedding'
    rows = [                               # Construye la lista de diccionarios que se enviara a Cypher
        {"eid": r["_eid"], "vec": [float(x) for x in r["embedding"]]}  # eid = id del nodo; vec = vector float
        for _, r in df.iterrows()          # Recorre cada fila del DataFrame
    ]

    with driver.session(database=NEO4J_DB) as session:  # Abre una sesion contra la BD (se cierra sola al salir)
        for i in tqdm(range(0, len(rows), WRITE_BATCH), desc=f"write {label}"):  # Itera en saltos de WRITE_BATCH
            batch = rows[i : i + WRITE_BATCH]   # Toma el sub-lote actual de filas
            session.run(query, rows=batch)      # Ejecuta la consulta Cypher pasando ese lote como parametro
    print(f"[{label}] OK.")                # Confirma que termino la escritura de esta etiqueta


def create_vector_index(label: str):       # Funcion que crea el indice vectorial para una etiqueta
    """Crea un vector index por etiqueta para busqueda por coseno."""
    idx_name = f"vec_{label.lower()}_embedding"  # Nombre del indice (en minusculas, unico por etiqueta)
    query = f"""
    CREATE VECTOR INDEX `{idx_name}` IF NOT EXISTS
    FOR (n:`{label}`) ON (n.embedding)
    OPTIONS {{ indexConfig: {{
        `vector.dimensions`: {EMBED_DIM},
        `vector.similarity_function`: 'cosine'
    }} }}
    """                                    # Cypher: crea el indice vectorial (si no existe) sobre la
                                           # propiedad 'embedding' de los nodos con esa etiqueta,
                                           # con la dimension EMBED_DIM y similitud por coseno
    with driver.session(database=NEO4J_DB) as session:  # Abre sesion contra la BD
        session.run(query)                 # Ejecuta la creacion/verificacion del indice
    print(f"[{label}] vector index '{idx_name}' creado/verificado.")  # Confirma la creacion del indice


def main():                                # Punto de entrada principal del script
    parser = argparse.ArgumentParser()     # Crea el analizador de argumentos de linea de comandos
    parser.add_argument("--label", required=True)  # Define el argumento obligatorio --label
    args = parser.parse_args()             # Lee y parsea los argumentos recibidos

    labels = (                             # Determina la lista de etiquetas a procesar
        [p.stem.replace("embeddings_", "") for p in OUTPUT_DIR.glob("embeddings_*.parquet")]  # Si es "all",
        if args.label == "all"             # extrae el nombre de etiqueta de cada parquet en la carpeta
        else [args.label]                  # Si no, procesa solo la etiqueta indicada
    )

    for lbl in labels:                     # Recorre cada etiqueta a procesar
        write_embeddings(lbl)              # Escribe sus embeddings en Neo4j
        create_vector_index(lbl)           # Crea el indice vectorial correspondiente

    driver.close()                         # Cierra la conexion con Neo4j al terminar


if __name__ == "__main__":                 # Si el archivo se ejecuta directamente (no importado)...
    main()                                 # ...llama a la funcion principal
