examples = [
    # ── Model ────────────────────────────────────────────────────────
    {
        "question": "What is the pipeline tag of a specific model, e.g bert-base-uncased?",
        "query": "MATCH (m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN m.model_id, m.pipeline_tag",
    },
    {
        "question": "Find all models with the pipeline tag 'text-classification'",
        "query": "MATCH (m:Model) WHERE m.pipeline_tag = 'text-classification' RETURN m.model_id",
    },
    {
        "question": "How many models have the pipeline tag 'text-generation'?",
        "query": "MATCH (m:Model) WHERE m.pipeline_tag = 'text-generation' RETURN count(m)",
    },
    {
        "question": "How many models are there in total?",
        "query": "MATCH (m:Model) RETURN count(m)",
    },
    {
        "question": "Find models whose model id contains a specific keyword, e.g 'llama'",
        "query": "MATCH (m:Model) WHERE m.model_id CONTAINS 'llama' RETURN m.model_id LIMIT 10",
    },
    {
        "question": "Search for models whose configuration mentions a specific keyword, e.g 'transformer'",
        "query": "MATCH (m:Model) WHERE m.config CONTAINS 'transformer' RETURN m.model_id LIMIT 10",
    },
    {
        "question": "What are the tags associated with a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE m.model_id = 'bert-base-uncased' RETURN t.name",
    },
    {
        "question": "How many tags does a specific model have?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE m.model_id = 'bert-base-uncased' RETURN count(t)",
    },
    {
        "question": "Which models have the tag 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(m:Model) WHERE t.name = 'pytorch' RETURN m.model_id",
    },
    {
        "question": "How many models are tagged with 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(m:Model) WHERE t.name = 'pytorch' RETURN count(m)",
    },
    {
        "question": "Which models have both the tag 'pytorch' and the pipeline tag 'text-classification'?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE t.name = 'pytorch' AND m.pipeline_tag = 'text-classification' RETURN m.model_id",
    },
    {
        "question": "What are the top 10 tags with the most models?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(m) AS num_models ORDER BY num_models DESC LIMIT 10",
    },
    {
        "question": "Which model has the largest number of tags?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN m.model_id, count(t) AS num_tags ORDER BY num_tags DESC LIMIT 5",
    },
    {
        "question": "Who created a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) WHERE m.model_id = 'bert-base-uncased' RETURN au.username",
    },
    {
        "question": "What is the full name of the author who created a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) WHERE m.model_id = 'bert-base-uncased' RETURN au.fullname",
    },
    {
        "question": "What models were created by a specific author, e.g 'google'?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(m:Model) WHERE au.username = 'google' RETURN m.model_id",
    },
    {
        "question": "How many models has a specific author created?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(m:Model) WHERE au.username = 'google' RETURN count(m)",
    },
    {
        "question": "Which authors have created the most models?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(m) AS num_models ORDER BY num_models DESC LIMIT 10",
    },
    {
        "question": "What is the repository name and id of a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository) WHERE m.model_id = 'bert-base-uncased' RETURN r.name, r.id",
    },
    {
        "question": "Which other models share tags with a specific model?",
        "query": "MATCH (m1:Model)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(m2:Model) WHERE m1.model_id = 'bert-base-uncased' AND m1 <> m2 RETURN DISTINCT m2.model_id LIMIT 10",
    },
    {
        "question": "Which other models were created by the same author as a specific model?",
        "query": "MATCH (m1:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m2:Model) WHERE m1.model_id = 'bert-base-uncased' AND m1 <> m2 RETURN DISTINCT m2.model_id",
    },
    {
        "question": "Which Spaces use a specific model?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN s.space_id",
    },
    {
        "question": "How many Spaces use a specific model?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN count(s)",
    },
    {
        "question": "What are the most used models by Spaces?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) RETURN m.model_id, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which models are used by Spaces built with the 'gradio' SDK?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) WHERE s.sdk = 'gradio' RETURN DISTINCT m.model_id",
    },
    {
        "question": "List the models used by a specific Space along with their tags",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN m.model_id, collect(t.name) AS tags",
    },
    {
        "question": "What discussions exist for a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE m.model_id = 'bert-base-uncased' RETURN d",
    },
    {
        "question": "How many discussions does a specific model have?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE m.model_id = 'bert-base-uncased' RETURN count(d)",
    },
    {
        "question": "Who opened discussions on a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(au:Author) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT au.username",
    },
    {
        "question": "Which files have conflicts in discussions on a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)<-[c:HAS_CONFLICTING_FILE]-(d:Discussion) WHERE m.model_id = 'bert-base-uncased' RETURN c.filename, c.repo_file_id",
    },
    {
        "question": "What commits has the creator of a specific model authored?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE m.model_id = 'bert-base-uncased' RETURN c LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific model modified in their commits?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    # ── Dataset ──────────────────────────────────────────────────────¿
    {
        "question": "What are the descriptions of datasets related to a specific topic, e.g 'question-answering'?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE t.name = 'question-answering' RETURN ds.dataset_id, ds.description LIMIT 10",
    },
    {
        "question": "Find datasets whose dataset id contains a specific keyword, e.g 'glue'",
        "query": "MATCH (ds:Dataset) WHERE ds.dataset_id CONTAINS 'glue' RETURN ds.dataset_id LIMIT 10",
    },
    {
        "question": "Search for datasets whose description mentions a specific keyword, e.g 'question answering'",
        "query": "MATCH (ds:Dataset) WHERE ds.description CONTAINS 'question answering' RETURN ds.dataset_id LIMIT 10",
    },
    {
        "question": "How many datasets are there in total?",
        "query": "MATCH (ds:Dataset) RETURN count(ds)",
    },
    {
        "question": "What are the tags associated with a specific dataset (e.g squad)?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE ds.dataset_id = 'squad' RETURN t.name",
    },
    {
        "question": "How many tags does a specific dataset have?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE ds.dataset_id = 'squad' RETURN count(t)",
    },
    {
        "question": "Which datasets have the tag 'nli'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE t.name = 'nli' RETURN ds.dataset_id",
    },
    {
        "question": "How many datasets are tagged with 'nli'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE t.name = 'nli' RETURN count(ds)",
    },
    {
        "question": "What are the top 10 tags with the most datasets?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(ds) AS num_datasets ORDER BY num_datasets DESC LIMIT 10",
    },
    {
        "question": "Which dataset has the largest number of tags?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN ds.dataset_id, count(t) AS num_tags ORDER BY num_tags DESC LIMIT 5",
    },
    {
        "question": "What is the full name of the author who created a specific dataset?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) WHERE ds.dataset_id = 'squad' RETURN au.fullname",
    },
    {
        "question": "What datasets were created by a specific author, e.g 'allenai'?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE au.username = 'allenai' RETURN ds.dataset_id",
    },
    {
        "question": "How many datasets has a specific author created, e.g 'allenai'?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE au.username = 'allenai' RETURN count(ds)",
    },
    {
        "question": "Which authors have created the most datasets?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(ds) AS num_datasets ORDER BY num_datasets DESC LIMIT 10",
    },
    {
        "question": "What is the repository name and id of a specific dataset, e.g squad?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository) WHERE ds.dataset_id = 'squad' RETURN r.name, r.id",
    },
    {
        "question": "Which other datasets share tags with a specific dataset?",
        "query": "MATCH (ds1:Dataset)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(ds2:Dataset) WHERE ds1.dataset_id = 'squad' AND ds1 <> ds2 RETURN DISTINCT ds2.dataset_id LIMIT 10",
    },
    {
        "question": "Which other datasets were created by the same author as a specific dataset?",
        "query": "MATCH (ds1:Dataset)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(ds2:Dataset) WHERE ds1.dataset_id = 'squad' AND ds1 <> ds2 RETURN DISTINCT ds2.dataset_id",
    },
    {
        "question": "Which Spaces use a specific dataset?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE ds.dataset_id = 'squad' RETURN s.space_id",
    },
    {
        "question": "How many Spaces use a specific dataset?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE ds.dataset_id = 'squad' RETURN count(s)",
    },
    {
        "question": "What are the most used datasets by Spaces?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) RETURN ds.dataset_id, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which datasets are used by Spaces built with the 'gradio' SDK?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE s.sdk = 'gradio' RETURN DISTINCT ds.dataset_id",
    },
    {
        "question": "What discussions exist for a specific dataset?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE ds.dataset_id = 'squad' RETURN d",
    },
    {
        "question": "Which files have conflicts in discussions on a specific dataset?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository)<-[c:HAS_CONFLICTING_FILE]-(d:Discussion) WHERE ds.dataset_id = 'squad' RETURN c.filename, c.repo_file_id",
    },
    # ── Space ────────────────────────────────────────────────────────
    {
        "question": "What is the SDK of a specific Space, e.g huggingface/diffusers-demo?",
        "query": "MATCH (s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN s.space_id, s.sdk",
    },
    {
        "question": "What hardware does a specific Space run on?",
        "query": "MATCH (s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN s.space_id, s.hardware",
    },
    {
        "question": "Find all Spaces built with the 'gradio' SDK",
        "query": "MATCH (s:Space) WHERE s.sdk = 'gradio' RETURN s.space_id",
    },
    {
        "question": "Find all Spaces built with the 'streamlit' SDK",
        "query": "MATCH (s:Space) WHERE s.sdk = 'streamlit' RETURN s.space_id",
    },
    {
        "question": "Find Spaces whose space id contains a specific keyword, e.g 'demo'",
        "query": "MATCH (s:Space) WHERE s.space_id CONTAINS 'demo' RETURN s.space_id LIMIT 10",
    },
    {
        "question": "How many Spaces are there in total?",
        "query": "MATCH (s:Space) RETURN count(s)",
    },
    {
        "question": "How many Spaces are built with the 'gradio' SDK?",
        "query": "MATCH (s:Space) WHERE s.sdk = 'gradio' RETURN count(s)",
    },
    {
        "question": "What are the tags associated with a specific Space?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN t.name",
    },
    {
        "question": "Which Spaces have the tag 'text-to-image'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(s:Space) WHERE t.name = 'text-to-image' RETURN s.space_id",
    },
    {
        "question": "Who created a specific Space?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN au.username",
    },
    {
        "question": "What Spaces were created by a specific author, e.g 'huggingface'?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(s:Space) WHERE au.username = 'huggingface' RETURN s.space_id",
    },
    {
        "question": "Which authors have created the most Spaces?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "What is the repository name and id of a specific Space?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN r.name, r.id",
    },
    {
        "question": "Which models does a specific Space use?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN m.model_id",
    },
    {
        "question": "How many models does a specific Space use?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN count(m)",
    },
    {
        "question": "Which datasets does a specific Space use?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN ds.dataset_id",
    },
    {
        "question": "How many datasets does a specific Space use?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN count(ds)",
    },
    {
        "question": "Which Spaces use both a model and a dataset?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(:Model) MATCH (s)-[:USES_DATASET]->(:Dataset) RETURN DISTINCT s.space_id LIMIT 10",
    },
    {
        "question": "Which Spaces use a specific dataset, e.g squad?",
        "query": "MATCH (s:Space)-[:USES_DATASET]->(ds:Dataset) WHERE ds.dataset_id = 'squad' RETURN s.space_id",
    },
    {
        "question": "List the models and datasets used by a specific Space",
        "query": "MATCH (s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' OPTIONAL MATCH (s)-[:USES_MODEL]->(m:Model) OPTIONAL MATCH (s)-[:USES_DATASET]->(ds:Dataset) RETURN collect(DISTINCT m.model_id) AS models, collect(DISTINCT ds.dataset_id) AS datasets",
    },
    {
        "question": "Which other Spaces share tags with a specific Space?",
        "query": "MATCH (s1:Space)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(s2:Space) WHERE s1.space_id = 'huggingface/diffusers-demo' AND s1 <> s2 RETURN DISTINCT s2.space_id LIMIT 10",
    },
    {
        "question": "Which other Spaces were created by the same author as a specific Space?",
        "query": "MATCH (s1:Space)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(s2:Space) WHERE s1.space_id = 'huggingface/diffusers-demo' AND s1 <> s2 RETURN DISTINCT s2.space_id",
    },
    {
        "question": "What discussions exist for a specific Space?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN d",
    },
    {
        "question": "Which files have conflicts in discussions on a specific Space?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository)<-[c:HAS_CONFLICTING_FILE]-(d:Discussion) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN c.filename, c.repo_file_id",
    },
    # ── Repository ───────────────────────────────────────────────────
    {
        "question": "What is the name of a specific repository, e.g bert-base-uncased?",
        "query": "MATCH (r:Repository) WHERE r.id = 'bert-base-uncased' RETURN r.id, r.name",
    },
    {
        "question": "Find repositories whose name contains a specific keyword, e.g 'bert'",
        "query": "MATCH (r:Repository) WHERE r.name CONTAINS 'bert' RETURN r.id, r.name LIMIT 10",
    },
    {
        "question": "Search for repositories whose card data mentions a specific keyword, e.g 'transformer'",
        "query": "MATCH (r:Repository) WHERE r.card_data CONTAINS 'transformer' RETURN r.id, r.name LIMIT 10",
    },
    {
        "question": "How many repositories are there in total?",
        "query": "MATCH (r:Repository) RETURN count(r)",
    },
    {
        "question": "What are the tags associated with a specific repository?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) WHERE r.id = 'bert-base-uncased' RETURN t.name",
    },
    {
        "question": "How many tags does a specific repository have?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) WHERE r.id = 'bert-base-uncased' RETURN count(t)",
    },
    {
        "question": "Which repositories have the tag 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository) WHERE t.name = 'pytorch' RETURN r.id, r.name",
    },
    {
        "question": "What are the top 10 tags with the most repositories?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "Which repository has the largest number of tags?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) RETURN r.id, r.name, count(t) AS num_tags ORDER BY num_tags DESC LIMIT 5",
    },
    {
        "question": "Who created a specific repository, e.g 'bert-base-uncased'0?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author) WHERE r.id = 'bert-base-uncased' RETURN au.username",
    },
    {
        "question": "What repositories were created by a specific author, e.g 'google'?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository) WHERE au.username = 'google' RETURN r.id, r.name",
    },
    {
        "question": "Which authors have created the most repositories?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "Is a specific repository a Model, Dataset or Space?",
        "query": "MATCH (n)-[:IS_A]->(r:Repository) WHERE r.id = 'bert-base-uncased' RETURN labels(n) AS specialization",
    },
    {
        "question": "How many repositories are Models?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository) RETURN count(r)",
    },
    {
        "question": "How many repositories are Datasets?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(r:Repository) RETURN count(r)",
    },
    {
        "question": "How many repositories are Spaces?",
        "query": "MATCH (s:Space)-[:IS_A]->(r:Repository) RETURN count(r)",
    },
    {
        "question": "What discussions belong to a specific repository?",
        "query": "MATCH (r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE r.id = 'bert-base-uncased' RETURN d",
    },
    {
        "question": "How many discussions belong to a specific repository?",
        "query": "MATCH (r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE r.id = 'bert-base-uncased' RETURN count(d)",
    },
    {
        "question": "Which files have conflicts in discussions on a specific repository?",
        "query": "MATCH (r:Repository)<-[c:HAS_CONFLICTING_FILE]-(d:Discussion) WHERE r.id = 'bert-base-uncased' RETURN c.filename, c.repo_file_id",
    },
    {
        "question": "Who opened discussions on a specific repository?",
        "query": "MATCH (r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(au:Author) WHERE r.id = 'bert-base-uncased' RETURN DISTINCT au.username",
    },
    {
        "question": "Which other repositories share tags with a specific repository?",
        "query": "MATCH (r1:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(r2:Repository) WHERE r1.id = 'bert-base-uncased' AND r1 <> r2 RETURN DISTINCT r2.id LIMIT 10",
    },
    {
        "question": "Which other repositories were created by the same author as a specific repository?",
        "query": "MATCH (r1:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(r2:Repository) WHERE r1.id = 'bert-base-uncased' AND r1 <> r2 RETURN DISTINCT r2.id",
    },
    {
        "question": "Which repositories have the most discussions?",
        "query": "MATCH (r:Repository)<-[:BELONGS_TO]-(d:Discussion) RETURN r.id, r.name, count(d) AS num_discussions ORDER BY num_discussions DESC LIMIT 10",
    },
    {
        "question": "What commits has the creator of a specific repository authored?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE r.id = 'bert-base-uncased' RETURN c LIMIT 10",
    },
    # ── Author ───────────────────────────────────────────────────────
    {
        "question": "What is the full name of a specific author, e.g 'google'?",
        "query": "MATCH (au:Author) WHERE au.username = 'google' RETURN au.username, au.fullname",
    },
    {
        "question": "Find authors whose username contains a specific keyword, e.g 'hugging'",
        "query": "MATCH (au:Author) WHERE au.username CONTAINS 'hugging' RETURN au.username, au.fullname LIMIT 10",
    },
    {
        "question": "Find authors whose full name contains a specific keyword, e.g 'Google'",
        "query": "MATCH (au:Author) WHERE au.fullname CONTAINS 'Google' RETURN au.username, au.fullname LIMIT 10",
    },
    {
        "question": "How many authors are there in total?",
        "query": "MATCH (au:Author) RETURN count(au)",
    },
    {
        "question": "What repositories were created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository) WHERE au.username = 'google' RETURN r.id, r.name",
    },
    {
        "question": "What models were created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(m:Model) WHERE au.username = 'google' RETURN m.model_id",
    },
    {
        "question": "What datasets were created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE au.username = 'allenai' RETURN ds.dataset_id",
    },
    {
        "question": "What Spaces were created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(s:Space) WHERE au.username = 'huggingface' RETURN s.space_id",
    },
    {
        "question": "How many models, datasets and Spaces has a specific author created?",
        "query": "MATCH (au:Author) WHERE au.username = 'google' OPTIONAL MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m:Model) OPTIONAL MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(ds:Dataset) OPTIONAL MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(s:Space) RETURN count(DISTINCT m) AS num_models, count(DISTINCT ds) AS num_datasets, count(DISTINCT s) AS num_spaces",
    },
    {
        "question": "What discussions were created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(d:Discussion) WHERE au.username = 'google' RETURN d LIMIT 10",
    },
    {
        "question": "How many discussions has a specific author created?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(d:Discussion) WHERE au.username = 'google' RETURN count(d)",
    },
    {
        "question": "What commits has a specific author authored?",
        "query": "MATCH (au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE au.username = 'google' RETURN c LIMIT 10",
    },
    {
        "question": "How many commits has a specific author authored?",
        "query": "MATCH (au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE au.username = 'google' RETURN count(c)",
    },
    {
        "question": "Which files has a specific author modified in their commits?",
        "query": "MATCH (au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE au.username = 'google' RETURN DISTINCT f",
    },
    {
        "question": "Which authors have created the most repositories?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "Which authors have created the most datasets?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(ds) AS num_datasets ORDER BY num_datasets DESC LIMIT 10",
    },
    {
        "question": "Which authors have created the most Spaces?",
        "query": "MATCH (s:Space)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which authors have authored the most commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN au.username, count(c) AS num_commits ORDER BY num_commits DESC LIMIT 10",
    },
    {
        "question": "Which authors have opened the most discussions?",
        "query": "MATCH (d:Discussion)-[:CREATED_BY]->(au:Author) RETURN au.username, count(d) AS num_discussions ORDER BY num_discussions DESC LIMIT 10",
    },
    {
        "question": "What tags appear on repositories created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE au.username = 'google' RETURN DISTINCT t.name",
    },
    {
        "question": "Which authors have created both models and datasets?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(:Model) MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(:Dataset) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which Spaces use models created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m:Model)<-[:USES_MODEL]-(s:Space) WHERE au.username = 'google' RETURN DISTINCT s.space_id",
    },
    {
        "question": "Which authors have models that are most used by Spaces?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Who opened discussions on repositories created by a specific author?",
        "query": "MATCH (au:Author)<-[:CREATED_BY]-(r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(opener:Author) WHERE au.username = 'google' RETURN DISTINCT opener.username",
    },
    # ── Tag ──────────────────────────────────────────────────────────
    {
        "question": "Does the tag 'pytorch' exist?",
        "query": "MATCH (t:Tag) WHERE t.name = 'pytorch' RETURN t.name",
    },
    {
        "question": "Find tags whose name contains a specific keyword, e.g 'text'",
        "query": "MATCH (t:Tag) WHERE t.name CONTAINS 'text' RETURN t.name LIMIT 10",
    },
    {
        "question": "How many tags are there in total?",
        "query": "MATCH (t:Tag) RETURN count(t)",
    },
    {
        "question": "Which repositories have the tag 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository) WHERE t.name = 'pytorch' RETURN r.id, r.name",
    },
    {
        "question": "Which models have the tag 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(m:Model) WHERE t.name = 'pytorch' RETURN m.model_id",
    },
    {
        "question": "Which datasets have the tag 'nli'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE t.name = 'nli' RETURN ds.dataset_id",
    },
    {
        "question": "Which Spaces have the tag 'text-to-image'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(s:Space) WHERE t.name = 'text-to-image' RETURN s.space_id",
    },
    {
        "question": "How many repositories have the tag 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository) WHERE t.name = 'pytorch' RETURN count(r)",
    },
    {
        "question": "How many models, datasets and Spaces have the tag 'pytorch'?",
        "query": "MATCH (t:Tag) WHERE t.name = 'pytorch' OPTIONAL MATCH (t)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(m:Model) OPTIONAL MATCH (t)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(ds:Dataset) OPTIONAL MATCH (t)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(s:Space) RETURN count(DISTINCT m) AS num_models, count(DISTINCT ds) AS num_datasets, count(DISTINCT s) AS num_spaces",
    },
    {
        "question": "What are the top 10 tags with the most repositories?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "What are the top 10 tags with the most datasets?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(ds) AS num_datasets ORDER BY num_datasets DESC LIMIT 10",
    },
    {
        "question": "What are the top 10 tags with the most Spaces?",
        "query": "MATCH (s:Space)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which authors have repositories tagged with 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)-[:CREATED_BY]->(au:Author) WHERE t.name = 'pytorch' RETURN DISTINCT au.username",
    },
    {
        "question": "Which authors use the tag 'pytorch' the most?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)-[:CREATED_BY]->(au:Author) WHERE t.name = 'pytorch' RETURN au.username, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "Which tags co-occur with the tag 'pytorch'?",
        "query": "MATCH (t1:Tag)<-[:HAS_TAG]-(r:Repository)-[:HAS_TAG]->(t2:Tag) WHERE t1.name = 'pytorch' AND t1 <> t2 RETURN t2.name, count(r) AS num_repos ORDER BY num_repos DESC LIMIT 10",
    },
    {
        "question": "Which repositories have both the tags 'pytorch' and 'text-classification'?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t1:Tag) MATCH (r)-[:HAS_TAG]->(t2:Tag) WHERE t1.name = 'pytorch' AND t2.name = 'text-classification' RETURN r.id, r.name",
    },
    {
        "question": "Which Spaces use models tagged with 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(m:Model)<-[:USES_MODEL]-(s:Space) WHERE t.name = 'pytorch' RETURN DISTINCT s.space_id",
    },
    {
        "question": "Which datasets tagged with 'nli' are used by Spaces?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(ds:Dataset)<-[:USES_DATASET]-(s:Space) WHERE t.name = 'nli' RETURN DISTINCT ds.dataset_id, s.space_id",
    },
    {
        "question": "What discussions belong to repositories tagged with 'pytorch'?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)<-[:BELONGS_TO]-(d:Discussion) WHERE t.name = 'pytorch' RETURN d LIMIT 10",
    },
    {
        "question": "Which models tagged with 'pytorch' are most used by Spaces?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(m:Model)<-[:USES_MODEL]-(s:Space) WHERE t.name = 'pytorch' RETURN m.model_id, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which tags are associated with the most distinct authors?",
        "query": "MATCH (t:Tag)<-[:HAS_TAG]-(r:Repository)-[:CREATED_BY]->(au:Author) RETURN t.name, count(DISTINCT au) AS num_authors ORDER BY num_authors DESC LIMIT 10",
    },
    {
        "question": "What tags does a specific repository have?",
        "query": "MATCH (r:Repository)-[:HAS_TAG]->(t:Tag) WHERE r.id = 'bert-base-uncased' RETURN t.name",
    },
    {
        "question": "Which tags appear on both a specific model and a specific dataset?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(ds:Dataset) WHERE m.model_id = 'bert-base-uncased' AND ds.dataset_id = 'squad' RETURN DISTINCT t.name",
    },
    # ── Discussion ───────────────────────────────────────────────────
    {
        "question": "How many discussions are there in total?",
        "query": "MATCH (d:Discussion) RETURN count(d)",
    },
    {
        "question": "What discussions belong to a specific repository?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository) WHERE r.id = 'bert-base-uncased' RETURN d",
    },
    {
        "question": "How many discussions belong to a specific repository?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository) WHERE r.id = 'bert-base-uncased' RETURN count(d)",
    },
    {
        "question": "What discussions exist for a specific model?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)<-[:IS_A]-(m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN d",
    },
    {
        "question": "What discussions exist for a specific dataset? e.g 'squad'?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)<-[:IS_A]-(ds:Dataset) WHERE ds.dataset_id = 'squad' RETURN d",
    },
    {
        "question": "What discussions exist for a specific Space?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)<-[:IS_A]-(s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN d",
    },
    {
        "question": "Who created the discussions on a specific repository?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository) MATCH (d)-[:CREATED_BY]->(au:Author) WHERE r.id = 'bert-base-uncased' RETURN DISTINCT au.username",
    },
    {
        "question": "What discussions were created by a specific author, e.g 'google'?",
        "query": "MATCH (d:Discussion)-[:CREATED_BY]->(au:Author) WHERE au.username = 'google' RETURN d LIMIT 10",
    },
    {
        "question": "How many discussions has a specific author created?",
        "query": "MATCH (d:Discussion)-[:CREATED_BY]->(au:Author) WHERE au.username = 'google' RETURN count(d)",
    },
    {
        "question": "Which files have conflicts in discussions on a specific repository?",
        "query": "MATCH (d:Discussion)-[c:HAS_CONFLICTING_FILE]->(r:Repository) WHERE r.id = 'bert-base-uncased' RETURN c.filename, c.repo_file_id",
    },
    {
        "question": "Which discussions have a conflicting file?",
        "query": "MATCH (d:Discussion)-[:HAS_CONFLICTING_FILE]->(:Repository) RETURN d LIMIT 10",
    },
    {
        "question": "How many discussions have a conflicting file?",
        "query": "MATCH (d:Discussion)-[:HAS_CONFLICTING_FILE]->(:Repository) RETURN count(DISTINCT d)",
    },
    {
        "question": "Which repositories have the most discussions?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository) RETURN r.id, r.name, count(d) AS num_discussions ORDER BY num_discussions DESC LIMIT 10",
    },
    {
        "question": "Which authors have created the most discussions?",
        "query": "MATCH (d:Discussion)-[:CREATED_BY]->(au:Author) RETURN au.username, count(d) AS num_discussions ORDER BY num_discussions DESC LIMIT 10",
    },
    {
        "question": "What are the most common conflicting filenames in discussions?",
        "query": "MATCH (d:Discussion)-[c:HAS_CONFLICTING_FILE]->(:Repository) RETURN c.filename, count(d) AS num_discussions ORDER BY num_discussions DESC LIMIT 10",
    },
    {
        "question": "Which repositories have discussions with conflicting files?",
        "query": "MATCH (d:Discussion)-[:HAS_CONFLICTING_FILE]->(r:Repository) RETURN DISTINCT r.id, r.name LIMIT 10",
    },
    {
        "question": "What discussions belong to repositories tagged with 'pytorch'?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE t.name = 'pytorch' RETURN d LIMIT 10",
    },
    {
        "question": "Which discussions were created by the same author who created the repository?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(d) RETURN d, r.id, au.username LIMIT 10",
    },
    {
        "question": "Which discussions were created by someone other than the repository creator?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(r:Repository)-[:CREATED_BY]->(owner:Author) MATCH (d)-[:CREATED_BY]->(opener:Author) WHERE owner <> opener RETURN d, r.id, opener.username LIMIT 10",
    },
    {
        "question": "Who opened discussions on repositories created by a specific author?",
        "query": "MATCH (owner:Author)<-[:CREATED_BY]-(r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(opener:Author) WHERE owner.username = 'google' RETURN DISTINCT opener.username",
    },
    {
        "question": "How many discussions belong to Models, Datasets and Spaces?",
        "query": "OPTIONAL MATCH (d1:Discussion)-[:BELONGS_TO]->(:Repository)<-[:IS_A]-(:Model) OPTIONAL MATCH (d2:Discussion)-[:BELONGS_TO]->(:Repository)<-[:IS_A]-(:Dataset) OPTIONAL MATCH (d3:Discussion)-[:BELONGS_TO]->(:Repository)<-[:IS_A]-(:Space) RETURN count(DISTINCT d1) AS model_discussions, count(DISTINCT d2) AS dataset_discussions, count(DISTINCT d3) AS space_discussions",
    },
    {
        "question": "What discussions belong to models created by a specific author?",
        "query": "MATCH (d:Discussion)-[:BELONGS_TO]->(:Repository)<-[:IS_A]-(m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author) WHERE au.username = 'google' RETURN d LIMIT 10",
    },
    {
        "question": "Which files have conflicts in discussions on a specific Space?",
        "query": "MATCH (d:Discussion)-[c:HAS_CONFLICTING_FILE]->(r:Repository)<-[:IS_A]-(s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN c.filename, c.repo_file_id",
    },
    {
        "question": "Who created discussions that have a conflicting file?",
        "query": "MATCH (d:Discussion)-[:HAS_CONFLICTING_FILE]->(:Repository) MATCH (d)-[:CREATED_BY]->(au:Author) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which files have conflicts in discussions on a specific model?",
        "query": "MATCH (d:Discussion)-[c:HAS_CONFLICTING_FILE]->(r:Repository)<-[:IS_A]-(m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN c.filename, c.repo_file_id",
    },
    # ── Commits ──────────────────────────────────────────────────────
    {
        "question": "How many commits are there in total?",
        "query": "MATCH (c:Commits) RETURN count(c)",
    },
    {
        "question": "What commits has a specific author authored, e.g 'google'?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE au.username = 'google' RETURN c LIMIT 10",
    },
    {
        "question": "How many commits has a specific author authored?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE au.username = 'google' RETURN count(c)",
    },
    {
        "question": "Which authors have authored the most commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN au.username, count(c) AS num_commits ORDER BY num_commits DESC LIMIT 10",
    },
    {
        "question": "Which files has a specific author modified in their commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) MATCH (c)-[:MODIFIES]->(f:ModifiedFile) WHERE au.username = 'google' RETURN DISTINCT f",
    },
    {
        "question": "How many files has a specific author modified in their commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) MATCH (c)-[:MODIFIES]->(f:ModifiedFile) WHERE au.username = 'google' RETURN count(DISTINCT f)",
    },
    {
        "question": "Which commits modify a file?",
        "query": "MATCH (c:Commits)-[:MODIFIES]->(f:ModifiedFile) RETURN c, f LIMIT 10",
    },
    {
        "question": "How many commits modify a file?",
        "query": "MATCH (c:Commits)-[:MODIFIES]->(:ModifiedFile) RETURN count(c)",
    },
    {
        "question": "How many commits have an author linked?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(:Author) RETURN count(c)",
    },
    {
        "question": "How many commits have no author linked?",
        "query": "MATCH (c:Commits) WHERE NOT (c)-[:AUTHORED_BY]->(:Author) RETURN count(c)",
    },
    {
        "question": "What commits has the creator of a specific model authored?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE m.model_id = 'bert-base-uncased' RETURN c LIMIT 10",
    },
    {
        "question": "What commits has the creator of a specific dataset authored?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE ds.dataset_id = 'squad' RETURN c LIMIT 10",
    },
    {
        "question": "What commits has the creator of a specific Space authored?",
        "query": "MATCH (s:Space)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN c LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific model modified in their commits?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    {
        "question": "Which authors have both authored commits and created repositories?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(r:Repository) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which authors have authored commits but have not created any repository?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE NOT (au)<-[:CREATED_BY]-(:Repository) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Who are the distinct authors of commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "What commits were authored by authors who have created Spaces?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(s:Space) RETURN c, au.username, s.space_id LIMIT 10",
    },
    {
        "question": "What commits were authored by the creator of a specific repository?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) WHERE r.id = 'bert-base-uncased' RETURN c LIMIT 10",
    },
    {
        "question": "Who authored the commits that modify files?",
        "query": "MATCH (c:Commits)-[:MODIFIES]->(:ModifiedFile) MATCH (c)-[:AUTHORED_BY]->(au:Author) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "List 10 commits",
        "query": "MATCH (c:Commits) RETURN c LIMIT 10",
    },
    {
        "question": "Which authors have both authored commits and created discussions?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(d:Discussion) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "How many distinct authors have authored commits?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN count(DISTINCT au)",
    },
    {
        "question": "What commits has the creator of a specific dataset authored, and which files did they modify?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE ds.dataset_id = 'squad' RETURN c, f LIMIT 10",
    },
    {
        "question": "What commits were authored by authors whose repositories have the tag 'pytorch'?",
        "query": "MATCH (c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE t.name = 'pytorch' RETURN c, au.username LIMIT 10",
    },
    # ── ModifiedFile ─────────────────────────────────────────────────
    {
        "question": "How many modified files are there in total?",
        "query": "MATCH (f:ModifiedFile) RETURN count(f)",
    },
    {
        "question": "Which files has a specific author modified, e.g 'google'?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE au.username = 'google' RETURN DISTINCT f",
    },
    {
        "question": "How many files has a specific author modified?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE au.username = 'google' RETURN count(DISTINCT f)",
    },
    {
        "question": "Who modified files in their commits?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific model modified?",
        "query": "MATCH (m:Model)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    {
        "question": "Which files has the creator of a specific dataset modified?",
        "query": "MATCH (ds:Dataset)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE ds.dataset_id = 'squad' RETURN DISTINCT f",
    },
    {
        "question": "Which files has the creator of a specific Space modified?",
        "query": "MATCH (s:Space)-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN DISTINCT f",
    },
    {
        "question": "Which authors have modified the most files?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN au.username, count(DISTINCT f) AS num_files ORDER BY num_files DESC LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific repository modified?",
        "query": "MATCH (r:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE r.id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    {
        "question": "Which authors have both created a repository and modified files?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(r:Repository) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which files were modified by authors who have created discussions?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(d:Discussion) RETURN DISTINCT f LIMIT 10",
    },
    {
        "question": "Which files were modified by the creator of a specific model?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m:Model) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    {
        "question": "How many files were modified by authors who have created Spaces?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(s:Space) RETURN count(DISTINCT f)",
    },
    {
        "question": "How many distinct authors have modified at least one file?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) RETURN count(DISTINCT au)",
    },
    {
        "question": "Which files were modified by authors who have created datasets?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(ds:Dataset) RETURN DISTINCT f LIMIT 10",
    },
    {
        "question": "Which files were modified by authors whose repositories have the tag 'pytorch'?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(r:Repository)-[:HAS_TAG]->(t:Tag) WHERE t.name = 'pytorch' RETURN DISTINCT f LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific Space modified in their commits?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(s:Space) WHERE s.space_id = 'huggingface/diffusers-demo' RETURN DISTINCT f",
    },
    {
        "question": "Which commits modify files?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits) RETURN c, f LIMIT 10",
    },
    {
        "question": "How many commits modify files?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits) RETURN count(c)",
    },
    {
        "question": "Which files were modified by authors who have created both models and datasets?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(:Commits)-[:AUTHORED_BY]->(au:Author) MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(:Model) MATCH (au)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(:Dataset) RETURN DISTINCT f LIMIT 10",
    },
    {
        "question": "Which authors have modified files but have not created any repository?",
        "query": "MATCH (f:ModifiedFile)<-[:MODIFIES]-(c:Commits)-[:AUTHORED_BY]->(au:Author) WHERE NOT (au)<-[:CREATED_BY]-(:Repository) RETURN DISTINCT au.username LIMIT 10",
    },
    {
        "question": "Which files were modified by authors who opened discussions on a specific model?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) WHERE m.model_id = 'bert-base-uncased' RETURN DISTINCT f",
    },
    {
        "question": "List 10 modified files",
        "query": "MATCH (f:ModifiedFile) RETURN f LIMIT 10",
    },
    {
        "question": "Which files were modified by a specific author, and how many commits did they author?",
        "query": "MATCH (au:Author) WHERE au.username = 'google' OPTIONAL MATCH (au)<-[:AUTHORED_BY]-(c:Commits) OPTIONAL MATCH (c)-[:MODIFIES]->(f:ModifiedFile) RETURN count(DISTINCT c) AS num_commits, count(DISTINCT f) AS num_files",
    },
]
