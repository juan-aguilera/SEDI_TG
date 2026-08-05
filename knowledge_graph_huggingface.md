# Knowledge Graph — `hugging-face-db`

Documentación del grafo de conocimiento construido sobre datos de Hugging Face.
Este documento describe los **nodos** (labels), las **relaciones** (tipos de arista) y las **propiedades** confirmadas mediante inspección del esquema en Neo4j.

> **Alcance de este documento.** Solo se documenta lo confirmado a partir de las consultas de esquema ejecutadas (`db.labels()`, `db.schema.relTypeProperties()` y conteos de nodos/relaciones), más la nueva propiedad `embeddings`. No se infieren propiedades de negocio de los nodos (p. ej. `likes`, `downloads`, `id`) que no aparecen en el esquema inspeccionado. Cuando el modelo evolucione, esta es la fuente que debe actualizarse.

---

## 1. Vista general

El grafo modela el ecosistema de Hugging Face en torno a un nodo central, **Repository**, del cual **Model**, **Dataset** y **Space** son especializaciones (`IS_A`). Alrededor giran los autores, las etiquetas, las discusiones (pull requests / issues) y el historial de commits con los archivos que modifican.

```
                 (Space)
                /   |   \
       USES_MODEL  IS_A  USES_DATASET
              /     |      \
        (Model)  (Repository) (Dataset)
           \        |  \        /
           IS_A     |   IS_A  IS_A
              \     |   /
               (Repository) ──HAS_TAG──▶ (Tag)
                 ▲   |   \
        BELONGS_TO   |    CREATED_BY
     HAS_CONFLICTING_FILE \        \
              |             ▼        ▼
        (Discussion)──CREATED_BY──▶(Author)◀──AUTHORED_BY──(Commits)──MODIFIES──▶(ModifiedFile)
```

---

## 2. Nodos (labels)

Conteos obtenidos con `CALL db.labels()` + `MATCH (n) WHERE label IN labels(n) RETURN count(n)`.

| Label | Nodos | Descripción | ¿`embeddings`? |
|---|---:|---|:---:|
| **Repository** | 1 173 897 | Nodo central. Repositorio genérico; superclase de Model, Dataset y Space. | ✅ |
| **Model** | 708 377 | Modelo publicado en el Hub. Es un `Repository` (`IS_A`). | ✅ |
| **Dataset** | 207 610 | Conjunto de datos publicado en el Hub. Es un `Repository` (`IS_A`). | ✅ |
| **Space** | 258 445 | Aplicación/demo del Hub. Es un `Repository` (`IS_A`). | ✅ |
| **Author** | 511 520 | Usuario u organización que crea repositorios, discusiones y commits. | ✅ |
| **Tag** | 77 180 | Etiqueta de clasificación asociada a repositorios. | ✅ |
| **Discussion** | 312 844 | Discusión, issue o pull request asociado a un repositorio. | — |
| **Commits** | 8 615 347 | Commit del historial de un repositorio. **Es el label con datos.** | — |
| **ModifiedFile** | 569 338 | Archivo modificado por uno o más commits. | — |
| **Commit** | 0 | Label vacío (sin instancias). El historial vive en `Commits`. | — |

**Nota sobre `Commit` vs `Commits`.** El label `Commit` (singular) existe en el esquema pero tiene **0 nodos**; todos los commits reales están bajo el label `Commits` (plural). Conviene tenerlo presente al escribir Cypher: consultar `(:Commit)` no devuelve resultados.

---

## 3. La nueva propiedad `embeddings`

Se ha añadido una propiedad `embeddings` (vector de representación para búsqueda semántica) a los siguientes labels:

- **Repository** y sus subtipos **Model**, **Dataset** y **Space**
- **Author**
- **Tag**

No llevan `embeddings`: **Discussion**, **Commits**, **ModifiedFile** ni el label vacío **Commit**.

Esta propiedad es la que habilita la ruta de *vector search* del router (frente a la ruta de *graph query*): las consultas semánticas se resuelven contra el índice vectorial construido sobre `embeddings` en estos labels, mientras que las consultas estructurales se traducen a Cypher sobre las relaciones descritas abajo.

