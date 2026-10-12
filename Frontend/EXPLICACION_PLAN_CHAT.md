# El chat del GraphRAG, explicado sin tecnicismos

Este archivo traduce el plan de [PLAN_chat_frontend.md](PLAN_chat_frontend.md). Ese plan está escrito para quien va a programar. Este es para entender **qué se construyó, por qué, y qué hace cada pieza**.

El chat **ya está implementado**. Vive en la carpeta `Frontend/`. El cerebro (el grafo, Neo4j, Azure) sigue en `Pipeline_RAG/`.

---

## 1. El problema que resolvía el plan

Antes del chat, el sistema solo se usaba desde un notebook de Jupyter: escribías una pregunta en una celda, corrías el código y leías la respuesta.

Eso tenía tres límites:

1. **No se veía como un chat.** No había pantalla con burbujas, ni barra de conversaciones.
2. **Cada pregunta empezaba de cero** si no usabas un truco de “sesión” en el notebook. No podías decir “explícame el primero” y esperar que el sistema recordara la lista anterior.
3. **Al cerrar el notebook se olvidaba todo.** La memoria vivía solo en la RAM del proceso.

El plan no era reinventar el GraphRAG. Era **ponerle una cara** tipo Claude o ChatGPT: varias conversaciones, historial, y que al reiniciar el servidor los chats sigan ahí.

---

## 2. La idea central, en una frase

El front **no responde** las preguntas. Solo muestra la conversación y le pide la respuesta al grafo que ya existía.

Piensa en un restaurante:

- Tú (el navegador) hablas con el mesero.
- El mesero (`Frontend/`) anota la mesa, el pedido y te trae el plato.
- La cocina (`Pipeline_RAG/` + Neo4j + Azure) es la que cocina.

Si cambias de mesa (otra sesión), la cocina no mezcla los platos.

---

## 3. Qué ves en la pantalla

Una sola página, en español, sin instalar Node ni “compilar” el front.

**Barra izquierda (sesiones)**

- Botón **Nuevo chat**: abre una conversación vacía.
- Lista de chats. El activo se ve resaltado.
- Doble clic en el título para renombrarlo.
- La **×** borra el chat (pide confirmación).
- Borrar un chat borra también su memoria.

**Centro (el hilo)**

- Si el chat está vacío: un texto corto y 2 o 3 preguntas de ejemplo. Al hacer clic, se copian al cuadro de abajo.
- Tus mensajes van a la derecha.
- Las respuestas van a la izquierda, con formato (negritas, listas, código).
- Debajo de la última respuesta del asistente puede aparecer una etiqueta: *Conversación*, *Consulta al grafo* o *Búsqueda vectorial*. Eso dice **por qué camino** pasó esa pregunta (ver sección 7).

**Abajo (el cuadro para escribir)**

- Enter envía. Shift+Enter hace un salto de línea.
- Mientras el grafo trabaja, el cuadro se bloquea y aparece “Consultando el grafo…” / “Consulta en curso…”.
- Si cambias de chat mientras una respuesta sigue en camino, al volver se recargan los mensajes de ese chat.

**La dirección del navegador**

Al abrir un chat, la URL queda algo como `http://127.0.0.1:8000/#un-codigo-largo`. Ese código es el identificador de la sesión. Si recargas la página, vuelves al mismo chat.

---

## 4. Cómo viaja una pregunta (el flujo)

```text
Tú escribes
    → la página (Frontend/web)
    → el servidor (Frontend/api)
    → el grafo (Pipeline_RAG)
    → Neo4j y/o Azure
    → el servidor guarda la respuesta
    → la página muestra la burbuja
```

Paso a paso, cuando das Enter:

1. El navegador manda el texto al servidor: “esta sesión, este mensaje”.
2. El servidor busca esa sesión en la lista de chats. Si no existe, dice que no la encontró.
3. Si el título todavía es “Nuevo chat”, lo cambia por las primeras palabras de tu pregunta (máximo unos 60 caracteres).
4. El servidor le pasa **solo la pregunta** al grafo. No le reenvía los hallazgos viejos: esos ya están guardados de turnos anteriores. Si los pisara con vacío, un “explícame el primero” no sabría de qué lista hablas.
5. El grafo decide la ruta (sección 7), busca o conversa, y escribe una respuesta en prosa.
6. El servidor devuelve el texto y la ruta. La página pinta la burbuja.

La página se abre **sin esperar a Neo4j**. La primera pregunta es la que conecta con la base y con Azure. Si eso falla, el error sale **en el chat**, no como una página en blanco.

