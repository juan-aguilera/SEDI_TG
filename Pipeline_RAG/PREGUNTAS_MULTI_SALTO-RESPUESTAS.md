# 28 preguntas multi-salto para evaluar GraphRAG

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

**Pregunta:** Which model or dataset has more discussions belonging to its repository?

**Tipo:** comparison de agregados

**Camino esperado:** para cada uno, `(:Model|:Dataset) -[:IS_A]-> Repository <-[:BELONGS_TO]- Discussion`, `count`, comparar.

**Por qué es multi-salto:** dos cadenas de conteo + comparación. Un `count` global de `Discussion`.

**Debe devolver:** el id ganador y los dos conteos.

**Respuesta**
 The repository with the most discussions in the returned results is the model j-hartmann/emotion-english-distilroberta-base — it has 6,012 discussions associated with its repository.

Details returned:

Repository: j-hartmann/emotion-english-distilroberta-base
Type: Model
Discussions (num_discussions): 6,012
What this means and limitations:

The field num_discussions is the count of discussion threads belonging to that repository on the Hub (as returned in this result).
No dataset rows were returned in the query result, so there is no dataset available here to compare against this model.
This answer is based only on the single row returned; if you want a full comparison across many models and datasets, request a larger result set.



---

### 9. ¿Mismo SDK en Spaces que usan cada uno?

**Pregunta:** Do any Spaces that use `bert-base-uncased` share an SDK with any Spaces that use the dataset `squad`?

**Tipo:** comparison de propiedades en vecinos de dos semillas

**Camino esperado:** `Space -[:USES_MODEL]-> Model` vs `Space -[:USES_DATASET]-> Dataset`, comparar conjuntos de `sdk`.

**Por qué es multi-salto:** hay que juntar dos vecindarios `USES_*` y cruzar una propiedad del Space, no del modelo ni del dataset.

**Debe devolver:** `yes`/`no` y los SDK en la intersección.

**Respuesta** Short answer: I can’t tell — the retrieval returned no rows, so I have no Space ids, SDK values, or dataset ids to compare for Spaces that use OmegLLaMA-3B.

What the empty result means:

No Space rows (with space.id and space.sdk) and no dataset-using Space rows were returned for this question.
An empty result can mean either there are no matching Space–dataset SDK overlaps in the graph, or the query/limit returned no rows; I can’t distinguish which from this empty result.
If a returned field were null/None it would mean that specific field was not returned — not that the Space lacks that property.
--query: MATCH (s1:Space)-[:USES_MODEL]->(m:Model) WHERE m.model_id = 'OmegLLaMA-3B' MATCH (s2:Space)-[:USES_DATASET]->(ds:Dataset) WHERE s1.sdk = s2.sdk RETURN DISTINCT s1.space_id AS space_id, ds.dataset_id AS dataset_id

---

### 10. ¿El creador del modelo también publicó datasets?

**Pregunta:** Did any author both createx a dataset and a model? If so, list them"

**Tipo:** comparison / existence across types

**Camino esperado:** `Model → Author`, luego `Author <-[:CREATED_BY]- Repository <-[:IS_A]- Dataset`.

**Por qué es multi-salto:** la pregunta es sobre **otra especialización** (`Dataset`) del mismo autor. 

**Debe devolver:** `yes`/`no` y `dataset_id` (o lista vacía explícita).

**Respuesta** 
Yes — several authors in the returned results have created both at least one dataset and at least one model. Below I list each such author, how many datasets and models were returned for them, and the identifiers of those datasets and models (truncated where the list is long).

Authors who created both datasets and models

0-hero — datasets (5), models (23)
Datasets:

datasets/0-hero/distilabel-math-preference-dpo
datasets/0-hero/lj_speech_with_spectogram
datasets/0-hero/lj_speech_with_spectogram_conversations
datasets/0-hero/OIG-small-chip2
datasets/0-hero/prompt-perfect
Models (first 5 shown):
models/0-hero/flan-alpaca-ul2
models/0-hero/flan-OIG-base
models/0-hero/flan-OIG-small
models/0-hero/flan-OIG-ul2
models/0-hero/flan-OIG-xl
...and 18 more models returned (see the results for the full list)
003myjoker1 — datasets (1), models (2)
Datasets:

datasets/003myjoker1/test
Models:
models/003myjoker1/llama-3-ru
models/003myjoker1/Realistic_Vision_V6.0_B1
012shin — datasets (7), models (7)
Datasets (all returned):

datasets/012shin/custompublic01
datasets/012shin/fake-audio-detection-augmented
datasets/012shin/fake-audio-detection-augmented2
datasets/012shin/fake-audio-detection-augmented_spec
datasets/012shin/fake-audio-detection-unsupervised
datasets/012shin/llama3-QA-pa-train
datasets/012shin/llama3-QA-pa-val
Models (all returned):
models/012shin/koalphaca_savepoint
models/012shin/llama3-finetuned-Public_administration
models/012shin/qlora-koalpaca-polyglot-12.8b-50step
models/012shin/qlora-koalpaca-polyglot-12.8b-QA
models/012shin/qlora-koalpaca-polyglot-5.8b-QA
models/012shin/roberta-finetuned-Public_Administration
models/012shin/roberta-finetuned-Public_Administration_full
026g — datasets (1), models (1)
Datasets:

datasets/026g/Test
Models:
models/026g/Test
0530tuandui — datasets (2), models (3)
Datasets:

datasets/0530tuandui/22
datasets/0530tuandui/gongxianzhe
Models:
models/0530tuandui/0614moxing
models/0530tuandui/11
models/0530tuandui/xie
05deepak — datasets (4), models (1)
Datasets:

datasets/05deepak/17k_synthetic_dataset_llama3_70b
datasets/05deepak/my-dataset
datasets/05deepak/synthetic_10k_subjects_classifier_dataset
datasets/05deepak/synthetic_16k_subjects_classifier_dataset
Models:
models/05deepak/finnetuned-tf-base-model
080-ai — datasets (4), models (5)
Datasets:

datasets/080-ai/20k_wikipedia_title_prompts
datasets/080-ai/3k_summarization
datasets/080-ai/mcq_ps_v1
datasets/080-ai/summary_history_alpaca
Models:
models/080-ai/flintlock_3B_v0.1
models/080-ai/flintlock_3B_v0.1a
models/080-ai/flintlock_3B_v0.1b
models/080-ai/sabre-2B
models/080-ai/tiny-cutlass
0ho — datasets (7), models (1)
Datasets:

datasets/0ho/C_openssl
datasets/0ho/libicu_pseudo_code
datasets/0ho/llama2
datasets/0ho/openssl_instruction
datasets/0ho/openssl_instruction2
datasets/0ho/openssl_pseudocode
datasets/0ho/pseudo_func
Models:
models/0ho/Checkso_libicu_ver
0ppxnhximxr — datasets (2), models (10)
Datasets:

datasets/0ppxnhximxr/CodeAI-train
datasets/0ppxnhximxr/CodeAI-valid
Models (first 4 shown):
models/0ppxnhximxr/CodeAI
models/0ppxnhximxr/CodeAI-small
models/0ppxnhximxr/CodeAI-small-vocabulary
models/0ppxnhximxr/distilbert-base-uncased-finetuned-emotion
...and 6 more models returned
0sunfire0 — datasets (2), models (18)
Datasets:

datasets/0sunfire0/QA-Treasuries-528-trimmed
datasets/0sunfire0/QA-Treasuries-539
Models (first 6 shown):
models/0sunfire0/a2c-AntBulletEnv-v0
models/0sunfire0/a2c-PandaReachDense-v2
models/0sunfire0/Cartpole-v1_train_01
models/0sunfire0/dqn-SpaceInvaders-00
models/0sunfire0/Llama_13b_test02
models/0sunfire0/Llama_7B_Test08
...and 12 more models returned
Limits and notes

