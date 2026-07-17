# ─────────────────────────────────────────────────────────────────────
# decompose.py
# Este archivo arma una "cadena" (chain) que toma la pregunta de un
# usuario y la divide en dos sub-preguntas mas pequenas:
#   1) una para buscar por similitud (vector search)
#   2) una para consultar el grafo Neo4j
# A esto se le llama "descomposicion de consultas" (query decomposition).
# ─────────────────────────────────────────────────────────────────────

# ── Importaciones: traemos herramientas ya hechas de otras librerias ──
import os                                   # Permite leer variables de entorno (ej: la API key)
import datetime                             # Manejo de fechas (importado por conveniencia; no se usa aqui)
from typing import Literal, Optional, Tuple # Tipos de datos para anotar el codigo (documentan, no obligan)

from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI
from pydantic import BaseModel, Field                               # Para definir la "forma" de los datos de salida
from langchain_core.output_parsers import PydanticToolsParser     # Convierte la respuesta del modelo en objetos Python
from langchain_core.prompts import ChatPromptTemplate             # Plantilla para armar el mensaje que se envia al modelo


# ── Definimos la "forma" que tendra cada sub-pregunta ──
# Una clase es como un molde: describe que campos tendra un objeto.
# Aqui decimos que cada SubQuery tendra un unico campo de texto: sub_query.
class SubQuery(BaseModel):
    """Decompose a given question/query into sub-queries"""

    # Field(...) marca el campo como obligatorio. La 'description' es una
    # pista que lee el modelo de IA para saber que debe escribir aqui.
    sub_query: str = Field(
        ...,
        description="A unique paraphrasing of the original questions.",
    )


# ── Creamos la conexion con el modelo de chat desplegado en Azure AI Foundry ──
# AzureChatOpenAI es igual que ChatOpenAI, pero en vez de hablar con el OpenAI
# publico, habla con TU deployment dentro de un recurso de Azure. Este deployment
# (gpt-5-mini) vive en el MISMO recurso de Azure que el modelo de embeddings,
# por eso reutilizamos AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / AZURE_OPENAI_API_VERSION.
llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    temperature=0,                                                # 0 = respuestas estables y predecibles (poca "creatividad")
)

# ── El "instructivo" (system prompt) que le damos al modelo ──
# Este texto le explica al modelo su tarea: partir la pregunta en DOS
# sub-consultas (una de similitud y una de grafo) e incluye un ejemplo.
system = """You are an expert at converting user questions into Neo4j Cypher queries. \

Perform query decomposition. Given a user question, break it down into two distinct subqueries that \
you need to answer in order to answer the original question.

For the given input question, create a query for similarity search and create a query to perform neo4j graph query.
Here is example:
Question: Find the articles about the photosynthesis and return their titles.
Answers:
sub_query1 : Find articles related to photosynthesis.
sub_query2 : Return titles of the articles
"""

# ── Armamos la plantilla del mensaje completo ──
# Combina el instructivo fijo (system) con la pregunta real del usuario.
# El hueco {question} se rellena mas adelante, al ejecutar la cadena.
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),                 # Primero: las instrucciones
        ("human", "{question}"),            # Despues: la pregunta del usuario
    ]
)

# ── Conectamos las piezas en una "cadena" (chain) ──
# bind_tools le dice al modelo que su respuesta debe seguir el molde SubQuery.
llm_with_tools = llm.bind_tools([SubQuery])
# El parser transforma la respuesta cruda del modelo en objetos SubQuery de Python.
parser = PydanticToolsParser(tools=[SubQuery])

# El operador | (tuberia) encadena los pasos en orden:
#   la pregunta entra por 'prompt' -> pasa al modelo 'llm_with_tools' -> sale procesada por 'parser'.
# El resultado 'query_analyzer' es lo que se usa en Graph/nodes.py con .invoke(question).
query_analyzer = prompt | llm_with_tools | parser
