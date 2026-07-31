# ─────────────────────────────────────────────────────────────────────
# index.py
# Este archivo arma el "buscador" (retriever) que usa vector_graph_chain.py:
# un objeto Neo4jVector que sabe conectarse a un indice vectorial YA
# EXISTENTE en Neo4j y, cuando alguien le pida buscar, convertir la
# pregunta en un vector y compararla contra los vectores ya guardados.
#
# OJO: este archivo no crea ni calcula embeddings nuevos. Los embeddings de
# los nodos (Model, Dataset, etc.) ya fueron generados una sola vez, de
# antemano, por Pipeline_embeddings (generate_embeddings.py + load_to_neo4j.py),
# usando Azure OpenAI. Aqui solo nos conectamos a eso que ya existe:
#   - Neo4jVector.from_existing_index(...) SOLO conecta, no escribe nada.
# ─────────────────────────────────────────────────────────────────────

import os
from langchain_neo4j import Neo4jVector
from langchain_openai import AzureOpenAIEmbeddings

# ── Configuracion por label ──────────────────────────────────────────
# id_key: propiedad que identifica al nodo (la misma que usa Pipeline_embeddings
#         en generate_embeddings.py -> NODE_CONFIG).
# text_props: propiedades que se concatenan como texto para el LLM (page_content).
# Hoy solo esta wireado el label "Model"; agregar otro label es agregar una
# entrada aqui (ver PLAN_busqueda_vectorial_multilabel.md para el caso multi-label).
LABEL_CONFIG = {
    "Model": {"id_key": "model_id", "text_props": ["model_id", "pipeline_tag", "config"]},
}


def _get_embedding_model():
    '''Modelo de embeddings para convertir la PREGUNTA del usuario en un vector.

    Tiene que ser el mismo proveedor/deployment que se uso para calcular los
    vectores ya guardados en Neo4j (Azure OpenAI, AZURE_EMBEDDING_DEPLOYMENT),
    si no, comparar la pregunta contra esos vectores no tendria sentido
    (espacios vectoriales distintos aunque tengan la misma dimension).
    '''
    return AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
    )


def _build_retrieval_query(label: str, id_key: str, text_props: list[str]) -> str:
    '''Arma el Cypher que decide que se devuelve por cada nodo encontrado.

    Para cuando este texto corre, Neo4j ya hizo la busqueda vectorial y ya
    tiene disponibles las variables `node` (el nodo encontrado) y `score`
    (su similitud con la pregunta) - este query solo arma el RETURN final:
      - text: concatena las text_props en un string (page_content del Document).
      - metadata: {node_id, label} limpio, en vez del default de la libreria
        (que deja las text_props en null dentro de metadata y no incluye
        un "node_id"/"label" con esos nombres).
    '''
    return (
        f"RETURN reduce(str='', k IN {text_props} | "
        "str + '\\n' + k + ': ' + coalesce(toString(node[k]), '')) AS text, "
        f"node{{node_id: node.{id_key}, label: '{label}'}} AS metadata, score"
    )


def get_neo4j_vector_index(label: str = "Model"):
    '''Conecta con el indice vectorial ya existente en Neo4j para `label`.

    Usa Neo4jVector.from_existing_index (no from_existing_graph): solo se
    conecta al indice `vec_<label>_embedding` ya creado por
    Pipeline_embeddings/load_to_neo4j.py, sin crear ni escribir nada nuevo.
    Devuelve un Neo4jVector normal - se usa igual que antes (.as_retriever(...)).
    '''
    cfg = LABEL_CONFIG[label]

    return Neo4jVector.from_existing_index(
        embedding=_get_embedding_model(),
        url=os.environ["NEO4J_URI"],
        username=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
        database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        index_name=f"vec_{label.lower()}_embedding",
        retrieval_query=_build_retrieval_query(label, cfg["id_key"], cfg["text_props"]),
    )
