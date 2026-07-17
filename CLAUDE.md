# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This is a graduate thesis (TG / "Trabajo de Grado") codebase building a GraphRAG (Graph Retrieval-Augmented Generation) system over a Neo4j knowledge graph. The graph is populated from Hugging Face Hub metadata (models, datasets, spaces, repositories, authors, tags) and from academic article metadata (OpenAlex). There are two independent pipelines:

- **`Pipeline_embeddings/`** — builds the knowledge graph's vector layer: pulls nodes from Neo4j, embeds them with **Azure OpenAI**, and writes the vectors + vector indexes back to Neo4j.
- **`Pipeline_RAG/`** — a LangChain/LangGraph question-answering workflow over the same Neo4j graph, using **OpenAI** (not Azure) directly, with a router that dispatches to graph QA or vector-search-augmented graph QA.

These two pipelines use different LLM providers and different environment variable conventions — see "Environment variables" below before touching either one.

`Articulos/` and `Documentacion Avance TG/` hold reference papers and thesis progress documents (Word/Excel/PowerPoint) — not code, only useful for background context on the GraphRAG design.

## Environment & setup

- Python virtualenv lives in `.venv/` (already created via standard `venv`). Activate with `.venv/Scripts/activate` (or `Activate.ps1` in PowerShell).
- Dependencies are consolidated in the root `requirements.txt` (covers both pipelines: `openai`, `neo4j`, `pandas`, `pyarrow`, `numpy`, `tenacity`, `python-dotenv`, `tqdm`, `langchain`, `langchain-community`, `langchain-openai`, `langgraph`, `pydantic`, `chromadb`). Install with:
  ```
  pip install -r requirements.txt
  ```
- Secrets are loaded from a root `.env` via `python-dotenv` (`load_dotenv()` is called in each entry-point script/module). Never commit `.env`; it's already git-ignored, along with `.venv/`, `__pycache__/`, `embeddings_out/`, and `*.parquet`.

### Environment variables

`Pipeline_embeddings/` (Azure OpenAI + Neo4j, using `NEO4J_*` names):
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_EMBEDDING_DEPLOYMENT`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` (optional, defaults to `"neo4j"`)

`Pipeline_RAG/` (plain OpenAI + Neo4j AuraDB, using `AURA_*` names):
- `OPENAI_API_KEY`
- `AURA_CONNECTION_URI`, `AURA_USERNAME`, `AURA_PASSWORD`

These two naming schemes point at the same logical Neo4j instance but are **not interchangeable** in code — each module reads its own hardcoded variable names, so both sets must be present in `.env` to run both pipelines.

## Running the pipelines

There is no test suite, linter, or build step configured in this repo — validation is done by running the scripts/notebooks directly against a live Neo4j + LLM backend.

**Embeddings pipeline** (run in order — Stage 1 then Stage 2 — from `Pipeline_embeddings/`):
```
python generate_embeddings.py --label Model      # or Dataset, Space, Repository, Author, Tag, or "all"
python load_to_neo4j.py --label Model            # or "all" (auto-discovers labels from embeddings_out/*.parquet)
```
- `generate_embeddings.py` is checkpoint/resume-safe: it reads any existing `embeddings_out/embeddings_<Label>.parquet`, skips already-embedded node `_eid`s, and appends new rows. Safe to interrupt and re-run.
- Node text-construction config (which properties are embedded per label, and the id property used) lives in `NODE_CONFIG` at the top of `generate_embeddings.py` — edit this dict to change what gets embedded, not the extraction/embedding logic below it.
- `load_to_neo4j.py` writes vectors to the `embedding` node property via `elementId()` matching, then creates a cosine-similarity vector index per label (`vec_<label>_embedding`, dimension 1536 for `text-embedding-3-small`).

