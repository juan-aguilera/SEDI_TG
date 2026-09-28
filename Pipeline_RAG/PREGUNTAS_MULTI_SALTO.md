# 25 preguntas multi-salto para evaluar GraphRAG

Banco de evaluación inspirado en GLM-RAG (Arseven et al., 2026) y en los benchmarks que usa ese trabajo: **HotpotQA**, **2WikiMultihopQA** y **MuSiQue**. Las preguntas están escritas sobre el grafo de Hugging Face Hub (`Model`, `Dataset`, `Space`, `Repository`, `Author`, `Tag`, `Discussion`, `Commits`, `ModifiedFile`).

Correr desde `00_run_script.ipynb`:

```python
from Graph.graph import app
result = app.invoke({"question": "..."})
```

---

## Qué es una pregunta multi-salto

En GLM-RAG, una pregunta **single-hop** se resuelve con un solo documento (o un solo nodo) semánticamente similar a la pregunta. El vector search basta: la evidencia está en el mismo sitio que el enunciado.

Una pregunta **multi-salto** (multi-hop) **no** se puede responder así. Hay que:

1. Extraer entidades semilla de la pregunta.
2. Recorrer **dos o más relaciones** del grafo (o combinar hechos de **varios nodos/documentos**).
3. Usar el resultado de un salto como entrada del siguiente.

El ejemplo canónico del paper es:

> *What is the three letter abbreviation for the country, which maintains border troops, and claims Bernd Baumgart as a citizen?*

Cadena: `Bernd Baumgart` → país que lo reclama como ciudadano (`East Germany`) → abreviatura de tres letras (`GDR`). El nodo respuesta (`GDR`) **no** es vecino directo de la entidad nombrada, y un retriever que solo mira similitud o grado estructural se pierde en vecinos irrelevantes.

MuSiQue construye estas preguntas **componiendo** preguntas single-hop: la respuesta de Q1 se inserta en Q2. HotpotQA y 2Wiki añaden **comparación** (¿A y B comparten propiedad P?) e **intersección** (entidad que cumple dos cadenas independientes).

Criterio operativo para este banco: si un `MATCH` de un solo salto, o un top-k de similitud sobre el texto de la pregunta, ya da la respuesta, **no** es multi-salto. El sistema tiene que **saltar**.

Relaciones del grafo que se recorren aquí:

```
(Model|Dataset|Space) -[:IS_A]-> (Repository) -[:CREATED_BY]-> (Author)
(Repository) -[:HAS_TAG]-> (Tag)
(Space) -[:USES_MODEL]-> (Model)
(Space) -[:USES_DATASET]-> (Dataset)
(Discussion) -[:BELONGS_TO]-> (Repository)
(Discussion) -[:CREATED_BY]-> (Author)
(Discussion) -[:HAS_CONFLICTING_FILE]-> (Repository)
(Commits) -[:AUTHORED_BY]-> (Author)
(Commits) -[:MODIFIES]-> (ModifiedFile)
```

`IS_A` hacia `Repository` cuenta como salto estructural: tags y autores viven en el repositorio, no en el subtipo.

---

## Cómo puntuar una corrida

Para cada pregunta anotar:

| Campo | Qué mirar |
|---|---|
| **Ruta** | `graph query` vs `vector search`. Las de §A–§C deberían ir a Cypher directo. Las de §D mezclan semántica + grafo y pueden ir al decomposer. |
| **Hops cubiertos** | ¿El Cypher recorre **toda** la cadena de la columna *Camino esperado*, o se corta en el primer vecino? |
| **Entidad intermedia** | ¿Resuelve el puente (modelo usado, autor, tag) aunque **no** se pida como respuesta? |
| **Respuesta** | Filas no vacías, labels reales (`Commits` plural, `AFFILLIATED_TO` no existe aquí), sin inventar aristas. |
| **Fallo típico** | Devolver el nodo semilla, un vecino semánticamente parecido, o un conteo global en vez de la cadena. |

Una respuesta “plausible pero de un solo salto” cuenta como **fallo de razonamiento**, no como acierto parcial.

---

## A. Puente / composicional (2 hops)

