# Plan — Retriever Router: selección de labels para la búsqueda vectorial

> Estado: **propuesta, no implementada**. Este documento describe el cambio; no se ha tocado código.

## Contexto

Hoy la rama vectorial de `Pipeline_RAG` está clavada a un solo label. `Indexes/index.py` tiene un
`LABEL_CONFIG` con una sola entrada (`Model`), y `Chains/vector_graph_chain.py` instancia el índice
**a nivel de módulo** (`vector_index = index.get_neo4j_vector_index()`, línea 46), es decir: el label
queda fijado en tiempo de import y no puede cambiar por pregunta.

Mientras tanto, `Pipeline_embeddings/load_to_neo4j.py` ya creó **6 índices vectoriales** en el Neo4j
local — `vec_model_embedding`, `vec_dataset_embedding`, `vec_space_embedding`,
`vec_repository_embedding`, `vec_author_embedding`, `vec_tag_embedding` — todos sobre `n.embedding`,
1536 dimensiones, coseno, generados con el mismo deployment de Azure. Cinco de los seis están
inaccesibles desde el pipeline de QA.

El objetivo es insertar, **después del `decomposer`**, un nodo *retriever router* que lea la
sub-consulta de similitud y decida sobre qué label(s) correr la búsqueda vectorial: si la pregunta
habla de spaces, se busca en `vec_space_embedding`; si habla de datasets, en `vec_dataset_embedding`;
etc. Resultado esperado: la búsqueda vectorial deja de devolver siempre `Model` y empieza a devolver
el tipo de nodo que la pregunta realmente pide.

**Nota sobre la decisión de diseño.** `OPINION_seleccion_labels_busqueda_vectorial.md` (en este mismo
folder) recomendaba *no* añadir un clasificador LLM de labels, por el riesgo de excluir en forma
irreversible un label relevante. Este plan adopta el router igual, pero neutraliza ese riesgo con dos
decisiones explícitas: **selección multi-label** (1..N labels, no uno solo) y **fallback a los 6
labels** ante cualquier ambigüedad o fallo. Con eso, el peor caso del router es exactamente el
comportamiento Top-K global que proponía `PLAN_busqueda_vectorial_multilabel.md` — nunca peor.

## Decisiones tomadas

| Decisión | Valor |
|---|---|
| Cardinalidad | 1..N labels (`List[Literal[...]]`) |
| Fusión de resultados | Búsqueda por cada label elegido → merge → orden por score → Top-K global |
| Fallback | Los 6 labels (lista vacía, excepción del LLM, o label desconocido) |
| Alcance | Incluye el arreglo del prompt downstream `create_few_shot_prompt_with_context` |

## Flujo resultante

```
question
   │
   ├─ route_question (Chains/router.py, conditional entry point) ── "graph query" ──> prompt_template → graph_qa → END
   │
   └─ "vector search"
        └─> decomposer            (subqueries[0] = similitud, subqueries[1] = grafo)
              └─> retriever_router   ★ NUEVO — elige labels a partir de subqueries[0]
                    └─> vector_search   (busca solo en los índices elegidos)
                          └─> prompt_template_with_context
                                └─> graph_qa_with_context → END
```

---

## Cambios

### 1. `Indexes/index.py` — completar labels + retriever multi-label

**1.a — Extender `LABEL_CONFIG` a los 6 labels.** Los valores salen de `NODE_CONFIG` en
`Pipeline_embeddings/generate_embeddings.py` (líneas 44-75) — deben coincidir exactamente, porque
`text_props` es lo que se embebió. Se añade una tercera clave `description`, en lenguaje natural, que
alimentará el prompt del router (única fuente de verdad; no duplicar la descripción en el prompt):

| Label | `id_key` | `text_props` |
|---|---|---|
| `Model` | `model_id` | `model_id`, `pipeline_tag`, `config` |
| `Dataset` | `dataset_id` | `dataset_id`, `citation`, `description` |
| `Space` | `space_id` | `space_id`, `sdk`, `hardware` |
| `Repository` | `id` | `id`, `name`, `card_data` |
| `Author` | `username` | `username`, `fullname` |
| `Tag` | `name` | `name` |

Añadir también `ALL_LABELS = list(LABEL_CONFIG)` — es la lista de fallback y se importa desde
`Graph/nodes.py` y `Chains/retriever_router.py`.

