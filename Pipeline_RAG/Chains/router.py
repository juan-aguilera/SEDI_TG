import os                                                           # Permite leer variables de entorno (endpoint, api key, etc.)
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["vector search", "graph query", "chat"] = Field(
        ...,
        description="Given a user question choose to route it to vectorstore, graphdb or chat.",
    )
    
llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)


structured_llm_router = llm.with_structured_output(RouteQuery)

system = """You are an expert at routing a user question to the correct retrieval strategy over a knowledge graph of the Hugging Face Hub ecosystem (Neo4j). The graph contains Model, Dataset, Space, Author, Tag, Repository, Commit, Discussion and ModifiedFile nodes.
Text embeddings exist for the descriptions/metadata of Dataset, Space, Author, Tag, Model and Repository nodes.
Numeric properties (downloads, likes, dates) are NOT embedded and must be handled as structural filters.

Choose exactly one of these three datasource values:
- "vector search"
- "graph query"
- "chat"

How to choose:

1. Vector search — use it when the question is about semantic similarity over descriptions, topics or purpose.
   Trigger terms include: similar, related, relevant, identical, closest, about, like, comparable.

2. Graph query — use it in either of these cases:
   a) The user already provides (or explicitly asks to run) a raw Cypher query. Return/execute it directly without translation.
   b) Natural-language questions that must be translated to Cypher: filters on numeric properties or dates, aggregations, counts, or traversing relationships between entities (e.g. author -> models, tag -> datasets).

3. Chat — previous findings exist (documents digest is not empty) AND the question can be answered using ONLY those rows: explain, compare, summarize, translate, reformat, OR read a field that is already present in the digest

   Do NOT choose chat if:
   - The asked field is missing from the digest for that row (e.g. they ask for likes and the rows only have model_id). Then graph query.
   - They introduce a new entity or a new filter ("now models by meta", "those with >1M downloads"). Graph query or vector search.
   - Chat history is empty. Never chat on the first turn.


Example questions for vector search:
    Find models about text summarization
    Show datasets similar to one on speech recognition
    Which Spaces are related to image generation?

Example questions for graph query (raw Cypher):
    MATCH (m:Model) RETURN COUNT(m)
    MATCH (t:Tag) RETURN t.name LIMIT 25

Example questions for graph query (natural language -> Cypher):
    Which models have more than one million downloads?
    List datasets created in 2024 together with their authors
    Which authors published the most models?
    Find the most liked Spaces tagged with a specific term, e.g. diffusion

Examples (previous list of 5 models):
- "explain the first one" -> chat
- "compare the 2nd and the 3rd" -> chat
- "how many likes does the first one have?" + digest rows include likes -> chat
- "how many likes does the first one have?" + digest has only model_id -> graph query
- "now show me models by meta" -> graph query or vector search
"""

route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Question: {question}\n\nDocuments digest:\n{documents_digest}\n\nChat history:\n{chat_history}"),
    ]
)

question_router = route_prompt | structured_llm_router