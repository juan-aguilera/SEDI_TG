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
#         TIENEN que ser las mismas (y en el mismo orden) que uso
#         generate_embeddings.py para construir el texto que se embebio; si no
#         coinciden, el texto que ve el LLM no es el que se vectorizo.
# description: para que sirve este tipo de nodo, en lenguaje natural. NO lo usa
#         la busqueda vectorial: alimenta el prompt del retriever router
#         (Chains/retriever_router.py), que decide sobre que label(s) buscar.
#         Esta es la unica fuente de verdad de esas descripciones - no
#         duplicarlas dentro del prompt.
#         OJO: no confundir esta clave con la propiedad de Neo4j llamada
#         "description" que aparece en los text_props de Dataset; son cosas
#         distintas y de niveles distintos.
#
# Los 6 labels de abajo son exactamente los que tienen embeddings e indice
# vectorial (`vec_<label>_embedding`) creados por Pipeline_embeddings.
LABEL_CONFIG = {
    "Model": {
        "id_key": "model_id",
        "text_props": ["model_id", "pipeline_tag", "config"],
        "description": (
            "A pre-trained machine learning model published on the Hugging Face Hub, "
            "with the task it solves (pipeline tag, e.g. text-classification, "
            "image-generation) and its architecture configuration."
        ),
    },
    "Dataset": {
        "id_key": "dataset_id",
        "text_props": ["dataset_id", "citation", "description"],
        "description": (
            "A collection of data published on the Hub, used to train or evaluate "
            "models, with its description and academic citation."
        ),
    },
    "Space": {
        "id_key": "space_id",
        "text_props": ["space_id", "sdk", "hardware"],
        "description": (
            "An interactive demo application hosted on the Hub, with the SDK it was "
            "built with (gradio, streamlit, docker) and the hardware it runs on."
        ),
    },
    "Repository": {
        "id_key": "id",
        "text_props": ["id", "name", "card_data"],
        "description": (
            "The git repository that backs a model, dataset or space, with its name "
            "and the metadata of its model card (README)."
        ),
    },
    "Author": {
        "id_key": "username",
        "text_props": ["username", "fullname"],
        "description": (
            "A user or organization that publishes repositories on the Hub, "
            "identified by username and full name."
        ),
    },
    "Tag": {
        "id_key": "name",
        "text_props": ["name"],
        "description": (
            "A free-form keyword attached to repositories to categorize them: task, "
            "language, license, library or domain."
        ),
    },
}

# Lista de todos los labels con indice vectorial disponible.
# Se usa como fallback del retriever router: si el router no logra elegir
# labels (lista vacia, label inventado, o error de la llamada al LLM), se busca
# en todos - asi nunca se excluye de forma irreversible el label correcto.
ALL_LABELS = list(LABEL_CONFIG)


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
def multi_label_similarity_search(query,labels,top_k=5):
    hits = []
    for label in labels:
        idx = get_neo4j_vector_index(label)
        for doc, score in idx.similarity_search_with_score(query, k=top_k):
            doc.metadata["score"] = score
            hits.append((score,doc))
    hits.sort(key=lambda h: h[0], reverse=True)
    return [doc for _, doc in hits[:top_k]]
