import os                                                           # Permite leer variables de entorno (endpoint, api key, etc.)
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI        
from langchain_core.output_parsers import PydanticToolsParser    



class DecomposeAndRoute(BaseModel):
    similarity_query: str = Field(..., description="Sub-question for vector similarity search.")
    graph_query: str = Field(..., description="Sub-question for the Neo4j Cypher query.")
    labels: List[Literal["Model", "Dataset", "Space", "Repository", "Author", "Tag"]] = Field(
        ...,
        min_length=1,
        description="Labels to search for the similarity_query, not the graph_query.",
    )

llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)


structured_llm_router = llm.with_structured_output(DecomposeAndRoute)

from Indexes.index import LABEL_CONFIG
_label_catalog = "\n".join(
    f"- {label}: {cfg['description']}"
    for label, cfg in LABEL_CONFIG.items()
)


system = f"""You are an expert at to topics: 

1. converting user questions into questions 
optimized for vector search and Neo4j Cypher queries.

Perform question decomposition. Given a user question, break it down into two distinct sub-questions that \
you need to answer in order to answer the original question.

For the given input question, create a question for similarity search and create a question to perform neo4j graph query.
Here is example:
Question: Find the articles about the photosynthesis and return their titles.
Answers:
similarity_query : Find articles related to photosynthesis.
graph_query: Return titles of the articles

2. Choosing which node types (labels) to search with vector similarity over a Hugging Face Hub knowledge graph in Neo4j.
You will receive a similarity-oriented subquery (similarity_query defined in the previous step). Return the labels whose
embedded metadata are most relevant for that subquery. You may return one or
more labels.
Available labels and what they represent:
{_label_catalog}
Rules:
- Return only labels from the list above.
- If the question is ambiguous or could involve more than one node type, return
  all the plausible ones.
- Never return an empty list.
- When in doubt, return more labels rather than fewer.
Examples:
- "spaces built with gradio" -> ["Space"]
- "datasets about sentiment analysis" -> ["Dataset"]
- "find models for text classification" -> ["Model"]
- "tags related to computer vision" -> ["Tag"]
- "authors named google or meta" -> ["Author"]
- "repositories whose model card mentions quantization" -> ["Repository"]

- "who created the most repositories" -> ["Author", "Repository"]
- "who is the author with most models" -> ["Author", "Model"]
- "gradio demos that use diffusion models" -> ["Space", "Model"]
- "datasets used to train speech recognition models" -> ["Dataset", "Model"]
- "spaces and models related to image generation" -> ["Space", "Model"]
- "tags and datasets about question answering" -> ["Tag", "Dataset"]
- "find authors and their spaces built with streamlit" -> ["Author", "Space"]
- "repositories and tags related to transformers NLP" -> ["Repository", "Tag"]

- "something about summarization on the hub" -> ["Model", "Dataset", "Space", "Tag"]
- "things similar to whisper for audio transcription" -> ["Model", "Dataset", "Space"]
- "content related to llama or llama-like systems" -> ["Model", "Repository", "Space", "Tag"]
- "who publishes the best demos and models for OCR" -> ["Author", "Space", "Model"] 

"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{question}"),
    ]
)

retriever_decompose_router = prompt | structured_llm_router