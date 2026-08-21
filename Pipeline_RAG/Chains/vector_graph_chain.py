# ─────────────────────────────────────────────────────────────────────
# vector_graph_chain.py
# Este archivo arma la pieza encargada de la "busqueda por similitud"
# (vector search): en vez de traducir la pregunta a una consulta Cypher
# exacta, convierte la pregunta en un vector numerico (embedding) y busca,
# dentro de Neo4j, los nodos cuyos textos embebidos sean mas parecidos a
# esa pregunta (los vecinos mas cercanos en ese espacio de vectores).
#
# Los labels a buscar (Model, Dataset, Space, Repository, Author, Tag)
# NO se fijan aqui: los elige el retriever_router (Chains/retriever_router.py)
# y llegan como argumento a get_vector_graph_chain(labels, ...). La busqueda
# multi-label la hace Indexes/index.py::MultilabelRetriever, que consulta
# uno o mas indices `vec_<label>_embedding` y fusiona resultados por score.
#
# Esto es util cuando el usuario hace una pregunta "difusa" (por ejemplo,
# "modelos para clasificacion de texto" o "spaces con gradio") que no se
# puede traducir facil a una consulta Cypher exacta, porque no menciona
# ids o nombres concretos.
#
# El resultado de esta cadena no es solo una respuesta en texto: tambien
# devuelve los documentos originales encontrados (return_source_documents),
# que luego se usan en Graph/nodes.py (funcion vector_search) para sacar
# los (label, node_id) y pasarlos como contexto a la siguiente etapa del
# flujo (la que arma la consulta Cypher "con contexto").
# ─────────────────────────────────────────────────────────────────────

import os                                    # Permite leer variables de entorno
from langchain_openai import AzureChatOpenAI  # Cliente para hablar con un deployment de Azure OpenAI
from langchain_classic.chains import RetrievalQA  # RetrievalQA: arma una cadena "pregunta -> buscar documentos parecidos -> responder usando esos documentos"

# ── Importaciones propias del proyecto ──
from Indexes import index   # Modulo con MultilabelRetriever y los indices vectoriales por label

# ── Creamos la conexion con el modelo de lenguaje (LLM) que va a redactar la respuesta ──
# Mismo patron que Chains/graph_qa_chain.py: Azure OpenAI, no OpenAI publico
# (OPENAI_API_KEY no esta configurada en este proyecto).
llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)


def get_vector_graph_chain(labels, top_k=5):
    '''Crea una RetrievalQA sobre los indices vectoriales de los labels dados.

    labels: lista elegida por el retriever_router (1..N de los 6 labels HF Hub).
    top_k: cuantos documentos devolver tras fusionar scores entre labels.
    '''
    # Arma la cadena de "Retrieval QA": dado un texto de entrada (query),
    # busca los documentos mas similares en los indices de esos labels y le
    # pide al LLM que responda usando esos documentos como contexto.
    # OJO: ya NO se crea un Neo4jVector a nivel de modulo (eso fijaba un
    # solo label al importar). El retriever se construye por llamada, con
    # los labels de esta pregunta; el cache de indices vive en index.py.
    vector_graph_chain = RetrievalQA.from_chain_type(
        llm,                                            # El modelo que va a redactar la respuesta final
        chain_type="stuff",                              # "stuff" = meter todos los documentos encontrados directo en el prompt (la forma mas simple; ojo con textos muy largos)
        retriever=index.MultilabelRetriever(labels=labels, top_k=top_k),  # Busca en N indices y fusiona por score
        verbose=True,                                     # Imprime en la consola los pasos internos (util para depurar / entender que esta pasando)
        return_source_documents=True,                     # Ademas de la respuesta en texto, devuelve los documentos originales usados (necesario para luego extraer label/node_id)
    )
    return vector_graph_chain   # Devolvemos la cadena ya armada, lista para usarse con .invoke({"query": "..."})