---

## 5. Qué es una “sesión” y por qué hay dos archivos

Una sesión es **un chat**: su título en la barra y todo lo que se habló ahí.

Hace falta **guardar dos cosas distintas**, y por eso hay dos archivos (ambos en `Frontend/chat_data/`, y no se suben a Git):

| Archivo | Qué guarda | Para qué sirve |
|---|---|---|
| `sessions.sqlite` | id, título, fechas | La barra izquierda: nombre, orden, crear/borrar/renombrar |
| `checkpoints.sqlite` | historial, hallazgos del grafo, última ruta | Que el grafo recuerde “el primero”, los documentos y los mensajes |

**Por qué no un solo archivo.** El “cuaderno de la cocina” (el checkpointer del grafo) guarda el estado interno del flujo. No guarda un título lindo ni sabe ordenar “el chat que toqué hace un rato”. Eso lo lleva una lista aparte.

**El id es el mismo en los dos.** Es un código único (un UUID). En el grafo se llama `thread_id`. Es el número de mesa: título y memoria apuntan a la misma mesa.

**Al borrar un chat** se borra la fila de la lista **y** la memoria de esa mesa.

Si alguna vez usaste el chat cuando todavía vivía dentro de `Pipeline_RAG/chat_data`, el primer arranque copia esos archivos a `Frontend/chat_data`.

---

## 6. Dos memorias distintas (esto importa para el TG)

El grafo se puede “encender” de dos maneras. Es el **mismo flujo** (mismos pasos, mismas reglas). Cambia **dónde se anota** lo hablado.

| Quién lo usa | Dónde vive la memoria | Qué pasa al cerrar |
|---|---|---|
| Notebook (`00_run_script.ipynb`) | Solo en la RAM (`MemorySaver`) | Se olvida |
| Chat web | En disco (`SqliteSaver`, el archivo de checkpoints) | Sigue ahí |

Por eso el plan pide una función `build_app(...)`:

- El notebook la llama **sin** argumento → memoria temporal, como antes.
- El chat le pasa el almacén en disco → las sesiones sobreviven.

No se tocó el router, los prompts, los embeddings ni las consultas Cypher. El chat no inventa otra forma de preguntarle a Neo4j.

---

## 7. Las tres rutas de una pregunta

El grafo ya sabía elegir camino. El chat **muestra** esa elección.

| Ruta | En la pantalla | Qué significa | Ejemplo |
|---|---|---|---|
| `vector search` | Búsqueda vectorial | Busca por parecido de significado (descripciones, temas) y luego consulta el grafo | “modelos relacionados con clasificación de texto” |
| `graph query` | Consulta al grafo | Pregunta estructural: conteos, filtros, un autor concreto, un id | “¿cuántos downloads tiene X?” |
| `chat` | Conversación | Habla de lo **ya encontrado**, sin volver a Neo4j | “explícame el primero”, “compáralos” |

Reglas que importan:

- En un chat **nuevo** (sin hallazgos) nunca debería ir a *Conversación*. No hay “el primero”.
- “Eso” o “el primero” **no** implican *Conversación* por sí solos. Si pides un dato que no está (likes, otro autor), vuelve al grafo. Antes, un paso reescribe “el primero” como un id real.

La etiqueta de la ruta solo se puede reconstruir con certeza en **el último** mensaje del asistente. El estado del grafo guarda la ruta del último turno, no de todos los anteriores.

---

## 8. Qué hace cada archivo (mapa de `Frontend/`)

```text
Frontend/
  run_chat.py              ← lo que tú corres para abrir el chat
  api/
    server.py              ← el mesero: recibe pedidos de la página
    sessions_store.py      ← la lista de chats (títulos y fechas)
  web/
    index.html             ← el esqueleto de la página
    styles.css             ← colores, columnas, burbujas
    app.js                 ← clics, envío, recarga, hash de la URL
    vendor/marked.min.js   ← convierte markdown de la respuesta a HTML
  chat_data/               ← se crea al usar el chat; no se sube a Git
    sessions.sqlite
    checkpoints.sqlite
  PLAN_chat_frontend.md    ← el plan original (técnico)
  EXPLICACION_PLAN_CHAT.md ← este archivo
```

**`run_chat.py`**  
Enciende el servidor en el puerto 8000 y escucha en `127.0.0.1` y en `localhost` (en Windows a veces `localhost` entra por IPv6 y si no hay nadie ahí el navegador parece “no abrir”).

