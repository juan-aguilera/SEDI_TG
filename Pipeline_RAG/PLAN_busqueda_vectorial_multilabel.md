# Generalizar la búsqueda vectorial de Pipeline_RAG a todos los nodos del HF Hub graph

## Contexto

Hoy `Chains/vector_graph_chain.py` está construido sobre `Indexes/index.py::get_neo4j_vector_index()`, que:
- Usa variables de entorno `AURA_*` que **no existen** en el `.env` del repo.
- Apunta a un label `Article` con propiedad `embedding_vectors`, creada al vuelo con `Neo4jVector.from_existing_graph` usando OpenAI público.

Esto no tiene relación con el grafo que realmente está poblado hoy: el grafo de Hugging Face Hub (`Model`, `Dataset`, `Space`, `Repository`, `Author`, `Tag`) en el Neo4j **local** (`NEO4J_*`), donde `Pipeline_embeddings/load_to_neo4j.py` ya creó 6 índices vectoriales — uno por label (`vec_model_embedding`, `vec_dataset_embedding`, `vec_space_embedding`, `vec_repository_embedding`, `vec_author_embedding`, `vec_tag_embedding`), todos sobre `n.embedding`, dimensión 1536, coseno, generados con **Azure OpenAI** (`AZURE_EMBEDDING_DEPLOYMENT`).

El objetivo es que la búsqueda vectorial deje de estar limitada a "solo artículos" y en su lugar busque, entre **todos** los tipos de nodo del HF Hub graph, cuáles son los más relevantes para la consulta — sin restringir de antemano a un subconjunto de labels (la relevancia la decide el score, no un filtro fijo).

Decisiones ya confirmadas:
- **Labels**: todos (Model, Dataset, Space, Repository, Author, Tag). No se excluye ninguno de antemano.
- **Fusión de resultados**: Top-K **global** — se juntan los candidatos de los 6 índices y se toman los K de mejor score en conjunto (no top-K fijo por label).
- **Alcance**: solo `vector_graph_chain` y su cadena de soporte. La etapa posterior de generación de Cypher "con contexto" (`create_few_shot_prompt_with_context` + ejemplos few-shot de `Prompts/prompt_examples.py`) sigue asumiendo el esquema de artículos académicos (OpenAlex) y **no se toca su lógica/ejemplos** en esta tanda — solo se ajusta el nombre de la clave de estado que lee, para no romper el wiring (ver más abajo). Adaptar esos ejemplos few-shot al esquema Model/Dataset/Space queda como trabajo pendiente, explícitamente anotado en el código.

Nota importante de correctitud: como los embeddings guardados en Neo4j se generaron con Azure OpenAI, la pregunta del usuario debe embeberse con el **mismo modelo/deployment** para que la similitud coseno tenga sentido. Usar `OpenAIEmbeddings` (OpenAI público) para la consulta, como hace hoy `index.py`, produciría vectores no comparables.

## Por qué una consulta Cypher manual y no `Neo4jVector.from_existing_index`

Se verificó la librería instalada (`langchain-neo4j` 0.10.0 + `neo4j` 6.2.0): `Neo4jVector` (tanto `from_existing_graph` como `from_existing_index`) solo soporta **un** label por índice — no existe un índice vectorial multi-label en Neo4j ni soporte para eso en esta versión de la librería. Para buscar "a través de" los 6 índices hay que consultarlos todos y fusionar resultados manualmente. La forma más simple y eficiente es un solo round-trip a Neo4j:

```cypher
UNWIND $indexNames AS idxName
CALL (idxName) {
  CALL db.index.vector.queryNodes(idxName, $topK, $queryVector) YIELD node, score
  RETURN node, score
}
RETURN node, score, labels(node) AS labels
ORDER BY score DESC
LIMIT $topK
```
(Verificar en implementación si la sintaxis de subconsulta con scope `CALL (idxName) { ... }` es soportada por la versión de Neo4j server en uso; si no, usar la forma equivalente `CALL { WITH idxName ... }`.)

## Cambios propuestos

### 1. `Pipeline_RAG/Indexes/index.py` — reescribir

Reemplaza las 4 funciones actuales (basadas en `AURA_*` + `Article`/`Title`/`Abstract`/`Topic`, ninguna de las cuales refleja el grafo real y 3 de las 4 son código muerto) por:

- Conexión reutilizando el mismo patrón que ya usan `Graph/nodes.py` y `Chains/graph_qa_chain.py`: `Neo4jGraph(url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASSWORD, database=NEO4J_DATABASE)`.
- `AzureOpenAIEmbeddings` (de `langchain_openai`) configurado con `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_API_VERSION` / `AZURE_EMBEDDING_DEPLOYMENT` — mismas variables que usa `Pipeline_embeddings/generate_embeddings.py`, para que la pregunta caiga en el mismo espacio vectorial que los nodos.
- Un pequeño `LABEL_CONFIG` (duplicado mínimo, solo lo necesario — `id_key` por label, tomado del `NODE_CONFIG` de `Pipeline_embeddings/generate_embeddings.py`: `Model→model_id`, `Dataset→dataset_id`, `Space→space_id`, `Repository→id`, `Author→username`, `Tag→name`) y la lista de nombres de índice `vec_<label.lower()>_embedding`.
- Una función `get_multi_label_vector_retriever(top_k=5)` que construye y devuelve un `Retriever` (ver punto 2).

### 2. Nuevo retriever multi-label (puede vivir en el mismo `index.py`)

Clase que extiende `langchain_core.retrievers.BaseRetriever`, con `_get_relevant_documents(query)`:
1. Embebe `query` con `AzureOpenAIEmbeddings`.
2. Ejecuta la consulta Cypher de arriba vía `Neo4jGraph.query(...)`, pasando la lista de los 6 nombres de índice, el vector y `top_k` — obtiene directamente el Top-K **global** ya ordenado por score.
3. Por cada registro devuelto, arma un `Document`:
   - `page_content`: texto genérico construido a partir de las propiedades del nodo (reutilizando la idea de `build_text()` de `generate_embeddings.py`, pero sin necesidad de ser idéntico — puede ser simplemente `"{label}: " + " | ".join(f"{k}: {v}" for k,v in props excluyendo 'embedding')`).
   - `metadata`: `{"label": <label real, tomado de LABEL_CONFIG/idxName, no de labels(node) que puede traer labels extra>, "node_id": <valor de la propiedad id_key correspondiente>, "score": score}`.

Esto reemplaza `vector_index.as_retriever(search_kwargs={'k':3})` en `vector_graph_chain.py`.

### 3. `Pipeline_RAG/Chains/vector_graph_chain.py`

- Sustituir `vector_index = index.get_neo4j_vector_index()` por `retriever = index.get_multi_label_vector_retriever(top_k=5)` (o el nombre final que se le dé).
- `RetrievalQA.from_chain_type(..., retriever=retriever, ...)` se mantiene igual en estructura (`chain_type="stuff"`, `return_source_documents=True`).
- El LLM de esta cadena (`ChatOpenAI(model="gpt-3.5-turbo", api_key=OPENAI_API_KEY)`) depende de `OPENAI_API_KEY`, que **no está** en el `.env`. Se recomienda cambiarlo a `AzureChatOpenAI` con el mismo patrón ya usado en `Chains/graph_qa_chain.py` (`AZURE_CHAT_DEPLOYMENT`, etc.), para que la cadena efectivamente pueda ejecutarse con las credenciales que sí existen hoy.

### 4. `Pipeline_RAG/Tools/parse_vector_search.py` — generalizar

- `Metadata` pasa de `{topics: str, article_id: str}` a `{label: str, node_id: str, score: float}`.
- Se elimina el hack de `extract_title()` (regex `title: (.+)` sobre `page_content`) — ya no hace falta, `label`/`node_id` vienen estructurados en la metadata, no hay que parsear texto.
- Se elimina la función `create_context()` (muerta y rota: referencia una variable `queries` que nunca se define) y `ResultModel` (no usado en ningún otro lado).

### 5. `Pipeline_RAG/Graph/nodes.py::vector_search`

- `documents = [DocumentModel(**doc.dict()) for doc in chain_result['source_documents']]` se mantiene, pero ahora valida contra la `Metadata` genérica.
- `extracted_data` pasa a ser `[{"label": doc.metadata.label, "node_id": doc.metadata.node_id, "score": doc.metadata.score} for doc in documents]`.
- La lista que hoy se llama `article_ids` (tuplas `("article_id", id)`) pasa a `context_refs` (tuplas `(label, node_id)`), reflejando que ya no son solo artículos.
- Se devuelve `{"context_refs": context_refs, "documents": extracted_data, "question": question, "subqueries": queries}`.