---

**1.b — Cachear los índices.**

*Qué se está cacheando.* No los resultados de las búsquedas — **el objeto de conexión**. Cada
llamada a `get_neo4j_vector_index(label)` construye un `Neo4jVector` desde cero, y eso significa tres
cosas que cuestan tiempo:

1. Abre un driver de Neo4j nuevo (handshake TCP + autenticación).
2. Crea un cliente `AzureOpenAIEmbeddings` nuevo.
3. Le pregunta a Neo4j por el índice `vec_<label>_embedding` para leer su configuración (dimensión,
   función de similitud) y verificar que existe — eso es un round-trip más.

*Por qué hoy no importa y mañana sí.* El código actual esquiva el problema poniendo la llamada
**a nivel de módulo** en `vector_graph_chain.py:46`:

```python
vector_index = index.get_neo4j_vector_index()   # se ejecuta UNA vez, al importar el archivo
```

Python ejecuta esa línea una sola vez, cuando importa el módulo, y todas las preguntas posteriores
reutilizan el mismo objeto. Es un caché — pero un caché de un solo elemento, decidido al arrancar, y
por eso mismo el label queda congelado. Es exactamente lo que hay que quitar (cambio 3).

Al quitarlo, la construcción del índice se muda adentro del flujo por pregunta:
`vector_search` → `get_vector_graph_chain(labels)` → `MultiLabelRetriever` →
`get_neo4j_vector_index(label)` **una vez por label elegido, en cada pregunta**. Sin caché, una
sesión de 20 preguntas con 2 labels cada una abriría 40 conexiones a Neo4j. Con el fallback de los 6
labels, 120.

*La solución.* Un diccionario a nivel de módulo que guarda el objeto ya construido por label:

```python
_INDEX_CACHE: dict[str, Neo4jVector] = {}

def get_neo4j_vector_index(label: str = "Model"):
    if label in _INDEX_CACHE:
        return _INDEX_CACHE[label]          # ya lo construimos antes: reusar
    cfg = LABEL_CONFIG[label]
    idx = Neo4jVector.from_existing_index(...)   # el cuerpo actual, sin cambios
    _INDEX_CACHE[label] = idx
    return idx
```

Comparado con lo de hoy, esto es el mismo truco (construir una vez, reusar) pero **por label y
perezoso**: si en toda la sesión solo se preguntan cosas de `Model` y `Space`, solo se construyen dos
conexiones; los otros cuatro índices nunca se tocan. Y las búsquedas siguen siendo frescas — cada
`similarity_search_with_score` va a Neo4j de verdad, lo único reutilizado es el "teléfono", no la
respuesta.

---

**1.c — Nueva función `multi_label_similarity_search(query, labels, top_k)`.**

Es el corazón del cambio: la función que busca en varios índices y decide qué sale.

```python
def multi_label_similarity_search(query, labels, top_k=5):
    hits = []
    for label in labels:                                    # (1) un índice por label elegido
        idx = get_neo4j_vector_index(label)
        for doc, score in idx.similarity_search_with_score(query, k=top_k):   # (2) top_k a CADA uno
            doc.metadata["score"] = score                   # (3) el score sobrevive al Document
            hits.append((score, doc))
    hits.sort(key=lambda h: h[0], reverse=True)             # (4) ranking global entre labels
    return [doc for _, doc in hits[:top_k]]                 # (5) recorte final
```

Para ver qué cambia, sigamos **la misma pregunta** por los dos caminos:
*"apps de gradio para generar imágenes"*.

**Cómo funciona hoy.** Al arrancar el programa se abrió una sola conexión, la del índice de `Model`
(`vector_graph_chain.py:46`), y ahí se queda. Cuando llega la pregunta:

1. La pregunta se convierte en un vector.
2. Ese vector se compara contra los vectores de los nodos `Model`.
3. Neo4j devuelve los 3 más parecidos, ya ordenados de mejor a peor.
4. Salen 3 `Model`.

Aunque la pregunta hable claramente de Spaces, salen Models: es el único índice donde se buscó.
Neo4j calculó una **nota de parecido** para poder ordenarlos, pero `as_retriever()` devuelve solo los
documentos y esa nota se pierde por el camino.

