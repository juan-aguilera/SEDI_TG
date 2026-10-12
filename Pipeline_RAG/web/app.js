const EXAMPLES = [
  "Encuentra los 5 modelos más relacionados con clasificación de texto",
  "¿Qué modelos creó Google?",
  "¿Cuántos datasets hay sobre question answering?",
];

const ROUTE_LABELS = {
  chat: "Conversación",
  "graph query": "Consulta al grafo",
  "vector search": "Búsqueda vectorial",
};

const state = {
  sessions: [],
  currentId: null,
  inflight: null,
};

const els = {
  app: document.querySelector("#app"),
  list: document.querySelector("#session-list"),
  messages: document.querySelector("#messages"),
  title: document.querySelector("#chat-title"),
  form: document.querySelector("#composer"),
  input: document.querySelector("#input"),
  send: document.querySelector("#send"),
  newChat: document.querySelector("#new-chat"),
  menu: document.querySelector("#menu-toggle"),
  backdrop: document.querySelector("#backdrop"),
};

let suppressHash = false;

els.newChat.addEventListener("click", () => {
  createSession();
});

els.menu.addEventListener("click", () => {
  els.app.classList.toggle("sidebar-open");
});

els.backdrop.addEventListener("click", () => {
  els.app.classList.remove("sidebar-open");
});

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  send(els.input.value);
});

els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    els.form.requestSubmit();
  }
});

els.input.addEventListener("input", resizeInput);

window.addEventListener("hashchange", () => {
  if (suppressHash) {
    suppressHash = false;
    return;
  }
  openFromHash(false);
});

refreshSessions()
  .then(() => openFromHash(true))
  .catch((error) => {
    els.messages.replaceChildren(errorNote(error.message || "No se pudo cargar el chat"));
  });

async function refreshSessions() {
  const response = await fetch("/api/sessions");
  if (!response.ok) throw new Error(await readError(response));
  state.sessions = await response.json();
  renderSessions();
}

function markActive() {
  for (const item of els.list.querySelectorAll(".session")) {
    item.classList.toggle("active", item.dataset.id === state.currentId);
  }
}

function renderSessions() {
  els.list.replaceChildren();
  for (const session of state.sessions) {
    const item = document.createElement("li");
    item.className = "session" + (session.id === state.currentId ? " active" : "");
    item.dataset.id = session.id;

    const name = document.createElement("button");
    name.type = "button";
    name.className = "session-name";
    name.textContent = session.title;
    name.title = "Doble clic para renombrar";
    name.addEventListener("click", (event) => {
      if (event.detail > 1) return;
      openSession(session.id);
      els.app.classList.remove("sidebar-open");
    });
    name.addEventListener("dblclick", (event) => {
      event.preventDefault();
      startRename(item, session);
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "session-delete";
    remove.setAttribute("aria-label", "Borrar chat");
    remove.textContent = "×";
    const busyHere = state.inflight && state.inflight.sessionId === session.id;
    remove.disabled = Boolean(busyHere);
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      removeSession(session.id);
    });

    item.append(name, remove);
    els.list.append(item);
  }
}

function startRename(item, session) {
  const name = item.querySelector(".session-name");
  const input = document.createElement("input");
  input.className = "session-rename";
  input.value = session.title;
  input.setAttribute("aria-label", "Nuevo título");
  name.replaceWith(input);
  input.focus();
  input.select();

  let done = false;
  const finish = async (save) => {
    if (done) return;
    done = true;
    const next = input.value.trim();
    if (save && next && next !== session.title) {
      await renameSession(session.id, next);
      return;
    }
    renderSessions();
  };
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      finish(true);
    } else if (event.key === "Escape") {
      event.preventDefault();
      finish(false);
    }
  });
  input.addEventListener("blur", () => finish(true));
}

