import json
from pathlib import Path

p = Path("Pipeline_RAG/00_run_script.ipynb")
nb = json.loads(p.read_text(encoding="utf-8"))
print("CELLS", len(nb["cells"]))
for i, c in enumerate(nb["cells"]):
    src = "".join(c.get("source", []))
    preview = src[:300].replace("\n", " | ")
    print(f"--- cell {i} {c['cell_type']} ({len(src)} chars) ---")
    print(preview)
    print()