**Cómo funcionaría con la función nueva.** El router leyó la pregunta y decidió `["Space", "Model"]`.
Entonces:

1. Se busca en `vec_space_embedding` → 5 candidatos, con notas `0.91, 0.88, 0.85, 0.83, 0.81`.
2. Se busca en `vec_model_embedding` → 5 candidatos, con notas `0.87, 0.79, 0.77, 0.74, 0.70`.
3. Ahora hay 10 candidatos que vienen de dos búsquedas distintas. **Cada lista viene ordenada por
   dentro, pero las dos juntas no lo están**: el mejor `Model` (0.87) le gana al tercer `Space`
   (0.85). Si simplemente se pegara una lista después de la otra, quedarían todos los Spaces primero
   y todos los Models después, aunque algún Model mereciera estar más arriba.
4. Por eso se re-ordenan los 10 por su nota, sin importar de qué índice vengan:

```
0.91 Space | 0.88 Space | 0.87 Model | 0.85 Space | 0.83 Space ‖ 0.81 Space | 0.79 Model | ...
└─────────────────── los 5 que se devuelven ─────────────────┘ ‖ └──────── se descartan ────────┘
```

5. Se cortan los 5 mejores → salen **4 Spaces y 1 Model**.

Nadie fijó esa proporción de 4 y 1: **la decidió la nota**. Ese es el motivo de pedirle `top_k`
completo a cada índice en vez de repartir cupos de antemano (tipo "2 Spaces y 3 Models"): no se sabe
cuántos de cada tipo merecen entrar hasta ver las notas. Si la pregunta resulta ser 100% de Spaces,
los 5 puestos pueden ser Spaces.

**Las diferencias, resumidas:**

- **Dónde se busca.** Antes: siempre en `Model`, decidido al arrancar el programa. Ahora: en los
  índices que el router elija, decidido en cada pregunta.
- **La nota de parecido (`score`).** Antes se descartaba, y no hacía falta: con un solo índice, el
  orden que devuelve Neo4j ya es el orden final. Ahora es imprescindible, porque es la única forma
  de comparar un candidato de un índice contra uno de otro. Por eso se usa
  `similarity_search_with_score()` en vez de `as_retriever()`, y se guarda en `metadata["score"]`.
- **Qué significa el número `k`.** Antes: 3 documentos, y ya. Ahora: `top_k` candidatos **a cada
  índice** — esos son los aspirantes — y de ese conjunto salen los `top_k` finales.

*Por qué las notas de distintos índices son comparables.* Porque los 6 índices se construyeron con la
misma función de similitud (coseno) y el mismo modelo de embeddings (`AZURE_EMBEDDING_DEPLOYMENT`,
1536 dims) — un 0.87 significa lo mismo en `vec_space_embedding` que en `vec_model_embedding`. Si
algún índice hubiera usado otro modelo u otra métrica, compararlas no tendría sentido y habría que
normalizar. Conviene dejarlo escrito como comentario en el código: es un supuesto real del que
depende que el merge sea correcto.

*Caso de un solo label.* Si el router devuelve `["Model"]`, la función se comporta prácticamente
igual que el código de hoy: un índice, `top_k` resultados ordenados. El bucle y el `sort` no estorban.

*Por qué N round-trips y no el Cypher `UNWIND` único de `PLAN_busqueda_vectorial_multilabel.md`:*
ese plan asumía buscar *siempre* en los 6 índices, donde un solo round-trip importa. Con el router,
lo típico son 1-2 labels. Además, cada label tiene `text_props` distintas, así que el `RETURN`
que arma `page_content` es distinto por label — unificarlos en un solo Cypher exigiría un `CASE`
por label, más frágil y menos legible que reusar `_build_retrieval_query`, que ya funciona y está
probado contra `vec_model_embedding`. El fallback de 6 labels son 6 lookups vectoriales
(milisegundos), no un problema.

`_build_retrieval_query()` **no se toca** — ya es genérico por label.

---

**1.d — Clase `MultiLabelRetriever(BaseRetriever)`.**

*El problema que resuelve: un desajuste de forma, no de lógica.* La lógica ya está toda en
`multi_label_similarity_search`. Pero esa lógica hay que enchufarla acá:

```python
RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=???, ...)
```