El enunciado nombra una entidad semilla. La respuesta está a **dos relaciones** de distancia. El nodo intermedio **no** es la respuesta.

### 1. Autor de los modelos que usa un Space

**Pregunta:** Who created the models used by the Space `huggingface/diffusers-demo`?

**Tipo:** bridge (HotpotQA / MuSiQue 2-hop)

**Camino esperado:** `Space -[:USES_MODEL]-> Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** “quién creó el Space” es un salto distinto y más corto. Aquí hay que pasar por los modelos usados y recién entonces llegar al autor. Vector search sobre “huggingface/diffusers-demo” no nombra a esos autores.

**Debe devolver:** `username` (y, si puede, `fullname`) de cada autor de esos modelos.

---

### 2. Pipeline tag de modelos usados por un Space

**Pregunta:** What are the pipeline tags of the models used by `huggingface/diffusers-demo`?

**Tipo:** bridge 2-hop

**Camino esperado:** `Space -[:USES_MODEL]-> Model` → `pipeline_tag`

**Por qué es multi-salto:** el Space no tiene `pipeline_tag`. Hay que saltar a `Model`. Un match directo sobre el Space devolvería `sdk` / `hardware` y parecería una respuesta, pero es el salto equivocado.

**Debe devolver:** lista de `pipeline_tag` de los modelos usados.

---

### 3. SDK de los Spaces que usan un dataset

**Pregunta:** What SDKs do the Spaces that use the dataset `squad` run on?

**Tipo:** bridge 2-hop (dirección inversa)

**Camino esperado:** `Dataset <-[:USES_DATASET]- Space` → `sdk`

**Por qué es multi-salto:** `squad` no tiene SDK. La semilla es el dataset; la propiedad pedida vive en otro label, unido por `USES_DATASET`.

**Debe devolver:** valores distintos de `s.sdk` (p. ej. `gradio`, `streamlit`).

---

### 4. Tags de un modelo vía su repositorio

**Pregunta:** Which tags are attached to the repository of the model `bert-base-uncased`, and which Spaces use that same model?

**Tipo:** bridge 2-hop con dos ramas desde la misma semilla

**Camino esperado:**
- `Model -[:IS_A]-> Repository -[:HAS_TAG]-> Tag`
- `Space -[:USES_MODEL]-> Model`

**Por qué es multi-salto:** hay que **combinar** dos cadenas que no viven en el mismo vecindario. Devolver solo tags o solo Spaces es un acierto a medias.

**Debe devolver:** `tags` **y** `space_id` para `bert-base-uncased`.

---

### 5. Datasets usados por Spaces del mismo autor que un modelo

**Pregunta:** Which datasets are used by Spaces created by the same author who created `bert-base-uncased`?

**Tipo:** composicional 2–3 hops (la respuesta de hop 1 alimenta hop 2)

**Camino esperado:** `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author <-[:CREATED_BY]- Repository <-[:IS_A]- Space -[:USES_DATASET]-> Dataset`

**Por qué es multi-salto:** el autor no está nombrado. Hay que **descubrirlo** desde el modelo, usarlo para filtrar Spaces, y recién entonces listar datasets. Es el patrón MuSiQue: Q1 = “quién creó bert…”, Q2 = “qué datasets usan los Spaces de ese autor”.

**Debe devolver:** `dataset_id` distintos (puede ser vacío si ese autor no tiene Spaces con `USES_DATASET`; el Cypher correcto sigue siendo el criterio).

---

## B. Comparación (2Wiki / HotpotQA comparison)

Hay que resolver **la misma propiedad en dos cadenas** y comparar. Un solo lookup no basta.

### 6. ¿Mismo autor?

**Pregunta:** Are `bert-base-uncased` and `distilbert-base-uncased` created by the same author?

**Tipo:** comparison (sí/no)

**Camino esperado:** dos caminos `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author`, luego igualdad de `username`.

**Por qué es multi-salto:** hay que materializar **dos** autores y compararlos. Devolver el autor de uno solo es fallo.

**Debe devolver:** `yes` / `no` (idealmente con los dos `username`).

---

### 7. ¿Comparten algún tag?

**Pregunta:** Do the dataset `squad` and the model `bert-base-uncased` share any tags?

**Tipo:** comparison + intersección de conjuntos

**Camino esperado:** `Dataset -[:IS_A]-> Repository -[:HAS_TAG]-> Tag` **y** `Model -[:IS_A]-> Repository -[:HAS_TAG]-> Tag`, intersección.

**Por qué es multi-salto:** tags de tipos distintos, cada uno vía `IS_A`. Listar los tags de uno de los dos no responde.

**Debe devolver:** `yes`/`no` y, si hay, los `Tag.name` comunes.

---

### 8. ¿Quién tiene más discusiones?

**Pregunta:** Which has more discussions belonging to its repository, the model `bert-base-uncased` or the dataset `squad`?

**Tipo:** comparison de agregados

**Camino esperado:** para cada uno, `(:Model|:Dataset) -[:IS_A]-> Repository <-[:BELONGS_TO]- Discussion`, `count`, comparar.

**Por qué es multi-salto:** dos cadenas de conteo + comparación. Un `count` global de `Discussion` es el fallo clásico.

**Debe devolver:** el id ganador y los dos conteos.

---

### 9. ¿Mismo SDK en Spaces que usan cada uno?

**Pregunta:** Do any Spaces that use `bert-base-uncased` share an SDK with any Spaces that use the dataset `squad`?

**Tipo:** comparison de propiedades en vecinos de dos semillas

**Camino esperado:** `Space -[:USES_MODEL]-> Model` vs `Space -[:USES_DATASET]-> Dataset`, comparar conjuntos de `sdk`.

**Por qué es multi-salto:** hay que juntar dos vecindarios `USES_*` y cruzar una propiedad del Space, no del modelo ni del dataset.

**Debe devolver:** `yes`/`no` y los SDK en la intersección.

---

### 10. ¿El creador del modelo también publicó datasets?

**Pregunta:** Did the author of `bert-base-uncased` also create any datasets? If so, list them.

**Tipo:** comparison / existence across types

**Camino esperado:** `Model → Author`, luego `Author <-[:CREATED_BY]- Repository <-[:IS_A]- Dataset`.

**Por qué es multi-salto:** la pregunta es sobre **otra especialización** (`Dataset`) del mismo autor. Listar modelos de Google no cuenta.

**Debe devolver:** `yes`/`no` y `dataset_id` (o lista vacía explícita).

---

## C. Intersección y 3–4 hops (lo más difícil)

El paper muestra que Recall cae al subir el número de documentos de apoyo y la distancia entidad-nivel. Estas preguntas exigen **tres o más aristas**, a menudo con un filtro en cada hop.

### 11. Spaces Gradio que usan modelos de un autor descubierto

**Pregunta:** Which Gradio Spaces use a model created by the same author as `bert-base-uncased`?

**Tipo:** intersección + puente (3 hops)

**Camino esperado:** `bert-base-uncased → Author → Model → Space` con `s.sdk = 'gradio'`.

**Por qué es multi-salto:** tres restricciones independientes (autor puente, `USES_MODEL`, `sdk`). Nombrar `google` en el Cypher porque “se sabe” es hacer trampa: el autor debe salir del grafo.

**Debe devolver:** `space_id` (limitar a 20 si hay muchos).

---

### 12. Tags de modelos usados por Spaces con un tag dado

**Pregunta:** What tags appear on models that are used by Spaces tagged `text-to-image`?

**Tipo:** composicional 3-hop

**Camino esperado:** `Tag(text-to-image) <-[:HAS_TAG]- Repository <-[:IS_A]- Space -[:USES_MODEL]-> Model -[:IS_A]-> Repository -[:HAS_TAG]-> Tag`

**Por qué es multi-salto:** el tag de partida está en el **Space**; el tag pedido está en el **Model**. Devolver tags de los Spaces es el error de un solo salto.

**Debe devolver:** `Tag.name` distintos de esos modelos, no del Space.

---

### 13. Autores que cumplen dos cadenas distintas

**Pregunta:** Which authors have created both a model tagged `pytorch` and a dataset that is used by at least one Space?

**Tipo:** intersection (2Wiki)

**Camino esperado:**
- cadena A: `Author ← Repository ← Model` y `HAS_TAG pytorch`
- cadena B: `Author ← Repository ← Dataset ← USES_DATASET Space`
- autores en la **intersección**.

**Por qué es multi-salto:** dos evidencias de apoyo, como en 2Wiki. Cumplir una sola cadena no basta.

**Debe devolver:** `username` que satisfagan **ambas**.

---

### 14. Archivos modificados por el creador de un modelo

**Pregunta:** Which files has the creator of `bert-base-uncased` modified in their commits?

**Tipo:** composicional 4-hop

**Camino esperado:** `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author <-[:AUTHORED_BY]- Commits -[:MODIFIES]-> ModifiedFile`

**Por qué es multi-salto:** `ModifiedFile` no toca al modelo. Hay que pasar autor → commits → archivos. Label correcto: `Commits` (plural). `(:Commit)` es un label vacío.

**Debe devolver:** identificadores distintos de `ModifiedFile` (limitar a 20).

---

### 15. Quién abre discusiones en repos de un autor (no el autor del repo)

**Pregunta:** Who opened discussions on repositories created by `google`, and which of those discussion authors are *not* `google`?

**Tipo:** 3-hop + filtro de desigualdad

**Camino esperado:** `Author(google) <-[:CREATED_BY]- Repository <-[:BELONGS_TO]- Discussion -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** hay dos roles de `Author` en la misma cadena (creador del repo vs. creador de la discusión). Colapsarlos en un solo `Author` es el fallo típico de Cypher.

