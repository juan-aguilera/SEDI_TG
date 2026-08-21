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


system = f"""You are an expert at choosing which node types (labels) to search with vector
similarity over a Hugging Face Hub knowledge graph in Neo4j.
You will receive a similarity-oriented subquery. Return the labels whose
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



relevant_labels_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{subquery}"),
    ]
)

retriever_router = relevant_labels_prompt | structured_llm_router