async function createSession() {
  if (state.inflight) return;
  const current = state.sessions.find((session) => session.id === state.currentId);
  const emptyVisible = !els.messages.querySelector(".bubble");
  if (current && current.title === "Nuevo chat" && emptyVisible) {
    els.input.focus();
    return;
  }
  const response = await fetch("/api/sessions", { method: "POST" });
  if (!response.ok) {
    showError(await readError(response));
    return;
  }
  const session = await response.json();
  await refreshSessions();
  await openSession(session.id);
  els.input.focus();
}

async function openSession(id, options = {}) {
  state.currentId = id;
  setHash(id, Boolean(options.replaceHash));
  markActive();
  const session = state.sessions.find((item) => item.id === id);
  els.title.textContent = session ? session.title : "Chat";
  await loadMessages(id);
  syncComposer();
}

async function openFromHash(initial) {
  const id = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  const known = id && state.sessions.some((session) => session.id === id);
  if (known) {
    await openSession(id, { replaceHash: true });
    return;
  }
  if (initial && state.sessions.length) {
    await openSession(state.sessions[0].id, { replaceHash: true });
    return;
  }
  if (id) history.replaceState(null, "", location.pathname + location.search);
  state.currentId = null;
  els.title.textContent = "GraphRAG";
  renderSessions();
  renderThread([]);
  syncComposer();
}

function setHash(id, replace) {
  const next = "#" + id;
  if (location.hash === next) return;
  if (replace) {
    history.replaceState(null, "", next);
    return;
  }
  suppressHash = true;
  location.hash = id;
}

async function loadMessages(id) {
  const response = await fetch("/api/sessions/" + encodeURIComponent(id) + "/messages");
  if (response.status === 404) {
    await refreshSessions();
    await openFromHash(true);
    return;
  }
  if (!response.ok) throw new Error(await readError(response));
  if (state.currentId !== id) return;
  renderThread(await response.json());
}

function renderThread(messages) {
  els.messages.replaceChildren();
  const pendingHere = state.inflight && state.inflight.sessionId === state.currentId;
  if (!messages.length && !pendingHere) {
    els.messages.append(emptyState());
    return;
  }
  for (const message of messages) {
    els.messages.append(bubble(message));
  }
  if (pendingHere) {
    const last = messages[messages.length - 1];
    const alreadyThere = last && last.role === "user" && last.content === state.inflight.text;
    if (!alreadyThere) els.messages.append(bubble({ role: "user", content: state.inflight.text }));
    els.messages.append(pendingBubble());
  }
  scrollDown();
}

function emptyState() {
  const wrap = document.createElement("div");
  wrap.className = "empty";
  const heading = document.createElement("h2");
  heading.textContent = "Pregunta al grafo";
  const copy = document.createElement("p");
  copy.textContent = "Cada chat recuerda lo anterior. Puedes pedir datos nuevos o hablar de lo que ya encontró.";
  const examples = document.createElement("div");
  examples.className = "examples";
  for (const text of EXAMPLES) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", () => useExample(text));
    examples.append(button);
  }
  wrap.append(heading, copy, examples);
  return wrap;
}

async function useExample(text) {
  if (!state.currentId) await createSession();
  if (!state.currentId || state.inflight) return;
  els.input.value = text;
  resizeInput();
  els.input.focus();
}

function bubble(message) {
  const node = document.createElement("article");
  node.className = "bubble " + (message.role === "user" ? "user" : "assistant");
  if (message.role === "user") {
    node.textContent = message.content;
    return node;
  }
  const body = document.createElement("div");
  body.className = "body";
  body.innerHTML = renderMarkdown(message.content || "");
  node.append(body);
  if (message.route && ROUTE_LABELS[message.route]) {
    const badge = document.createElement("span");
    badge.className = "route";
    badge.textContent = ROUTE_LABELS[message.route];
    node.append(badge);
  }
  return node;
}

function pendingBubble() {
  const node = document.createElement("article");
  node.className = "bubble assistant pending";
  node.textContent = "Consultando el grafo…";
  return node;
}

function errorNote(text) {
  const node = document.createElement("article");
  node.className = "bubble error";
  node.textContent = text;
  return node;
}

function showError(text) {
  const empty = els.messages.querySelector(".empty");
  if (empty) empty.remove();
  els.messages.append(errorNote(text));
  scrollDown();
}

