# `Graph/nodes.py` explained, function by function

This file walks through every function in `Pipeline_RAG/Graph/nodes.py`, written for someone new
to code. It explains what each line does, not just what the function is "for". It's a companion to
`ARQUITECTURA_Y_WORKFLOW.md` (which explains the overall pipeline) — this one zooms into a single file.

## What this file is, in one sentence

`Graph/nodes.py` defines the six **nodes** of the LangGraph pipeline — the actual step functions
that get wired together in `Graph/graph.py`. Every node follows the same shape: it takes the shared
`state` dictionary, reads a few values out of it, does some work (usually calling an LLM or Neo4j),
and returns a small dictionary of updates that get merged back into `state`.

## Background you need before reading the functions

### The shared "ficha de trabajo" — `GraphState`

`state: GraphState` shows up in every function signature. `GraphState` (defined in `Graph/state.py`)
is a `TypedDict` — basically a dictionary with a fixed, documented shape. Think of it as a work ticket
that starts with just the user's `question` and gets more fields stamped onto it as it passes through
each node:

| Field | What it holds |
|---|---|
| `question` | The user's original question (text). |
| `subqueries` | The two sub-questions the original question got split into. |
| `context_refs` | List of `(label, node_id)` tuples found by the vector search. |
| `documents` | The final result of whichever QA chain answered the question. |
| `prompt` | The few-shot prompt built for the "direct Cypher" branch. |
| `prompt_with_context` | The few-shot prompt built for the "vector search + context" branch. |

A node doesn't need to return every field — only the ones it changed. LangGraph merges whatever a
node returns into the existing `state`.

### The module-level setup (lines 1–42)

Before any of the six functions are defined, the file does some one-time setup that all of them share:

```python
graph = Neo4jGraph(
    url=neo4j_url,
    username=neo4j_user,
    password=neo4j_pwd,
    database=neo4j_db,
)
```
Opens one connection to the local Neo4j database (credentials read from `.env` via `NEO4J_URI`,
`NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`). This is the same Neo4j graph that
`Pipeline_embeddings` populates with Hugging Face Hub data (`Model`, `Dataset`, `Space`, etc.).

```python
llm = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    temperature=0,
)
```
Creates one chat model client, pointed at an Azure OpenAI deployment (not public OpenAI).
`temperature=0` means "give me the most predictable answer every time" — no creative randomness,
which is what you want when the model's job is to output valid Cypher syntax. This `llm` object
isn't actually used inside `nodes.py` itself (each chain builds its own `llm` in its own file), but
it's set up here in case a node needs it directly.

```python
EMBEDDING_MODEL = AzureOpenAIEmbeddings(...)
```
Creates an embeddings client (turns text into vectors of numbers). Also unused directly in this file
today — it's set up for symmetry with the chat model, but the actual embedding work happens inside
`Chains/vector_graph_chain.py` and `Prompts/prompt_template.py`.

Both connections (`graph` and `llm`) are created **once**, when Python first imports this file — not
every time a node function runs. That's why they live at the top of the file instead of inside a
function.

---

## The router isn't in this file

Quick orientation: the very first decision in the pipeline — "should this question go through direct
Cypher generation, or through vector search first?" — happens in `Chains/router.py`, **before** any
node in this file runs. `nodes.py` only contains what happens *after* that choice is made.

---

## Branch A — Direct Graph QA (no vector search)

Two nodes: `prompt_template` → `graph_qa`.

### `prompt_template(state)`

```python
def  prompt_template(state: GraphState):
    question = state["question"]
    prompt = create_few_shot_prompt()
    return {"prompt": prompt, "question":question}
```

**Purpose:** build the instructions (the "prompt") that will later tell the LLM how to translate the
question into Cypher.

- `question = state["question"]` — reads the user's question out of the shared state. (It isn't
  actually used below — it's just re-returned unchanged.)
- `prompt = create_few_shot_prompt()` — calls a function in `Prompts/prompt_template.py`. That
  function builds a `FewShotPromptTemplate`: a block of instructions plus a handful of worked
  examples (`question → Cypher query` pairs), picked dynamically from a pool of 28 examples using a
  similarity-based selector (`MaxMarginalRelevanceExampleSelector`). Giving the LLM examples like this
  ("few-shot learning") makes it far more likely to produce syntactically correct, on-schema Cypher
  than just asking it cold.
- `return {"prompt": prompt, "question": question}` — stores the finished prompt object into
  `state["prompt"]`, ready for the next node to use.

**Reads from state:** `question`. **Writes to state:** `prompt`, `question`.

### `graph_qa(state)`

```python
def graph_qa(state: GraphState):
    question = state["question"]
    graph_qa_chain = get_graph_qa_chain(state)
    result = graph_qa_chain.invoke(
        {
            "query": question,
        },
    )
    return {"documents": result, "question":question}
```