y `RetrievalQA` no acepta una función suelta en `retriever=`. Espera un **objeto** que implemente la
interfaz de retriever de LangChain (que se pueda invocar como parte de una cadena y devuelva
`List[Document]`). Es un contrato de la librería, no una decisión nuestra.

*Por qué no sirve `as_retriever()`, que es lo que se usa hoy.* `as_retriever()` es un método **de un
`Neo4jVector`**, o sea de **un** índice. El objeto que produce lleva adentro esa única conexión y no
tiene forma de saber de otros índices. Estructuralmente no puede abarcar varios labels: no es que le
falte una opción, es que su unidad de trabajo es un índice.

*La solución: el adaptador más pequeño posible.* Una clase que solo guarda "sobre qué labels buscar"
y "cuántos resultados", y cuando `RetrievalQA` la llama, delega en nuestra función:

```python
class MultiLabelRetriever(BaseRetriever):
    labels: List[str]      # se pasan al construirla, distintos en cada pregunta
    top_k: int = 5

    def _get_relevant_documents(self, query, *, run_manager=None):
        return multi_label_similarity_search(query, self.labels, self.top_k)
```

`_get_relevant_documents` es el único método que `BaseRetriever` exige implementar; LangChain se
encarga del resto de la interfaz (`.invoke()`, versión async, callbacks). `BaseRetriever` es un
modelo Pydantic, por eso `labels` y `top_k` se declaran como atributos de clase con tipo, y se
construye con `MultiLabelRetriever(labels=["Space","Model"], top_k=5)`.

*Reparto de responsabilidades:* la **función** sabe *cómo* buscar; la **clase** solo le da la forma
que `RetrievalQA` exige y transporta los labels elegidos por el router. Por eso es tan corta — si
tuviera lógica de negocio adentro, estaría mal ubicada.

*La alternativa que se descartó:* llamar a `multi_label_similarity_search` directamente desde
`Graph/nodes.py::vector_search` y eliminar `RetrievalQA`. Es viable y quitaría una capa, pero
`RetrievalQA` es lo que hoy devuelve `chain_result['source_documents']`, que `nodes.py:69` parsea
para armar `context_refs`. Cambiarlo obligaría a reescribir también ese nodo y su contrato con el
state — más superficie tocada, sin beneficio para el objetivo de este plan.

---

### 2. `Chains/retriever_router.py` — NUEVO

Copiar el patrón exacto de `Chains/router.py` (mismo `AzureChatOpenAI` sin `temperature` —
gpt-5-mini rechaza `temperature=0` con 400; misma construcción `prompt | with_structured_output`):

```python
class RelevantLabels(BaseModel):
    """Choose which node types to search with vector similarity."""
    labels: List[Literal["Model", "Dataset", "Space", "Repository", "Author", "Tag"]] = Field(...)
```

System prompt: catálogo de los 6 labels construido a partir de `LABEL_CONFIG[...]["description"]`,
más la instrucción clave de seguridad — *"if the question is ambiguous or could involve more than one
node type, return all the plausible ones; never return an empty list; when in doubt, return more
labels rather than fewer"*. Ejemplos cortos que cubran los seis (`"spaces built with gradio"` →
`["Space"]`; `"who created the most repositories"` → `["Author", "Repository"]`).

Exporta `retriever_router = prompt | llm.with_structured_output(RelevantLabels)`, invocado con
`{"subquery": ...}`.

### 3. `Chains/vector_graph_chain.py` — parametrizar por labels

- **Borrar** la línea 46 de módulo (`vector_index = index.get_neo4j_vector_index()`) — es lo que hoy
  fija el label en import time.
- `get_vector_graph_chain()` → `get_vector_graph_chain(labels, top_k=5)`; el `retriever=` pasa a ser
  `index.MultiLabelRetriever(labels=labels, top_k=top_k)` en vez de
  `vector_index.as_retriever(search_kwargs={'k':3})`.
- El resto (`RetrievalQA.from_chain_type`, `chain_type="stuff"`, `return_source_documents=True`,
  `llm` de Azure) se mantiene igual.

### 4. `Graph/state.py` y `Graph/labels.py`