function renderMarkdown(text) {
  if (typeof marked === "undefined" || typeof marked.parse !== "function") {
    return escapeHtml(text).replace(/\n/g, "<br>");
  }
  const html = marked.parse(text || "", { gfm: true, breaks: true });
  const template = document.createElement("template");
  template.innerHTML = html;
  template.content.querySelectorAll("script, iframe, object, embed, link, meta").forEach((node) => {
    node.remove();
  });
  template.content.querySelectorAll("*").forEach((element) => {
    for (const attr of [...element.attributes]) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on") || name === "srcdoc") element.removeAttribute(attr.name);
      if ((name === "href" || name === "src") && /^\s*javascript:/i.test(attr.value)) {
        element.removeAttribute(attr.name);
      }
    }
  });
  return template.innerHTML;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function send(raw) {
  const content = raw.trim();
  if (!content || !state.currentId || state.inflight) return;
  const sessionId = state.currentId;
  state.inflight = { sessionId, text: content };
  els.input.value = "";
  resizeInput();
  syncComposer();
  renderSessions();
  const empty = els.messages.querySelector(".empty");
  if (empty) empty.remove();
  els.messages.append(bubble({ role: "user", content }));
  els.messages.append(pendingBubble());
  scrollDown();

  try {
    const response = await fetch("/api/sessions/" + encodeURIComponent(sessionId) + "/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) {
      const detail = await readError(response);
      state.inflight = null;
      if (state.currentId === sessionId) {
        try {
          await loadMessages(sessionId);
        } catch (_error) {
          /* el hilo local sigue visible */
        }
        showError(detail);
      }
      return;
    }
    state.inflight = null;
    await refreshSessions();
    if (state.currentId === sessionId) {
      const session = state.sessions.find((item) => item.id === sessionId);
      if (session) els.title.textContent = session.title;
      await loadMessages(sessionId);
    }
  } catch (error) {
    state.inflight = null;
    if (state.currentId === sessionId) showError(error.message || "Error de red");
  } finally {
    syncComposer();
    renderSessions();
  }
}

async function renameSession(id, title) {
  const response = await fetch("/api/sessions/" + encodeURIComponent(id), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    showError(await readError(response));
    renderSessions();
    return;
  }
  await refreshSessions();
  if (state.currentId === id) {
    const session = state.sessions.find((item) => item.id === id);
    if (session) els.title.textContent = session.title;
  }
}

async function removeSession(id) {
  if (state.inflight && state.inflight.sessionId === id) return;
  const session = state.sessions.find((item) => item.id === id);
  const title = session ? session.title : "este chat";
  if (!window.confirm("¿Borrar «" + title + "»?")) return;
  const response = await fetch("/api/sessions/" + encodeURIComponent(id), { method: "DELETE" });
  if (!response.ok) {
    showError(await readError(response));
    return;
  }
  const wasCurrent = state.currentId === id;
  await refreshSessions();
  if (!wasCurrent) return;
  if (state.sessions.length) {
    await openSession(state.sessions[0].id);
    return;
  }
  state.currentId = null;
  history.replaceState(null, "", location.pathname + location.search);
  els.title.textContent = "GraphRAG";
  renderThread([]);
  syncComposer();
}

function syncComposer() {
  const busy = Boolean(state.inflight);
  const ready = Boolean(state.currentId) && !busy;
  els.input.disabled = !ready;
  els.send.disabled = !ready;
  els.newChat.disabled = busy;
  if (!state.currentId) els.input.placeholder = "Crea un chat para empezar";
  else if (busy) els.input.placeholder = "Consulta en curso…";
  else els.input.placeholder = "Escribe una pregunta…";
}

function resizeInput() {
  els.input.style.height = "auto";
  els.input.style.height = Math.min(els.input.scrollHeight, 160) + "px";
}

function scrollDown() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function readError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg || String(item)).join(" ");
    }
  } catch (_error) {
    /* cuerpo vacío */
  }
  return "No se pudo completar la acción";
}