**Purpose:** actually answer the question — turn it into Cypher, run that Cypher against Neo4j, and
capture the result.

- `question = state["question"]` — reads the question again.
- `graph_qa_chain = get_graph_qa_chain(state)` — calls into `Chains/graph_qa_chain.py`. That function
  reads `state["prompt"]` (the prompt built by the previous node) and uses it to assemble a
  `GraphCypherQAChain` — a LangChain object whose whole job is: *question in English → Cypher query →
  run against Neo4j → raw result out*. Key settings on that chain (see `graph_qa_chain.py` for the
  detail): `validate_cypher=True` (checks the generated Cypher is syntactically valid before running
  it), `return_direct=True` (returns Neo4j's raw output instead of having another LLM call summarize
  it), `allow_dangerous_requests=True` (an explicit acknowledgment required by the library, since the
  Cypher being executed was written by an LLM, not a human).
- `result = graph_qa_chain.invoke({"query": question})` — runs the chain. `.invoke(...)` is the
  standard way to "run" any LangChain chain: you hand it a dictionary of inputs (here, just `"query"`,
  the key this particular chain expects) and it returns the output.
- `return {"documents": result, "question": question}` — stores the raw Neo4j result into
  `state["documents"]`. Since this branch ends right after this node (`graph_qa → END` in
  `Graph/graph.py`), `state["documents"]` here becomes the final answer of the whole pipeline for this
  branch.

**Reads from state:** `question`, `prompt` (indirectly, via `get_graph_qa_chain`). **Writes to
state:** `documents`, `question`.

---

## Branch B — Vector search + contextual Graph QA

Four nodes: `decomposer` → `vector_search` → `prompt_template_with_context` → `graph_qa_with_context`.

### `decomposer(state)`

```python
def decomposer(state: GraphState):
    question = state["question"]
    subqueries = query_analyzer.invoke(question)
    return {"subqueries": subqueries, "question":question}
```

**Purpose:** split one question into two smaller, more specific sub-questions — one suited to a
similarity/vector search, one suited to a graph query.

- `question = state["question"]` — reads the original question.
- `subqueries = query_analyzer.invoke(question)` — calls `query_analyzer`, a chain defined in
  `Chains/decompose.py`. Under the hood, that chain sends the question to an Azure LLM with an
  instruction (a "system prompt") telling it: *break this into exactly two sub-queries — one for
  similarity search, one for a follow-up graph query* — and forces the answer into a structured
  `SubQuery` object (just one field: `sub_query: str`) via `bind_tools`. The result is a **list** of
  `SubQuery` objects (in practice, two of them).
- `return {"subqueries": subqueries, "question": question}` — stores that list into
  `state["subqueries"]` so later nodes in this branch can use `subqueries[0]` (similarity search) and
  `subqueries[1]` (graph query) separately.

**Reads from state:** `question`. **Writes to state:** `subqueries`, `question`.

### `vector_search(state)`

```python
def vector_search(state: GraphState):
    question = state["question"]
    queries = state["subqueries"]

    vector_graph_chain = get_vector_graph_chain()

    chain_result = vector_graph_chain.invoke({
        "query": queries[0].sub_query},
    )
    documents = [DocumentModel(**doc.dict()) for doc in chain_result['source_documents']]
    extracted_data = [{"label": doc.metadata.label, "node_id": doc.metadata.node_id} for doc in documents]
    context_refs = [(doc.metadata.label, doc.metadata.node_id) for doc in documents]

    return {"context_refs": context_refs, "documents": extracted_data, "question":question, "subqueries": queries}
```

**Purpose:** take the *first* sub-question (the one meant for similarity search) and find the graph
nodes whose text is most similar to it, using vector embeddings rather than exact Cypher matching.
This is useful for "fuzzy" questions that don't mention exact ids or names (e.g. "models for text
classification").

- `question`, `queries = state["subqueries"]` — reads the question and the two sub-queries produced
  by `decomposer`.
- `vector_graph_chain = get_vector_graph_chain()` — calls `Chains/vector_graph_chain.py`, which
  assembles a `RetrievalQA` chain: given a text query, it (1) embeds it, (2) searches a Neo4j vector
  index for the `k=3` most similar `Model` nodes (the index was built ahead of time by
  `Pipeline_embeddings`), and (3) asks an LLM to write a text answer using those nodes as context.
  `return_source_documents=True` on that chain means it also hands back the raw matched nodes, not
  just the LLM's prose answer.
- `chain_result = vector_graph_chain.invoke({"query": queries[0].sub_query})` — runs the search using
  **only the first** sub-query (`queries[0]`); the second one is reserved for the later Cypher step.