- `GraphState`: añadir `target_labels: List[str]`.
- `labels.py`: añadir `RETRIEVER_ROUTER = "retriever_router"`. (El archivo ya tiene constantes
  muertas heredadas — `RETRIEVE`, `GRADE_DOCUMENTS`, `GENERATE`, `CREATE_CONTEXT`, `CREATE_PREFIX`;
  no tocarlas en esta tanda.)

### 5. `Graph/nodes.py` — nodo nuevo + `vector_search` label-aware

**Nodo nuevo `retriever_router(state)`**, entre `decomposer` (líneas 45-52) y `vector_search`:

```python
def retriever_router(state: GraphState):
    queries = state["subqueries"]
    sim_query = queries[0].sub_query if queries else state["question"]
    try:
        labels = retriever_router_chain.invoke({"subquery": sim_query}).labels
    except Exception as e:
        print(f"---RETRIEVER ROUTER FALLO ({e}); usando los 6 labels---")
        labels = []
    labels = [l for l in labels if l in ALL_LABELS] or ALL_LABELS   # fallback seguro
    print(f"---RETRIEVER ROUTER -> {labels}---")
    return {"target_labels": labels, "subqueries": queries, "question": state["question"]}
```

Ese `or ALL_LABELS` es el fallback pedido: cubre lista vacía, labels inventados por el LLM y
excepción de la llamada. El `print` mantiene el estilo de trazas del pipeline (`route_question` en
`graph.py:16` hace lo mismo) y hace visible la decisión en el notebook.

**`vector_search(state)` (líneas 54-73):** leer los labels y pasarlos a la chain:

```python
labels = state.get("target_labels") or ALL_LABELS
vector_graph_chain = get_vector_graph_chain(labels=labels)
```

`context_refs` ya tiene la forma correcta `(label, node_id)` — **no cambia**. Devolver también
`target_labels` para que sobrevivan en el state final.

**Endurecimiento barato, en las mismas funciones que ya se tocan:** `decomposer` no garantiza dos
sub-consultas (usa `bind_tools` + `PydanticToolsParser`, sin `min_items`), y `graph_qa_with_context`
hace `queries[1].sub_query` a ciegas → `IndexError` si el LLM devuelve una sola. Añadir el mismo
guard que en `retriever_router`: `queries[1].sub_query if len(queries) > 1 else state["question"]`.

### 6. `Tools/parse_vector_search.py` — `score` en `Metadata`

`Metadata` es estricto y `nodes.py:69` hace `DocumentModel(**doc.dict())`; si el retriever inyecta
`score` en el metadata sin declararlo, **Pydantic falla**. No es opcional:

```python
class Metadata(BaseModel):
    node_id: str
    label: str
    score: Optional[float] = None
```

De paso, borrar el código muerto y roto del mismo archivo: `create_context()` (usa
`doc.extract_title()`, `doc.metadata.article_id` y una variable `queries` inexistente — daría
`NameError`) y `ResultModel` (sin referencias). Nadie los importa: `Graph/nodes.py` solo trae
`DocumentModel`.

### 7. `Prompts/prompt_template.py` — arreglar el prefix con contexto

`create_few_shot_prompt_with_context` (líneas ~88-89) sigue describiendo ids de OpenAlex:
*"a form of tuple ('a..', 'W..') ... use the second element as a node id, e.g 'W....'"*. Recibe
realmente `[("Model", "models/google/bert-..."), ("Space", "spaces/...")]`. Ese desfase es la causa
del fallo end-to-end visible en `00_run_script.ipynb` celda 3 (el Cypher generado pidió `m.name` y
`m.description`, que no existen en `Model`, y devolvió `None`).

Reescribir el prefix para que diga la verdad y, sobre todo, para que **nombre la propiedad de id de
cada label** — es lo que el LLM necesita para escribir el `WHERE`:

```
A context is provided from a vector search, as a list of tuples (label, node_id).
Match each node_id against the id property of its label:
  Model -> model_id | Dataset -> dataset_id | Space -> space_id
  Repository -> id  | Author -> username    | Tag -> name
Example: ("Model", "models/google/bert-base") ->
  MATCH (m:Model) WHERE m.model_id = "models/google/bert-base"
Use ONLY properties that exist in the schema.
Here are the contexts: {context}
```

