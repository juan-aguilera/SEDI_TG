import os
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI



class Rewrite(BaseModel):
    standalone_question: str = Field(
        ...,
        description="The user's follow-up rewritten as one self-contained question. No pronouns. Concrete ids/names from the documents digest when the follow-up refers to a previous result.",
    )


llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_DECOMPOSER_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
)


structured_llm_rewriter = llm.with_structured_output(Rewrite)


system = """You rewrite follow-up questions so they can be sent to a Hugging Face Hub knowledge graph (Neo4j) without the chat history.

The downstream step will either translate the result to Cypher or run vector search. Your only job is to produce ONE standalone question.

Rules:
- Output a single natural-language question (or a raw Cypher query if the user already wrote Cypher). Never output two sub-questions. Never output JSON, labels, or explanations.
- Keep the same language as the user's current question.
- If the current question is already self-contained (names, ids, and filters are explicit), copy it with at most light cleanup. Do not add constraints the user did not ask for.
- If it uses references ("the first one", "that model", "those", "el primero", "esos"), replace them with concrete ids or names from the documents digest. Rank 1 is the first row, rank 2 the second, and so on.
- Use ONLY ids, names, and values that appear in the documents digest or chat history. Do not invent model_ids, authors, tags, counts, or dates.
- If you cannot resolve a reference because the digest is empty or has no matching row, return the user's current question unchanged.
- Preserve the user's intent (counts, likes, downloads, filters, similarity, new entity). Do not turn a retrieval question into a chat-style "explain this".

Examples (digest has five models, rank 1 = models/google/bert_uncased_L-12_H-768_A-12):
- "how many likes does the first one have?" -> "How many likes does models/google/bert_uncased_L-12_H-768_A-12 have?"
- "now show models by meta" -> "Show models created by meta"
- "find models about text classification" -> "find models about text classification"
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Question: {question}\n\nDocuments digest:\n{documents_digest}\n\nChat history:\n{chat_history}"),
    ]
)

rewrite_chain = prompt | structured_llm_rewriter