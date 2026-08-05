import os                                                           # Permite leer variables de entorno (endpoint, api key, etc.)
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["vector search", "graph query"] = Field(
        ...,
        description="Given a user question choose to route it to vectorstore or graphdb.",
    )
    
#llm = ChatOpenAI(temperature=0)

llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)


structured_llm_router = llm.with_structured_output(RouteQuery)

system = """You are an expert at routing a user question to the correct retrieval strategy over a knowledge graph of the 
Hugging Face Hub ecosystem (Neo4j). The graph contains Model, Dataset, Space, Author, Tag, Repository, Commits
Discussion and ModifiedFile nodes. 
Text embeddings exist for the descriptions/metadata of Dataset, Space, Author, Tag, Model and Repository nodes. 
Numeric properties (downloads, likes, dates) are NOT embedded and must be handled as structural filters.

Choose exactly one of three routes:

1. Vector Search — use it when the question is about semantic similarity over descriptions, topics or purpose.
 Trigger terms include: similar, related, relevant, identical, closest, about, like, comparable.

2. Graph DB Query — use it when the user already provides (or explicitly asks for) a raw Cypher query. 
Return/execute it directly without translation.

3. Graph QA Chain — use it for natural-language questions that require translating to Cypher: 
filtering on numeric properties or dates, aggregations, counts, or traversing relationships between 
entities (e.g. author -> models, tag -> datasets).

Example questions of Vector Search Case:
    Find models about text summarization
    Show datasets similar to one on speech recognition
    Which Spaces are related to image generation?

Example questions of Graph DB Query:
    MATCH (m:Model) RETURN COUNT(m)
    MATCH (t:Tag) RETURN t.name LIMIT 25

Example questions of Graph QA Chain:
    Which models have more than one million downloads?
    List datasets created in 2024 together with their authors
    Which authors published the most models?
    Find the most liked Spaces tagged with a specific term, e.g. diffusion
"""

route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{question}")
    ]
)

question_router = route_prompt | structured_llm_router