---

## 4. Relaciones (tipos de arista)

Conteos obtenidos con `MATCH ()-[r]->() RETURN DISTINCT type(r), count(r)`.
Propiedades obtenidas con `CALL db.schema.relTypeProperties()`.

| Relación | Dirección (origen → destino) | Aristas | Propiedades |
|---|---|---:|---|
| **IS_A** | (Model \| Dataset \| Space) → Repository | 1 173 868 | — |
| **CREATED_BY** | (Repository \| Discussion) → Author | 911 960 | — |
| **BELONGS_TO** | Discussion → Repository | 625 668 | — |
| **HAS_CONFLICTING_FILE** | Discussion → Repository | 148 192 | `filename` · `repo_file_id` |
| **AUTHORED_BY** | Commits → Author | 7 183 936 | — |
| **MODIFIES** | Commits → ModifiedFile | 569 338 | — |
| **USES_MODEL** | Space → Model | 184 987 | — |
| **USES_DATASET** | Space → Dataset | 3 392 | — |
| **HAS_TAG** | Repository → Tag | 5 627 006 | — |

### Propiedades de relación confirmadas

Solo un tipo de relación tiene propiedades en el esquema:

**`HAS_CONFLICTING_FILE`**

| Propiedad | Tipo | Obligatoria |
|---|---|:---:|
| `filename` | `STRING NOT NULL` | ✅ |
| `repo_file_id` | `STRING NOT NULL` | ✅ |

El resto de tipos (`IS_A`, `CREATED_BY`, `BELONGS_TO`, `USES_MODEL`, `USES_DATASET`, `HAS_TAG`, `MODIFIES`, `AUTHORED_BY`) no declaran propiedades (`propertyName = null`, `mandatory = false`).

---

## 5. Relaciones por nodo

Resumen de cómo participa cada label en el grafo.

**Repository** (central)
- Recibe `IS_A` desde Model, Dataset y Space.
- `CREATED_BY` → Author.
- `HAS_TAG` → Tag.
- Recibe `BELONGS_TO` y `HAS_CONFLICTING_FILE` desde Discussion.

**Model** (`IS_A` → Repository)
- `IS_A` → Repository.
- Recibe `USES_MODEL` desde Space.
- Hereda las relaciones de Repository.

**Dataset** (`IS_A` → Repository)
- `IS_A` → Repository.
- Recibe `USES_DATASET` desde Space.
- Hereda las relaciones de Repository.

**Space** (`IS_A` → Repository)
- `IS_A` → Repository.
- `USES_MODEL` → Model.
- `USES_DATASET` → Dataset.
- Hereda las relaciones de Repository.

**Author**
- Recibe `CREATED_BY` desde Repository y Discussion.
- Recibe `AUTHORED_BY` desde Commits.

**Tag**
- Recibe `HAS_TAG` desde Repository.

**Discussion**
- `CREATED_BY` → Author.
- `BELONGS_TO` → Repository.
- `HAS_CONFLICTING_FILE` → Repository (con `filename` y `repo_file_id`).

**Commits**
- `AUTHORED_BY` → Author.
- `MODIFIES` → ModifiedFile.

**ModifiedFile**
- Recibe `MODIFIES` desde Commits.

---

## 6. Notas de consistencia

Los conteos son coherentes con la estructura del grafo:

- `IS_A` (1 173 868) ≈ Model + Dataset + Space (708 377 + 207 610 + 258 445 = 1 174 432). Confirma que los tres subtipos apuntan a Repository.
- `MODIFIES` (569 338) = ModifiedFile (569 338). Cada archivo modificado tiene su arista `MODIFIES`.
- `AUTHORED_BY` (7 183 936) < Commits (8 615 347): no todos los commits tienen autor enlazado.
- `HAS_TAG` (5 627 006) sobre 77 180 tags distintos: relación de muchos-a-muchos (un repositorio tiene varias etiquetas y una etiqueta clasifica muchos repositorios).

---

*Documento de referencia del esquema. Actualizar cuando cambien labels, relaciones, propiedades o el alcance de `embeddings`.*
