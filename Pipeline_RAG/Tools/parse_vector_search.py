# Import Python Libraries
from pydantic import BaseModel
from typing import List

# Import Custom Libraries
from Graph.state import GraphState

# Metadata de un Document devuelto por el retriever de Indexes/index.py:
# node_id y label vienen directo del retrieval_query (ya estructurados,
# no hace falta parsear texto con regex como se hacia antes con article_id/topics).
class Metadata(BaseModel):
    node_id: str
    label: str

class DocumentModel(BaseModel):
    page_content: str
    metadata: Metadata

class ResultModel(BaseModel):
    documents: List[DocumentModel]
    

def create_context(state: GraphState):
    """Originally designed to be a node, but not used as node anymore, merged to vector search step"""
    chain_result = state["documents"]
    question = state["question"]

    # Convert the result to a list of DocumentModel instances
    documents = [DocumentModel(**doc.dict()) for doc in chain_result['source_documents']]
    extracted_data = [{"title": doc.extract_title(), "article_id": doc.metadata.article_id} for doc in documents]
    article_ids = [("article_id", doc.metadata.article_id) for doc in documents]
    
    return {"article_ids": article_ids, "question":question, "subqueries": queries}