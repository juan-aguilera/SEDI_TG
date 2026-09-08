# ─────────────────────────────────────────────────────────────────────
# Este archivo arma una "cadena" (chain) que toma la pregunta de un
# usuario, el resultado de la consulta al grafo y devuelve una respuesta
# en lenguaje natural. Usa el prompt answer_promt.py para generar la respuesta.
# ─────────────────────────────────────────────────────────────────────

# ── Importaciones: traemos herramientas ya hechas de otras librerias ──
import os                                   # Permite leer variables de entorno (ej: la API key)
import datetime                             # Manejo de fechas (importado por conveniencia; no se usa aqui)
from typing import Literal, Optional, Tuple # Tipos de datos para anotar el codigo (documentan, no obligan)
import json
from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI
from pydantic import BaseModel, Field                               # Para definir la "forma" de los datos de salida
from langchain_core.output_parsers import PydanticToolsParser     # Convierte la respuesta del modelo en objetos Python
from langchain_core.prompts import ChatPromptTemplate 
from langchain_core.output_parsers import StrOutputParser
from Prompts.answer_promt import answer_prompt

# ── Creamos la conexion con el modelo de chat desplegado en Azure AI Foundry ──
llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
)

generate_answer_chain = answer_prompt | llm | StrOutputParser()

def _to_text(value) -> str:
    """ChatPromptTemplate only accepts strings in template variables."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and hasattr(value[0], "sub_query"):
        return json.dumps([q.sub_query for q in value], ensure_ascii=False)
    return json.dumps(value, default=str, ensure_ascii=False)
    
def generate_answer(inputs: dict) -> str:
    return generate_answer_chain.invoke({
        "question": inputs["question"],
        "documents": _to_text(inputs.get("documents")),
    })