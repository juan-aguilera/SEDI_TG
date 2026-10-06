# 25 preguntas multi-salto para evaluar GraphRAG

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

**Pregunta:** Who created the models used by the Space `spaces/1PGAlt/audioEditing`?

**Tipo:** bridge (HotpotQA / MuSiQue 2-hop)

**Camino esperado:** `Space -[:USES_MODEL]-> Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** “quién creó el Space” es un salto distinto y más corto. Aquí hay que pasar por los modelos usados y recién entonces llegar al autor. Vector search sobre “huggingface/diffusers-demo” no nombra a esos autores.

**Debe devolver:** `username` (y, si puede, `fullname`) de cada autor de esos modelos.

**Respuesta**
The models used by the Space spaces/0ffchain/openchat-openchat2 were created by the user openchat.

The retrieved graph result returned a single author username: openchat. That means the Space references at least one model whose recorded creator (author username) is openchat.

What’s missing from this result:

The query did not return model identifiers, names, or how many models the Space uses, so I can’t list the specific models or confirm that every model the Space uses is by openchat.
If you want model-level details (IDs, descriptions, or whether multiple authors are involved), please provide the model rows or run a query that returns each model node together with its author.

---

### 2. Pipeline tag de modelos usados por un Space

**Pregunta:** What are the pipeline tags of the models used by `spaces/0jung/clothes_segmenation`?

**Tipo:** bridge 2-hop

**Camino esperado:** `Space -[:USES_MODEL]-> Model` → `pipeline_tag`

**Por qué es multi-salto:** el Space no tiene `pipeline_tag`. Hay que saltar a `Model`. Un match directo sobre el Space devolvería `sdk` / `hardware` y parecería una respuesta, pero es el salto equivocado.

**Debe devolver:** lista de `pipeline_tag` de los modelos usados.

**Respuesta**

The models used by the Space spaces/0jung/clothes_segmenation have the pipeline tag image-segmentation.

Details

The query returned a single pipeline tag value: "image-segmentation", which indicates the Space references model(s) intended for image segmentation tasks (segmentation pipelines).

Limits

The result contains only the pipeline tag value; it did not return model IDs, counts, or any other tags.
If the Space uses multiple models with different pipeline tags, those additional tags were not returned by this query — provide model-level rows if you want a per-model breakdown.

---

### 3. SDK de los Spaces que usan un dataset

**Pregunta:** What SDKs do the Spaces that use the dataset `squad` run on?

**Tipo:** bridge 2-hop (dirección inversa)

**Camino esperado:** `Dataset <-[:USES_DATASET]- Space` → `sdk`

**Por qué es multi-salto:** `squad` no tiene SDK. La semilla es el dataset; la propiedad pedida vive en otro label, unido por `USES_DATASET`.

**Debe devolver:** valores distintos de `s.sdk` (p. ej. `gradio`, `streamlit`).

**Respuesta**
The Spaces that use the dataset datasets/mstz/iris (in the returned result) run on the Gradio SDK — the query returned a single sdk value: "gradio".

Details

This means the retrieved rows reported the SDK field for those Space(s) as "gradio", i.e., the Space implementations referenced that SDK.

Limits

The query returned only the single SDK value "gradio"; it did not return Space identifiers or how many Spaces were found.
There could be additional Spaces using the dataset that run on other SDKs but were not returned by this query.
If you want a per-Space breakdown (Space name → SDK), run a query that returns each Space id/name together with its sdk field and I can summarize those results.

---

### 4. Tags de un modelo vía su repositorio

**Pregunta:** Which tags are attached to the repository of the model `models/gywy/Mistral-7B-v0.1-chinese`, and which Spaces use that same model?

**Tipo:** bridge 2-hop con dos ramas desde la misma semilla

**Camino esperado:**
- `Model -[:IS_A]-> Repository -[:HAS_TAG]-> Tag`
- `Space -[:USES_MODEL]-> Model`

**Por qué es multi-salto:** hay que **combinar** dos cadenas que no viven en el mismo vecindario. Devolver solo tags o solo Spaces es un acierto a medias.

**Debe devolver:** `tags` **y** `space_id` para `bert-base-uncased`.

**Respuesta**

The repository for models/gywy/Mistral-7B-v0.1-chinese has these tags: autotrain_compatible, endpoints_compatible, has_space, mistral, pytorch, region:us, text-generation, text-generation-inference, and transformers.
The query returned one Space that uses this model: spaces/0ldDriver/gywy-Mistral-7B-v0.1-chinese.

Tags on the repository

autotrain_compatible — indicates compatibility with AutoTrain workflows.
endpoints_compatible — indicates the repo is set up to be served via inference endpoints.
has_space — the repository is linked to at least one Space.
mistral — labels the model family or origin (the literal tag value is "mistral").
pytorch — indicates PyTorch-compatible files or weights.
region:us — a regional tag (literally returned as "region:us").
text-generation — the model is tagged for text generation tasks.
text-generation-inference — indicates readiness/compatibility for text-generation inference workflows.
transformers — indicates usage with the Hugging Face Transformers library.
Spaces that use this model

spaces/0ldDriver/gywy-Mistral-7B-v0.1-chinese
Limits

The query returned only the listed tags and a single Space ID; there may be additional tags or other Spaces using this model that were not returned by this query.
All values above are taken exactly from the retrieved result; I did not add or infer other repository or Space details.

---

### 5. Datasets usados por Spaces del mismo autor que un modelo

**Pregunta:** Which datasets are used by Spaces created by the same author who created `models/bdsaglam/llama-3-8b-jerx-debug-peft-tqwogc49`?

**Tipo:** composicional 2–3 hops (la respuesta de hop 1 alimenta hop 2)

**Camino esperado:** `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author <-[:CREATED_BY]- Repository <-[:IS_A]- Space -[:USES_DATASET]-> Dataset`

**Por qué es multi-salto:** el autor no está nombrado. Hay que **descubrirlo** desde el modelo, usarlo para filtrar Spaces, y recién entonces listar datasets. Es el patrón MuSiQue: Q1 = “quién creó bert…”, Q2 = “qué datasets usan los Spaces de ese autor”.

**Debe devolver:** `dataset_id` distintos (puede ser vacío si ese autor no tiene Spaces con `USES_DATASET`; el Cypher correcto sigue siendo el criterio).

**Respuesta**:

The Spaces created by the author of model models/bdsaglam/llama-3-8b-jerx-debug-peft-tqwogc49 (in the returned result) use the dataset datasets/bdsaglam/musique.

Details

The query returned a single dataset identifier: datasets/bdsaglam/musique. That means at least one Space authored by the same person who created the model references this dataset.

What’s missing / next steps

The result did not return Space identifiers, the author’s username, or how many Spaces use the dataset, so I can’t list the individual Spaces or confirm this is the only dataset they use.
If you want a per‑Space breakdown, run a query that returns each Space id together with the dataset ids it uses (for example: Space id → dataset id). Return those rows and I will group and summarize them.
Limits

A single returned dataset id indicates what was returned by this query, not a full census of all datasets the author’s Spaces might use.
If a field is null or absent in a future result, that means it was not returned — not that the real entity lacks that value.


---

## B. Comparación (2Wiki / HotpotQA comparison)

Hay que resolver **la misma propiedad en dos cadenas** y comparar. Un solo lookup no basta.

### 6. ¿Mismo autor?

**Pregunta:** Tell me 3 different authors that created more than 2 models and their models id?

**Tipo:** comparison (sí/no)

**Camino esperado:** dos caminos `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author`, luego igualdad de `username`.

**Por qué es multi-salto:** hay que materializar **dos** autores y compararlos. Devolver el autor de uno solo es fallo.

**Debe devolver:** 3 autores y sus modelos.

**Respuesta**

The three authors are 0-hero, 000jd, and 009qjqiwi — each has more than two models in the returned result. Below I list the model IDs returned for each author.

Authors and their model IDs

0-hero: models/0-hero/flan-alpaca-ul2, models/0-hero/flan-OIG-base, models/0-hero/flan-OIG-small, models/0-hero/flan-OIG-ul2, models/0-hero/flan-OIG-xl, models/0-hero/indic-vocab-only, models/0-hero/led-large-legal-summary, models/0-hero/Matter-0.1-7B, models/0-hero/Matter-0.1-7B-boost, models/0-hero/Matter-0.1-7B-boost-DPO-preview, models/0-hero/Matter-0.1-7B-DPO-preview, models/0-hero/Matter-0.1-Slim-7B-A, models/0-hero/Matter-0.1-Slim-7B-B, models/0-hero/Matter-0.1-Slim-7B-C, models/0-hero/Matter-0.1-Slim-7B-C-DPO, models/0-hero/Matter-0.1-Slim-7B-preview, models/0-hero/Matter-0.2-32B, models/0-hero/Matter-0.2-7B, models/0-hero/Matter-0.2-7B-DPO, models/0-hero/Matter-0.2-8x22B, models/0-hero/mistral-speech-to-text, models/0-hero/mistral-speech-to-text-preview, models/0-hero/OLMo-50M-Mixture-of-Depths-Bitnet

000jd: models/000jd/banglaGPT, models/000jd/banglaGPT-v3, models/000jd/banglaGPTv2, models/000jd/phi-1_5-finetuned-bangla-bot, models/000jd/phi-1_5-finetuned-bangla-to-english-sentences-translation-bot

009qjqiwi: models/009qjqiwi/lora-trained-xl-colab, models/009qjqiwi/lora-trained-xl-colab-alimi, models/009qjqiwi/poormannai

Notes and limits

These authors and model IDs are exactly what was returned by the query; I didn’t add or infer any additional authors or models.
This is the returned subset of the graph results, not necessarily a full census of all authors or models in the Hub.



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