**Debe devolver:** `username` de quienes abrieron discusiones, excluyendo `google`.

---

### 16. Archivos en conflicto en discusiones de modelos de un autor

**Pregunta:** Which conflicting filenames appear in discussions of models created by `google`?

**Tipo:** 3–4 hops con propiedad de arista

**Camino esperado:** `Author ← CREATED_BY Repository ← IS_A Model` y, sobre el mismo repo, `Discussion -[c:HAS_CONFLICTING_FILE]-> Repository` → `c.filename`

**Por qué es multi-salto:** `filename` vive en la **relación**, no en el modelo. Hay que llegar al repo del modelo y a la discusión con conflicto.

**Debe devolver:** `filename` / `repo_file_id` distintos.

---

### 17. Modelo más usado por Spaces, luego su autor y tags

**Pregunta:** Among models used by at least one Space, which model is used by the most Spaces, who created it, and what tags does it have?

**Tipo:** composicional 3-hop con agregación intermedia (MuSiQue 3-hop)

**Camino esperado:** `Space -[:USES_MODEL]-> Model` → `count` → top-1 → `CREATED_BY` y `HAS_TAG` vía `Repository`.

**Por qué es multi-salto:** la semilla no está nombrada. El sistema debe **elegir** el puente (el modelo top) y recién entonces saltar a autor y tags. Devolver el ranking de modelos sin autor/tags es quedarse a medio camino.