**`api/server.py`**  
Las “puertas” que usa la página:

- Ver la lista de chats
- Crear un chat vacío (aún no llama al grafo)
- Renombrar
- Borrar
- Leer los mensajes de un chat
- Enviar un mensaje y esperar la respuesta

Mientras responde, **un solo pedido a la vez** (un candado). Este chat es para una persona, y Azure/Neo4j no se pisan.

**`api/sessions_store.py`**  
Crea, lista, renombra y borra filas de `sessions.sqlite`. También recorta el título.

**`web/`**  
Solo HTML, CSS y JavaScript. FastAPI los sirve: abres el navegador y ya. No hay proyecto de React ni `npm`.

**Fuera de `Frontend/`, se tocó poco**

- `Pipeline_RAG/Graph/graph.py`: la función `build_app` para elegir memoria temporal o en disco.
- `requirements.txt`: tres librerías nuevas (`fastapi`, `uvicorn`, `langgraph-checkpoint-sqlite`).
- `.gitignore`: para no subir `Frontend/chat_data/`.

---

## 9. Qué no entra (a propósito)

El plan recorta para el TG. **No** hay:

- Login ni varios usuarios (cualquiera que abra esa computadora ve los mismos chats)
- Respuesta palabra por palabra mientras se genera (esperas el texto completo)
- Subir archivos
- Regenerar o editar un mensaje ya enviado
- Deshacer si el grafo falla a mitad de camino

Sobre ese último punto: el primer paso del grafo anota tu pregunta. Si después falla Neo4j o Azure, la pregunta puede quedar guardada **sin** respuesta. En esta fase no se “rebobina” el cuaderno.

---

## 10. Cómo se relaciona con el plan de memoria del pipeline

Hay otro plan en `Pipeline_RAG/PLAN_conversacion_memoria.md`. Ese es el **cerebro conversacional**:

- recordar hallazgos entre turnos
- ruta `chat` sin volver a Neo4j
- reescribir “el primero” como un id

El plan de frontend **asume que eso ya existe** y solo lo envuelve:

- cada chat = un `thread_id`
- guardarlo en disco
- pintarlo en el navegador

Sin esa memoria, el chat sería solo una caja que manda preguntas sueltas.

---

## 11. Cómo probarlo (resumen)

1. Activa el entorno: en la raíz del repo, `.\.venv\Scripts\Activate.ps1`
2. Si nunca instalaste las librerías nuevas: `pip install -r requirements.txt`
3. `cd Frontend` y `python run_chat.py`
4. Abre **http://127.0.0.1:8000** (si el 8000 está bloqueado en Windows, cambia el puerto en `run_chat.py` y abre ese)
5. Neo4j encendido y el `.env` en la raíz. Si falta, la página abre igual; el error sale al mandar la primera pregunta

Prueba corta:

1. Nuevo chat → una pregunta que busque modelos → debe ir a búsqueda o consulta al grafo.
2. En el **mismo** chat: “explícame el primero” → etiqueta *Conversación*, no vuelve a Neo4j.
3. Otro chat nuevo → “explícame el primero” → **no** debería ir a *Conversación* (no hay lista previa).
4. Cierra el servidor, ábrelo otra vez → los chats siguen en la barra.

---

## 12. Glosario (las palabras del plan original)

| Palabra del plan | En cristiano |
|---|---|
| Front / frontend | Lo que ves: página y servidor del chat |
| Pipeline / grafo | El sistema que ya respondía preguntas sobre Hugging Face en Neo4j |
| Sesión / `thread_id` | Un chat. Un número de mesa. |
| Checkpointer / `MemorySaver` / `SqliteSaver` | Dónde se anota lo hablado: RAM o archivo |
| Checkpoint | La foto del estado de un chat (mensajes, hallazgos, ruta) |
| API / endpoint | Una puerta del servidor: “dame los chats”, “manda este mensaje” |
| `invoke` | “Corre el grafo con esta pregunta” |
| `documents` | Los hallazgos crudos del último retrieval (la lista de modelos, etc.) |
| Ruta / `route` | El camino elegido: conversar, consultar el grafo o buscar por similitud |
| Hash (`#...`) | El pedazo de la URL que identifica el chat abierto |
| Worker | Una copia del servidor. Aquí hay una sola. |
| Markdown | Texto con `**negritas**` y listas que la página convierte en formato |
| CDN | Internet de terceros. `marked` está guardado en el proyecto para no depender de eso |
| Rollback | Deshacer un turno a medias. Aquí no se hace. |
