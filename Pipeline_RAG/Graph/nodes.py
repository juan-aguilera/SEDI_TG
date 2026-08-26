# Import Python libraries
import os
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings

# Import Custom libraries
from Chains.vector_graph_chain import get_vector_graph_chain
from Chains.graph_qa_chain import get_graph_qa_chain, get_graph_qa_chain_with_context
from Chains.decompose import query_analyzer
from Chains.retriever_router import retriever_router as retriever_router_agent
from Prompts.prompt_template import create_few_shot_prompt, create_few_shot_prompt_with_context
from Prompts.prompt_examples import examples
from Graph.state import GraphState
from Tools.parse_vector_search import DocumentModel
from Indexes.index import ALL_LABELS  # fallback del retriever_router / vector_search


neo4j_url = os.environ.get('NEO4J_URI')
neo4j_user = os.environ.get('NEO4J_USER')
neo4j_pwd = os.environ.get('NEO4J_PASSWORD')
neo4j_db = os.environ.get('NEO4J_DATABASE')

graph = Neo4jGraph(
    url=neo4j_url,
    username=neo4j_user,
    password=neo4j_pwd,
    database=neo4j_db,
)
schema = graph.get_schema()   
llm = AzureChatOpenAI(

    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),     # nombre del deployment en Foundry (gpt-5-mini)
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),       # URL base del recurso de Azure OpenAI
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),               # clave secreta del recurso de Azure
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),       # version de la API (verificar que soporte gpt-5-mini)
    # temperature no se fija: gpt-5-mini solo acepta el valor por defecto (1);
    # pasar temperature=0 explicito hace que Azure devuelva un 400 BadRequestError.
)

EMBEDDING_MODEL = AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"])

def decomposer(state: GraphState):
    
    '''Returns a dictionary of at least one of the GraphState'''    
    '''Decompose a given question to sub-queries'''
    
    question = state["question"]
    subqueries = query_analyzer.invoke(question)
    return {"subqueries": subqueries, "question":question}


def retriever_router(state: GraphState):
    queries = state["subqueries"]
    similarity_query = queries[0].sub_query if queries else state["question"]
    try:
        labels = retriever_router_agent.invoke(
            {"subquery": similarity_query}
        ).labels
    except Exception as e:
        print(f"---RETRIEVER ROUTER FALLO (error: {e}); USANDO TODOS LOS LABELS----")
        labels = []
    labels = [l for l in labels if l in ALL_LABELS] or ALL_LABELS
    print(f"---RETRIEVER ROUTER -> {labels}---")
    return {
        "target_labels": labels,
        "subqueries": queries,
        "question": state["question"],
    }
    
def vector_search(state: GraphState):
    
    ''' Returns a dictionary of at least one of the GraphState'''
    ''' Perform a vector similarity search and return node id as a parsed output'''

    question = state["question"]
    queries = state["subqueries"]
    labels = state.get("target_labels") or ALL_LABELS
    # decomposer no garantiza N subqueries; si faltan, caemos a la pregunta original
    sim_query = queries[0].sub_query if queries else question

    vector_graph_chain = get_vector_graph_chain(labels, top_k=5)

    chain_result = vector_graph_chain.invoke({
        "query": sim_query},
    )
    # Convert the result to a list of DocumentModel instances
    documents = [DocumentModel(**doc.dict()) for doc in chain_result['source_documents']]
    extracted_data = [{"label": doc.metadata.label, "node_id": doc.metadata.node_id} for doc in documents]
    context_refs = [(doc.metadata.label, doc.metadata.node_id) for doc in documents]

    return {"context_refs": context_refs, "documents": extracted_data, 
    "question":question, "subqueries": queries,
    "target_labels": labels}


def  prompt_template(state: GraphState):
    
    '''Returns a dictionary of at least one of the GraphState'''
    '''Create a simple prompt tempalate for graph qa chain'''
    
    question = state["question"]

    # Create a prompt template
    prompt = create_few_shot_prompt(schema)
    
    return {"prompt": prompt, "question":question}
    

def graph_qa(state: GraphState):
    
    ''' Returns a dictionary of at least one of the GraphState '''
    ''' Invoke a Graph QA Chain '''
    
    question = state["question"]
    
    graph_qa_chain = get_graph_qa_chain(state)
    
    result = graph_qa_chain.invoke(
        {
            #"context": graph.schema, 
            "query": question,
        },
    )
    return {"documents": result, "question":question}
    
def prompt_template_with_context(state: GraphState):
    
    '''Returns a dictionary of at least one of the GraphState'''
    '''Create a dynamic prompt template for graph qa with context chain'''
    
    question = state["question"]
    queries = state["subqueries"]

    # Create a prompt template
    prompt_with_context = create_few_shot_prompt_with_context(state,schema)
    
    return {"prompt_with_context": prompt_with_context, "question":question, "subqueries": queries}



def graph_qa_with_context(state: GraphState):
    
    '''Returns a dictionary of at least one of the GraphState'''
    '''Invoke a Graph QA chain with dynamic prompt template'''
    
    question = state["question"]
    queries = state["subqueries"]
    prompt_with_context = state["prompt_with_context"]
    # decomposer no garantiza 2 subqueries; si solo hay una, usamos la pregunta original
    graph_query = queries[1].sub_query if len(queries) > 1 else question

    # Instantiate graph_qa_chain_with_context
    # Pass the GraphState as 'state'. This chain uses state['prompt'] as input argument
    graph_qa_chain = get_graph_qa_chain_with_context(state)
    
    result = graph_qa_chain.invoke(
        {
            "query": graph_query,
        },
    )
    return {"documents": result, "prompt_with_context":prompt_with_context, "subqueries": queries}


