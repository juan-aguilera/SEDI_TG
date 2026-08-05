examples = [
    {
        "question": "What is the pipeline tag of a specific model, e.g bert-base-uncased?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'}) RETURN m.model_id, m.pipeline_tag",
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
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN t.name",
    },
    {
        "question": "How many tags does a specific model have?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN count(t)",
    },
    {
        "question": "Which models have the tag 'pytorch'?",
        "query": "MATCH (t:Tag {name: 'pytorch'})<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(m:Model) RETURN m.model_id",
    },
    {
        "question": "How many models are tagged with 'pytorch'?",
        "query": "MATCH (t:Tag {name: 'pytorch'})<-[:HAS_TAG]-(r:Repository)<-[:IS_A]-(m:Model) RETURN count(m)",
    },
    {
        "question": "Which models have both the tag 'pytorch' and the pipeline tag 'text-classification'?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag {name: 'pytorch'}) WHERE m.pipeline_tag = 'text-classification' RETURN m.model_id",
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
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username",
    },
    {
        "question": "What is the full name of the author who created a specific model?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.fullname",
    },
    {
        "question": "What models were created by a specific author, e.g 'google'?",
        "query": "MATCH (au:Author {username: 'google'})<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(m:Model) RETURN m.model_id",
    },
    {
        "question": "How many models has a specific author created?",
        "query": "MATCH (au:Author {username: 'google'})<-[:CREATED_BY]-(r:Repository)<-[:IS_A]-(m:Model) RETURN count(m)",
    },
    {
        "question": "Which authors have created the most models?",
        "query": "MATCH (m:Model)-[:IS_A]->(r:Repository)-[:CREATED_BY]->(au:Author) RETURN au.username, count(m) AS num_models ORDER BY num_models DESC LIMIT 10",
    },
    {
        "question": "What is the repository name and id of a specific model?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository) RETURN r.name, r.id",
    },
    {
        "question": "Which other models share tags with a specific model?",
        "query": "MATCH (m1:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(:Repository)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(:Repository)<-[:IS_A]-(m2:Model) WHERE m1 <> m2 RETURN DISTINCT m2.model_id LIMIT 10",
    },
    {
        "question": "Which other models were created by the same author as a specific model?",
        "query": "MATCH (m1:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:CREATED_BY]-(:Repository)<-[:IS_A]-(m2:Model) WHERE m1 <> m2 RETURN DISTINCT m2.model_id",
    },
    {
        "question": "Which Spaces use a specific model?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model {model_id: 'bert-base-uncased'}) RETURN s.space_id",
    },
    {
        "question": "How many Spaces use a specific model?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model {model_id: 'bert-base-uncased'}) RETURN count(s)",
    },
    {
        "question": "What are the most used models by Spaces?",
        "query": "MATCH (s:Space)-[:USES_MODEL]->(m:Model) RETURN m.model_id, count(s) AS num_spaces ORDER BY num_spaces DESC LIMIT 10",
    },
    {
        "question": "Which models are used by Spaces built with the 'gradio' SDK?",
        "query": "MATCH (s:Space {sdk: 'gradio'})-[:USES_MODEL]->(m:Model) RETURN DISTINCT m.model_id",
    },
    {
        "question": "List the models used by a specific Space along with their tags",
        "query": "MATCH (s:Space {space_id: 'huggingface/diffusers-demo'})-[:USES_MODEL]->(m:Model)-[:IS_A]->(r:Repository)-[:HAS_TAG]->(t:Tag) RETURN m.model_id, collect(t.name) AS tags",
    },
    {
        "question": "What discussions exist for a specific model?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) RETURN d",
    },
    {
        "question": "How many discussions does a specific model have?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion) RETURN count(d)",
    },
    {
        "question": "Who opened discussions on a specific model?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)<-[:BELONGS_TO]-(d:Discussion)-[:CREATED_BY]->(au:Author) RETURN DISTINCT au.username",
    },
    {
        "question": "Which files have conflicts in discussions on a specific model?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(r:Repository)<-[c:HAS_CONFLICTING_FILE]-(d:Discussion) RETURN c.filename, c.repo_file_id",
    },
    {
        "question": "What commits has the creator of a specific model authored?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits) RETURN c LIMIT 10",
    },
    {
        "question": "Which files has the creator of a specific model modified in their commits?",
        "query": "MATCH (m:Model {model_id: 'bert-base-uncased'})-[:IS_A]->(:Repository)-[:CREATED_BY]->(au:Author)<-[:AUTHORED_BY]-(c:Commits)-[:MODIFIES]->(f:ModifiedFile) RETURN DISTINCT f",
    },
]