**GraphRAG QA pipeline** (`Pipeline_RAG/`): driven interactively from `00_run_script.ipynb`, which imports the compiled LangGraph app and invokes it with a question:
```python
from Graph.graph import app
result = app.invoke({"question": "find top 5 cited articles and return their title"})
```

## Pipeline_RAG architecture

The QA workflow is a LangGraph `StateGraph` (compiled in `Graph/graph.py`) over a shared `GraphState` TypedDict (`Graph/state.py`: `question`, `documents`, `article_ids`, `prompt`, `prompt_with_context`, `subqueries`). A router chain (`Chains/router.py`) classifies the incoming question as `"vector search"` or `"graph query"` and picks one of two branches:

- **Graph QA branch** (direct Cypher QA, no vector search): `prompt_template` → `graph_qa` → END. Builds a few-shot Cypher-generation prompt (`Prompts/prompt_template.py::create_few_shot_prompt`, examples from `Prompts/prompt_examples.py`, selected via `MaxMarginalRelevanceExampleSelector` over a Chroma store) and runs it through a `GraphCypherQAChain` (`Chains/graph_qa_chain.py`).
- **Vector-search-augmented branch**: `decomposer` → `vector_search` → `prompt_template_with_context` → `graph_qa_with_context` → END.
  - `decomposer` (`Chains/decompose.py`) splits the question into two sub-queries: one for similarity search, one for the follow-up graph query.
  - `vector_search` runs a `RetrievalQA` chain (`Chains/vector_graph_chain.py`) against a Neo4j vector index (`Indexes/index.py::get_neo4j_vector_index`, over `Article` nodes' `title`/`abstract`) and parses results into `DocumentModel`/`Metadata` (`Tools/parse_vector_search.py`) to extract `article_id`s.
  - `prompt_template_with_context` builds a Cypher-generation prompt seeded with those `article_id`s as context (`create_few_shot_prompt_with_context`), then `graph_qa_with_context` runs it through another `GraphCypherQAChain`.

All node functions live in `Graph/nodes.py` and are wired into the graph in `Graph/graph.py`; node/edge name constants are centralized in `Graph/labels.py` — use those constants rather than string literals when adding nodes or edges. `Tools/tools.py` defines `@tool`-decorated functions for a future agent-based version but is dead code today (undefined `AURA_CONNECTION_URI` etc., not imported anywhere) — don't assume it's wired in.

The article/author/institution graph schema referenced by the few-shot Cypher examples (`Prompts/prompt_examples.py`) uses labels `Article`, `Author`, `Institution`, `Journal`, `Title`, `Year`, `Funder`, `Country` with relationships like `HAS_TITLE`, `WRITTEN_BY`, `AFFILLIATED_TO` (note: misspelled in the actual data), `PUBLISHED_IN`, `YEAR_PUBLISHED`, `FUNDED_BY`, `IS_FROM` — this is a *different* graph/schema than the Hugging Face Hub graph (`Model`/`Dataset`/`Space`/`Repository`/`Author`/`Tag`) that `Pipeline_embeddings` operates on.

## Pipeline_embeddings architecture

Two-stage, label-driven process over Hugging Face Hub node labels (`Model`, `Dataset`, `Space`, `Repository`, `Author`, `Tag`):

1. `generate_embeddings.py`: pages through Neo4j nodes for a label (`FETCH_PAGE_SIZE=5000`), builds a representative text string per node from `NODE_CONFIG[label]["text_props"]`, embeds in batches (`EMBED_BATCH_SIZE=128`) via Azure OpenAI with retry/backoff (`tenacity`, handling `RateLimitError`/`APIConnectionError`/`APITimeoutError`/`InternalServerError`), and flushes to `embeddings_out/embeddings_<Label>.parquet` every 10k rows.
2. `load_to_neo4j.py`: reads the parquet, `UNWIND`s rows in batches of 1000 to set the `embedding` vector property by `elementId()`, then creates a Neo4j vector index per label.

`embeddings_out/*.parquet` is git-ignored (regeneratable output, not source).
