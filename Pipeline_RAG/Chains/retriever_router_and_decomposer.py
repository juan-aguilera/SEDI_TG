import os                                                           # Permite leer variables de entorno (endpoint, api key, etc.)
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI                       # Cliente para hablar con un deployment de Azure OpenAI


class RelevantLabels(BaseModel):
    """Choose which node types to search with vector similarity."""
    labels: List[Literal["Model", "Dataset", "Space", "Repository", "Author", "Tag"]] = Field(
        ...,
        description="Relevant HF Hub labels for the similarity subquery.",
    )

llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)


structured_llm_router = llm.with_structured_output(RelevantLabels)


from Indexes.index import LABEL_CONFIG
_label_catalog = "\n".join(
    f"- {label}: {cfg['description']}"
    for label, cfg in LABEL_CONFIG.items()
)


system = f"""You are an expert at decomposing a Hugging Face Hub question and choosing
vector-search labels over a Neo4j knowledge graph.

You receive the original user question once. Fill ALL of these fields in a single response:
- similarity_query: a semantic search question (topic, similarity, "about / related to").
  No counts, rankings, or "who has the most".
- labels: 1 or more node types to search for THAT similarity_query only, not for graph_query.
- graph_query: a follow-up over the nodes that vector search will already have found
  (authors, tags, likes, titles of THOSE results). Do not repeat the semantic search.

Available labels:
{_label_catalog}

Label rules:
- Return only labels from the list above.
- If similarity_query is ambiguous, return all plausible labels.
- Never return an empty list. When in doubt, return more labels rather than fewer.

Example:
Question: Find authors of spaces similar to whisper demos
similarity_query: spaces related to whisper or audio transcription demos
graph_query: return the authors of those spaces
labels: ["Space"]

More label choices for a similarity_query (not for the original question):
- "spaces built with gradio" -> ["Space"]
- "datasets about sentiment analysis" -> ["Dataset"]
- "models for text classification" -> ["Model"]
- "tags related to computer vision" -> ["Tag"]
- "authors named google or meta" -> ["Author"]
- "repositories whose model card mentions quantization" -> ["Repository"]
- "gradio demos that use diffusion models" -> ["Space", "Model"]
- "datasets used to train speech recognition models" -> ["Dataset", "Model"]
- "something about summarization on the hub" -> ["Model", "Dataset", "Space", "Tag"]
"""



relevant_labels_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{subquery}"),
    ]
)

retriever_decompose_router = relevant_labels_prompt | structured_llm_router