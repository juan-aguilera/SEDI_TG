# Import Python Libraries
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph


# Import Custom Libraries
from Chains.router import question_router
from Graph.state import GraphState
from Graph.labels import VECTOR_SEARCH, GRAPH_QA, GRAPH_QA_WITH_CONTEXT, PROMPT_TEMPLATE, PROMPT_TEMPLATE_WITH_CONTEXT, GENERATE, DECOMPOSE_AND_ROUTE, REWRITE_GRAPH, REWRITE_VECTOR, INGEST
from Graph.nodes import vector_search, graph_qa, graph_qa_with_context, prompt_template, prompt_template_with_context, generate, decompose_and_route, rewrite, ingest
from Tools.session_memory import recent_messages, messages_as_text, documents_digest


load_dotenv()

def route_question(state: GraphState):
    print("---ROUTE QUESTION---")
    source = question_router.invoke({
        "question": state["question"],
        "chat_history": messages_as_text(recent_messages(state.get("messages") or [])),
        "documents_digest": documents_digest(state.get("documents")),
    })
    if source.datasource == "vector search":
        print("---ROUTE QUESTION TO VECTOR SEARCH---")
        return REWRITE_VECTOR
    elif source.datasource == "graph query":
        print("---ROUTE QUESTION TO GRAPH QA---")
        return REWRITE_GRAPH
    elif source.datasource == "chat":
        print("---ROUTE QUESTION TO CHAT---")
        return GENERATE

workflow = StateGraph(GraphState)

# Nodes for graph qa
workflow.add_node(PROMPT_TEMPLATE, prompt_template)
workflow.add_node(GRAPH_QA, graph_qa)
workflow.add_node(REWRITE_GRAPH, rewrite)


# Nodes for graph qa with vector search

workflow.add_node(REWRITE_VECTOR, rewrite)
workflow.add_node(DECOMPOSE_AND_ROUTE, decompose_and_route)
workflow.add_node(VECTOR_SEARCH, vector_search)
workflow.add_node(PROMPT_TEMPLATE_WITH_CONTEXT, prompt_template_with_context)
workflow.add_node(GRAPH_QA_WITH_CONTEXT, graph_qa_with_context)
workflow.add_node(GENERATE, generate)

# INGEST ENTRY POINT: every turn starts here, then route_question branches.
workflow.add_node(INGEST, ingest)
workflow.set_entry_point(INGEST)
workflow.add_conditional_edges(
    INGEST,
    route_question,
    {
        REWRITE_VECTOR: REWRITE_VECTOR,
        REWRITE_GRAPH: REWRITE_GRAPH,
        GENERATE: GENERATE,
    },
)

# Edges for graph qa with vector search
"""
workflow.add_edge(DECOMPOSER, RETRIEVER_ROUTER)
workflow.add_edge(RETRIEVER_ROUTER, VECTOR_SEARCH)
"""
workflow.add_edge(REWRITE_VECTOR, DECOMPOSE_AND_ROUTE)
workflow.add_edge(DECOMPOSE_AND_ROUTE, VECTOR_SEARCH)
workflow.add_edge(VECTOR_SEARCH, PROMPT_TEMPLATE_WITH_CONTEXT)
workflow.add_edge(PROMPT_TEMPLATE_WITH_CONTEXT, GRAPH_QA_WITH_CONTEXT)
workflow.add_edge(GRAPH_QA_WITH_CONTEXT, GENERATE)
workflow.add_edge(GENERATE, END)

# Edges for graph qa
workflow.add_edge(REWRITE_GRAPH, PROMPT_TEMPLATE)
workflow.add_edge(PROMPT_TEMPLATE, GRAPH_QA)
workflow.add_edge(GRAPH_QA, GENERATE)
workflow.add_edge(GENERATE, END)

app = workflow.compile()

#app.get_graph().draw_mermaid_png(output_file_path="graph.png")
