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


def create_few_shot_prompt(schema):
    '''Create a prompt template without context variable. The suffix provides dynamically selected prompt examples using similarity search'''
    
    prefix = """
    Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.

    [Schema: {schema}]

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    Emit exactly one Cypher statement. A single RETURN, and only at the end.
    For intermediate aggregations or to chain OPTIONAL MATCH, use WITH, never a second RETURN.
    Do not concatenate multiple queries.

    Examples: Here are a few examples of generated Cypher statement for particular questions:
    """

    FEW_SHOT_PROMPT = FewShotPromptTemplate(
        example_selector = example_selector,
        example_prompt = example_prompt,
        prefix=prefix,
        suffix="Question: {question}, \nCypher Query: ",
        input_variables =["question","query","schema"],
    ) 
    return FEW_SHOT_PROMPT

def create_few_shot_prompt_with_context(state: GraphState, schema):
    '''Create a prompt template with context variable. The context variable will be based on the output from vector qa chain'''
    '''The output of vector qa is list of node ids against which to perform graph query'''
    
    context = state["context_refs"]

    # `context` son tuplas (label, node_id) del grafo HF Hub. El prefijo pide
    # un solo Cypher filtrando con IN [...]; el ejemplo fijo de abajo (y el
    # few-shot equivalente en prompt_examples.py) muestra OPTIONAL MATCH + WITH
    # + un solo RETURN, que es el patron que Neo4j exige.
    prefix = """
    Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.
    [Schema: {schema}]
    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    Emit exactly one Cypher statement. A single RETURN, and only at the end.
    For intermediate aggregations or to chain OPTIONAL MATCH, use WITH, never a second RETURN.
    Do not concatenate multiple queries.

    A context is provided from a vector search in a form of tuple (label, node_id) where label is the type of node and node_id is the id of the node in the graph.
    Use the second element of each tuple as a node id. Filter with WHERE <id_property> IN [...ids from context...].
    Here are the contexts: """ + str(context) + """
    Using node ids from the context above, create a Cypher statement and use that to query the graph.

    Example of the required shape (one statement, OPTIONAL MATCH, WITH, one RETURN):
    Question: Using the list of model_ids from the similarity search, retrieve those models with pipeline tag, repository, tags and spaces
    Cypher query: MATCH (m:Model) WHERE m.model_id IN ['bert-base-uncased', 'distilbert-base-uncased'] OPTIONAL MATCH (m)-[:IS_A]->(r:Repository) OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag) WITH m, r, collect(DISTINCT t.name) AS tags OPTIONAL MATCH (s:Space)-[:USES_MODEL]->(m) RETURN m.model_id AS model_id, m.pipeline_tag AS pipeline_tag, r.id AS repo_id, r.name AS repo_name, tags, collect(DISTINCT s.space_id) AS spaces LIMIT 5

    Examples: Here are a few examples of generated Cypher statement for some question examples:
    """

    FEW_SHOT_PROMPT = FewShotPromptTemplate(
        example_selector = example_selector,
        example_prompt = example_prompt,
        prefix=prefix,
        suffix="Question: {question}, \nCypher Query: ",
        input_variables =["question", "query", "schema"],
    ) 
    return FEW_SHOT_PROMPT
