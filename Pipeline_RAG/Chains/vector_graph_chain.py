# ─────────────────────────────────────────────────────────────────────
# vector_graph_chain.py
# Este archivo arma la pieza encargada de la "busqueda por similitud"
# (vector search): en vez de traducir la pregunta a una consulta Cypher
# exacta, convierte la pregunta en un vector numerico (embedding) y busca,
# dentro de Neo4j, los nodos (hoy: Model) cuyo texto sea mas parecido a
# esa pregunta (los vecinos mas cercanos en ese espacio de vectores).
#
# Esto es util cuando el usuario hace una pregunta "difusa" (por ejemplo,
# "modelos para clasificacion de texto") que no se puede traducir facil a
# una consulta Cypher exacta, porque no menciona ids o nombres concretos.
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
from Indexes import index   # Modulo que sabe conectarse al indice vectorial ya existente en Neo4j

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

# ── Obtenemos el indice vectorial ya existente en Neo4j ──
# get_neo4j_vector_index() (definido en Indexes/index.py) se conecta a
# Neo4j y arma un objeto Neo4jVector sobre el indice `vec_model_embedding`,
# ya creado y poblado de antemano por Pipeline_embeddings.
# OJO: esta linea se ejecuta UNA sola vez, apenas Python importa este
# archivo (no cada vez que se llama a get_vector_graph_chain), asi que la
# conexion al indice se crea al arrancar el programa y se reutiliza despues.
vector_index = index.get_neo4j_vector_index()

def get_vector_graph_chain():
    '''Create a Neo4j Retrieval QA Chain. Returns top K most relevant Model nodes'''
    # Arma la cadena de "Retrieval QA": dado un texto de entrada (query),
    # busca los documentos mas similares en el indice vectorial y le pide
    # al LLM que responda usando esos documentos como contexto.
    vector_graph_chain = RetrievalQA.from_chain_type(
        llm,                                            # El modelo que va a redactar la respuesta final
        chain_type="stuff",                              # "stuff" = meter todos los documentos encontrados directo en el prompt (la forma mas simple; ojo con textos muy largos)
        retriever = vector_index.as_retriever(search_kwargs={'k':3}),  # Convierte el indice en un "buscador": trae los k=3 nodos mas parecidos a la pregunta
        verbose=True,                                     # Imprime en la consola los pasos internos (util para depurar / entender que esta pasando)
        return_source_documents=True,                     # Ademas de la respuesta en texto, devuelve los documentos originales usados (necesario para luego extraer label/node_id)
    )
    return vector_graph_chain   # Devolvemos la cadena ya armada, lista para usarse con .invoke({"query": "..."})
