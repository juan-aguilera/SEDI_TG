from typing import List, TypedDict


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        documents: result of chain
        context_refs: list of (label, node_id) tuples from vector search
        prompt: prompt template object
        prompt_with_context: prompt template with context from vector search
        subqueries: decomposed queries
    """

    question: str
    documents: dict
    context_refs: List[tuple]
    prompt: object
    prompt_with_context: object
    subqueries: object

    """
    GraphState es el "estado compartido" que va pasando por todo el flujo del pipeline. Está definido
      en Pipeline_RAG/Graph/state.py.

Qué es, en simple

Es un diccionario con forma fija: una caja de datos donde cada casilla tiene un nombre y un tipo definido de antemano.
 Técnicamente es un TypedDict de Python — un diccionario normal,
pero anotado para que quede documentado qué llaves puede tener y qué tipo de dato va en cada una.

Piénsalo como una ficha de trabajo que se va llenando a medida que la pregunta avanza por los pasos del sistema. 


Las casillas que tiene

┌─────────────────────┬─────────────────────────────────────────────────────────────────────────────┐
│       Casilla       │                                 Qué guarda                                  │
├─────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ question            │ La pregunta original del usuario (texto).                                   │
├─────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ documents           │ El resultado devuelto por una cadena (la respuesta/datos).                  │
├─────────────────────┼────────────────────────────────────────────────┤
│ context_refs        │ Lista de tuplas (label, node_id) encontradas en la búsqueda por similitud. │
├─────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ prompt              │ Las instrucciones (few-shot prompt) armadas p. │
├─────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ prompt_with_context │ Las mismas instrucciones, pero ya con contexto extra incluido.              │
├─────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ subqueries          │ Las sub-preguntas en que se descompuso la pregunta original.                │
└─────────────────────┴─────────────────────────────────────────────────────────────────────────────┘

Cómo se usa en graph_qa_chain.py

Fíjate que las dos funciones reciben state: GraphState y de ahí solo sacan una casilla:

def get_graph_qa_chain(state: GraphState):
    prompt = state["prompt"]              # lee la casilla "prompt" d
    ...

def get_graph_qa_chain_with_context(state: GraphState):
    prompt_with_context = state["prompt_with_context"]   # lee la casilla "prompt_with_context"
    ...

O sea: GraphState no "hace" nada por sí solo, es solo el contenedor que transporta la información entre pasos.
 En este archivo se usa nada más para leer las instrucciones (prompt / prompt_with_context) que otros pasos 
 anteriores ya dejaron listas en la ficha.

Ese : GraphState que aparece después del nombre del parámetro es una  lector (y a los editores de código) 
"aquí espero recibir una fichacon esa forma". No obliga en tiempo de ejecución — es documentación qr errores.
"""