**Debe devolver:** `model_id`, `count`, `username`, lista de tags.

---

### 18. Spaces que usan modelo y dataset: autores de ambos

**Pregunta:** For Spaces that use both a model and a dataset, return the Space, the author of the model, and the author of the dataset.

**Tipo:** 3 hops, dos puentes en paralelo

**Camino esperado:** `Space -[:USES_MODEL]-> Model → Author_m` **y** `Space -[:USES_DATASET]-> Dataset → Author_d`

**Por qué es multi-salto:** un Space “que usa ambos” es un filtro; la pregunta pide **dos autores distintos** por fila. Devolver solo el creador del Space es el salto corto equivocado.

**Debe devolver:** `space_id`, `model_author`, `dataset_author` (limitar a 10).

---

### 19. Pipeline tags de modelos cuyos creadores también commitean archivos

**Pregunta:** What pipeline tags appear on models whose creators have also authored commits that modify files?

**Tipo:** intersección 4-hop

**Camino esperado:** `ModifiedFile <-[:MODIFIES]- Commits -[:AUTHORED_BY]-> Author <-[:CREATED_BY]- Repository <-[:IS_A]- Model` → `pipeline_tag`

**Por qué es multi-salto:** cruza el subgrafo de historial (`Commits`/`ModifiedFile`) con el de publicación (`Model`). No hay arista directa entre archivo y pipeline tag.