This list is exactly what was returned in the query result you provided. It may be a limited/top-N subset of the graph rather than a full census of all authors on the Hub.
If a field were null/None in the returned rows it would mean that specific field was not returned; here every shown author has both datasets and models arrays populated in the result.


---

## C. Intersección y 3–4 hops (lo más difícil)

El paper muestra que Recall cae al subir el número de documentos de apoyo y la distancia entidad-nivel. Estas preguntas exigen **tres o más aristas**, a menudo con un filtro en cada hop.

### 11. Spaces Gradio que usan modelos de un autor descubierto

**Pregunta:** Which Gradio Spaces use a model created by the same author as the model `models/bigscience/bloom`?

**Tipo:** intersección + puente (3 hops)

**Camino esperado:** `bert-base-uncased → Author → Model → Space` con `s.sdk = 'gradio'`.

**Por qué es multi-salto:** tres restricciones independientes (autor puente, `USES_MODEL`, `sdk`). Nombrar `google` en el Cypher porque “se sabe” es hacer trampa: el autor debe salir del grafo.

**Debe devolver:** `space_id` (limitar a 20 si hay muchos).

**Respuesta**
Direct answer: The graph query returned these 10 Gradio Space repositories as matches for “Spaces that use a model created by the same author as models/bigscience/bloom.”

What was returned

ysharma/dummy_m4
009qjqiwi/bigscience-bloom
0x7d8/gpt4free
101-5/gpt4free
63ji/bigscience-bloom
9bestenbier/bigscience-bloom
a1092/bigscience-bloom
aavyas/bigscience-bloom
Abdullah36/bigscience-bloom
abdulmeLINK/debugger-bloom
What this means

These repository IDs (owner/repo) are the Space nodes the query returned as using a model created by the same author as models/bigscience/bloom.
Many of the matches are independent Spaces whose repo name includes "bigscience-bloom" (different owners), which suggests multiple people have Spaces named around that model.
Two different repos are named "gpt4free" under different owners, and two others have different names (dummy_m4 and debugger-bloom).

--query: 
MATCH (m0:Model {model_id: 'models/bigscience/bloom'})-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)
MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m:Model)<-[:USES_MODEL]-(s:Space)
WHERE s.sdk = 'gradio'
RETURN DISTINCT s.space_id


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

**Respuesta**
Short answer: The query returned these ten authors as matching your criteria — each was found to have (1) created at least one model tagged "pytorch" and (2) created at least one dataset that is used by at least one Space.

Authors returned

0-hero
abidlabs
abokbot
agemagician
ahuang11
akoksal
unknown
albertvillanova
alespalla
alexkueck

--query:
MATCH (t:Tag)<-[:HAS_TAG]-(r1:Repository)<-[:IS_A]-(m:Model) MATCH (r1)-[:CREATED_BY]->(au:Author) WHERE t.name = 'pytorch' MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset)-[:IS_A]->(r2:Repository)-[:CREATED_BY]->(au) RETURN DISTINCT au.username


---

### 19. Pipeline tags de modelos cuyos creadores también commitean archivos

**Pregunta:** What pipeline tags appear on models whose creators have also authored commits that modify files?

**Tipo:** intersección 4-hop

**Camino esperado:** `ModifiedFile <-[:MODIFIES]- Commits -[:AUTHORED_BY]-> Author <-[:CREATED_BY]- Repository <-[:IS_A]- Model` → `pipeline_tag`

**Por qué es multi-salto:** cruza el subgrafo de historial (`Commits`/`ModifiedFile`) con el de publicación (`Model`). No hay arista directa entre archivo y pipeline tag.

**Debe devolver:** `pipeline_tag` distintos.

**Respuesta**
Direct answer: The models whose creators also authored commits that modify files have these pipeline tags: unknown, text-to-image, conversational, text-generation, image-text-to-text, text2text-generation, robotics, and video-to-video.

