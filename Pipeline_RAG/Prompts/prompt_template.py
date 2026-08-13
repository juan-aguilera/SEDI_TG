import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_core.example_selectors import SemanticSimilarityExampleSelector, MaxMarginalRelevanceExampleSelector
from Prompts.prompt_examples import examples
from langchain_openai import AzureOpenAIEmbeddings

# Import Custom Libraries
from Graph.state import GraphState

EMBEDDING_MODEL = AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
    )

# Instantiate a example selector
# input_keys=["question"]: GraphCypherQAChain llama a select_examples con un dict que
# ademas de "question" trae "examples" (None) y "schema" (texto largo). Sin input_keys,
# el selector intenta unir TODOS los valores del dict con " ".join(...) y explota con
# "TypeError: sequence item 0: expected str instance, NoneType found" apenas "examples"
# viene en None. Restringir a "question" hace que solo se compare contra la pregunta.
example_selector = MaxMarginalRelevanceExampleSelector.from_examples(
    examples = examples,
    embeddings = EMBEDDING_MODEL,
    vectorstore_cls = Chroma,
    k=5,
    input_keys=["question"],
)

# Configure a formatter
example_prompt = PromptTemplate(
    input_variables=["question", "query"],
    template="Question: {question}\nCypher query: {query}"
)


def create_few_shot_prompt():
    '''Create a prompt template without context variable. The suffix provides dynamically selected prompt examples using similarity search'''
    
    prefix = """
    Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.

    Examples: Here are a few examples of generated Cypher statements for particular questions:
    """

    FEW_SHOT_PROMPT = FewShotPromptTemplate(
        example_selector = example_selector,
        example_prompt = example_prompt,
        prefix=prefix,
        suffix="Question: {question}, \nCypher Query: ",
        input_variables =["question","query"],
    ) 
    return FEW_SHOT_PROMPT

def create_few_shot_prompt_with_context(state: GraphState):
    '''Create a prompt template with context variable. The context variable will be based on the output from vector qa chain'''
    '''The output of vector qa is list of node ids against which to perform graph query'''
    
    context = state["context_refs"]

    # NOTA: el prefijo de abajo y los ejemplos few-shot de Prompts/prompt_examples.py
    # todavia asumen ids estilo OpenAlex ("W...", esquema de articulos). Ahora
    # `context` trae tuplas (label, node_id) reales del grafo de HF Hub (ej.
    # ("Model", "bert-base-uncased")), pero el LLM no tiene ejemplos de como usar
    # esos ids en Cypher contra Model/Dataset/Space. Adaptar el texto y los
    # ejemplos few-shot al esquema real queda fuera de alcance de este cambio
    # (ver PLAN_busqueda_vectorial_multilabel.md punto 7 y ARQUITECTURA_Y_WORKFLOW.md).
    prefix = f"""
    Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    
    A context is provided from a vector search in a form of tuple (label,node_id) where label is the type of node and node_id is the id of the node in the graph.
    Use the second element of the tuple as a node id to construct the Cypher statement. 
    Here are the contexts: {context}

    Using node id from the context above, create cypher statements and use that to query with the graph.
    Examples: Here are a few examples of generated Cypher statements for some question examples:
    """

    FEW_SHOT_PROMPT = FewShotPromptTemplate(
        example_selector = example_selector,
        example_prompt = example_prompt,
        prefix=prefix,
        suffix="Question: {question}, \nCypher Query: ",
        input_variables =["question", "query"],
    ) 
    return FEW_SHOT_PROMPT
