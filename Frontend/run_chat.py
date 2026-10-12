"""Abre el chat en el puerto 8000.

En Windows, http://localhost a veces entra por IPv6 y uvicorn solo
escucha 127.0.0.1, así que el navegador dice que no abre. Este script
escucha en las dos.

    cd Frontend
    python run_chat.py

Luego abre http://127.0.0.1:8000
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parent
PIPELINE_ROOT = FRONTEND_ROOT.parent / "Pipeline_RAG"
for path in (FRONTEND_ROOT, PIPELINE_ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def _listen(address: tuple, family: int, v6only: bool = False) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if v6only:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind(address)
    sock.listen(128)
    return sock


def main() -> None:
    try:
        import uvicorn
        from api.server import app
    except ModuleNotFoundError as exc:
        print(f"Falta un paquete ({exc.name}).")
        print("Desde la raíz del repo: pip install -r requirements.txt")
        sys.exit(1)

    port = 8000
    sockets = []
    try:
        sockets.append(_listen(("127.0.0.1", port), socket.AF_INET))
    except OSError as exc:
        print(f"No pude usar el puerto {port} ({exc}).")
        print("Si ya hay un chat abierto, ciérralo y vuelve a correr este script.")
        sys.exit(1)
    try:
        sockets.append(_listen(("::1", port), socket.AF_INET6, v6only=True))
    except OSError:
        pass

    print(f"Chat listo: http://127.0.0.1:{port}")
    print(f"También:    http://localhost:{port}")
    config = uvicorn.Config(app, log_level="info")
    uvicorn.Server(config).run(sockets=sockets)


if __name__ == "__main__":
    main()