What this means:

Each of the listed pipeline tags was observed on at least one model whose creator is also listed as the author of a commit that modified files.
The unknown entry is the literal pipeline_tag value returned by the query — it means the tag value was "unknown" in the results, not that the tag field was necessarily missing in the Hub.
The other tags span several usage areas suggested by their names: text-focused (text-generation, text2text-generation, conversational), image/multimodal (text-to-image, image-text-to-text, video-to-video), and robotics.
Returned tags (one per line):

unknown
text-to-image
conversational
text-generation
image-text-to-text
text2text-generation
robotics
video-to-video

---query: MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) RETURN DISTINCT m.pipeline_tag

---

### 20. Autores que discuten un modelo que no crearon

**Pregunta:** Are there authors who opened a discussion on a model they did not create? List up to 10 such (discussion_author, model_id, model_author) triples.

**Tipo:** comparación de dos caminos que llegan a `Author`

**Camino esperado:** `Discussion -[:CREATED_BY]-> Author_d` y `Discussion -[:BELONGS_TO]-> Repository <-[:IS_A]- Model -[:CREATED_BY]-> Author_m` con `Author_d <> Author_m`.

**Por qué es multi-salto:** hay que **alinear** dos cadenas sobre la misma discusión y exigir desigualdad. Un listado de autores de discusiones, sin cruzar con el creador del modelo, no responde.

**Debe devolver:** hasta 10 tripletas.

**Respuesta** 

Yes — the retrieved rows show authors who opened discussions on models they did not create. Below are up to 10 such (discussion_author, model_id, model_author) triples from the result.

Matches (unique triples, up to 10)

sfconvertbot, models/0-hero/flan-OIG-base, 0-hero
sfconvertbot, models/0-hero/flan-OIG-small, 0-hero
sfconvertbot, models/0-hero/led-large-legal-summary, 0-hero
kevinpro, models/0-hero/Matter-0.1-7B, 0-hero
sfconvertbot, models/0-hero/Matter-0.1-7B-boost, 0-hero
What this means

Each triple shows a discussion opener (discussion_author) who is different from the model’s author (model_author = 0-hero), so these are examples of people opening discussions on other authors’ models.
All returned rows reference models whose author is 0-hero; the discussion authors in the result are sfconvertbot and kevinpro.

--query: MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)<-[:IS_A]-(m:Model), (d)-[:CREATED_BY]->(disc:Author), (r)-[:CREATED_BY]->(modelAuthor:Author) WHERE disc.username <> modelAuthor.username RETURN disc.username AS discussion_author, m.model_id AS model_id, modelAuthor.username AS model_author LIMIT 10


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


**Respuesta**
Short answer: I found five models flagged for image generation, but none of them list any Spaces that use them — so no Space authors were returned by this result.

Models matched (what the query returned)

aellaboudy/generativeModel — pipeline_tag: text-to-image. Tags include: base_model:runwayml/stable-diffusion-v1-5, diffusers, stable-diffusion, text-to-image.
MY555/Surya-Image-generator-tunning — pipeline_tag: text-to-image. Tags include: base_model:stabilityai/stable-diffusion-xl-base-1.0, diffusers, stable-diffusion-xl, text-to-image.
ayjays132/CustomImageGenerator — pipeline_tag: text-to-image. Tags include: diffusers, image-generation, generative-model, diffusers:StableDiffusionPipeline, license:apache-2.0.
Genrator/1st — pipeline_tag: text-to-image. Tags include: diffusers, diffusers:StableDiffusionPipeline, stable-diffusion, text-to-image.
Lonewolf2005/MyImageGen-VGG16 — pipeline_tag: unknown. Tags returned: license:apache-2.0, region:us.
What “spaces” and authors were returned

For every model above, the returned "spaces" field is an empty list. That means this retrieval did not return any Spaces that use those models, and therefore no Space authors were included in the results.
Notes and next steps