**Debe devolver:** `pipeline_tag` distintos.

---

### 20. Autores que discuten un modelo que no crearon

**Pregunta:** Are there authors who opened a discussion on a model they did not create? List up to 10 such (discussion_author, model_id, model_author) triples.

**Tipo:** comparación de dos caminos que llegan a `Author`

**Camino esperado:** `Discussion -[:CREATED_BY]-> Author_d` y `Discussion -[:BELONGS_TO]-> Repository <-[:IS_A]- Model -[:CREATED_BY]-> Author_m` con `Author_d <> Author_m`.

**Por qué es multi-salto:** hay que **alinear** dos cadenas sobre la misma discusión y exigir desigualdad. Un listado de autores de discusiones, sin cruzar con el creador del modelo, no responde.

**Debe devolver:** hasta 10 tripletas.

---

### 21. Tags que co-ocurren con `pytorch` solo en modelos de un autor puente

**Pregunta:** Which tags co-occur with `pytorch` on models created by the author of `bert-base-uncased`?

**Tipo:** puente + intersección de tags (3 hops)

**Camino esperado:** `bert-base-uncased → Author → Model` con tag `pytorch` **y** otros `HAS_TAG` del mismo repo, excluyendo `pytorch`.

**Por qué es multi-salto:** “tags que co-ocurren con pytorch” en todo el grafo es más fácil y **no** es esta pregunta. El filtro de autor se descubre desde otro modelo.

**Debe devolver:** `Tag.name` distintos de `pytorch`.

---

### 22. Descripción de datasets usados por Spaces que usan un modelo dado

**Pregunta:** What are the dataset ids and descriptions of datasets used by Spaces that also use `bert-base-uncased`?

**Tipo:** bridge 3-hop cruzando `USES_MODEL` y `USES_DATASET`

**Camino esperado:** `Model <-[:USES_MODEL]- Space -[:USES_DATASET]-> Dataset` → `dataset_id`, `description`

**Por qué es multi-salto:** el dataset no está ligado al modelo. El Space es el **puente**. Devolver Spaces que usan BERT, o datasets similares a SQuAD, es single-hop semántico.

**Debe devolver:** pares `dataset_id` / `description` (limitar a 10).

---

## D. Semilla semántica + hops de grafo (rama vector search)

En GLM-RAG, el retriever parte de entidades semilla y recorre el KG; vanilla RAG falla porque la similitud con el texto de la pregunta no alcanza el documento de apoyo lejano. Estas preguntas **no nombran un id concreto**: primero hay que anclar nodos por significado y **después** caminar el grafo. El router puede mandarlas a `vector search` → decomposer.

### 23. Modelos de un tema, luego autores de los Spaces que los usan

**Pregunta:** Find models about image generation and return the authors of the Spaces that use those models.

**Tipo:** semantic seed + 2 graph hops

