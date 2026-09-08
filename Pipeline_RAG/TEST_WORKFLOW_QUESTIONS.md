# Test questions — GraphRAG workflow

Questions to run through `Pipeline_RAG` and check that the router picks the right branch, then that the answer looks reasonable.

Run each one from `00_run_script.ipynb`:

```python
from Graph.graph import app
result = app.invoke({"question": "..."})
```

Watch the console for the route:

| Print | Branch |
|---|---|
| `---ROUTE QUESTION TO GRAPH QA---` | Graph query: `prompt_template` → `graph_qa` |
| `---ROUTE QUESTION TO VECTOR SEARCH---` | Vector search: `decomposer` → `vector_search` → `prompt_template_with_context` → `graph_qa_with_context` |

The router (`Chains/router.py`) sends **semantic** questions (similar / related / about / like) to vector search, and **structural** ones (counts, known ids, relationship hops, aggregations) to graph QA.

---

## A. Graph query path

Expected route: `graph query`. These name a concrete id, ask for a count, or walk a relationship.

### Model

1. How many models are there in total?
2. What is the pipeline tag of bert-base-uncased?
3. Find models whose model id contains 'llama'.
4. What are the tags associated with bert-base-uncased?
5. Who created bert-base-uncased?
6. How many models has google created?
7. Which authors have created the most models?
8. Which Spaces use bert-base-uncased?
9. How many discussions does bert-base-uncased have?
10. Which files have conflicts in discussions on bert-base-uncased?

### Dataset

11. Find datasets tagged with 'speech-recognition'.
12. What are the descriptions of datasets tagged 'question-answering'?
13. Who created the dataset squad?
14. How many datasets has allenai created?
15. Which Spaces use the dataset squad?
16. How many datasets are there in total?

### Space

17. What is the SDK of huggingface/diffusers-demo?
18. How many Spaces are built with the 'gradio' SDK?
19. Which models does huggingface/diffusers-demo use?
20. Who created huggingface/diffusers-demo?
21. Which Spaces use both a model and a dataset?

### Repository / Author / Tag

22. Who created the repository bert-base-uncased?
23. What tags does the repository bert-base-uncased have?
24. What is the full name of the author google?
25. How many commits has google authored?
26. Which authors have created the most repositories?
27. How many repositories have the tag 'pytorch'?
28. Which tags co-occur with 'pytorch'?

### Discussion / Commits / ModifiedFile

29. How many discussions belong to bert-base-uncased?
30. Who opened discussions on bert-base-uncased?
31. How many commits are there in total?
32. Which files has google modified in their commits?
33. What commits has the creator of bert-base-uncased authored?

---

## B. Vector search path

Expected route: `vector search`. These ask for things **about / similar / related / like** a topic, without a concrete node id. The first hop should hit the matching label index (`Model`, `Dataset`, `Space`, `Author`, `Tag`, `Repository`).

### Model

34. Find models about text summarization.
35. Show models similar to BERT for sentence embeddings.
36. Which models are related to image generation?
37. Find models about speech-to-text.

### Dataset

38. Show datasets similar to one on speech recognition.
39. Find datasets about question answering.
40. Which datasets are related to named entity recognition?

### Space

41. Which Spaces are related to image generation?
42. Find Spaces like a Gradio demo for chatbots.
43. Show Spaces about audio transcription.

### Author / Tag / Repository

44. Find authors similar to Google Research.
45. Find tags related to natural language inference.
46. Find repositories about transformer language models.
47. Show repositories similar to a BERT model card.

### Mixed (vector first, then a graph hop)

These should still route to vector search. After the hits come back, the Cypher step should walk a relationship.

48. Find models about text classification and return who created them.
49. Show datasets similar to SQuAD and list the Spaces that use them.
50. Find Spaces related to image generation and return the models they use.
51. Find authors similar to Hugging Face and list the models they created.
52. Find models about translation and return their tags.

---

## How to score a run

For each question, write down:

1. **Route** — did the console print the expected branch?
2. **Hits (vector path only)** — do `context_refs` / `documents` have the right label (Model vs Dataset vs Space, …)?
3. **Answer** — is `result["documents"]` non-empty and on-schema (no `Article`, no `Commit` singular, no invented relationships)?
4. **Cypher (if logged)** — does it use `IS_A` → `Repository` before `HAS_TAG` / `CREATED_BY`, `USES_MODEL` / `USES_DATASET` from Space, and `Commits` (plural)?

If a graph-query question is sent to vector search (or the other way around), the failure is in `Chains/router.py`, not in Cypher generation.