The result set here is what was returned; an empty spaces array is not proof there are no Spaces in the Hub that use these models — it only means none were returned by this query/result.
If you want the authors of Spaces that actually reference these models, I can (a) run a query specifically to find Spaces that reference each repo (and return their authors), or (b) look up a specific model’s repo page for linked Spaces — tell mend by the retrieval — not necessarily an exhaustive list of all Hub authors who ever use image-generation models.





---

### 24. Datasets de un tema, Spaces que los usan, SDK y modelos de esos Spaces

**Pregunta:** Find datasets about question answering, then list the Spaces that use them, the SDK of those Spaces, and the models those Spaces use.

**Tipo:** semantic seed + 3 graph hops (MuSiQue 3-hop)

**Camino esperado:** vector/`HAS_TAG` sobre Dataset (QA / SQuAD-like) → `USES_DATASET` → `sdk` → `USES_MODEL`

**Por qué es multi-salto:** tres hechos de apoyo en labels distintos. Un decomposer débil genera solo “find QA datasets” y nunca camina a Space/Model.

**Debe devolver:** `dataset_id`, `space_id`, `sdk`, `model_id` (limitar a 10 filas).


**Respuesta**

Direct answer — what the result shows: I found five datasets that appear to be about question answering. In the returned rows, none of these datasets had any Spaces using them (the "spaces" field is an empty list for every dataset), so there are no SDKs or Space-linked models to report from this result.

Datasets returned

RUCAIBox/Question-Answering (datasets/RUCAIBox/Question-Answering) — downloads: 1
Description: not returned.
Spaces referencing this dataset: none returned.
Models used by those Spaces: none returned.

datapaf/CodeQuestionAnswering (datasets/datapaf/CodeQuestionAnswering) — downloads: 2
Description: not returned.
Spaces referencing this dataset: none returned.
Models used by those Spaces: none returned.

jp1924/VisualQuestionAnswering (datasets/jp1924/VisualQuestionAnswering) — downloads: 10
Description: not returned.
Spaces referencing this dataset: none returned.
Models used by those Spaces: none returned.

weijiang2009/AlgmonQuestioningAnsweringDataset (datasets/weijiang2009/AlgmonQuestioningAnsweringDataset) — downloads: 1
Description: not returned.
Spaces referencing this dataset: none returned.
Models used by those Spaces: none returned.

vivekraina/Stanford_Question_Answering_Dataset (datasets/vivekraina/Stanford_Question_Answering_Dataset) — downloads: 2
Description: not returned.
Spaces referencing this dataset: none returned.
Models used by those Spaces: none returned.

Interpretation and next steps

Because every dataset row has an empty "spaces" array, there is no SDK field or Space model list returned to extract. That means from this particular retrieval you cannot list Spaces, their SDKs, or models for these datasets.
If you want, I can try to retrieve Spaces that reference one or more of these dataset repositories (or search the Hub for Spaces tagged with "question-answering") to obtain the SDK and model information. Tell me which dataset(s) you'd like me to investigate next.

---

### 26. Spaces de un tema, pipeline de los modelos que usan y autores de esos modelos

**Pregunta:** Find Spaces about speech recognition and return the pipeline tag of the models they use together with the authors of those models.

**Tipo:** semantic seed + 2 graph hops