**Camino esperado:** vector sobre `Model` (p. ej. text-to-image / diffusion) → `Space -[:USES_MODEL]-> Model` → `Space -[:IS_A]-> Repository -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** “modelos de image generation” es el primer salto semántico. La respuesta pedida es el **autor del Space**, no el del modelo ni el `model_id`. Quedarse en la lista de modelos es single-hop.

**Debe devolver:** `model_id` + `space_id` + `author.username` de esos Spaces.

---

### 24. Datasets de un tema, Spaces que los usan, SDK y modelos de esos Spaces

**Pregunta:** Find datasets about question answering, then list the Spaces that use them, the SDK of those Spaces, and the models those Spaces use.

**Tipo:** semantic seed + 3 graph hops (MuSiQue 3-hop)

**Camino esperado:** vector/`HAS_TAG` sobre Dataset (QA / SQuAD-like) → `USES_DATASET` → `sdk` → `USES_MODEL`

**Por qué es multi-salto:** tres hechos de apoyo en labels distintos. Un decomposer débil genera solo “find QA datasets” y nunca camina a Space/Model.

**Debe devolver:** `dataset_id`, `space_id`, `sdk`, `model_id` (limitar a 10 filas).

---

### 25. Autores parecidos a una org, modelos `text-generation`, Spaces Gradio, tags de esos Spaces

**Pregunta:** Find authors similar to Hugging Face, keep only their models with pipeline tag `text-generation`, then return Gradio Spaces that use those models and the tags of those Spaces.

**Tipo:** semantic seed + intersección + 3 hops

**Camino esperado:** vector sobre `Author` → `CREATED_BY` modelos con `pipeline_tag = 'text-generation'` → `Space` con `sdk = 'gradio'` → `HAS_TAG` del Space.

**Por qué es multi-salto:** cuatro filtros encadenados (autor semántico, pipeline del modelo, SDK del Space, tags del Space). Es el caso en el que GLM-RAG argumenta que el grafo gana a vanilla RAG: ningún chunk único contiene autor + pipeline + Space + tags.

**Debe devolver:** `author`, `model_id`, `space_id`, lista de tags del Space.

---

## Mapa rápido

| # | Hops | Patrón | Semilla | Respuesta |
|---|:---:|---|---|---|
| 1 | 2–3 | bridge | Space id | Author de modelos |
| 2 | 2 | bridge | Space id | `pipeline_tag` |
| 3 | 2 | bridge | Dataset id | `sdk` |
| 4 | 2+2 | bridge dual | Model id | tags + Spaces |
| 5 | 3 | compositional | Model id | Dataset ids |
| 6 | 2+2 | comparison | dos Model id | yes/no |
| 7 | 2+2 | comparison | Model + Dataset | tags comunes |
| 8 | 2+2 | comparison count | Model + Dataset | id + counts |
| 9 | 2+2 | comparison | Model + Dataset | SDK comunes |
| 10 | 3 | existence | Model id | Datasets del autor |
| 11 | 3 | intersection | Model id + sdk | Space ids |
| 12 | 3 | compositional | Tag name | tags de Model |
| 13 | 3+3 | intersection | Tag + USES_DATASET | Authors |
| 14 | 4 | compositional | Model id | ModifiedFile |
| 15 | 3 | roles de Author | Author username | Authors ≠ google |
| 16 | 3–4 | rel property | Author username | `filename` |
| 17 | 3 | agg + bridge | (ninguna id) | model + author + tags |
| 18 | 3 | dual bridge | filtro Space | dos authors |
| 19 | 4 | intersection | (ninguna id) | pipeline tags |
| 20 | 3 | comparison paths | (ninguna id) | tripletas |
| 21 | 3 | co-occurrence | Model id | tags ≠ pytorch |
| 22 | 3 | bridge cruzado | Model id | dataset + description |
| 23 | sem+2 | vector+graph | tema | authors de Spaces |
| 24 | sem+3 | vector+graph | tema | Space + sdk + model |
| 25 | sem+3 | vector+graph | autor~HF | Space Gradio + tags |

---

## Notas de implementación al evaluar

- **`IS_A` no es opcional** para tags y autores: `HAS_TAG` y `CREATED_BY` salen de `Repository`, no de `Model`/`Dataset`/`Space`.
- **`USES_MODEL` / `USES_DATASET` salen del Space**, no del modelo/dataset.
- **`Commits`** es el label con datos; **`Commit`** tiene 0 nodos.
- **`HAS_CONFLICTING_FILE`** lleva `filename` y `repo_file_id` en la arista.
- Las preguntas 17, 19 y 20 no nombran ids: si el modelo se inventa un `model_id` famoso en vez de agregar sobre el grafo, es fallo.
- Si 23–25 caen en `graph query` sin vector search, no es automáticamente un error: un Cypher con `CONTAINS` / tags puede ser válido. El error es **no completar los hops posteriores**.
- Este banco **no** incluye preguntas single-hop del estilo “How many models are there?” o “What is the pipeline tag of bert-base-uncased?”. Esas ya están en `TEST_WORKFLOW_QUESTIONS.md`.
