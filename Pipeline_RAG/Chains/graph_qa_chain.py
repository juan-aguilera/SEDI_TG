# ─────────────────────────────────────────────────────────────────────
# graph_qa_chain.py
# Este archivo arma la pieza que realmente "conversa" con la base de datos
# Neo4j: recibe una pregunta en lenguaje natural, hace que un modelo de
# lenguaje (LLM) la traduzca a una consulta Cypher (el lenguaje de consultas
# de Neo4j, algo asi como el "SQL" de las bases de datos de grafos), ejecuta
# esa consulta contra la base de datos real, y devuelve el resultado.
# A esto se le llama "Graph Cypher QA Chain" (QA = Question Answering,
# "responder preguntas").
#
# Hay dos versiones de esta pieza en este archivo:
#   1) Una version simple: la pregunta se traduce a Cypher directamente.
#   2) Una version "con contexto": se le da al modelo informacion extra
#      (encontrada previamente por una busqueda de similitud) para que
#      arme una mejor consulta Cypher.
# ─────────────────────────────────────────────────────────────────────

# ── Importaciones: traemos herramientas ya hechas de otras librerias ──
import os                                    # Permite leer variables de entorno (usuario, contrasena, direccion de la base de datos, etc.)
import openai                                 # Libreria de OpenAI (importada por costumbre; en este archivo no se usa directamente)
from langchain_openai import ChatOpenAI      # Cliente para hablar con un modelo de chat de OpenAI publico (importado pero no se usa: el modelo activo abajo es el de Azure)
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain  # Neo4jGraph: conexion a la base de datos de grafos.
                                                              # GraphCypherQAChain: arma la "cadena" completa pregunta -> Cypher -> respuesta.
from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI


# ── Importaciones propias del proyecto ──
from Prompts.prompt_template import create_few_shot_prompt, create_few_shot_prompt_with_context  # Funciones que arman las instrucciones que se le dan al modelo (no se usan directamente en este archivo, se importan por si se necesitan)
from Graph.state import GraphState           # Define la "forma" del estado que se pasa entre los pasos del flujo (question, prompt, documents, etc.)

# ── Nos conectamos a la base de datos Neo4j (instancia LOCAL, no AuraDB) ──
# Estos datos (direccion, usuario, contrasena, nombre de la base) se leen
# del archivo .env, que es donde se guardan las contrasenas y datos
# sensibles para no dejarlos escritos directamente en el codigo.
graph = Neo4jGraph(
    url=os.environ.get('NEO4J_URI'),          # Direccion de la base de datos Neo4j (ej: bolt://localhost:7687)
    username=os.environ.get('NEO4J_USER'),    # Usuario para entrar a la base de datos
    password=os.environ.get('NEO4J_PASSWORD'),# Contrasena de ese usuario
    database=os.environ.get('NEO4J_DATABASE'),# Nombre de la base de datos dentro del servidor Neo4j
)

# ── Creamos la conexion con el modelo de lenguaje (LLM) que va a traducir preguntas a Cypher ──
# Este modelo vive en Azure AI Foundry (un "deployment" propio), no en OpenAI publico.
llm = AzureChatOpenAI(

    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)

def get_graph_qa_chain(state: GraphState):
    """
    Arma la cadena "pregunta -> Cypher -> respuesta" en su version SIMPLE
    (sin contexto extra de una busqueda previa).
    Recibe 'state', que es un diccionario con la informacion que se ha ido
    acumulando en el flujo (aqui usamos la parte 'prompt', que ya trae las
    instrucciones armadas para el modelo).
    """

    prompt = state["prompt"]   # Sacamos del estado las instrucciones (few-shot prompt) que le vamos a dar al modelo

    # GraphCypherQAChain.from_llm(...) arma toda la cadena de trabajo:
    # 1) usa 'cypher_llm' para convertir la pregunta en una consulta Cypher
    # 2) ejecuta esa consulta contra 'graph' (la base de datos Neo4j)
    # 3) usa 'qa_llm' para convertir el resultado crudo en una respuesta (si aplica)
    graph_qa_chain = GraphCypherQAChain.from_llm(
            cypher_llm = llm, #should use gpt-4 for production   # Modelo que genera la consulta Cypher (idealmente uno mas potente en produccion)
            qa_llm = llm,                   # Modelo que arma la respuesta final a partir del resultado
            validate_cypher= True,          # Revisa que la consulta Cypher generada sea valida antes de ejecutarla
            graph=graph,                    # La conexion a la base de datos Neo4j que creamos arriba
            verbose=True,                   # Imprime en la consola los pasos internos (util para depurar / entender que esta pasando)
            cypher_prompt = prompt,         # Las instrucciones (few-shot prompt) que guian al modelo para escribir el Cypher
            # return_intermediate_steps = True,   # (deshabilitado) si se activa, tambien devolveria los pasos intermedios (la consulta Cypher generada, etc.)
            return_direct = True,           # Devuelve el resultado crudo de la base de datos, sin que un LLM lo "resuma" de nuevo
            allow_dangerous_requests = True,  # requerido por langchain-neo4j: reconoce que Cypher generado por el LLM se ejecuta directo contra la BD (puede modificar datos si el LLM se equivoca)
        )
    return graph_qa_chain   # Devolvemos la cadena ya armada, lista para usarse con .invoke(...)

def get_graph_qa_chain_with_context(state: GraphState):
    """
    Arma la misma cadena "pregunta -> Cypher -> respuesta", pero en su
    version CON CONTEXTO: usa un 'prompt_with_context', que ya trae
    incluida informacion encontrada antes (por ejemplo, ids de nodos
    hallados en una busqueda de similitud), para que el Cypher generado
    sea mas preciso. Recibe 'state' para poder leer ese
    'prompt_with_context' ya armado.
    """

    prompt_with_context = state["prompt_with_context"]  # Sacamos del estado las instrucciones que ya incluyen ese contexto extra

    graph_qa_chain = GraphCypherQAChain.from_llm(
            cypher_llm = llm, #should use gpt-4 for production   # Modelo que genera la consulta Cypher (idealmente uno mas potente en produccion)
            qa_llm = llm,                   # Modelo que arma la respuesta final a partir del resultado
            validate_cypher= True,          # Revisa que la consulta Cypher generada sea valida antes de ejecutarla
            graph=graph,                    # La misma conexion a la base de datos Neo4j
            verbose=False,                  # Aqui no imprimimos los pasos internos (para no llenar la consola)
            cypher_prompt = prompt_with_context,  # Instrucciones que YA incluyen el contexto extra encontrado antes
            # return_intermediate_steps = True,   # (deshabilitado) ver comentario equivalente arriba
            return_direct = True,           # Devuelve el resultado crudo de la base de datos, sin resumen adicional de un LLM
            allow_dangerous_requests = True,  # requerido por langchain-neo4j: reconoce que Cypher generado por el LLM se ejecuta directo contra la BD
        )
    return graph_qa_chain   # Devolvemos la cadena ya armada, lista para usarse con .invoke(...)