**Camino esperado:** vector sobre `Space` → `Space -[:USES_MODEL]-> Model` (`pipeline_tag`) → `Model -[:IS_A]-> Repository -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** “Spaces de speech recognition” es la semilla semántica. La respuesta pedida es el `pipeline_tag` y el autor del **modelo**, no el Space ni su SDK. Quedarse en la lista de Spaces es single-hop.

**Debe devolver:** `space_id`, `model_id`, `pipeline_tag`, `author.username` (limitar a 10).

**Respuesta**
Direct answer — what the result shows: There are four models linked to Spaces about speech recognition in the returned rows. Three models are labeled with the pipeline tag automatic-speech-recognition, and one model’s pipeline tag was returned as unknown. For every model the authors field was an empty list (no author information was returned).

Models and the Spaces that use them (grouped by pipeline tag)

automatic-speech-recognition

facebook/wav2vec2-base-960h — used by Space: Engg-Abhinav/Speech-Recognition
Authors: the authors list was empty (no authors returned).

Mei000/whisper-small-sv-SE — used by Space: Mei000/Speech_recognition
Authors: the authors list was empty (no authors returned).

facebook/s2t-medium-librispeech-asr — used by Spaces: Stereo0001/Speech-Recognition-Example and radames/Speech-Recognition-Example
Authors: the authors list was empty (no authors returned).

unknown

csukuangfj/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20 — used by Space: waysolong/speech-recognition
Authors: the authors list was empty (no authors returned).
Notes and next steps

The empty authors arrays mean the query returned no author information for these models; it does not prove the models have no authors on the Hub.
If you want, I can fetch the Spaces themselves or the individual model pages to retrieve full author metadata, model descriptions, or other pipeline tags.


---

### 27. Modelos de un tema, datasets que usan los Spaces puente y autores de esos datasets

**Pregunta:** Find models about named entity recognition, then list the datasets used by Spaces that use those models and the authors of those datasets.

**Tipo:** semantic seed + 3 graph hops (bridge)

**Camino esperado:** vector sobre `Model` → `Space -[:USES_MODEL]-> Model` → `Space -[:USES_DATASET]-> Dataset` → `Dataset -[:IS_A]-> Repository -[:CREATED_BY]-> Author`

**Por qué es multi-salto:** el dataset no está ligado al modelo. El Space es el **puente**, y el autor pedido es el del dataset. Devolver modelos de NER, o los Spaces que los usan, deja el camino a medias.

**Debe devolver:** `model_id`, `space_id`, `dataset_id`, `author.username` (limitar a 10).

**Respuesta**: Short answer: I found two named‑entity‑recognition models and six Spaces that reference NER models, but the query result did not return any datasets or dataset authors — so I cannot list datasets used by those Spaces or give their authors from this result.

Found NER models

models/imrazaa/named-entity-recognition-multinerd
models/mdarhri00/named-entity-recognition
Spaces that reference named‑entity‑recognition models (returned)

spaces/adolph69/mdarhri00-named-entity-recognition
spaces/asmalljob/docker01
spaces/DanyaalMajid/NLP-Q2
spaces/Ellison0922/mdarhri00-named-entity-recognition
spaces/guptavipin/named-entity-recognition
spaces/mcheng/mdarhri00-named-entity-recognition
What this result means

The query successfully returned the two NER model IDs and a list of Spaces that use NER models.
However, the fields for datasets and dataset_authors are empty in the returned document. That means the retrieval did not include datasets used by those Spaces nor the authors of any such datasets — not that those Spaces necessarily use no datasets.
The returned data does not include a mapping of which specific Space uses which specific model, so I can’t assert connections beyond the lists shown.


---

### 28. Datasets parecidos a un tema, Spaces Streamlit que los usan y tags de esos Spaces

**Pregunta:** Find datasets similar to ones about sentiment analysis, keep only the Streamlit Spaces that use them, and return the tags of those Spaces.

**Tipo:** semantic seed + intersección + 2 hops

**Camino esperado:** vector sobre `Dataset` → `Space -[:USES_DATASET]-> Dataset` con `sdk = 'streamlit'` → `Space -[:IS_A]-> Repository -[:HAS_TAG]-> Tag`

**Por qué es multi-salto:** tres filtros en labels distintos (dataset semántico, SDK del Space, tags del Space). Ningún nodo solo junta el tema del dataset, el SDK y los tags.

**Debe devolver:** `dataset_id`, `space_id`, lista de tags del Space (limitar a 10).

**Respuesta**
Short answer: the query returned five sentiment‑analysis datasets but none of them had any Streamlit Spaces listed as users, so there are no Streamlit Space tags to return from this result.

What the result means

For each of the five datasets the returned "spaces" field is an empty list, so the retrieval did not return any Streamlit Spaces that use these datasets.
A missing / empty "spaces" array in these rows means the query did not return Space usage data for these datasets — it is not proof that no Space uses them, only that this result does not show any.
Datasets the query did return (dataset id — repo name — dataset tags when available)

datasets/Huggmachas/sentiment-analysis-datasets — Huggmachas/sentiment-analysis-datasets — tags: ["region:us"]
datasets/nlplabtdtu/sentiment-analysis-se — nlplabtdtu/sentiment-analysis-se — tags: ["region:us"]
datasets/sinarashidi/sentiment-analysis — sinarashidi/sentiment-analysis — tags: ["region:us"]
datasets/mohamedsaeed823/sentiment-analysis — mohamedsaeed823/sentiment-analysis — tags: ["croissant", "csv", "datasets", "license:apache-2.0", "mlcroissant", "pandas", "region:us", "size_categories:1K<n<10K", "text"]
datasets/ttxy/sentiment — ttxy/sentiment — tags: ["language:code", "license:bsd", "region:us", "sentiment", "task_categories:text-classification"]
Conclusion about Streamlit Space tags

Because no Streamlit Spaces were returned in the "spaces" fields, there are no Space tags to list from this result.
Recommended next steps to get the Space tags you want

Query Spaces that reference these specific dataset IDs (or the dataset's repo pages) and filter those Spaces by widget framework = Streamlit.
Alternatively, inspect each dataset’s repository page for a "Used in" / "Spaces using this dataset" section or check Space README files for dataset references.
If you want, I can produce the exact query template or a checklist of fields to request so the next retrieval returns Space ids and their tags.


--query: MATCH (ds:Dataset) WHERE ds.dataset_id IN ['datasets/Huggmachas/sentiment-analysis-datasets','datasets/nlplabtdtu/sentiment-analysis-se','datasets/sinarashidi/sentiment-analysis','datasets/mohamedsaeed823/sentiment-analysis','datasets/ttxy/sentiment'] OPTIONAL MATCH (ds)-[:IS_A]->(r:Repository) OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag) OPTIONAL MATCH (s:Space)-[:USES_DATASET]->(ds) WITH ds, r, collect(DISTINCT t.name) AS tags, collect(DISTINCT s.space_id) AS spaces RETURN ds.dataset_id AS dataset_id, ds.description AS description, r.id AS repo_id, r.name AS repo_name, tags, spaces


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
| 26 | sem+2 | vector+graph | tema (Space) | pipeline + author del Model |
| 27 | sem+3 | vector+graph | tema (Model) | dataset puente + author |
| 28 | sem+2 | vector+graph | dataset~tema | Space Streamlit + tags |

---

## Notas de implementación al evaluar

- **`IS_A` no es opcional** para tags y autores: `HAS_TAG` y `CREATED_BY` salen de `Repository`, no de `Model`/`Dataset`/`Space`.
- **`USES_MODEL` / `USES_DATASET` salen del Space**, no del modelo/dataset.
- **`Commits`** es el label con datos; **`Commit`** tiene 0 nodos.
- **`HAS_CONFLICTING_FILE`** lleva `filename` y `repo_file_id` en la arista.
- Las preguntas 17, 19 y 20 no nombran ids: si el modelo se inventa un `model_id` famoso en vez de agregar sobre el grafo, es fallo.
- Si 23–28 caen en `graph query` sin vector search, no es automáticamente un error: un Cypher con `CONTAINS` / tags puede ser válido. El error es **no completar los hops posteriores**.
- Este banco **no** incluye preguntas single-hop del estilo “How many models are there?” o “What is the pipeline tag of bert-base-uncased?”. Esas ya están en `TEST_WORKFLOW_QUESTIONS.md`.
