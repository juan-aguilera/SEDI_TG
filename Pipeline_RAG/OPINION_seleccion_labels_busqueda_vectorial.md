# ¿Vale la pena un módulo LLM que decida qué labels buscar? — Opinión y sugerencias

## La pregunta

Antes de ejecutar la búsqueda vectorial multi-label (Model, Dataset, Space, Repository, Author, Tag),
¿debería haber un paso adicional que use un LLM para leer la pregunta del usuario y decidir de antemano
"esta pregunta es sobre Models y Datasets, busca solo ahí" — en vez de buscar siempre en los 6 índices
y dejar que el score decida?

## TL;DR de mi recomendación

**No lo agregaría todavía.** El diseño ya acordado (Top-K global sobre los 6 índices, dejando que el
score de similitud decida qué sale arriba) ya resuelve el problema de "qué label es relevante" de forma
más barata, más robusta y sin un punto de fallo adicional. Un clasificador LLM de labels tiene sentido
como optimización *futura*, solo si en la práctica se observa un problema concreto que el ranking por
score no resuelve — no como parte por defecto del diseño.

## Comparando las opciones

### A. Clasificador LLM de labels (lo que propones)

Un nuevo nodo/chain (análogo a `Chains/router.py`) que recibe la pregunta y devuelve algo como
`labels_relevantes = ["Model", "Dataset"]`, y esa lista se usa para decidir sobre qué índices de Neo4j
correr la búsqueda vectorial.

**A favor:**
- En preguntas muy claras ("¿quién es el autor con más modelos?") podría evitar tocar los índices de
  Space/Tag/Dataset/Repository, que no aportan nada ahí.
- Es un patrón que el proyecto ya usa (`Chains/router.py` hace exactamente esto, pero para decidir entre
  "vector search" / "graph query" / "graph db query"), así que no sería una idea ajena a la arquitectura.

**En contra:**
- Agrega una llamada a LLM (latencia de cientos de ms a un par de segundos, más costo de tokens) **antes**
  de cada búsqueda vectorial, para reemplazar algo que consultar los 6 índices ya hace casi gratis: una
  sola consulta Cypher con `UNWIND` + `db.index.vector.queryNodes` sobre 6 índices tarda milisegundos.
  Es decir, se paga el costo más caro (LLM) para ahorrarse el costo más barato (6 lookups vectoriales en
  la misma base de datos).
- Es un punto de fallo nuevo con un modo de error silencioso y peligroso: si el clasificador se equivoca y
  excluye un label que sí era relevante, esos nodos **nunca entran a la búsqueda** — no hay manera de que
  el score los "rescate" después, porque ni siquiera se consultaron. Con Top-K global, en cambio, un label
  "irrelevante" simplemente sale con score bajo y no compite por los primeros puestos — nunca se pierde
  información de forma irreversible.
- El conjunto de labels es pequeño y fijo (6). Un clasificador LLM brilla cuando hay muchas categorías,
  la relación pregunta→categoría requiere razonamiento genuino, o el conjunto cambia dinámicamente. Ninguno
  de esos casos aplica aquí: son 6 tipos de nodo conocidos, y la relevancia semántica de una pregunta hacia
  cada uno de ellos es exactamente lo que un embedding ya captura de forma continua (no binaria como
  "sí/no pertenece a este label").

### B. Top-K global sobre todos los índices (lo ya planeado en `PLAN_busqueda_vectorial_multilabel.md`)

Buscar siempre en los 6 índices y devolver los K nodos de mejor score en conjunto, sin importar el label.

**A favor:**
- Cero llamadas a LLM adicionales — el "ruteo por label" ocurre gratis como efecto colateral del ranking
  por similitud coseno.
- Nunca excluye de forma irreversible un tipo de nodo: si una pregunta resulta ser más relevante para
  `Dataset` que para `Model`, el score simplemente lo refleja.
- Es la opción más simple de implementar, depurar y explicar en una tesis (menos piezas, menos
  configuración, menos lugares donde algo puede salir mal).

**En contra:**
- Si el corpus de un label es mucho más grande o sus textos son más "genéricos" que los de otro, podría
  dominar el Top-K con nodos poco interesantes (ej. muchos `Tag` cortos con embeddings parecidos entre sí).
  Esto es un riesgo real pero se mitiga con ajustes numéricos simples (ver más abajo), no con un LLM.

### C. Alternativas intermedias, más baratas que un LLM, si el Top-K global resulta insuficiente

Si después de probar el Top-K global se nota que ciertos labels ensucian los resultados o que otros nunca
aparecen aunque deberían, antes de llegar a un LLM yo probaría, en este orden:

1. **Filtro por palabra clave (gratis, sin llamadas externas):** si la pregunta menciona literalmente
   "modelo(s)", "dataset(s)", "space(s)", "repositorio(s)", "autor(es)", "tag(s)" (o sus equivalentes en
   inglés), usar eso como pista fuerte para priorizar esos labels — sin excluir los demás, solo como
   señal adicional de ranking (ej. sumar un pequeño bonus al score de ese label). Es prácticamente gratis
   y funciona bien en preguntas donde el usuario ya nombra el tipo de nodo que busca.
2. **Límite de resultados por label (post-filtro numérico):** en vez de Top-K puramente global, aplicar un
   tope como "máximo 3 resultados por label dentro del Top-K" — así ningún label puede monopolizar todos
   los cupos, pero tampoco hay que decidir de antemano cuáles labels son relevantes. Es una línea de código,
   no un módulo nuevo.
3. **Similitud contra una "descripción del label" (embeddings, no LLM):** calcular una sola vez un embedding
   de una frase corta que describa cada label (ej. "Model: modelos de machine learning con su tarea y
   configuración"), y comparar la pregunta contra esas 6 descripciones usando el mismo embedding ya
   calculado para la búsqueda vectorial (no hay llamada extra a un LLM generativo, solo comparaciones de
   coseno adicionales, casi gratis). Esto da una señal de "qué tan relevante es cada label para esta
   pregunta" sin excluir nada de forma dura y sin latencia de generación de texto.

Solo si ninguna de estas resuelve el problema observado, consideraría un clasificador LLM — y en ese caso,
lo más consistente con el proyecto sería extender el patrón que ya existe en `Chains/router.py`
(un `AzureChatOpenAI` con `structured_output`/`bind_tools` y un Pydantic model, ej.
`RelevantLabels(labels: List[Literal["Model","Dataset",...]])`), en lugar de inventar un mecanismo
distinto — así se mantiene consistencia arquitectónica con el resto del pipeline.

## Recomendación concreta

1. Implementar primero el Top-K global tal como está en `PLAN_busqueda_vectorial_multilabel.md` — sin
   clasificador de labels.
2. Probar con preguntas reales y variadas, revisando qué labels salen en el Top-K y si hay ruido evidente
   (ej. muchos `Tag` sin valor informativo, o un label que nunca aparece aunque debería).
3. Si aparece un problema concreto, resolverlo primero con las opciones de bajo costo de la sección C
   (palabra clave, tope por label, similitud contra descripción de label) — todas evolucionan el mismo
   código sin agregar una dependencia nueva a un LLM.
4. Reservar el clasificador LLM (extendiendo `Chains/router.py`) como último recurso, solo si el problema
   persiste y realmente requiere razonamiento sobre la pregunta que un embedding no puede capturar.

Esto sigue el mismo espíritu de "no diseñar para necesidades hipotéticas": agregar un LLM de ruteo por
label antes de tener evidencia de que hace falta sería resolver un problema que quizás nunca ocurra, a
cambio de latencia, costo y un nuevo punto de fallo silencioso.