Generar esa tabla desde `LABEL_CONFIG` (importándolo de `Indexes.index`) en vez de escribirla a mano,
para no duplicar la fuente de verdad. `create_few_shot_prompt()` (la rama sin contexto) no se toca.

---

## Archivos

| Archivo | Acción |
|---|---|
| `Chains/retriever_router.py` | **nuevo** |
| `Indexes/index.py` | LABEL_CONFIG ×6, `ALL_LABELS`, caché, `multi_label_similarity_search`, `MultiLabelRetriever` |
| `Chains/vector_graph_chain.py` | quitar índice de módulo; `get_vector_graph_chain(labels, top_k)` |
| `Graph/nodes.py` | nodo `retriever_router`; `vector_search` label-aware; guards de `subqueries` |
| `Graph/graph.py` | registrar nodo; `DECOMPOSER → RETRIEVER_ROUTER → VECTOR_SEARCH` |
| `Graph/state.py` | `target_labels` |
| `Graph/labels.py` | `RETRIEVER_ROUTER` |
| `Tools/parse_vector_search.py` | `score` en `Metadata`; borrar código muerto |
| `Prompts/prompt_template.py` | prefix con contexto (label, node_id) |

## Verificación

Prerrequisito: Neo4j local encendido y `.env` cargado (`NEO4J_*`, `AZURE_*`).

**1. Los 6 índices existen y están poblados** (hoy solo hay evidencia de `vec_model_embedding`).
Antes de tocar código, correr en Neo4j Browser:
```cypher
SHOW VECTOR INDEXES YIELD name, state, populationPercent
```
Si algún `vec_<label>_embedding` falta o no está online, hay que correr
`Pipeline_embeddings/load_to_neo4j.py --label <Label>` primero — el router elegiría un índice
inexistente y `from_existing_index` lanzaría error.

**2. El router aislado** (sin tocar el grafo):
```python
from Chains.retriever_router import retriever_router
for q in ["spaces built with gradio",
          "datasets about sentiment analysis",
          "who is the author with most models",
          "tags related to computer vision",
          "find models for text classification"]:
    print(q, "->", retriever_router.invoke({"subquery": q}).labels)
```
Esperado: `["Space"]`, `["Dataset"]`, `["Author"]` (o `["Author","Model"]`), `["Tag"]`, `["Model"]`.

**3. La búsqueda multi-label aislada:**
```python
from Indexes.index import multi_label_similarity_search
for d in multi_label_similarity_search("gradio demo apps", ["Space", "Model"], top_k=5):
    print(d.metadata)   # debe traer label, node_id y score; y aparecer Space, no solo Model
```

**4. End-to-end en `00_run_script.ipynb`**, una pregunta por label, verificando en la traza que el
`print` del router eligió el label correcto y que `result['documents']` trae ese label:
```python
app.invoke({"question": 'find top 5 spaces related to image generation'})
app.invoke({"question": 'find datasets about question answering'})
```
El criterio de éxito real es el paso final: `graph_qa_with_context` debe generar Cypher que use la
propiedad de id correcta (`s.space_id`, `d.dataset_id`) y devolver filas con valores, **no `None`**
como en la corrida actual de la celda 3.

**5. Regresión de la rama no-vectorial** — debe seguir intacta (no toca ninguno de estos nodos):
```python
app.invoke({"question": 'What models were created by a specific author, e.g "GOOGLE"?'})
```

## Fuera de alcance

- `Prompts/prompt_examples.py` ya está migrado al esquema HF Hub (31 ejemplos), pero **ninguno cubre
  `Dataset`**. Añadir ejemplos de Dataset/Space mejoraría el Cypher generado — trabajo aparte.
- `Tools/tools.py` sigue siendo código muerto y no importable (`AURA_*`, imports faltantes).
- `CLAUDE.md`, `ARQUITECTURA_Y_WORKFLOW.md` y `PLAN_busqueda_vectorial_multilabel.md` quedan
  desactualizados respecto a HEAD (describen `AURA_*`, `Article`, `OPENAI_API_KEY`, `article_ids`,
  ya inexistentes). Conviene actualizarlos, pero después de que el router esté verificado.
- El warning de Neo4j `db.index.vector.queryNodes is deprecated... replaced by SEARCH` viene de
  `langchain-neo4j`, no de nuestro código. No bloquea.