- `documents = [DocumentModel(**doc.dict()) for doc in chain_result['source_documents']]` — the raw
  matched nodes come back as generic LangChain `Document` objects; this line converts each one into a
  `DocumentModel` (a stricter, project-defined shape from `Tools/parse_vector_search.py`) so the code
  below can rely on it having `.metadata.label` and `.metadata.node_id` fields.
- `extracted_data = [...]` — builds a plain list of `{"label": ..., "node_id": ...}` dictionaries, one
  per matched node — a simple, readable version of what was found.
- `context_refs = [...]` — builds the same information as a list of `(label, node_id)` tuples instead.
  This is the form the *next* node actually needs, to plug straight into a prompt as "here's what the
  vector search already found."
- The return statement stores `context_refs` and `documents` (here, `extracted_data` — a slightly
  confusing naming collision with `state["documents"]`'s other use in Branch A, since here it holds
  the *search hits*, not a final answer) plus passes `question` and `subqueries` through unchanged.

**Reads from state:** `question`, `subqueries`. **Writes to state:** `context_refs`, `documents`,
`question`, `subqueries`.

### `prompt_template_with_context(state)`

```python
def prompt_template_with_context(state: GraphState):
    question = state["question"]
    queries = state["subqueries"]

    prompt_with_context = create_few_shot_prompt_with_context(state)

    return {"prompt_with_context": prompt_with_context, "question":question, "subqueries": queries}
```

**Purpose:** build a second, *smarter* prompt for the LLM — one that already knows which nodes the
vector search just found, so the Cypher it generates next can reference them directly.

- `question`, `queries = state["subqueries"]` — read through, not transformed here.
- `prompt_with_context = create_few_shot_prompt_with_context(state)` — calls the "with context"
  version of the prompt builder, in `Prompts/prompt_template.py`. That function reads
  `state["context_refs"]` (the `(label, node_id)` tuples `vector_search` just produced) and weaves
  them directly into the prompt's instructions, telling the LLM something like *"here are node ids
  found by a prior search — use them to build your Cypher query"* — on top of the same 28 few-shot
  examples used in Branch A.
- `return {"prompt_with_context": ..., ...}` — stores the finished, context-aware prompt into
  `state["prompt_with_context"]`.

**Reads from state:** `question`, `subqueries`, `context_refs` (indirectly, inside
`create_few_shot_prompt_with_context`). **Writes to state:** `prompt_with_context`, `question`,
`subqueries`.

### `graph_qa_with_context(state)`

```python
def graph_qa_with_context(state: GraphState):
    queries = state["subqueries"]
    prompt_with_context = state["prompt_with_context"]

    graph_qa_chain = get_graph_qa_chain_with_context(state)

    result = graph_qa_chain.invoke(
        {
            "query": queries[1].sub_query,
        },
    )
    return {"documents": result, "prompt_with_context":prompt_with_context, "subqueries": queries}
```

**Purpose:** the final step of Branch B — take the *second* sub-question (the one meant for the graph
query) plus the context-aware prompt, generate Cypher, run it against Neo4j, and return the answer.

- `queries = state["subqueries"]`, `prompt_with_context = state["prompt_with_context"]` — reads both
  values produced earlier in this branch.
- `graph_qa_chain = get_graph_qa_chain_with_context(state)` — same idea as `graph_qa` in Branch A, but
  built with `state["prompt_with_context"]` instead of the plain `state["prompt"]`, so the Cypher
  generator has the vector-search hits available as extra context.
- `result = graph_qa_chain.invoke({"query": queries[1].sub_query})` — runs the chain using
  `queries[1]` — the **second** sub-query (the graph-query-oriented one). This is the counterpart to
  `vector_search`'s use of `queries[0]`: between the two nodes, both sub-questions from `decomposer`
  end up used exactly once.
- `return {"documents": result, ...}` — stores the raw Neo4j result into `state["documents"]`. Since
  this node is the last step before `END` in Branch B, this becomes the pipeline's final answer for
  this branch.

**Reads from state:** `subqueries`, `prompt_with_context`. **Writes to state:** `documents`,
`prompt_with_context`, `subqueries`.

---

## Putting it together — one question, traced through Branch B

1. User asks a question → `decomposer` splits it into `subqueries[0]` (similarity) and
   `subqueries[1]` (graph).
2. `vector_search` embeds `subqueries[0]`, finds the 3 most similar `Model` nodes in Neo4j, and
   records their `(label, node_id)` as `context_refs`.
3. `prompt_template_with_context` builds a Cypher-generation prompt that includes those
   `context_refs` as hints.
4. `graph_qa_with_context` feeds `subqueries[1]` plus that prompt to an LLM, gets back a Cypher query,
   runs it against Neo4j, and the raw result becomes the final `documents` — the answer returned to
   whoever called `app.invoke({"question": ...})`.
